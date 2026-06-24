from __future__ import annotations

from typing import Any

from .drivers import CaseDriverProfile
from .models import (
    BudgetCalculationReport,
    BudgetLine,
    BudgetProposal,
    BudgetSupportItem,
    EvidenceRef,
    HumanConfirmation,
    IntakePreflightPacket,
)
from .util import new_id


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
    all_priced = True
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
            if rate is None:
                all_priced = False
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
                    assumptions=assumptions,
                    evidence_refs=evidence_refs,
                )
            )

    subtotal_fees = (
        round(sum(line.estimated_fees or 0 for line in lines), 2) if all_priced else None
    )
    subtotal_expenses = round(sum(line.estimated_expenses for line in lines), 2)
    contingency_percent = float(template.get("contingency_percent", 0.0))
    contingency_amount = (
        round((subtotal_fees or 0) * contingency_percent / 100, 2) if all_priced else None
    )
    total = (
        round((subtotal_fees or 0) + subtotal_expenses + (contingency_amount or 0), 2)
        if all_priced
        else None
    )
    mode = "priced" if all_priced else "hours_only"
    report = BudgetCalculationReport(
        calculation_report_id=new_id("calcreport"),
        mode=mode,
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
        lines=lines,
        subtotal_fees=subtotal_fees,
        subtotal_expenses=subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=contingency_amount,
        total_proposed_budget=total,
        scenario_name=str(template.get("scenario_name", "baseline")),
        calculation_report=report,
        assumptions=assumptions,
        exclusions=exclusions,
        unknowns=unknowns,
        budget_support_items=support_items,
    )
