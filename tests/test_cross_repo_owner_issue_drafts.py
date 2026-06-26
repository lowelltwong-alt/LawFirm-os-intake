from pathlib import Path

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from lawfirm_os_intake.models import (
    CrossRepoOwnerIssueDraftReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, write_json


REQUIRED_TARGET_REPOS = {
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
}


def _readiness_report_path(tmp_path, *, ready=True):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic owner issue draft fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves owner issue draft behavior.",
        proof_artifact_refs=["promotion/cross_repo_promotion_package.json"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Owner issue creation remains manual."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_owner_issue_draft_check",
        status=("passed" if ready else "failed"),
        artifact_ref="promotion/cross_repo_promotion_package.json",
        message=(
            "Synthetic owner issue draft proof."
            if ready
            else "Synthetic owner issue draft blocker."
        ),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-owner-issue-draft-fixture",
        status=(
            "ready_for_pr_review_external_adoption_required"
            if ready
            else "blocked_missing_or_failed_learning_artifacts"
        ),
        review_readiness=(
            "ready_for_human_pr_review_not_auto_marked"
            if ready
            else "not_ready_learning_artifact_chain_blocked"
        ),
        source_owner_handoff_report_ref="learning_owner_handoff_report.json",
        source_budget_event_lake_bundle_report_ref=(
            "budget_event_lake_admission_bundle_report.json"
        ),
        source_budget_calibration_readiness_report_ref=("budget_calibration_readiness_report.json"),
        total_slice_count=1,
        implemented_slice_count=1,
        slices=[slice_status],
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


def _owner_adoption_report_path(tmp_path, repo_root, *, ready=True):
    readiness_path = _readiness_report_path(tmp_path, ready=ready)
    _, checklist_dir = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path / ("pr-review-ready" if ready else "pr-review-blocked"),
    )
    _, owner_dir = run_cross_repo_owner_adoption(
        promotion_package_path=repo_root / "promotion/cross_repo_promotion_package.json",
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_dir / "pr_review_checklist.json",
        out_dir=tmp_path / ("owner-adoption-ready" if ready else "owner-adoption-blocked"),
    )
    return owner_dir / "cross_repo_owner_adoption_report.json"


def test_cross_repo_owner_issue_drafts_are_local_manual_issue_text(tmp_path, repo_root):
    owner_adoption_report_path = _owner_adoption_report_path(tmp_path, repo_root, ready=True)

    report, run_dir = run_cross_repo_owner_issue_drafts(
        owner_adoption_report_path=owner_adoption_report_path,
        out_dir=tmp_path / "owner-issue-drafts",
    )
    persisted = CrossRepoOwnerIssueDraftReport.model_validate(
        load_json(run_dir / "cross_repo_owner_issue_draft_report.json")
    )

    assert persisted.issue_draft_report_id == report.issue_draft_report_id
    assert persisted.status == "issue_drafts_ready_for_manual_creation"
    assert persisted.draft_count == persisted.ready_draft_count == 5
    assert persisted.blocked_draft_count == 0
    assert set(persisted.target_repos) == REQUIRED_TARGET_REPOS
    assert set(draft.target_repo for draft in persisted.drafts) == REQUIRED_TARGET_REPOS
    assert all(draft.status == "ready_for_manual_issue_creation" for draft in persisted.drafts)
    assert all(draft.issue_body_markdown for draft in persisted.drafts)
    assert all(draft.manual_creation_required is True for draft in persisted.drafts)
    assert all(draft.github_issue_created is False for draft in persisted.drafts)
    assert all(draft.github_write_performed is False for draft in persisted.drafts)
    assert all(Path(ref).is_file() for ref in persisted.draft_output_refs)
    assert (run_dir / "cross_repo_owner_issue_drafts.jsonl").is_file()
    assert persisted.manual_creation_required is True
    assert persisted.github_issue_created is False
    assert persisted.github_pr_created is False
    assert persisted.github_write_performed is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    markdown_text = (run_dir / "owner_issue_drafts" / "orchestrator.issue_draft.md").read_text(
        encoding="utf-8"
    )
    assert "## Required Owner Actions" in markdown_text
    assert "Intake did not create this issue" in markdown_text
    assert "Orchestrator" in markdown_text


def test_cross_repo_owner_issue_drafts_block_when_owner_adoption_is_blocked(
    tmp_path,
    repo_root,
):
    owner_adoption_report_path = _owner_adoption_report_path(tmp_path, repo_root, ready=False)

    report, _ = run_cross_repo_owner_issue_drafts(
        owner_adoption_report_path=owner_adoption_report_path,
        out_dir=tmp_path / "owner-issue-drafts-blocked",
    )

    assert report.status == "blocked_by_owner_adoption"
    assert report.ready_draft_count == 0
    assert report.blocked_draft_count == 5
    assert all(draft.status == "blocked_by_owner_adoption_packet" for draft in report.drafts)
    assert report.github_issue_created is False
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False


def test_cross_repo_owner_issue_drafts_cli(tmp_path, repo_root, capsys):
    owner_adoption_report_path = _owner_adoption_report_path(tmp_path, repo_root, ready=True)

    exit_code = main(
        [
            "build-cross-repo-owner-issue-drafts",
            "--owner-adoption-report",
            str(owner_adoption_report_path),
            "--out-dir",
            str(tmp_path / "owner-issue-drafts-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "issue_drafts_ready_for_manual_creation"' in captured.out
    assert '"draft_count": 5' in captured.out
    assert '"github_issue_created": false' in captured.out
    assert '"manual_creation_required": true' in captured.out
    assert (
        tmp_path / "owner-issue-drafts-cli" / "cross_repo_owner_issue_draft_report.json"
    ).is_file()
