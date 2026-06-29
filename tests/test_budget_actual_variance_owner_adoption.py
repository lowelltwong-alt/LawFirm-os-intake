import json

from lawfirm_os_intake.budget_actual_variance_owner_adoption import (
    run_budget_actual_variance_owner_adoption,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetActualVarianceDriverCandidate,
    BudgetActualVarianceLedgerEvent,
    BudgetActualVarianceLedgerReport,
    BudgetActualVarianceOwnerAdoptionReport,
)
from lawfirm_os_intake.util import load_json, write_json


def _comparison_report() -> BudgetActualComparisonReport:
    return BudgetActualComparisonReport(
        budget_actual_comparison_report_id="budget-actual-comparison-owner-fixture",
        run_id="run-owner-fixture",
        preflight_packet_id="preflight-owner-fixture",
        budget_proposal_id="budget-proposal-owner-fixture",
        status="variance_review_required",
        comparison_scope="phase_and_code",
        comparison_budget_state="human_revised_candidate",
        budget_revision_report_id="budget-revision-owner-fixture",
        budget_revision_report_ref="synthetic://budget_revision_report.json",
        actual_resolution_scenario_id="midcase_resolution",
        phase_comparisons=[
            BudgetActualPhaseComparison(
                phase_id="L300",
                budgeted_fees=100.0,
                budgeted_expenses=0.0,
                budgeted_total=100.0,
                actual_fees=135.0,
                actual_expenses=5.0,
                actual_total=140.0,
                variance_amount=40.0,
                variance_percent=40.0,
                status="over_threshold",
                external_code_candidates=["L300"],
                variance_driver_candidates=["fee_overrun"],
                requires_human_review=True,
            )
        ],
        variance_driver_candidates=[
            BudgetActualVarianceDriverCandidate(
                candidate_id="budgetvardriver-owner-fixture",
                driver_label="fee_overrun",
                phase_id="L300",
                variance_amount=40.0,
                reason="Synthetic actual costs exceed the revised candidate budget.",
                target_learning_loop="budget_driver",
            )
        ],
        learning_disposition_candidates=["budget_driver"],
        variance_threshold_percent=10.0,
        total_budgeted=100.0,
        total_actual=140.0,
        total_variance_amount=40.0,
        total_variance_percent=40.0,
        actuals_source_ref="synthetic://actuals/owner-fixture.json",
        generated_at="2026-06-29T00:00:00Z",
    )


def _variance_event(
    *,
    comparison_report_id: str = "budget-actual-comparison-owner-fixture",
) -> BudgetActualVarianceLedgerEvent:
    return BudgetActualVarianceLedgerEvent(
        budget_actual_variance_ledger_event_id="budget-actual-event-owner-fixture",
        ledger_id="budget-actual-ledger-owner-fixture",
        sequence_index=0,
        budget_actual_comparison_report_id=comparison_report_id,
        run_id="run-owner-fixture",
        preflight_packet_id="preflight-owner-fixture",
        budget_proposal_id="budget-proposal-owner-fixture",
        budget_revision_report_id="budget-revision-owner-fixture",
        actuals_source_ref="synthetic://actuals/owner-fixture.json",
        comparison_budget_state="human_revised_candidate",
        actual_resolution_scenario_id="midcase_resolution",
        comparison_scope="phase",
        phase_id="L300",
        event_kind="budget_actual_phase_comparison_recorded",
        decision_status="over_threshold_requires_review",
        local_event_label="budget_actual_cost_variance_requires_review",
        comparison_status="over_threshold",
        budgeted_fees=100.0,
        budgeted_expenses=0.0,
        budgeted_total=100.0,
        actual_fees=135.0,
        actual_expenses=5.0,
        actual_total=140.0,
        variance_amount=40.0,
        variance_percent=40.0,
        variance_driver_candidates=["fee_overrun"],
        learning_disposition_candidates=["budget_driver"],
        proposed_next_actions=[
            "review_budget_actual_variance",
            "route_confirmed_signal_to_reviewed_learning_gate",
        ],
        required_human_decisions=[
            "confirm_variance_is_real",
            "choose_learning_disposition_or_no_learning",
        ],
        structured_refs=[
            "synthetic://budget_actual_comparison_report.json",
            "budget-proposal://budget-proposal-owner-fixture",
            "budget-phase://L300",
        ],
        requires_human_review=True,
    )


def _ledger_report(
    *,
    comparison_report_id: str = "budget-actual-comparison-owner-fixture",
) -> BudgetActualVarianceLedgerReport:
    event = _variance_event(comparison_report_id=comparison_report_id)
    return BudgetActualVarianceLedgerReport(
        budget_actual_variance_ledger_report_id="budget-actual-ledger-report-owner-fixture",
        ledger_id="budget-actual-ledger-owner-fixture",
        budget_actual_comparison_report_id=comparison_report_id,
        run_id="run-owner-fixture",
        preflight_packet_id="preflight-owner-fixture",
        budget_proposal_id="budget-proposal-owner-fixture",
        budget_revision_report_id="budget-revision-owner-fixture",
        budget_revision_report_ref="synthetic://budget_revision_report.json",
        actuals_source_ref="synthetic://actuals/owner-fixture.json",
        status="variance_ledger_ready_for_review",
        comparison_scope="phase_and_code",
        comparison_budget_state="human_revised_candidate",
        actual_resolution_scenario_id="midcase_resolution",
        entry_count=1,
        phase_event_count=1,
        code_event_count=0,
        revision_context_event_count=0,
        variance_review_event_count=1,
        missing_actuals_event_count=0,
        actuals_without_budget_event_count=0,
        within_threshold_event_count=0,
        event_kind_counts={"budget_actual_phase_comparison_recorded": 1},
        total_budgeted=100.0,
        total_actual=140.0,
        total_variance_amount=40.0,
        total_variance_percent=40.0,
        events=[event],
        required_next_gates=[
            "human_actuals_variance_review",
            "orchestrator_supplies_billing_actuals_before_real_use",
            "append_only_actuals_outcome_required",
            "exception_lake_admission_by_exception_lake_runtime",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "no_silent_profile_template_budget_or_guideline_mutation",
        ],
        generated_at="2026-06-29T00:00:00Z",
    )


