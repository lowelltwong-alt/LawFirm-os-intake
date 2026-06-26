from __future__ import annotations

import json
from pathlib import Path

from .models import (
    BudgetActualCodeComparison,
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetActualVarianceLedgerEvent,
    BudgetActualVarianceLedgerReport,
    ExceptionLakeCandidate,
)
from .util import digest_text, now_iso, write_json


BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME = "budget_actual_variance_ledger_report.json"
BUDGET_ACTUAL_VARIANCE_LEDGER_FILENAME = "budget_actual_variance_ledger.jsonl"
BUDGET_ACTUAL_VARIANCE_LEDGER_NOTES_FILENAME = "budget_actual_variance_ledger_report.md"

BUDGET_ACTUAL_VARIANCE_LEDGER_REQUIRED_NEXT_GATES = [
    "human_actuals_variance_review",
    "orchestrator_supplies_billing_actuals_before_real_use",
    "append_only_actuals_outcome_required",
    "exception_lake_admission_by_exception_lake_runtime",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "no_silent_profile_template_budget_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _is_actuals_without_budget(
    *,
    budgeted_total: float | None,
    actual_total: float | None,
) -> bool:
    return (budgeted_total or 0) == 0 and (actual_total or 0) > 0


def _event_kind(
    *,
    scope: str,
    comparison_status: str,
    budgeted_total: float | None,
    actual_total: float | None,
) -> str:
    if comparison_status == "actuals_not_available":
        return "budget_actual_missing_actuals_recorded"
    if _is_actuals_without_budget(budgeted_total=budgeted_total, actual_total=actual_total):
        return "budget_actual_without_budget_recorded"
    if scope == "code":
        return "budget_actual_code_comparison_recorded"
    return "budget_actual_phase_comparison_recorded"


def _decision_status(
    *,
    comparison_status: str,
    budgeted_total: float | None,
    actual_total: float | None,
) -> str:
    if comparison_status == "actuals_not_available":
        return "actuals_missing_pending_source"
    if _is_actuals_without_budget(budgeted_total=budgeted_total, actual_total=actual_total):
        return "actuals_without_budget_requires_review"
    if comparison_status == "over_threshold":
        return "over_threshold_requires_review"
    if comparison_status == "under_threshold":
        return "under_threshold_requires_review"
    return "recorded_within_threshold"


def _local_event_label(decision_status: str) -> str:
    if decision_status == "recorded_within_threshold":
        return "budget_actual_cost_within_threshold_recorded"
    if decision_status == "actuals_missing_pending_source":
        return "budget_actual_missing_actuals"
    if decision_status == "actuals_without_budget_requires_review":
        return "budget_actuals_without_budget_requires_review"
    return "budget_actual_cost_variance_requires_review"


def _next_actions(decision_status: str) -> list[str]:
    if decision_status == "recorded_within_threshold":
        return [
            "preserve_comparison_as_coverage_evidence",
            "do_not_use_for_learning_without_reviewed_gate",
        ]
    if decision_status == "actuals_missing_pending_source":
        return [
            "obtain_orchestrator_supplied_actuals_source",
            "rerun_actuals_comparison",
            "block_learning_until_source_available",
        ]
    if decision_status == "actuals_without_budget_requires_review":
        return [
            "review_unbudgeted_actual_cost",
            "classify_mapping_or_scope_driver",
            "route_to_reviewed_learning_gate_if_confirmed",
        ]
    return [
        "review_budget_actual_variance",
        "classify_driver_after_human_review",
        "route_confirmed_signal_to_reviewed_learning_gate",
    ]


def _required_decisions(decision_status: str) -> list[str]:
    if decision_status == "recorded_within_threshold":
        return []
    if decision_status == "actuals_missing_pending_source":
        return [
            "confirm_actuals_source_missing_or_delayed",
            "assign_actuals_followup_owner",
        ]
    if decision_status == "actuals_without_budget_requires_review":
        return [
            "confirm_actual_cost_is_in_scope",
            "choose_template_mapping_or_scope_exception",
        ]
    return [
        "confirm_variance_is_real",
        "choose_learning_disposition_or_no_learning",
    ]


def _candidate_ids_for_event(
    *,
    decision_status: str,
    exception_candidates: list[ExceptionLakeCandidate],
) -> list[str]:
    if decision_status == "recorded_within_threshold":
        return []
    return sorted({candidate.candidate_id for candidate in exception_candidates})


