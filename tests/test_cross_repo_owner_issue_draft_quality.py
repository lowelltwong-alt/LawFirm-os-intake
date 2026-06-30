import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.cross_repo_owner_issue_draft_quality import (
    build_owner_issue_draft_quality_report,
    run_owner_issue_draft_quality_audit,
)
from lawfirm_os_intake.cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from lawfirm_os_intake.models import (
    CrossRepoOwnerIssueDraftQualityReport,
    CrossRepoOwnerIssueDraftReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, write_json


def _readiness_report_path(tmp_path, *, ready=True):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic owner issue draft quality fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves owner issue draft quality-audit behavior.",
        proof_artifact_refs=["promotion/cross_repo_promotion_package.json"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Owner issue creation remains manual."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_owner_issue_draft_quality_check",
        status=("passed" if ready else "failed"),
        artifact_ref="promotion/cross_repo_promotion_package.json",
        message=(
            "Synthetic owner issue draft quality proof."
            if ready
            else "Synthetic owner issue draft quality blocker."
        ),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-owner-issue-draft-quality-fixture",
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
        source_budget_fixture_update_review_report_ref=("budget_fixture_update_review_report.json"),
        source_budget_fixture_update_pr_package_report_ref=(
            "budget_fixture_update_pr_package_report.json"
        ),
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
        generated_at="2026-06-30T00:00:00Z",
    )
    return write_json(
        tmp_path / "readiness" / "intake_vertical_readiness_audit_report.json",
        report.model_dump(mode="json"),
    )


def _owner_issue_draft_report_path(tmp_path, repo_root, *, ready=True):
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
    _, issue_dir = run_cross_repo_owner_issue_drafts(
        owner_adoption_report_path=owner_dir / "cross_repo_owner_adoption_report.json",
        out_dir=tmp_path / ("owner-issue-drafts-ready" if ready else "owner-issue-drafts-blocked"),
    )
    return issue_dir / "cross_repo_owner_issue_draft_report.json"


def test_owner_issue_draft_quality_audit_accepts_complete_manual_drafts(tmp_path, repo_root):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)

    report, run_dir = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality",
    )
    persisted = CrossRepoOwnerIssueDraftQualityReport.model_validate(
        load_json(run_dir / "owner_issue_draft_quality_report.json")
    )

    assert persisted.quality_report_id == report.quality_report_id
    assert persisted.status == "owner_issue_draft_quality_ready_for_manual_review"
    assert persisted.draft_count == persisted.ready_item_count == 5
    assert persisted.blocked_item_count == 0
    assert persisted.failed_item_count == 0
    assert all(
        item.status == "ready_for_manual_owner_issue_review" for item in persisted.quality_items
    )
    assert all(item.markdown_output_exists for item in persisted.quality_items)
    assert all(item.markdown_matches_embedded_body for item in persisted.quality_items)
    assert all(not item.missing_required_sections for item in persisted.quality_items)
    assert all(not item.missing_source_evidence_labels for item in persisted.quality_items)
    assert all(not item.missing_boundary_phrases for item in persisted.quality_items)
    assert all(check.status == "passed" for check in persisted.checks)
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

    notes = (run_dir / "owner_issue_draft_quality_report.md").read_text(encoding="utf-8")
    assert "Owner Issue Draft Quality Report" in notes
    assert "does not create issues" in notes


def test_owner_issue_draft_quality_audit_fails_closed_on_missing_boundary(
    tmp_path,
    repo_root,
):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)
    data = load_json(issue_draft_report_path)
    data["drafts"][0]["issue_body_markdown"] = data["drafts"][0]["issue_body_markdown"].replace(
        "- Intake did not create this issue.\n",
        "",
    )
    tampered_path = write_json(tmp_path / "tampered_issue_draft_report.json", data)

    report = build_owner_issue_draft_quality_report(
        issue_draft_report=CrossRepoOwnerIssueDraftReport.model_validate(load_json(tampered_path)),
        issue_draft_report_ref=str(tampered_path),
    )

    assert report.status == "blocked_by_owner_issue_draft_quality"
    assert report.failed_item_count == 1
    failed_item = next(
        item for item in report.quality_items if item.status == "failed_quality_gate"
    )
    assert "Intake did not create this issue." in failed_item.missing_boundary_phrases
    assert any(
        check.check_id == "issue_draft_boundary_text_complete" and check.status == "failed"
        for check in report.checks
    )
    assert report.github_issue_created is False
    assert report.github_write_performed is False
    assert report.silent_learning_performed is False


