from __future__ import annotations

from typing import Any

from .drivers import CaseDriverProfile
from .models import (
    BudgetCalculationReport,
    BudgetLine,
    BudgetProposal,
    BudgetScenario,
    BudgetScenarioSet,
    BudgetSupportItem,
    EvidenceRef,
    HumanConfirmation,
    IntakePreflightPacket,
)
from .util import new_id

DEFAULT_SCENARIOS = [
    {
        "scenario_id": "early_resolution",
        "scenario_name": "Early Resolution",
        "resolution_phase": "L200",
        "description": "Motion to dismiss granted or pre-discovery settlement.",
    },
    {
        "scenario_id": "standard",
        "scenario_name": "Standard",
        "resolution_phase": "L300",
        "description": "Resolves at mediation or on summary judgment after discovery.",
    },
    {
        "scenario_id": "through_trial",
        "scenario_name": "Through Trial",
        "resolution_phase": "L400",
        "description": "Full discovery, dispositive motions, trial preparation, and trial.",
    },
]


def _budget_template(profile: dict[str, Any], matter_family: str) -> dict[str, Any] | None:
    templates = profile.get("budget_templates", {})
    return templates.get(matter_family)


def _confirmation_ref(confirmation: HumanConfirmation) -> str:
    return f"human-confirmation://{confirmation.confirmation_id}"


def _template_ref(profile: dict[str, Any], matter_family: str, path: str) -> str:
    return f"practice-profile://{profile['profile_id']}/budget_templates/{matter_family}/{path}"


def _policy_ref(path: str) -> str:
    return f"workflow-policy://budget-boundary/{path}"


def _confirmed_matter_observed_refs(
    packet: IntakePreflightPacket, confirmation: HumanConfirmation
) -> list[EvidenceRef]:
    for candidate in packet.matter_family_candidates:
        if (
            candidate.label == confirmation.confirmed_matter_family
            and candidate.source_evidence_status == "observed_support"
        ):
            return candidate.observed_evidence_refs[:3]
    return []


def _support_item(
    item_type: str,
    text: str,
    source_kind: str,
    *,
    evidence_refs: list[EvidenceRef] | None = None,
    structured_ref: str | None = None,
) -> BudgetSupportItem:
    return BudgetSupportItem(
        item_type=item_type,  # type: ignore[arg-type]
        text=text,
        source_kind=source_kind,  # type: ignore[arg-type]
        evidence_refs=evidence_refs or [],
        structured_ref=structured_ref,
    )


def _template_support_items(
    profile: dict[str, Any],
    matter_family: str,
    template: dict[str, Any],
) -> list[BudgetSupportItem]:
    items: list[BudgetSupportItem] = []
    for item_type in ("assumptions", "exclusions", "unknowns"):
        singular = item_type[:-1] if item_type != "unknowns" else "unknown"
        for index, text in enumerate(template.get(item_type, [])):
            items.append(
                _support_item(
                    singular,
                    str(text),
                    "synthetic_practice_profile",
                    structured_ref=_template_ref(profile, matter_family, f"{item_type}/{index}"),
                )
            )

    for phase in template.get("phases", []):
        phase_id = str(phase["phase_id"])
        for task in phase.get("tasks", []):
            task_id = str(task["task_id"])
            for index, text in enumerate(task.get("assumptions", [])):
                items.append(
                    _support_item(
                        "assumption",
                        str(text),
                        "synthetic_practice_profile",
                        structured_ref=_template_ref(
                            profile,
                            matter_family,
                            f"phases/{phase_id}/tasks/{task_id}/assumptions/{index}",
                        ),
                    )
                )
    return items


def _workflow_exclusion_support_items(exclusions: list[str]) -> list[BudgetSupportItem]:
    return [
        _support_item(
            "exclusion",
            text,
            "workflow_policy",
            structured_ref=_policy_ref(text.replace("/", "-").replace(" ", "-")),
        )
        for text in exclusions
    ]


def _numeric_driver_values(
    case_drivers: CaseDriverProfile | None,
) -> dict[str, tuple[float, str]]:
    """Usable (numeric, known) driver values for hour scaling, keyed by driver id.

    Drivers that are ``unknown`` or non-numeric are excluded so a scaled task falls
    back to its template hours rather than inventing a number.
    """

    values: dict[str, tuple[float, str]] = {}
    if case_drivers is None:
        return values
    for driver in case_drivers.drivers:
        if driver.provenance == "unknown":
            continue
        if isinstance(driver.value, bool) or not isinstance(driver.value, (int, float)):
            continue
        values[driver.driver_id] = (float(driver.value), driver.provenance)
    return values


