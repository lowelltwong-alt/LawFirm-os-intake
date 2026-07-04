from copy import deepcopy

import pytest

from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_learning_loop import (
    BUDGET_LEARNING_LOOP_REPORT_FILENAME,
    run_budget_learning_loop_report,
)
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.carrier_rejection_learning import run_carrier_rejection_learning
from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import BudgetLearningLoopReport, HumanConfirmation
from lawfirm_os_intake.reviewed_learning_gate import run_reviewed_learning_gate
from lawfirm_os_intake.util import load_json, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    budget, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    budget_path = write_json(tmp_path / "budget.json", budget.model_dump(mode="json"))
    return budget, budget_dir, budget_path


def _learning_loop_sources(tmp_path, repo_root):
    _, budget_dir, budget_path = _budget(tmp_path, repo_root)
    _, review_dir = run_budget_review_record(
        budget_path=budget_dir / "legal_budget_proposal.json",
        review_path=repo_root
        / "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        out_dir=tmp_path / "budget-review",
    )
    _, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_dir / "legal_budget_proposal.json",
        actuals_path=repo_root / "examples/synthetic/actuals/medmal-phase-code-actuals.json",
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        out_dir=tmp_path / "actuals",
    )
    _, carrier_dir = run_carrier_rejection_capture(
        budget_path,
        repo_root / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        tmp_path / "carrier-rejections",
    )
    _, carrier_review_dir = run_carrier_rejection_review(
        carrier_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "carrier-rejection-review",
    )
    _, learning_dir = run_carrier_rejection_learning(
        carrier_review_dir / "carrier_rejection_review_packet.json",
        tmp_path / "carrier-rejection-learning",
    )
    _, gate_dir = run_reviewed_learning_gate(
        out_dir=tmp_path / "learning-gate",
        carrier_rejection_learning_report_path=(
            learning_dir / "carrier_rejection_learning_report.json"
        ),
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        budget_actual_comparison_report_path=(actuals_dir / "budget_actual_comparison_report.json"),
    )
    return {
        "actuals": actuals_dir / "budget_actual_comparison_report.json",
        "actual_ledger": actuals_dir / "budget_actual_variance_ledger_report.json",
        "reconciliation": carrier_dir / "carrier_rejection_reconciliation_report.json",
        "carrier_ledger": carrier_dir / "carrier_rejection_decision_ledger_report.json",
        "review_packet": carrier_review_dir / "carrier_rejection_review_packet.json",
        "learning": learning_dir / "carrier_rejection_learning_report.json",
        "gate": gate_dir / "reviewed_learning_gate_report.json",
    }


def _run_report(tmp_path, sources):
    return run_budget_learning_loop_report(
        budget_actual_comparison_report_path=sources["actuals"],
        budget_actual_variance_ledger_report_path=sources["actual_ledger"],
        carrier_rejection_reconciliation_report_path=sources["reconciliation"],
        carrier_rejection_decision_ledger_report_path=sources["carrier_ledger"],
        carrier_rejection_review_packet_path=sources["review_packet"],
        carrier_rejection_learning_report_path=sources["learning"],
        reviewed_learning_gate_report_path=sources["gate"],
        out_dir=tmp_path / "budget-learning-loop",
        generated_at="2026-07-04T00:00:00Z",
    )


def test_budget_learning_loop_report_summarizes_actuals_rejections_and_learning(
    tmp_path,
    repo_root,
):
    sources = _learning_loop_sources(tmp_path, repo_root)

    report, run_dir = _run_report(tmp_path, sources)
    persisted = BudgetLearningLoopReport.model_validate(
        load_json(run_dir / BUDGET_LEARNING_LOOP_REPORT_FILENAME)
    )

    assert persisted.budget_learning_loop_report_id == report.budget_learning_loop_report_id
    assert report.status == "budget_learning_loop_ready_for_review"
    assert report.comparison_budget_state == "human_revised_candidate"
    assert report.actuals.status == "variance_review_required"
    assert report.actuals.ledger_entry_count == (
        report.actuals.phase_event_count
        + report.actuals.code_event_count
        + report.actuals.revision_context_event_count
    )
    assert report.actuals.variance_review_event_count == 5
    assert report.actuals.actuals_without_budget_event_count == 2
    assert set(report.actuals.learning_disposition_candidates) >= {
        "budget_driver",
        "template_mapping",
    }
    assert report.carrier_rejections.decision_ledger_entry_count == 10
    assert report.carrier_rejections.total_disputed_amount == 21950.0
    assert report.carrier_rejections.total_recovered_amount == 8000.0
    assert report.carrier_rejections.total_write_down_amount == 7000.0
    assert report.reviewed_learning_gate.candidate_count == 13
    assert report.reviewed_learning_gate.reviewed_outcome_required is True
    assert report.reviewed_learning_gate.shadow_eval_required is True
    assert {lane.lane_id for lane in report.lifecycle_lanes} == {
        "actuals_variance_review",
        "carrier_rejection_capture",
        "appeal_financial_outcome",
        "reviewed_learning_gate",
    }
    assert report.candidate_only is True
    assert report.synthetic_only is True
    assert report.local_json_only is True
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.appeal_submission_performed is False
    assert report.silent_learning_performed is False
    assert (run_dir / "budget_learning_loop_report.md").is_file()


def test_budget_learning_loop_cli_writes_report(tmp_path, repo_root, capsys):
    sources = _learning_loop_sources(tmp_path, repo_root)

    exit_code = main(
        [
            "build-budget-learning-loop-report",
            "--budget-actual-comparison-report",
            str(sources["actuals"]),
            "--budget-actual-variance-ledger-report",
            str(sources["actual_ledger"]),
            "--carrier-rejection-reconciliation-report",
            str(sources["reconciliation"]),
            "--carrier-rejection-decision-ledger-report",
            str(sources["carrier_ledger"]),
            "--carrier-rejection-review-packet",
            str(sources["review_packet"]),
            "--carrier-rejection-learning-report",
            str(sources["learning"]),
            "--reviewed-learning-gate-report",
            str(sources["gate"]),
            "--out-dir",
            str(tmp_path / "budget-learning-loop-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "budget_learning_loop_ready_for_review"' in captured.out
    assert '"learning_candidate_count": 13' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / "budget-learning-loop-cli" / BUDGET_LEARNING_LOOP_REPORT_FILENAME).is_file()


def test_budget_learning_loop_report_fails_closed_on_mismatched_budget_id(
    tmp_path,
    repo_root,
):
    sources = _learning_loop_sources(tmp_path, repo_root)
    raw_actuals = deepcopy(load_json(sources["actuals"]))
    raw_actuals["budget_proposal_id"] = "wrong-budget-id"
    mismatched_actuals = write_json(tmp_path / "mismatched_actuals.json", raw_actuals)
    sources = {**sources, "actuals": mismatched_actuals}

    with pytest.raises(ValueError, match="budget_proposal_id"):
        _run_report(tmp_path, sources)
