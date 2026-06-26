from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetActualAmount,
    BudgetActualCodeComparison,
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetActualsSource,
    BudgetActualVarianceDriverCandidate,
    BudgetCodeBudgetSnapshot,
    BudgetProposal,
    BudgetRevisionReport,
    ExceptionLakeCandidate,
)
from .util import append_jsonl, load_json, new_id, now_iso, write_json


BUDGET_ACTUAL_COMPARISON_REPORT_FILENAME = "budget_actual_comparison_report.json"
BUDGET_ACTUAL_COMPARISON_NOTES_FILENAME = "budget_actual_comparison_report.md"
BUDGET_ACTUAL_VARIANCE_CANDIDATES_FILENAME = "budget_actual_variance_candidates.jsonl"


def _phase_budget_totals(budget: BudgetProposal) -> dict[str, dict[str, float | set[str]]]:
    totals: dict[str, dict[str, float | set[str]]] = {}
    for line in budget.lines:
        row = totals.setdefault(
            line.phase_id,
            {"fees": 0.0, "expenses": 0.0, "codes": set()},
        )
        row["fees"] = float(row["fees"]) + float(line.estimated_fees or 0.0)
        row["expenses"] = float(row["expenses"]) + float(line.estimated_expenses or 0.0)
        codes = row["codes"]
        if isinstance(codes, set):
            if line.external_code_candidate:
                codes.add(line.external_code_candidate)
            if line.expense_code:
                codes.add(line.expense_code)
    return totals


def _code_budget_totals(budget: BudgetProposal) -> dict[str, BudgetCodeBudgetSnapshot]:
    rows: dict[str, dict[str, Any]] = {}
    for line in budget.lines:
        if line.external_code_candidate:
            fee_row = rows.setdefault(
                line.external_code_candidate,
                {"fees": 0.0, "expenses": 0.0, "phase_ids": set()},
            )
            fee_row["fees"] += float(line.estimated_fees or 0.0)
            fee_row["phase_ids"].add(line.phase_id)
        expense_code = line.expense_code or line.external_code_candidate
        if expense_code:
            expense_row = rows.setdefault(
                expense_code,
                {"fees": 0.0, "expenses": 0.0, "phase_ids": set()},
            )
            expense_row["expenses"] += float(line.estimated_expenses or 0.0)
            expense_row["phase_ids"].add(line.phase_id)
    snapshots = {}
    for code, row in rows.items():
        phase_ids = sorted(row["phase_ids"])
        phase_id = phase_ids[0] if len(phase_ids) == 1 else None
        snapshots[code] = BudgetCodeBudgetSnapshot(
            code=code,
            phase_id=phase_id,
            budgeted_fees=round(row["fees"], 2),
            budgeted_expenses=round(row["expenses"], 2),
            budgeted_total=round(row["fees"] + row["expenses"], 2),
        )
    return snapshots


def _phase_rows_from_revision(
    revision_report: BudgetRevisionReport,
) -> dict[str, dict[str, float | set[str]]]:
    rows: dict[str, dict[str, float | set[str]]] = {}
    for snapshot in revision_report.revised_phase_totals:
        rows[snapshot.phase_id] = {
            "fees": float(snapshot.budgeted_fees or 0.0),
            "expenses": float(snapshot.budgeted_expenses),
            "codes": set(snapshot.external_code_candidates),
        }
    return rows


def _code_rows_from_revision(
    revision_report: BudgetRevisionReport,
) -> dict[str, BudgetCodeBudgetSnapshot]:
    return {snapshot.code: snapshot for snapshot in revision_report.revised_code_totals}


def _coerce_amounts(
    values: dict[str, dict[str, float] | BudgetActualAmount],
) -> dict[str, BudgetActualAmount]:
    amounts: dict[str, BudgetActualAmount] = {}
    for key, value in values.items():
        if isinstance(value, BudgetActualAmount):
            amounts[key] = value
        else:
            amounts[key] = BudgetActualAmount.model_validate(value)
    return amounts


