from pathlib import Path

from lawfirm_os_intake.budget_lifecycle_owner_adoption import (
    run_budget_lifecycle_owner_adoption,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetLifecycleAuditCheck,
    BudgetLifecycleAuditReport,
    BudgetLifecycleFinancialSummary,
    BudgetLifecycleOwnerAdoptionReport,
)
from lawfirm_os_intake.util import load_json, write_json


REQUIRED_TARGET_REPOS = {
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
}


def _lifecycle_audit_report(*, ready=True) -> BudgetLifecycleAuditReport:
    return BudgetLifecycleAuditReport(
        lifecycle_audit_report_id=(
            "budget-lifecycle-audit-ready" if ready else "budget-lifecycle-audit-blocked"
        ),
        status=(
            "ready_for_budget_lifecycle_review"
            if ready
            else "blocked_inconsistent_lifecycle_evidence"
        ),
        budget_proposal_id="budget-proposal-1" if ready else None,
        preflight_packet_id="preflight-packet-1" if ready else None,
        run_ids=["run-1"],
        source_budget_change_ledger_report_ref="budget_change_ledger_report.json",
        source_budget_actual_variance_ledger_report_ref=(
            "budget_actual_variance_ledger_report.json"
        ),
        source_carrier_rejection_decision_ledger_report_ref=(
            "carrier_rejection_decision_ledger_report.json"
        ),
        source_budget_event_lake_bundle_report_ref=(
            "budget_event_lake_admission_bundle_report.json"
        ),
        budget_change_ledger_report_id="budget-change-ledger-report-1",
        budget_actual_variance_ledger_report_id="budget-actual-ledger-report-1",
        carrier_rejection_decision_ledger_report_id="carrier-decision-ledger-report-1",
        budget_event_lake_bundle_report_id="budget-event-lake-bundle-report-1",
        budget_change_event_count=1,
        actual_variance_event_count=2,
        carrier_rejection_event_count=3,
        total_lifecycle_event_count=6,
        human_budget_change_event_count=1,
        actual_variance_review_event_count=2,
        carrier_pending_decision_event_count=1,
        carrier_appeal_result_event_count=1,
        carrier_financial_outcome_event_count=1,
        pending_human_decision_count=2,
        required_human_decisions=["confirm_variance_is_real", "confirm_appeal_result"],
        proposed_next_actions=["review_budget_actual_variance", "review_appeal_result"],
        candidate_record_families=[
            "budget_human_change_record",
            "budget_actual_variance_record",
            "carrier_rejection_decision_record",
            "carrier_financial_outcome_record",
        ],
        local_event_labels=[
            "budget_human_change_recorded",
            "budget_actual_cost_variance_requires_review",
            "carrier_rejection_financial_outcome_recorded",
        ],
        financial_summary=BudgetLifecycleFinancialSummary(
            original_budget_total=100000,
            human_revision_total_delta=5000,
            human_revised_candidate_total=105000,
            actual_comparison_budgeted_total=105000,
            actual_total=112000,
            actual_variance_amount=7000,
            carrier_disputed_amount=12000,
            carrier_recovered_amount=4000,
            carrier_write_down_amount=8000,
        ),
        checks=[
            BudgetLifecycleAuditCheck(
                check_id="synthetic_lifecycle_check",
                status="passed" if ready else "failed",
                message="Synthetic lifecycle owner adoption check.",
                artifact_refs=["budget_lifecycle_audit_report.json"],
            )
        ],
        required_next_gates=[
            "human_budget_lifecycle_review",
            "orchestrator_evidence_packet_assembly",
            "exception_lake_runtime_admission_validation",
            "reviewed_learning_gate_before_candidate_changes",
            "no_silent_profile_template_budget_or_guideline_mutation",
        ],
        generated_at="2026-06-26T00:00:00Z",
    )


def _lifecycle_audit_report_path(tmp_path, *, ready=True) -> Path:
    return write_json(
        tmp_path / "budget_lifecycle_audit_report.json",
        _lifecycle_audit_report(ready=ready).model_dump(mode="json"),
    )


def test_budget_lifecycle_owner_adoption_groups_required_owners_without_writes(tmp_path):
    audit_path = _lifecycle_audit_report_path(tmp_path, ready=True)

    report, run_dir = run_budget_lifecycle_owner_adoption(
        budget_lifecycle_audit_report_path=audit_path,
        out_dir=tmp_path / "budget-lifecycle-owner-adoption",
    )
    persisted = BudgetLifecycleOwnerAdoptionReport.model_validate(
        load_json(run_dir / "budget_lifecycle_owner_adoption_report.json")
    )

    assert persisted.owner_adoption_report_id == report.owner_adoption_report_id
    assert persisted.status == "owner_adoption_packets_ready"
    assert persisted.packet_count == persisted.ready_packet_count == 3
    assert persisted.blocked_packet_count == 0
    assert set(persisted.target_repos) == REQUIRED_TARGET_REPOS
    assert set(packet.target_repo for packet in persisted.packets) == REQUIRED_TARGET_REPOS
    assert all(packet.status == "ready_for_owner_review" for packet in persisted.packets)
    assert all(
        packet.source_budget_proposal_id == "budget-proposal-1" for packet in persisted.packets
    )
    assert all(
        packet.source_preflight_packet_id == "preflight-packet-1" for packet in persisted.packets
    )
    assert all(packet.required_owner_actions for packet in persisted.packets)
    assert all(packet.acceptance_checks for packet in persisted.packets)
    assert all(packet.red_team_notes for packet in persisted.packets)
    assert all(Path(ref).is_file() for ref in persisted.packet_output_refs)
    assert (run_dir / "budget_lifecycle_owner_adoption_packets.jsonl").is_file()
    assert persisted.github_issue_created is False
    assert persisted.github_pr_created is False
    assert persisted.github_write_performed is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.connector_implemented is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "budget_lifecycle_owner_adoption_report.md").read_text(encoding="utf-8")
    assert "LawFirm-os-orchestrator" in notes
    assert "does not create issues" in notes


def test_budget_lifecycle_owner_adoption_blocks_failed_lifecycle_audit(tmp_path):
    audit_path = _lifecycle_audit_report_path(tmp_path, ready=False)

    report, _ = run_budget_lifecycle_owner_adoption(
        budget_lifecycle_audit_report_path=audit_path,
        out_dir=tmp_path / "budget-lifecycle-owner-adoption-blocked",
    )

    assert report.status == "blocked_by_lifecycle_audit"
    assert report.ready_packet_count == 0
    assert report.blocked_packet_count == 3
    assert all(packet.status == "blocked_by_lifecycle_audit" for packet in report.packets)
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False
    assert report.connector_implemented is False


def test_budget_lifecycle_owner_adoption_cli(tmp_path, capsys):
    audit_path = _lifecycle_audit_report_path(tmp_path, ready=True)

    exit_code = main(
        [
            "build-budget-lifecycle-owner-adoption",
            "--budget-lifecycle-audit-report",
            str(audit_path),
            "--out-dir",
            str(tmp_path / "budget-lifecycle-owner-adoption-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "owner_adoption_packets_ready"' in captured.out
    assert '"packet_count": 3' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert '"connector_implemented": false' in captured.out
    assert (
        tmp_path
        / "budget-lifecycle-owner-adoption-cli"
        / "budget_lifecycle_owner_adoption_report.json"
    ).is_file()
