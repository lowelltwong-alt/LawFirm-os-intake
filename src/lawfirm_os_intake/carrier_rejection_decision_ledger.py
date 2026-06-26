from __future__ import annotations

import json
from pathlib import Path

from .models import (
    CarrierAppealResult,
    CarrierRejectionCaptureSourceBundle,
    CarrierRejectionDecisionLedgerEvent,
    CarrierRejectionDecisionLedgerReport,
    CarrierRejectionNotice,
    CarrierRejectionRemediationCase,
    CarrierResponseReconciliationReport,
)
from .util import digest_text, now_iso, write_json


CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME = "carrier_rejection_decision_ledger_report.json"
CARRIER_REJECTION_DECISION_LEDGER_FILENAME = "carrier_rejection_decision_ledger.jsonl"
CARRIER_REJECTION_DECISION_LEDGER_NOTES_FILENAME = "carrier_rejection_decision_ledger_report.md"

CARRIER_REJECTION_DECISION_LEDGER_REQUIRED_NEXT_GATES = [
    "human_rejection_decision_review",
    "append_only_rejection_review_outcome",
    "orchestrator_evidence_packet_before_lake_admission",
    "exception_lake_admission_by_exception_lake_runtime",
    "appeal_submission_requires_human_authorization_and_orchestrator_connector",
    "reviewed_learning_gate_before_candidate_changes",
    "no_silent_profile_template_budget_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _money(value: float | None) -> float:
    return round(float(value or 0.0), 2)


def _source_channels(refs: list) -> list[str]:
    return sorted({ref.source_channel for ref in refs})


def _event_kind_for_case(case: CarrierRejectionRemediationCase) -> str:
    if case.local_event_label == "carrier_response_missing_after_sla":
        return "carrier_response_missing_after_sla"
    if case.local_event_label == "carrier_rejection_unlinked":
        return "carrier_rejection_unlinked_notice"
    if case.local_event_label == "carrier_rejection_parse_failed":
        return "carrier_rejection_parse_failed"
    return "carrier_rejection_notice_captured"


def _decision_status_for_case(case: CarrierRejectionRemediationCase) -> str:
    if case.local_event_label == "carrier_response_missing_after_sla":
        return "blocked_missing_response_followup"
    if case.local_event_label in {
        "carrier_rejection_unlinked",
        "carrier_rejection_parse_failed",
    }:
        return "blocked_linkage_or_parse_review"
    if case.status == "appeal_result_captured":
        return "appeal_result_captured_pending_review"
    return "captured_pending_human_review"


def _pending_actions_for_case(case: CarrierRejectionRemediationCase) -> list[str]:
    if case.local_event_label == "carrier_response_missing_after_sla":
        return [
            "confirm_response_still_missing",
            "assign_followup_owner",
            "perform_orchestrator_owned_carrier_followup",
        ]
    if case.local_event_label == "carrier_rejection_unlinked":
        return [
            "link_submission_invoice_budget_or_appeal",
            "escalate_unlinked_notice_if_linkage_fails",
        ]
    if case.local_event_label == "carrier_rejection_parse_failed":
        return [
            "repair_parser_or_manual_extraction",
            "rerun_reconciliation_before_learning_use",
        ]
    if case.status == "appeal_result_captured":
        return [
            "review_appeal_result",
            "record_financial_outcome",
            "decide_learning_candidate_after_human_review",
        ]
    return [
        "appeal",
        "fix_and_resubmit",
        "accept_write_down",
        "request_more_information",
    ]


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


def _candidate_ids_by_appeal(report: CarrierResponseReconciliationReport) -> dict[str, list[str]]:
    by_appeal: dict[str, list[str]] = {}
    for candidate in report.exception_lake_candidates:
        for ref in candidate.structured_refs:
            prefix = "carrier-appeal-result://"
            if not ref.startswith(prefix):
                continue
            appeal_result_id = ref.removeprefix(prefix)
            by_appeal.setdefault(appeal_result_id, []).append(candidate.candidate_id)
    return {appeal_id: sorted(set(ids)) for appeal_id, ids in by_appeal.items()}


def _notice_by_id(bundle: CarrierRejectionCaptureSourceBundle) -> dict[str, CarrierRejectionNotice]:
    return {notice.notice_id: notice for notice in bundle.notices}


def _case_for_notice_id(
    report: CarrierResponseReconciliationReport,
) -> dict[str, CarrierRejectionRemediationCase]:
    return {
        notice_id: case
        for case in report.remediation_cases
        for notice_id in case.duplicate_notice_ids
    }


def _case_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
    case: CarrierRejectionRemediationCase,
    candidate_ids: list[str],
) -> CarrierRejectionDecisionLedgerEvent:
    notices = [notice for notice in bundle.notices if notice.notice_id in case.duplicate_notice_ids]
    response_type = sorted({notice.response_type for notice in notices})
    return CarrierRejectionDecisionLedgerEvent(
        decision_ledger_event_id=_stable_id(
            "carrierdecisionevent",
            f"{ledger_id}|{sequence_index}|{case.remediation_case_id}|case",
        ),
        decision_ledger_id=ledger_id,
        sequence_index=sequence_index,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        remediation_case_id=case.remediation_case_id,
        notice_ids=case.duplicate_notice_ids,
        carrier_id=case.carrier_id,
        submission_id=case.submission_id,
        invoice_id=case.invoice_id,
        phase_id=case.phase_id,
        task_id=case.task_id,
        external_code_candidate=case.external_code_candidate,
        event_kind=_event_kind_for_case(case),  # type: ignore[arg-type]
        decision_status=_decision_status_for_case(case),  # type: ignore[arg-type]
        local_event_label=case.local_event_label,
        canonical_lake_class_candidate=case.canonical_lake_class,
        source_channels=_source_channels(case.source_refs),
        source_refs=case.source_refs,
        response_type=",".join(response_type) if response_type else None,
        disputed_amount=_money(case.disputed_amount),
        current_financial_exposure=_money(case.current_financial_exposure),
        proposed_next_actions=_pending_actions_for_case(case),
        required_human_decisions=case.required_human_decisions,
        exception_candidate_ids=candidate_ids,
        structured_refs=[
            f"carrier-rejection-case://{case.remediation_case_id}",
            *[f"carrier-rejection-notice://{notice_id}" for notice_id in case.duplicate_notice_ids],
            f"carrier-reconciliation-report://{report.reconciliation_report_id}",
        ],
    )