def _status_and_percent(
    *,
    budgeted_total: float,
    actual_total: float,
    threshold: float,
) -> tuple[str, float | None, float]:
    variance_amount = round(actual_total - budgeted_total, 2)
    if budgeted_total == 0 and actual_total > 0:
        return "over_threshold", None, variance_amount
    variance_percent = (
        round((variance_amount / budgeted_total) * 100, 2) if budgeted_total else None
    )
    if variance_percent is None or abs(variance_percent) <= threshold:
        return "within_threshold", variance_percent, variance_amount
    if variance_percent > threshold:
        return "over_threshold", variance_percent, variance_amount
    return "under_threshold", variance_percent, variance_amount


def _driver_candidates_for_row(
    *,
    phase_id: str | None,
    code: str | None,
    budgeted_fees: float,
    budgeted_expenses: float,
    actual_fees: float,
    actual_expenses: float,
    variance_amount: float,
    status: str,
) -> list[BudgetActualVarianceDriverCandidate]:
    if status not in {"over_threshold", "under_threshold"}:
        return []
    if budgeted_fees + budgeted_expenses == 0 and actual_fees + actual_expenses > 0:
        return [
            BudgetActualVarianceDriverCandidate(
                candidate_id=new_id("budgetvardriver"),
                driver_label="actuals_without_budget",
                phase_id=phase_id,
                code=code,
                variance_amount=variance_amount,
                reason="Actual costs exist where the comparison budget has zero budgeted amount.",
                target_learning_loop="template_mapping",
            )
        ]
    fee_variance = actual_fees - budgeted_fees
    expense_variance = actual_expenses - budgeted_expenses
    if abs(expense_variance) > abs(fee_variance):
        label = "expense_overrun" if expense_variance > 0 else "expense_underrun"
    else:
        label = "fee_overrun" if fee_variance > 0 else "fee_underrun"
    return [
        BudgetActualVarianceDriverCandidate(
            candidate_id=new_id("budgetvardriver"),
            driver_label=label,  # type: ignore[arg-type]
            phase_id=phase_id,
            code=code,
            variance_amount=variance_amount,
            reason=(
                "Actual cost variance exceeded the configured threshold and requires "
                "human review before any learning or template change."
            ),
            target_learning_loop="budget_driver",
        )
    ]


def _phase_comparison(
    *,
    phase_id: str,
    budget_row: dict[str, float | set[str]],
    actual_row: BudgetActualAmount | None,
    threshold: float,
) -> tuple[BudgetActualPhaseComparison, list[BudgetActualVarianceDriverCandidate], float]:
    budgeted_fees = round(float(budget_row["fees"]), 2)
    budgeted_expenses = round(float(budget_row["expenses"]), 2)
    budgeted_total = round(budgeted_fees + budgeted_expenses, 2)
    codes = sorted(budget_row["codes"]) if isinstance(budget_row["codes"], set) else []
    if actual_row is None:
        return (
            BudgetActualPhaseComparison(
                phase_id=phase_id,
                budgeted_fees=budgeted_fees,
                budgeted_expenses=budgeted_expenses,
                budgeted_total=budgeted_total,
                status="actuals_not_available",
                external_code_candidates=codes,
            ),
            [],
            0.0,
        )
    actual_fees = round(actual_row.fees, 2)
    actual_expenses = round(actual_row.expenses, 2)
    actual_total = round(actual_fees + actual_expenses, 2)
    status, variance_percent, variance_amount = _status_and_percent(
        budgeted_total=budgeted_total,
        actual_total=actual_total,
        threshold=threshold,
    )
    drivers = _driver_candidates_for_row(
        phase_id=phase_id,
        code=None,
        budgeted_fees=budgeted_fees,
        budgeted_expenses=budgeted_expenses,
        actual_fees=actual_fees,
        actual_expenses=actual_expenses,
        variance_amount=variance_amount,
        status=status,
    )
    return (
        BudgetActualPhaseComparison(
            phase_id=phase_id,
            budgeted_fees=budgeted_fees,
            budgeted_expenses=budgeted_expenses,
            budgeted_total=budgeted_total,
            actual_fees=actual_fees,
            actual_expenses=actual_expenses,
            actual_total=actual_total,
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            status=status,  # type: ignore[arg-type]
            external_code_candidates=codes,
            variance_driver_candidates=[driver.driver_label for driver in drivers],
        ),
        drivers,
        actual_total,
    )


