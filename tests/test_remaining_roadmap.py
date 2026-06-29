from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from lawfirm_os_intake.intake_local_closeout import run_intake_local_closeout
from lawfirm_os_intake.models import (
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
    PRReadinessDecisionRecord,
    RemainingRoadmapReport,
)
from lawfirm_os_intake.pr_readiness_decision import run_pr_readiness_decision_record
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.remaining_roadmap import run_remaining_roadmap_plan
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _readiness_report_path(tmp_path, *, ready=True):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic remaining-roadmap fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves remaining-roadmap planning behavior.",
        proof_artifact_refs=["src/lawfirm_os_intake/remaining_roadmap.py"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Manual owner adoption remains required."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_remaining_roadmap_check",
        status=("passed" if ready else "failed"),
        artifact_ref="src/lawfirm_os_intake/remaining_roadmap.py",
        message=(
            "Synthetic remaining-roadmap proof."
            if ready
            else "Synthetic remaining-roadmap blocker."
        ),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-remaining-roadmap-fixture",
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
        generated_at="2026-06-29T00:00:00Z",
    )
    return write_json(
        tmp_path / "readiness" / "intake_vertical_readiness_audit_report.json",
        report.model_dump(mode="json"),
    )


def _decision_record(checklist, closeout):
    return PRReadinessDecisionRecord(
        pr_readiness_decision_id="pr-readiness-decision-remaining-roadmap-fixture",
        checklist_report_id=checklist["checklist_report_id"],
        closeout_report_id=closeout["closeout_report_id"],
        observed_pr_number=closeout["observed_pr_number"],
        observed_pr_url=closeout["observed_pr_url"],
        observed_pr_state=closeout["observed_pr_state"],
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-29T00:00:00Z",
        decision="keep_draft",
        decision_reason="Synthetic reviewer keeps the PR draft while owner work is planned.",
        accepted_checklist_item_ids=[],
        validation_evidence_refs=[],
        required_followups=["Use remaining-roadmap report for owner-gated followups."],
        red_team_notes=[
            "Remaining roadmap is not a GitHub state change.",
            "Critical items still require owner repo review or governance approval.",
        ],
    )


def _source_paths(tmp_path, repo_root, *, ready=True, with_decision=True):
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
    _, closeout_dir = run_intake_local_closeout(
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        owner_adoption_report_path=owner_adoption_path,
        owner_issue_draft_report_path=issue_dir / "cross_repo_owner_issue_draft_report.json",
        out_dir=tmp_path / ("local-closeout-ready" if ready else "local-closeout-blocked"),
        observed_pr_number=7,
        observed_pr_url="https://github.com/lowelltwong-alt/LawFirm-os-intake/pull/7",
        observed_pr_state="draft",
    )
    closeout_path = closeout_dir / "intake_local_closeout_report.json"
    paths = {
        "readiness": readiness_path,
        "checklist": checklist_path,
        "closeout": closeout_path,
    }
    if with_decision:
        decision_path = write_json(
            tmp_path / "pr-readiness-decision.json",
            _decision_record(load_json(checklist_path), load_json(closeout_path)).model_dump(
                mode="json"
            ),
        )
        _, pr_decision_dir = run_pr_readiness_decision_record(
            pr_review_checklist_path=checklist_path,
            intake_local_closeout_report_path=closeout_path,
            decision_path=decision_path,
            out_dir=tmp_path / "pr-readiness-decision",
        )
        paths["pr_decision"] = pr_decision_dir / "pr_readiness_decision_report.json"
    return paths


def test_remaining_roadmap_report_names_easy_and_critical_work(tmp_path, repo_root):
    paths = _source_paths(tmp_path, repo_root, ready=True, with_decision=True)

    report, run_dir = run_remaining_roadmap_plan(
        readiness_audit_report_path=paths["readiness"],
        intake_local_closeout_report_path=paths["closeout"],
        pr_readiness_decision_report_path=paths["pr_decision"],
        out_dir=tmp_path / "remaining-roadmap",
    )
    persisted = RemainingRoadmapReport.model_validate(
        load_json(run_dir / "remaining_roadmap_report.json")
    )
    items = load_jsonl(run_dir / "remaining_roadmap_items.jsonl")

    assert persisted.remaining_roadmap_report_id == report.remaining_roadmap_report_id
    assert persisted.status == "remaining_roadmap_ready_manual_execution_required"
    assert persisted.source_pr_readiness_decision == "keep_draft"
    assert persisted.item_count == 10
    assert persisted.easy_item_count == 2
    assert persisted.medium_item_count == 4
    assert persisted.large_item_count == 4
    assert persisted.critical_item_count == 4
    assert persisted.owner_gated_item_count == 7
    assert persisted.local_or_human_item_count == 3
    assert persisted.next_recommended_item_ids == [
        "human-pr-review-and-state-decision",
        "manual-owner-issue-creation",
        "owner-triage-and-pr-splitting",
    ]
    assert len(items) == 10
    assert all(item["red_team_notes"] for item in items)
    assert all(check.status in {"passed", "warning"} for check in persisted.checks)
    assert any(
        check.check_id == "remaining_plan_sources_have_no_side_effects" and check.status == "passed"
        for check in persisted.checks
    )
    assert persisted.github_write_performed is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "remaining_roadmap_report.md").read_text(encoding="utf-8")
    assert "Critical-risk items: 4" in notes
    assert "This roadmap is local planning evidence only" in notes


def test_remaining_roadmap_fails_closed_when_source_evidence_is_blocked(
    tmp_path,
    repo_root,
):
    paths = _source_paths(tmp_path, repo_root, ready=False, with_decision=False)

    report, _ = run_remaining_roadmap_plan(
        readiness_audit_report_path=paths["readiness"],
        intake_local_closeout_report_path=paths["closeout"],
        out_dir=tmp_path / "remaining-roadmap-blocked",
    )

    assert report.status == "blocked_by_source_evidence"
    assert any(
        check.check_id == "readiness_audit_ready_for_remaining_plan" and check.status == "failed"
        for check in report.checks
    )
    assert any(
        check.check_id == "local_closeout_ready_for_remaining_plan" and check.status == "failed"
        for check in report.checks
    )
    assert any(
        check.check_id == "pr_readiness_decision_not_supplied" and check.status == "warning"
        for check in report.checks
    )
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False
    assert report.external_writes_performed is False


def test_remaining_roadmap_cli_writes_report(tmp_path, repo_root, capsys):
    paths = _source_paths(tmp_path, repo_root, ready=True, with_decision=True)

    exit_code = main(
        [
            "plan-remaining-roadmap",
            "--readiness-audit-report",
            str(paths["readiness"]),
            "--intake-local-closeout-report",
            str(paths["closeout"]),
            "--pr-readiness-decision-report",
            str(paths["pr_decision"]),
            "--out-dir",
            str(tmp_path / "remaining-roadmap-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "remaining_roadmap_ready_manual_execution_required"' in captured.out
    assert '"item_count": 10' in captured.out
    assert '"critical_item_count": 4' in captured.out
    assert '"owner_gated_item_count": 7' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert (tmp_path / "remaining-roadmap-cli" / "remaining_roadmap_report.json").is_file()
