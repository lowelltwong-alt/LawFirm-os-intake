from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import (
    BudgetActualCodeComparison,
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetLine,
    BudgetPreconditionReport,
    BudgetProposal,
    CarrierRejectionCaptureSourceBundle,
    CarrierRejectionDecisionLedgerReport,
    CarrierRejectionSourceRef,
    EvidenceRef,
    HumanConfirmation,
    IntakePreflightPacket,
    OrchestratorOwnerReviewBudgetActualLine,
    OrchestratorOwnerReviewBudgetPreconditions,
    OrchestratorOwnerReviewCarrierAppeal,
    OrchestratorOwnerReviewCarrierAppealResult,
    OrchestratorOwnerReviewCarrierRejectionNotice,
    OrchestratorOwnerReviewHumanConfirmation,
    OrchestratorOwnerReviewRequest,
    OrchestratorOwnerReviewSourceRef,
)
from .util import digest_json, load_json, now_iso, write_json


ORCHESTRATOR_OWNER_REVIEW_REQUEST_FILENAME = "orchestrator_owner_review_request.json"
ORCHESTRATOR_OWNER_REVIEW_REQUEST_NOTES_FILENAME = "orchestrator_owner_review_request.md"
REQUEST_SCHEMA_VERSION = "intake_owner_review_request.v0_1"
WORKFLOW_LABEL = "orchestrator.local.intake_to_budget_owner_review"
MONEY_QUANT = Decimal("0.01")

_PARTY_GAP_TERMS = (
    "party count",
    "number of parties",
    "parties unknown",
    "unknown parties",
    "principal party",
    "party role",
    "role ambiguity",
    "entity relationship",
    "joint employer",
    "affiliate",
)

_COMPLEXITY_GAP_TERMS = (
    "complexity",
    "claim count",
    "class",
    "collective",
    "damages",
    "depositions",
    "discovery",
    "esi",
    "custodian",
    "expert",
    "vendor",
    "critical gap",
)


def _stable_request_id(*values: object) -> str:
    digest = digest_json([str(value) for value in values]).split(":", maxsplit=1)[1]
    return f"intake-owner-review-request-{digest[:20]}"


def _money(value: float | int | str | Decimal | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(MONEY_QUANT)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"money value is not decimal-compatible: {value!r}") from exc


def _money_str(value: float | int | str | Decimal | None) -> str:
    return str(_money(value))


def _bare_sha256(value: str) -> str:
    bare = value.removeprefix("sha256:")
    if len(bare) != 64 or any(char not in "0123456789abcdef" for char in bare):
        raise ValueError(f"source hash must be sha256:64hex or bare 64hex: {value}")
    return bare


def _evidence_ref_string(ref: EvidenceRef) -> str:
    return f"{ref.source_id}#{ref.segment_id}"


def _evidence_ref_strings(refs: Iterable[EvidenceRef]) -> list[str]:
    return sorted({_evidence_ref_string(ref) for ref in refs})


def _confirmation_status(
    *,
    confirmation: HumanConfirmation,
    confirmed: bool,
) -> str:
    if confirmed:
        return "confirmed"
    if confirmation.status == "declined_or_referred":
        return "declined_referred"
    if confirmation.status in {
        "needs_more_information",
        "unknown",
        "human_only",
        "declined",
    }:
        return confirmation.status
    return "pending"