def _code_comparison(
    *,
    code: str,
    budget_row: BudgetCodeBudgetSnapshot | None,
    actual_row: BudgetActualAmount | None,
    threshold: float,
) -> tuple[BudgetActualCodeComparison, list[BudgetActualVarianceDriverCandidate], float]:
    budgeted_fees = round(budget_row.budgeted_fees if budget_row else 0.0, 2)
    budgeted_expenses = round(budget_row.budgeted_expenses if budget_row else 0.0, 2)
    budgeted_total = round(budgeted_fees + budgeted_expenses, 2)
    phase_id = budget_row.phase_id if budget_row else None
    if actual_row is None:
        return (
            BudgetActualCodeComparison(
                code=code,
                phase_id=phase_id,
                budgeted_fees=budgeted_fees,
                budgeted_expenses=budgeted_expenses,
                budgeted_total=budgeted_total,
                status="actuals_not_available",
            ),
            [],
            0.0,
        )
    actual_fees = round(actual_row.fees, 2)
    actual_expenses = round(actual_row.expenses, 2)
    actual_total = round(actual_fees + actual_expenses, 2)
    status, variance_percent, variance_amount = _status_and_percent(
        budgeted_total=budgeted_total,
        actual_total=actual_total,
        threshold=threshold,
    )
    drivers = _driver_candidates_for_row(
        phase_id=phase_id,
        code=code,
        budgeted_fees=budgeted_fees,
        budgeted_expenses=budgeted_expenses,
        actual_fees=actual_fees,
        actual_expenses=actual_expenses,
        variance_amount=variance_amount,
        status=status,
    )
    return (
        BudgetActualCodeComparison(
            code=code,
            phase_id=phase_id,
            budgeted_fees=budgeted_fees,
            budgeted_expenses=budgeted_expenses,
            budgeted_total=budgeted_total,
            actual_fees=actual_fees,
            actual_expenses=actual_expenses,
            actual_total=actual_total,
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            status=status,  # type: ignore[arg-type]
            variance_driver_candidates=[driver.driver_label for driver in drivers],
        ),
        drivers,
        actual_total,
    )