def test_owner_issue_draft_quality_audit_fails_closed_on_markdown_mismatch(
    tmp_path,
    repo_root,
):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)
    data = load_json(issue_draft_report_path)
    markdown_path = Path(data["draft_output_refs"][0])
    markdown_path.write_text("tampered markdown output\n", encoding="utf-8")

    report, _ = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality-mismatch",
    )

    assert report.status == "blocked_by_owner_issue_draft_quality"
    assert report.failed_item_count == 1
    failed_item = next(
        item for item in report.quality_items if item.status == "failed_quality_gate"
    )
    assert failed_item.markdown_output_exists is True
    assert failed_item.markdown_matches_embedded_body is False
    assert any(
        check.check_id == "issue_draft_markdown_outputs_exist_and_match"
        and check.status == "failed"
        for check in report.checks
    )


def test_owner_issue_draft_quality_audit_resolves_refs_relative_to_source_report(
    tmp_path,
    repo_root,
    monkeypatch,
):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)
    data = load_json(issue_draft_report_path)
    data["draft_output_refs"] = [
        str(Path(ref).relative_to(issue_draft_report_path.parent))
        for ref in data["draft_output_refs"]
    ]
    write_json(issue_draft_report_path, data)
    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    report, _ = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality-relative",
    )

    assert report.status == "owner_issue_draft_quality_ready_for_manual_review"
    assert all(item.markdown_output_exists for item in report.quality_items)
    assert all(item.markdown_matches_embedded_body for item in report.quality_items)


def test_owner_issue_draft_quality_audit_blocks_blocked_source_drafts(tmp_path, repo_root):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=False)

    report, _ = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality-blocked",
    )

    assert report.status == "blocked_by_owner_issue_draft_quality"
    assert report.ready_item_count == 0
    assert report.blocked_item_count == 5
    assert report.failed_item_count == 0
    assert all(item.status == "blocked_by_source_issue_draft" for item in report.quality_items)
    assert any(
        check.check_id == "source_issue_draft_report_ready_without_writes"
        and check.status == "failed"
        for check in report.checks
    )
    assert report.github_issue_created is False
    assert report.sibling_repo_write_performed is False
    assert report.external_writes_performed is False


def test_owner_issue_draft_quality_cli_writes_report(tmp_path, repo_root, capsys):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)

    exit_code = main(
        [
            "audit-owner-issue-draft-quality",
            "--issue-draft-report",
            str(issue_draft_report_path),
            "--out-dir",
            str(tmp_path / "owner-issue-draft-quality-cli"),
        ]
    )
    captured = capsys.readouterr()
    stdout = json.loads(captured.out)

    assert exit_code == 0
    assert stdout["status"] == "owner_issue_draft_quality_ready_for_manual_review"
    assert stdout["draft_count"] == 5
    assert stdout["ready_item_count"] == 5
    assert stdout["github_issue_created"] is False
    assert stdout["github_write_performed"] is False
    assert stdout["silent_learning_performed"] is False
    assert (
        tmp_path / "owner-issue-draft-quality-cli" / "owner_issue_draft_quality_report.json"
    ).is_file()


def test_owner_issue_draft_quality_model_rejects_invalid_source_status(
    tmp_path,
    repo_root,
):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)
    report, _ = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality-model-status",
    )
    data = report.model_dump(mode="json")
    data["quality_items"][0]["source_issue_draft_status"] = "invented_source_status"

    with pytest.raises(ValidationError):
        CrossRepoOwnerIssueDraftQualityReport.model_validate(data)


def test_owner_issue_draft_quality_model_rejects_target_repo_drift(
    tmp_path,
    repo_root,
):
    issue_draft_report_path = _owner_issue_draft_report_path(tmp_path, repo_root, ready=True)
    report, _ = run_owner_issue_draft_quality_audit(
        issue_draft_report_path=issue_draft_report_path,
        out_dir=tmp_path / "owner-issue-draft-quality-model-targets",
    )
    data = report.model_dump(mode="json")
    data["target_repos"] = data["target_repos"][1:]

    with pytest.raises(ValidationError):
        CrossRepoOwnerIssueDraftQualityReport.model_validate(data)