def _structured_refs(
    *,
    report: BudgetActualComparisonReport,
    report_ref: str,
    scope: str,
    phase_id: str | None = None,
    code: str | None = None,
) -> list[str]:
    refs = [
        report_ref,
        f"budget-actual-comparison-report://{report.budget_actual_comparison_report_id}",
        f"budget-proposal://{report.budget_proposal_id}",
        "docs/legal-budget-design.md#actuals-comparison-boundary",
    ]
    if report.actuals_source_ref:
        refs.append(f"budget-actuals-source://{report.actuals_source_ref}")
    if report.budget_revision_report_id:
        refs.append(f"budget-revision-report://{report.budget_revision_report_id}")
    if phase_id:
        refs.append(f"budget-phase://{phase_id}")
    if code:
        refs.append(f"budget-code://{code}")
    if scope == "revision_context":
        refs.append("docs/legal-budget-design.md#budget-change-ledger")
    return refs


def _phase_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: BudgetActualComparisonReport,
    row: BudgetActualPhaseComparison,
    report_ref: str,
    exception_candidates: list[ExceptionLakeCandidate],
) -> BudgetActualVarianceLedgerEvent:
    decision_status = _decision_status(
        comparison_status=row.status,
        budgeted_total=row.budgeted_total,
        actual_total=row.actual_total,
    )
    event_kind = _event_kind(
        scope="phase",
        comparison_status=row.status,
        budgeted_total=row.budgeted_total,
        actual_total=row.actual_total,
    )
    return BudgetActualVarianceLedgerEvent(
        budget_actual_variance_ledger_event_id=_stable_id(
            "budgetactualevent",
            f"{ledger_id}|{sequence_index}|phase|{row.phase_id}|{row.status}",
        ),
        ledger_id=ledger_id,
        sequence_index=sequence_index,
        budget_actual_comparison_report_id=report.budget_actual_comparison_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_revision_report_id=report.budget_revision_report_id,
        actuals_source_ref=report.actuals_source_ref,
        comparison_budget_state=report.comparison_budget_state,
        actual_resolution_scenario_id=report.actual_resolution_scenario_id,
        comparison_scope="phase",
        phase_id=row.phase_id,
        event_kind=event_kind,  # type: ignore[arg-type]
        decision_status=decision_status,  # type: ignore[arg-type]
        local_event_label=_local_event_label(decision_status),
        comparison_status=row.status,
        budgeted_fees=_money(row.budgeted_fees),
        budgeted_expenses=_money(row.budgeted_expenses),
        budgeted_total=_money(row.budgeted_total),
        actual_fees=_money(row.actual_fees),
        actual_expenses=_money(row.actual_expenses),
        actual_total=_money(row.actual_total),
        variance_amount=_money(row.variance_amount),
        variance_percent=_money(row.variance_percent),
        variance_driver_candidates=row.variance_driver_candidates,
        learning_disposition_candidates=report.learning_disposition_candidates,
        proposed_next_actions=_next_actions(decision_status),
        required_human_decisions=_required_decisions(decision_status),
        exception_candidate_ids=_candidate_ids_for_event(
            decision_status=decision_status,
            exception_candidates=exception_candidates,
        ),
        structured_refs=_structured_refs(
            report=report,
            report_ref=report_ref,
            scope="phase",
            phase_id=row.phase_id,
        ),
        requires_human_review=decision_status != "recorded_within_threshold",
    )


def _code_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: BudgetActualComparisonReport,
    row: BudgetActualCodeComparison,
    report_ref: str,
    exception_candidates: list[ExceptionLakeCandidate],
) -> BudgetActualVarianceLedgerEvent:
    decision_status = _decision_status(
        comparison_status=row.status,
        budgeted_total=row.budgeted_total,
        actual_total=row.actual_total,
    )
    event_kind = _event_kind(
        scope="code",
        comparison_status=row.status,
        budgeted_total=row.budgeted_total,
        actual_total=row.actual_total,
    )
    return BudgetActualVarianceLedgerEvent(
        budget_actual_variance_ledger_event_id=_stable_id(
            "budgetactualevent",
            f"{ledger_id}|{sequence_index}|code|{row.code}|{row.status}",
        ),
        ledger_id=ledger_id,
        sequence_index=sequence_index,
        budget_actual_comparison_report_id=report.budget_actual_comparison_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_revision_report_id=report.budget_revision_report_id,
        actuals_source_ref=report.actuals_source_ref,
        comparison_budget_state=report.comparison_budget_state,
        actual_resolution_scenario_id=report.actual_resolution_scenario_id,
        comparison_scope="code",
        phase_id=row.phase_id,
        code=row.code,
        event_kind=event_kind,  # type: ignore[arg-type]
        decision_status=decision_status,  # type: ignore[arg-type]
        local_event_label=_local_event_label(decision_status),
        comparison_status=row.status,
        budgeted_fees=_money(row.budgeted_fees),
        budgeted_expenses=_money(row.budgeted_expenses),
        budgeted_total=_money(row.budgeted_total),
        actual_fees=_money(row.actual_fees),
        actual_expenses=_money(row.actual_expenses),
        actual_total=_money(row.actual_total),
        variance_amount=_money(row.variance_amount),
        variance_percent=_money(row.variance_percent),
        variance_driver_candidates=row.variance_driver_candidates,
        learning_disposition_candidates=report.learning_disposition_candidates,
        proposed_next_actions=_next_actions(decision_status),
        required_human_decisions=_required_decisions(decision_status),
        exception_candidate_ids=_candidate_ids_for_event(
            decision_status=decision_status,
            exception_candidates=exception_candidates,
        ),
        structured_refs=_structured_refs(
            report=report,
            report_ref=report_ref,
            scope="code",
            phase_id=row.phase_id,
            code=row.code,
        ),
        requires_human_review=decision_status != "recorded_within_threshold",
    )


