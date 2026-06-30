from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from lawfirm_os_intake.intake_local_closeout import run_intake_local_closeout
from lawfirm_os_intake.models import (
    IntakeLocalCloseoutReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
    PRReadinessDecisionRecord,
    PRReadinessDecisionReport,
    PRReviewChecklistReport,
)
from lawfirm_os_intake.pr_readiness_decision import (
    build_pr_readiness_decision_report,
    run_pr_readiness_decision_record,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _readiness_report_path(tmp_path):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic PR readiness decision fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves PR readiness decision behavior.",
        proof_artifact_refs=["src/lawfirm_os_intake/pr_readiness_decision.py"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Manual PR decision remains required."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_pr_readiness_decision_check",
        status="passed",
        artifact_ref="src/lawfirm_os_intake/pr_readiness_decision.py",
        message="Synthetic PR readiness decision proof.",
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-pr-decision-fixture",
        status="ready_for_pr_review_external_adoption_required",
        review_readiness="ready_for_human_pr_review_not_auto_marked",
        source_owner_handoff_report_ref="learning_owner_handoff_report.json",
        source_budget_event_lake_bundle_report_ref=(
            "budget_event_lake_admission_bundle_report.json"
        ),
        source_budget_calibration_readiness_report_ref="budget_calibration_readiness_report.json",
        source_budget_fixture_update_review_report_ref="budget_fixture_update_review_report.json",
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
        generated_at="2026-06-27T00:00:00Z",
    )
    return write_json(
        tmp_path / "readiness" / "intake_vertical_readiness_audit_report.json",
        report.model_dump(mode="json"),
    )


def _source_paths(tmp_path, repo_root):
    readiness_path = _readiness_report_path(tmp_path)
    _, checklist_dir = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path / "pr-review-checklist",
    )
    checklist_path = checklist_dir / "pr_review_checklist.json"
    _, owner_dir = run_cross_repo_owner_adoption(
        promotion_package_path=repo_root / "promotion/cross_repo_promotion_package.json",
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        out_dir=tmp_path / "owner-adoption",
    )
    owner_adoption_path = owner_dir / "cross_repo_owner_adoption_report.json"
    _, issue_dir = run_cross_repo_owner_issue_drafts(
        owner_adoption_report_path=owner_adoption_path,
        out_dir=tmp_path / "owner-issue-drafts",
    )
    _, closeout_dir = run_intake_local_closeout(
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        owner_adoption_report_path=owner_adoption_path,
        owner_issue_draft_report_path=issue_dir / "cross_repo_owner_issue_draft_report.json",
        out_dir=tmp_path / "local-closeout",
        observed_pr_number=7,
        observed_pr_url="https://github.com/lowelltwong-alt/LawFirm-os-intake/pull/7",
        observed_pr_state="draft",
    )
    return {
        "checklist": checklist_path,
        "closeout": closeout_dir / "intake_local_closeout_report.json",
    }


def _decision_record(checklist, closeout, *, decision="mark_ready_for_review", accepted_ids=None):
    accepted = decision == "mark_ready_for_review"
    item_ids = [item["item_id"] for item in checklist["items"]]
    return PRReadinessDecisionRecord(
        pr_readiness_decision_id=f"pr-readiness-decision-{decision}",
        checklist_report_id=checklist["checklist_report_id"],
        closeout_report_id=closeout["closeout_report_id"],
        observed_pr_number=closeout["observed_pr_number"],
        observed_pr_url=closeout["observed_pr_url"],
        observed_pr_state=closeout["observed_pr_state"],
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-27T00:00:00Z",
        decision=decision,
        decision_reason="Synthetic PR readiness decision.",
        accepted_checklist_item_ids=accepted_ids
        if accepted_ids is not None
        else (item_ids if accepted else []),
        validation_evidence_refs=(
            [
                "python scripts/run_full_pytest.py",
                "python scripts/validate_repo.py",
                "bash scripts/smoke_demo.sh",
            ]
            if accepted
            else []
        ),
        required_followups=[] if accepted else ["Keep PR draft until followups are resolved."],
        red_team_notes=[
            "Decision record is not a GitHub state change.",
            "Owner adoption and issue creation remain manual actions.",
        ],
    )


