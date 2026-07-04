from copy import deepcopy

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_linking_preflight import run_matter_linking_preflight
from lawfirm_os_intake.matter_linking_review_outcomes import (
    MATTER_LINKING_REVIEW_OUTCOME_HISTORY_FILENAME,
    MATTER_LINKING_REVIEW_OUTCOME_NOTES_FILENAME,
    MATTER_LINKING_REVIEW_OUTCOME_RECORD_FILENAME,
    MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME,
    build_matter_linking_review_outcome_report,
    run_matter_linking_review_outcome_record,
)
from lawfirm_os_intake.models import (
    MatterLinkingPreflightReport,
    MatterLinkingReviewDecision,
    MatterLinkingReviewOutcomeRecord,
    MatterLinkingReviewOutcomeReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


FIXED_TIME = "2026-07-04T00:00:00Z"


def _resolved_preflight(repo_root, tmp_path):
    _, run_dir = run_matter_linking_preflight(
        input_path=(
            repo_root
            / "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
        ),
        out_dir=tmp_path / "resolved-preflight",
        generated_at=FIXED_TIME,
    )
    return run_dir / "matter_linking_preflight_report.json"


def _ambiguous_preflight(repo_root, tmp_path):
    _, run_dir = run_matter_linking_preflight(
        input_path=repo_root / "examples/synthetic/upfront/upfront-like-intake-output.example.json",
        out_dir=tmp_path / "ambiguous-preflight",
        generated_at=FIXED_TIME,
    )
    return run_dir / "matter_linking_preflight_report.json"


def _weak_preflight(repo_root, tmp_path):
    _, run_dir = run_matter_linking_preflight(
        input_path=(
            repo_root
            / "examples/synthetic/upfront/upfront-like-intake-output.weak-single-candidate.example.json"
        ),
        out_dir=tmp_path / "weak-preflight",
        generated_at=FIXED_TIME,
    )
    return run_dir / "matter_linking_preflight_report.json"


def _confirm_split_outcome(repo_root):
    return load_json(
        repo_root / "examples/synthetic/upfront/matter-linking-review-confirm-split.outcome.json"
    )


def _request_more_info_outcome(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/upfront/matter-linking-review-request-more-info.outcome.json"
    )


def test_matter_linking_review_outcome_records_confirmed_split(
    tmp_path,
    repo_root,
):
    preflight_path = _resolved_preflight(repo_root, tmp_path)
    outcome_path = write_json(tmp_path / "confirm-split.json", _confirm_split_outcome(repo_root))

    report, run_dir = run_matter_linking_review_outcome_record(
        matter_linking_preflight_report_path=preflight_path,
        outcome_path=outcome_path,
        out_dir=tmp_path / "review-outcome",
        generated_at=FIXED_TIME,
    )
    persisted = MatterLinkingReviewOutcomeReport.model_validate(
        load_json(run_dir / MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME)
    )
    history = load_jsonl(run_dir / MATTER_LINKING_REVIEW_OUTCOME_HISTORY_FILENAME)
    notes = (run_dir / MATTER_LINKING_REVIEW_OUTCOME_NOTES_FILENAME).read_text(encoding="utf-8")

    assert persisted.matter_linking_review_outcome_report_id == (
        report.matter_linking_review_outcome_report_id
    )
    assert report.status == "matter_linking_review_outcome_recorded"
    assert report.overall_outcome == "confirm_split"
    assert report.source_cluster_count == 2
    assert report.reviewed_cluster_count == 2
    assert report.unreviewed_cluster_count == 0
    assert report.unknown_cluster_count == 0
    assert report.split_decision_count == 1
    assert "matter_linking_confirmed_split_candidate" in report.candidate_lake_event_labels
    assert "source_matter_link_resolved_candidate" in report.candidate_lake_event_labels
    assert "confirm_principal_party_roles_per_cluster_before_budget" in (report.required_next_gates)
    assert report.budget_amount_output_authorized is False
    assert report.matter_opening_authorized is False
    assert report.conflict_conclusion_emitted is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert len(history) == 1
    assert history[0]["matter_linking_review_outcome_record_id"] == (
        "matter-linking-review-outcome.synthetic-confirm-split.v0_1"
    )
    assert (run_dir / MATTER_LINKING_REVIEW_OUTCOME_RECORD_FILENAME).is_file()
    assert "does not call Upfront" in notes


def test_matter_linking_review_outcome_records_request_more_info_as_pending(
    tmp_path,
    repo_root,
):
    preflight_path = _ambiguous_preflight(repo_root, tmp_path)
    outcome_path = write_json(
        tmp_path / "request-more-info.json",
        _request_more_info_outcome(repo_root),
    )

    report, _ = run_matter_linking_review_outcome_record(
        matter_linking_preflight_report_path=preflight_path,
        outcome_path=outcome_path,
        out_dir=tmp_path / "request-more-info-outcome",
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_linking_review_outcome_recorded_pending_followup"
    assert report.overall_outcome == "request_more_info"
    assert report.request_more_info_decision_count == 1
    assert report.unreviewed_cluster_count == 0
    assert report.required_followups
    assert "complete_matter_linking_followup_before_budget_or_opening" in (
        report.required_next_gates
    )
    assert "matter_linking_followup_required_candidate" in report.candidate_lake_event_labels
    assert report.budget_amount_output_authorized is False
    assert report.matter_opening_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False


def test_matter_linking_review_outcome_blocks_unknown_cluster(
    tmp_path,
    repo_root,
):
    preflight_path = _resolved_preflight(repo_root, tmp_path)
    outcome = deepcopy(_confirm_split_outcome(repo_root))
    outcome["decisions"][0]["selected_cluster_ids"].append("cluster.unknown")
    outcome["decisions"][0]["evidence_refs"].append("cluster.unknown")
    outcome_path = write_json(tmp_path / "bad-cluster.json", outcome)
    preflight_report = load_json(preflight_path)

    report = build_matter_linking_review_outcome_report(
        matter_linking_preflight_report=MatterLinkingPreflightReport.model_validate(
            preflight_report
        ),
        matter_linking_preflight_report_ref=str(preflight_path),
        outcome_record=MatterLinkingReviewOutcomeRecord.model_validate(outcome),
        history_ref="matter_linking_review_outcome_history.jsonl",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert outcome_path.is_file()
    assert report.status == "blocked_by_matter_linking_review_outcome"
    assert "outcome_decisions_target_known_clusters" in failed
    assert report.unknown_cluster_ids == ["cluster.unknown"]
    assert report.external_writes_performed is False


def test_matter_linking_review_outcome_blocks_source_preflight_failure(
    tmp_path,
    repo_root,
):
    preflight_path = _weak_preflight(repo_root, tmp_path)
    outcome = deepcopy(_confirm_split_outcome(repo_root))
    outcome["matter_linking_preflight_report_id"] = load_json(preflight_path)[
        "matter_linking_preflight_report_id"
    ]
    outcome_path = write_json(tmp_path / "weak-source-outcome.json", outcome)

    report, _ = run_matter_linking_review_outcome_record(
        matter_linking_preflight_report_path=preflight_path,
        outcome_path=outcome_path,
        out_dir=tmp_path / "weak-source-review",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_matter_linking_review_outcome"
    assert "matter_linking_preflight_ready_without_writes" in failed


def test_matter_linking_review_decision_requires_merge_cardinality():
    with pytest.raises(ValueError, match="confirm_merge decisions require at least two clusters"):
        MatterLinkingReviewDecision(
            decision_id="bad-merge",
            outcome="confirm_merge",
            selected_cluster_ids=["cluster.case-a"],
            decision_reason="Synthetic malformed merge decision.",
            evidence_refs=["cluster.case-a"],
            red_team_notes=["This should fail closed."],
            candidate_exception_lake_labels=["matter_linking_confirmed_merge_candidate"],
        )


def test_matter_linking_review_outcome_cli_writes_record_history_and_report(
    tmp_path,
    repo_root,
    capsys,
):
    preflight_path = _resolved_preflight(repo_root, tmp_path)
    outcome_path = write_json(tmp_path / "confirm-split.json", _confirm_split_outcome(repo_root))

    exit_code = main(
        [
            "record-matter-linking-review-outcome",
            "--matter-linking-preflight-report",
            str(preflight_path),
            "--outcome",
            str(outcome_path),
            "--out-dir",
            str(tmp_path / "cli-review-outcome"),
            "--generated-at",
            FIXED_TIME,
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "matter_linking_review_outcome_recorded"' in captured.out
    assert '"overall_outcome": "confirm_split"' in captured.out
    assert '"reviewed_cluster_count": 2' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path / "cli-review-outcome" / MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME
    ).is_file()
    assert (
        tmp_path / "cli-review-outcome" / MATTER_LINKING_REVIEW_OUTCOME_HISTORY_FILENAME
    ).is_file()
