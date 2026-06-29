from lawfirm_os_intake.budget_calibration_readiness import (
    build_budget_calibration_readiness_report,
    run_budget_calibration_readiness_audit,
)
from lawfirm_os_intake.budget_fixture_binding_handoff import (
    build_budget_fixture_binding_handoff_report,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetCalibrationCorpusReport,
    BudgetCalibrationReadinessReport,
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayPlan,
    BudgetCorpusReplayReviewOutcomeReport,
    BudgetCorpusReplayReviewPacket,
    BudgetFixtureBindingCandidate,
    BudgetFixtureBindingCandidateReport,
)
from lawfirm_os_intake.util import load_json, write_json


def _corpus_report():
    return BudgetCalibrationCorpusReport(
        corpus_report_id="corpus-report-1",
        status="synthetic_corpus_ready_for_review",
        corpus_root_ref="examples/synthetic",
        artifact_count=1,
        eligible_artifact_count=1,
        supporting_artifact_count=0,
        blocked_artifact_count=0,
        artifact_kind_counts={"budget_review_fixture": 1},
        calibration_role_counts={"outcome_evidence_fixture": 1},
        artifacts=[
            {
                "artifact_id": "artifact-1",
                "artifact_ref": "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
                "artifact_kind": "budget_review_fixture",
                "calibration_role": "outcome_evidence_fixture",
                "eligibility": "eligible_for_synthetic_calibration_review",
                "sha256": "sha256:" + "a" * 64,
                "data_origin": "synthetic",
                "synthetic_only": True,
                "contains_real_client_data": False,
                "contains_real_matter_data": False,
                "contains_privileged_data": False,
            }
        ],
        checks=[
            {
                "check_id": "synthetic_only",
                "status": "passed",
                "message": "synthetic corpus only",
                "artifact_refs": [],
            }
        ],
        required_next_gates=["human_corpus_review"],
        generated_at="2026-06-26T00:00:00Z",
    )


def _replay_plan():
    return BudgetCorpusReplayPlan(
        replay_plan_id="replay-plan-1",
        source_corpus_report_id="corpus-report-1",
        source_corpus_report_ref="budget_calibration_corpus_report.json",
        source_corpus_status="synthetic_corpus_ready_for_review",
        status="replay_plan_ready_for_review",
        case_count=1,
        planned_case_count=1,
        supporting_case_count=0,
        blocked_case_count=0,
        cases=[
            {
                "replay_case_id": "replay-case-1",
                "source_artifact_id": "artifact-1",
                "source_artifact_ref": "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
                "artifact_kind": "budget_review_fixture",
                "calibration_role": "outcome_evidence_fixture",
                "eligibility": "eligible_for_synthetic_calibration_review",
                "status": "planned_for_replay",
                "command_chain": [
                    {
                        "command_id": "cmd-1",
                        "command": "lawfirm-os-intake record-budget-review",
                        "purpose": "synthetic replay",
                        "expected_output_refs": [
                            ".lawfirm-os-intake/replay/budget_revision_report.json"
                        ],
                    }
                ],
                "expected_outputs": [".lawfirm-os-intake/replay/budget_revision_report.json"],
                "required_next_gates": ["human_replay_review"],
            }
        ],
        checks=[
            {
                "check_id": "plan_ready",
                "status": "passed",
                "message": "plan ready",
                "case_ids": ["replay-case-1"],
            }
        ],
        required_next_gates=["replay_execution"],
        generated_at="2026-06-26T00:00:00Z",
    )


