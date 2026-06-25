from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BudgetLine,
    BudgetProposal,
    CarrierCompliantProjection,
    CarrierCompliantProjectionBasis,
    CarrierCompliantProjectionLine,
)
from .util import new_id


def load_carrier_guideline(path: str | Path) -> dict[str, Any]:
    guideline = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(guideline, dict):
        raise ValueError("carrier guideline must be a mapping")
    if guideline.get("contains_real_carrier_guidelines", False):
        raise ValueError("real carrier guidelines are prohibited in this starter repository")
    if guideline.get("data_scope") != "synthetic_only":
        raise ValueError("carrier guideline artifact must be synthetic_only")
    if guideline.get("status") != "candidate":
        raise ValueError("carrier guideline artifact must be candidate status")
    return guideline


def attach_carrier_compliant_projection(
    budget: BudgetProposal,
    *,
    guideline: dict[str, Any] | None,
    guideline_ref: str,
    carrier_id: str | None,
) -> BudgetProposal:
    if guideline is None:
        return budget
    projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref=guideline_ref,
        carrier_id=carrier_id,
    )
    if projection is None:
        return budget
    return budget.model_copy(update={"carrier_compliant_projection": projection})


def build_carrier_compliant_projection(
    budget: BudgetProposal,
    *,
    guideline: dict[str, Any],
    guideline_ref: str,
    carrier_id: str | None,
) -> CarrierCompliantProjection | None:
    resolved_carrier_id = carrier_id or str(guideline.get("default_carrier_id", ""))
    carrier_rules = _carrier_rules(guideline, resolved_carrier_id)
    if carrier_rules is None:
        return None

    rate_caps = {
        str(role): float(cap) for role, cap in (carrier_rules.get("rate_caps") or {}).items()
    }
    expense_caps = {
        str(code): float(cap) for code, cap in (carrier_rules.get("expense_caps") or {}).items()
    }
    disallowed_expense_codes = {
        str(code) for code in carrier_rules.get("disallowed_expense_codes", [])
    }
    projection_lines = [
        _project_line(
            line,
            guideline_id=str(guideline.get("guideline_id", "unknown")),
            carrier_id=resolved_carrier_id,
            rate_caps=rate_caps,
            expense_caps=expense_caps,
            disallowed_expense_codes=disallowed_expense_codes,
        )
        for line in budget.lines
    ]

    proposed_subtotal_fees = budget.subtotal_fees
    compliant_subtotal_fees = (
        round(sum(line.compliant_fees or 0.0 for line in projection_lines), 2)
        if proposed_subtotal_fees is not None
        else None
    )
    proposed_subtotal_expenses = budget.subtotal_expenses
    compliant_subtotal_expenses = round(
        sum(line.compliant_expenses for line in projection_lines), 2
    )
    contingency_allowed = bool(carrier_rules.get("contingency_allowed", True))
    proposed_contingency = budget.contingency_amount
    compliant_contingency = (
        round((compliant_subtotal_fees or 0.0) * budget.contingency_percent / 100, 2)
        if proposed_subtotal_fees is not None and contingency_allowed
        else 0.0
        if proposed_subtotal_fees is not None
        else None
    )
    compliant_total = (
        round(
            (compliant_subtotal_fees or 0.0)
            + compliant_subtotal_expenses
            + (compliant_contingency or 0.0),
            2,
        )
        if budget.total_proposed_budget is not None
        else None
    )
    over_cap_amount = (
        round(max(0.0, budget.total_proposed_budget - compliant_total), 2)
        if budget.total_proposed_budget is not None and compliant_total is not None
        else 0.0
    )
    rate_cap_delta = round(
        sum(_delta(line.proposed_fees, line.compliant_fees) for line in projection_lines),
        2,
    )
    expense_cap_delta = round(
        sum(
            max(0.0, line.proposed_expenses - line.compliant_expenses) for line in projection_lines
        ),
        2,
    )
    contingency_delta = _delta(proposed_contingency, compliant_contingency)

    return CarrierCompliantProjection(
        projection_id=new_id("carrierprojection"),
        status="projected_for_human_review",
        basis=CarrierCompliantProjectionBasis(
            guideline_id=str(guideline.get("guideline_id", "unknown")),
            guideline_ref=guideline_ref,
            carrier_id=resolved_carrier_id,
            guideline_status="candidate",
            rate_caps=rate_caps,
            expense_caps=expense_caps,
            contingency_allowed=contingency_allowed,
            budget_cadence=str(carrier_rules.get("budget_cadence", "unknown")),
            variance_approval_percent=float(carrier_rules.get("variance_approval_percent", 0.0)),
        ),
        proposed_total=budget.total_proposed_budget,
        compliant_total=compliant_total,
        proposed_subtotal_fees=proposed_subtotal_fees,
        compliant_subtotal_fees=compliant_subtotal_fees,
        proposed_subtotal_expenses=proposed_subtotal_expenses,
        compliant_subtotal_expenses=compliant_subtotal_expenses,
        proposed_contingency_amount=proposed_contingency,
        compliant_contingency_amount=compliant_contingency,
        over_cap_amount=over_cap_amount,
        rate_cap_delta=rate_cap_delta,
        expense_cap_delta=expense_cap_delta,
        contingency_delta=contingency_delta,
        line_count=len(projection_lines),
        capped_line_count=sum(1 for line in projection_lines if line.capped),
        disallowed_line_count=sum(1 for line in projection_lines if line.disallowed),
        lines=projection_lines,
    )


