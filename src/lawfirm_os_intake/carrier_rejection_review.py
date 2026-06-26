from __future__ import annotations

from pathlib import Path

from .models import (
    CarrierRejectionReviewDecisionTemplate,
    CarrierRejectionReviewPacket,
    CarrierRejectionReviewRecommendation,
    CarrierRejectionReviewRedTeamNote,
    CarrierResponseReconciliationReport,
    RunEvent,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


REVIEW_PACKET_FILENAME = "carrier_rejection_review_packet.json"
REVIEW_NOTES_FILENAME = "carrier_rejection_review_notes.md"
DECISION_TEMPLATE_FILENAME = "carrier_rejection_review_decision_template.json"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _candidate_ids_by_case(report: CarrierResponseReconciliationReport) -> dict[str, list[str]]:
    by_case: dict[str, list[str]] = {
        case.remediation_case_id: [] for case in report.remediation_cases
    }
    for candidate in report.exception_lake_candidates:
        for ref in candidate.structured_refs:
            prefix = "carrier-rejection-case://"
            if not ref.startswith(prefix):
                continue
            case_id = ref.removeprefix(prefix)
            if case_id in by_case:
                by_case[case_id].append(candidate.candidate_id)
    return {case_id: sorted(set(ids)) for case_id, ids in by_case.items()}


def _recommendation_action(status: str, label: str, has_appeal_result: bool) -> str:
    if has_appeal_result:
        return "record_appeal_result"
    if label == "carrier_response_missing_after_sla":
        return "confirm_missing_response_followup"
    if label == "carrier_rejection_unlinked":
        return "link_or_escalate_unlinked_notice"
    if label == "carrier_rejection_parse_failed" or status == "parse_failed":
        return "parse_repair_required"
    if label.startswith("carrier_") and label not in {
        "carrier_rejection_duplicate_notice",
        "carrier_rejection_learning_candidate",
    }:
        return "appeal_review_required"
    return "human_decision_required"


def _recommendation_priority(action: str, exposure: float, gap_count: int) -> str:
    if gap_count:
        return "critical"
    if action in {"confirm_missing_response_followup", "link_or_escalate_unlinked_notice"}:
        return "high"
    if action == "parse_repair_required":
        return "high"
    if exposure > 0:
        return "high"
    if action == "record_appeal_result":
        return "medium"
    return "medium"


def _why_lines(
    case_status: str,
    label: str,
    action: str,
    duplicate_count: int,
    source_ref_count: int,
    exposure: float,
) -> list[str]:
    lines = [
        f"Deterministic reconciliation classified the case as `{label}` with status `{case_status}`.",
        f"The case has {source_ref_count} source ref(s) and current exposure {exposure:.2f}.",
    ]
    if duplicate_count > 1:
        lines.append(
            "Duplicate notices share one idempotency key; review one logical rejection while preserving every notice ID."
        )
    if action == "confirm_missing_response_followup":
        lines.append(
            "The expected-response ledger has no matched carrier response after the configured due date."
        )
    elif action == "link_or_escalate_unlinked_notice":
        lines.append(
            "The notice was captured but could not be linked to a known submitted budget, invoice, appeal, or portal action."
        )
    elif action == "parse_repair_required":
        lines.append(
            "The source was captured but deterministic parsing failed; it must become a reviewed exception, not ignored data."
        )
    elif action == "record_appeal_result":
        lines.append(
            "An appeal result was captured and must be reviewed as append-only outcome evidence."
        )
    elif action == "appeal_review_required":
        lines.append(
            "A human should decide whether to appeal, correct and resubmit, accept a write-down, or request more information."
        )
    return lines


def _recommendations(
    report: CarrierResponseReconciliationReport,
) -> list[CarrierRejectionReviewRecommendation]:
    candidate_ids = _candidate_ids_by_case(report)
    gap_case_ids = {gap.split(":", maxsplit=1)[0] for gap in report.gap_report if ":" in gap}
    items: list[CarrierRejectionReviewRecommendation] = []
    for case in report.remediation_cases:
        has_appeal = bool(case.linked_appeal_result_ids)
        action = _recommendation_action(case.status, case.local_event_label, has_appeal)
        case_gap_count = 1 if case.remediation_case_id in gap_case_ids else 0
        source_channels = sorted({ref.source_channel for ref in case.source_refs})
        exposure = round(case.current_financial_exposure, 2)
        items.append(
            CarrierRejectionReviewRecommendation(
                recommendation_id=_stable_id(
                    "carrierrejrec", f"{report.reconciliation_report_id}|{case.remediation_case_id}"
                ),
                remediation_case_id=case.remediation_case_id,
                local_event_label=case.local_event_label,
                recommended_action=action,  # type: ignore[arg-type]
                priority=_recommendation_priority(action, exposure, case_gap_count),  # type: ignore[arg-type]
                human_owner=case.human_owner,
                followup_due_at=case.followup_due_at,
                financial_exposure=exposure,
                source_ref_count=len(case.source_refs),
                source_channels=source_channels,
                why=_why_lines(
                    case.status,
                    case.local_event_label,
                    action,
                    len(case.duplicate_notice_ids),
                    len(case.source_refs),
                    exposure,
                ),
                required_human_decisions=case.required_human_decisions,
                learning_disposition_candidates=case.learning_disposition_candidates,
                exception_candidate_ids=candidate_ids.get(case.remediation_case_id, []),
            )
        )
    return items


def _red_team_notes(
    report: CarrierResponseReconciliationReport,
) -> list[CarrierRejectionReviewRedTeamNote]:
    notes: list[CarrierRejectionReviewRedTeamNote] = [
        CarrierRejectionReviewRedTeamNote(
            note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|boundary"),
            severity="critical",
            scope="boundary",
            message=(
                "This review packet is not a Lake admission, budget approval, write-down, "
                "appeal submission, client notice, or carrier portal action."
            ),
            recommended_check=(
                "Confirm not_authorized_for_lake_write, not_authorized_for_external_submission, "
                "external_writes_performed=false, and silent_learning_performed=false."
            ),
        ),
        CarrierRejectionReviewRedTeamNote(
            note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|learning-loop"),
            severity="high",
            scope="learning_loop",
            message=(
                "Reviewed outcomes may support candidate guideline or budget-driver changes, "
                "but no profile, rule, or template may mutate silently."
            ),
            recommended_check=(
                "Require before/after behavior, supporting rejection IDs, reviewer, and shadow eval "
                "before any promotion proposal."
            ),
        ),
    ]
    if report.status == "blocked_missing_required_followup":
        notes.append(
            CarrierRejectionReviewRedTeamNote(
                note_id=_stable_id(
                    "carrierrejrt", f"{report.reconciliation_report_id}|followup-gaps"
                ),
                severity="critical",
                scope="capture_completeness",
                remediation_case_ids=[
                    gap.split(":", maxsplit=1)[0] for gap in report.gap_report if ":" in gap
                ],
                message="One or more remediation cases are missing human owner or follow-up due date.",
                recommended_check=(
                    "Assign an owner and due date before treating the reconciliation as ready for review."
                ),
            )
        )
    if report.duplicate_notice_count:
        notes.append(
            CarrierRejectionReviewRedTeamNote(
                note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|dupes"),
                severity="high",
                scope="idempotency",
                remediation_case_ids=[
                    case.remediation_case_id
                    for case in report.remediation_cases
                    if len(case.duplicate_notice_ids) > 1
                ],
                message=(
                    "Duplicate portal/email notices must not double-count exposure, deadlines, "
                    "appeal obligations, or learning pressure."
                ),
                recommended_check="Review duplicate_notice_ids and one-case financial exposure.",
            )
        )
    if report.unlinked_notice_count:
        notes.append(
            CarrierRejectionReviewRedTeamNote(
                note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|unlinked"),
                severity="high",
                scope="linkage",
                remediation_case_ids=[
                    case.remediation_case_id
                    for case in report.remediation_cases
                    if case.local_event_label == "carrier_rejection_unlinked"
                ],
                message=(
                    "Captured but unlinked notices are possible production incidents because "
                    "they may indicate an identifier, portal, or connector mismatch."
                ),
                recommended_check=(
                    "Try deterministic submission, claim, invoice, appeal, and source-record linkage; "
                    "otherwise keep the Lake candidate as an investigation exception."
                ),
            )
        )
    if report.parser_failure_count:
        notes.append(
            CarrierRejectionReviewRedTeamNote(
                note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|parse"),
                severity="high",
                scope="parser_failure",
                remediation_case_ids=[
                    case.remediation_case_id
                    for case in report.remediation_cases
                    if case.local_event_label == "carrier_rejection_parse_failed"
                ],
                message="Parser failures are captured evidence and must not be dropped from review.",
                recommended_check=(
                    "Open a parser-rule candidate with source hash, parser version, and expected field gap."
                ),
            )
        )
    if report.missing_response_count:
        notes.append(
            CarrierRejectionReviewRedTeamNote(
                note_id=_stable_id("carrierrejrt", f"{report.reconciliation_report_id}|missing"),
                severity="high",
                scope="capture_completeness",
                remediation_case_ids=[
                    case.remediation_case_id
                    for case in report.remediation_cases
                    if case.local_event_label == "carrier_response_missing_after_sla"
                ],
                message=(
                    "The capture target is 100%; a missing expected response is an exception "
                    "even if no rejection notice was captured."
                ),
                recommended_check=(
                    "Verify the expected-response ledger, due date, and portal/email/LEDES/manual capture state."
                ),
            )
        )
    return notes


def _decision_templates(
    report: CarrierResponseReconciliationReport,
) -> list[CarrierRejectionReviewDecisionTemplate]:
    templates: list[CarrierRejectionReviewDecisionTemplate] = []
    for case in report.remediation_cases:
        outcomes = [
            "confirm_classification",
            "correct_classification",
            "needs_more_information",
            "human_only",
            "create_learning_candidate",
            "no_learning_change",
        ]
        required = [
            "reviewer_id",
            "reviewed_at",
            "decision_reason",
            "supporting_source_refs_or_structured_refs",
        ]
        if case.local_event_label == "carrier_rejection_unlinked":
            outcomes.extend(["confirm_linkage", "correct_linkage"])
            required.append("linked_submission_or_investigation_reason")
        else:
            outcomes.append("confirm_linkage")
        if case.local_event_label == "carrier_response_missing_after_sla":
            outcomes.extend(["fix_and_resubmit", "close_no_action"])
            required.extend(["followup_owner", "followup_due_at"])
        elif case.local_event_label == "carrier_rejection_parse_failed":
            outcomes.extend(["fix_and_resubmit", "close_no_action"])
            required.append("parser_gap_or_manual_extraction_summary")
        else:
            outcomes.extend(["appeal", "no_appeal", "accept_write_down", "fix_and_resubmit"])
        if case.linked_appeal_result_ids:
            outcomes.append("record_appeal_result")
            required.append("appeal_result_disposition")
        templates.append(
            CarrierRejectionReviewDecisionTemplate(
                remediation_case_id=case.remediation_case_id,
                allowed_outcomes=sorted(set(outcomes)),  # type: ignore[arg-type]
                required_fields=sorted(set(required)),
            )
        )
    return templates


def _packet_status(report: CarrierResponseReconciliationReport) -> str:
    if report.status == "blocked_missing_required_followup":
        return "blocked_missing_required_followup"
    if not report.remediation_cases:
        return "no_cases_to_review"
    return "ready_for_human_review"


def build_carrier_rejection_review_packet(
    report: CarrierResponseReconciliationReport,
    human_readable_review_ref: str | None = None,
) -> CarrierRejectionReviewPacket:
    recommendations = _recommendations(report)
    total_exposure = round(
        sum(case.current_financial_exposure for case in report.remediation_cases), 2
    )
    return CarrierRejectionReviewPacket(
        review_packet_id=_stable_id(
            "carrierrejreview", f"{report.reconciliation_report_id}|human-review"
        ),
        reconciliation_report_id=report.reconciliation_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        status=_packet_status(report),  # type: ignore[arg-type]
        expected_response_count=report.expected_response_count,
        reconciled_response_count=report.reconciled_response_count,
        missing_response_count=report.missing_response_count,
        unlinked_notice_count=report.unlinked_notice_count,
        duplicate_notice_count=report.duplicate_notice_count,
        parser_failure_count=report.parser_failure_count,
        appeal_result_count=report.appeal_result_count,
        remediation_case_count=len(report.remediation_cases),
        total_financial_exposure=total_exposure,
        dry_run_exception_candidate_count=len(report.exception_lake_candidates),
        recommendations=recommendations,
        red_team_notes=_red_team_notes(report),
        decision_templates=_decision_templates(report),
        dry_run_exception_candidate_ids=sorted(
            candidate.candidate_id for candidate in report.exception_lake_candidates
        ),
        gap_report=report.gap_report,
        allowed_reviewer_outcomes=[
            "confirm_classification",
            "correct_classification",
            "confirm_linkage",
            "correct_linkage",
            "needs_more_information",
            "appeal",
            "no_appeal",
            "accept_write_down",
            "fix_and_resubmit",
            "record_appeal_result",
            "human_only",
            "create_learning_candidate",
            "no_learning_change",
        ],
        required_review_sections=[
            "reconciliation_summary",
            "recommendations_with_why",
            "red_team_notes",
            "financial_exposure",
            "decision_template",
            "exception_lake_dry_run_refs",
            "authority_boundaries",
        ],
        human_readable_review_ref=human_readable_review_ref,
        generated_at=now_iso(),
    )


def render_carrier_rejection_review_notes(packet: CarrierRejectionReviewPacket) -> str:
    lines = [
        "# Carrier Rejection Human Review Packet",
        "",
        f"**Review packet ID:** {packet.review_packet_id}",
        f"**Reconciliation report ID:** {packet.reconciliation_report_id}",
        f"**Run ID:** {packet.run_id}",
        f"**Budget proposal ID:** {packet.budget_proposal_id}",
        f"**Status:** {packet.status}",
        "",
        "## Reconciliation Summary",
        "",
        f"- Expected responses: {packet.expected_response_count}",
        f"- Reconciled responses: {packet.reconciled_response_count}",
        f"- Missing after SLA: {packet.missing_response_count}",
        f"- Unlinked notices: {packet.unlinked_notice_count}",
        f"- Duplicate notices collapsed: {packet.duplicate_notice_count}",
        f"- Parser failures: {packet.parser_failure_count}",
        f"- Appeal results captured: {packet.appeal_result_count}",
        f"- Remediation cases: {packet.remediation_case_count}",
        f"- Total current financial exposure: {packet.total_financial_exposure:.2f}",
        f"- Dry-run Exception Lake candidates: {packet.dry_run_exception_candidate_count}",
        "",
        "## Recommendations",
        "",
    ]
    if not packet.recommendations:
        lines.append("- none")
    for rec in packet.recommendations:
        lines.extend(
            [
                f"- Case `{rec.remediation_case_id}`: {rec.recommended_action}; "
                f"priority={rec.priority}; label={rec.local_event_label}; "
                f"owner={rec.human_owner or 'unassigned'}; due={rec.followup_due_at or 'unset'}; "
                f"exposure={rec.financial_exposure:.2f}",
                "  Why:",
                *(f"  - {item}" for item in rec.why),
                "  Human decisions:",
                *(f"  - {item}" for item in rec.required_human_decisions or ["none"]),
                "  Learning candidates:",
                *(f"  - {item}" for item in rec.learning_disposition_candidates or ["none"]),
                "  Dry-run Lake candidate refs:",
                *(f"  - {item}" for item in rec.exception_candidate_ids or ["none"]),
            ]
        )
    lines.extend(["", "## Red-Team Notes", ""])
    for note in packet.red_team_notes:
        case_text = ", ".join(note.remediation_case_ids) or "packet"
        lines.extend(
            [
                f"- [{note.severity}] {note.scope} ({case_text}): {note.message}",
                f"  Check: {note.recommended_check}",
            ]
        )
    lines.extend(["", "## Decision Template", ""])
    if not packet.decision_templates:
        lines.append("- none")
    for item in packet.decision_templates:
        lines.extend(
            [
                f"- Case `{item.remediation_case_id}`",
                f"  Allowed outcomes: {', '.join(item.allowed_outcomes)}",
                f"  Required fields: {', '.join(item.required_fields)}",
                f"  Mutation policy: {item.mutation_policy}",
                f"  External submission authorized: {item.external_submission_authorized}",
                f"  Silent learning allowed: {item.silent_learning_allowed}",
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Candidate only: {packet.candidate_only}",
            f"- Lake write authorized: {not packet.not_authorized_for_lake_write}",
            f"- External submission authorized: {not packet.not_authorized_for_external_submission}",
            f"- External writes performed: {packet.external_writes_performed}",
            f"- Silent learning performed: {packet.silent_learning_performed}",
            f"- Mutation policy: {packet.mutation_policy}",
            f"- Future Orchestrator owner: {packet.target_orchestrator_owner}",
            f"- Future Exception Lake owner: {packet.target_exception_lake_owner}",
            "",
            "This packet does not admit Exception Lake records, submit appeals, approve budgets, accept write-downs, notify a client or carrier, or mutate guideline/profile/template state.",
            "",
        ]
    )
    return "\n".join(lines)


def run_carrier_rejection_review(
    reconciliation_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[CarrierRejectionReviewPacket, Path]:
    report = CarrierResponseReconciliationReport.model_validate(
        load_json(reconciliation_report_path)
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    notes_path = run_dir / REVIEW_NOTES_FILENAME
    packet = build_carrier_rejection_review_packet(report, str(notes_path))

    packet_path = run_dir / REVIEW_PACKET_FILENAME
    decision_template_path = run_dir / DECISION_TEMPLATE_FILENAME
    ledger_path = run_dir / "run_ledger.jsonl"
    write_json(packet_path, packet.model_dump(mode="json"))
    write_json(
        decision_template_path,
        [item.model_dump(mode="json") for item in packet.decision_templates],
    )
    notes_path.write_text(render_carrier_rejection_review_notes(packet), encoding="utf-8")
    append_jsonl(
        ledger_path,
        RunEvent(
            run_id=packet.run_id,
            step_index=1,
            step_name="carrier_rejection_human_review_packet_built",
            status="blocked" if packet.status.startswith("blocked") else "completed",
            timestamp=now_iso(),
            input_refs=[str(reconciliation_report_path)],
            output_refs=[str(packet_path), str(notes_path), str(decision_template_path)],
        ).model_dump(mode="json"),
    )
    return packet, run_dir