def _execution_report():
    return BudgetCorpusReplayExecutionReport(
        replay_execution_report_id="replay-execution-1",
        replay_plan_id="replay-plan-1",
        replay_plan_ref="budget_corpus_replay_plan.json",
        execution_mode="execute",
        status="execution_passed_for_review",
        replay_run_root=".lawfirm-os-intake/replay",
        selected_case_ids=["replay-case-1"],
        case_count=1,
        executed_case_count=1,
        dry_run_case_count=0,
        skipped_case_count=0,
        blocked_case_count=0,
        failed_case_count=0,
        command_count=1,
        executed_command_count=1,
        failed_command_count=0,
        cases=[
            {
                "replay_case_id": "replay-case-1",
                "source_artifact_ref": "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
                "artifact_kind": "budget_review_fixture",
                "status": "executed_passed",
                "command_results": [
                    {
                        "command_id": "cmd-1",
                        "replay_case_id": "replay-case-1",
                        "status": "executed_passed",
                        "execution_mode": "execute",
                        "planned_command": "lawfirm-os-intake record-budget-review",
                        "resolved_command": "lawfirm-os-intake record-budget-review",
                        "return_code": 0,
                        "output_checks": [
                            {
                                "output_ref": ".lawfirm-os-intake/replay/budget_revision_report.json",
                                "resolved_output_path": ".lawfirm-os-intake/replay/budget_revision_report.json",
                                "exists": True,
                                "sha256": "sha256:" + "b" * 64,
                                "size_bytes": 100,
                            }
                        ],
                    }
                ],
                "output_checks": [
                    {
                        "output_ref": ".lawfirm-os-intake/replay/budget_revision_report.json",
                        "resolved_output_path": ".lawfirm-os-intake/replay/budget_revision_report.json",
                        "exists": True,
                        "sha256": "sha256:" + "b" * 64,
                        "size_bytes": 100,
                    }
                ],
            }
        ],
        checks=[
            {
                "check_id": "execution_passed",
                "status": "passed",
                "message": "execution passed",
                "case_ids": ["replay-case-1"],
                "command_ids": ["cmd-1"],
            }
        ],
        required_next_gates=["human_replay_review"],
        generated_at="2026-06-26T00:00:00Z",
    )


def _review_packet():
    return BudgetCorpusReplayReviewPacket(
        review_packet_id="review-packet-1",
        replay_execution_report_id="replay-execution-1",
        replay_execution_report_ref="budget_corpus_replay_execution_report.json",
        replay_execution_status="execution_passed_for_review",
        replay_execution_mode="execute",
        status="ready_for_human_replay_review",
        recommendation_count=1,
        decision_template_count=1,
        executed_passed_case_count=1,
        dry_run_case_count=0,
        failed_case_count=0,
        blocked_case_count=0,
        supporting_context_case_count=0,
        recommendations=[
            {
                "recommendation_id": "recommendation-1",
                "replay_case_id": "replay-case-1",
                "source_artifact_ref": "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
                "artifact_kind": "budget_review_fixture",
                "replay_case_status": "executed_passed",
                "recommended_action": "review_fixture_binding",
                "priority": "high",
                "why": ["executed replay produced approved outputs"],
                "output_refs": [".lawfirm-os-intake/replay/budget_revision_report.json"],
                "required_human_decisions": ["approve or reject fixture binding"],
            }
        ],
        red_team_notes=[
            {
                "note_id": "redteam-1",
                "severity": "high",
                "scope": "learning_loop",
                "message": "fixture binding is not learning approval",
                "recommended_check": "inspect outputs before fixture update",
                "replay_case_ids": ["replay-case-1"],
            }
        ],
        decision_templates=[
            {
                "decision_template_id": "template-1",
                "replay_case_id": "replay-case-1",
                "source_artifact_ref": "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
                "recommended_action": "review_fixture_binding",
                "allowed_outcomes": ["approve_fixture_binding", "reject_fixture_binding"],
                "recommended_outcome": "approve_fixture_binding",
                "required_fields": ["reviewer_id", "reviewed_at", "decision_reason"],
            }
        ],
        required_next_gates=["append_only_review_outcome"],
        generated_at="2026-06-26T00:00:00Z",
    )


def _outcome_report(*, approved=True):
    return BudgetCorpusReplayReviewOutcomeReport(
        review_outcome_report_id="review-outcome-report-1",
        review_packet_id="review-packet-1",
        replay_execution_report_id="replay-execution-1",
        source_review_packet_ref="budget_corpus_replay_review_packet.json",
        review_outcome_record_id="review-outcome-record-1",
        status=(
            "review_outcome_recorded_learning_still_blocked"
            if approved
            else "review_outcome_rejected_or_needs_repair"
        ),
        replay_case_id="replay-case-1",
        outcome="approve_fixture_binding" if approved else "reject_fixture_binding",
        decision_action="review_fixture_binding",
        decision_reason="synthetic review decision",
        append_only_history_ref="budget_corpus_replay_review_outcome_history.jsonl",
        approved_output_refs=[".lawfirm-os-intake/replay/budget_revision_report.json"]
        if approved
        else [],
        rejected_output_refs=[]
        if approved
        else [".lawfirm-os-intake/replay/budget_revision_report.json"],
        checks=[
            {
                "check_id": "outcome_recorded",
                "status": "passed",
                "message": "outcome recorded",
                "replay_case_ids": ["replay-case-1"],
            }
        ],
        required_next_gates=["fixture_binding_candidate_review"],
        fixture_binding_approved=approved,
        generated_at="2026-06-26T00:00:00Z",
    )


