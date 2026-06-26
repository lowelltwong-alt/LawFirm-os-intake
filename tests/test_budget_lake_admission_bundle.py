from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_lake_admission_bundle import (
    build_budget_event_lake_admission_bundle,
    run_budget_event_lake_admission_bundle,
)
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    BudgetLakeAdmissionBundleReport,
    BudgetProposal,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run_budget(tmp_path, repo_root) -> tuple[BudgetProposal, object]:
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
    budget, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget, budget_dir


def _generate_ledgers(tmp_path, repo_root):
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
    return review_dir, actuals_dir, carrier_dir


def test_budget_event_lake_bundle_links_all_ledgers_without_admission(tmp_path, repo_root):
    review_dir, actuals_dir, carrier_dir = _generate_ledgers(tmp_path, repo_root)

    report, run_dir = run_budget_event_lake_admission_bundle(
        out_dir=tmp_path / "lake-bundle",
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=(
            actuals_dir / "budget_actual_variance_ledger_report.json"
        ),
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
    )
    persisted = BudgetLakeAdmissionBundleReport.model_validate(
        load_json(run_dir / "budget_event_lake_admission_bundle_report.json")
    )
    notes_text = (run_dir / "budget_event_lake_admission_bundle.md").read_text(encoding="utf-8")

    assert persisted.bundle_report_id == report.bundle_report_id
    assert persisted.status == "ready_for_exception_lake_review"
    assert persisted.artifact_count == 6
    assert persisted.ledger_report_count == 3
    assert persisted.jsonl_row_count == persisted.total_event_count
    assert len(persisted.budget_proposal_ids) == 1
    assert len(persisted.preflight_packet_ids) == 1
    assert {
        "budget_human_change_record",
        "budget_actual_variance_record",
        "carrier_rejection_decision_record",
        "carrier_appeal_result_record",
        "carrier_financial_outcome_record",
    } <= set(persisted.candidate_record_families)
    assert {
        "budget_human_change_recorded",
        "budget_actual_cost_variance_requires_review",
        "carrier_rejection_financial_outcome_recorded",
    } <= set(persisted.local_event_labels)
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(artifact.sha256.startswith("sha256:") for artifact in persisted.artifacts)
    assert persisted.no_lake_admission_performed is True
    assert persisted.sqlite_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    assert "does not admit Exception Lake records" in notes_text


def test_budget_event_lake_bundle_blocks_missing_jsonl(tmp_path, repo_root):
    review_dir, _, _ = _generate_ledgers(tmp_path, repo_root)
    missing_jsonl = tmp_path / "missing-budget-change-ledger.jsonl"

    report = build_budget_event_lake_admission_bundle(
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_change_ledger_jsonl_path=missing_jsonl,
    )

    assert report.status == "blocked_missing_artifacts"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "artifact_files_exist" in failed
    assert str(missing_jsonl) in next(
        check.artifact_refs for check in report.checks if check.check_id == "artifact_files_exist"
    )
    assert report.sqlite_write_performed is False
    assert report.lake_write_performed is False


def test_budget_event_lake_bundle_blocks_mismatched_budget_ids(tmp_path, repo_root):
    review_dir, actuals_dir, _ = _generate_ledgers(tmp_path, repo_root)
    drifted = load_json(actuals_dir / "budget_actual_variance_ledger_report.json")
    drifted["budget_proposal_id"] = "budget-proposal-drifted"
    drifted_path = write_json(tmp_path / "drifted_actual_ledger_report.json", drifted)

    report = build_budget_event_lake_admission_bundle(
        budget_change_ledger_report_path=review_dir / "budget_change_ledger_report.json",
        budget_actual_variance_ledger_report_path=drifted_path,
        budget_actual_variance_ledger_jsonl_path=(
            actuals_dir / "budget_actual_variance_ledger.jsonl"
        ),
    )

    assert report.status == "blocked_inconsistent_evidence"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "budget_proposal_id_consistent" in failed
    assert "budget-proposal-drifted" in report.budget_proposal_ids
    assert len(report.budget_proposal_ids) == 2


def test_budget_event_lake_bundle_cli(tmp_path, repo_root, capsys):
    review_dir, actuals_dir, carrier_dir = _generate_ledgers(tmp_path, repo_root)

    exit_code = main(
        [
            "build-budget-event-lake-bundle",
            "--budget-change-ledger-report",
            str(review_dir / "budget_change_ledger_report.json"),
            "--budget-actual-variance-ledger-report",
            str(actuals_dir / "budget_actual_variance_ledger_report.json"),
            "--carrier-rejection-decision-ledger-report",
            str(carrier_dir / "carrier_rejection_decision_ledger_report.json"),
            "--out-dir",
            str(tmp_path / "lake-bundle-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_exception_lake_review"' in captured.out
    assert '"artifact_count": 6' in captured.out
    assert '"sqlite_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (
        tmp_path / "lake-bundle-cli" / "budget_event_lake_admission_bundle_report.json"
    ).is_file()