def build_budget_actual_comparison_report(
    *,
    run_id: str,
    preflight_packet_id: str,
    budget: BudgetProposal,
    actuals_by_phase: dict[str, dict[str, float] | BudgetActualAmount] | None = None,
    actuals_by_code: dict[str, dict[str, float] | BudgetActualAmount] | None = None,
    actuals_source_ref: str | None = None,
    variance_threshold_percent: float = 15.0,
    budget_revision_report: BudgetRevisionReport | None = None,
    budget_revision_report_ref: str | None = None,
    actual_resolution_scenario_id: str | None = None,
) -> BudgetActualComparisonReport:
    phase_actuals = _coerce_amounts(actuals_by_phase or {})
    code_actuals = _coerce_amounts(actuals_by_code or {})
    if budget_revision_report is not None:
        phase_rows = _phase_rows_from_revision(budget_revision_report)
        code_rows = _code_rows_from_revision(budget_revision_report)
        comparison_budget_state = "human_revised_candidate"
    else:
        phase_rows = _phase_budget_totals(budget)
        code_rows = _code_budget_totals(budget)
        comparison_budget_state = "original_proposal"
    all_phase_ids = sorted(set(phase_rows) | set(phase_actuals))
    phase_comparisons: list[BudgetActualPhaseComparison] = []
    code_comparisons: list[BudgetActualCodeComparison] = []
    variance_drivers: list[BudgetActualVarianceDriverCandidate] = []
    total_budgeted = 0.0
    total_actual_phase = 0.0

    for phase_id in all_phase_ids:
        budget_row = phase_rows.get(phase_id, {"fees": 0.0, "expenses": 0.0, "codes": set()})
        total_budgeted += round(float(budget_row["fees"]) + float(budget_row["expenses"]), 2)
        comparison, drivers, actual_total = _phase_comparison(
            phase_id=phase_id,
            budget_row=budget_row,
            actual_row=phase_actuals.get(phase_id),
            threshold=variance_threshold_percent,
        )
        phase_comparisons.append(comparison)
        variance_drivers.extend(drivers)
        total_actual_phase += actual_total

    total_actual_code = 0.0
    if code_actuals:
        for code in sorted(set(code_rows) | set(code_actuals)):
            comparison, drivers, actual_total = _code_comparison(
                code=code,
                budget_row=code_rows.get(code),
                actual_row=code_actuals.get(code),
                threshold=variance_threshold_percent,
            )
            code_comparisons.append(comparison)
            variance_drivers.extend(drivers)
            total_actual_code += actual_total
    if budget_revision_report is not None and budget_revision_report.total_delta:
        variance_drivers.append(
            BudgetActualVarianceDriverCandidate(
                candidate_id=new_id("budgetvardriver"),
                driver_label="human_revision_delta",
                variance_amount=budget_revision_report.total_delta,
                reason=(
                    "Human budget review changed the comparison budget; actuals should be "
                    "interpreted against the append-only revised candidate."
                ),
                target_learning_loop="budget_driver",
            )
        )

    any_actuals = bool(phase_actuals or code_actuals)
    any_variance_review = any(
        row.status in {"over_threshold", "under_threshold"}
        for row in [*phase_comparisons, *code_comparisons]
    )
    total_budgeted = round(total_budgeted, 2)
    if phase_actuals:
        total_actual_value = round(total_actual_phase, 2)
    elif code_actuals:
        total_actual_value = round(total_actual_code, 2)
    else:
        total_actual_value = None
    total_variance_amount = (
        round(total_actual_value - total_budgeted, 2) if total_actual_value is not None else None
    )
    total_variance_percent = (
        round((total_variance_amount / total_budgeted) * 100, 2)
        if total_variance_amount is not None and total_budgeted
        else None
    )
    if not any_actuals:
        status = "actuals_not_available"
    elif any_variance_review:
        status = "variance_review_required"
    else:
        status = "passed"
    learning_disposition_candidates = sorted(
        {driver.target_learning_loop for driver in variance_drivers}
    )
    return BudgetActualComparisonReport(
        budget_actual_comparison_report_id=new_id("budgetactuals"),
        run_id=run_id,
        preflight_packet_id=preflight_packet_id,
        budget_proposal_id=budget.budget_proposal_id,
        status=status,
        comparison_scope="phase_and_code" if code_comparisons else "phase",
        comparison_budget_state=comparison_budget_state,  # type: ignore[arg-type]
        budget_revision_report_id=(
            budget_revision_report.budget_revision_report_id
            if budget_revision_report is not None
            else None
        ),
        budget_revision_report_ref=budget_revision_report_ref,
        actual_resolution_scenario_id=actual_resolution_scenario_id,
        phase_comparisons=phase_comparisons,
        code_comparisons=code_comparisons,
        variance_driver_candidates=variance_drivers,
        learning_disposition_candidates=learning_disposition_candidates,
        variance_threshold_percent=variance_threshold_percent,
        total_budgeted=total_budgeted,
        total_actual=total_actual_value,
        total_variance_amount=total_variance_amount,
        total_variance_percent=total_variance_percent,
        actuals_source_ref=actuals_source_ref,
        generated_at=now_iso(),
    )


def build_budget_actual_variance_exception_candidates(
    report: BudgetActualComparisonReport,
    report_ref: str,
) -> list[ExceptionLakeCandidate]:
    if report.status != "variance_review_required":
        return []
    phase_ids = [
        row.phase_id
        for row in report.phase_comparisons
        if row.status in {"over_threshold", "under_threshold"}
    ]
    codes = [
        row.code
        for row in report.code_comparisons
        if row.status in {"over_threshold", "under_threshold"}
    ]
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=report.run_id,
            preflight_packet_id=report.preflight_packet_id,
            local_event_label="budget_actual_cost_variance_requires_review",
            canonical_lake_class="workflow_escalation",
            reason=(
                "Budget actual-cost comparison exceeded variance threshold for phase(s) "
                f"{', '.join(phase_ids) or 'none'} and code(s) {', '.join(codes) or 'none'}."
            ),
            structured_refs=[
                report_ref,
                f"budget-proposal://{report.budget_proposal_id}",
                "docs/legal-budget-design.md#actuals-comparison-boundary",
            ],
            blocked_state="budget_actual_variance_requires_review",
        )
    ]