def _candidate_report(*, ready=True):
    candidate = BudgetFixtureBindingCandidate(
        fixture_binding_candidate_id="fixture-binding-candidate-1",
        review_outcome_report_id="review-outcome-report-1",
        review_outcome_record_id="review-outcome-record-1",
        review_packet_id="review-packet-1",
        replay_execution_report_id="replay-execution-1",
        replay_case_id="replay-case-1",
        source_artifact_ref="examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        artifact_kind="budget_review_fixture",
        approved_output_refs=[".lawfirm-os-intake/replay/budget_revision_report.json"]
        if ready
        else [],
        proposed_target_fixture_refs=[
            "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
        ]
        if ready
        else [],
        proposed_binding_action=(
            "bind_replay_outputs_to_synthetic_fixture" if ready else "exclude_from_fixture_binding"
        ),
        status=(
            "candidate_ready_for_fixture_update_review"
            if ready
            else "blocked_pending_approved_outcome"
        ),
        why=["candidate for calibration readiness tests"],
        required_human_steps=["human fixture update review"],
    )
    return BudgetFixtureBindingCandidateReport(
        fixture_binding_candidate_report_id="fixture-binding-candidate-report-1",
        review_packet_id="review-packet-1",
        review_outcome_report_id="review-outcome-report-1",
        review_outcome_record_id="review-outcome-record-1",
        replay_execution_report_id="replay-execution-1",
        replay_case_id="replay-case-1",
        source_review_packet_ref="budget_corpus_replay_review_packet.json",
        source_review_outcome_report_ref="budget_corpus_replay_review_outcome_report.json",
        status=(
            "fixture_binding_candidates_ready_for_review"
            if ready
            else "blocked_pending_approved_outcome"
        ),
        candidate_count=1,
        ready_candidate_count=1 if ready else 0,
        blocked_candidate_count=0 if ready else 1,
        candidates=[candidate],
        checks=[
            {
                "check_id": "candidate_check",
                "status": "passed" if ready else "failed",
                "message": "candidate check",
                "candidate_ids": ["fixture-binding-candidate-1"],
                "replay_case_ids": ["replay-case-1"],
            }
        ],
        required_next_gates=["human_fixture_update_review"],
        generated_at="2026-06-26T00:00:00Z",
    )


def _handoff_report(*, ready=True):
    return build_budget_fixture_binding_handoff_report(
        candidate_report=_candidate_report(ready=ready),
        candidate_report_ref="budget_fixture_binding_candidate_report.json",
    )


def _build_report(*, ready=True):
    return build_budget_calibration_readiness_report(
        corpus_report=_corpus_report(),
        corpus_report_ref="budget_calibration_corpus_report.json",
        replay_plan=_replay_plan(),
        replay_plan_ref="budget_corpus_replay_plan.json",
        replay_execution_report=_execution_report(),
        replay_execution_report_ref="budget_corpus_replay_execution_report.json",
        replay_review_packet=_review_packet(),
        replay_review_packet_ref="budget_corpus_replay_review_packet.json",
        replay_review_outcome_report=_outcome_report(approved=ready),
        replay_review_outcome_report_ref="budget_corpus_replay_review_outcome_report.json",
        fixture_binding_candidate_report=_candidate_report(ready=ready),
        fixture_binding_candidate_report_ref="budget_fixture_binding_candidate_report.json",
        fixture_binding_handoff_report=_handoff_report(ready=ready),
        fixture_binding_handoff_report_ref="budget_fixture_binding_handoff_report.json",
    )