def _duplicate_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
    case: CarrierRejectionRemediationCase,
    candidate_ids: list[str],
) -> CarrierRejectionDecisionLedgerEvent:
    return CarrierRejectionDecisionLedgerEvent(
        decision_ledger_event_id=_stable_id(
            "carrierdecisionevent",
            f"{ledger_id}|{sequence_index}|{case.remediation_case_id}|duplicate",
        ),
        decision_ledger_id=ledger_id,
        sequence_index=sequence_index,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        remediation_case_id=case.remediation_case_id,
        notice_ids=case.duplicate_notice_ids,
        carrier_id=case.carrier_id,
        submission_id=case.submission_id,
        invoice_id=case.invoice_id,
        phase_id=case.phase_id,
        task_id=case.task_id,
        external_code_candidate=case.external_code_candidate,
        event_kind="carrier_duplicate_notice_collapsed",
        decision_status="captured_pending_human_review",
        local_event_label="carrier_rejection_duplicate_notice",
        canonical_lake_class_candidate="workflow_escalation",
        source_channels=_source_channels(case.source_refs),
        source_refs=case.source_refs,
        disputed_amount=_money(case.disputed_amount),
        current_financial_exposure=_money(case.current_financial_exposure),
        proposed_next_actions=[
            "review_duplicate_notice_ids",
            "preserve_one_exposure_amount",
            "prevent_double_counting_deadline_or_learning_pressure",
        ],
        required_human_decisions=["confirm_duplicate_collapse"],
        exception_candidate_ids=candidate_ids,
        structured_refs=[
            f"carrier-rejection-case://{case.remediation_case_id}",
            *[f"carrier-rejection-notice://{notice_id}" for notice_id in case.duplicate_notice_ids],
            f"carrier-reconciliation-report://{report.reconciliation_report_id}",
        ],
    )