def _revision_context_event(
    *,
    ledger_id: str,
    sequence_index: int,
    report: BudgetActualComparisonReport,
    report_ref: str,
    exception_candidates: list[ExceptionLakeCandidate],
) -> BudgetActualVarianceLedgerEvent:
    return BudgetActualVarianceLedgerEvent(
        budget_actual_variance_ledger_event_id=_stable_id(
            "budgetactualevent",
            f"{ledger_id}|{sequence_index}|revision_context|{report.budget_revision_report_id}",
        ),
        ledger_id=ledger_id,
        sequence_index=sequence_index,
        budget_actual_comparison_report_id=report.budget_actual_comparison_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_revision_report_id=report.budget_revision_report_id,
        actuals_source_ref=report.actuals_source_ref,
        comparison_budget_state=report.comparison_budget_state,
        actual_resolution_scenario_id=report.actual_resolution_scenario_id,
        comparison_scope="revision_context",
        event_kind="budget_actual_human_revision_context_recorded",
        decision_status="human_revision_context_requires_review",
        local_event_label="budget_actual_human_revision_context_recorded",
        comparison_status="revision_context",
        variance_driver_candidates=["human_revision_delta"],
        learning_disposition_candidates=report.learning_disposition_candidates,
        proposed_next_actions=[
            "review_actuals_against_human_revised_candidate",
            "preserve_original_and_revised_budget_lineage",
            "block_learning_until_budget_change_and_actuals_are_jointly_reviewed",
        ],
        required_human_decisions=[
            "confirm_revised_candidate_is_correct_comparison_budget",
            "confirm_variance_interpretation_accounts_for_human_revision",
        ],
        exception_candidate_ids=sorted(
            {candidate.candidate_id for candidate in exception_candidates}
        ),
        structured_refs=_structured_refs(
            report=report,
            report_ref=report_ref,
            scope="revision_context",
        ),
        requires_human_review=True,
    )


