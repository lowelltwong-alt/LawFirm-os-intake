from __future__ import annotations

from .models import (
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetProposal,
)
from .util import new_id, now_iso


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


def build_budget_actual_comparison_report(
    *,
    run_id: str,
    preflight_packet_id: str,
    budget: BudgetProposal,
    actuals_by_phase: dict[str, dict[str, float]] | None = None,
    actuals_source_ref: str | None = None,
    variance_threshold_percent: float = 15.0,
) -> BudgetActualComparisonReport:
    actuals = actuals_by_phase or {}
    phase_rows = _phase_budget_totals(budget)
    all_phase_ids = sorted(set(phase_rows) | set(actuals))
    comparisons: list[BudgetActualPhaseComparison] = []
    any_actuals = bool(actuals)
    any_variance_review = False
    total_budgeted = 0.0
    total_actual = 0.0

    for phase_id in all_phase_ids:
        budget_row = phase_rows.get(phase_id, {"fees": 0.0, "expenses": 0.0, "codes": set()})
        budgeted_fees = round(float(budget_row["fees"]), 2)
        budgeted_expenses = round(float(budget_row["expenses"]), 2)
        budgeted_total = round(budgeted_fees + budgeted_expenses, 2)
        total_budgeted += budgeted_total
        actual_row = actuals.get(phase_id)

        if actual_row is None:
            comparisons.append(
                BudgetActualPhaseComparison(
                    phase_id=phase_id,
                    budgeted_fees=budgeted_fees,
                    budgeted_expenses=budgeted_expenses,
                    budgeted_total=budgeted_total,
                    status="actuals_not_available",
                    external_code_candidates=sorted(budget_row["codes"]),  # type: ignore[arg-type]
                )
            )
            continue

        actual_fees = round(float(actual_row.get("fees", 0.0)), 2)
        actual_expenses = round(float(actual_row.get("expenses", 0.0)), 2)
        actual_total = round(actual_fees + actual_expenses, 2)
        total_actual += actual_total
        variance_amount = round(actual_total - budgeted_total, 2)
        variance_percent = (
            round((variance_amount / budgeted_total) * 100, 2) if budgeted_total else None
        )
        if variance_percent is None or abs(variance_percent) <= variance_threshold_percent:
            status = "within_threshold"
        elif variance_percent > variance_threshold_percent:
            status = "over_threshold"
            any_variance_review = True
        else:
            status = "under_threshold"
            any_variance_review = True
        comparisons.append(
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
                status=status,
                external_code_candidates=sorted(budget_row["codes"]),  # type: ignore[arg-type]
            )
        )

    total_budgeted = round(total_budgeted, 2)
    total_actual_value = round(total_actual, 2) if any_actuals else None
    total_variance_amount = (
        round(total_actual - total_budgeted, 2) if total_actual_value is not None else None
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
    return BudgetActualComparisonReport(
        budget_actual_comparison_report_id=new_id("budgetactuals"),
        run_id=run_id,
        preflight_packet_id=preflight_packet_id,
        budget_proposal_id=budget.budget_proposal_id,
        status=status,
        phase_comparisons=comparisons,
        variance_threshold_percent=variance_threshold_percent,
        total_budgeted=total_budgeted,
        total_actual=total_actual_value,
        total_variance_amount=total_variance_amount,
        total_variance_percent=total_variance_percent,
        actuals_source_ref=actuals_source_ref,
        generated_at=now_iso(),
    )
