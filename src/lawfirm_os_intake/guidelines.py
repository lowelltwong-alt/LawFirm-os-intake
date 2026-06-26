from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BudgetLine,
    BudgetProposal,
    CarrierCompliantLeverageSummary,
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
    staffing_rules = carrier_rules.get("staffing_rules") or {}
    task_role_overrides = {
        str(code): str(role)
        for code, role in (staffing_rules.get("task_role_overrides") or {}).items()
    }
    role_rates = _role_rates_from_budget_lines(budget.lines)
    projection_lines = [
        _project_line(
            line,
            guideline_id=str(guideline.get("guideline_id", "unknown")),
            carrier_id=resolved_carrier_id,
            rate_caps=rate_caps,
            expense_caps=expense_caps,
            disallowed_expense_codes=disallowed_expense_codes,
            task_role_overrides=task_role_overrides,
            role_rates=role_rates,
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
        sum(line.rate_cap_delta for line in projection_lines),
        2,
    )
    expense_cap_delta = round(sum(line.expense_cap_delta for line in projection_lines), 2)
    staffing_rule_delta = round(sum(line.staffing_rule_delta for line in projection_lines), 2)
    contingency_delta = _delta(proposed_contingency, compliant_contingency)
    proposed_blended_rate = _blended_rate(
        total_fees=proposed_subtotal_fees,
        total_hours=sum(line.proposed_hours for line in projection_lines),
    )
    compliant_blended_rate = _blended_rate(
        total_fees=compliant_subtotal_fees,
        total_hours=sum(line.proposed_hours for line in projection_lines),
    )

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
            staffing_task_role_overrides=task_role_overrides,
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
        staffing_rule_delta=staffing_rule_delta,
        contingency_delta=contingency_delta,
        proposed_blended_rate=proposed_blended_rate,
        compliant_blended_rate=compliant_blended_rate,
        blended_rate_delta=_delta(proposed_blended_rate, compliant_blended_rate),
        line_count=len(projection_lines),
        capped_line_count=sum(1 for line in projection_lines if line.capped),
        disallowed_line_count=sum(1 for line in projection_lines if line.disallowed),
        staffing_rule_adjusted_line_count=sum(
            1 for line in projection_lines if line.staffing_rule_applied
        ),
        leverage_summary=_leverage_summary(projection_lines),
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
    task_role_overrides: dict[str, str],
    role_rates: dict[str, float],
) -> CarrierCompliantProjectionLine:
    guideline_refs: list[str] = []
    compliant_staffing_role = _compliant_staffing_role(line, task_role_overrides)
    staffing_rule_applied = compliant_staffing_role != line.staffing_role
    proposed_rate = line.hourly_rate
    staffing_rule_rate = None
    if staffing_rule_applied:
        staffing_rule_rate = role_rates.get(compliant_staffing_role)
    rate_before_cap = staffing_rule_rate if staffing_rule_applied else proposed_rate
    compliant_rate = rate_before_cap
    rate_cap_applied = False
    if rate_before_cap is not None and compliant_staffing_role in rate_caps:
        cap = rate_caps[compliant_staffing_role]
        if rate_before_cap > cap:
            compliant_rate = cap
            rate_cap_applied = True
            guideline_refs.append(
                _guideline_ref(guideline_id, carrier_id, f"rate_caps/{compliant_staffing_role}")
            )
    if staffing_rule_applied:
        match_key = _staffing_rule_match_key(line, task_role_overrides)
        guideline_refs.append(
            _guideline_ref(
                guideline_id, carrier_id, f"staffing_rules/task_role_overrides/{match_key}"
            )
        )

    proposed_fees = line.estimated_fees
    staffing_rule_fees = (
        round(line.estimated_hours * staffing_rule_rate, 2)
        if staffing_rule_rate is not None
        else None
    )
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
    staffing_rule_delta = (
        _delta(proposed_fees, staffing_rule_fees) if staffing_rule_applied else 0.0
    )
    rate_cap_delta = (
        _delta(staffing_rule_fees if staffing_rule_applied else proposed_fees, compliant_fees)
        if rate_cap_applied
        else 0.0
    )
    expense_cap_delta = max(0.0, round(proposed_expenses - compliant_expenses, 2))
    capped = rate_cap_applied or expense_cap_applied
    note_parts = []
    if staffing_rule_applied:
        if staffing_rule_rate is None:
            note_parts.append(
                f"staffing role projected from {line.staffing_role} to {compliant_staffing_role}; target role rate unavailable"
            )
        else:
            note_parts.append(
                f"staffing role projected from {line.staffing_role} to {compliant_staffing_role}"
            )
    if rate_cap_applied:
        note_parts.append(f"rate capped from {rate_before_cap} to {compliant_rate}")
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
        compliant_staffing_role=compliant_staffing_role,
        proposed_hours=line.estimated_hours,
        proposed_rate=proposed_rate,
        staffing_rule_rate=staffing_rule_rate,
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
        staffing_rule_applied=staffing_rule_applied,
        over_cap_amount=over_cap_amount,
        rate_cap_delta=rate_cap_delta,
        expense_cap_delta=expense_cap_delta,
        staffing_rule_delta=staffing_rule_delta,
        guideline_refs=guideline_refs,
        note=note,
    )