def _build_human_confirmations(
    confirmation: HumanConfirmation,
    budget: BudgetProposal,
) -> dict[str, OrchestratorOwnerReviewHumanConfirmation]:
    decision_refs = _evidence_ref_strings(confirmation.decision_evidence_refs)
    party_refs = _evidence_ref_strings(
        ref for party in confirmation.confirmed_parties for ref in party.evidence_refs
    )
    review_ref = f"human-confirmation://{confirmation.confirmation_id}"
    budget_ref = f"budget-proposal://{budget.budget_proposal_id}"
    return {
        "confirm_matter_family": OrchestratorOwnerReviewHumanConfirmation(
            status=_confirmation_status(
                confirmation=confirmation,
                confirmed=confirmation.status == "confirmed"
                and bool(confirmation.confirmed_matter_family),
            ),
            human_review_ref=review_ref,
            evidence_refs=decision_refs,
        ),
        "confirm_representation_posture": OrchestratorOwnerReviewHumanConfirmation(
            status=_confirmation_status(
                confirmation=confirmation,
                confirmed=confirmation.status == "confirmed"
                and bool(confirmation.confirmed_representation_posture),
            ),
            human_review_ref=review_ref,
            evidence_refs=decision_refs,
        ),
        "confirm_principal_party_roles": OrchestratorOwnerReviewHumanConfirmation(
            status=_confirmation_status(
                confirmation=confirmation,
                confirmed=confirmation.status == "confirmed"
                and bool(confirmation.confirmed_parties),
            ),
            human_review_ref=review_ref,
            evidence_refs=party_refs or decision_refs,
        ),
        "approve_budget_proposal_before_external_submission": (
            OrchestratorOwnerReviewHumanConfirmation(
                status="pending",
                human_review_ref=budget_ref,
                evidence_refs=[],
            )
        ),
        "approve_exception_lake_handoff_before_admission": (
            OrchestratorOwnerReviewHumanConfirmation(
                status="pending",
                human_review_ref=(
                    f"exception-lake-handoff-manifest://{budget.budget_proposal_id}/candidate-only"
                ),
                evidence_refs=[],
            )
        ),
    }


def _gap_text(packet: IntakePreflightPacket, budget: BudgetProposal) -> str:
    pieces = [
        *packet.missing_information,
        *budget.unknowns,
        *[
            " ".join(str(value) for value in candidate.model_dump(mode="json").values())
            for candidate in packet.missing_information_candidates
        ],
    ]
    return " ".join(pieces).casefold()


