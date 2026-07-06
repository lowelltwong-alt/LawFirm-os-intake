from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .drivers import CaseDriverProfile
from .models import (
    BudgetCalculationReport,
    BudgetDriverEffect,
    BudgetDriverProfileSummary,
    BudgetGuidelineFlag,
    BudgetLine,
    BudgetProposal,
    BudgetScenario,
    BudgetScenarioSet,
    BudgetSupportItem,
    EvidenceRef,
    HumanConfirmation,
    IntakePreflightPacket,
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentExecutableDriverImpactReport,
)
from .rates import RoleRateResolution
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


@dataclass(frozen=True)
class BudgetTotals:
    subtotal_fees: float | None
    subtotal_fees_min: float | None
    subtotal_fees_max: float | None
    subtotal_expenses: float
    subtotal_expenses_min: float | None
    subtotal_expenses_max: float | None
    contingency_amount: float | None
    contingency_amount_min: float | None
    contingency_amount_max: float | None
    total: float | None
    total_min: float | None
    total_max: float | None
    total_hours: float
    total_hours_min: float | None
    total_hours_max: float | None


def _budget_template(profile: dict[str, Any], matter_family: str) -> dict[str, Any] | None:
    templates = profile.get("budget_templates", {})
    return templates.get(matter_family)


def _confirmation_ref(confirmation: HumanConfirmation) -> str:
    return f"human-confirmation://{confirmation.confirmation_id}"


def _template_ref(profile: dict[str, Any], matter_family: str, path: str) -> str:
    return f"practice-profile://{profile['profile_id']}/budget_templates/{matter_family}/{path}"


def _policy_ref(path: str) -> str:
    return f"workflow-policy://budget-boundary/{path}"


def _driver_policy_ref(case_drivers: CaseDriverProfile | None, path: str) -> str:
    policy_id = case_drivers.policy_id if case_drivers is not None else "unknown"
    return f"budget-driver-policy://{policy_id}/{path}"


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


def apply_labor_employment_budget_fact_constraints(
    budget: BudgetProposal,
    report: LaborEmploymentBudgetFactAuditReport | None,
    report_ref: str | None,
) -> BudgetProposal:
    if report is None:
        return budget
    if (
        report.budget_readiness_state == "blocked_missing_critical_facts"
        or report.critical_gap_count > 0
    ):
        return budget

    unknowns = list(budget.unknowns)
    support_items = list(budget.budget_support_items)
    seen_unknowns = set(unknowns)
    seen_structured_refs = {
        item.structured_ref for item in support_items if item.structured_ref is not None
    }
    base_ref = (
        "labor-employment-budget-fact-report://"
        f"{report.labor_employment_budget_fact_audit_report_id}"
    )

    def add_unknown(text: str, structured_ref: str) -> None:
        if text not in seen_unknowns:
            unknowns.append(text)
            seen_unknowns.add(text)
        if structured_ref not in seen_structured_refs:
            support_items.append(
                _support_item(
                    "unknown",
                    text,
                    "labor_employment_budget_fact_report",
                    structured_ref=structured_ref,
                )
            )
            seen_structured_refs.add(structured_ref)

    if report.budget_readiness_state == "range_only_pending_human_review":
        add_unknown(
            "L&E budget fact report requires broad/range or hours-only treatment until human fact review is complete.",
            f"{base_ref}/budget_readiness_state/range_only_pending_human_review",
        )

    for gap in report.gaps:
        add_unknown(
            f"L&E budget fact needs review: {gap.recommended_question}",
            f"{base_ref}/gap/{gap.gap_id}",
        )

    for index, question in enumerate(report.required_human_questions):
        add_unknown(
            f"L&E budget fact human question: {question}",
            f"{base_ref}/required_human_questions/{index}",
        )

    return budget.model_copy(update={"unknowns": unknowns, "budget_support_items": support_items})


