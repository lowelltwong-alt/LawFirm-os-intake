from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_human_review_packet import (
    build_budget_human_review_packet,
    run_budget_human_review_packet,
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
from lawfirm_os_intake.models import BudgetHumanReviewPacket, HumanConfirmation
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


def _generate_human_review_inputs(tmp_path, repo_root):
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
    return {
        "revision": review_dir / "budget_revision_report.json",
        "actuals": actuals_dir / "budget_actual_comparison_report.json",
        "carrier_review": carrier_review_dir / "carrier_rejection_review_packet.json",
        "carrier_learning": carrier_learning_dir / "carrier_rejection_learning_report.json",
        "lifecycle": lifecycle_dir / "budget_lifecycle_audit_report.json",
    }


def test_budget_human_review_packet_consolidates_recommendations_and_red_team(
    tmp_path,
    repo_root,
):
    paths = _generate_human_review_inputs(tmp_path, repo_root)

    packet, run_dir = run_budget_human_review_packet(
        budget_lifecycle_audit_report_path=paths["lifecycle"],
        budget_revision_report_path=paths["revision"],
        budget_actual_comparison_report_path=paths["actuals"],
        carrier_rejection_review_packet_path=paths["carrier_review"],
        carrier_rejection_learning_report_path=paths["carrier_learning"],
        out_dir=tmp_path / "budget-human-review",
    )
    persisted = BudgetHumanReviewPacket.model_validate(
        load_json(run_dir / "budget_human_review_packet.json")
    )
    notes = (run_dir / "budget_human_review_packet.md").read_text(encoding="utf-8")

    assert persisted.budget_human_review_packet_id == packet.budget_human_review_packet_id
    assert persisted.status == "ready_for_human_budget_review"
    assert persisted.pending_human_decision_count > 0
    assert persisted.recommendations
    areas = {recommendation.review_area for recommendation in persisted.recommendations}
    assert {
        "authority_boundary",
        "budget_revision",
        "actual_variance",
        "carrier_rejection",
        "lake_handoff",
        "learning_loop",
    }.issubset(areas)
    assert all(recommendation.why for recommendation in persisted.recommendations)
    assert all(template.allowed_outcomes for template in persisted.decision_templates)
    assert any(note.scope == "authority_boundary" for note in persisted.red_team_notes)
    assert any(note.scope == "learning_loop_mutation" for note in persisted.red_team_notes)
    assert "does not submit a budget or appeal" in notes
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.budget_submission_performed is False
    assert persisted.appeal_submission_performed is False
    assert persisted.silent_learning_performed is False
    assert (run_dir / "budget_human_review_decision_templates.json").is_file()


def test_budget_human_review_packet_blocks_failed_lifecycle_audit(tmp_path, repo_root):
    paths = _generate_human_review_inputs(tmp_path, repo_root)
    payload = load_json(paths["lifecycle"])
    payload["status"] = "blocked_inconsistent_lifecycle_evidence"
    payload["checks"].append(
        {
            "check_id": "synthetic_failed_lifecycle_check",
            "status": "failed",
            "message": "Synthetic failed lifecycle check.",
            "artifact_refs": ["synthetic-lifecycle.json"],
        }
    )
    blocked_lifecycle = write_json(tmp_path / "blocked_lifecycle.json", payload)

    packet = build_budget_human_review_packet(
        budget_lifecycle_audit_report_path=blocked_lifecycle,
    )

    assert packet.status == "blocked_by_lifecycle_audit"
    assert not packet.recommendations
    assert any(
        check.check_id == "budget_lifecycle_audit_ready_without_writes" and check.status == "failed"
        for check in packet.checks
    )
    assert packet.budget_submission_performed is False
    assert packet.lake_write_performed is False


def test_budget_human_review_packet_cli(tmp_path, repo_root, capsys):
    paths = _generate_human_review_inputs(tmp_path, repo_root)

    exit_code = main(
        [
            "build-budget-human-review-packet",
            "--budget-lifecycle-audit-report",
            str(paths["lifecycle"]),
            "--budget-revision-report",
            str(paths["revision"]),
            "--budget-actual-comparison-report",
            str(paths["actuals"]),
            "--carrier-rejection-review-packet",
            str(paths["carrier_review"]),
            "--carrier-rejection-learning-report",
            str(paths["carrier_learning"]),
            "--out-dir",
            str(tmp_path / "budget-human-review-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_budget_review"' in captured.out
    assert '"recommendation_count":' in captured.out
    assert '"budget_submission_performed": false' in captured.out
    assert '"appeal_submission_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (tmp_path / "budget-human-review-cli" / "budget_human_review_packet.json").is_file()