def _has_gap(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _build_budget_preconditions(
    *,
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    budget: BudgetProposal,
    budget_precondition_report: BudgetPreconditionReport | None,
) -> OrchestratorOwnerReviewBudgetPreconditions:
    gap_text = _gap_text(packet, budget)
    critical_le_gap = (
        budget_precondition_report is not None
        and budget_precondition_report.labor_employment_critical_gap_count > 0
    )
    matter_family_confirmed = confirmation.status == "confirmed" and bool(
        confirmation.confirmed_matter_family
    )
    posture_confirmed = confirmation.status == "confirmed" and bool(
        confirmation.confirmed_representation_posture
    )
    principal_roles_confirmed = confirmation.status == "confirmed" and bool(
        confirmation.confirmed_parties
    )
    return OrchestratorOwnerReviewBudgetPreconditions(
        party_count_known=principal_roles_confirmed and not _has_gap(gap_text, _PARTY_GAP_TERMS),
        complexity_known=(
            budget.pricing_status != "insufficient_information"
            and not critical_le_gap
            and not _has_gap(gap_text, _COMPLEXITY_GAP_TERMS)
        ),
        matter_family_confirmed=matter_family_confirmed,
        representation_posture_confirmed=posture_confirmed,
        principal_roles_confirmed=principal_roles_confirmed,
    )


def _source_coverage(read_state: str, availability_state: str) -> str:
    if availability_state == "missing" or read_state == "missing":
        return "missing"
    if availability_state in {"duplicate", "unreadable"} or read_state in {"unread", "unreadable"}:
        return "partial"
    return "full"


def _preflight_source_refs(packet: IntakePreflightPacket) -> list[OrchestratorOwnerReviewSourceRef]:
    segments_by_source: dict[str, list[str]] = {}
    for segment in packet.segments:
        segments_by_source.setdefault(segment.source_id, []).append(segment.segment_id)
    refs: list[OrchestratorOwnerReviewSourceRef] = []
    for source in packet.source_inventory:
        refs.append(
            OrchestratorOwnerReviewSourceRef(
                source_ref_id=source.source_id,
                sha256=_bare_sha256(source.source_sha256),
                segment_refs=sorted(segments_by_source.get(source.source_id, [])),
                coverage=_source_coverage(source.read_state, source.availability_state),  # type: ignore[arg-type]
            )
        )
    return refs


def _carrier_source_ref_id(ref: CarrierRejectionSourceRef) -> str:
    return f"{ref.source_id}#{ref.source_record_id}"


def _carrier_segment_refs(ref: CarrierRejectionSourceRef) -> list[str]:
    refs = [ref.source_record_id]
    if ref.message_id:
        refs.append(ref.message_id)
    if ref.portal_status_id:
        refs.append(ref.portal_status_id)
    if ref.row_ref:
        refs.append(ref.row_ref)
    if ref.attachment_id:
        refs.append(ref.attachment_id)
    return sorted(set(refs))


def _source_refs_from_carrier_refs(
    refs: Iterable[CarrierRejectionSourceRef],
) -> list[OrchestratorOwnerReviewSourceRef]:
    result: list[OrchestratorOwnerReviewSourceRef] = []
    seen: set[str] = set()
    for ref in refs:
        source_ref_id = _carrier_source_ref_id(ref)
        if source_ref_id in seen:
            continue
        seen.add(source_ref_id)
        result.append(
            OrchestratorOwnerReviewSourceRef(
                source_ref_id=source_ref_id,
                sha256=_bare_sha256(ref.content_sha256),
                segment_refs=_carrier_segment_refs(ref),
                coverage="partial",
            )
        )
    return result


def _combine_source_refs(
    *groups: Iterable[OrchestratorOwnerReviewSourceRef],
) -> list[OrchestratorOwnerReviewSourceRef]:
    by_id: dict[str, OrchestratorOwnerReviewSourceRef] = {}
    for group in groups:
        for ref in group:
            existing = by_id.get(ref.source_ref_id)
            if existing is not None and existing.sha256 != ref.sha256:
                raise ValueError(
                    f"source_ref_id collision with different hashes: {ref.source_ref_id}"
                )
            by_id[ref.source_ref_id] = ref
    return [by_id[key] for key in sorted(by_id)]


def _line_code(line: BudgetLine) -> str:
    return line.external_code_candidate or line.expense_code or line.task_id


def _line_total(line: BudgetLine) -> Decimal:
    return _money(line.estimated_fees) + _money(line.estimated_expenses)


def _projection_maps(budget: BudgetProposal) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    by_code: dict[str, Decimal] = {}
    by_phase: dict[str, Decimal] = {}
    projection = budget.carrier_compliant_projection
    if projection is None:
        for line in budget.lines:
            total = _line_total(line)
            by_code[_line_code(line)] = by_code.get(_line_code(line), Decimal("0.00")) + total
            by_phase[line.phase_id] = by_phase.get(line.phase_id, Decimal("0.00")) + total
        return by_code, by_phase
    for line in projection.lines:
        code = line.external_code_candidate or line.expense_code or line.task_id
        total = _money(line.compliant_line_total)
        by_code[code] = by_code.get(code, Decimal("0.00")) + total
        by_phase[line.phase_id] = by_phase.get(line.phase_id, Decimal("0.00")) + total
    return by_code, by_phase


def _write_down_maps(
    ledger: CarrierRejectionDecisionLedgerReport | None,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    by_code: dict[str, Decimal] = {}
    by_phase: dict[str, Decimal] = {}
    if ledger is None:
        return by_code, by_phase
    for event in ledger.events:
        if event.event_kind != "carrier_financial_outcome_recorded":
            continue
        amount = _money(event.write_down_amount or event.remaining_write_down_amount)
        if amount == 0:
            continue
        if event.external_code_candidate:
            by_code[event.external_code_candidate] = (
                by_code.get(event.external_code_candidate, Decimal("0.00")) + amount
            )
        if event.phase_id:
            by_phase[event.phase_id] = by_phase.get(event.phase_id, Decimal("0.00")) + amount
    return by_code, by_phase


def _variance_driver(row: BudgetActualCodeComparison | BudgetActualPhaseComparison) -> str:
    if row.variance_driver_candidates:
        return row.variance_driver_candidates[0]
    return row.status


def _actual_lines_from_report(
    *,
    report: BudgetActualComparisonReport,
    budget: BudgetProposal,
    ledger: CarrierRejectionDecisionLedgerReport | None,
) -> list[OrchestratorOwnerReviewBudgetActualLine]:
    compliant_by_code, compliant_by_phase = _projection_maps(budget)
    write_down_by_code, write_down_by_phase = _write_down_maps(ledger)
    lines: list[OrchestratorOwnerReviewBudgetActualLine] = []
    if report.code_comparisons:
        for row in report.code_comparisons:
            phase = row.phase_id or "unresolved_phase"
            lines.append(
                OrchestratorOwnerReviewBudgetActualLine(
                    line_id=f"budget-actual-code-{row.code}",
                    budget_phase=phase,
                    budget_task_code=row.code,
                    proposed_budget_amount=_money_str(row.budgeted_total),
                    carrier_compliant_projection_amount=_money_str(
                        compliant_by_code.get(row.code, _money(row.budgeted_total))
                    ),
                    actual_billed_amount=_money_str(row.actual_total),
                    write_down_or_disallowed_amount=_money_str(
                        write_down_by_code.get(
                            row.code,
                            write_down_by_phase.get(phase, Decimal("0.00")),
                        )
                    ),
                    variance_driver_candidate=_variance_driver(row),
                )
            )
        return lines
    for row in report.phase_comparisons:
        code = "+".join(row.external_code_candidates) or row.phase_id
        lines.append(
            OrchestratorOwnerReviewBudgetActualLine(
                line_id=f"budget-actual-phase-{row.phase_id}",
                budget_phase=row.phase_id,
                budget_task_code=code,
                proposed_budget_amount=_money_str(row.budgeted_total),
                carrier_compliant_projection_amount=_money_str(
                    compliant_by_phase.get(row.phase_id, _money(row.budgeted_total))
                ),
                actual_billed_amount=_money_str(row.actual_total),
                write_down_or_disallowed_amount=_money_str(
                    write_down_by_phase.get(row.phase_id, Decimal("0.00"))
                ),
                variance_driver_candidate=_variance_driver(row),
            )
        )
    return lines


def _actual_lines_from_budget(
    budget: BudgetProposal,
) -> list[OrchestratorOwnerReviewBudgetActualLine]:
    compliant_by_code, _ = _projection_maps(budget)
    lines: list[OrchestratorOwnerReviewBudgetActualLine] = []
    for index, line in enumerate(budget.lines, start=1):
        code = _line_code(line)
        proposed = _line_total(line)
        lines.append(
            OrchestratorOwnerReviewBudgetActualLine(
                line_id=f"budget-line-{index}-{code}",
                budget_phase=line.phase_id,
                budget_task_code=code,
                proposed_budget_amount=_money_str(proposed),
                carrier_compliant_projection_amount=_money_str(
                    compliant_by_code.get(code, proposed)
                ),
                actual_billed_amount="0.00",
                write_down_or_disallowed_amount="0.00",
                variance_driver_candidate="actuals_not_supplied",
            )
        )
    return lines


def _channel(source_ref: CarrierRejectionSourceRef | None) -> str:
    if source_ref is None:
        return "unknown"
    return {
        "portal_status": "carrier_portal",
        "portal_export": "carrier_portal",
        "email_notice": "email",
        "ledes_response": "ledes_response",
        "returned_workbook": "returned_workbook",
        "appeal_correspondence": "appeal_correspondence",
        "manual_entry": "manual_entry",
    }[source_ref.source_channel]


def _appeal_results_by_notice(
    bundle: CarrierRejectionCaptureSourceBundle,
) -> dict[str, list[OrchestratorOwnerReviewCarrierAppealResult]]:
    results: dict[str, list[OrchestratorOwnerReviewCarrierAppealResult]] = {}
    for result in bundle.appeal_results:
        results.setdefault(result.related_notice_id, []).append(
            OrchestratorOwnerReviewCarrierAppealResult(
                result_id=result.appeal_result_id,
                result=result.result,
                received_at=result.status_timestamp,
            )
        )
    return results


def _financial_outcome_for_notice(
    notice_id: str,
    ledger: CarrierRejectionDecisionLedgerReport | None,
) -> str | None:
    if ledger is None:
        return None
    outcomes = [
        event
        for event in ledger.events
        if notice_id in event.notice_ids
        and event.event_kind == "carrier_financial_outcome_recorded"
    ]
    if not outcomes:
        return None
    recovered = sum(_money(event.recovered_amount) for event in outcomes)
    write_down = sum(_money(event.write_down_amount) for event in outcomes)
    return f"recovered={recovered}; write_down={write_down}"


def _carrier_notices_from_bundle(
    *,
    bundle: CarrierRejectionCaptureSourceBundle,
    ledger: CarrierRejectionDecisionLedgerReport | None,
) -> list[OrchestratorOwnerReviewCarrierRejectionNotice]:
    appeal_results = _appeal_results_by_notice(bundle)
    notices: list[OrchestratorOwnerReviewCarrierRejectionNotice] = []
    for notice in bundle.notices:
        first_source = notice.source_refs[0] if notice.source_refs else None
        source_ref_id = _carrier_source_ref_id(first_source) if first_source else notice.notice_id
        notices.append(
            OrchestratorOwnerReviewCarrierRejectionNotice(
                notice_id=notice.notice_id,
                channel=_channel(first_source),
                source_ref_id=source_ref_id,
                notice_title=notice.reason_code or notice.response_type,
                reason_summary=notice.reason_text_excerpt,
                carrier_reason_code=notice.reason_code or notice.response_type,
                matched_budget_line_id=(
                    notice.line_id
                    or notice.external_code_candidate
                    or notice.expense_code
                    or notice.task_id
                    or notice.phase_id
                    or ""
                ),
                appeal=OrchestratorOwnerReviewCarrierAppeal(
                    requested=False,
                    human_authorization_ref=None,
                ),
                appeal_results=appeal_results.get(notice.notice_id, []),
                financial_outcome=_financial_outcome_for_notice(notice.notice_id, ledger),
            )
        )
    return notices


def _carrier_notices_from_ledger(
    ledger: CarrierRejectionDecisionLedgerReport,
) -> list[OrchestratorOwnerReviewCarrierRejectionNotice]:
    notices: list[OrchestratorOwnerReviewCarrierRejectionNotice] = []
    seen: set[str] = set()
    for event in ledger.events:
        if event.event_kind not in {
            "carrier_rejection_notice_captured",
            "carrier_rejection_unlinked_notice",
            "carrier_rejection_parse_failed",
            "carrier_response_missing_after_sla",
        }:
            continue
        notice_id = event.notice_ids[0] if event.notice_ids else event.decision_ledger_event_id
        if notice_id in seen:
            continue
        seen.add(notice_id)
        first_source = event.source_refs[0] if event.source_refs else None
        source_ref_id = _carrier_source_ref_id(first_source) if first_source else notice_id
        notices.append(
            OrchestratorOwnerReviewCarrierRejectionNotice(
                notice_id=notice_id,
                channel=_channel(first_source),
                source_ref_id=source_ref_id,
                notice_title=event.local_event_label,
                reason_summary=event.decision_status,
                carrier_reason_code=event.local_event_label,
                matched_budget_line_id=(
                    event.external_code_candidate or event.task_id or event.phase_id or ""
                ),
                appeal=OrchestratorOwnerReviewCarrierAppeal(
                    requested=False,
                    human_authorization_ref=None,
                ),
                appeal_results=[],
                financial_outcome=None,
            )
        )
    return notices


def _bind_synthetic_placeholders(value: object, budget: BudgetProposal) -> object:
    if isinstance(value, dict):
        replaced = {}
        for key, item in value.items():
            if key == "budget_proposal_id" and item == "filled-by-test-budget-proposal":
                replaced[key] = budget.budget_proposal_id
            elif key == "preflight_packet_id" and item == "filled-by-test-preflight-packet":
                replaced[key] = budget.preflight_packet_id
            else:
                replaced[key] = _bind_synthetic_placeholders(item, budget)
        return replaced
    if isinstance(value, list):
        return [_bind_synthetic_placeholders(item, budget) for item in value]
    return value


def _load_budget_precondition_report(
    path: str | Path | None,
) -> BudgetPreconditionReport | None:
    if path is None:
        return None
    return BudgetPreconditionReport.model_validate(load_json(path))


def _load_actual_report(path: str | Path | None) -> BudgetActualComparisonReport | None:
    if path is None:
        return None
    return BudgetActualComparisonReport.model_validate(load_json(path))


def _load_carrier_ledger(
    path: str | Path | None,
) -> CarrierRejectionDecisionLedgerReport | None:
    if path is None:
        return None
    return CarrierRejectionDecisionLedgerReport.model_validate(load_json(path))


def _load_carrier_bundle(
    path: str | Path | None,
    budget: BudgetProposal,
) -> CarrierRejectionCaptureSourceBundle | None:
    if path is None:
        return None
    raw = _bind_synthetic_placeholders(load_json(path), budget)
    return CarrierRejectionCaptureSourceBundle.model_validate(raw)


def _validate_lineage(
    *,
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    budget: BudgetProposal,
    budget_precondition_report: BudgetPreconditionReport | None,
    actual_report: BudgetActualComparisonReport | None,
    carrier_ledger: CarrierRejectionDecisionLedgerReport | None,
    carrier_bundle: CarrierRejectionCaptureSourceBundle | None,
) -> None:
    if confirmation.preflight_packet_id != packet.packet_id:
        raise ValueError("human confirmation does not bind to preflight packet")
    if budget.preflight_packet_id != packet.packet_id:
        raise ValueError("budget proposal does not bind to preflight packet")
    if budget.confirmation_id != confirmation.confirmation_id:
        raise ValueError("budget proposal does not bind to human confirmation")
    if budget_precondition_report is not None:
        if budget_precondition_report.preflight_packet_id != packet.packet_id:
            raise ValueError("budget precondition report does not bind to preflight packet")
        if budget_precondition_report.confirmation_id != confirmation.confirmation_id:
            raise ValueError("budget precondition report does not bind to human confirmation")
    if actual_report is not None:
        if actual_report.preflight_packet_id != packet.packet_id:
            raise ValueError("actual comparison report does not bind to preflight packet")
        if actual_report.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError("actual comparison report does not bind to budget proposal")
        if actual_report.billing_connector_read_performed:
            raise ValueError("actual comparison report cannot claim billing connector reads")
    if carrier_ledger is not None:
        if carrier_ledger.preflight_packet_id != packet.packet_id:
            raise ValueError("carrier rejection decision ledger does not bind to preflight packet")
        if carrier_ledger.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError("carrier rejection decision ledger does not bind to budget proposal")
        if (
            carrier_ledger.lake_write_performed
            or carrier_ledger.sqlite_write_performed
            or carrier_ledger.external_writes_performed
            or carrier_ledger.appeal_submission_performed
            or carrier_ledger.silent_learning_performed
        ):
            raise ValueError("carrier rejection ledger contains prohibited side effects")
    if carrier_bundle is not None:
        if carrier_bundle.preflight_packet_id != packet.packet_id:
            raise ValueError("carrier rejection source bundle does not bind to preflight packet")
        if carrier_bundle.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError("carrier rejection source bundle does not bind to budget proposal")
        if (
            carrier_bundle.contains_real_client_data
            or carrier_bundle.contains_real_matter_data
            or carrier_bundle.contains_privileged_data
            or carrier_bundle.data_origin != "synthetic"
        ):
            raise ValueError("carrier rejection source bundle must remain synthetic-only")


def build_orchestrator_owner_review_request(
    *,
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    budget: BudgetProposal,
    budget_precondition_report: BudgetPreconditionReport | None = None,
    actual_report: BudgetActualComparisonReport | None = None,
    carrier_ledger: CarrierRejectionDecisionLedgerReport | None = None,
    carrier_bundle: CarrierRejectionCaptureSourceBundle | None = None,
    lake_handoff_mode: str = "disabled",
) -> OrchestratorOwnerReviewRequest:
    _validate_lineage(
        packet=packet,
        confirmation=confirmation,
        budget=budget,
        budget_precondition_report=budget_precondition_report,
        actual_report=actual_report,
        carrier_ledger=carrier_ledger,
        carrier_bundle=carrier_bundle,
    )
    carrier_refs: list[CarrierRejectionSourceRef] = []
    if carrier_bundle is not None:
        carrier_refs.extend(ref for notice in carrier_bundle.notices for ref in notice.source_refs)
        carrier_refs.extend(
            ref for result in carrier_bundle.appeal_results for ref in result.source_refs
        )
    elif carrier_ledger is not None:
        carrier_refs.extend(ref for event in carrier_ledger.events for ref in event.source_refs)

    if carrier_bundle is not None:
        carrier_notices = _carrier_notices_from_bundle(
            bundle=carrier_bundle,
            ledger=carrier_ledger,
        )
    elif carrier_ledger is not None:
        carrier_notices = _carrier_notices_from_ledger(carrier_ledger)
    else:
        carrier_notices = []

    actual_lines = (
        _actual_lines_from_report(report=actual_report, budget=budget, ledger=carrier_ledger)
        if actual_report is not None
        else _actual_lines_from_budget(budget)
    )
    source_refs = _combine_source_refs(
        _preflight_source_refs(packet),
        _source_refs_from_carrier_refs(carrier_refs),
    )
    request = OrchestratorOwnerReviewRequest(
        request_id=_stable_request_id(
            packet.packet_id,
            confirmation.confirmation_id,
            budget.budget_proposal_id,
            actual_report.budget_actual_comparison_report_id if actual_report else "",
            carrier_ledger.decision_ledger_report_id if carrier_ledger else "",
        ),
        generated_at=now_iso(),
        source_refs=source_refs,
        human_confirmations=_build_human_confirmations(confirmation, budget),
        budget_preconditions=_build_budget_preconditions(
            packet=packet,
            confirmation=confirmation,
            budget=budget,
            budget_precondition_report=budget_precondition_report,
        ),
        budget_actual_lines=actual_lines,
        carrier_rejection_notices=carrier_notices,
        lake_handoff_mode=lake_handoff_mode,  # type: ignore[arg-type]
    )
    return request


def render_orchestrator_owner_review_request(
    request: OrchestratorOwnerReviewRequest,
) -> str:
    pending_pauses = [
        key
        for key, value in request.human_confirmations.items()
        if value.status not in {"confirmed", "approved", "human_only", "declined_referred"}
    ]
    missing_preconditions = [
        key
        for key, value in request.budget_preconditions.model_dump(mode="json").items()
        if value is not True
    ]
    lines = [
        "# Orchestrator Owner Review Request",
        "",
        f"**Request ID:** {request.request_id}",
        f"**Schema:** {request.schema_version}",
        f"**Workflow label:** `{request.workflow_label}`",
        "",
        "## Contents",
        "",
        f"- Source refs: {len(request.source_refs)}",
        f"- Budget/actual lines: {len(request.budget_actual_lines)}",
        f"- Carrier rejection notices: {len(request.carrier_rejection_notices)}",
        f"- Lake handoff mode: {request.lake_handoff_mode}",
        "",
        "## Human Pauses",
        "",
    ]
    for key, value in request.human_confirmations.items():
        lines.append(f"- `{key}`: {value.status}")
    lines.extend(["", "## Budget Preconditions", ""])
    for key, value in request.budget_preconditions.model_dump(mode="json").items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Current Blockers",
            "",
        ]
    )
    if not pending_pauses and not missing_preconditions:
        lines.append(
            "- No local request blockers detected; Orchestrator owner review is still required."
        )
    for pause in pending_pauses:
        lines.append(f"- Human pause pending or unresolved: `{pause}`")
    for precondition in missing_preconditions:
        lines.append(f"- Budget precondition missing: `{precondition}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Synthetic: {request.synthetic}",
            f"- Contains real firm data: {request.contains_real_firm_data}",
            f"- Contains real client data: {request.contains_real_client_data}",
            f"- Contains real matter data: {request.contains_real_matter_data}",
            f"- Contains privileged data: {request.contains_privileged_data}",
            "",
            "This is a local request artifact for Orchestrator owner review. It does not call Orchestrator, write sibling repos, submit budgets, submit appeals, admit Exception Lake records, write SQLite, or create canonical route/event authority.",
            "",
        ]
    )
    return "\n".join(lines)