def _phase_order(template: dict[str, Any]) -> list[str]:
    return [str(phase["phase_id"]) for phase in template.get("phases", [])]


def _scenario_definitions(template: dict[str, Any]) -> list[dict[str, str]]:
    raw = template.get("scenarios") or DEFAULT_SCENARIOS
    definitions: list[dict[str, str]] = []
    for scenario in raw:
        scenario_id = str(scenario["scenario_id"])
        definitions.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": str(
                    scenario.get("scenario_name") or scenario_id.replace("_", " ").title()
                ),
                "resolution_phase": str(scenario["resolution_phase"]),
                "description": str(scenario.get("description", "")),
            }
        )
    return definitions


def _included_phase_ids(phase_order: list[str], resolution_phase: str) -> list[str]:
    if not phase_order:
        return []
    if resolution_phase not in phase_order:
        return phase_order[:]
    return phase_order[: phase_order.index(resolution_phase) + 1]


def _lines_for_phases(lines: list[BudgetLine], included_phase_ids: list[str]) -> list[BudgetLine]:
    if not included_phase_ids:
        return lines[:]
    included = set(included_phase_ids)
    return [line for line in lines if line.phase_id in included]


def _line_external_codes(lines: list[BudgetLine]) -> list[str]:
    codes: set[str] = set()
    for line in lines:
        if line.external_code_candidate:
            codes.add(line.external_code_candidate)
        if line.expense_code:
            codes.add(line.expense_code)
    return sorted(codes)


def _budget_totals(
    lines: list[BudgetLine],
    contingency_percent: float,
) -> tuple[float | None, float, float | None, float | None, float | None, float | None]:
    all_priced = all(line.hourly_rate is not None for line in lines)
    subtotal_fees = (
        round(sum(line.estimated_fees or 0 for line in lines), 2) if all_priced else None
    )
    subtotal_expenses = round(sum(line.estimated_expenses for line in lines), 2)
    contingency_amount = (
        round((subtotal_fees or 0) * contingency_percent / 100, 2) if all_priced else None
    )
    total = (
        round((subtotal_fees or 0) + subtotal_expenses + (contingency_amount or 0), 2)
        if all_priced
        else None
    )
    total_min = None
    total_max = None
    if all_priced:
        min_fees = round(
            sum(
                (line.estimated_hours_min or line.estimated_hours) * (line.hourly_rate or 0)
                for line in lines
            ),
            2,
        )
        max_fees = round(
            sum(
                (line.estimated_hours_max or line.estimated_hours) * (line.hourly_rate or 0)
                for line in lines
            ),
            2,
        )
        min_contingency = round(min_fees * contingency_percent / 100, 2)
        max_contingency = round(max_fees * contingency_percent / 100, 2)
        total_min = round(min_fees + subtotal_expenses + min_contingency, 2)
        total_max = round(max_fees + subtotal_expenses + max_contingency, 2)
    return (
        subtotal_fees,
        subtotal_expenses,
        contingency_amount,
        total,
        total_min,
        total_max,
    )


def _pricing_status(lines: list[BudgetLine]) -> str:
    if not lines:
        return "insufficient_information"
    return "priced" if all(line.hourly_rate is not None for line in lines) else "hours_only"


def _calculation_report(
    lines: list[BudgetLine],
    contingency_percent: float,
    *,
    mode: str,
) -> BudgetCalculationReport:
    (
        subtotal_fees,
        subtotal_expenses,
        contingency_amount,
        total,
        _total_min,
        _total_max,
    ) = _budget_totals(lines, contingency_percent)
    return BudgetCalculationReport(
        calculation_report_id=new_id("calcreport"),
        mode=mode,  # type: ignore[arg-type]
        line_count=len(lines),
        total_hours=round(sum(line.estimated_hours for line in lines), 2),
        priced_line_count=sum(1 for line in lines if line.hourly_rate is not None),
        unpriced_line_count=sum(1 for line in lines if line.hourly_rate is None),
        subtotal_fees=subtotal_fees,
        subtotal_expenses=subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=contingency_amount,
        total_proposed_budget=total,
        rate_sources=sorted({line.rate_source for line in lines}),
    )