def _pending_decision_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
    case: CarrierRejectionRemediationCase,
    candidate_ids: list[str],
) -> CarrierRejectionDecisionLedgerEvent:
    return CarrierRejectionDecisionLedgerEvent(
        decision_ledger_event_id=_stable_id(
            "carrierdecisionevent",
            f"{ledger_id}|{sequence_index}|{case.remediation_case_id}|pending",
        ),
        decision_ledger_id=ledger_id,
        sequence_index=sequence_index,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        remediation_case_id=case.remediation_case_id,
        notice_ids=case.duplicate_notice_ids,
        carrier_id=case.carrier_id,
        submission_id=case.submission_id,
        invoice_id=case.invoice_id,
        phase_id=case.phase_id,
        task_id=case.task_id,
        external_code_candidate=case.external_code_candidate,
        event_kind="carrier_fix_or_appeal_decision_pending",
        decision_status="pending_human_fix_or_appeal_decision",
        local_event_label=case.local_event_label,
        canonical_lake_class_candidate=case.canonical_lake_class,
        source_channels=_source_channels(case.source_refs),
        source_refs=case.source_refs,
        disputed_amount=_money(case.disputed_amount),
        current_financial_exposure=_money(case.current_financial_exposure),
        proposed_next_actions=_pending_actions_for_case(case),
        required_human_decisions=case.required_human_decisions,
        exception_candidate_ids=candidate_ids,
        structured_refs=[
            f"carrier-rejection-case://{case.remediation_case_id}",
            f"carrier-reconciliation-report://{report.reconciliation_report_id}",
            "docs/carrier-rejection-learning-loop-roadmap.md#remediation-workflow",
        ],
    )


def _appeal_result_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
    result: CarrierAppealResult,
    case: CarrierRejectionRemediationCase | None,
    notice: CarrierRejectionNotice | None,
    candidate_ids: list[str],
) -> CarrierRejectionDecisionLedgerEvent:
    return CarrierRejectionDecisionLedgerEvent(
        decision_ledger_event_id=_stable_id(
            "carrierdecisionevent",
            f"{ledger_id}|{sequence_index}|{result.appeal_result_id}|appeal",
        ),
        decision_ledger_id=ledger_id,
        sequence_index=sequence_index,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        remediation_case_id=case.remediation_case_id if case else None,
        appeal_result_id=result.appeal_result_id,
        notice_ids=[result.related_notice_id],
        carrier_id=notice.carrier_id if notice else case.carrier_id if case else None,
        submission_id=notice.submission_id if notice else case.submission_id if case else None,
        invoice_id=notice.invoice_id if notice else case.invoice_id if case else None,
        phase_id=notice.phase_id if notice else case.phase_id if case else None,
        task_id=notice.task_id if notice else case.task_id if case else None,
        external_code_candidate=(
            notice.external_code_candidate
            if notice
            else case.external_code_candidate
            if case
            else None
        ),
        event_kind="carrier_appeal_result_received",
        decision_status="appeal_result_captured_pending_review",
        local_event_label="carrier_appeal_result_received",
        canonical_lake_class_candidate="workflow_escalation",
        source_channels=_source_channels(result.source_refs),
        source_refs=result.source_refs,
        appeal_result=result.result,
        disputed_amount=_money(case.disputed_amount if case else None),
        current_financial_exposure=_money(case.current_financial_exposure if case else None),
        appealed_amount=_money(result.appealed_amount),
        recovered_amount=_money(result.recovered_amount),
        write_down_amount=_money(result.write_down_amount),
        remaining_write_down_amount=_money(result.write_down_amount),
        proposed_next_actions=[
            "review_appeal_result",
            "record_financial_outcome",
            "decide_learning_candidate_after_human_review",
        ],
        required_human_decisions=[
            "confirm_appeal_result",
            "confirm_recovered_amount",
            "confirm_remaining_write_down",
        ],
        exception_candidate_ids=candidate_ids,
        structured_refs=[
            f"carrier-appeal-result://{result.appeal_result_id}",
            f"carrier-rejection-notice://{result.related_notice_id}",
            f"carrier-reconciliation-report://{report.reconciliation_report_id}",
            *([f"carrier-rejection-case://{case.remediation_case_id}"] if case else []),
        ],
    )


