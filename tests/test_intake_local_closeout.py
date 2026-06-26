from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from lawfirm_os_intake.intake_local_closeout import run_intake_local_closeout
from lawfirm_os_intake.models import (
    IntakeLocalCloseoutReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, write_json


def _readiness_report_path(tmp_path, *, ready=True):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic local closeout fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves local closeout behavior.",
        proof_artifact_refs=["promotion/cross_repo_promotion_package.json"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Manual external actions remain required."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_local_closeout_check",
        status=("passed" if ready else "failed"),
        artifact_ref="promotion/cross_repo_promotion_package.json",
        message=("Synthetic local closeout proof." if ready else "Synthetic closeout blocker."),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-local-closeout-fixture",
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


def _closeout_source_paths(tmp_path, repo_root, *, ready=True):
    readiness_path = _readiness_report_path(tmp_path, ready=ready)
    _, checklist_dir = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path / ("pr-review-ready" if ready else "pr-review-blocked"),
    )
    checklist_path = checklist_dir / "pr_review_checklist.json"
    _, owner_dir = run_cross_repo_owner_adoption(
        promotion_package_path=repo_root / "promotion/cross_repo_promotion_package.json",
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        out_dir=tmp_path / ("owner-adoption-ready" if ready else "owner-adoption-blocked"),
    )
    owner_adoption_path = owner_dir / "cross_repo_owner_adoption_report.json"
    _, issue_dir = run_cross_repo_owner_issue_drafts(
        owner_adoption_report_path=owner_adoption_path,
        out_dir=tmp_path / ("owner-issue-ready" if ready else "owner-issue-blocked"),
    )
    return {
        "readiness": readiness_path,
        "checklist": checklist_path,
        "owner_adoption": owner_adoption_path,
        "owner_issue": issue_dir / "cross_repo_owner_issue_draft_report.json",
    }


def test_intake_local_closeout_ready_with_manual_actions_remaining(tmp_path, repo_root):
    paths = _closeout_source_paths(tmp_path, repo_root, ready=True)

    report, run_dir = run_intake_local_closeout(
        readiness_audit_report_path=paths["readiness"],
        pr_review_checklist_path=paths["checklist"],
        owner_adoption_report_path=paths["owner_adoption"],
        owner_issue_draft_report_path=paths["owner_issue"],
        out_dir=tmp_path / "local-closeout",
        observed_pr_number=7,
        observed_pr_url="https://github.com/lowelltwong-alt/LawFirm-os-intake/pull/7",
        observed_pr_state="draft",
    )
    persisted = IntakeLocalCloseoutReport.model_validate(
        load_json(run_dir / "intake_local_closeout_report.json")
    )

    assert persisted.closeout_report_id == report.closeout_report_id
    assert persisted.status == "intake_local_closeout_ready_manual_actions_required"
    assert persisted.observed_pr_number == 7
    assert persisted.observed_pr_state == "draft"
    assert persisted.check_count == persisted.passed_check_count == 7
    assert persisted.blocking_check_count == 0
    assert persisted.manual_actions_remaining
    assert persisted.manual_pr_state_change_required is True
    assert persisted.manual_owner_issue_creation_required is True
    assert persisted.pr_state_change_performed is False
    assert persisted.github_issue_created is False
    assert persisted.github_write_performed is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "intake_local_closeout_report.md").read_text(encoding="utf-8")
    assert "Manual Actions Remaining" in notes_text
    assert "PR remains draft" in notes_text
    assert "does not mark a PR ready" in notes_text


def test_intake_local_closeout_blocks_when_evidence_is_blocked(tmp_path, repo_root):
    paths = _closeout_source_paths(tmp_path, repo_root, ready=False)

    report, _ = run_intake_local_closeout(
        readiness_audit_report_path=paths["readiness"],
        pr_review_checklist_path=paths["checklist"],
        owner_adoption_report_path=paths["owner_adoption"],
        owner_issue_draft_report_path=paths["owner_issue"],
        out_dir=tmp_path / "local-closeout-blocked",
        observed_pr_state="draft",
    )

    assert report.status == "blocked_by_closeout_evidence"
    assert report.blocking_check_count > 0
    assert any(check.check_id == "readiness_audit_ready" for check in report.checks)
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False


def test_intake_local_closeout_cli(tmp_path, repo_root, capsys):
    paths = _closeout_source_paths(tmp_path, repo_root, ready=True)

    exit_code = main(
        [
            "audit-intake-local-closeout",
            "--readiness-audit-report",
            str(paths["readiness"]),
            "--pr-review-checklist",
            str(paths["checklist"]),
            "--owner-adoption-report",
            str(paths["owner_adoption"]),
            "--owner-issue-draft-report",
            str(paths["owner_issue"]),
            "--observed-pr-number",
            "7",
            "--observed-pr-state",
            "draft",
            "--out-dir",
            str(tmp_path / "local-closeout-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "intake_local_closeout_ready_manual_actions_required"' in captured.out
    assert '"observed_pr_number": 7' in captured.out
    assert '"manual_pr_state_change_required": true' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert (tmp_path / "local-closeout-cli" / "intake_local_closeout_report.json").is_file()