def run_orchestrator_owner_review_request(
    *,
    preflight_packet_path: str | Path,
    confirmation_path: str | Path,
    budget_path: str | Path,
    out_dir: str | Path,
    budget_precondition_report_path: str | Path | None = None,
    budget_actual_comparison_report_path: str | Path | None = None,
    carrier_rejection_decision_ledger_report_path: str | Path | None = None,
    carrier_rejection_source_bundle_path: str | Path | None = None,
    lake_handoff_mode: str = "disabled",
) -> tuple[OrchestratorOwnerReviewRequest, Path]:
    packet = IntakePreflightPacket.model_validate(load_json(preflight_packet_path))
    confirmation = HumanConfirmation.model_validate(load_json(confirmation_path))
    budget = BudgetProposal.model_validate(load_json(budget_path))
    budget_precondition_report = _load_budget_precondition_report(budget_precondition_report_path)
    actual_report = _load_actual_report(budget_actual_comparison_report_path)
    carrier_ledger = _load_carrier_ledger(carrier_rejection_decision_ledger_report_path)
    carrier_bundle = _load_carrier_bundle(carrier_rejection_source_bundle_path, budget)
    request = build_orchestrator_owner_review_request(
        packet=packet,
        confirmation=confirmation,
        budget=budget,
        budget_precondition_report=budget_precondition_report,
        actual_report=actual_report,
        carrier_ledger=carrier_ledger,
        carrier_bundle=carrier_bundle,
        lake_handoff_mode=lake_handoff_mode,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / ORCHESTRATOR_OWNER_REVIEW_REQUEST_FILENAME,
        request.model_dump(mode="json"),
    )
    (run_dir / ORCHESTRATOR_OWNER_REVIEW_REQUEST_NOTES_FILENAME).write_text(
        render_orchestrator_owner_review_request(request),
        encoding="utf-8",
    )
    return request, run_dir