def render_budget_actual_comparison_report(report: BudgetActualComparisonReport) -> str:
    lines = [
        "# Budget Actual Comparison Report",
        "",
        f"**Report ID:** {report.budget_actual_comparison_report_id}",
        f"**Status:** {report.status}",
        f"**Scope:** {report.comparison_scope}",
        f"**Comparison budget state:** {report.comparison_budget_state}",
        "",
        "## Summary",
        "",
        f"- Total budgeted: {report.total_budgeted}",
        f"- Total actual: {report.total_actual}",
        f"- Total variance amount: {report.total_variance_amount}",
        f"- Total variance percent: {report.total_variance_percent}",
        f"- Billing connector read performed: {report.billing_connector_read_performed}",
        f"- Billing connector write performed: {report.billing_connector_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        "",
        "## Phase Comparisons",
        "",
    ]
    for row in report.phase_comparisons:
        lines.append(
            f"- {row.phase_id}: budgeted={row.budgeted_total}; actual={row.actual_total}; "
            f"variance={row.variance_amount} ({row.variance_percent}%); status={row.status}; "
            f"drivers={', '.join(row.variance_driver_candidates) or 'none'}"
        )
    lines.extend(["", "## Code Comparisons", ""])
    if not report.code_comparisons:
        lines.append("- none")
    for row in report.code_comparisons:
        lines.append(
            f"- {row.code}: budgeted={row.budgeted_total}; actual={row.actual_total}; "
            f"variance={row.variance_amount} ({row.variance_percent}%); status={row.status}; "
            f"drivers={', '.join(row.variance_driver_candidates) or 'none'}"
        )
    lines.extend(
        [
            "",
            "## Learning Candidates",
            "",
            *(f"- {item}" for item in report.learning_disposition_candidates or ["none"]),
            "",
            "This report uses synthetic or Orchestrator-supplied actuals only. Intake does not read billing, write billing, admit Lake records, mutate budget profiles, or silently learn from variance.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_actual_comparison(
    *,
    budget_path: str | Path,
    actuals_path: str | Path,
    out_dir: str | Path,
    budget_revision_report_path: str | Path | None = None,
) -> tuple[BudgetActualComparisonReport, Path]:
    budget_path = Path(budget_path)
    actuals_path = Path(actuals_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    budget = BudgetProposal.model_validate(load_json(budget_path))
    actuals_source = BudgetActualsSource.model_validate(load_json(actuals_path))
    if actuals_source.budget_proposal_id not in {None, "__BUDGET_PROPOSAL_ID__"}:
        if actuals_source.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError(
                "actuals source budget_proposal_id does not match proposal: "
                f"{actuals_source.budget_proposal_id} != {budget.budget_proposal_id}"
            )
    revision_report = None
    revision_report_ref = None
    if budget_revision_report_path is not None:
        revision_report_path = Path(budget_revision_report_path)
        revision_report = BudgetRevisionReport.model_validate(load_json(revision_report_path))
        if revision_report.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError(
                "budget revision report budget_proposal_id does not match proposal: "
                f"{revision_report.budget_proposal_id} != {budget.budget_proposal_id}"
            )
        revision_report_ref = str(revision_report_path)
    report = build_budget_actual_comparison_report(
        run_id=revision_report.run_id if revision_report else new_id("budgetactualrun"),
        preflight_packet_id=budget.preflight_packet_id,
        budget=budget,
        actuals_by_phase=actuals_source.actuals_by_phase,
        actuals_by_code=actuals_source.actuals_by_code,
        actuals_source_ref=actuals_source.source_ref or str(actuals_path),
        budget_revision_report=revision_report,
        budget_revision_report_ref=revision_report_ref,
        actual_resolution_scenario_id=actuals_source.actual_resolution_scenario_id,
    )
    report_path = run_dir / BUDGET_ACTUAL_COMPARISON_REPORT_FILENAME
    notes_path = run_dir / BUDGET_ACTUAL_COMPARISON_NOTES_FILENAME
    candidates_path = run_dir / BUDGET_ACTUAL_VARIANCE_CANDIDATES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_budget_actual_comparison_report(report), encoding="utf-8")
    candidates_path.touch()
    for candidate in build_budget_actual_variance_exception_candidates(report, str(report_path)):
        append_jsonl(candidates_path, candidate.model_dump(mode="json"))
    return report, run_dir