def apply_labor_employment_driver_impact_constraints(
    budget: BudgetProposal,
    report: LaborEmploymentExecutableDriverImpactReport | None,
    report_ref: str | None,
) -> BudgetProposal:
    if report is None:
        return budget
    if report.block_amount_budget_impact_count > 0:
        return budget

    unknowns = list(budget.unknowns)
    support_items = list(budget.budget_support_items)
    display_banner = dict(budget.display_banner)
    seen_unknowns = set(unknowns)
    seen_structured_refs = {
        item.structured_ref for item in support_items if item.structured_ref is not None
    }
    base_ref = (
        f"labor-employment-driver-impact-report://{report.executable_driver_impact_report_id}"
    )
    ref_root = report_ref or base_ref

    def add_unknown(text: str, structured_ref: str) -> None:
        if text not in seen_unknowns:
            unknowns.append(text)
            seen_unknowns.add(text)
        if structured_ref not in seen_structured_refs:
            support_items.append(
                _support_item(
                    "unknown",
                    text,
                    "labor_employment_driver_impact_report",
                    structured_ref=structured_ref,
                )
            )
            seen_structured_refs.add(structured_ref)

    if report.range_widening_impact_count:
        add_unknown(
            "L&E driver impact report requires budget range review before relying on point estimates.",
            f"{base_ref}/range_widening_impact_count",
        )
    if report.scenario_fork_impact_count:
        add_unknown(
            "L&E driver impact report requires scenario-fork review before choosing a budget path.",
            f"{base_ref}/scenario_fork_impact_count",
        )
    if report.rate_guideline_review_impact_count:
        add_unknown(
            "L&E driver impact report requires carrier/rate guideline review before compliant projection or submission.",
            f"{base_ref}/rate_guideline_review_impact_count",
        )

    for case in report.cases:
        for item in case.impact_items:
            if item.impact_state != "source_bound_impact_candidate":
                continue
            if not (
                item.range_widening_factor > 1.0
                or item.scenario_fork_required
                or item.rate_guideline_review_required
            ):
                continue
            actions = ", ".join(item.impact_actions)
            add_unknown(
                "L&E budget driver impact needs review: "
                f"{item.driver_dimension} ({actions}); "
                f"range factor {item.range_widening_factor}.",
                f"{base_ref}/case/{case.executable_fixture_id}/driver/{item.driver_dimension}",
            )

    display_banner["labor_employment_driver_impact_status"] = report.status
    display_banner["labor_employment_driver_impact_report_ref"] = ref_root
    display_banner["labor_employment_driver_max_range_widening_factor"] = (
        report.max_range_widening_factor
    )
    display_banner["labor_employment_driver_scenario_fork_review_required"] = (
        report.scenario_fork_impact_count > 0
    )
    display_banner["labor_employment_driver_rate_guideline_review_required"] = (
        report.rate_guideline_review_impact_count > 0
    )
    return budget.model_copy(
        update={
            "unknowns": unknowns,
            "budget_support_items": support_items,
            "display_banner": display_banner,
        }
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


def _drivers_by_id(case_drivers: CaseDriverProfile | None) -> dict[str, Any]:
    if case_drivers is None:
        return {}
    return {driver.driver_id: driver for driver in case_drivers.drivers}


def _driver_range(
    case_drivers: CaseDriverProfile | None,
    driver_id: str,
) -> tuple[float, float, float] | None:
    if case_drivers is None:
        return None
    ranges = case_drivers.count_driver_range_policy or {}
    raw = ranges.get(driver_id) if isinstance(ranges, dict) else None
    if not isinstance(raw, dict):
        return None
    try:
        minimum = float(raw["min"])
        likely = float(raw.get("likely", minimum))
        maximum = float(raw["max"])
    except (KeyError, TypeError, ValueError):
        return None
    if minimum > maximum:
        return None
    likely = min(max(likely, minimum), maximum)
    return minimum, likely, maximum


def _range_from_scaled_driver(
    *,
    base_value: float,
    per_unit: float,
    likely_value: float,
    driver_range: tuple[float, float, float] | None,
    provenance: str | None,
    allow_wide_range: bool,
) -> tuple[float, float]:
    if (
        allow_wide_range
        and driver_range is not None
        and provenance in {"unknown", "profile_default"}
    ):
        minimum, _likely, maximum = driver_range
        low = round(base_value + per_unit * minimum, 2)
        high = round(base_value + per_unit * maximum, 2)
        likely = round(base_value + per_unit * likely_value, 2)
        return min(low, likely), max(high, likely)
    likely = round(base_value + per_unit * likely_value, 2)
    return likely, likely


def _resolution_path_driver(case_drivers: CaseDriverProfile | None) -> Any | None:
    if case_drivers is None:
        return None
    driver = _drivers_by_id(case_drivers).get("resolution_path")
    if driver is None or driver.provenance not in {"observed_support", "human_confirmed"}:
        return None
    if driver.value is None:
        return None
    return driver


def _driver_profile_summary(
    case_drivers: CaseDriverProfile | None,
) -> BudgetDriverProfileSummary | None:
    if case_drivers is None:
        return None
    return BudgetDriverProfileSummary(
        case_driver_profile_id=case_drivers.case_driver_profile_id,
        policy_id=case_drivers.policy_id,
        policy_version=case_drivers.policy_version,
        driver_count=len(case_drivers.drivers),
        observed_or_confirmed_driver_ids=case_drivers.observed_or_confirmed_driver_ids,
        default_driver_ids=case_drivers.default_driver_ids,
        unknown_driver_ids=case_drivers.unknown_driver_ids,
    )


def _driver_effect_key(
    effect: BudgetDriverEffect,
) -> tuple[str, str | None, str, tuple[str, ...], tuple[str, ...]]:
    return (
        effect.driver_id,
        None if effect.driver_value is None else str(effect.driver_value),
        effect.effect_type,
        tuple(effect.phase_ids),
        tuple(effect.task_ids),
    )


def _intensity_adjustment(
    phase_id: str,
    task_id: str,
    case_drivers: CaseDriverProfile | None,
) -> tuple[float, list[str], list[BudgetDriverEffect]]:
    if case_drivers is None:
        return 1.0, [], []
    policy = case_drivers.intensity_multiplier_policy or {}
    effects_by_driver = policy.get("effects", {})
    if not isinstance(effects_by_driver, dict):
        return 1.0, [], []

    drivers = _drivers_by_id(case_drivers)
    multiplier = 1.0
    notes: list[str] = []
    effects: list[BudgetDriverEffect] = []
    for driver_id, value_effects in effects_by_driver.items():
        driver = drivers.get(str(driver_id))
        if driver is None or driver.value is None:
            continue
        if not isinstance(value_effects, dict):
            continue
        effect = value_effects.get(str(driver.value))
        if not isinstance(effect, dict):
            continue
        phase_ids = [str(item) for item in effect.get("phase_ids", [])]
        if phase_ids and phase_id not in phase_ids:
            continue
        raw_multiplier = float(effect.get("raw_multiplier", effect.get("multiplier", 1.0)))
        driver_multiplier = _effective_intensity_multiplier(effect, phase_id)
        multiplier *= driver_multiplier
        note = (
            f"Driver {driver.driver_id}={driver.value} ({driver.provenance}) "
            f"applies {driver_multiplier}x effective intensity to {phase_id} "
            f"(raw {raw_multiplier}x; normalization "
            f"{case_drivers.intensity_normalization_mode}); "
            f"{effect.get('note', 'synthetic candidate policy effect')}"
        )
        if driver.provenance == "profile_default":
            note += " This is a synthetic profile default, not observed source evidence."
        notes.append(note)
        effects.append(
            BudgetDriverEffect(
                driver_id=driver.driver_id,
                driver_value=driver.value,
                provenance=driver.provenance,
                effect_type="intensity_multiplier",
                applied=True,
                phase_ids=phase_ids or [phase_id],
                task_ids=[task_id],
                multiplier=driver_multiplier,
                source_refs=driver.source_refs,
                structured_ref=_driver_policy_ref(
                    case_drivers,
                    f"intensity_multiplier_policy/effects/{driver.driver_id}/{driver.value}",
                ),
                note=note,
            )
        )

    cap = float(policy.get("cumulative_multiplier_cap", 2.5))
    if multiplier > cap:
        note = (
            f"Cumulative driver multiplier {round(multiplier, 4)}x for {phase_id}/{task_id} "
            f"was capped at {cap}x by synthetic policy; cap is a guardrail, not observed fact."
        )
        notes.append(note)
        effects.append(
            BudgetDriverEffect(
                driver_id="cumulative_multiplier_cap",
                driver_value=cap,
                provenance="profile_default",
                effect_type="intensity_multiplier",
                applied=True,
                phase_ids=[phase_id],
                task_ids=[task_id],
                multiplier=cap,
                capped=True,
                structured_ref=_driver_policy_ref(
                    case_drivers,
                    "intensity_multiplier_policy/cumulative_multiplier_cap",
                ),
                note=note,
            )
        )
        multiplier = cap
    return round(multiplier, 4), notes, effects


def _effective_intensity_multiplier(effect: dict[str, Any], phase_id: str) -> float:
    by_phase = effect.get("effective_multipliers_by_phase", {})
    if isinstance(by_phase, dict) and phase_id in by_phase:
        return float(by_phase[phase_id])
    if "effective_multiplier" in effect:
        return float(effect["effective_multiplier"])
    return float(effect.get("multiplier", 1.0))


def _driver_boundary_effects(
    case_drivers: CaseDriverProfile | None,
) -> list[BudgetDriverEffect]:
    if case_drivers is None:
        return []
    drivers = _drivers_by_id(case_drivers)
    effects: list[BudgetDriverEffect] = []
    for driver_id in ("resolution_path", "coverage_posture"):
        driver = drivers.get(driver_id)
        if driver is None:
            continue
        if driver.provenance == "unknown":
            if driver_id == "coverage_posture":
                note = (
                    "Budget driver coverage_posture is unknown; no coverage-specific line, "
                    "coverage conclusion, or defense-fee adjustment was applied."
                )
            else:
                note = (
                    "Budget driver resolution_path is unknown; scenario set remains a "
                    "review comparison rather than an observed or selected path."
                )
            effects.append(
                BudgetDriverEffect(
                    driver_id=driver.driver_id,
                    driver_value=None,
                    provenance=driver.provenance,
                    effect_type="unknown_driver",
                    applied=False,
                    structured_ref=_driver_policy_ref(case_drivers, f"drivers/{driver.driver_id}"),
                    note=note,
                )
            )
            continue
        if driver_id == "coverage_posture":
            review_values = set(
                str(item)
                for item in case_drivers.coverage_posture_policy.get(
                    "review_required_values",
                    [],
                )
            )
            value = str(driver.value)
            if value in review_values:
                note = (
                    f"Coverage posture {value} ({driver.provenance}) requires human review; "
                    "coverage work is not blended into the defense-fee budget."
                )
                effects.append(
                    BudgetDriverEffect(
                        driver_id=driver.driver_id,
                        driver_value=driver.value,
                        provenance=driver.provenance,
                        effect_type="coverage_boundary",
                        applied=False,
                        source_refs=driver.source_refs,
                        structured_ref=_driver_policy_ref(
                            case_drivers,
                            f"coverage_posture_policy/review_required_values/{value}",
                        ),
                        note=note,
                    )
                )
    return effects


def _guideline_flags(
    lines: list[BudgetLine],
    total_proposed_budget: float | None,
    case_drivers: CaseDriverProfile | None,
) -> list[BudgetGuidelineFlag]:
    if case_drivers is None:
        return []
    policy = case_drivers.synthetic_guideline_constraints or {}
    if not policy:
        return [
            BudgetGuidelineFlag(
                constraint_id="unknown_guidelines",
                constraint_type="unknown_guidelines",
                status="unknown",
                provenance="unknown",
                structured_ref=_driver_policy_ref(case_drivers, "synthetic_guideline_constraints"),
                note=(
                    "No synthetic guideline constraints were available; real carrier "
                    "guidelines remain outside this repo."
                ),
            )
        ]

    flags: list[BudgetGuidelineFlag] = []
    role_caps = policy.get("role_rate_caps", {})
    if isinstance(role_caps, dict):
        for role, cap in sorted(role_caps.items()):
            role_lines = [line for line in lines if line.staffing_role == str(role)]
            if not role_lines:
                continue
            max_rate = max((line.hourly_rate or 0.0) for line in role_lines)
            cap_value = float(cap)
            flagged = max_rate > cap_value
            flags.append(
                BudgetGuidelineFlag(
                    constraint_id=f"role_rate_cap:{role}",
                    constraint_type="role_rate_cap",
                    status="flagged_for_human_review" if flagged else "not_triggered",
                    role=str(role),
                    current_value=max_rate,
                    threshold_value=cap_value,
                    structured_ref=_driver_policy_ref(
                        case_drivers,
                        f"synthetic_guideline_constraints/role_rate_caps/{role}",
                    ),
                    note=(
                        f"Synthetic role rate cap for {role} "
                        f"{'is exceeded' if flagged else 'is not exceeded'}; "
                        "budget rates are not rewritten."
                    ),
                )
            )

    phase_caps = policy.get("phase_budget_caps", {})
    if isinstance(phase_caps, dict):
        for phase_id, cap in sorted(phase_caps.items()):
            phase_lines = [line for line in lines if line.phase_id == str(phase_id)]
            if not phase_lines:
                continue
            phase_total = round(
                sum((line.estimated_fees or 0.0) + line.estimated_expenses for line in phase_lines),
                2,
            )
            cap_value = float(cap)
            flagged = phase_total > cap_value
            flags.append(
                BudgetGuidelineFlag(
                    constraint_id=f"phase_budget_cap:{phase_id}",
                    constraint_type="phase_budget_cap",
                    status="flagged_for_human_review" if flagged else "not_triggered",
                    phase_id=str(phase_id),
                    current_value=phase_total,
                    threshold_value=cap_value,
                    structured_ref=_driver_policy_ref(
                        case_drivers,
                        f"synthetic_guideline_constraints/phase_budget_caps/{phase_id}",
                    ),
                    note=(
                        f"Synthetic phase cap for {phase_id} "
                        f"{'is exceeded' if flagged else 'is not exceeded'}; "
                        "budget lines are not rewritten."
                    ),
                )
            )

    if "total_budget_cap" in policy and total_proposed_budget is not None:
        cap_value = float(policy["total_budget_cap"])
        flagged = total_proposed_budget > cap_value
        flags.append(
            BudgetGuidelineFlag(
                constraint_id="total_budget_cap",
                constraint_type="total_budget_cap",
                status="flagged_for_human_review" if flagged else "not_triggered",
                current_value=total_proposed_budget,
                threshold_value=cap_value,
                structured_ref=_driver_policy_ref(
                    case_drivers,
                    "synthetic_guideline_constraints/total_budget_cap",
                ),
                note=(
                    "Synthetic total budget cap "
                    f"{'is exceeded' if flagged else 'is not exceeded'}; "
                    "proposal remains review-only and is not rewritten."
                ),
            )
        )
    return flags


def _budget_driver_support_items(
    driver_effects: list[BudgetDriverEffect],
    guideline_flags: list[BudgetGuidelineFlag],
) -> list[BudgetSupportItem]:
    items: list[BudgetSupportItem] = []
    for effect in driver_effects:
        item_type = "unknown" if effect.effect_type == "unknown_driver" else "assumption"
        items.append(
            _support_item(
                item_type,
                effect.note,
                "budget_driver_policy",
                structured_ref=effect.structured_ref,
            )
        )
    for flag in guideline_flags:
        if flag.status == "flagged_for_human_review":
            items.append(
                _support_item(
                    "unknown",
                    flag.note,
                    "budget_driver_policy",
                    structured_ref=flag.structured_ref,
                )
            )
    return items


def _phase_order(template: dict[str, Any]) -> list[str]:
    return [str(phase["phase_id"]) for phase in template.get("phases", [])]


def _scenario_definitions(
    template: dict[str, Any],
    case_drivers: CaseDriverProfile | None = None,
) -> list[dict[str, Any]]:
    raw = template.get("scenarios") or (
        case_drivers.scenario_policy if case_drivers is not None else None
    )
    if not raw:
        raw = _default_scenarios_for_phase_order(_phase_order(template))
    definitions: list[dict[str, Any]] = []
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
                "probability": (
                    float(scenario["probability"]) if "probability" in scenario else None
                ),
            }
        )
    return definitions


