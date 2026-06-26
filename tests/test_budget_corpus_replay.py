from lawfirm_os_intake.budget_calibration_corpus import (
    build_budget_calibration_corpus_report,
    run_budget_calibration_corpus_audit,
)
from lawfirm_os_intake.budget_corpus_replay import (
    build_budget_corpus_replay_plan,
    run_budget_corpus_replay_plan,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import BudgetCorpusReplayPlan
from lawfirm_os_intake.util import load_json, write_json


def _planned_case_by_kind(plan: BudgetCorpusReplayPlan, kind: str):
    return next(
        case
        for case in plan.cases
        if case.artifact_kind == kind and case.status == "planned_for_replay"
    )


def test_budget_corpus_replay_plan_maps_eligible_artifacts_to_command_chains(repo_root):
    corpus_report = build_budget_calibration_corpus_report(
        repo_root / "examples/synthetic",
        repo_root=repo_root,
    )
    plan = build_budget_corpus_replay_plan(
        corpus_report,
        source_corpus_report_ref="processed/budget-corpus/budget_calibration_corpus_report.json",
    )

    assert plan.status == "replay_plan_ready_for_review"
    assert plan.planned_case_count > 0
    assert plan.blocked_case_count == 0
    assert plan.calibration_applied is False
    assert plan.profile_mutation_performed is False
    assert plan.template_mutation_performed is False
    assert plan.budget_mutation_performed is False
    assert plan.carrier_guideline_mutation_performed is False
    assert plan.lake_write_performed is False
    assert plan.sqlite_write_performed is False
    assert plan.external_writes_performed is False
    assert plan.silent_learning_performed is False

    budget_review_case = _planned_case_by_kind(plan, "budget_review_fixture")
    budget_review_commands = [command.command for command in budget_review_case.command_chain]
    assert any("demo" in command for command in budget_review_commands)
    assert any("record-budget-review" in command for command in budget_review_commands)
    assert any("review-learning-gate" in command for command in budget_review_commands)

    actuals_case = _planned_case_by_kind(plan, "actuals_fixture")
    actuals_commands = [command.command for command in actuals_case.command_chain]
    assert any("compare-budget-actuals" in command for command in actuals_commands)
    assert any("--budget-actual-comparison-report" in command for command in actuals_commands)

    carrier_case = _planned_case_by_kind(plan, "carrier_rejection_fixture")
    carrier_commands = [command.command for command in carrier_case.command_chain]
    assert any("capture-carrier-rejections" in command for command in carrier_commands)
    assert any("review-carrier-rejections" in command for command in carrier_commands)
    assert any("propose-carrier-rejection-learning" in command for command in carrier_commands)
    assert any("--carrier-learning-report" in command for command in carrier_commands)

    shadow_case = _planned_case_by_kind(plan, "learning_shadow_eval_fixture")
    shadow_commands = [command.command for command in shadow_case.command_chain]
    assert any("run-learning-shadow-eval" in command for command in shadow_commands)
    assert any(
        "{required_learning_proposed_change_set_json}" in command for command in shadow_commands
    )

    for case in plan.cases:
        if case.status == "supporting_context_only":
            assert case.command_chain == []
        if case.artifact_kind == "learning_support_fixture":
            assert case.status == "supporting_context_only"
            assert case.command_chain == []
        for command in case.command_chain:
            assert command.execution_mode == "planned_only_not_executed"
            assert command.not_authorized_for_external_write is True
            assert command.not_authorized_for_lake_write is True
            assert command.external_writes_performed is False
            assert command.lake_write_performed is False
            assert command.sqlite_write_performed is False
            assert command.silent_learning_performed is False


def test_budget_corpus_replay_plan_blocks_when_corpus_report_is_blocked(tmp_path):
    corpus = tmp_path / "corpus"
    write_json(
        corpus / "actuals" / "real-actuals.json",
        {
            "schema_version": "0.1",
            "actuals_source_id": "real-actuals",
            "data_origin": "production",
            "contains_real_client_data": True,
            "external_writes_performed": True,
        },
    )
    corpus_report = build_budget_calibration_corpus_report(corpus, repo_root=tmp_path)
    plan = build_budget_corpus_replay_plan(
        corpus_report,
        source_corpus_report_ref="blocked-corpus-report.json",
    )

    assert corpus_report.status == "blocked_real_or_privileged_data"
    assert plan.status == "blocked_by_corpus_report"
    assert plan.planned_case_count == 0
    assert plan.blocked_case_count == 1
    assert all(case.command_chain == [] for case in plan.cases)
    assert plan.external_writes_performed is False
    assert plan.silent_learning_performed is False


def test_budget_corpus_replay_cli_writes_plan(tmp_path, repo_root, capsys):
    _, audit_dir = run_budget_calibration_corpus_audit(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=tmp_path / "budget-corpus",
    )

    exit_code = main(
        [
            "plan-budget-corpus-replay",
            "--corpus-report",
            str(audit_dir / "budget_calibration_corpus_report.json"),
            "--out-dir",
            str(tmp_path / "budget-replay"),
        ]
    )
    captured = capsys.readouterr()
    plan_path = tmp_path / "budget-replay" / "budget_corpus_replay_plan.json"
    notes_path = tmp_path / "budget-replay" / "budget_corpus_replay_plan.md"
    plan = BudgetCorpusReplayPlan.model_validate(load_json(plan_path))

    assert exit_code == 0
    assert plan.status == "replay_plan_ready_for_review"
    assert plan.candidate_only is True
    assert '"calibration_applied": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not execute commands" in notes_path.read_text(encoding="utf-8")


def test_budget_corpus_replay_runner_persists_candidate_plan(tmp_path, repo_root):
    _, audit_dir = run_budget_calibration_corpus_audit(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=tmp_path / "budget-corpus",
    )
    plan, run_dir = run_budget_corpus_replay_plan(
        corpus_report_path=audit_dir / "budget_calibration_corpus_report.json",
        out_dir=tmp_path / "budget-replay-runner",
    )
    persisted = BudgetCorpusReplayPlan.model_validate(
        load_json(run_dir / "budget_corpus_replay_plan.json")
    )

    assert persisted.replay_plan_id == plan.replay_plan_id
    assert persisted.candidate_only is True
    assert persisted.non_authoritative is True
    assert persisted.synthetic_only is True
