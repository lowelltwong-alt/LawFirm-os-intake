from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_lake_admission_bundle import (
    run_budget_event_lake_admission_bundle,
)
from lawfirm_os_intake.budget_lifecycle_audit import (
    build_budget_lifecycle_audit_report,
    run_budget_lifecycle_audit,
)
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    BudgetLifecycleAuditReport,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, write_json
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


def _generate_lifecycle_inputs(tmp_path, repo_root):
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
    return review_dir, actuals_dir, carrier_dir, lake_dir


def test_budget_lifecycle_audit_summarizes_all_event_streams(tmp_path, repo_root):
    review_dir, actuals_dir, carrier_dir, lake_dir = _generate_lifecycle_inputs(
        tmp_path,
        repo_root,
    )

    report, run_dir = run_budget_lifecycle_audit(
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
    persisted = BudgetLifecycleAuditReport.model_validate(
        load_json(run_dir / "budget_lifecycle_audit_report.json")
    )
    notes = (run_dir / "budget_lifecycle_audit_report.md").read_text(encoding="utf-8")

    assert persisted.lifecycle_audit_report_id == report.lifecycle_audit_report_id
    assert persisted.status == "ready_for_budget_lifecycle_review"
    assert persisted.budget_proposal_id
    assert persisted.preflight_packet_id
    assert persisted.total_lifecycle_event_count == (
        persisted.budget_change_event_count
        + persisted.actual_variance_event_count
        + persisted.carrier_rejection_event_count
    )
    assert persisted.human_budget_change_event_count > 0
    assert persisted.actual_variance_review_event_count > 0
    assert persisted.carrier_pending_decision_event_count > 0
    assert persisted.carrier_appeal_result_event_count > 0
    assert persisted.carrier_financial_outcome_event_count > 0
    assert persisted.pending_human_decision_count > 0
    assert persisted.financial_summary.human_revision_total_delta is not None
    assert persisted.financial_summary.actual_total is not None
    assert persisted.financial_summary.carrier_write_down_amount >= 0
    assert "budget_human_change_record" in persisted.candidate_record_families
    assert "carrier_financial_outcome_record" in persisted.candidate_record_families
    assert all(check.status != "failed" for check in persisted.checks)
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    assert "does not admit Exception Lake records" in notes


def test_budget_lifecycle_audit_blocks_missing_artifacts(tmp_path, repo_root):
    review_dir, actuals_dir, carrier_dir, _ = _generate_lifecycle_inputs(tmp_path, repo_root)
    missing_lake_bundle = tmp_path / "missing-lake-bundle.json"

    report = build_budget_lifecycle_audit_report(
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=(
            actuals_dir / "budget_actual_variance_ledger_report.json"
        ),
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
        budget_event_lake_bundle_report_path=missing_lake_bundle,
    )

    assert report.status == "blocked_missing_lifecycle_artifacts"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "lifecycle_artifacts_exist" in failed
    assert str(missing_lake_bundle) in next(
        check.artifact_refs
        for check in report.checks
        if check.check_id == "lifecycle_artifacts_exist"
    )
    assert report.lake_write_performed is False


def test_budget_lifecycle_audit_blocks_budget_id_drift(tmp_path, repo_root):
    review_dir, actuals_dir, carrier_dir, lake_dir = _generate_lifecycle_inputs(
        tmp_path,
        repo_root,
    )
    drifted = load_json(actuals_dir / "budget_actual_variance_ledger_report.json")
    drifted["budget_proposal_id"] = "budget-proposal-drifted"
    drifted_path = write_json(tmp_path / "drifted_actual_ledger_report.json", drifted)

    report = build_budget_lifecycle_audit_report(
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=drifted_path,
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
        budget_event_lake_bundle_report_path=(
            lake_dir / "budget_event_lake_admission_bundle_report.json"
        ),
    )

    assert report.status == "blocked_inconsistent_lifecycle_evidence"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "budget_proposal_id_consistent" in failed
    assert report.budget_proposal_id is None


def test_budget_lifecycle_audit_cli(tmp_path, repo_root, capsys):
    review_dir, actuals_dir, carrier_dir, lake_dir = _generate_lifecycle_inputs(
        tmp_path,
        repo_root,
    )

    exit_code = main(
        [
            "audit-budget-lifecycle",
            "--budget-change-ledger-report",
            str(review_dir / "budget_change_ledger_report.json"),
            "--budget-actual-variance-ledger-report",
            str(actuals_dir / "budget_actual_variance_ledger_report.json"),
            "--carrier-rejection-decision-ledger-report",
            str(carrier_dir / "carrier_rejection_decision_ledger_report.json"),
            "--budget-event-lake-bundle-report",
            str(lake_dir / "budget_event_lake_admission_bundle_report.json"),
            "--out-dir",
            str(tmp_path / "lifecycle-audit-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_budget_lifecycle_review"' in captured.out
    assert '"pending_human_decision_count":' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / "lifecycle-audit-cli" / "budget_lifecycle_audit_report.json").is_file()
