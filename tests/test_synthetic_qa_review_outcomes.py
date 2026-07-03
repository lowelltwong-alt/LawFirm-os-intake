import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    SyntheticQABlockerReviewOutcomeRecord,
    SyntheticQABlockerReviewOutcomeReport,
)
from lawfirm_os_intake.synthetic_qa_review_outcomes import (
    run_synthetic_qa_review_outcome_record,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _blocker_report_path(repo_root):
    return repo_root / "apps/legal-intake-budget/src/fixtures/demo-synthetic-qa-blocker-report.json"


def _blocker_report(repo_root):
    return load_json(_blocker_report_path(repo_root))


def _decision(row, index, *, outcome="accepted_for_poc_review"):
    followups = []
    if outcome == "needs_fix":
        followups = [f"Fix or re-run QA evidence for {row['row_id']}."]
    if outcome == "defer_to_roadmap":
        followups = [f"Carry {row['row_id']} into the remaining roadmap."]
    return {
        "decision_id": f"synthetic-qa-review-decision-{index}",
        "row_id": row["row_id"],
        "outcome": outcome,
        "decision_reason": f"Synthetic QA reviewer decision for {row['label']}.",
        "evidence_refs": [row["row_id"], *row["evidence_refs"]],
        "required_followups": followups,
        "red_team_notes": ["This is POC QA evidence only and does not prove production readiness."],
        "candidate_exception_lake_labels": [
            "synthetic_qa_review_decision_candidate",
            *row["candidate_exception_lake_labels"],
        ],
    }


def _record_payload(report, decisions):
    return {
        "schema_version": "0.1",
        "synthetic_qa_review_outcome_record_id": "synthetic-qa-review-outcome-record-1",
        "synthetic_qa_blocker_report_id": report["synthetic_qa_blocker_report_id"],
        "reviewer_id": "synthetic-qa-reviewer",
        "reviewed_at": "2026-07-03T00:00:00Z",
        "decision_reason": "Synthetic POC QA review pass over the blocker queue.",
        "decisions": decisions,
    }


def test_synthetic_qa_review_outcome_records_partial_review_append_only(tmp_path, repo_root):
    report = _blocker_report(repo_root)
    rows = report["rows"]
    decisions = [
        _decision(rows[0], 1),
        _decision(rows[1], 2, outcome="needs_fix"),
        _decision(rows[2], 3, outcome="defer_to_roadmap"),
    ]
    outcome_path = write_json(
        tmp_path / "synthetic-qa-review-outcome.json",
        _record_payload(report, decisions),
    )

    outcome_report, run_dir = run_synthetic_qa_review_outcome_record(
        synthetic_qa_blocker_report_path=_blocker_report_path(repo_root),
        outcome_path=outcome_path,
        out_dir=tmp_path / "synthetic-qa-review-outcome",
        generated_at="2026-07-03T00:00:00Z",
    )
    persisted_report = SyntheticQABlockerReviewOutcomeReport.model_validate(
        load_json(run_dir / "synthetic_qa_review_outcome_report.json")
    )
    persisted_record = SyntheticQABlockerReviewOutcomeRecord.model_validate(
        load_json(run_dir / "synthetic_qa_review_outcome_record.json")
    )
    history = load_jsonl(run_dir / "synthetic_qa_review_outcome_history.jsonl")

    assert persisted_report.synthetic_qa_review_outcome_report_id == (
        outcome_report.synthetic_qa_review_outcome_report_id
    )
    assert persisted_report.status == "synthetic_qa_review_outcome_recorded_pending_followup"
    assert persisted_report.source_row_count == report["row_count"]
    assert persisted_report.reviewed_row_count == 3
    assert persisted_report.unreviewed_row_count == report["row_count"] - 3
    assert persisted_report.needs_fix_decision_count == 1
    assert persisted_report.deferred_decision_count == 1
    assert persisted_report.unresolved_followup_count == 2
    assert persisted_report.append_only is True
    assert persisted_report.not_authorized_for_calibration is True
    assert persisted_report.lake_write_performed is False
    assert persisted_report.sqlite_write_performed is False
    assert persisted_report.external_writes_performed is False
    assert persisted_report.silent_learning_performed is False
    assert (
        persisted_record.synthetic_qa_blocker_report_id == report["synthetic_qa_blocker_report_id"]
    )
    assert len(history) == 1
    assert history[0]["synthetic_qa_review_outcome_record_id"] == (
        persisted_record.synthetic_qa_review_outcome_record_id
    )
    assert "does not approve budgets" in (
        run_dir / "synthetic_qa_review_outcome_report.md"
    ).read_text(encoding="utf-8")


def test_synthetic_qa_review_outcome_records_full_poc_acceptance(tmp_path, repo_root):
    report = _blocker_report(repo_root)
    decisions = [_decision(row, index) for index, row in enumerate(report["rows"], start=1)]
    outcome_path = write_json(
        tmp_path / "synthetic-qa-review-outcome-all.json",
        _record_payload(report, decisions),
    )

    outcome_report, _ = run_synthetic_qa_review_outcome_record(
        synthetic_qa_blocker_report_path=_blocker_report_path(repo_root),
        outcome_path=outcome_path,
        out_dir=tmp_path / "synthetic-qa-review-outcome-all",
        generated_at="2026-07-03T00:00:00Z",
    )

    assert outcome_report.status == "synthetic_qa_review_outcome_recorded"
    assert outcome_report.accepted_decision_count == report["row_count"]
    assert outcome_report.reviewed_row_count == report["row_count"]
    assert outcome_report.unreviewed_row_count == 0
    assert outcome_report.unresolved_followup_count == 0
    assert outcome_report.budget_submission_authorized is False
    assert outcome_report.training_pipeline_created is False


def test_synthetic_qa_review_outcome_rejects_unknown_rows(tmp_path, repo_root):
    report = _blocker_report(repo_root)
    decision = _decision(report["rows"][0], 1)
    decision["row_id"] = "quality_gate:unknown"
    outcome_path = write_json(
        tmp_path / "synthetic-qa-review-outcome-unknown.json",
        _record_payload(report, [decision]),
    )

    with pytest.raises(ValueError, match="unknown blocker rows"):
        run_synthetic_qa_review_outcome_record(
            synthetic_qa_blocker_report_path=_blocker_report_path(repo_root),
            outcome_path=outcome_path,
            out_dir=tmp_path / "synthetic-qa-review-outcome-unknown",
        )


def test_synthetic_qa_review_outcome_cli_writes_report_and_history(tmp_path, repo_root, capsys):
    report = _blocker_report(repo_root)
    outcome_path = write_json(
        tmp_path / "synthetic-qa-review-outcome-cli.json",
        _record_payload(report, [_decision(report["rows"][0], 1)]),
    )

    code = main(
        [
            "record-synthetic-qa-review-outcome",
            "--synthetic-qa-blocker-report",
            str(_blocker_report_path(repo_root)),
            "--outcome",
            str(outcome_path),
            "--out-dir",
            str(tmp_path / "synthetic-qa-review-outcome-cli"),
            "--generated-at",
            "2026-07-03T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path / "synthetic-qa-review-outcome-cli" / "synthetic_qa_review_outcome_report.json"
    )
    history_path = (
        tmp_path / "synthetic-qa-review-outcome-cli" / "synthetic_qa_review_outcome_history.jsonl"
    )
    outcome_report = SyntheticQABlockerReviewOutcomeReport.model_validate(load_json(report_path))

    assert code == 0
    assert outcome_report.status == "synthetic_qa_review_outcome_recorded_pending_followup"
    assert '"lake_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert len(load_jsonl(history_path)) == 1