def _carrier_rules(guideline: dict[str, Any], carrier_id: str) -> dict[str, Any] | None:
    carriers = guideline.get("carriers", {})
    if not isinstance(carriers, dict):
        return None
    rules = carriers.get(carrier_id)
    return rules if isinstance(rules, dict) else None


def _project_line(
    line: BudgetLine,
    *,
    guideline_id: str,
    carrier_id: str,
    rate_caps: dict[str, float],
    expense_caps: dict[str, float],
    disallowed_expense_codes: set[str],
) -> CarrierCompliantProjectionLine:
    guideline_refs: list[str] = []
    proposed_rate = line.hourly_rate
    compliant_rate = proposed_rate
    rate_cap_applied = False
    if proposed_rate is not None and line.staffing_role in rate_caps:
        cap = rate_caps[line.staffing_role]
        if proposed_rate > cap:
            compliant_rate = cap
            rate_cap_applied = True
            guideline_refs.append(
                _guideline_ref(guideline_id, carrier_id, f"rate_caps/{line.staffing_role}")
            )

    proposed_fees = line.estimated_fees
    compliant_fees = (
        round(line.estimated_hours * compliant_rate, 2) if compliant_rate is not None else None
    )
    proposed_expenses = line.estimated_expenses
    compliant_expenses = proposed_expenses
    expense_cap_applied = False
    disallowed = False
    if line.expense_code and line.expense_code in disallowed_expense_codes:
        compliant_expenses = 0.0
        disallowed = True
        guideline_refs.append(
            _guideline_ref(
                guideline_id, carrier_id, f"disallowed_expense_codes/{line.expense_code}"
            )
        )
    elif line.expense_code and line.expense_code in expense_caps:
        cap = expense_caps[line.expense_code]
        if proposed_expenses > cap:
            compliant_expenses = cap
            expense_cap_applied = True
            guideline_refs.append(
                _guideline_ref(guideline_id, carrier_id, f"expense_caps/{line.expense_code}")
            )

    proposed_line_total = (
        round((proposed_fees or 0.0) + proposed_expenses, 2) if proposed_fees is not None else None
    )
    compliant_line_total = (
        round((compliant_fees or 0.0) + compliant_expenses, 2)
        if compliant_fees is not None
        else None
    )
    over_cap_amount = _delta(proposed_line_total, compliant_line_total)
    capped = rate_cap_applied or expense_cap_applied
    note_parts = []
    if rate_cap_applied:
        note_parts.append(f"rate capped from {proposed_rate} to {compliant_rate}")
    if expense_cap_applied:
        note_parts.append(f"expense capped from {proposed_expenses} to {compliant_expenses}")
    if disallowed:
        note_parts.append("expense disallowed in projection")
    note = "; ".join(note_parts) if note_parts else "no guideline adjustment"

    return CarrierCompliantProjectionLine(
        phase_id=line.phase_id,
        task_id=line.task_id,
        external_code_candidate=line.external_code_candidate,
        expense_code=line.expense_code,
        staffing_role=line.staffing_role,
        proposed_hours=line.estimated_hours,
        proposed_rate=proposed_rate,
        compliant_rate=compliant_rate,
        proposed_fees=proposed_fees,
        compliant_fees=compliant_fees,
        proposed_expenses=proposed_expenses,
        compliant_expenses=compliant_expenses,
        proposed_line_total=proposed_line_total,
        compliant_line_total=compliant_line_total,
        capped=capped,
        disallowed=disallowed,
        rate_cap_applied=rate_cap_applied,
        expense_cap_applied=expense_cap_applied,
        over_cap_amount=over_cap_amount,
        guideline_refs=guideline_refs,
        note=note,
    )


def _guideline_ref(guideline_id: str, carrier_id: str, path: str) -> str:
    return f"carrier-guideline://{guideline_id}/{carrier_id}/{path}"


def _delta(proposed: float | None, compliant: float | None) -> float:
    if proposed is None or compliant is None:
        return 0.0
    return round(max(0.0, proposed - compliant), 2)
