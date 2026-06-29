import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.models import LearningProposedChangeSet
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def test_learning_proposed_changes_create_reviewer_notes_and_red_team(
    tmp_path,
    repo_root,
):
    change_set, run_dir = run_learning_proposed_changes(
        shadow_eval_plan_path=repo_root
        / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
        promotion_readiness_report_path=repo_root
        / "examples/synthetic/learning/proposed-change-readiness-report.json",
        out_dir=tmp_path / "learning-proposed-changes",
    )
    persisted = LearningProposedChangeSet.model_validate(
        load_json(run_dir / "learning_proposed_change_set.json")
    )
    jsonl_changes = load_jsonl(run_dir / "learning_proposed_changes.jsonl")

    assert persisted.proposed_change_set_id == change_set.proposed_change_set_id
    assert persisted.status == "draft_candidates_ready_for_human_review"
    assert persisted.change_count == 2
    assert len(jsonl_changes) == persisted.change_count
    assert persisted.promotion_readiness_report_id == (
        "learningpromotion_fixture_learning_proposed_changes"
    )
    assert set(persisted.target_learning_loops) == {
        "budget_model",
        "capture_completeness",
    }
    assert set(persisted.target_owners) == {
        "LawFirm-os-intake",
        "LawFirm-os-orchestrator",
    }

    budget_change = next(
        change
        for change in persisted.changes
        if change.candidate_id == "learninggate_fixture_budget_driver"
    )
    orchestrator_change = next(
        change
        for change in persisted.changes
        if change.candidate_id == "learninggate_fixture_capture_completeness"
    )
    assert budget_change.change_type == "budget_driver_adjustment_candidate"
    assert budget_change.recommendation == "draft_for_human_review"
    assert budget_change.recommendation_rationale
    assert {note.risk_area for note in budget_change.red_team_notes} >= {
        "evidence",
        "authority",
        "math",
    }
    assert orchestrator_change.change_type == "capture_reconciliation_rule_candidate"
    assert orchestrator_change.recommendation == "hold_for_owning_repo"
    assert {note.risk_area for note in orchestrator_change.red_team_notes} >= {
        "evidence",
        "authority",
        "workflow",
    }
    assert all(
        "proposed_change_artifact" in change.required_next_gates
        and "shadow_eval_result" in change.required_next_gates
        for change in persisted.changes
    )
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.baseline_mutated is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "learning_proposed_change_set.md").read_text(encoding="utf-8")
    assert "Recommendation:" in notes_text
    assert "Why:" in notes_text
    assert "Red-team objections:" in notes_text
    assert "They do not mutate budgets" in notes_text


def test_learning_proposed_changes_cli_no_candidates_and_mismatch_fail_closed(
    tmp_path,
    repo_root,
    capsys,
):
    exit_code = main(
        [
            "draft-learning-proposed-changes",
            "--shadow-eval-plan",
            str(repo_root / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json"),
            "--promotion-readiness-report",
            str(repo_root / "examples/synthetic/learning/proposed-change-readiness-report.json"),
            "--out-dir",
            str(tmp_path / "learning-proposed-changes-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "draft_candidates_ready_for_human_review"' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert '"proposed_changes_applied": false' in captured.out
    assert (
        tmp_path / "learning-proposed-changes-cli" / "learning_proposed_change_set.json"
    ).is_file()

    raw_plan = load_json(
        repo_root / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json"
    )
    raw_plan["status"] = "no_learning_candidates"
    raw_plan["case_count"] = 0
    raw_plan["cases"] = []
    no_candidate_plan = write_json(tmp_path / "no-candidate-plan.json", raw_plan)
    empty_set, _ = run_learning_proposed_changes(
        shadow_eval_plan_path=no_candidate_plan,
        out_dir=tmp_path / "learning-proposed-changes-empty",
    )

    assert empty_set.status == "no_learning_candidates"
    assert empty_set.change_count == 0
    assert empty_set.changes == []

    raw_report = load_json(
        repo_root / "examples/synthetic/learning/proposed-change-readiness-report.json"
    )
    raw_report["shadow_eval_plan_id"] = "shadowevalplan_wrong"
    mismatch_report = write_json(tmp_path / "mismatch-readiness-report.json", raw_report)
    with pytest.raises(ValueError, match="does not match shadow eval plan"):
        run_learning_proposed_changes(
            shadow_eval_plan_path=repo_root
            / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
            promotion_readiness_report_path=mismatch_report,
            out_dir=tmp_path / "learning-proposed-changes-mismatch",
        )
