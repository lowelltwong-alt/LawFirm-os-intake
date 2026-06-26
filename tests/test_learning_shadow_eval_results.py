import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.learning_shadow_eval_results import run_learning_shadow_eval_results
from lawfirm_os_intake.models import LearningShadowEvalResultReport
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


def test_learning_shadow_eval_results_pass_for_owner_review(
    tmp_path,
    repo_root,
):
    change_set_path = _change_set_path(tmp_path, repo_root)

    report, run_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=[
            repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json",
            repo_root / "examples/synthetic/learning/shadow-eval-result-capture-completeness.json",
        ],
        out_dir=tmp_path / "learning-shadow-eval-results",
    )
    persisted = LearningShadowEvalResultReport.model_validate(
        load_json(run_dir / "learning_shadow_eval_result_report.json")
    )
    jsonl_results = load_jsonl(run_dir / "learning_shadow_eval_results.jsonl")

    assert persisted.shadow_eval_result_report_id == report.shadow_eval_result_report_id
    assert persisted.status == "shadow_eval_passed_owner_review_required"
    assert persisted.change_count == 2
    assert persisted.result_count == 2
    assert persisted.passed_result_count == 2
    assert persisted.failed_result_count == 0
    assert persisted.blocked_result_count == 0
    assert len(jsonl_results) == 2
    assert all(result.status == "passed_for_owning_repo_review" for result in persisted.results)
    assert all(
        "owner_review_still_required" in result.passed_checks for result in persisted.results
    )
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.baseline_mutated is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "learning_shadow_eval_result_report.md").read_text(encoding="utf-8")
    assert "owner_review_required" in notes_text
    assert "no proposed change is applied here" in notes_text


def test_learning_shadow_eval_results_block_fail_and_mismatch(
    tmp_path,
    repo_root,
):
    change_set_path = _change_set_path(tmp_path, repo_root)

    blocked_report, _ = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        out_dir=tmp_path / "learning-shadow-eval-blocked",
    )
    assert blocked_report.status == "shadow_eval_blocked"
    assert blocked_report.blocked_result_count == 2
    assert all(
        result.status == "blocked_missing_fixture_result" for result in blocked_report.results
    )

    failed_fixture = load_json(
        repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json"
    )
    failed_fixture["fixture_result_id"] = "shadowevalfixture_failed_budget_driver"
    failed_fixture["evaluation_outcome"] = "failed"
    failed_fixture["passed_eval_suites"] = []
    failed_fixture["failed_eval_suites"] = ["budget driver counterfactual"]
    failed_fixture["passed_regression_guardrails"] = []
    failed_fixture["failed_regression_guardrails"] = ["no budget submission"]
    failed_fixture_path = write_json(tmp_path / "failed-shadow-eval-fixture.json", failed_fixture)
    failed_report, _ = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=[failed_fixture_path],
        out_dir=tmp_path / "learning-shadow-eval-failed",
    )
    assert failed_report.status == "shadow_eval_failed"
    assert failed_report.failed_result_count == 1
    failed_result = next(
        result for result in failed_report.results if result.status == "failed_shadow_eval"
    )
    assert "eval_suite_failed:budget driver counterfactual" in failed_result.failed_checks

    mismatch_fixture = load_json(
        repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json"
    )
    mismatch_fixture["proposed_change_id"] = "proposedchange_unknown"
    mismatch_fixture_path = write_json(
        tmp_path / "mismatch-shadow-eval-fixture.json", mismatch_fixture
    )
    with pytest.raises(ValueError, match="does not match proposed change set"):
        run_learning_shadow_eval_results(
            proposed_change_set_path=change_set_path,
            fixture_result_paths=[mismatch_fixture_path],
            out_dir=tmp_path / "learning-shadow-eval-mismatch",
        )


def test_learning_shadow_eval_cli(tmp_path, repo_root, capsys):
    change_set_path = _change_set_path(tmp_path, repo_root)

    exit_code = main(
        [
            "run-learning-shadow-eval",
            "--proposed-change-set",
            str(change_set_path),
            "--fixture-result",
            str(repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json"),
            "--fixture-result",
            str(
                repo_root
                / "examples/synthetic/learning/shadow-eval-result-capture-completeness.json"
            ),
            "--out-dir",
            str(tmp_path / "learning-shadow-eval-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "shadow_eval_passed_owner_review_required"' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert '"proposed_changes_applied": false' in captured.out
    assert (
        tmp_path / "learning-shadow-eval-cli" / "learning_shadow_eval_result_report.json"
    ).is_file()