def test_pr_readiness_decision_records_manual_ready_action(tmp_path, repo_root):
    paths = _source_paths(tmp_path, repo_root)
    checklist = load_json(paths["checklist"])
    closeout = load_json(paths["closeout"])
    decision_path = write_json(
        tmp_path / "pr-readiness-decision.json",
        _decision_record(checklist, closeout).model_dump(mode="json"),
    )

    report, run_dir = run_pr_readiness_decision_record(
        pr_review_checklist_path=paths["checklist"],
        intake_local_closeout_report_path=paths["closeout"],
        decision_path=decision_path,
        out_dir=tmp_path / "pr-readiness-decision",
    )
    persisted = PRReadinessDecisionReport.model_validate(
        load_json(run_dir / "pr_readiness_decision_report.json")
    )
    history = load_jsonl(run_dir / "pr_readiness_decision_history.jsonl")

    assert persisted.pr_readiness_decision_report_id == report.pr_readiness_decision_report_id
    assert persisted.status == "pr_readiness_decision_recorded_manual_ready_action_required"
    assert persisted.decision == "mark_ready_for_review"
    assert persisted.manual_ready_action_required is True
    assert persisted.observed_pr_number == 7
    assert len(history) == 1
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.pr_marked_ready is False
    assert persisted.github_write_performed is False
    assert persisted.github_issue_created is False
    assert persisted.github_pr_created is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "pr_readiness_decision_report.md").read_text(encoding="utf-8")
    assert "does not mark a PR ready" in notes


def test_pr_readiness_decision_records_keep_draft(tmp_path, repo_root):
    paths = _source_paths(tmp_path, repo_root)
    checklist = load_json(paths["checklist"])
    closeout = load_json(paths["closeout"])
    record = _decision_record(checklist, closeout, decision="keep_draft")

    report = build_pr_readiness_decision_report(
        checklist=PRReviewChecklistReport.model_validate(load_json(paths["checklist"])),
        checklist_ref=str(paths["checklist"]),
        closeout=IntakeLocalCloseoutReport.model_validate(load_json(paths["closeout"])),
        closeout_ref=str(paths["closeout"]),
        decision_record=record,
        history_ref="pr_readiness_decision_history.jsonl",
    )

    assert report.status == "pr_readiness_decision_recorded_keep_draft"
    assert report.manual_ready_action_required is False
    assert report.required_followups == ["Keep PR draft until followups are resolved."]
    assert all(check.status == "passed" for check in report.checks)
    assert report.github_write_performed is False


def test_pr_readiness_decision_blocks_when_ready_decision_missing_items(
    tmp_path,
    repo_root,
):
    paths = _source_paths(tmp_path, repo_root)
    checklist = load_json(paths["checklist"])
    closeout = load_json(paths["closeout"])
    record = _decision_record(
        checklist,
        closeout,
        decision="mark_ready_for_review",
        accepted_ids=[checklist["items"][0]["item_id"]],
    )

    report = build_pr_readiness_decision_report(
        checklist=PRReviewChecklistReport.model_validate(load_json(paths["checklist"])),
        checklist_ref=str(paths["checklist"]),
        closeout=IntakeLocalCloseoutReport.model_validate(load_json(paths["closeout"])),
        closeout_ref=str(paths["closeout"]),
        decision_record=record,
        history_ref="pr_readiness_decision_history.jsonl",
    )

    assert report.status == "blocked_by_pr_readiness_decision_evidence"
    assert report.manual_ready_action_required is False
    assert any(
        check.check_id == "ready_decision_accepts_all_checklist_items" and check.status == "failed"
        for check in report.checks
    )
    assert report.pr_marked_ready is False
    assert report.github_write_performed is False


def test_pr_readiness_decision_cli_writes_report(tmp_path, repo_root, capsys):
    paths = _source_paths(tmp_path, repo_root)
    checklist = load_json(paths["checklist"])
    closeout = load_json(paths["closeout"])
    decision_path = write_json(
        tmp_path / "pr-readiness-decision.json",
        _decision_record(checklist, closeout).model_dump(mode="json"),
    )

    exit_code = main(
        [
            "record-pr-readiness-decision",
            "--pr-review-checklist",
            str(paths["checklist"]),
            "--intake-local-closeout-report",
            str(paths["closeout"]),
            "--decision",
            str(decision_path),
            "--out-dir",
            str(tmp_path / "pr-readiness-decision-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "pr_readiness_decision_recorded_manual_ready_action_required"' in captured.out
    assert '"manual_ready_action_required": true' in captured.out
    assert '"pr_marked_ready": false' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (tmp_path / "pr-readiness-decision-cli" / "pr_readiness_decision_report.json").is_file()
