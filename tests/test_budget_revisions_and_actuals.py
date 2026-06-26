from pathlib import Path

from lawfirm_os_intake.budget_actuals import (
    build_budget_actual_comparison_report,
    run_budget_actual_comparison,
)
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    BudgetActualComparisonReport,
    BudgetChangeLedgerReport,
    BudgetProposal,
    BudgetRevisionReport,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def _run_budget(tmp_path, repo_root) -> tuple[BudgetProposal, Path]:
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget, budget_dir


def test_budget_review_record_writes_append_only_revision_report(tmp_path, repo_root):
    budget, budget_dir = _run_budget(tmp_path, repo_root)
    original_payload = load_json(budget_dir / "legal_budget_proposal.json")

    report, review_dir = run_budget_review_record(
        budget_path=budget_dir / "legal_budget_proposal.json",
        review_path=repo_root
        / "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        out_dir=tmp_path / "budget-review",
    )
    persisted = BudgetRevisionReport.model_validate(
        load_json(review_dir / "budget_revision_report.json")
    )
    history = load_jsonl(review_dir / "budget_revision_history.jsonl")
    candidates = load_jsonl(review_dir / "budget_revision_exception_lake_candidates.jsonl")
    ledger = BudgetChangeLedgerReport.model_validate(
        load_json(review_dir / "budget_change_ledger_report.json")
    )
    ledger_rows = load_jsonl(review_dir / "budget_change_ledger.jsonl")

    assert persisted.budget_revision_report_id == report.budget_revision_report_id
    assert persisted.status == "revision_recorded"
    assert persisted.budget_proposal_id == budget.budget_proposal_id
    assert persisted.change_count == 2
    assert persisted.numeric_change_count == 2
    assert persisted.total_delta != 0
    assert persisted.revised_total == round(persisted.original_total + persisted.total_delta, 2)
    assert persisted.original_budget_mutated is False
    assert persisted.superseding_budget_written is False
    assert persisted.budget_submission_authorized is False
    assert persisted.carrier_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False
    assert history[0]["budget_proposal_id"] == budget.budget_proposal_id
    assert candidates[0]["local_event_label"] == "budget_human_change_recorded"
    assert candidates[0]["raw_payload_included"] is False
    assert candidates[0]["canonical_promotion_required"] is True
    assert ledger.status == "ledger_recorded"
    assert ledger.budget_revision_report_id == persisted.budget_revision_report_id
    assert ledger.budget_review_change_record_id == persisted.budget_review_change_record_id
    assert ledger.entry_count == 2
    assert ledger.numeric_change_entry_count == 2
    assert ledger.total_delta == persisted.total_delta
    assert ledger.event_kind_counts == {"human_budget_change_recorded": 2}
    assert len(ledger_rows) == 2
    assert ledger_rows[0]["budget_change_ledger_event_id"] == (
        ledger.events[0].budget_change_ledger_event_id
    )
    assert [event.change_class for event in ledger.events] == [
        "hours_change",
        "expense_change",
    ]
    assert ledger.events[0].budget_total_before_event == persisted.original_total
    assert ledger.events[-1].budget_total_after_event == persisted.revised_total
    assert all(
        event.exception_lake_local_event_label == "budget_human_change_recorded"
        for event in ledger.events
    )
    assert all(event.requires_exception_lake_admission_review for event in ledger.events)
    assert ledger.source_budget_mutated is False
    assert ledger.source_revision_report_mutated is False
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.silent_learning_performed is False
    assert (review_dir / "budget_change_ledger_report.md").is_file()
    assert load_json(budget_dir / "legal_budget_proposal.json") == original_payload


def test_budget_review_no_change_writes_outcome_ledger_event(tmp_path, repo_root):
    budget, budget_dir = _run_budget(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "confirmed-no-change-review.json",
        {
            "schema_version": "0.1",
            "budget_review_change_record_id": "budget-review-no-change.synthetic-medmal.v0_1",
            "budget_proposal_id": "__BUDGET_PROPOSAL_ID__",
            "reviewer_id": "synthetic-pricing-reviewer",
            "reviewer_role": "human_pricing_reviewer",
            "reviewed_at": "2026-06-26T00:00:00Z",
            "outcome": "confirmed_no_change",
            "decision_reason": "Synthetic reviewer confirms no budget edits are needed.",
            "changes": [],
        },
    )

    report, review_dir = run_budget_review_record(
        budget_path=budget_dir / "legal_budget_proposal.json",
        review_path=review_path,
        out_dir=tmp_path / "budget-review-no-change",
    )
    ledger = BudgetChangeLedgerReport.model_validate(
        load_json(review_dir / "budget_change_ledger_report.json")
    )
    event = ledger.events[0]

    assert report.status == "confirmed_no_change"
    assert ledger.status == "no_change_confirmed"
    assert ledger.entry_count == 1
    assert ledger.numeric_change_entry_count == 0
    assert ledger.event_kind_counts == {"human_budget_no_change_confirmed": 1}
    assert event.event_kind == "human_budget_no_change_confirmed"
    assert event.status == "no_change_confirmed"
    assert event.change_class == "review_outcome_only"
    assert event.change_id is None
    assert event.budget_total_before_event == report.original_total
    assert event.budget_total_after_event == report.original_total
    assert event.reviewer_id == "synthetic-pricing-reviewer"
    assert event.lake_write_performed is False
    assert event.sqlite_write_performed is False
    assert event.silent_learning_performed is False