def _write_chain(tmp_path, *, ready=True):
    paths = {
        "corpus_report": write_json(
            tmp_path / "budget_calibration_corpus_report.json",
            _corpus_report().model_dump(mode="json"),
        ),
        "replay_plan": write_json(
            tmp_path / "budget_corpus_replay_plan.json",
            _replay_plan().model_dump(mode="json"),
        ),
        "replay_execution_report": write_json(
            tmp_path / "budget_corpus_replay_execution_report.json",
            _execution_report().model_dump(mode="json"),
        ),
        "replay_review_packet": write_json(
            tmp_path / "budget_corpus_replay_review_packet.json",
            _review_packet().model_dump(mode="json"),
        ),
        "replay_review_outcome_report": write_json(
            tmp_path / "budget_corpus_replay_review_outcome_report.json",
            _outcome_report(approved=ready).model_dump(mode="json"),
        ),
        "fixture_binding_candidate_report": write_json(
            tmp_path / "budget_fixture_binding_candidate_report.json",
            _candidate_report(ready=ready).model_dump(mode="json"),
        ),
        "fixture_binding_handoff_report": write_json(
            tmp_path / "budget_fixture_binding_handoff_report.json",
            _handoff_report(ready=ready).model_dump(mode="json"),
        ),
    }
    return paths


def test_budget_calibration_readiness_ready_chain():
    report = _build_report()

    assert report.status == "ready_for_manual_fixture_update_review"
    assert report.ready_fixture_binding_handoff_count == 1
    assert report.blocked_fixture_binding_handoff_count == 0
    assert report.approved_output_refs == [".lawfirm-os-intake/replay/budget_revision_report.json"]
    assert report.proposed_target_fixture_refs == [
        "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
    ]
    assert all(check.status == "passed" for check in report.checks)
    assert report.manual_fixture_update_review_required is True
    assert report.fixture_update_authorized is False
    assert report.fixture_update_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.downstream_learning_gate_allowed is False
    assert report.calibration_applied is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_budget_calibration_readiness_blocks_rejected_fixture_binding():
    report = _build_report(ready=False)

    assert report.status == "blocked_by_calibration_chain"
    assert report.ready_fixture_binding_handoff_count == 0
    assert report.blocked_fixture_binding_handoff_count == 1
    failed_check_ids = {check.check_id for check in report.checks if check.status == "failed"}
    assert "review_outcome_approves_fixture_binding" in failed_check_ids
    assert "fixture_binding_candidates_ready" in failed_check_ids
    assert "fixture_binding_handoff_ready" in failed_check_ids
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_budget_calibration_readiness_cli_writes_report(tmp_path, capsys):
    paths = _write_chain(tmp_path)

    exit_code = main(
        [
            "audit-budget-calibration-readiness",
            "--corpus-report",
            str(paths["corpus_report"]),
            "--replay-plan",
            str(paths["replay_plan"]),
            "--replay-execution-report",
            str(paths["replay_execution_report"]),
            "--replay-review-packet",
            str(paths["replay_review_packet"]),
            "--replay-review-outcome-report",
            str(paths["replay_review_outcome_report"]),
            "--fixture-binding-candidate-report",
            str(paths["fixture_binding_candidate_report"]),
            "--fixture-binding-handoff-report",
            str(paths["fixture_binding_handoff_report"]),
            "--out-dir",
            str(tmp_path / "budget-calibration-readiness"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path / "budget-calibration-readiness" / "budget_calibration_readiness_report.json"
    )
    notes_path = (
        tmp_path / "budget-calibration-readiness" / "budget_calibration_readiness_report.md"
    )
    report = BudgetCalibrationReadinessReport.model_validate(load_json(report_path))

    assert exit_code == 0
    assert report.status == "ready_for_manual_fixture_update_review"
    assert '"fixture_update_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not update fixtures" in notes_path.read_text(encoding="utf-8")


def test_run_budget_calibration_readiness_audit_blocks_bad_chain(tmp_path):
    paths = _write_chain(tmp_path, ready=False)

    report, run_dir = run_budget_calibration_readiness_audit(
        corpus_report_path=paths["corpus_report"],
        replay_plan_path=paths["replay_plan"],
        replay_execution_report_path=paths["replay_execution_report"],
        replay_review_packet_path=paths["replay_review_packet"],
        replay_review_outcome_report_path=paths["replay_review_outcome_report"],
        fixture_binding_candidate_report_path=paths["fixture_binding_candidate_report"],
        fixture_binding_handoff_report_path=paths["fixture_binding_handoff_report"],
        out_dir=tmp_path / "budget-calibration-readiness",
    )
    persisted = BudgetCalibrationReadinessReport.model_validate(
        load_json(run_dir / "budget_calibration_readiness_report.json")
    )

    assert report.status == "blocked_by_calibration_chain"
    assert persisted.budget_calibration_readiness_report_id == (
        report.budget_calibration_readiness_report_id
    )
    assert persisted.fixture_update_authorized is False
    assert persisted.silent_learning_performed is False