def _default_scenarios_for_phase_order(phase_order: list[str]) -> list[dict[str, Any]]:
    if not phase_order:
        return DEFAULT_SCENARIOS
    if {"L200", "L300", "L400"}.issubset(set(phase_order)):
        return DEFAULT_SCENARIOS
    last_index = len(phase_order) - 1
    early_phase = phase_order[min(1, last_index)]
    standard_phase = phase_order[min(2, last_index)]
    through_trial_phase = phase_order[last_index]
    defaults: list[dict[str, Any]] = []
    for scenario, resolution_phase in zip(
        DEFAULT_SCENARIOS,
        [early_phase, standard_phase, through_trial_phase],
        strict=True,
    ):
        remapped = dict(scenario)
        remapped["resolution_phase"] = resolution_phase
        defaults.append(remapped)
    return defaults


def _included_phase_ids(phase_order: list[str], resolution_phase: str) -> list[str]:
    if not phase_order:
        return []
    if resolution_phase not in phase_order:
        raise ValueError(
            "scenario_policy_invalid: resolution_phase "
            f"{resolution_phase!r} is not in budget template phase order"
        )
    return phase_order[: phase_order.index(resolution_phase) + 1]


def _lines_for_phases(lines: list[BudgetLine], included_phase_ids: list[str]) -> list[BudgetLine]:
    if not included_phase_ids:
        return []
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
) -> BudgetTotals:
    all_priced = all(line.hourly_rate is not None for line in lines)
    total_hours = round(sum(line.estimated_hours for line in lines), 2)
    total_hours_min = round(
        sum(
            line.estimated_hours_min
            if line.estimated_hours_min is not None
            else line.estimated_hours
            for line in lines
        ),
        2,
    )
    total_hours_max = round(
        sum(
            line.estimated_hours_max
            if line.estimated_hours_max is not None
            else line.estimated_hours
            for line in lines
        ),
        2,
    )
    subtotal_fees = (
        round(sum(line.estimated_fees or 0 for line in lines), 2) if all_priced else None
    )
    subtotal_expenses = round(sum(line.estimated_expenses for line in lines), 2)
    subtotal_expenses_min = round(
        sum(
            line.estimated_expenses_min
            if line.estimated_expenses_min is not None
            else line.estimated_expenses
            for line in lines
        ),
        2,
    )
    subtotal_expenses_max = round(
        sum(
            line.estimated_expenses_max
            if line.estimated_expenses_max is not None
            else line.estimated_expenses
            for line in lines
        ),
        2,
    )
    contingency_amount = (
        round((subtotal_fees or 0) * contingency_percent / 100, 2) if all_priced else None
    )
    total = (
        round((subtotal_fees or 0) + subtotal_expenses + (contingency_amount or 0), 2)
        if all_priced
        else None
    )
    subtotal_fees_min = None
    subtotal_fees_max = None
    contingency_amount_min = None
    contingency_amount_max = None
    total_min = None
    total_max = None
    if all_priced:
        subtotal_fees_min = round(
            sum(
                (
                    line.estimated_hours_min
                    if line.estimated_hours_min is not None
                    else line.estimated_hours
                )
                * (line.hourly_rate or 0)
                for line in lines
            ),
            2,
        )
        subtotal_fees_max = round(
            sum(
                (
                    line.estimated_hours_max
                    if line.estimated_hours_max is not None
                    else line.estimated_hours
                )
                * (line.hourly_rate or 0)
                for line in lines
            ),
            2,
        )
        contingency_amount_min = round(subtotal_fees_min * contingency_percent / 100, 2)
        contingency_amount_max = round(subtotal_fees_max * contingency_percent / 100, 2)
        total_min = round(
            subtotal_fees_min + subtotal_expenses_min + contingency_amount_min,
            2,
        )
        total_max = round(
            subtotal_fees_max + subtotal_expenses_max + contingency_amount_max,
            2,
        )
    return BudgetTotals(
        subtotal_fees=subtotal_fees,
        subtotal_fees_min=subtotal_fees_min,
        subtotal_fees_max=subtotal_fees_max,
        subtotal_expenses=subtotal_expenses,
        subtotal_expenses_min=subtotal_expenses_min,
        subtotal_expenses_max=subtotal_expenses_max,
        contingency_amount=contingency_amount,
        contingency_amount_min=contingency_amount_min,
        contingency_amount_max=contingency_amount_max,
        total=total,
        total_min=total_min,
        total_max=total_max,
        total_hours=total_hours,
        total_hours_min=total_hours_min,
        total_hours_max=total_hours_max,
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
    totals = _budget_totals(lines, contingency_percent)
    return BudgetCalculationReport(
        calculation_report_id=new_id("calcreport"),
        mode=mode,  # type: ignore[arg-type]
        line_count=len(lines),
        total_hours=round(sum(line.estimated_hours for line in lines), 2),
        priced_line_count=sum(1 for line in lines if line.hourly_rate is not None),
        unpriced_line_count=sum(1 for line in lines if line.hourly_rate is None),
        subtotal_fees=totals.subtotal_fees,
        subtotal_expenses=totals.subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=totals.contingency_amount,
        total_proposed_budget=totals.total,
        rate_sources=sorted({line.rate_source for line in lines}),
    )


def _scenario_phase_rank(phase_order: list[str], scenario: BudgetScenario) -> int:
    try:
        return phase_order.index(scenario.resolution_phase)
    except ValueError as exc:
        raise ValueError(
            "scenario_policy_invalid: resolution_phase "
            f"{scenario.resolution_phase!r} is not in budget template phase order"
        ) from exc


def _scenario_policy_issue_notes(
    scenario_set: BudgetScenarioSet,
) -> list[BudgetSupportItem]:
    items: list[BudgetSupportItem] = []
    for code, note in zip(
        scenario_set.policy_issue_codes,
        scenario_set.policy_issue_notes,
        strict=False,
    ):
        items.append(
            _support_item(
                "unknown",
                note,
                "budget_driver_policy",
                structured_ref=_policy_ref(f"scenario_policy/{code}"),
            )
        )
    return items


def _rate_review_support_items(
    rate_resolution: RoleRateResolution | None,
    rate_issue_codes: set[str],
    rate_issue_notes: list[str],
) -> list[BudgetSupportItem]:
    items: list[BudgetSupportItem] = []
    if rate_resolution is not None and rate_resolution.review_required:
        for code, note in zip(
            rate_resolution.review_issue_codes,
            rate_resolution.review_notes,
            strict=False,
        ):
            items.append(
                _support_item(
                    "unknown",
                    note,
                    "carrier_rate_card",
                    structured_ref=(
                        f"carrier-rate-card://{rate_resolution.rate_card_id}"
                        f"/{rate_resolution.carrier_id}/{rate_resolution.state}/review/{code}"
                    ),
                )
            )
    for note in rate_issue_notes:
        structured_code = next(iter(sorted(rate_issue_codes)), "rate_review_required")
        card_id = rate_resolution.rate_card_id if rate_resolution is not None else "unknown"
        carrier_id = rate_resolution.carrier_id if rate_resolution is not None else "unknown"
        state = rate_resolution.state if rate_resolution is not None else "unknown"
        items.append(
            _support_item(
                "unknown",
                note,
                "carrier_rate_card",
                structured_ref=(
                    f"carrier-rate-card://{card_id}/{carrier_id}/{state}/review/{structured_code}"
                ),
            )
        )
    return items


def _build_scenario_set(
    template: dict[str, Any],
    lines: list[BudgetLine],
    contingency_percent: float,
    case_drivers: CaseDriverProfile | None = None,
) -> BudgetScenarioSet:
    phase_order = _phase_order(template)
    scenarios: list[BudgetScenario] = []
    for definition in _scenario_definitions(template, case_drivers):
        included_phase_ids = _included_phase_ids(phase_order, definition["resolution_phase"])
        scenario_lines = _lines_for_phases(lines, included_phase_ids)
        totals = _budget_totals(scenario_lines, contingency_percent)
        scenarios.append(
            BudgetScenario(
                scenario_id=definition["scenario_id"],
                scenario_name=definition["scenario_name"],
                description=definition["description"],
                resolution_phase=definition["resolution_phase"],
                included_phase_ids=included_phase_ids,
                included_external_codes=_line_external_codes(scenario_lines),
                included_line_count=len(scenario_lines),
                total_hours=totals.total_hours,
                total_hours_min=totals.total_hours_min,
                total_hours_max=totals.total_hours_max,
                subtotal_fees=totals.subtotal_fees,
                subtotal_fees_min=totals.subtotal_fees_min,
                subtotal_fees_max=totals.subtotal_fees_max,
                subtotal_expenses=totals.subtotal_expenses,
                subtotal_expenses_min=totals.subtotal_expenses_min,
                subtotal_expenses_max=totals.subtotal_expenses_max,
                contingency_percent=contingency_percent,
                contingency_amount=totals.contingency_amount,
                contingency_amount_min=totals.contingency_amount_min,
                contingency_amount_max=totals.contingency_amount_max,
                total_proposed_budget=totals.total,
                total_budget_min=totals.total_min,
                total_budget_max=totals.total_max,
                probability=definition.get("probability"),
                pricing_status=_pricing_status(scenario_lines),  # type: ignore[arg-type]
            )
        )

    phase_ordered_scenarios = sorted(
        scenarios,
        key=lambda scenario: _scenario_phase_rank(phase_order, scenario),
    )
    priced_totals = [scenario.total_proposed_budget for scenario in phase_ordered_scenarios]
    if all(total is not None for total in priced_totals):
        monotonic = all(
            float(priced_totals[index]) <= float(priced_totals[index + 1])
            for index in range(len(priced_totals) - 1)
        )
        basis = "total_proposed_budget"
    else:
        hours = [scenario.total_hours for scenario in phase_ordered_scenarios]
        monotonic = all(hours[index] <= hours[index + 1] for index in range(len(hours) - 1))
        basis = "total_hours"
    if not monotonic:
        raise ValueError(
            "scenario_policy_invalid: scenario totals are not monotonic by budget phase order"
        )
    scenario_ids = {scenario.scenario_id for scenario in scenarios}
    standard = "standard" if "standard" in scenario_ids else scenarios[-1].scenario_id
    selected = standard
    selected_basis = "default_standard"
    resolution_driver = _resolution_path_driver(case_drivers)
    if resolution_driver is not None and str(resolution_driver.value) in scenario_ids:
        selected = str(resolution_driver.value)
        selected_basis = "confirmed_resolution_path"
    elif "standard" not in scenario_ids:
        selected_basis = "fallback_last_scenario"

    probability_values = [scenario.probability for scenario in scenarios]
    probability_sum = None
    expected_total = None
    unknown_probability_mass = None
    expected_total_min = None
    expected_total_max = None
    expected_value_method = "not_computed"
    probability_integrity_status = "not_configured"
    policy_issue_codes: list[str] = []
    policy_issue_notes: list[str] = []
    if any(value is not None for value in probability_values) and not all(
        value is not None for value in probability_values
    ):
        probability_sum = round(
            sum(float(value) for value in probability_values if value is not None),
            6,
        )
        probability_integrity_status = "partial_probability_weights"
        policy_issue_codes.append("scenario_probability_partial")
        policy_issue_notes.append(
            "Budget scenario probabilities are partially configured; expected value was "
            "not computed and the scenario policy needs human review."
        )
    elif all(value is not None for value in probability_values):
        probability_sum = round(sum(float(value) for value in probability_values), 6)
        all_scenarios_priced = all(
            scenario.total_proposed_budget is not None for scenario in scenarios
        )
        if not all_scenarios_priced:
            probability_integrity_status = "hours_only_not_computed"
        elif abs(probability_sum - 1.0) <= 0.000001:
            expected_total = round(
                sum(
                    float(scenario.probability or 0) * float(scenario.total_proposed_budget or 0)
                    for scenario in scenarios
                ),
                2,
            )
            expected_total_min = expected_total
            expected_total_max = expected_total
            expected_value_method = "reviewed_probabilities"
            probability_integrity_status = "reviewed_probabilities"
        elif 0 <= probability_sum < 1:
            unknown_probability_mass = round(1 - probability_sum, 6)
            known_min = sum(
                float(scenario.probability or 0)
                * float(scenario.total_budget_min if scenario.total_budget_min is not None else 0)
                for scenario in scenarios
            )
            known_max = sum(
                float(scenario.probability or 0)
                * float(scenario.total_budget_max if scenario.total_budget_max is not None else 0)
                for scenario in scenarios
            )
            unweighted_totals = [
                float(
                    scenario.total_budget_min
                    if scenario.total_budget_min is not None
                    else (
                        scenario.total_proposed_budget
                        if scenario.total_proposed_budget is not None
                        else 0
                    )
                )
                for scenario in scenarios
            ]
            unweighted_max_totals = [
                float(
                    scenario.total_budget_max
                    if scenario.total_budget_max is not None
                    else (
                        scenario.total_proposed_budget
                        if scenario.total_proposed_budget is not None
                        else 0
                    )
                )
                for scenario in scenarios
            ]
            if unweighted_totals and unweighted_max_totals:
                expected_total_min = round(
                    known_min + unknown_probability_mass * min(unweighted_totals),
                    2,
                )
                expected_total_max = round(
                    known_max + unknown_probability_mass * max(unweighted_max_totals),
                    2,
                )
                expected_value_method = "bounded_unknown_mass"
            probability_integrity_status = "bounded_unknown_mass"
            policy_issue_codes.append("scenario_probability_sum_not_one")
            policy_issue_notes.append(
                "Budget scenario probabilities sum to "
                f"{probability_sum}; expected value is a bounded review range, "
                "not a reviewed weighted mean."
            )
        else:
            probability_integrity_status = "probability_sum_mismatch"
            policy_issue_codes.append("scenario_probability_sum_not_one")
            policy_issue_notes.append(
                "Budget scenario probabilities sum to "
                f"{probability_sum}; expected value was not computed because "
                "scenario weights must sum to 1.0 before review use."
            )
    status = "flagged_for_human_review" if policy_issue_codes else "ready_for_human_review"
    return BudgetScenarioSet(
        scenario_set_id=new_id("budgetscenarios"),
        status=status,  # type: ignore[arg-type]
        selected_scenario_id=selected,
        standard_scenario_id=standard,
        selected_scenario_basis=selected_basis,  # type: ignore[arg-type]
        expected_total=expected_total,
        unknown_probability_mass=unknown_probability_mass,
        expected_total_min=expected_total_min,
        expected_total_max=expected_total_max,
        expected_value_method=expected_value_method,  # type: ignore[arg-type]
        expected_total_probability_sum=probability_sum,
        probability_integrity_status=probability_integrity_status,  # type: ignore[arg-type]
        policy_issue_codes=policy_issue_codes,
        policy_issue_notes=policy_issue_notes,
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


def _task_rate(
    *,
    task: dict[str, Any],
    role: str,
    rates: dict[str, float],
    rate_resolution: RoleRateResolution | None,
) -> tuple[float | None, str, str | None, str | None, str | None]:
    timekeeper_id = task.get("timekeeper_id")
    if timekeeper_id is not None and rate_resolution is not None:
        override = rate_resolution.named_timekeeper_overrides.get(str(timekeeper_id))
        if override is not None and override.title == role:
            note = (
                f"Named synthetic timekeeper {override.timekeeper_id} ({override.title}) "
                f"resolved at {override.approved_rate} by {override.precedence_tier}; "
                "candidate-only and not authorized for real billing."
            )
            return (
                override.approved_rate,
                "synthetic_named_timekeeper_override",
                override.timekeeper_id,
                note,
                None,
            )
        if override is not None:
            note = (
                f"Named synthetic timekeeper {override.timekeeper_id} is approved as "
                f"{override.title}, but task {task.get('task_id')} is staffed as {role}; "
                "budget line remains hours-only pending human rate review."
            )
            return (
                None,
                "absent",
                override.timekeeper_id,
                note,
                "named_timekeeper_title_mismatch_for_rates",
            )
    rate = rates.get(role)
    if rate is None:
        return (
            None,
            "absent",
            str(timekeeper_id) if timekeeper_id is not None else None,
            None,
            None,
        )
    return (
        rate,
        "synthetic_profile",
        str(timekeeper_id) if timekeeper_id is not None else None,
        None,
        None,
    )


def build_budget_proposal(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    profile: dict[str, Any],
    case_drivers: CaseDriverProfile | None = None,
    rate_resolution: RoleRateResolution | None = None,
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
            driver_profile_summary=_driver_profile_summary(case_drivers),
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

    if rate_resolution is not None and not rate_resolution.review_required:
        rates = dict(rate_resolution.role_rates)
    else:
        rates = (
            {}
            if rate_resolution is not None and rate_resolution.review_required
            else {str(k): float(v) for k, v in profile.get("synthetic_hourly_rates", {}).items()}
        )
    driver_values = _numeric_driver_values(case_drivers)
    driver_lookup = _drivers_by_id(case_drivers)
    driver_effects_by_key: dict[
        tuple[str, str | None, str, tuple[str, ...], tuple[str, ...]], BudgetDriverEffect
    ] = {}
    lines: list[BudgetLine] = []
    rate_issue_notes: list[str] = []
    rate_issue_codes: set[str] = set()
    evidence_refs = _confirmed_matter_observed_refs(packet, confirmation)

    for phase in template.get("phases", []):
        phase_id = str(phase["phase_id"])
        phase_name = str(phase["phase_name"])
        for task in phase.get("tasks", []):
            task_id = str(task["task_id"])
            role = str(task["staffing_role"])
            base_hours = float(task["estimated_hours"])
            base_expenses = float(task.get("estimated_expenses", 0.0))
            assumptions = list(task.get("assumptions", []))

            scaling_driver = task.get("scaling_driver")
            scaling_formula: str | None = None
            hours_min: float | None = None
            hours_max: float | None = None
            expenses_min: float | None = None
            expenses_max: float | None = None
            estimate_basis = "template_default"
            estimate_basis_refs = [
                _template_ref(
                    profile,
                    confirmation.confirmed_matter_family,
                    f"phases/{phase_id}/tasks/{task_id}",
                )
            ]
            if scaling_driver is not None and scaling_driver in driver_values:
                units, provenance = driver_values[scaling_driver]
                hours_per_unit = float(task.get("hours_per_unit", 0.0))
                expense_per_unit = float(task.get("expense_per_unit", 0.0))
                hours = round(hours_per_unit * units, 2)
                expenses = round(base_expenses + expense_per_unit * units, 2)
                estimate_basis = "driver_adjusted"
                estimate_basis_refs.append(
                    _driver_policy_ref(case_drivers, f"drivers/{scaling_driver}")
                )
                driver_range = _driver_range(case_drivers, str(scaling_driver))
                hours_min, hours_max = _range_from_scaled_driver(
                    base_value=0.0,
                    per_unit=hours_per_unit,
                    likely_value=units,
                    driver_range=driver_range,
                    provenance=provenance,
                    allow_wide_range=True,
                )
                expenses_min, expenses_max = _range_from_scaled_driver(
                    base_value=base_expenses,
                    per_unit=expense_per_unit,
                    likely_value=units,
                    driver_range=driver_range,
                    provenance=provenance,
                    allow_wide_range=expense_per_unit > 0,
                )
                scaling_formula = (
                    f"{hours_per_unit} hours/unit * {units} {scaling_driver} ({provenance})"
                )
                driver = driver_lookup.get(str(scaling_driver))
                assumptions = assumptions + [
                    f"Hours scaled by driver {scaling_driver}={units} ({provenance}); "
                    f"template hours {base_hours} used only as fallback."
                ]
                if provenance == "profile_default" and driver_range is not None:
                    assumptions = assumptions + [
                        f"Range widened by synthetic {scaling_driver} min/likely/max policy; "
                        "profile default is not observed fact."
                    ]
                if driver is not None:
                    note = (
                        f"Count driver {scaling_driver}={units} ({provenance}) scaled "
                        f"{phase_id}/{task_id}; profile defaults are assumptions, not observed facts."
                    )
                    effect = BudgetDriverEffect(
                        driver_id=str(scaling_driver),
                        driver_value=driver.value,
                        provenance=driver.provenance,
                        effect_type="count_scaling",
                        applied=True,
                        phase_ids=[phase_id],
                        task_ids=[task_id],
                        source_refs=driver.source_refs,
                        structured_ref=_driver_policy_ref(
                            case_drivers,
                            f"drivers/{scaling_driver}",
                        ),
                        note=note,
                    )
                    driver_effects_by_key[_driver_effect_key(effect)] = effect
            else:
                hours = base_hours
                expenses = base_expenses
                if scaling_driver is not None:
                    driver = driver_lookup.get(str(scaling_driver))
                    driver_range = _driver_range(case_drivers, str(scaling_driver))
                    if driver is not None and driver.provenance == "unknown" and driver_range:
                        estimate_basis = "unknown"
                        estimate_basis_refs.append(
                            _driver_policy_ref(case_drivers, f"drivers/{scaling_driver}")
                        )
                        hours_per_unit = float(task.get("hours_per_unit", 0.0))
                        expense_per_unit = float(task.get("expense_per_unit", 0.0))
                        minimum, _likely, maximum = driver_range
                        ranged_hours_min = round(hours_per_unit * minimum, 2)
                        ranged_hours_max = round(hours_per_unit * maximum, 2)
                        ranged_expenses_min = round(
                            base_expenses + expense_per_unit * minimum,
                            2,
                        )
                        ranged_expenses_max = round(
                            base_expenses + expense_per_unit * maximum,
                            2,
                        )
                        hours_min = min(hours, ranged_hours_min)
                        hours_max = max(hours, ranged_hours_max)
                        expenses_min = min(expenses, ranged_expenses_min)
                        expenses_max = max(expenses, ranged_expenses_max)
                        assumptions = assumptions + [
                            f"Range widened by unknown {scaling_driver} min/max policy; "
                            "template value remains the likely fallback."
                        ]

            intensity_multiplier, intensity_notes, intensity_effects = _intensity_adjustment(
                phase_id,
                task_id,
                case_drivers,
            )
            if hours_min is None:
                hours_min = float(task.get("estimated_hours_min", max(0.0, hours * 0.8)))
            if hours_max is None:
                hours_max = float(task.get("estimated_hours_max", hours * 1.25))
            if expenses_min is None:
                expenses_min = float(task.get("estimated_expenses_min", expenses))
            if expenses_max is None:
                expenses_max = float(task.get("estimated_expenses_max", expenses))
            if intensity_multiplier != 1.0:
                hours = round(hours * intensity_multiplier, 2)
                hours_min = round(hours_min * intensity_multiplier, 2)
                hours_max = round(hours_max * intensity_multiplier, 2)
                apply_intensity_to_expenses = (
                    bool(
                        (case_drivers.intensity_multiplier_policy or {}).get(
                            "applies_to_expense_bearing_lines",
                            False,
                        )
                    )
                    if case_drivers is not None
                    else False
                )
                if apply_intensity_to_expenses and expenses > 0:
                    expenses = round(expenses * intensity_multiplier, 2)
                    expenses_min = round(expenses_min * intensity_multiplier, 2)
                    expenses_max = round(expenses_max * intensity_multiplier, 2)
                assumptions = assumptions + [
                    f"Hours adjusted by cumulative intensity multiplier {intensity_multiplier}x."
                ]
                if apply_intensity_to_expenses and expenses > 0:
                    assumptions = assumptions + [
                        "Expense-bearing line adjusted by the same synthetic intensity multiplier."
                    ]
            assumptions = assumptions + intensity_notes
            for effect in intensity_effects:
                driver_effects_by_key[_driver_effect_key(effect)] = effect

            rate, rate_source, timekeeper_id, timekeeper_note, rate_issue_code = _task_rate(
                task=task,
                role=role,
                rates=rates,
                rate_resolution=rate_resolution,
            )
            if timekeeper_note is not None:
                assumptions = assumptions + [timekeeper_note]
            if rate_issue_code is not None:
                rate_issue_codes.add(rate_issue_code)
                if timekeeper_note is not None:
                    rate_issue_notes.append(timekeeper_note)
            fees = round(hours * rate, 2) if rate is not None else None
            if rate is not None and rate_source == "synthetic_named_timekeeper_override":
                rate_formula = (
                    f"{hours} hours * {rate} synthetic named timekeeper rate ({timekeeper_id})"
                )
            elif rate is not None:
                rate_formula = f"{hours} hours * {rate} synthetic hourly rate"
            else:
                rate_formula = "hours only; no authorized rate present"
            calculation_formula = (
                f"{scaling_formula}; {rate_formula}" if scaling_formula else rate_formula
            )
            lines.append(
                BudgetLine(
                    phase_id=phase_id,
                    phase_name=phase_name,
                    task_id=task_id,
                    task_name=str(task["task_name"]),
                    staffing_role=role,
                    timekeeper_id=timekeeper_id,
                    estimated_hours=hours,
                    estimated_hours_min=round(hours_min, 2),
                    estimated_hours_max=round(hours_max, 2),
                    hourly_rate=rate,
                    rate_source=rate_source,  # type: ignore[arg-type]
                    rate_is_synthetic=True,
                    estimated_fees=fees,
                    estimated_expenses=expenses,
                    estimated_expenses_min=round(expenses_min, 2),
                    estimated_expenses_max=round(expenses_max, 2),
                    calculation_formula=calculation_formula,
                    external_code_candidate=task.get("external_code_candidate"),
                    expense_code=task.get("expense_code"),
                    assumptions=assumptions,
                    evidence_refs=[],
                    estimate_basis=estimate_basis,  # type: ignore[arg-type]
                    estimate_basis_refs=estimate_basis_refs,
                )
            )

    contingency_percent = float(template.get("contingency_percent", 0.0))
    scenario_set = _build_scenario_set(
        template,
        lines,
        contingency_percent,
        case_drivers=case_drivers,
    )
    selected_lines = _selected_scenario_lines(template, lines, scenario_set)
    selected_scenario = next(
        scenario
        for scenario in scenario_set.scenarios
        if scenario.scenario_id == scenario_set.selected_scenario_id
    )
    selected_totals = _budget_totals(selected_lines, contingency_percent)
    mode = _pricing_status(selected_lines)
    report = _calculation_report(selected_lines, contingency_percent, mode=mode)
    driver_effects = sorted(
        [
            *driver_effects_by_key.values(),
            *_driver_boundary_effects(case_drivers),
        ],
        key=lambda effect: (
            effect.driver_id,
            "" if effect.driver_value is None else str(effect.driver_value),
            ",".join(effect.phase_ids),
            ",".join(effect.task_ids),
        ),
    )
    guideline_flags = _guideline_flags(selected_lines, selected_totals.total, case_drivers)
    driver_assumptions = [
        effect.note for effect in driver_effects if effect.effect_type != "unknown_driver"
    ]
    driver_unknowns = [
        effect.note for effect in driver_effects if effect.effect_type == "unknown_driver"
    ]
    scenario_policy_unknowns = list(scenario_set.policy_issue_notes)
    rate_resolution_unknowns = (
        list(rate_resolution.review_notes)
        if rate_resolution is not None and rate_resolution.review_required
        else []
    )
    driver_unknowns = (
        driver_unknowns
        + [flag.note for flag in guideline_flags if flag.status == "flagged_for_human_review"]
        + scenario_policy_unknowns
        + rate_resolution_unknowns
        + rate_issue_notes
    )

    policy_exclusions = [
        "conflict clearance",
        "engagement authorization",
        "carrier/client submission",
        "court filing",
    ]
    rate_basis_assumptions = (
        [f"Rate basis: {rate_resolution.note}"]
        if rate_resolution is not None and rate_resolution.source == "carrier_rate_card"
        else []
    )
    assumptions = (
        list(template.get("assumptions", [])) + rate_basis_assumptions + driver_assumptions
    )
    exclusions = list(template.get("exclusions", [])) + policy_exclusions
    unknowns = list(template.get("unknowns", [])) + driver_unknowns
    rate_basis_support_items = [
        _support_item(
            "assumption",
            text,
            "carrier_rate_card",
            structured_ref=(
                f"carrier-rate-card://{rate_resolution.rate_card_id}"
                f"/{rate_resolution.carrier_id}/{rate_resolution.state}"
            ),
        )
        for text in rate_basis_assumptions
    ]
    support_items = [
        _support_item(
            "assumption",
            "Budget generation was attempted only after human confirmation.",
            "human_confirmation",
            structured_ref=_confirmation_ref(confirmation),
        ),
        *_template_support_items(profile, confirmation.confirmed_matter_family, template),
        *rate_basis_support_items,
        *_budget_driver_support_items(driver_effects, guideline_flags),
        *_scenario_policy_issue_notes(scenario_set),
        *_rate_review_support_items(rate_resolution, rate_issue_codes, rate_issue_notes),
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
        subtotal_fees=selected_totals.subtotal_fees,
        subtotal_expenses=selected_totals.subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=selected_totals.contingency_amount,
        total_proposed_budget=selected_totals.total,
        scenario_name=selected_scenario.scenario_id,
        headline_subtotal_fees=selected_scenario.subtotal_fees,
        headline_subtotal_expenses=selected_scenario.subtotal_expenses,
        headline_contingency_amount=selected_scenario.contingency_amount,
        headline_total_proposed_budget=selected_scenario.total_proposed_budget,
        headline_total_proposed_budget_min=selected_scenario.total_budget_min,
        headline_total_proposed_budget_max=selected_scenario.total_budget_max,
        expected_total_proposed_budget_min=scenario_set.expected_total_min,
        expected_total_proposed_budget_max=scenario_set.expected_total_max,
        unknown_probability_mass=scenario_set.unknown_probability_mass,
        expected_value_method=scenario_set.expected_value_method,
        scenario_set=scenario_set,
        calculation_report=report,
        assumptions=assumptions,
        exclusions=exclusions,
        unknowns=unknowns,
        driver_profile_summary=_driver_profile_summary(case_drivers),
        driver_effects=driver_effects,
        guideline_flags=guideline_flags,
        budget_support_items=support_items,
        display_banner={
            "candidate_only": True,
            "synthetic_only": True,
            "pricing_status": mode,
            "rate_review_required": bool(
                (rate_resolution is not None and rate_resolution.review_required)
                or rate_issue_codes
            ),
            "rate_review_issue_codes": sorted(
                set(rate_resolution.review_issue_codes if rate_resolution is not None else [])
                | rate_issue_codes
            ),
            "not_authorized_for_client_submission": True,
            "blocked_actions": [
                "client_submission",
                "carrier_submission",
                "matter_opening",
                "conflict_clearance",
            ],
        },
    )
