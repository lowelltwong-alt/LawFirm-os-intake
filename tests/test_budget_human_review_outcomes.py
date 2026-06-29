import pytest

from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_human_review_packet import run_budget_human_review_packet
from lawfirm_os_intake.budget_human_review_outcomes import (
    build_budget_human_review_outcome_report,
    run_budget_human_review_outcome_record,
)
from lawfirm_os_intake.budget_lake_admission_bundle import (
    run_budget_event_lake_admission_bundle,
)
from lawfirm_os_intake.budget_lifecycle_audit import run_budget_lifecycle_audit
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.carrier_rejection_learning import run_carrier_rejection_learning
from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    BudgetHumanReviewOutcomeDecision,
    BudgetHumanReviewOutcomeRecord,
    BudgetHumanReviewOutcomeReport,
    BudgetHumanReviewPacket,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run_budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    return run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )


def _generate_human_review_packet(tmp_path, repo_root):
    _, budget_dir = _run_budget(tmp_path, repo_root)
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
        budget_path=budget_dir / "legal_budget_proposal.json",
        source_bundle_path=repo_root
        / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        out_dir=tmp_path / "carrier-rejections",
    )
    _, carrier_review_dir = run_carrier_rejection_review(
        reconciliation_report_path=carrier_dir / "carrier_rejection_reconciliation_report.json",
        out_dir=tmp_path / "carrier-rejection-review",
    )
    _, carrier_learning_dir = run_carrier_rejection_learning(
        review_packet_path=carrier_review_dir / "carrier_rejection_review_packet.json",
        out_dir=tmp_path / "carrier-rejection-learning",
    )
    _, lake_dir = run_budget_event_lake_admission_bundle(
        out_dir=tmp_path / "lake-bundle",
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=(
            actuals_dir / "budget_actual_variance_ledger_report.json"
        ),
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
    )
    _, lifecycle_dir = run_budget_lifecycle_audit(
        out_dir=tmp_path / "lifecycle-audit",
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=(
            actuals_dir / "budget_actual_variance_ledger_report.json"
        ),
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
        budget_event_lake_bundle_report_path=(
            lake_dir / "budget_event_lake_admission_bundle_report.json"
        ),
    )
    packet, run_dir = run_budget_human_review_packet(
        budget_lifecycle_audit_report_path=lifecycle_dir / "budget_lifecycle_audit_report.json",
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        budget_actual_comparison_report_path=actuals_dir / "budget_actual_comparison_report.json",
        carrier_rejection_review_packet_path=carrier_review_dir
        / "carrier_rejection_review_packet.json",
        carrier_rejection_learning_report_path=carrier_learning_dir
        / "carrier_rejection_learning_report.json",
        out_dir=tmp_path / "budget-human-review",
    )
    persisted = BudgetHumanReviewPacket.model_validate(
        load_json(run_dir / "budget_human_review_packet.json")
    )
    assert persisted.budget_human_review_packet_id == packet.budget_human_review_packet_id
    return persisted, run_dir / "budget_human_review_packet.json"


def _decision_from_template(packet, template):
    outcome = template.recommended_outcome
    data = {
        "decision_id": f"budget-human-review-decision-{template.template_id}",
        "template_id": template.template_id,
        "review_area": template.review_area,
        "outcome": outcome,
        "decision_reason": (
            f"Synthetic reviewer accepted the template recommendation for {template.review_area}."
        ),
        "evidence_refs": [
            packet.budget_human_review_packet_id,
            template.template_id,
            *template.source_recommendation_ids,
        ],
        "source_recommendation_ids": template.source_recommendation_ids,
        "candidate_record_families": [],
    }
    if outcome in {"appeal", "reopen", "needs_more_information"}:
        data["followup_owner"] = "synthetic-budget-reviewer"
        data["followup_due_at"] = "2026-07-15T00:00:00Z"
        data["required_followups"] = [
            f"Resolve {template.review_area} before any external budget action."
        ]
    if outcome == "correct":
        data["proposed_correction_refs"] = [
            f"budget-human-review://correction/{template.template_id}"
        ]
    if outcome == "write_off":
        data["financial_amount"] = abs(packet.financial_summary.carrier_write_down_amount or 1.0)
    if outcome == "route_to_owner_review":
        data["target_owner_repo"] = "LawFirm-os-exceptions-lake-runtime"
    return BudgetHumanReviewOutcomeDecision(**data)


