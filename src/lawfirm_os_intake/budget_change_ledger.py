from __future__ import annotations

import json
from pathlib import Path

from .models import (
    BudgetChangeLedgerEvent,
    BudgetChangeLedgerReport,
    BudgetReviewChangeRecord,
    BudgetRevisionDelta,
    BudgetRevisionReport,
)
from .util import digest_text, now_iso, write_json


BUDGET_CHANGE_LEDGER_REPORT_FILENAME = "budget_change_ledger_report.json"
BUDGET_CHANGE_LEDGER_FILENAME = "budget_change_ledger.jsonl"
BUDGET_CHANGE_LEDGER_NOTES_FILENAME = "budget_change_ledger_report.md"

BUDGET_CHANGE_LEDGER_REQUIRED_NEXT_GATES = [
    "human_budget_change_ledger_review",
    "exception_lake_admission_by_exception_lake_runtime",
    "actuals_comparison_may_reference_ledger_but_not_mutate_it",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_budget_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _change_class(delta: BudgetRevisionDelta | None, outcome: str) -> str:
    if delta is None:
        return "review_outcome_only"
    if delta.field == "estimated_hours":
        return "hours_change"
    if delta.field == "hourly_rate":
        return "rate_change"
    if delta.field == "estimated_expenses":
        return "expense_change"
    if delta.field == "assumption":
        return "assumption_change"
    if delta.field == "exclusion":
        return "exclusion_change"
    if delta.field == "unknown":
        return "unknown_info_change"
    if delta.field == "scenario_id":
        return "scenario_change"
    if outcome == "corrected":
        return "other_non_numeric_change"
    return "review_outcome_only"


def _event_kind(outcome: str) -> str:
    if outcome == "corrected":
        return "human_budget_change_recorded"
    if outcome == "confirmed_no_change":
        return "human_budget_no_change_confirmed"
    if outcome == "human_only":
        return "human_budget_human_only_hold"
    if outcome == "declined_referred":
        return "human_budget_declined_referred"
    return "human_budget_review_blocked"


def _event_status(outcome: str) -> str:
    if outcome == "corrected":
        return "recorded_candidate"
    if outcome == "confirmed_no_change":
        return "no_change_confirmed"
    return "blocked_from_budget_use"


def _report_status(outcome: str) -> str:
    if outcome == "corrected":
        return "ledger_recorded"
    if outcome == "confirmed_no_change":
        return "no_change_confirmed"
    return "blocked_budget_review_outcome_recorded"


def _candidate_reason(
    *,
    record: BudgetReviewChangeRecord,
    delta: BudgetRevisionDelta | None,
) -> str:
    if delta is None:
        return (
            f"Human budget review outcome `{record.outcome}` was recorded for "
            f"budget proposal `{record.budget_proposal_id}`."
        )
    return (
        f"Human budget review change `{delta.change_id}` adjusted `{delta.field}` "
        f"with total candidate delta {delta.total_delta}."
    )


def _event_reason(
    *,
    record: BudgetReviewChangeRecord,
    delta: BudgetRevisionDelta | None,
) -> str:
    return delta.reason if delta is not None else record.decision_reason


def _event_refs(delta: BudgetRevisionDelta | None) -> tuple[list, list[str]]:
    if delta is None:
        return [], []
    return delta.evidence_refs, delta.structured_refs


def _event_from_delta(
    *,
    ledger_id: str,
    sequence_index: int,
    record: BudgetReviewChangeRecord,
    report: BudgetRevisionReport,
    delta: BudgetRevisionDelta,
    before_total: float | None,
    after_total: float | None,
) -> BudgetChangeLedgerEvent:
    evidence_refs, structured_refs = _event_refs(delta)
    stable_basis = "|".join(
        [
            ledger_id,
            str(sequence_index),
            report.budget_revision_report_id,
            delta.delta_id,
        ]
    )
    return BudgetChangeLedgerEvent(
        budget_change_ledger_event_id=_stable_id("budgetchangeevent", stable_basis),
        ledger_id=ledger_id,
        sequence_index=sequence_index,
        budget_revision_report_id=report.budget_revision_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_review_change_record_id=record.budget_review_change_record_id,
        source_budget_proposal_ref=report.source_budget_proposal_ref,
        reviewer_id=record.reviewer_id,
        reviewer_role=record.reviewer_role,
        reviewed_at=record.reviewed_at,
        review_outcome=record.outcome,
        decision_reason=record.decision_reason,
        supersedes_budget_review_change_record_id=(
            record.supersedes_budget_review_change_record_id
        ),
        change_id=delta.change_id,
        delta_id=delta.delta_id,
        event_kind="human_budget_change_recorded",
        status="recorded_candidate",
        change_class=_change_class(delta, record.outcome),  # type: ignore[arg-type]
        target_type=delta.target_type,
        phase_id=delta.phase_id,
        task_id=delta.task_id,
        external_code_candidate=delta.external_code_candidate,
        expense_code=delta.expense_code,
        staffing_role=delta.staffing_role,
        field=delta.field,
        previous_value=delta.previous_value,
        new_value=delta.new_value,
        hours_delta=delta.hours_delta,
        fee_delta=delta.fee_delta,
        expense_delta=delta.expense_delta,
        total_delta=delta.total_delta,
        budget_total_before_event=before_total,
        budget_total_after_event=after_total,
        reason=_event_reason(record=record, delta=delta),
        evidence_refs=evidence_refs,
        structured_refs=structured_refs,
        exception_lake_local_event_label="budget_human_change_recorded",
        exception_lake_candidate_reason=_candidate_reason(record=record, delta=delta),
    )


def _outcome_only_event(
    *,
    ledger_id: str,
    record: BudgetReviewChangeRecord,
    report: BudgetRevisionReport,
) -> BudgetChangeLedgerEvent:
    stable_basis = "|".join(
        [
            ledger_id,
            "0",
            report.budget_revision_report_id,
            record.budget_review_change_record_id,
            record.outcome,
        ]
    )
    return BudgetChangeLedgerEvent(
        budget_change_ledger_event_id=_stable_id("budgetchangeevent", stable_basis),
        ledger_id=ledger_id,
        sequence_index=0,
        budget_revision_report_id=report.budget_revision_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_review_change_record_id=record.budget_review_change_record_id,
        source_budget_proposal_ref=report.source_budget_proposal_ref,
        reviewer_id=record.reviewer_id,
        reviewer_role=record.reviewer_role,
        reviewed_at=record.reviewed_at,
        review_outcome=record.outcome,
        decision_reason=record.decision_reason,
        supersedes_budget_review_change_record_id=(
            record.supersedes_budget_review_change_record_id
        ),
        event_kind=_event_kind(record.outcome),  # type: ignore[arg-type]
        status=_event_status(record.outcome),  # type: ignore[arg-type]
        change_class="review_outcome_only",
        budget_total_before_event=report.original_total,
        budget_total_after_event=report.original_total,
        reason=record.decision_reason,
        structured_refs=[f"budget-revision-report://{report.budget_revision_report_id}"],
        exception_lake_local_event_label=_event_kind(record.outcome),
        exception_lake_candidate_reason=_candidate_reason(record=record, delta=None),
    )


def _event_kind_counts(events: list[BudgetChangeLedgerEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_kind] = counts.get(event.event_kind, 0) + 1
    return counts


def build_budget_change_ledger_report(
    *,
    record: BudgetReviewChangeRecord,
    report: BudgetRevisionReport,
    ledger_ref: str,
    revision_report_ref: str,
) -> BudgetChangeLedgerReport:
    if record.budget_review_change_record_id != report.budget_review_change_record_id:
        raise ValueError(
            "budget change ledger record id does not match revision report: "
            f"{record.budget_review_change_record_id} != "
            f"{report.budget_review_change_record_id}"
        )
    if record.budget_proposal_id != report.budget_proposal_id:
        raise ValueError(
            "budget change ledger budget_proposal_id does not match revision report: "
            f"{record.budget_proposal_id} != {report.budget_proposal_id}"
        )
    ledger_id = _stable_id(
        "budgetchangeledger",
        "|".join(
            [
                report.budget_revision_report_id,
                record.budget_review_change_record_id,
            ]
        ),
    )
    events: list[BudgetChangeLedgerEvent] = []
    current_total = report.original_total
    if report.deltas:
        for index, delta in enumerate(report.deltas):
            before_total = current_total
            after_total = (
                _money(before_total + delta.total_delta) if before_total is not None else None
            )
            events.append(
                _event_from_delta(
                    ledger_id=ledger_id,
                    sequence_index=index,
                    record=record,
                    report=report,
                    delta=delta,
                    before_total=before_total,
                    after_total=after_total,
                )
            )
            current_total = after_total
    else:
        events.append(_outcome_only_event(ledger_id=ledger_id, record=record, report=report))
    return BudgetChangeLedgerReport(
        budget_change_ledger_report_id=_stable_id(
            "budgetchangeledgerreport",
            "|".join(
                [
                    ledger_id,
                    report.budget_revision_report_id,
                    record.budget_review_change_record_id,
                ]
            ),
        ),
        ledger_id=ledger_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_revision_report_id=report.budget_revision_report_id,
        budget_review_change_record_id=record.budget_review_change_record_id,
        source_budget_proposal_ref=report.source_budget_proposal_ref,
        source_budget_revision_report_ref=revision_report_ref,
        ledger_ref=ledger_ref,
        status=_report_status(record.outcome),  # type: ignore[arg-type]
        review_outcome=record.outcome,
        entry_count=len(events),
        numeric_change_entry_count=sum(
            1 for event in events if event.fee_delta or event.expense_delta or event.hours_delta
        ),
        total_delta=report.total_delta,
        event_kind_counts=_event_kind_counts(events),
        events=events,
        required_next_gates=BUDGET_CHANGE_LEDGER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def write_budget_change_ledger_outputs(
    *,
    run_dir: Path,
    ledger_report: BudgetChangeLedgerReport,
) -> None:
    write_json(
        run_dir / BUDGET_CHANGE_LEDGER_REPORT_FILENAME,
        ledger_report.model_dump(mode="json"),
    )
    ledger_rows = "\n".join(
        json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for event in ledger_report.events
    )
    (run_dir / BUDGET_CHANGE_LEDGER_FILENAME).write_text(
        ledger_rows + ("\n" if ledger_rows else ""),
        encoding="utf-8",
    )
    (run_dir / BUDGET_CHANGE_LEDGER_NOTES_FILENAME).write_text(
        render_budget_change_ledger_report(ledger_report),
        encoding="utf-8",
    )


def render_budget_change_ledger_report(report: BudgetChangeLedgerReport) -> str:
    lines = [
        "# Budget Change Ledger Report",
        "",
        f"**Report ID:** {report.budget_change_ledger_report_id}",
        f"**Ledger ID:** {report.ledger_id}",
        f"**Status:** {report.status}",
        f"**Budget proposal:** {report.budget_proposal_id}",
        f"**Revision report:** {report.budget_revision_report_id}",
        f"**Review record:** {report.budget_review_change_record_id}",
        "",
        "## Summary",
        "",
        f"- Entry count: {report.entry_count}",
        f"- Numeric change entry count: {report.numeric_change_entry_count}",
        f"- Total delta: {report.total_delta}",
        f"- Event kind counts: {report.event_kind_counts}",
        f"- Source budget mutated: {report.source_budget_mutated}",
        f"- Source revision report mutated: {report.source_revision_report_mutated}",
        f"- Superseding budget written: {report.superseding_budget_written}",
        f"- Budget submission authorized: {report.budget_submission_authorized}",
        f"- Carrier submission authorized: {report.carrier_submission_authorized}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Ledger Events",
        "",
    ]
    for event in report.events:
        lines.append(
            f"- {event.sequence_index}: {event.event_kind}; "
            f"change={event.change_id or 'none'}; field={event.field or 'none'}; "
            f"before={event.budget_total_before_event}; "
            f"after={event.budget_total_after_event}; delta={event.total_delta}"
        )
        lines.append(f"  - reason: {event.reason}")
        lines.append(
            f"  - Lake label candidate: {event.exception_lake_local_event_label}; "
            f"admission review required={event.requires_exception_lake_admission_review}"
        )
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This ledger is append-only local candidate evidence. It does not mutate budgets, admit Lake/SQLite records, submit budgets, read or write billing, or authorize learning.",
            "",
        ]
    )
    return "\n".join(lines)