def test_budget_actuals_compare_against_human_revised_candidate(tmp_path, repo_root):
    budget, budget_dir = _run_budget(tmp_path, repo_root)
    revision_report, review_dir = run_budget_review_record(
        budget_path=budget_dir / "legal_budget_proposal.json",
        review_path=repo_root
        / "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        out_dir=tmp_path / "budget-review",
    )

    report, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_dir / "legal_budget_proposal.json",
        actuals_path=repo_root / "examples/synthetic/actuals/medmal-phase-code-actuals.json",
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        out_dir=tmp_path / "actuals",
    )
    persisted = BudgetActualComparisonReport.model_validate(
        load_json(actuals_dir / "budget_actual_comparison_report.json")
    )
    candidates = load_jsonl(actuals_dir / "budget_actual_variance_candidates.jsonl")
    code_status = {row.code: row.status for row in persisted.code_comparisons}
    phase_status = {row.phase_id: row.status for row in persisted.phase_comparisons}

    assert persisted.budget_actual_comparison_report_id == report.budget_actual_comparison_report_id
    assert persisted.budget_revision_report_id == revision_report.budget_revision_report_id
    assert persisted.comparison_budget_state == "human_revised_candidate"
    assert persisted.comparison_scope == "phase_and_code"
    assert persisted.status == "variance_review_required"
    assert phase_status["L500"] == "over_threshold"
    assert code_status["L599"] == "over_threshold"
    assert "actuals_without_budget" in {
        driver.driver_label for driver in persisted.variance_driver_candidates
    }
    assert "human_revision_delta" in {
        driver.driver_label for driver in persisted.variance_driver_candidates
    }
    assert set(persisted.learning_disposition_candidates) >= {
        "budget_driver",
        "template_mapping",
    }
    assert persisted.billing_connector_read_performed is False
    assert persisted.billing_connector_write_performed is False
    assert persisted.external_writes_performed is False
    assert candidates[0]["local_event_label"] == "budget_actual_cost_variance_requires_review"


def test_budgeted_zero_actual_positive_is_over_threshold(tmp_path, repo_root):
    budget, _ = _run_budget(tmp_path, repo_root)
    report = build_budget_actual_comparison_report(
        run_id="budgetactualrun-test",
        preflight_packet_id=budget.preflight_packet_id,
        budget=budget,
        actuals_by_phase={"L599": {"fees": 1.0, "expenses": 0.0}},
        actuals_by_code={"L599": {"fees": 1.0, "expenses": 0.0}},
    )

    assert report.status == "variance_review_required"
    assert next(row for row in report.phase_comparisons if row.phase_id == "L599").status == (
        "over_threshold"
    )
    assert next(row for row in report.code_comparisons if row.code == "L599").status == (
        "over_threshold"
    )


def test_budget_actuals_use_actual_resolution_scenario_when_available(tmp_path, repo_root):
    budget, _ = _run_budget(tmp_path, repo_root)

    default_report = build_budget_actual_comparison_report(
        run_id="budgetactualrun-default",
        preflight_packet_id=budget.preflight_packet_id,
        budget=budget,
        actuals_by_phase={"L300": {"fees": 1.0, "expenses": 0.0}},
    )
    early_report = build_budget_actual_comparison_report(
        run_id="budgetactualrun-early",
        preflight_packet_id=budget.preflight_packet_id,
        budget=budget,
        actuals_by_phase={"L300": {"fees": 1.0, "expenses": 0.0}},
        actual_resolution_scenario_id="early_resolution",
    )

    default_l300 = next(row for row in default_report.phase_comparisons if row.phase_id == "L300")
    early_l300 = next(row for row in early_report.phase_comparisons if row.phase_id == "L300")
    assert default_l300.budgeted_total > 0
    assert early_l300.budgeted_total == 0
    assert early_l300.status == "over_threshold"
    assert early_report.actual_resolution_scenario_id == "early_resolution"
    assert "actuals_without_budget" in {
        driver.driver_label for driver in early_report.variance_driver_candidates
    }


def test_budget_review_and_actuals_cli(tmp_path, repo_root, capsys):
    _, budget_dir = _run_budget(tmp_path, repo_root)
    review_exit = main(
        [
            "record-budget-review",
            "--budget",
            str(budget_dir / "legal_budget_proposal.json"),
            "--review",
            str(
                repo_root
                / "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
            ),
            "--out-dir",
            str(tmp_path / "review-cli"),
        ]
    )
    actuals_exit = main(
        [
            "compare-budget-actuals",
            "--budget",
            str(budget_dir / "legal_budget_proposal.json"),
            "--actuals",
            str(repo_root / "examples/synthetic/actuals/medmal-phase-code-actuals.json"),
            "--budget-revision-report",
            str(tmp_path / "review-cli" / "budget_revision_report.json"),
            "--out-dir",
            str(tmp_path / "actuals-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert review_exit == 0
    assert actuals_exit == 0
    assert '"status": "revision_recorded"' in captured.out
    assert '"budget_change_ledger_entry_count": 2' in captured.out
    assert '"sqlite_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert '"comparison_budget_state": "human_revised_candidate"' in captured.out
    assert (tmp_path / "review-cli" / "budget_revision_report.json").is_file()
    assert (tmp_path / "review-cli" / "budget_change_ledger_report.json").is_file()
    assert (tmp_path / "review-cli" / "budget_change_ledger.jsonl").is_file()
    assert (tmp_path / "actuals-cli" / "budget_actual_comparison_report.json").is_file()