def _outcome_record_from_packet(packet):
    decisions = [
        _decision_from_template(packet, template) for template in packet.decision_templates
    ]
    return BudgetHumanReviewOutcomeRecord(
        budget_human_review_outcome_record_id=(
            f"budget-human-review-outcome-{packet.budget_human_review_packet_id}"
        ),
        budget_human_review_packet_id=packet.budget_human_review_packet_id,
        source_budget_human_review_packet_ref="budget_human_review_packet.json",
        reviewer_id="synthetic-budget-reviewer",
        reviewer_role="budget_review_owner",
        reviewed_at="2026-06-29T00:00:00Z",
        overall_outcome="correct",
        decision_reason="Synthetic append-only human budget review outcome.",
        decisions=decisions,
    )


def test_budget_human_review_outcome_records_append_only_decisions(tmp_path, repo_root):
    packet, packet_path = _generate_human_review_packet(tmp_path, repo_root)
    record = _outcome_record_from_packet(packet)
    record_path = write_json(
        tmp_path / "budget_human_review_outcome.json",
        record.model_dump(mode="json"),
    )

    report, run_dir = run_budget_human_review_outcome_record(
        budget_human_review_packet_path=packet_path,
        outcome_path=record_path,
        out_dir=tmp_path / "budget-human-review-outcome",
    )
    persisted = BudgetHumanReviewOutcomeReport.model_validate(
        load_json(run_dir / "budget_human_review_outcome_report.json")
    )
    history = load_jsonl(run_dir / "budget_human_review_outcome_history.jsonl")
    notes = (run_dir / "budget_human_review_outcome_report.md").read_text(encoding="utf-8")

    assert persisted.budget_human_review_outcome_report_id == (
        report.budget_human_review_outcome_report_id
    )
    assert report.status == "budget_human_review_outcome_recorded"
    assert report.decision_count == len(packet.decision_templates)
    assert report.appeal_decision_count == 1
    assert report.write_off_decision_count == 1
    assert report.correction_decision_count == 1
    assert report.route_to_owner_decision_count == 1
    assert report.no_learning_change_decision_count == 1
    assert "carrier_rejection_appeal_followup_candidate" in (report.candidate_lake_event_labels)
    assert len(history) == 1
    assert history[0]["budget_human_review_outcome_record_id"] == (
        record.budget_human_review_outcome_record_id
    )
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.budget_submission_performed is False
    assert report.appeal_submission_performed is False
    assert report.budget_mutation_performed is False
    assert report.carrier_guideline_mutation_performed is False
    assert report.silent_learning_performed is False
    assert "does not submit a budget or appeal" in notes


def test_budget_human_review_outcome_blocks_unknown_template(tmp_path, repo_root):
    packet, packet_path = _generate_human_review_packet(tmp_path, repo_root)
    record = _outcome_record_from_packet(packet)
    record.decisions[0].template_id = "missing-template"

    report = build_budget_human_review_outcome_report(
        budget_human_review_packet=packet,
        budget_human_review_packet_ref=str(packet_path),
        outcome_record=record,
        history_ref="budget_human_review_outcome_history.jsonl",
    )

    assert report.status == "blocked_by_outcome_evidence"
    assert any(
        check.check_id == "outcome_decisions_match_templates" and check.status == "failed"
        for check in report.checks
    )
    assert report.external_writes_performed is False


def test_budget_human_review_outcome_requires_appeal_followup(tmp_path, repo_root):
    packet, _ = _generate_human_review_packet(tmp_path, repo_root)
    template = next(
        template
        for template in packet.decision_templates
        if template.recommended_outcome == "appeal"
    )
    data = _decision_from_template(packet, template).model_dump(mode="json")
    data.pop("followup_owner")

    with pytest.raises(ValueError, match="appeal decisions require followup_owner"):
        BudgetHumanReviewOutcomeDecision.model_validate(data)


def test_budget_human_review_outcome_cli_writes_record_history_and_report(
    tmp_path,
    repo_root,
    capsys,
):
    packet, packet_path = _generate_human_review_packet(tmp_path, repo_root)
    record_path = write_json(
        tmp_path / "budget_human_review_outcome.json",
        _outcome_record_from_packet(packet).model_dump(mode="json"),
    )

    exit_code = main(
        [
            "record-budget-human-review-outcome",
            "--budget-human-review-packet",
            str(packet_path),
            "--outcome",
            str(record_path),
            "--out-dir",
            str(tmp_path / "budget-human-review-outcome-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "budget_human_review_outcome_recorded"' in captured.out
    assert '"appeal_decision_count": 1' in captured.out
    assert '"write_off_decision_count": 1' in captured.out
    assert '"budget_submission_performed": false' in captured.out
    assert '"appeal_submission_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (
        tmp_path / "budget-human-review-outcome-cli" / "budget_human_review_outcome_report.json"
    ).is_file()
    assert (
        tmp_path / "budget-human-review-outcome-cli" / "budget_human_review_outcome_history.jsonl"
    ).is_file()
