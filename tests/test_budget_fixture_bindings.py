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
from lawfirm_os_intake.budget_fixture_bindings import (
    build_budget_fixture_binding_candidate_report,
    run_budget_fixture_binding_candidates,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetFixtureBindingCandidateReport,
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


def _planned_case_id(plan, kind: str):
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


def _outcome_payload(packet, recommendation, *, outcome: str, approved_output_refs=None):
    return {
        "schema_version": "0.1",
        "review_outcome_id": f"reviewoutcome-{recommendation.replay_case_id}-{outcome}",
        "review_packet_id": packet.review_packet_id,
        "replay_case_id": recommendation.replay_case_id,
        "reviewer_id": "synthetic-replay-reviewer",
        "reviewer_role": "human_replay_reviewer",
        "reviewed_at": "2026-06-26T00:00:00Z",
        "outcome": outcome,
        "decision_reason": "Synthetic reviewer decision for fixture binding proposal test.",
        "approved_output_refs": approved_output_refs or [],
        "rejected_output_refs": [],
        "evidence_refs": [packet.review_packet_id, recommendation.replay_case_id],
        "required_followups": ["fixture update review before learning use"],
    }


def _review_outcome_report(tmp_path, repo_root, *, outcome: str, approve_outputs: bool):
    packet, packet_path, recommendation = _executed_review_packet(tmp_path, repo_root)
    outcome_path = write_json(
        tmp_path / f"{outcome}.json",
        _outcome_payload(
            packet,
            recommendation,
            outcome=outcome,
            approved_output_refs=recommendation.output_refs if approve_outputs else [],
        ),
    )
    outcome_report, outcome_dir = run_budget_corpus_replay_review_outcome_record(
        review_packet_path=packet_path,
        outcome_path=outcome_path,
        out_dir=tmp_path / f"budget-replay-review-outcome-{outcome}",
    )
    return (
        packet,
        packet_path,
        recommendation,
        outcome_report,
        outcome_dir / "budget_corpus_replay_review_outcome_report.json",
    )


def test_fixture_binding_candidates_from_approved_replay_outcome(tmp_path, repo_root):
    _, packet_path, recommendation, outcome_report, outcome_report_path = _review_outcome_report(
        tmp_path,
        repo_root,
        outcome="approve_fixture_binding",
        approve_outputs=True,
    )

    report, run_dir = run_budget_fixture_binding_candidates(
        review_packet_path=packet_path,
        review_outcome_report_path=outcome_report_path,
        out_dir=tmp_path / "budget-fixture-bindings",
    )
    persisted = BudgetFixtureBindingCandidateReport.model_validate(
        load_json(run_dir / "budget_fixture_binding_candidate_report.json")
    )
    candidates = load_jsonl(run_dir / "budget_fixture_binding_candidates.jsonl")
    candidate = persisted.candidates[0]

    assert (
        persisted.fixture_binding_candidate_report_id == report.fixture_binding_candidate_report_id
    )
    assert report.status == "fixture_binding_candidates_ready_for_review"
    assert report.ready_candidate_count == 1
    assert candidate.status == "candidate_ready_for_fixture_update_review"
    assert candidate.proposed_binding_action == "bind_replay_outputs_to_synthetic_fixture"
    assert candidate.source_artifact_ref == recommendation.source_artifact_ref
    assert candidate.proposed_target_fixture_refs == [recommendation.source_artifact_ref]
    assert candidate.approved_output_refs == outcome_report.approved_output_refs
    assert len(candidates) == 1
    assert candidates[0]["fixture_binding_candidate_id"] == candidate.fixture_binding_candidate_id
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.downstream_learning_gate_allowed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_fixture_binding_candidates_block_without_approval(tmp_path, repo_root):
    _, packet_path, _, _, outcome_report_path = _review_outcome_report(
        tmp_path,
        repo_root,
        outcome="reject_fixture_binding",
        approve_outputs=False,
    )

    report, _ = run_budget_fixture_binding_candidates(
        review_packet_path=packet_path,
        review_outcome_report_path=outcome_report_path,
        out_dir=tmp_path / "budget-fixture-bindings",
    )
    candidate = report.candidates[0]

    assert report.status == "blocked_pending_approved_outcome"
    assert report.ready_candidate_count == 0
    assert report.blocked_candidate_count == 1
    assert candidate.status == "blocked_pending_approved_outcome"
    assert candidate.proposed_binding_action == "exclude_from_fixture_binding"
    assert candidate.proposed_target_fixture_refs == []
    assert report.fixture_binding_applied is False
    assert report.silent_learning_performed is False


def test_fixture_binding_candidates_block_approval_without_outputs(tmp_path, repo_root):
    packet, packet_path, recommendation, outcome_report, outcome_report_path = (
        _review_outcome_report(
            tmp_path,
            repo_root,
            outcome="approve_fixture_binding",
            approve_outputs=True,
        )
    )
    malformed_report = outcome_report.model_copy(update={"approved_output_refs": []})

    report = build_budget_fixture_binding_candidate_report(
        packet=packet,
        outcome_report=malformed_report,
        review_packet_ref=str(packet_path),
        review_outcome_report_ref=str(outcome_report_path),
    )
    candidate = report.candidates[0]

    assert recommendation.output_refs
    assert report.status == "blocked_missing_approved_outputs"
    assert candidate.status == "blocked_missing_approved_outputs"
    assert candidate.approved_output_refs == []
    assert candidate.proposed_target_fixture_refs == []
    assert any(
        check.check_id == "approved_outputs_present" and check.status == "failed"
        for check in report.checks
    )
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_fixture_binding_candidate_cli_writes_report(tmp_path, repo_root, capsys):
    _, packet_path, _, _, outcome_report_path = _review_outcome_report(
        tmp_path,
        repo_root,
        outcome="approve_fixture_binding",
        approve_outputs=True,
    )

    exit_code = main(
        [
            "propose-budget-fixture-bindings",
            "--review-packet",
            str(packet_path),
            "--review-outcome-report",
            str(outcome_report_path),
            "--out-dir",
            str(tmp_path / "budget-fixture-bindings"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path / "budget-fixture-bindings" / "budget_fixture_binding_candidate_report.json"
    )
    notes_path = tmp_path / "budget-fixture-bindings" / "budget_fixture_binding_candidate_report.md"
    report = BudgetFixtureBindingCandidateReport.model_validate(load_json(report_path))

    assert exit_code == 0
    assert report.status == "fixture_binding_candidates_ready_for_review"
    assert '"fixture_binding_applied": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "candidate fixture-binding proposal only" in notes_path.read_text(encoding="utf-8")