def _build_scenario_set(
    template: dict[str, Any],
    lines: list[BudgetLine],
    contingency_percent: float,
) -> BudgetScenarioSet:
    phase_order = _phase_order(template)
    scenarios: list[BudgetScenario] = []
    for definition in _scenario_definitions(template):
        included_phase_ids = _included_phase_ids(phase_order, definition["resolution_phase"])
        scenario_lines = _lines_for_phases(lines, included_phase_ids)
        (
            subtotal_fees,
            subtotal_expenses,
            contingency_amount,
            total,
            total_min,
            total_max,
        ) = _budget_totals(scenario_lines, contingency_percent)
        scenarios.append(
            BudgetScenario(
                scenario_id=definition["scenario_id"],
                scenario_name=definition["scenario_name"],
                description=definition["description"],
                resolution_phase=definition["resolution_phase"],
                included_phase_ids=included_phase_ids,
                included_external_codes=_line_external_codes(scenario_lines),
                included_line_count=len(scenario_lines),
                total_hours=round(sum(line.estimated_hours for line in scenario_lines), 2),
                subtotal_fees=subtotal_fees,
                subtotal_expenses=subtotal_expenses,
                contingency_percent=contingency_percent,
                contingency_amount=contingency_amount,
                total_proposed_budget=total,
                total_budget_min=total_min,
                total_budget_max=total_max,
                pricing_status=_pricing_status(scenario_lines),  # type: ignore[arg-type]
            )
        )

    priced_totals = [scenario.total_proposed_budget for scenario in scenarios]
    if all(total is not None for total in priced_totals):
        monotonic = all(
            float(priced_totals[index]) <= float(priced_totals[index + 1])
            for index in range(len(priced_totals) - 1)
        )
        basis = "total_proposed_budget"
    else:
        hours = [scenario.total_hours for scenario in scenarios]
        monotonic = all(hours[index] <= hours[index + 1] for index in range(len(hours) - 1))
        basis = "total_hours"
    scenario_ids = {scenario.scenario_id for scenario in scenarios}
    selected = "standard" if "standard" in scenario_ids else scenarios[-1].scenario_id
    return BudgetScenarioSet(
        scenario_set_id=new_id("budgetscenarios"),
        selected_scenario_id=selected,
        standard_scenario_id=selected,
        scenarios=scenarios,
        monotonic_total_order=monotonic,
        total_order_basis=basis,  # type: ignore[arg-type]
    )


def _selected_scenario_lines(
    template: dict[str, Any],
    lines: list[BudgetLine],
    scenario_set: BudgetScenarioSet,
) -> list[BudgetLine]:
    selected = next(
        scenario
        for scenario in scenario_set.scenarios
        if scenario.scenario_id == scenario_set.selected_scenario_id
    )
    included_phase_ids = _included_phase_ids(_phase_order(template), selected.resolution_phase)
    return _lines_for_phases(lines, included_phase_ids)


