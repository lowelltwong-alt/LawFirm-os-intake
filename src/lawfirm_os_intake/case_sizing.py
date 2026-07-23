"""Case sizing + settlement economics v0 (deterministic, candidate-only).

Extends the existing driver machinery with a versioned ``CaseCostDriver`` catalog,
a proportionality gate, and settlement-posture cost-of-risk arithmetic. All money
is exact integer minor units. Win probability is a declared assumption, never a
model output. Nothing here authorizes a budget, submission, or matter action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    CaseCostDriverCatalog,
    CaseCostDriverSpec,
    CaseSizingEffect,
    CaseSizingReport,
    ProportionalityAssessment,
    SettlementPosture,
    SettlementPostureAnalysis,
    SettlementPostureInput,
    SizedWorkPlan,
)
from .util import digest_json, now_iso

CASE_SIZING_POLICY_REF = "config/synthetic-case-sizing-policy.yaml"


def load_case_sizing_policy(path: str | Path) -> dict[str, Any]:
    """Load the synthetic case-sizing policy, refusing real-firm content."""

    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("case sizing policy must be a mapping")
    if policy.get("contains_real_firm_data", False):
        raise ValueError("real firm case-sizing policies are prohibited in this repository")
    if policy.get("data_origin") != "synthetic" or policy.get("candidate_only") is not True:
        raise ValueError("case sizing policy must be synthetic candidate-only")
    return policy


def build_case_cost_driver_catalog(policy: dict[str, Any]) -> CaseCostDriverCatalog:
    drivers = [
        CaseCostDriverSpec(
            driver_id=str(spec["driver_id"]),
            driver_class=str(spec["driver_class"]),
            measurement=str(spec["measurement"]),
            effect_surface=[str(item) for item in spec.get("effect_surface", [])],
            effect_form=str(spec["effect_form"]),  # type: ignore[arg-type]
            unit=spec.get("unit"),
            note=str(spec.get("note", "")),
        )
        for spec in policy.get("drivers", [])
    ]
    return CaseCostDriverCatalog(
        catalog_id=str(policy.get("case_sizing_policy_id", "unknown")),
        version=str(policy.get("version", "unknown")),
        drivers=drivers,
    )


def _multiplier_factor(policy: dict[str, Any], driver_id: str, value: Any) -> float:
    table = policy.get("factors", {}).get(driver_id, {})
    if driver_id == "party_count":
        surcharge = float(table.get("per_additional_party_surcharge", 0.0))
        count = int(value) if value is not None else 1
        return 1.0 + surcharge * max(count - 1, 0)
    if value is None:
        return 1.0
    return float(table.get(str(value), 1.0))


def size_work_plan(
    *,
    base_work_plan_total_minor_units: int,
    case_type: str,
    drivers: dict[str, Any],
    policy: dict[str, Any],
) -> SizedWorkPlan:
    """Apply the case cost drivers to the base work-plan total (exact minor units)."""

    catalog = build_case_cost_driver_catalog(policy)
    running = int(base_work_plan_total_minor_units)
    effects: list[CaseSizingEffect] = []
    applied: list[str] = []
    for spec in catalog.drivers:
        value = drivers.get(spec.driver_id)
        before = running
        if spec.effect_form == "multiplier":
            factor = _multiplier_factor(policy, spec.driver_id, value)
            after = round(before * factor)
            effects.append(
                CaseSizingEffect(
                    driver_id=spec.driver_id,
                    driver_value=str(value),
                    effect_form="multiplier",
                    factor=factor,
                    before_minor_units=before,
                    after_minor_units=after,
                    note=f"{spec.driver_id}={value} -> x{factor}",
                )
            )
        elif spec.effect_form == "additive":
            amount = int(policy.get("additives", {}).get(spec.driver_id, {}).get(str(value), 0))
            after = before + amount
            effects.append(
                CaseSizingEffect(
                    driver_id=spec.driver_id,
                    driver_value=str(value),
                    effect_form="additive",
                    amount_minor_units=amount,
                    before_minor_units=before,
                    after_minor_units=after,
                    note=f"{spec.driver_id}={value} -> +{amount}",
                )
            )
        else:  # gate
            gate = policy.get("gates", {}).get(spec.driver_id, {})
            open_bands = {str(band) for band in gate.get("open_bands", [])}
            gate_open = str(value) in open_bands
            amount = int(gate.get("trial_block_minor_units", 0)) if gate_open else 0
            after = before + amount
            effects.append(
                CaseSizingEffect(
                    driver_id=spec.driver_id,
                    driver_value=str(value),
                    effect_form="gate",
                    gate_open=gate_open,
                    amount_minor_units=amount,
                    before_minor_units=before,
                    after_minor_units=after,
                    note=f"{spec.driver_id}={value} -> gate {'open' if gate_open else 'closed'}",
                )
            )
        running = after
        applied.append(spec.driver_id)

    return SizedWorkPlan(
        case_type=case_type,
        base_work_plan_total_minor_units=int(base_work_plan_total_minor_units),
        sized_work_plan_total_minor_units=running,
        effects=effects,
        drivers_applied=applied,
    )


def assess_proportionality(
    *,
    work_plan_total_minor_units: int,
    exposure_minor_units: int,
    case_type: str,
    policy: dict[str, Any],
    override_reason: str | None = None,
) -> ProportionalityAssessment:
    """Fail-closed proportionality gate: over-band budgets block for human override."""

    bands = policy.get("proportionality_bands", {})
    if case_type not in bands:
        raise ValueError(f"no proportionality band declared for case type {case_type!r}")
    band_max = float(bands[case_type]["max_budget_to_exposure_ratio"])
    ratio = round(work_plan_total_minor_units / exposure_minor_units, 6)
    disproportionate = ratio > band_max
    return ProportionalityAssessment(
        case_type=case_type,
        work_plan_total_minor_units=int(work_plan_total_minor_units),
        exposure_minor_units=int(exposure_minor_units),
        ratio=ratio,
        band_max_ratio=band_max,
        status="blocked_disproportionate_budget" if disproportionate else "within_band",
        human_override_required=disproportionate,
        override_reason=override_reason if disproportionate else None,
        recommended_plan="settle_lean_plan" if disproportionate else "full_work_plan",
    )


def rank_settlement_postures(inp: SettlementPostureInput) -> SettlementPostureAnalysis:
    """Rank settle-now / defend-then-settle / try by expected total cost of risk."""

    loss_probability = (100.0 - inp.win_probability_percent) / 100.0
    try_indemnity = round(inp.exposure_minor_units * loss_probability)
    raw = [
        SettlementPosture(
            posture="settle_now",
            indemnity_minor_units=inp.settlement_value_minor_units,
            defense_minor_units=inp.defense_cost_settle_now_minor_units,
            expected_total_cost_of_risk_minor_units=(
                inp.settlement_value_minor_units + inp.defense_cost_settle_now_minor_units
            ),
            formula="S + defense(settle_now)",
        ),
        SettlementPosture(
            posture="defend_then_settle",
            indemnity_minor_units=inp.settlement_value_after_defense_minor_units,
            defense_minor_units=inp.defense_cost_defend_settle_minor_units,
            expected_total_cost_of_risk_minor_units=(
                inp.settlement_value_after_defense_minor_units
                + inp.defense_cost_defend_settle_minor_units
            ),
            formula="S' + defense(defend_then_settle)",
        ),
        SettlementPosture(
            posture="try",
            indemnity_minor_units=try_indemnity,
            defense_minor_units=inp.defense_cost_try_minor_units,
            expected_total_cost_of_risk_minor_units=(
                try_indemnity + inp.defense_cost_try_minor_units
            ),
            formula="(1 - p) * E + defense(try)  [p is a declared assumption]",
        ),
    ]
    # Stable ordering: cost ascending, then a fixed posture order to break ties.
    order = {"settle_now": 0, "defend_then_settle": 1, "try": 2}
    postures = sorted(
        raw, key=lambda p: (p.expected_total_cost_of_risk_minor_units, order[p.posture])
    )
    best = postures[0]
    return SettlementPostureAnalysis(
        postures=postures,
        recommended_posture=best.posture,
        recommended_budget_envelope_minor_units=best.defense_minor_units,
        recommended_expected_cost_of_risk_minor_units=(
            best.expected_total_cost_of_risk_minor_units
        ),
    )


def build_case_sizing_report(
    *,
    case_type: str,
    base_work_plan_total_minor_units: int,
    drivers: dict[str, Any],
    posture_input: SettlementPostureInput,
    policy: dict[str, Any],
    override_reason: str | None = None,
    generated_at: str | None = None,
) -> CaseSizingReport:
    sized = size_work_plan(
        base_work_plan_total_minor_units=base_work_plan_total_minor_units,
        case_type=case_type,
        drivers=drivers,
        policy=policy,
    )
    proportionality = assess_proportionality(
        work_plan_total_minor_units=sized.sized_work_plan_total_minor_units,
        exposure_minor_units=posture_input.exposure_minor_units,
        case_type=case_type,
        policy=policy,
        override_reason=override_reason,
    )
    analysis = rank_settlement_postures(posture_input)
    basis = {
        "case_type": case_type,
        "sized": sized.sized_work_plan_total_minor_units,
        "ratio": proportionality.ratio,
        "recommended": analysis.recommended_posture,
    }
    return CaseSizingReport(
        case_sizing_report_id="casesizing-" + digest_json(basis).removeprefix("sha256:")[:16],
        case_type=case_type,
        sized_work_plan=sized,
        proportionality=proportionality,
        settlement_posture_analysis=analysis,
        required_next_gates=[
            "human_review_before_any_budget_authorization",
            "human_review_of_recommended_settlement_posture",
            "orchestrator_owned_submission_contract",
        ],
        generated_at=generated_at or now_iso(),
    )
