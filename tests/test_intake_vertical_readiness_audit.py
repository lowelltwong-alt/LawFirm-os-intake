from lawfirm_os_intake.cli import main
from lawfirm_os_intake.intake_vertical_readiness_audit import (
    run_intake_vertical_readiness_audit,
)
from lawfirm_os_intake.learning_owner_handoffs import run_learning_owner_handoffs
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.learning_shadow_eval_results import run_learning_shadow_eval_results
from lawfirm_os_intake.models import IntakeVerticalReadinessAuditReport
from lawfirm_os_intake.util import load_json


def _change_set_path(tmp_path, repo_root):
    _, run_dir = run_learning_proposed_changes(
        shadow_eval_plan_path=repo_root
        / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
        promotion_readiness_report_path=repo_root
        / "examples/synthetic/learning/proposed-change-readiness-report.json",
        out_dir=tmp_path / "learning-proposed-changes",
    )
    return run_dir / "learning_proposed_change_set.json"


def _owner_handoff_report_path(tmp_path, repo_root, *, include_fixture_results=True):
    change_set_path = _change_set_path(tmp_path, repo_root)
    fixture_result_paths = []
    if include_fixture_results:
        fixture_result_paths = [
            repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json",
            repo_root / "examples/synthetic/learning/shadow-eval-result-capture-completeness.json",
        ]
    _, shadow_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=fixture_result_paths,
        out_dir=tmp_path / "learning-shadow-eval",
    )
    _, handoff_dir = run_learning_owner_handoffs(
        shadow_eval_result_report_path=shadow_dir / "learning_shadow_eval_result_report.json",
        out_dir=tmp_path / "learning-owner-handoffs",
    )
    return handoff_dir / "learning_owner_handoff_report.json"


def test_intake_vertical_readiness_audit_marks_pr_review_ready_but_not_promoted(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)

    report, run_dir = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness",
    )
    persisted = IntakeVerticalReadinessAuditReport.model_validate(
        load_json(run_dir / "intake_vertical_readiness_audit_report.json")
    )

    assert persisted.audit_report_id == report.audit_report_id
    assert persisted.status == "ready_for_pr_review_external_adoption_required"
    assert persisted.review_readiness == "ready_for_human_pr_review_not_auto_marked"
    assert persisted.implemented_slice_count == persisted.total_slice_count == 9
    assert persisted.missing_artifact_refs == []
    assert persisted.missing_command_refs == []
    assert all(
        slice_status.status == "implemented_local_candidate" for slice_status in report.slices
    )
    assert all(check.status == "passed" for check in persisted.artifact_checks)
    assert {
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
    }.issubset(set(persisted.external_adoption_target_repos))
    assert persisted.pr_marked_ready is False
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.no_connector_implemented is True
    assert persisted.no_lake_admission_performed is True
    assert persisted.no_sibling_repo_writes is True
    assert persisted.no_canonical_mutation is True
    assert persisted.sqlite_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "intake_vertical_readiness_audit_report.md").read_text(encoding="utf-8")
    assert "External Adoption Still Required" in notes_text
    assert "does not mark a PR ready" in notes_text


def test_intake_vertical_readiness_audit_fails_closed_for_missing_local_surfaces(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        repo_root=tmp_path / "empty-repo-root",
        out_dir=tmp_path / "intake-vertical-readiness-missing",
    )

    assert report.status == "incomplete_missing_local_artifacts"
    assert report.review_readiness == "not_ready_missing_local_artifacts"
    assert report.implemented_slice_count == 0
    assert report.missing_artifact_refs
    assert report.pr_marked_ready is False
    assert report.promotion_authorized is False


def test_intake_vertical_readiness_audit_blocks_failed_or_missing_learning_chain(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(
        tmp_path,
        repo_root,
        include_fixture_results=False,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-blocked",
    )

    assert report.status == "blocked_missing_or_failed_learning_artifacts"
    assert report.review_readiness == "not_ready_learning_artifact_chain_blocked"
    assert report.implemented_slice_count == report.total_slice_count == 9
    assert any(
        check.check_id == "owner_handoff_ready_without_writes" and check.status == "failed"
        for check in report.artifact_checks
    )
    assert any(
        check.check_id == "shadow_eval_results_passed_without_writes" and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.external_writes_performed is False


def test_intake_vertical_readiness_audit_cli(tmp_path, repo_root, capsys):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)

    exit_code = main(
        [
            "audit-intake-vertical-readiness",
            "--owner-handoff-report",
            str(owner_handoff_report_path),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "intake-vertical-readiness-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_pr_review_external_adoption_required"' in captured.out
    assert '"review_readiness": "ready_for_human_pr_review_not_auto_marked"' in captured.out
    assert '"pr_marked_ready": false' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert (
        tmp_path / "intake-vertical-readiness-cli" / "intake_vertical_readiness_audit_report.json"
    ).is_file()