def _financial_outcome_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
    result: CarrierAppealResult,
    case: CarrierRejectionRemediationCase | None,
    notice: CarrierRejectionNotice | None,
    candidate_ids: list[str],
) -> CarrierRejectionDecisionLedgerEvent:
    write_down = _money(result.write_down_amount)
    if not write_down and result.appealed_amount is not None:
        write_down = max(0.0, _money(result.appealed_amount) - _money(result.recovered_amount))
    return CarrierRejectionDecisionLedgerEvent(
        decision_ledger_event_id=_stable_id(
            "carrierdecisionevent",
            f"{ledger_id}|{sequence_index}|{result.appeal_result_id}|financial",
        ),
        decision_ledger_id=ledger_id,
        sequence_index=sequence_index,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        remediation_case_id=case.remediation_case_id if case else None,
        appeal_result_id=result.appeal_result_id,
        notice_ids=[result.related_notice_id],
        carrier_id=notice.carrier_id if notice else case.carrier_id if case else None,
        submission_id=notice.submission_id if notice else case.submission_id if case else None,
        invoice_id=notice.invoice_id if notice else case.invoice_id if case else None,
        phase_id=notice.phase_id if notice else case.phase_id if case else None,
        task_id=notice.task_id if notice else case.task_id if case else None,
        external_code_candidate=(
            notice.external_code_candidate
            if notice
            else case.external_code_candidate
            if case
            else None
        ),
        event_kind="carrier_financial_outcome_recorded",
        decision_status="financial_outcome_captured_pending_review",
        local_event_label="carrier_rejection_financial_outcome_recorded",
        canonical_lake_class_candidate="workflow_escalation",
        source_channels=_source_channels(result.source_refs),
        source_refs=result.source_refs,
        appeal_result=result.result,
        disputed_amount=_money(case.disputed_amount if case else None),
        current_financial_exposure=write_down,
        appealed_amount=_money(result.appealed_amount),
        recovered_amount=_money(result.recovered_amount),
        write_down_amount=write_down,
        remaining_write_down_amount=write_down,
        proposed_next_actions=[
            "confirm_financial_outcome",
            "route_write_down_or_recovery_review",
            "block_learning_until_reviewed",
        ],
        required_human_decisions=[
            "confirm_recovered_amount",
            "confirm_remaining_write_down",
            "confirm_accounting_disposition",
        ],
        exception_candidate_ids=candidate_ids,
        structured_refs=[
            f"carrier-appeal-result://{result.appeal_result_id}",
            f"carrier-financial-outcome://{result.appeal_result_id}",
            f"carrier-reconciliation-report://{report.reconciliation_report_id}",
            *([f"carrier-rejection-case://{case.remediation_case_id}"] if case else []),
        ],
    )


