from lawfirm_os_intake.budget_human_review_outcome_owner_adoption import (
    build_budget_human_review_outcome_owner_adoption_packets,
    build_budget_human_review_outcome_owner_adoption_report,
    run_budget_human_review_outcome_owner_adoption,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetHumanReviewOutcomeCheck,
    BudgetHumanReviewOutcomeDecision,
    BudgetHumanReviewOutcomeOwnerAdoptionReport,
    BudgetHumanReviewOutcomeRecord,
    BudgetHumanReviewOutcomeReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


REQUIRED_OUTCOME_GATES = [
    "append_only_human_budget_decision",
    "orchestrator_human_pause_before_external_action",
    "exception_lake_owner_review_before_admission",
    "reviewed_learning_gate_before_mutation",
    "no_budget_or_appeal_submission_from_intake",
]


def _decision(
    *,
    decision_id,
    template_id,
    review_area,
    outcome,
    followup=None,
):
    payload = {
        "decision_id": decision_id,
        "template_id": template_id,
        "review_area": review_area,
        "outcome": outcome,
        "decision_reason": f"Synthetic decision for {review_area}.",
        "evidence_refs": ["budgethumanreviewpacket_001", template_id],
    }
    if outcome == "correct":
        payload["proposed_correction_refs"] = [f"budget-human-review://correction/{template_id}"]
    if outcome in {"appeal", "reopen", "needs_more_information"}:
        payload["followup_owner"] = "synthetic-budget-reviewer"
        payload["followup_due_at"] = "2026-07-15T00:00:00Z"
        payload["required_followups"] = [followup or f"Resolve {review_area}."]
    if outcome == "write_off":
        payload["financial_amount"] = 1250.0
    if outcome == "route_to_owner_review":
        payload["target_owner_repo"] = "LawFirm-os-exceptions-lake-runtime"
    return BudgetHumanReviewOutcomeDecision(**payload)


def _record():
    decisions = [
        _decision(
            decision_id="decision-correct",
            template_id="template-correct",
            review_area="budget_revision",
            outcome="correct",
        ),
        _decision(
            decision_id="decision-appeal",
            template_id="template-appeal",
            review_area="carrier_rejection",
            outcome="appeal",
            followup="Prepare appeal packet after human authorization.",
        ),
        _decision(
            decision_id="decision-write-off",
            template_id="template-write-off",
            review_area="appeal_result",
            outcome="write_off",
        ),
        _decision(
            decision_id="decision-route",
            template_id="template-route",
            review_area="lake_handoff",
            outcome="route_to_owner_review",
        ),
        _decision(
            decision_id="decision-no-learning",
            template_id="template-no-learning",
            review_area="learning_loop",
            outcome="no_learning_change",
        ),
    ]
    return BudgetHumanReviewOutcomeRecord(
        budget_human_review_outcome_record_id="budget-human-review-outcome-001",
        budget_human_review_packet_id="budgethumanreviewpacket_001",
        source_budget_human_review_packet_ref="budget_human_review_packet.json",
        reviewer_id="synthetic-budget-reviewer",
        reviewer_role="budget_review_owner",
        reviewed_at="2026-06-29T00:00:00Z",
        overall_outcome="correct",
        decision_reason="Synthetic budget human review outcome.",
        decisions=decisions,
    )


def _outcome_report(record, *, ready=True):
    checks = [
        BudgetHumanReviewOutcomeCheck(
            check_id="synthetic_outcome_check",
            status="passed" if ready else "failed",
            message="Synthetic outcome report check.",
            artifact_refs=["budget_human_review_outcome_report.json"],
            blocking_refs=[] if ready else ["budget_human_review_outcome_report.json"],
        )
    ]
    return BudgetHumanReviewOutcomeReport(
        budget_human_review_outcome_report_id="budgethumanreviewoutcomereport_001",
        status=("budget_human_review_outcome_recorded" if ready else "blocked_by_outcome_evidence"),
        source_budget_human_review_packet_ref="budget_human_review_packet.json",
        budget_human_review_packet_id=record.budget_human_review_packet_id,
        source_budget_human_review_packet_status="ready_for_human_budget_review",
        budget_human_review_outcome_record_id=(record.budget_human_review_outcome_record_id),
        overall_outcome=record.overall_outcome,
        decision_reason=record.decision_reason,
        reviewer_id=record.reviewer_id,
        reviewed_at=record.reviewed_at,
        decision_count=len(record.decisions),
        appeal_decision_count=1,
        write_off_decision_count=1,
        correction_decision_count=1,
        route_to_owner_decision_count=1,
        no_learning_change_decision_count=1,
        unresolved_followup_count=1,
        recorded_outcomes=[decision.outcome for decision in record.decisions],
        required_followups=["Prepare appeal packet after human authorization."],
        candidate_lake_event_labels=[
            "budget_human_review_correction_candidate",
            "budget_human_review_outcome_recorded_candidate",
            "carrier_rejection_appeal_followup_candidate",
            "carrier_financial_outcome_candidate",
        ],
        append_only_history_ref="budget_human_review_outcome_history.jsonl",
        checks=checks,
        required_next_gates=REQUIRED_OUTCOME_GATES,
        generated_at="2026-06-29T00:00:00Z",
    )


def test_budget_outcome_owner_adoption_routes_ready_outcomes():
    record = _record()
    outcome_report = _outcome_report(record)
    checks = []
    packets = build_budget_human_review_outcome_owner_adoption_packets(
        outcome_report=outcome_report,
        outcome_report_ref="budget_human_review_outcome_report.json",
        outcome_record=record,
        outcome_record_ref="budget_human_review_outcome_record.json",
        checks=checks,
    )
    report = build_budget_human_review_outcome_owner_adoption_report(
        outcome_report=outcome_report,
        outcome_report_ref="budget_human_review_outcome_report.json",
        outcome_record=record,
        outcome_record_ref="budget_human_review_outcome_record.json",
        packets=packets,
        packet_output_refs=[f"{packet.target_repo}.json" for packet in packets],
        checks=checks,
    )

    assert report.status == "budget_outcome_owner_adoption_packets_ready"
    assert report.packet_count == 3
    assert report.ready_packet_count == 3
    assert report.blocked_packet_count == 0
    assert set(report.target_repos) == {
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
    }
    assert any(
        packet.adoption_focus == "runtime_action_followup_workflow"
        and "Prepare appeal packet after human authorization." in packet.required_followups
        for packet in report.packets
    )
    assert report.github_issue_created is False
    assert report.sibling_repo_write_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.appeal_submission_performed is False
    assert report.silent_learning_performed is False


def test_budget_outcome_owner_adoption_blocks_failed_outcome_report(tmp_path):
    record = _record()
    outcome_report = _outcome_report(record, ready=False)
    record_path = write_json(
        tmp_path / "budget_human_review_outcome_record.json",
        record.model_dump(mode="json"),
    )
    report_path = write_json(
        tmp_path / "budget_human_review_outcome_report.json",
        outcome_report.model_dump(mode="json"),
    )

    report, _ = run_budget_human_review_outcome_owner_adoption(
        budget_human_review_outcome_report_path=report_path,
        budget_human_review_outcome_record_path=record_path,
        out_dir=tmp_path / "owner-adoption",
    )

    assert report.status == "blocked_by_budget_outcome_evidence"
    assert report.ready_packet_count == 0
    assert report.blocked_packet_count == 3
    assert any(
        check.check_id == "budget_human_review_outcome_report_ready_without_writes"
        and check.status == "failed"
        for check in report.checks
    )
    assert report.external_writes_performed is False


def test_budget_outcome_owner_adoption_cli_writes_packets(tmp_path, capsys):
    record = _record()
    outcome_report = _outcome_report(record)
    record_path = write_json(
        tmp_path / "budget_human_review_outcome_record.json",
        record.model_dump(mode="json"),
    )
    report_path = write_json(
        tmp_path / "budget_human_review_outcome_report.json",
        outcome_report.model_dump(mode="json"),
    )

    exit_code = main(
        [
            "build-budget-human-review-outcome-owner-adoption",
            "--budget-human-review-outcome-report",
            str(report_path),
            "--budget-human-review-outcome-record",
            str(record_path),
            "--out-dir",
            str(tmp_path / "owner-adoption-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = BudgetHumanReviewOutcomeOwnerAdoptionReport.model_validate(
        load_json(
            tmp_path
            / "owner-adoption-cli"
            / "budget_human_review_outcome_owner_adoption_report.json"
        )
    )
    packets = load_jsonl(
        tmp_path / "owner-adoption-cli" / "budget_human_review_outcome_owner_adoption_packets.jsonl"
    )

    assert exit_code == 0
    assert report.status == "budget_outcome_owner_adoption_packets_ready"
    assert len(packets) == 3
    assert '"ready_packet_count": 3' in captured.out
    assert '"github_issue_created": false' in captured.out
    assert '"sibling_repo_write_performed": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert '"appeal_submission_performed": false' in captured.out
    assert (
        tmp_path
        / "owner-adoption-cli"
        / "budget_human_review_outcome_owner_packets"
        / "orchestrator.budget_human_review_outcome_owner_packet.json"
    ).is_file()
