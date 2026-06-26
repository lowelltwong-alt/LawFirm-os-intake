from lawfirm_os_intake.budget_calibration_corpus import run_budget_calibration_corpus_audit
from lawfirm_os_intake.budget_corpus_replay import run_budget_corpus_replay_plan
from lawfirm_os_intake.budget_corpus_replay_execution import (
    run_budget_corpus_replay_execution,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayPlan,
)
from lawfirm_os_intake.util import load_json


def _write_plan(tmp_path, repo_root):
    _, audit_dir = run_budget_calibration_corpus_audit(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=tmp_path / "budget-corpus",
    )
    plan, plan_dir = run_budget_corpus_replay_plan(
        corpus_report_path=audit_dir / "budget_calibration_corpus_report.json",
        out_dir=tmp_path / "budget-replay-plan",
    )
    return plan, plan_dir / "budget_corpus_replay_plan.json"


def _planned_case_id(plan: BudgetCorpusReplayPlan, kind: str) -> str:
    return next(
        case.replay_case_id
        for case in plan.cases
        if case.artifact_kind == kind and case.status == "planned_for_replay"
    )


def test_budget_corpus_replay_execution_dry_run_audits_plan(tmp_path, repo_root):
    plan, plan_path = _write_plan(tmp_path, repo_root)

    report, run_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
    )
    persisted = BudgetCorpusReplayExecutionReport.model_validate(
        load_json(run_dir / "budget_corpus_replay_execution_report.json")
    )

    assert persisted.replay_execution_report_id == report.replay_execution_report_id
    assert report.status == "dry_run_ready_for_review"
    assert report.execution_mode == "dry_run"
    assert report.dry_run_case_count == plan.planned_case_count
    assert report.executed_case_count == 0
    assert report.calibration_applied is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert any(
        command.status == "planned_only_not_executed"
        for case in report.cases
        for command in case.command_results
    )
    assert any(case.status == "skipped_supporting_context" for case in report.cases)


def test_budget_corpus_replay_execution_runs_selected_budget_review_case(tmp_path, repo_root):
    plan, plan_path = _write_plan(tmp_path, repo_root)
    budget_review_case_id = _planned_case_id(plan, "budget_review_fixture")

    report, run_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
        execute=True,
        case_ids=[budget_review_case_id],
    )
    case = next(case for case in report.cases if case.replay_case_id == budget_review_case_id)

    assert report.status == "execution_passed_for_review"
    assert report.execution_mode == "execute"
    assert report.executed_case_count == 1
    assert report.failed_case_count == 0
    assert case.status == "executed_passed"
    assert all(command.status == "executed_passed" for command in case.command_results)
    assert all(output.exists for output in case.output_checks)
    assert (
        run_dir
        / "replay-output"
        / "cases"
        / budget_review_case_id
        / "budget-review"
        / "budget_revision_report.json"
    ).is_file()
    assert (
        run_dir
        / "replay-output"
        / "cases"
        / budget_review_case_id
        / "learning-gate"
        / "reviewed_learning_gate_report.json"
    ).is_file()


def test_budget_corpus_replay_execution_blocks_shadow_eval_without_proposed_change_set(
    tmp_path,
    repo_root,
):
    plan, plan_path = _write_plan(tmp_path, repo_root)
    shadow_case_id = _planned_case_id(plan, "learning_shadow_eval_fixture")

    report, _ = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
        execute=True,
        case_ids=[shadow_case_id],
    )
    case = next(case for case in report.cases if case.replay_case_id == shadow_case_id)

    assert report.status == "execution_failed"
    assert case.status == "executed_failed"
    assert case.command_results[0].status == "blocked_missing_placeholder"
    assert "required_learning_proposed_change_set_json_missing" in case.blocking_reasons
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_budget_corpus_replay_execution_cli_writes_report(tmp_path, repo_root, capsys):
    _, plan_path = _write_plan(tmp_path, repo_root)

    exit_code = main(
        [
            "replay-budget-corpus",
            "--replay-plan",
            str(plan_path),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "budget-replay-cli"),
        ]
    )
    captured = capsys.readouterr()
    report_path = tmp_path / "budget-replay-cli" / "budget_corpus_replay_execution_report.json"
    notes_path = tmp_path / "budget-replay-cli" / "budget_corpus_replay_execution_report.md"
    report = BudgetCorpusReplayExecutionReport.model_validate(load_json(report_path))

    assert exit_code == 0
    assert report.status == "dry_run_ready_for_review"
    assert '"calibration_applied": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not authorize calibration" in notes_path.read_text(encoding="utf-8")