def _event_kind_counts(events: list[CarrierRejectionDecisionLedgerEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_kind] = counts.get(event.event_kind, 0) + 1
    return counts


def _status_for_report(report: CarrierResponseReconciliationReport, event_count: int) -> str:
    if event_count == 0:
        return "decision_ledger_no_events"
    if report.status == "blocked_missing_required_followup":
        return "decision_ledger_blocked_missing_followup"
    return "decision_ledger_ready_for_review"


def build_carrier_rejection_decision_ledger_report(
    *,
    report: CarrierResponseReconciliationReport,
    bundle: CarrierRejectionCaptureSourceBundle,
) -> CarrierRejectionDecisionLedgerReport:
    if report.source_bundle_id != bundle.bundle_id:
        raise ValueError("carrier decision ledger bundle id does not match reconciliation report")
    if report.budget_proposal_id != bundle.budget_proposal_id:
        raise ValueError("carrier decision ledger budget id does not match bundle")
    if report.preflight_packet_id != bundle.preflight_packet_id:
        raise ValueError("carrier decision ledger preflight id does not match bundle")

    ledger_id = _stable_id(
        "carrierdecisionledger",
        f"{report.reconciliation_report_id}|{bundle.bundle_id}",
    )
    case_candidate_ids = _candidate_ids_by_case(report)
    appeal_candidate_ids = _candidate_ids_by_appeal(report)
    notices = _notice_by_id(bundle)
    cases_by_notice = _case_for_notice_id(report)
    events: list[CarrierRejectionDecisionLedgerEvent] = []

    for case in report.remediation_cases:
        events.append(
            _case_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                bundle=bundle,
                case=case,
                candidate_ids=case_candidate_ids.get(case.remediation_case_id, []),
            )
        )
        if len(case.duplicate_notice_ids) > 1:
            events.append(
                _duplicate_event(
                    ledger_id=ledger_id,
                    sequence_index=len(events),
                    report=report,
                    bundle=bundle,
                    case=case,
                    candidate_ids=case_candidate_ids.get(case.remediation_case_id, []),
                )
            )
        if not case.linked_appeal_result_ids:
            events.append(
                _pending_decision_event(
                    ledger_id=ledger_id,
                    sequence_index=len(events),
                    report=report,
                    bundle=bundle,
                    case=case,
                    candidate_ids=case_candidate_ids.get(case.remediation_case_id, []),
                )
            )

    for result in bundle.appeal_results:
        case = cases_by_notice.get(result.related_notice_id)
        notice = notices.get(result.related_notice_id)
        candidates = appeal_candidate_ids.get(result.appeal_result_id, [])
        events.append(
            _appeal_result_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                bundle=bundle,
                result=result,
                case=case,
                notice=notice,
                candidate_ids=candidates,
            )
        )
        events.append(
            _financial_outcome_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                bundle=bundle,
                result=result,
                case=case,
                notice=notice,
                candidate_ids=candidates,
            )
        )

    kind_counts = _event_kind_counts(events)
    return CarrierRejectionDecisionLedgerReport(
        decision_ledger_report_id=_stable_id(
            "carrierdecisionledgerreport",
            f"{ledger_id}|{report.reconciliation_report_id}",
        ),
        decision_ledger_id=ledger_id,
        reconciliation_report_id=report.reconciliation_report_id,
        source_bundle_id=bundle.bundle_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        status=_status_for_report(report, len(events)),  # type: ignore[arg-type]
        entry_count=len(events),
        remediation_case_event_count=len(report.remediation_cases),
        pending_decision_event_count=kind_counts.get("carrier_fix_or_appeal_decision_pending", 0),
        appeal_result_event_count=kind_counts.get("carrier_appeal_result_received", 0),
        financial_outcome_event_count=kind_counts.get("carrier_financial_outcome_recorded", 0),
        total_disputed_amount=round(
            sum(case.current_financial_exposure for case in report.remediation_cases),
            2,
        ),
        total_recovered_amount=round(
            sum(
                event.recovered_amount
                for event in events
                if event.event_kind == "carrier_financial_outcome_recorded"
            ),
            2,
        ),
        total_write_down_amount=round(
            sum(
                event.write_down_amount
                for event in events
                if event.event_kind == "carrier_financial_outcome_recorded"
            ),
            2,
        ),
        event_kind_counts=kind_counts,
        events=events,
        required_next_gates=CARRIER_REJECTION_DECISION_LEDGER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def write_carrier_rejection_decision_ledger_outputs(
    *,
    run_dir: Path,
    ledger_report: CarrierRejectionDecisionLedgerReport,
) -> None:
    write_json(
        run_dir / CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME,
        ledger_report.model_dump(mode="json"),
    )
    ledger_rows = "\n".join(
        json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for event in ledger_report.events
    )
    (run_dir / CARRIER_REJECTION_DECISION_LEDGER_FILENAME).write_text(
        ledger_rows + ("\n" if ledger_rows else ""),
        encoding="utf-8",
    )
    (run_dir / CARRIER_REJECTION_DECISION_LEDGER_NOTES_FILENAME).write_text(
        render_carrier_rejection_decision_ledger_report(ledger_report),
        encoding="utf-8",
    )


def render_carrier_rejection_decision_ledger_report(
    report: CarrierRejectionDecisionLedgerReport,
) -> str:
    lines = [
        "# Carrier Rejection Decision Ledger Report",
        "",
        f"**Report ID:** {report.decision_ledger_report_id}",
        f"**Ledger ID:** {report.decision_ledger_id}",
        f"**Status:** {report.status}",
        f"**Reconciliation report:** {report.reconciliation_report_id}",
        f"**Source bundle:** {report.source_bundle_id}",
        "",
        "## Summary",
        "",
        f"- Entry count: {report.entry_count}",
        f"- Remediation case event count: {report.remediation_case_event_count}",
        f"- Pending decision event count: {report.pending_decision_event_count}",
        f"- Appeal result event count: {report.appeal_result_event_count}",
        f"- Financial outcome event count: {report.financial_outcome_event_count}",
        f"- Total disputed/exposure amount: {report.total_disputed_amount}",
        f"- Total recovered amount: {report.total_recovered_amount}",
        f"- Total write-down amount: {report.total_write_down_amount}",
        f"- Event kind counts: {report.event_kind_counts}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Appeal submission performed: {report.appeal_submission_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Events",
        "",
    ]
    for event in report.events:
        lines.append(
            f"- {event.sequence_index}: {event.event_kind}; case={event.remediation_case_id or 'none'}; "
            f"appeal={event.appeal_result_id or 'none'}; status={event.decision_status}; "
            f"exposure={event.current_financial_exposure}; recovered={event.recovered_amount}; "
            f"write_down={event.write_down_amount}"
        )
        lines.append(f"  - next actions: {', '.join(event.proposed_next_actions) or 'none'}")
        lines.append(
            f"  - Lake admission review required: {event.requires_exception_lake_admission_review}"
        )
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This ledger is append-only local candidate evidence. It does not submit appeals, write portal/email/billing systems, admit Lake/SQLite records, mutate budgets, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)
