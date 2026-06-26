from lawfirm_os_intake.cli import main
from lawfirm_os_intake.learning_owner_handoffs import run_learning_owner_handoffs
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.learning_shadow_eval_results import run_learning_shadow_eval_results
from lawfirm_os_intake.models import LearningOwnerHandoffReport
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _change_set_path(tmp_path, repo_root):
    _, run_dir = run_learning_proposed_changes(
        shadow_eval_plan_path=repo_root
        / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
        promotion_readiness_report_path=repo_root
        / "examples/synthetic/learning/proposed-change-readiness-report.json",
        out_dir=tmp_path / "learning-proposed-changes",
    )
    return run_dir / "learning_proposed_change_set.json"


def _passed_shadow_eval_report_path(tmp_path, repo_root):
    change_set_path = _change_set_path(tmp_path, repo_root)
    _, run_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=[
            repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json",
            repo_root / "examples/synthetic/learning/shadow-eval-result-capture-completeness.json",
        ],
        out_dir=tmp_path / "learning-shadow-eval",
    )
    return run_dir / "learning_shadow_eval_result_report.json"


def test_learning_owner_handoffs_group_passed_results_by_owner(tmp_path, repo_root):
    result_report_path = _passed_shadow_eval_report_path(tmp_path, repo_root)

    report, run_dir = run_learning_owner_handoffs(
        shadow_eval_result_report_path=result_report_path,
        out_dir=tmp_path / "learning-owner-handoffs",
    )
    persisted = LearningOwnerHandoffReport.model_validate(
        load_json(run_dir / "learning_owner_handoff_report.json")
    )
    packages = load_jsonl(run_dir / "learning_owner_handoff_packages.jsonl")

    assert persisted.owner_handoff_report_id == report.owner_handoff_report_id
    assert persisted.status == "owner_handoff_ready_review_required"
    assert persisted.package_count == 2
    assert persisted.passed_candidate_count == 2
    assert persisted.failed_candidate_count == 0
    assert persisted.blocked_candidate_count == 0
    assert len(packages) == 2
    assert set(persisted.target_owners) == {
        "LawFirm-os-intake",
        "LawFirm-os-orchestrator",
    }
    assert all(package.status == "ready_for_owner_review" for package in persisted.packages)
    assert all(package.promotion_authorized is False for package in persisted.packages)
    assert all(package.proposed_changes_applied is False for package in persisted.packages)
    assert all(
        item.disposition == "ready_for_owner_review"
        for item in persisted.packages[0].ready_items + persisted.packages[1].ready_items
    )
    assert (run_dir / "owner_handoffs" / "intake.json").is_file()
    assert (run_dir / "owner_handoffs" / "orchestrator.json").is_file()
    assert persisted.package_output_refs
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "learning_owner_handoff_report.md").read_text(encoding="utf-8")
    assert "Owner packages separate passed, failed, and blocked candidates" in notes_text
    owner_notes = (run_dir / "owner_handoffs" / "intake.md").read_text(encoding="utf-8")
    assert "This package is an owner-review handoff only" in owner_notes


def test_learning_owner_handoffs_separate_blocked_and_failed(tmp_path, repo_root):
    change_set_path = _change_set_path(tmp_path, repo_root)
    _, blocked_eval_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        out_dir=tmp_path / "learning-shadow-eval-blocked",
    )
    blocked_report, _ = run_learning_owner_handoffs(
        shadow_eval_result_report_path=blocked_eval_dir / "learning_shadow_eval_result_report.json",
        out_dir=tmp_path / "learning-owner-handoffs-blocked",
    )

    assert blocked_report.status == "owner_handoff_blocked_or_failed"
    assert blocked_report.blocked_candidate_count == 2
    assert blocked_report.failed_candidate_count == 0
    assert blocked_report.passed_candidate_count == 0
    assert all(
        package.status == "blocked_or_failed_before_review" for package in blocked_report.packages
    )
    assert all(package.blocked_items for package in blocked_report.packages)

    failed_fixture = load_json(
        repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json"
    )
    failed_fixture["fixture_result_id"] = "shadowevalfixture_failed_owner_handoff"
    failed_fixture["evaluation_outcome"] = "failed"
    failed_fixture["passed_eval_suites"] = []
    failed_fixture["failed_eval_suites"] = ["budget driver counterfactual"]
    failed_fixture["passed_regression_guardrails"] = []
    failed_fixture["failed_regression_guardrails"] = ["no budget submission"]
    failed_fixture_path = write_json(tmp_path / "failed-owner-handoff-fixture.json", failed_fixture)
    _, failed_eval_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=[failed_fixture_path],
        out_dir=tmp_path / "learning-shadow-eval-failed",
    )
    failed_report, _ = run_learning_owner_handoffs(
        shadow_eval_result_report_path=failed_eval_dir / "learning_shadow_eval_result_report.json",
        out_dir=tmp_path / "learning-owner-handoffs-failed",
    )

    assert failed_report.status == "owner_handoff_blocked_or_failed"
    assert failed_report.failed_candidate_count == 1
    assert failed_report.blocked_candidate_count == 1
    assert failed_report.passed_candidate_count == 0
    failed_package = next(package for package in failed_report.packages if package.failed_items)
    assert failed_package.failed_items[0].disposition == "failed_before_owner_review"


def test_learning_owner_handoffs_cli_and_no_candidates(tmp_path, repo_root, capsys):
    result_report_path = _passed_shadow_eval_report_path(tmp_path, repo_root)

    exit_code = main(
        [
            "build-learning-owner-handoffs",
            "--shadow-eval-result-report",
            str(result_report_path),
            "--out-dir",
            str(tmp_path / "learning-owner-handoffs-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "owner_handoff_ready_review_required"' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert '"proposed_changes_applied": false' in captured.out
    assert (
        tmp_path / "learning-owner-handoffs-cli" / "learning_owner_handoff_report.json"
    ).is_file()

    raw_result = load_json(result_report_path)
    raw_result["status"] = "no_learning_candidates"
    raw_result["change_count"] = 0
    raw_result["result_count"] = 0
    raw_result["passed_result_count"] = 0
    raw_result["failed_result_count"] = 0
    raw_result["blocked_result_count"] = 0
    raw_result["target_learning_loops"] = []
    raw_result["target_owners"] = []
    raw_result["results"] = []
    no_candidate_result_path = write_json(tmp_path / "no-candidate-shadow-eval.json", raw_result)
    empty_report, _ = run_learning_owner_handoffs(
        shadow_eval_result_report_path=no_candidate_result_path,
        out_dir=tmp_path / "learning-owner-handoffs-empty",
    )

    assert empty_report.status == "no_learning_candidates"
    assert empty_report.package_count == 0
    assert empty_report.packages == []
