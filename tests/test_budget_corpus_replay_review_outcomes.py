import pytest

from lawfirm_os_intake.budget_calibration_corpus import run_budget_calibration_corpus_audit
from lawfirm_os_intake.budget_corpus_replay import run_budget_corpus_replay_plan
from lawfirm_os_intake.budget_corpus_replay_execution import (
    run_budget_corpus_replay_execution,
)
from lawfirm_os_intake.budget_corpus_replay_review import (
    run_budget_corpus_replay_review,
)
from lawfirm_os_intake.budget_corpus_replay_review_outcomes import (
    run_budget_corpus_replay_review_outcome_record,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetCorpusReplayReviewOutcomeRecord,
    BudgetCorpusReplayReviewOutcomeReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


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


def _executed_review_packet(tmp_path, repo_root):
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
        replay_execution_report_path=execution_dir / "budget_corpus_replay_execution_report.json",
        out_dir=tmp_path / "budget-replay-review",
    )
    recommendation = next(rec for rec in packet.recommendations if rec.replay_case_id == case_id)
    return packet, review_dir / "budget_corpus_replay_review_packet.json", recommendation


def _dry_run_review_packet(tmp_path, repo_root):
    _, plan_path = _write_plan(tmp_path, repo_root)
    _, execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=plan_path,
        out_dir=tmp_path / "budget-replay-execution",
        repo_root=repo_root,
    )
    packet, review_dir = run_budget_corpus_replay_review(
        replay_execution_report_path=execution_dir / "budget_corpus_replay_execution_report.json",
        out_dir=tmp_path / "budget-replay-review",
    )
    recommendation = next(
        rec
        for rec in packet.recommendations
        if rec.recommended_action == "execute_before_learning_review"
    )
    return packet, review_dir / "budget_corpus_replay_review_packet.json", recommendation


def _outcome_payload(packet, recommendation, *, outcome: str, approved_output_refs=None):
    return {
        "schema_version": "0.1",
        "review_outcome_id": f"reviewoutcome-{recommendation.replay_case_id}",
        "review_packet_id": packet.review_packet_id,
        "replay_case_id": recommendation.replay_case_id,
        "reviewer_id": "synthetic-replay-reviewer",
        "reviewer_role": "human_replay_reviewer",
        "reviewed_at": "2026-06-26T00:00:00Z",
        "outcome": outcome,
        "decision_reason": "Synthetic reviewer decision for replay outcome test.",
        "approved_output_refs": approved_output_refs or [],
        "rejected_output_refs": [],
        "evidence_refs": [packet.review_packet_id, recommendation.replay_case_id],
        "required_followups": ["owning repo review before learning use"],
    }


def test_replay_review_outcome_records_approval_append_only(tmp_path, repo_root):
    packet, packet_path, recommendation = _executed_review_packet(tmp_path, repo_root)
    outcome_path = write_json(
        tmp_path / "approve-replay-outcome.json",
        _outcome_payload(
            packet,
            recommendation,
            outcome="approve_fixture_binding",
            approved_output_refs=recommendation.output_refs,
        ),
    )

    report, run_dir = run_budget_corpus_replay_review_outcome_record(
        review_packet_path=packet_path,
        outcome_path=outcome_path,
        out_dir=tmp_path / "budget-replay-review-outcome",
    )
    persisted_record = BudgetCorpusReplayReviewOutcomeRecord.model_validate(
        load_json(run_dir / "budget_corpus_replay_review_outcome_record.json")
    )
    persisted_report = BudgetCorpusReplayReviewOutcomeReport.model_validate(
        load_json(run_dir / "budget_corpus_replay_review_outcome_report.json")
    )
    history = load_jsonl(run_dir / "budget_corpus_replay_review_outcome_history.jsonl")

    assert persisted_report.review_outcome_report_id == report.review_outcome_report_id
    assert report.status == "review_outcome_recorded_learning_still_blocked"
    assert report.fixture_binding_approved is True
    assert report.downstream_learning_gate_allowed is False
    assert report.source_packet_mutated is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert persisted_record.source_review_packet_ref == str(packet_path)
    assert persisted_record.fixture_binding_approved is True
    assert len(history) == 1
    assert history[0]["review_outcome_id"] == persisted_record.review_outcome_id


def test_replay_review_outcome_rejects_disallowed_dry_run_approval(tmp_path, repo_root):
    packet, packet_path, recommendation = _dry_run_review_packet(tmp_path, repo_root)
    outcome_path = write_json(
        tmp_path / "invalid-dry-run-approval.json",
        _outcome_payload(
            packet,
            recommendation,
            outcome="approve_fixture_binding",
            approved_output_refs=["not-generated"],
        ),
    )

    with pytest.raises(ValueError, match="not allowed"):
        run_budget_corpus_replay_review_outcome_record(
            review_packet_path=packet_path,
            outcome_path=outcome_path,
            out_dir=tmp_path / "budget-replay-review-outcome",
        )


def test_replay_review_outcome_rejects_unbound_approved_output(tmp_path, repo_root):
    packet, packet_path, recommendation = _executed_review_packet(tmp_path, repo_root)
    outcome_path = write_json(
        tmp_path / "invalid-unbound-output.json",
        _outcome_payload(
            packet,
            recommendation,
            outcome="approve_fixture_binding",
            approved_output_refs=["unbound-output.json"],
        ),
    )

    with pytest.raises(ValueError, match="not present"):
        run_budget_corpus_replay_review_outcome_record(
            review_packet_path=packet_path,
            outcome_path=outcome_path,
            out_dir=tmp_path / "budget-replay-review-outcome",
        )


def test_replay_review_outcome_cli_writes_report_and_history(tmp_path, repo_root, capsys):
    packet, packet_path, recommendation = _dry_run_review_packet(tmp_path, repo_root)
    outcome_path = write_json(
        tmp_path / "needs-replay-repair.json",
        _outcome_payload(
            packet,
            recommendation,
            outcome="needs_replay_repair",
        ),
    )

    exit_code = main(
        [
            "record-budget-corpus-replay-review-outcome",
            "--review-packet",
            str(packet_path),
            "--outcome",
            str(outcome_path),
            "--out-dir",
            str(tmp_path / "budget-replay-review-outcome"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path
        / "budget-replay-review-outcome"
        / "budget_corpus_replay_review_outcome_report.json"
    )
    history_path = (
        tmp_path
        / "budget-replay-review-outcome"
        / "budget_corpus_replay_review_outcome_history.jsonl"
    )
    notes_path = (
        tmp_path / "budget-replay-review-outcome" / "budget_corpus_replay_review_outcome_report.md"
    )
    report = BudgetCorpusReplayReviewOutcomeReport.model_validate(load_json(report_path))

    assert exit_code == 0
    assert report.status == "review_outcome_rejected_or_needs_repair"
    assert report.append_only is True
    assert report.downstream_learning_gate_allowed is False
    assert '"source_packet_mutated": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert len(load_jsonl(history_path)) == 1
    assert notes_path.is_file()
    assert "does not mutate the review packet" in notes_path.read_text(encoding="utf-8")
