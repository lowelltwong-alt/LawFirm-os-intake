from lawfirm_os_intake.budget_calibration_corpus import run_budget_calibration_corpus_audit
from lawfirm_os_intake.budget_corpus_replay import run_budget_corpus_replay_plan
from lawfirm_os_intake.budget_corpus_replay_execution import (
    run_budget_corpus_replay_execution,
)
from lawfirm_os_intake.budget_corpus_replay_review import (
    run_budget_corpus_replay_review,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayReviewPacket,
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


def _planned_case_id(plan, kind: str) -> str:
    return next(
        case.replay_case_id
        for case in plan.cases
        if case.artifact_kind == kind and case.status == "planned_for_replay"
    )


def _execution_report_path(run_dir):
    return run_dir / "budget_corpus_replay_execution_report.json"


def test_replay_review_packet_blocks_dry_run_until_execution(tmp_path, repo_root):
    _, plan_path = _write_plan(tmp_path, repo_root)
    execution_report, execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
    )

    packet, review_dir = run_budget_corpus_replay_review(
        replay_execution_report_path=_execution_report_path(execution_dir),
        out_dir=tmp_path / "budget-replay-review",
    )
    persisted = BudgetCorpusReplayReviewPacket.model_validate(
        load_json(review_dir / "budget_corpus_replay_review_packet.json")
    )

    assert persisted.review_packet_id == packet.review_packet_id
    assert execution_report.status == "dry_run_ready_for_review"
    assert packet.status == "blocked_pending_replay_execution"
    assert packet.dry_run_case_count > 0
    assert any(
        rec.recommended_action == "execute_before_learning_review" for rec in packet.recommendations
    )
    assert packet.human_review_required is True
    assert packet.append_only_review_outcome_required is True
    assert packet.downstream_learning_gate_allowed_without_review is False
    assert packet.external_writes_performed is False
    assert packet.silent_learning_performed is False


def test_replay_review_packet_for_executed_case_requires_human_decision(
    tmp_path,
    repo_root,
):
    plan, plan_path = _write_plan(tmp_path, repo_root)
    case_id = _planned_case_id(plan, "budget_review_fixture")
    _, execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
        execute=True,
        case_ids=[case_id],
    )

    packet, review_dir = run_budget_corpus_replay_review(
        replay_execution_report_path=_execution_report_path(execution_dir),
        out_dir=tmp_path / "budget-replay-review",
    )
    recommendation = next(rec for rec in packet.recommendations if rec.replay_case_id == case_id)
    template = next(item for item in packet.decision_templates if item.replay_case_id == case_id)

    assert packet.status == "ready_for_human_replay_review"
    assert packet.executed_passed_case_count == 1
    assert recommendation.recommended_action == "review_fixture_binding"
    assert recommendation.downstream_learning_gate_candidate is True
    assert recommendation.downstream_learning_gate_allowed_without_review is False
    assert recommendation.output_refs
    assert template.recommended_outcome == "needs_more_information"
    assert "approve_fixture_binding" in template.allowed_outcomes
    assert template.append_only_review_outcome_required is True
    assert template.lake_write_authorized is False
    assert template.silent_learning_allowed is False
    assert (review_dir / "budget_corpus_replay_review_decision_template.json").is_file()
    assert "passed replay only proves command execution" in " ".join(
        note.message.lower() for note in packet.red_team_notes
    )


def test_replay_review_packet_flags_failed_shadow_eval_input(tmp_path, repo_root):
    plan, plan_path = _write_plan(tmp_path, repo_root)
    case_id = _planned_case_id(plan, "learning_shadow_eval_fixture")
    report, execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
        execute=True,
        case_ids=[case_id],
    )
    persisted_execution = BudgetCorpusReplayExecutionReport.model_validate(
        load_json(_execution_report_path(execution_dir))
    )

    packet, _ = run_budget_corpus_replay_review(
        replay_execution_report_path=_execution_report_path(execution_dir),
        out_dir=tmp_path / "budget-replay-review",
    )
    recommendation = next(rec for rec in packet.recommendations if rec.replay_case_id == case_id)

    assert report.status == "execution_failed"
    assert persisted_execution.status == "execution_failed"
    assert packet.status == "replay_repair_required"
    assert recommendation.recommended_action == "provide_shadow_eval_input_or_hold"
    assert "required_learning_proposed_change_set_json_missing" in recommendation.blocking_reasons
    assert any(note.scope == "shadow_eval" for note in packet.red_team_notes)
    assert packet.silent_learning_performed is False


def test_replay_review_cli_writes_packet_and_templates(tmp_path, repo_root, capsys):
    _, plan_path = _write_plan(tmp_path, repo_root)
    _, execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
    )

    exit_code = main(
        [
            "review-budget-corpus-replay",
            "--replay-execution-report",
            str(_execution_report_path(execution_dir)),
            "--out-dir",
            str(tmp_path / "budget-replay-review"),
        ]
    )
    captured = capsys.readouterr()
    packet_path = tmp_path / "budget-replay-review" / "budget_corpus_replay_review_packet.json"
    notes_path = tmp_path / "budget-replay-review" / "budget_corpus_replay_review_packet.md"
    templates_path = (
        tmp_path / "budget-replay-review" / "budget_corpus_replay_review_decision_template.json"
    )
    packet = BudgetCorpusReplayReviewPacket.model_validate(load_json(packet_path))

    assert exit_code == 0
    assert packet.status == "blocked_pending_replay_execution"
    assert '"human_review_required": true' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert templates_path.is_file()
    assert "does not approve fixture binding" in notes_path.read_text(encoding="utf-8")