def test_budget_actual_variance_owner_adoption_packets_are_ready(tmp_path):
    comparison_path = write_json(
        tmp_path / "budget_actual_comparison_report.json",
        _comparison_report().model_dump(mode="json"),
    )
    ledger_path = write_json(
        tmp_path / "budget_actual_variance_ledger_report.json",
        _ledger_report().model_dump(mode="json"),
    )

    report, run_dir = run_budget_actual_variance_owner_adoption(
        budget_actual_comparison_report_path=comparison_path,
        budget_actual_variance_ledger_report_path=ledger_path,
        out_dir=tmp_path / "actual-variance-owner-adoption",
    )

    persisted = BudgetActualVarianceOwnerAdoptionReport.model_validate(
        load_json(run_dir / "budget_actual_variance_owner_adoption_report.json")
    )
    rows = [
        json.loads(line)
        for line in (run_dir / "budget_actual_variance_owner_adoption_packets.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert persisted.owner_adoption_report_id == report.owner_adoption_report_id
    assert persisted.status == "budget_actual_variance_owner_adoption_packets_ready"
    assert persisted.packet_count == persisted.ready_packet_count == 3
    assert persisted.blocked_packet_count == 0
    assert persisted.target_repos == [
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
    ]
    assert persisted.candidate_lake_event_labels == ["budget_actual_cost_variance_requires_review"]
    assert persisted.variance_driver_candidates == ["fee_overrun"]
    assert persisted.learning_disposition_candidates == ["budget_driver"]
    assert persisted.variance_review_event_count == 1
    assert persisted.billing_connector_read_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.silent_learning_performed is False
    assert len(rows) == 3
    assert all(row["status"] == "ready_for_owner_review" for row in rows)
    assert any(
        "governed billing-actuals read boundary" in action
        for packet in persisted.packets
        if packet.target_repo == "LawFirm-os-orchestrator"
        for action in packet.required_owner_actions
    )
    assert (
        run_dir
        / "budget_actual_variance_owner_packets"
        / "semantic-substrate.budget_actual_variance_owner_packet.json"
    ).is_file()
    assert (
        run_dir
        / "budget_actual_variance_owner_packets"
        / "exceptions-lake-runtime.budget_actual_variance_owner_packet.md"
    ).is_file()


def test_budget_actual_variance_owner_adoption_blocks_mismatched_lineage(tmp_path):
    comparison_path = write_json(
        tmp_path / "budget_actual_comparison_report.json",
        _comparison_report().model_dump(mode="json"),
    )
    ledger_path = write_json(
        tmp_path / "budget_actual_variance_ledger_report.json",
        _ledger_report(comparison_report_id="different-comparison-report").model_dump(mode="json"),
    )

    report, _ = run_budget_actual_variance_owner_adoption(
        budget_actual_comparison_report_path=comparison_path,
        budget_actual_variance_ledger_report_path=ledger_path,
        out_dir=tmp_path / "actual-variance-owner-adoption-blocked",
    )

    assert report.status == "blocked_by_budget_actual_variance_evidence"
    assert report.blocked_packet_count == 3
    assert any(
        check.check_id == "budget_actual_variance_ledger_matches_comparison"
        and check.status == "failed"
        for check in report.checks
    )
    assert report.github_issue_created is False
    assert report.sibling_repo_write_performed is False
    assert report.lake_write_performed is False
    assert report.billing_connector_read_performed is False


def test_budget_actual_variance_owner_adoption_cli(tmp_path, capsys):
    comparison_path = write_json(
        tmp_path / "budget_actual_comparison_report.json",
        _comparison_report().model_dump(mode="json"),
    )
    ledger_path = write_json(
        tmp_path / "budget_actual_variance_ledger_report.json",
        _ledger_report().model_dump(mode="json"),
    )

    exit_code = main(
        [
            "build-budget-actual-variance-owner-adoption",
            "--budget-actual-comparison-report",
            str(comparison_path),
            "--budget-actual-variance-ledger-report",
            str(ledger_path),
            "--out-dir",
            str(tmp_path / "actual-variance-owner-adoption-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "budget_actual_variance_owner_adoption_packets_ready"' in captured.out
    assert '"packet_count": 3' in captured.out
    assert '"variance_review_event_count": 1' in captured.out
    assert '"billing_connector_read_performed": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (
        tmp_path
        / "actual-variance-owner-adoption-cli"
        / "budget_actual_variance_owner_adoption_report.json"
    ).is_file()
