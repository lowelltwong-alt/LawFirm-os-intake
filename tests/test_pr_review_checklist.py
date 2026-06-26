from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
    PRReviewChecklistReport,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, write_json


def _slice_status() -> IntakeVerticalReadinessSliceStatus:
    return IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic close-out fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves checklist command behavior.",
        proof_artifact_refs=["src/lawfirm_os_intake/pr_review_checklist.py"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Human review remains required."],
    )


def _readiness_report_path(tmp_path, *, ready=True):
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_readiness_check",
        status=("passed" if ready else "failed"),
        artifact_ref="synthetic-readiness-artifact.json",
        message=(
            "Synthetic readiness proof."
            if ready
            else "Synthetic readiness blocker for checklist tests."
        ),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-checklist-fixture",
        status=(
            "ready_for_pr_review_external_adoption_required"
            if ready
            else "blocked_missing_or_failed_lake_bundle"
        ),
        review_readiness=(
            "ready_for_human_pr_review_not_auto_marked"
            if ready
            else "not_ready_lake_bundle_blocked"
        ),
        source_owner_handoff_report_ref="learning_owner_handoff_report.json",
        source_budget_event_lake_bundle_report_ref=(
            "budget_event_lake_admission_bundle_report.json"
        ),
        source_budget_calibration_readiness_report_ref=("budget_calibration_readiness_report.json"),
        source_budget_fixture_update_review_report_ref=("budget_fixture_update_review_report.json"),
        source_budget_fixture_update_pr_package_report_ref=(
            "budget_fixture_update_pr_package_report.json"
        ),
        total_slice_count=1,
        implemented_slice_count=1,
        slices=[_slice_status()],
        artifact_checks=[artifact_check],
        required_external_adoption_actions=[
            "Semantic Substrate owner review for promoted contracts.",
            "Orchestrator owner review for runtime workflow.",
            "Exception Lake owner review for append-only storage.",
        ],
        external_adoption_target_repos=[
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ],
        generated_at="2026-06-26T00:00:00Z",
    )
    return write_json(
        tmp_path / "readiness" / "intake_vertical_readiness_audit_report.json",
        report.model_dump(mode="json"),
    )


def test_pr_review_checklist_marks_ready_for_human_review_only(tmp_path):
    readiness_path = _readiness_report_path(tmp_path, ready=True)

    report, run_dir = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path / "pr-review-checklist",
    )
    persisted = PRReviewChecklistReport.model_validate(
        load_json(run_dir / "pr_review_checklist.json")
    )

    assert persisted.checklist_report_id == report.checklist_report_id
    assert persisted.status == "ready_for_human_pr_review"
    assert persisted.recommendation == "eligible_for_human_to_mark_ready_after_review"
    assert persisted.blocking_item_count == 0
    assert persisted.item_count == len(persisted.items)
    assert persisted.source_readiness_audit_report_ref == str(readiness_path)
    assert persisted.pr_marked_ready is False
    assert persisted.github_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.no_lake_admission_performed is True
    assert persisted.no_sibling_repo_writes is True
    assert persisted.no_canonical_mutation is True
    assert persisted.sqlite_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    assert {
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
    }.issubset(set(persisted.external_adoption_target_repos))
    assert any(item.red_team_note for item in persisted.items)

    notes_text = (run_dir / "pr_review_checklist.md").read_text(encoding="utf-8")
    assert "Do not mark the PR ready automatically" in notes_text
    assert "Red-team note" in notes_text
    assert "GitHub write performed: False" in notes_text


def test_pr_review_checklist_blocks_when_readiness_audit_is_blocked(tmp_path):
    readiness_path = _readiness_report_path(tmp_path, ready=False)

    report, _ = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path / "pr-review-checklist-blocked",
    )

    assert report.status == "blocked_by_readiness_audit"
    assert report.recommendation == "keep_draft_until_human_review_complete"
    assert report.blocking_item_count == 1
    assert any(
        item.item_id == "pr-review-readiness-audit-blocker"
        and item.status == "blocked_by_readiness_audit"
        for item in report.items
    )
    assert "Resolve readiness audit blockers" in report.required_human_decisions[-1]
    assert report.pr_marked_ready is False
    assert report.github_write_performed is False


def test_pr_review_checklist_cli(tmp_path, capsys):
    readiness_path = _readiness_report_path(tmp_path, ready=True)

    exit_code = main(
        [
            "build-pr-review-checklist",
            "--readiness-audit-report",
            str(readiness_path),
            "--out-dir",
            str(tmp_path / "pr-review-checklist-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_pr_review"' in captured.out
    assert '"recommendation": "eligible_for_human_to_mark_ready_after_review"' in captured.out
    assert '"pr_marked_ready": false' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert (tmp_path / "pr-review-checklist-cli" / "pr_review_checklist.json").is_file()