def _event_kind_counts(events: list[BudgetActualVarianceLedgerEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_kind] = counts.get(event.event_kind, 0) + 1
    return counts


def _report_status(report: BudgetActualComparisonReport) -> str:
    if report.status == "actuals_not_available":
        return "variance_ledger_no_actuals"
    if report.status == "variance_review_required":
        return "variance_ledger_ready_for_review"
    return "variance_ledger_passed"


def build_budget_actual_variance_ledger_report(
    *,
    report: BudgetActualComparisonReport,
    report_ref: str,
    exception_candidates: list[ExceptionLakeCandidate] | None = None,
) -> BudgetActualVarianceLedgerReport:
    exception_candidates = exception_candidates or []
    ledger_id = _stable_id(
        "budgetactualledger",
        f"{report.budget_actual_comparison_report_id}|{report.budget_proposal_id}",
    )
    events: list[BudgetActualVarianceLedgerEvent] = []
    for row in report.phase_comparisons:
        events.append(
            _phase_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                row=row,
                report_ref=report_ref,
                exception_candidates=exception_candidates,
            )
        )
    for row in report.code_comparisons:
        events.append(
            _code_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                row=row,
                report_ref=report_ref,
                exception_candidates=exception_candidates,
            )
        )
    if report.comparison_budget_state == "human_revised_candidate":
        events.append(
            _revision_context_event(
                ledger_id=ledger_id,
                sequence_index=len(events),
                report=report,
                report_ref=report_ref,
                exception_candidates=exception_candidates,
            )
        )
    review_statuses = {
        "over_threshold_requires_review",
        "under_threshold_requires_review",
        "actuals_without_budget_requires_review",
        "human_revision_context_requires_review",
    }
    return BudgetActualVarianceLedgerReport(
        budget_actual_variance_ledger_report_id=_stable_id(
            "budgetactualledgerreport",
            f"{ledger_id}|{report.budget_actual_comparison_report_id}",
        ),
        ledger_id=ledger_id,
        budget_actual_comparison_report_id=report.budget_actual_comparison_report_id,
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        budget_revision_report_id=report.budget_revision_report_id,
        budget_revision_report_ref=report.budget_revision_report_ref,
        actuals_source_ref=report.actuals_source_ref,
        status=_report_status(report),  # type: ignore[arg-type]
        comparison_scope=report.comparison_scope,
        comparison_budget_state=report.comparison_budget_state,
        actual_resolution_scenario_id=report.actual_resolution_scenario_id,
        entry_count=len(events),
        phase_event_count=sum(1 for event in events if event.comparison_scope == "phase"),
        code_event_count=sum(1 for event in events if event.comparison_scope == "code"),
        revision_context_event_count=sum(
            1 for event in events if event.comparison_scope == "revision_context"
        ),
        variance_review_event_count=sum(
            1 for event in events if event.decision_status in review_statuses
        ),
        missing_actuals_event_count=sum(
            1 for event in events if event.decision_status == "actuals_missing_pending_source"
        ),
        actuals_without_budget_event_count=sum(
            1
            for event in events
            if event.decision_status == "actuals_without_budget_requires_review"
        ),
        within_threshold_event_count=sum(
            1 for event in events if event.decision_status == "recorded_within_threshold"
        ),
        event_kind_counts=_event_kind_counts(events),
        total_budgeted=report.total_budgeted,
        total_actual=report.total_actual,
        total_variance_amount=report.total_variance_amount,
        total_variance_percent=report.total_variance_percent,
        events=events,
        required_next_gates=BUDGET_ACTUAL_VARIANCE_LEDGER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def write_budget_actual_variance_ledger_outputs(
    *,
    run_dir: Path,
    ledger_report: BudgetActualVarianceLedgerReport,
) -> None:
    write_json(
        run_dir / BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME,
        ledger_report.model_dump(mode="json"),
    )
    ledger_rows = "\n".join(
        json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for event in ledger_report.events
    )
    (run_dir / BUDGET_ACTUAL_VARIANCE_LEDGER_FILENAME).write_text(
        ledger_rows + ("\n" if ledger_rows else ""),
        encoding="utf-8",
    )
    (run_dir / BUDGET_ACTUAL_VARIANCE_LEDGER_NOTES_FILENAME).write_text(
        render_budget_actual_variance_ledger_report(ledger_report),
        encoding="utf-8",
    )


def render_budget_actual_variance_ledger_report(
    report: BudgetActualVarianceLedgerReport,
) -> str:
    lines = [
        "# Budget Actual Variance Ledger Report",
        "",
        f"**Report ID:** {report.budget_actual_variance_ledger_report_id}",
        f"**Ledger ID:** {report.ledger_id}",
        f"**Status:** {report.status}",
        f"**Actual comparison:** {report.budget_actual_comparison_report_id}",
        f"**Budget proposal:** {report.budget_proposal_id}",
        "",
        "## Summary",
        "",
        f"- Entry count: {report.entry_count}",
        f"- Phase event count: {report.phase_event_count}",
        f"- Code event count: {report.code_event_count}",
        f"- Revision context event count: {report.revision_context_event_count}",
        f"- Variance review event count: {report.variance_review_event_count}",
        f"- Missing actuals event count: {report.missing_actuals_event_count}",
        f"- Actuals without budget event count: {report.actuals_without_budget_event_count}",
        f"- Within threshold event count: {report.within_threshold_event_count}",
        f"- Total budgeted: {report.total_budgeted}",
        f"- Total actual: {report.total_actual}",
        f"- Total variance amount: {report.total_variance_amount}",
        f"- Event kind counts: {report.event_kind_counts}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- Billing connector read performed: {report.billing_connector_read_performed}",
        f"- Billing connector write performed: {report.billing_connector_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Events",
        "",
    ]
    for event in report.events:
        subject = event.phase_id or event.code or event.comparison_scope
        lines.append(
            f"- {event.sequence_index}: {event.event_kind}; subject={subject}; "
            f"status={event.decision_status}; budgeted={event.budgeted_total}; "
            f"actual={event.actual_total}; variance={event.variance_amount}"
        )
        lines.append(f"  - drivers: {', '.join(event.variance_driver_candidates) or 'none'}")
        lines.append(
            f"  - Lake admission review required: {event.requires_exception_lake_admission_review}"
        )
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This ledger is append-only local candidate evidence. It does not read or write billing systems, admit Lake/SQLite records, mutate budgets, submit budgets, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)