def build_budget_proposal(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    profile: dict[str, Any],
    case_drivers: CaseDriverProfile | None = None,
) -> BudgetProposal:
    if confirmation.status != "confirmed":
        raise ValueError("human confirmation must be confirmed before budget generation")
    if (
        not confirmation.confirmed_matter_family
        or not confirmation.confirmed_representation_posture
    ):
        raise ValueError("confirmed matter family and representation posture are required")

    template = _budget_template(profile, confirmation.confirmed_matter_family)
    if not template:
        unknown = "no approved synthetic budget template exists for the confirmed matter family"
        exclusions = [
            "client submission",
            "carrier submission",
            "matter opening",
            "conflict clearance",
        ]
        return BudgetProposal(
            budget_proposal_id=new_id("budget"),
            preflight_packet_id=packet.packet_id,
            confirmation_id=confirmation.confirmation_id,
            practice_profile_id=str(profile["profile_id"]),
            matter_family=confirmation.confirmed_matter_family,
            representation_posture=confirmation.confirmed_representation_posture,
            pricing_status="insufficient_information",
            lines=[],
            calculation_report=BudgetCalculationReport(
                calculation_report_id=new_id("calcreport"),
                mode="insufficient_information",
                line_count=0,
                total_hours=0,
                priced_line_count=0,
                unpriced_line_count=0,
                subtotal_expenses=0,
                contingency_percent=0,
            ),
            unknowns=[unknown],
            exclusions=exclusions,
            budget_support_items=[
                _support_item(
                    "unknown",
                    unknown,
                    "missing_template",
                    structured_ref=_template_ref(
                        profile, confirmation.confirmed_matter_family, "missing"
                    ),
                ),
                _support_item(
                    "assumption",
                    "Budget generation was attempted only after human confirmation.",
                    "human_confirmation",
                    structured_ref=_confirmation_ref(confirmation),
                ),
                *_workflow_exclusion_support_items(exclusions),
            ],
        )

    rates = {str(k): float(v) for k, v in profile.get("synthetic_hourly_rates", {}).items()}
    driver_values = _numeric_driver_values(case_drivers)
    lines: list[BudgetLine] = []
    evidence_refs = _confirmed_matter_observed_refs(packet, confirmation)

    for phase in template.get("phases", []):
        for task in phase.get("tasks", []):
            role = str(task["staffing_role"])
            base_hours = float(task["estimated_hours"])
            base_expenses = float(task.get("estimated_expenses", 0.0))
            assumptions = list(task.get("assumptions", []))

            scaling_driver = task.get("scaling_driver")
            scaling_formula: str | None = None
            if scaling_driver is not None and scaling_driver in driver_values:
                units, provenance = driver_values[scaling_driver]
                hours_per_unit = float(task.get("hours_per_unit", 0.0))
                expense_per_unit = float(task.get("expense_per_unit", 0.0))
                hours = round(hours_per_unit * units, 2)
                expenses = round(base_expenses + expense_per_unit * units, 2)
                scaling_formula = (
                    f"{hours_per_unit} hours/unit * {units} {scaling_driver} ({provenance})"
                )
                assumptions = assumptions + [
                    f"Hours scaled by driver {scaling_driver}={units} ({provenance}); "
                    f"template hours {base_hours} used only as fallback."
                ]
            else:
                hours = base_hours
                expenses = base_expenses

            rate = rates.get(role)
            fees = round(hours * rate, 2) if rate is not None else None
            hours_min = float(task.get("estimated_hours_min", max(0.0, hours * 0.8)))
            hours_max = float(task.get("estimated_hours_max", hours * 1.25))
            if rate is not None:
                rate_formula = f"{hours} hours * {rate} synthetic hourly rate"
            else:
                rate_formula = "hours only; no authorized rate present"
            calculation_formula = (
                f"{scaling_formula}; {rate_formula}" if scaling_formula else rate_formula
            )
            lines.append(
                BudgetLine(
                    phase_id=str(phase["phase_id"]),
                    phase_name=str(phase["phase_name"]),
                    task_id=str(task["task_id"]),
                    task_name=str(task["task_name"]),
                    staffing_role=role,
                    estimated_hours=hours,
                    estimated_hours_min=round(hours_min, 2),
                    estimated_hours_max=round(hours_max, 2),
                    hourly_rate=rate,
                    rate_source="synthetic_profile" if rate is not None else "absent",
                    rate_is_synthetic=True,
                    estimated_fees=fees,
                    estimated_expenses=expenses,
                    calculation_formula=calculation_formula,
                    external_code_candidate=task.get("external_code_candidate"),
                    expense_code=task.get("expense_code"),
                    assumptions=assumptions,
                    evidence_refs=evidence_refs,
                )
            )

    contingency_percent = float(template.get("contingency_percent", 0.0))
    scenario_set = _build_scenario_set(template, lines, contingency_percent)
    selected_lines = _selected_scenario_lines(template, lines, scenario_set)
    selected_scenario = next(
        scenario
        for scenario in scenario_set.scenarios
        if scenario.scenario_id == scenario_set.selected_scenario_id
    )
    (
        subtotal_fees,
        subtotal_expenses,
        contingency_amount,
        total,
        _total_min,
        _total_max,
    ) = _budget_totals(selected_lines, contingency_percent)
    mode = _pricing_status(selected_lines)
    report = _calculation_report(selected_lines, contingency_percent, mode=mode)

    policy_exclusions = [
        "conflict clearance",
        "engagement authorization",
        "carrier/client submission",
        "court filing",
    ]
    assumptions = list(template.get("assumptions", []))
    exclusions = list(template.get("exclusions", [])) + policy_exclusions
    unknowns = list(template.get("unknowns", []))
    support_items = [
        _support_item(
            "assumption",
            "Budget generation was attempted only after human confirmation.",
            "human_confirmation",
            structured_ref=_confirmation_ref(confirmation),
        ),
        *_template_support_items(profile, confirmation.confirmed_matter_family, template),
        *_workflow_exclusion_support_items(policy_exclusions),
    ]
    if evidence_refs:
        support_items.append(
            _support_item(
                "assumption",
                "Matter-family budget template selection is grounded in observed intake evidence.",
                "observed_evidence",
                evidence_refs=evidence_refs,
            )
        )

    return BudgetProposal(
        budget_proposal_id=new_id("budget"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        practice_profile_id=str(profile["profile_id"]),
        matter_family=confirmation.confirmed_matter_family,
        representation_posture=confirmation.confirmed_representation_posture,
        pricing_status=mode,
        lines=selected_lines,
        subtotal_fees=subtotal_fees,
        subtotal_expenses=subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=contingency_amount,
        total_proposed_budget=total,
        scenario_name=selected_scenario.scenario_id,
        scenario_set=scenario_set,
        calculation_report=report,
        assumptions=assumptions,
        exclusions=exclusions,
        unknowns=unknowns,
        budget_support_items=support_items,
    )