def _guideline_ref(guideline_id: str, carrier_id: str, path: str) -> str:
    return f"carrier-guideline://{guideline_id}/{carrier_id}/{path}"


def _delta(proposed: float | None, compliant: float | None) -> float:
    if proposed is None or compliant is None:
        return 0.0
    return round(max(0.0, proposed - compliant), 2)


def _role_rates_from_budget_lines(lines: list[BudgetLine]) -> dict[str, float]:
    rates: dict[str, float] = {}
    for line in lines:
        if line.hourly_rate is not None and line.staffing_role not in rates:
            rates[line.staffing_role] = line.hourly_rate
    return rates


def _staffing_rule_match_key(
    line: BudgetLine,
    task_role_overrides: dict[str, str],
) -> str:
    for key in (line.external_code_candidate, line.task_id):
        if key and key in task_role_overrides:
            return key
    return line.task_id


def _compliant_staffing_role(
    line: BudgetLine,
    task_role_overrides: dict[str, str],
) -> str:
    match_key = _staffing_rule_match_key(line, task_role_overrides)
    return task_role_overrides.get(match_key, line.staffing_role)


def _blended_rate(*, total_fees: float | None, total_hours: float) -> float | None:
    if total_fees is None or total_hours <= 0:
        return None
    return round(total_fees / total_hours, 2)


def _percent(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(value / total * 100, 2)


def _leverage_summary(
    lines: list[CarrierCompliantProjectionLine],
) -> list[CarrierCompliantLeverageSummary]:
    roles = sorted(
        {
            role
            for line in lines
            for role in (line.staffing_role, line.compliant_staffing_role or line.staffing_role)
        }
    )
    proposed_hours_total = sum(line.proposed_hours for line in lines)
    compliant_hours_total = proposed_hours_total
    proposed_fees_total = sum(line.proposed_fees or 0.0 for line in lines)
    compliant_fees_total = sum(line.compliant_fees or 0.0 for line in lines)
    summaries: list[CarrierCompliantLeverageSummary] = []
    for role in roles:
        proposed_hours = sum(line.proposed_hours for line in lines if line.staffing_role == role)
        compliant_hours = sum(
            line.proposed_hours
            for line in lines
            if (line.compliant_staffing_role or line.staffing_role) == role
        )
        proposed_fees = sum(
            line.proposed_fees or 0.0 for line in lines if line.staffing_role == role
        )
        compliant_fees = sum(
            line.compliant_fees or 0.0
            for line in lines
            if (line.compliant_staffing_role or line.staffing_role) == role
        )
        summaries.append(
            CarrierCompliantLeverageSummary(
                role=role,
                proposed_hours=round(proposed_hours, 2),
                compliant_hours=round(compliant_hours, 2),
                proposed_fees=round(proposed_fees, 2),
                compliant_fees=round(compliant_fees, 2),
                proposed_hours_percent=_percent(proposed_hours, proposed_hours_total),
                compliant_hours_percent=_percent(compliant_hours, compliant_hours_total),
                proposed_fee_percent=_percent(proposed_fees, proposed_fees_total),
                compliant_fee_percent=_percent(compliant_fees, compliant_fees_total),
            )
        )
    return summaries
