import shutil

from scripts import run_validation_suite

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_demo_qa_recipe import UI_DEMO_QA_RECIPE_REPORT_FILENAME
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"


def _step(step):
    return run_validation_suite.ValidationSuiteStepEvidence(
        step_id=step.name,
        command_key=step.command_key,
        command=list(step.command),
        command_display=" ".join(step.command),
        status="passed",
        return_code=0,
        timeout_seconds=step.timeout_seconds,
        duration_seconds=0.1,
        started_at="2026-07-05T00:00:00Z",
        completed_at="2026-07-05T00:00:01Z",
        evidence_refs=["scripts/run_validation_suite.py"],
    )


def _validation_report(tmp_path):
    report = run_validation_suite.build_validation_suite_evidence_report(
        steps=[_step(step) for step in run_validation_suite.validation_steps()],
        generated_at="2026-07-05T00:00:00Z",
        git_commit="abc123",
        working_tree_dirty=False,
    )
    return write_json(
        tmp_path / "validation_suite_evidence_report.json",
        report.model_dump(mode="json"),
    )


def test_run_ui_demo_qa_recipe_promotes_temp_fixtures_with_strict_gates(
    repo_root,
    tmp_path,
    capsys,
):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(repo_root / FIXTURE_ROOT, fixtures)
    validation_report = _validation_report(tmp_path)

    code = main(
        [
            "run-ui-demo-qa-recipe",
            "--out-dir",
            str(tmp_path / "recipe"),
            "--repo-root",
            str(repo_root),
            "--fixtures-root",
            str(fixtures),
            "--validation-suite-evidence-report",
            str(validation_report),
            "--generated-at",
            "2026-07-05T00:00:00Z",
            "--write-fixtures",
        ]
    )
    captured = capsys.readouterr()

    report = load_json(tmp_path / "recipe" / UI_DEMO_QA_RECIPE_REPORT_FILENAME)
    final_promotion = load_json(
        tmp_path / "recipe" / "final-promotion" / "ui_demo_fixture_promotion_report.json"
    )
    final_run = load_json(
        tmp_path / "recipe" / "final-synthetic-qa-review" / "synthetic_qa_review_run_report.json"
    )
    promoted_bundle = load_json(fixtures / "demo-ui-review-data-bundle.json")
    promoted_poc = load_json(fixtures / "demo-poc-qa-triage-report.json")

    assert code == 0
    assert report["status"] == "ui_demo_qa_recipe_verified"
    assert report["validation_mode"] == "provided"
    assert report["validation_suite_status"] == "validation_suite_passed"
    assert report["validation_exact_step_order_confirmed"] is True
    assert report["validation_worktree_clean_confirmed"] is True
    assert report["initial_synthetic_qa_status"] == "synthetic_qa_review_run_ready"
    assert report["temp_promotion_status"] == "ui_demo_fixture_promotion_verified"
    assert report["rust_boundary_status"] == "passed"
    assert report["rust_manifest_status"] == "passed"
    assert report["rust_boundary_root_matches_temp_fixtures"] is True
    assert report["rust_manifest_root_matches_temp_fixtures"] is True
    assert report["final_synthetic_qa_status"] == "synthetic_qa_review_run_ready"
    assert report["final_ui_bundle_status"] == "ready_for_review"
    assert report["final_poc_qa_triage_status"] == "poc_qa_ready_for_review"
    assert report["final_promotion_status"] == "ui_demo_fixture_promotion_verified"
    assert report["step_count"] == len(report["steps"]) == 7
    assert report["failed_step_count"] == 0
    assert report["blocked_step_count"] == 0
    assert report["temp_fixture_updates_performed"] is True
    assert report["local_fixture_updates_performed"] is True
    assert report["rollback_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert all(step["status"] == "passed" for step in report["steps"])
    assert {step["step_id"] for step in report["steps"]} == {
        "validation_suite_evidence",
        "initial_synthetic_qa_run",
        "temp_fixture_promotion",
        "rust_fixture_boundary",
        "rust_fixture_manifest",
        "final_synthetic_qa_run",
        "final_fixture_promotion",
    }
    assert final_promotion["status"] == "ui_demo_fixture_promotion_verified"
    assert final_promotion["missing_source_count"] == 0
    assert final_promotion["forbidden_run_root_leak_count"] == 0
    assert final_run["status"] == "synthetic_qa_review_run_ready"
    assert promoted_bundle["status"] == "ready_for_review"
    assert promoted_bundle["present_detail_report_count"] == promoted_bundle["detail_report_count"]
    assert promoted_poc["status"] == "poc_qa_ready_for_review"
    assert not list((tmp_path / "recipe").rglob("*.sqlite"))
    assert not list((tmp_path / "recipe").rglob("*.db"))
    assert '"status": "ui_demo_qa_recipe_verified"' in captured.out
