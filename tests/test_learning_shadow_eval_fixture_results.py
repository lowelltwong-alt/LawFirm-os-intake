import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.learning_shadow_eval_fixture_results import (
    run_learning_shadow_eval_fixture_results,
)
from lawfirm_os_intake.learning_shadow_eval_results import run_learning_shadow_eval_results
from lawfirm_os_intake.models import (
    LearningShadowEvalFixtureEvidenceReport,
    LearningShadowEvalResultReport,
)
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


def _review_payload(change_set_path, *, decision="record_fixture_results", limit=None):
    change_set = load_json(change_set_path)
    changes = change_set["changes"]
    if limit is not None:
        changes = changes[:limit]
    return {
        "schema_version": "0.1",
        "shadow_eval_fixture_review_id": "shadow-eval-fixture-review-test",
        "proposed_change_set_id": change_set["proposed_change_set_id"],
        "reviewer_id": "synthetic-reviewer",
        "reviewer_role": "test reviewer",
        "reviewed_at": "2026-06-26T00:00:00Z",
        "decision": decision,
        "decision_reason": "Synthetic reviewer confirmed fixture evidence for tests.",
        "items": [
            {
                "proposed_change_id": change["proposed_change_id"],
                "candidate_id": change["candidate_id"],
                "evaluation_outcome": "passed",
                "passed_eval_suites": change["required_eval_suites"],
                "failed_eval_suites": [],
                "passed_regression_guardrails": change["regression_guardrails"],
                "failed_regression_guardrails": [],
                "expected_behavior_summary": change["proposed_behavior_summary"],
                "observed_behavior_summary": (
                    "Synthetic reviewer observed expected proposed behavior."
                ),
                "support_refs": [
                    "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
                    "examples/synthetic/learning/proposed-change-readiness-report.json",
                    f"synthetic-shadow-eval://reviewed/{change['proposed_change_id']}",
                ],
            }
            for change in changes
        ],
        "evidence_refs": [str(change_set_path)],
        "required_followups": [
            "run-learning-shadow-eval",
            "owning-repo review remains required",
        ],
        "reviewed_red_team_notes": [
            "Passing synthetic fixture evidence is owner-review input only.",
            "No baseline, profile, template, guideline, Lake, or connector mutation is authorized.",
        ],
    }


def test_record_learning_shadow_eval_fixture_results_and_reuse_report(
    tmp_path,
    repo_root,
):
    change_set_path = _change_set_path(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "fixture-review.json",
        _review_payload(change_set_path),
    )

    report, run_dir = run_learning_shadow_eval_fixture_results(
        proposed_change_set_path=change_set_path,
        review_path=review_path,
        out_dir=tmp_path / "learning-shadow-eval-fixture-evidence",
    )
    persisted = LearningShadowEvalFixtureEvidenceReport.model_validate(
        load_json(run_dir / "learning_shadow_eval_fixture_evidence_report.json")
    )
    jsonl_results = load_jsonl(run_dir / "learning_shadow_eval_fixture_results.jsonl")

    assert persisted.fixture_evidence_report_id == report.fixture_evidence_report_id
    assert persisted.status == "fixture_results_recorded"
    assert persisted.change_count == 2
    assert persisted.passed_item_count == 2
    assert persisted.failed_item_count == 0
    assert persisted.blocked_item_count == 0
    assert persisted.missing_item_count == 0
    assert len(persisted.fixture_result_refs) == 2
    assert len(jsonl_results) == 2
    assert all(
        load_json(ref)["evaluation_outcome"] == "passed" for ref in persisted.fixture_result_refs
    )
    assert all(ref.endswith(".json") for ref in persisted.fixture_result_refs)
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.baseline_mutated is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    shadow_report, shadow_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_report_paths=[run_dir / "learning_shadow_eval_fixture_evidence_report.json"],
        out_dir=tmp_path / "learning-shadow-eval",
    )
    persisted_shadow = LearningShadowEvalResultReport.model_validate(
        load_json(shadow_dir / "learning_shadow_eval_result_report.json")
    )
    assert persisted_shadow.shadow_eval_result_report_id == (
        shadow_report.shadow_eval_result_report_id
    )
    assert persisted_shadow.status == "shadow_eval_passed_owner_review_required"
    assert persisted_shadow.passed_result_count == 2
    assert persisted_shadow.blocked_result_count == 0
    assert all(result.fixture_result_id for result in persisted_shadow.results)


def test_record_learning_shadow_eval_fixture_results_partial_blocks_downstream(
    tmp_path,
    repo_root,
):
    change_set_path = _change_set_path(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "partial-fixture-review.json",
        _review_payload(
            change_set_path,
            decision="record_partial_fixture_results",
            limit=1,
        ),
    )

    report, run_dir = run_learning_shadow_eval_fixture_results(
        proposed_change_set_path=change_set_path,
        review_path=review_path,
        out_dir=tmp_path / "partial-learning-shadow-eval-fixture-evidence",
    )
    assert report.status == "fixture_results_partially_recorded"
    assert report.passed_item_count == 1
    assert report.missing_item_count == 1

    shadow_report, _ = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_report_paths=[run_dir / "learning_shadow_eval_fixture_evidence_report.json"],
        out_dir=tmp_path / "partial-learning-shadow-eval",
    )
    assert shadow_report.status == "shadow_eval_blocked"
    assert shadow_report.passed_result_count == 1
    assert shadow_report.blocked_result_count == 1
    assert any(
        result.status == "blocked_missing_fixture_result" for result in shadow_report.results
    )


def test_record_learning_shadow_eval_fixture_results_mismatch_fails_closed(
    tmp_path,
    repo_root,
):
    change_set_path = _change_set_path(tmp_path, repo_root)
    review = _review_payload(change_set_path)
    review["items"][0]["candidate_id"] = "candidate-mismatch"
    review_path = write_json(tmp_path / "mismatch-fixture-review.json", review)

    with pytest.raises(ValueError, match="candidate_id does not match"):
        run_learning_shadow_eval_fixture_results(
            proposed_change_set_path=change_set_path,
            review_path=review_path,
            out_dir=tmp_path / "mismatch-learning-shadow-eval-fixture-evidence",
        )


def test_learning_shadow_eval_fixture_results_cli(tmp_path, repo_root, capsys):
    change_set_path = _change_set_path(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "cli-fixture-review.json",
        _review_payload(change_set_path),
    )
    fixture_out_dir = tmp_path / "cli-learning-shadow-eval-fixture-evidence"

    exit_code = main(
        [
            "record-learning-shadow-eval-fixture-results",
            "--proposed-change-set",
            str(change_set_path),
            "--review",
            str(review_path),
            "--out-dir",
            str(fixture_out_dir),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"status": "fixture_results_recorded"' in captured.out
    assert '"proposed_changes_applied": false' in captured.out
    assert (fixture_out_dir / "learning_shadow_eval_fixture_evidence_report.json").is_file()

    shadow_exit_code = main(
        [
            "run-learning-shadow-eval",
            "--proposed-change-set",
            str(change_set_path),
            "--fixture-result-report",
            str(fixture_out_dir / "learning_shadow_eval_fixture_evidence_report.json"),
            "--out-dir",
            str(tmp_path / "cli-learning-shadow-eval"),
        ]
    )
    shadow_captured = capsys.readouterr()
    assert shadow_exit_code == 0
    assert '"status": "shadow_eval_passed_owner_review_required"' in shadow_captured.out
