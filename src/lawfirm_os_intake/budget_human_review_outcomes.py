from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetHumanReviewDecisionTemplate,
    BudgetHumanReviewOutcomeCheck,
    BudgetHumanReviewOutcomeDecision,
    BudgetHumanReviewOutcomeRecord,
    BudgetHumanReviewOutcomeReport,
    BudgetHumanReviewPacket,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_HUMAN_REVIEW_OUTCOME_RECORD_FILENAME = "budget_human_review_outcome_record.json"
BUDGET_HUMAN_REVIEW_OUTCOME_HISTORY_FILENAME = "budget_human_review_outcome_history.jsonl"
BUDGET_HUMAN_REVIEW_OUTCOME_REPORT_FILENAME = "budget_human_review_outcome_report.json"
BUDGET_HUMAN_REVIEW_OUTCOME_NOTES_FILENAME = "budget_human_review_outcome_report.md"

READY_BUDGET_HUMAN_REVIEW_PACKET_STATUS = "ready_for_human_budget_review"

BUDGET_HUMAN_REVIEW_OUTCOME_REQUIRED_NEXT_GATES = [
    "append_only_human_budget_decision",
    "orchestrator_human_pause_before_external_action",
    "exception_lake_owner_review_before_admission",
    "reviewed_learning_gate_before_mutation",
    "no_budget_or_appeal_submission_from_intake",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    decision_ids: list[str] | None = None,
    template_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> BudgetHumanReviewOutcomeCheck:
    return BudgetHumanReviewOutcomeCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        decision_ids=decision_ids or [],
        template_ids=template_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _packet_boundary_clear(packet: BudgetHumanReviewPacket) -> bool:
    return (
        packet.lake_write_performed is False
        and packet.sqlite_write_performed is False
        and packet.external_writes_performed is False
        and packet.billing_connector_read_performed is False
        and packet.billing_connector_write_performed is False
        and packet.carrier_portal_write_performed is False
        and packet.email_send_performed is False
        and packet.appeal_submission_performed is False
        and packet.budget_submission_performed is False
        and packet.budget_mutation_performed is False
        and packet.profile_mutation_performed is False
        and packet.template_mutation_performed is False
        and packet.carrier_guideline_mutation_performed is False
        and packet.silent_learning_performed is False
    )


def _record_boundary_clear(record: BudgetHumanReviewOutcomeRecord) -> bool:
    return (
        record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.billing_connector_write_performed is False
        and record.carrier_portal_write_performed is False
        and record.email_send_performed is False
        and record.appeal_submission_performed is False
        and record.budget_submission_performed is False
        and record.budget_mutation_performed is False
        and record.profile_mutation_performed is False
        and record.template_mutation_performed is False
        and record.carrier_guideline_mutation_performed is False
        and record.silent_learning_performed is False
    )


def _template_by_id(
    packet: BudgetHumanReviewPacket,
) -> dict[str, BudgetHumanReviewDecisionTemplate]:
    return {template.template_id: template for template in packet.decision_templates}


def _decisions_with_known_templates(
    decisions: list[BudgetHumanReviewOutcomeDecision],
    template_map: dict[str, BudgetHumanReviewDecisionTemplate],
) -> list[BudgetHumanReviewOutcomeDecision]:
    return [decision for decision in decisions if decision.template_id in template_map]


def _decisions_missing_templates(
    decisions: list[BudgetHumanReviewOutcomeDecision],
    template_map: dict[str, BudgetHumanReviewDecisionTemplate],
) -> list[BudgetHumanReviewOutcomeDecision]:
    return [decision for decision in decisions if decision.template_id not in template_map]


def _decisions_with_disallowed_outcomes(
    decisions: list[BudgetHumanReviewOutcomeDecision],
    template_map: dict[str, BudgetHumanReviewDecisionTemplate],
) -> list[BudgetHumanReviewOutcomeDecision]:
    disallowed: list[BudgetHumanReviewOutcomeDecision] = []
    for decision in _decisions_with_known_templates(decisions, template_map):
        template = template_map[decision.template_id]
        if decision.outcome not in template.allowed_outcomes:
            disallowed.append(decision)
    return disallowed


def _decisions_with_mismatched_areas(
    decisions: list[BudgetHumanReviewOutcomeDecision],
    template_map: dict[str, BudgetHumanReviewDecisionTemplate],
) -> list[BudgetHumanReviewOutcomeDecision]:
    mismatched: list[BudgetHumanReviewOutcomeDecision] = []
    for decision in _decisions_with_known_templates(decisions, template_map):
        template = template_map[decision.template_id]
        if decision.review_area != template.review_area:
            mismatched.append(decision)
    return mismatched


def _decisions_missing_recommendation_refs(
    decisions: list[BudgetHumanReviewOutcomeDecision],
    template_map: dict[str, BudgetHumanReviewDecisionTemplate],
) -> list[BudgetHumanReviewOutcomeDecision]:
    missing: list[BudgetHumanReviewOutcomeDecision] = []
    for decision in _decisions_with_known_templates(decisions, template_map):
        template = template_map[decision.template_id]
        if template.source_recommendation_ids and not set(
            template.source_recommendation_ids
        ).issubset(set(decision.source_recommendation_ids)):
            missing.append(decision)
    return missing


def _decisions_missing_followups(
    decisions: list[BudgetHumanReviewOutcomeDecision],
) -> list[BudgetHumanReviewOutcomeDecision]:
    followup_outcomes = {"appeal", "reopen", "needs_more_information"}
    return [
        decision
        for decision in decisions
        if decision.outcome in followup_outcomes
        and not (
            decision.followup_owner and decision.followup_due_at and decision.required_followups
        )
    ]


def _candidate_lake_event_labels(
    decisions: list[BudgetHumanReviewOutcomeDecision],
) -> list[str]:
    labels = {"budget_human_review_outcome_recorded_candidate"}
    outcomes = {decision.outcome for decision in decisions}
    if "correct" in outcomes:
        labels.add("budget_human_review_correction_candidate")
    if "appeal" in outcomes:
        labels.add("carrier_rejection_appeal_followup_candidate")
    if "write_off" in outcomes:
        labels.add("carrier_financial_outcome_candidate")
    if "route_to_owner_review" in outcomes:
        labels.add("budget_human_review_owner_routing_candidate")
    if "no_learning_change" in outcomes:
        labels.add("budget_learning_no_change_candidate")
    return sorted(labels)


def build_budget_human_review_outcome_report(
    *,
    budget_human_review_packet: BudgetHumanReviewPacket,
    budget_human_review_packet_ref: str,
    outcome_record: BudgetHumanReviewOutcomeRecord,
    history_ref: str,
) -> BudgetHumanReviewOutcomeReport:
    template_map = _template_by_id(budget_human_review_packet)
    missing_templates = _decisions_missing_templates(outcome_record.decisions, template_map)
    disallowed_outcomes = _decisions_with_disallowed_outcomes(
        outcome_record.decisions,
        template_map,
    )
    mismatched_areas = _decisions_with_mismatched_areas(outcome_record.decisions, template_map)
    missing_recommendation_refs = _decisions_missing_recommendation_refs(
        outcome_record.decisions,
        template_map,
    )
    missing_followups = _decisions_missing_followups(outcome_record.decisions)
    required_followups = [
        followup
        for decision in outcome_record.decisions
        for followup in decision.required_followups
    ]
    recorded_outcomes = [decision.outcome for decision in outcome_record.decisions]
    packet_ready_without_writes = (
        budget_human_review_packet.status == READY_BUDGET_HUMAN_REVIEW_PACKET_STATUS
        and _packet_boundary_clear(budget_human_review_packet)
    )
    checks = [
        _check(
            "budget_human_review_packet_ready_without_writes",
            packet_ready_without_writes,
            "Source budget human review packet is ready and has no side effects.",
            artifact_refs=[budget_human_review_packet_ref],
        ),
        _check(
            "outcome_record_matches_packet",
            outcome_record.budget_human_review_packet_id
            == budget_human_review_packet.budget_human_review_packet_id,
            "Outcome record is bound to the supplied budget human review packet.",
            artifact_refs=[budget_human_review_packet_ref],
        ),
        _check(
            "outcome_decisions_match_templates",
            not missing_templates,
            "Every human decision references a decision template in the packet.",
            decision_ids=[decision.decision_id for decision in missing_templates],
            template_ids=[decision.template_id for decision in missing_templates],
            blocking_refs=[decision.template_id for decision in missing_templates],
        ),
        _check(
            "outcome_decisions_allowed_by_templates",
            not disallowed_outcomes,
            "Every human decision outcome is allowed by its packet decision template.",
            decision_ids=[decision.decision_id for decision in disallowed_outcomes],
            template_ids=[decision.template_id for decision in disallowed_outcomes],
            blocking_refs=[
                f"{decision.template_id}:{decision.outcome}" for decision in disallowed_outcomes
            ],
        ),
        _check(
            "outcome_decisions_match_review_areas",
            not mismatched_areas,
            "Every human decision review area matches its packet decision template.",
            decision_ids=[decision.decision_id for decision in mismatched_areas],
            template_ids=[decision.template_id for decision in mismatched_areas],
            blocking_refs=[
                f"{decision.template_id}:{decision.review_area}" for decision in mismatched_areas
            ],
        ),
        _check(
            "outcome_decisions_bind_recommendations",
            not missing_recommendation_refs,
            "Every template-backed decision cites packet recommendation IDs when the template provides them.",
            decision_ids=[decision.decision_id for decision in missing_recommendation_refs],
            template_ids=[decision.template_id for decision in missing_recommendation_refs],
            blocking_refs=[decision.template_id for decision in missing_recommendation_refs],
        ),
        _check(
            "outcome_decisions_have_required_followups",
            not missing_followups,
            "Appeal, reopen, and needs-more-information outcomes include owner, due date, and followups.",
            decision_ids=[decision.decision_id for decision in missing_followups],
            template_ids=[decision.template_id for decision in missing_followups],
            blocking_refs=[decision.decision_id for decision in missing_followups],
        ),
        _check(
            "human_outcome_record_complete",
            bool(
                outcome_record.reviewer_id.strip()
                and outcome_record.reviewed_at.strip()
                and outcome_record.decision_reason.strip()
                and outcome_record.decisions
            ),
            "Human budget review outcome includes reviewer, timestamp, reason, and decisions.",
        ),
        _check(
            "no_side_effects_from_outcome_recording",
            _record_boundary_clear(outcome_record),
            "Recording the outcome did not write Lake/SQLite records, submit budgets or appeals, mutate profiles/templates/budgets/guidelines, or apply learning.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if not packet_ready_without_writes:
        status = "blocked_by_review_packet_evidence"
    elif failed_checks:
        status = "blocked_by_outcome_evidence"
    else:
        status = "budget_human_review_outcome_recorded"

    return BudgetHumanReviewOutcomeReport(
        budget_human_review_outcome_report_id=_stable_id(
            "budgethumanreviewoutcome",
            "|".join(
                [
                    budget_human_review_packet.budget_human_review_packet_id,
                    outcome_record.budget_human_review_outcome_record_id,
                    outcome_record.overall_outcome,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_budget_human_review_packet_ref=budget_human_review_packet_ref,
        budget_human_review_packet_id=(budget_human_review_packet.budget_human_review_packet_id),
        source_budget_human_review_packet_status=budget_human_review_packet.status,
        budget_human_review_outcome_record_id=(
            outcome_record.budget_human_review_outcome_record_id
        ),
        overall_outcome=outcome_record.overall_outcome,
        decision_reason=outcome_record.decision_reason,
        reviewer_id=outcome_record.reviewer_id,
        reviewed_at=outcome_record.reviewed_at,
        decision_count=len(outcome_record.decisions),
        appeal_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "appeal"
        ),
        write_off_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "write_off"
        ),
        correction_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "correct"
        ),
        route_to_owner_decision_count=sum(
            1
            for decision in outcome_record.decisions
            if decision.outcome == "route_to_owner_review"
        ),
        no_learning_change_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "no_learning_change"
        ),
        unresolved_followup_count=len(required_followups),
        recorded_outcomes=recorded_outcomes,
        required_followups=required_followups,
        candidate_lake_event_labels=_candidate_lake_event_labels(outcome_record.decisions),
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=BUDGET_HUMAN_REVIEW_OUTCOME_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_human_review_outcome_report(
    report: BudgetHumanReviewOutcomeReport,
) -> str:
    lines = [
        "# Budget Human Review Outcome Report",
        "",
        f"**Report ID:** {report.budget_human_review_outcome_report_id}",
        f"**Status:** {report.status}",
        f"**Outcome record:** `{report.budget_human_review_outcome_record_id}`",
        f"**Review packet:** `{report.source_budget_human_review_packet_ref}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Human Decisions",
        "",
        f"- Overall outcome: {report.overall_outcome}",
        f"- Decision reason: {report.decision_reason}",
        f"- Decision count: {report.decision_count}",
        f"- Appeal decisions: {report.appeal_decision_count}",
        f"- Write-off decisions: {report.write_off_decision_count}",
        f"- Correction decisions: {report.correction_decision_count}",
        f"- Owner-route decisions: {report.route_to_owner_decision_count}",
        f"- No-learning-change decisions: {report.no_learning_change_decision_count}",
        f"- Unresolved followups: {report.unresolved_followup_count}",
        "",
        "## Candidate Lake Event Labels",
        "",
        *(f"- {label}" for label in report.candidate_lake_event_labels),
        "",
        "## Required Followups",
        "",
    ]
    if not report.required_followups:
        lines.append("- No required followups recorded.")
    for followup in report.required_followups:
        lines.append(f"- {followup}")
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- Non-authoritative: {report.non_authoritative}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Budget submission performed: {report.budget_submission_performed}",
            f"- Appeal submission performed: {report.appeal_submission_performed}",
            f"- Budget mutation performed: {report.budget_mutation_performed}",
            f"- Profile mutation performed: {report.profile_mutation_performed}",
            f"- Template mutation performed: {report.template_mutation_performed}",
            f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report records local append-only budget human review outcome evidence only. It does not submit a budget or appeal, write billing, admit Lake/SQLite records, mutate profiles/templates/budgets/guidelines, write sibling repos, promote canon, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_human_review_outcome_record(
    *,
    budget_human_review_packet_path: str | Path,
    outcome_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetHumanReviewOutcomeReport, Path]:
    packet_path = Path(budget_human_review_packet_path)
    outcome_record_path = Path(outcome_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = BudgetHumanReviewPacket.model_validate(load_json(packet_path))
    outcome_record = BudgetHumanReviewOutcomeRecord.model_validate(load_json(outcome_record_path))
    history_path = run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_HISTORY_FILENAME
    report = build_budget_human_review_outcome_report(
        budget_human_review_packet=packet,
        budget_human_review_packet_ref=str(packet_path),
        outcome_record=outcome_record,
        history_ref=str(history_path),
    )
    write_json(
        run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_RECORD_FILENAME,
        outcome_record.model_dump(mode="json"),
    )
    append_jsonl(history_path, outcome_record.model_dump(mode="json"))
    write_json(
        run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_NOTES_FILENAME).write_text(
        render_budget_human_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir
