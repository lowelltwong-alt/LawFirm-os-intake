"""DT2 — deterministic canonical pricing engine.

Prices a ``CanonicalDriverProfile`` into exact minor-unit dollars, composing the
three governed inputs DT1 put in place:

1. **Baseline hours** — the contract's CLCM-sourced case-type median (professional
   malpractice: 472 attorney hours; Hannaford-Agor & Waters, NCSC 2013) spread over
   UTBMS phases by the CLCM-sourced phase fractions.
2. **× driver multipliers** — elicited assignments apply their contract ``point``
   values (or additive deltas) to the phases containing their target rows;
   ``not_elicited`` drivers stay neutral 1.0 (the assumption is already
   rule-attributed on the profile). Correlated drivers compose via the contract's
   capped-composite rule; every phase multiplier is capped at the contract's
   ``row_multiplier_cap``. Posture flags and un-elicited phase blocks have no hour
   effect. E-code expense rows (E115/E119) are excluded — expenses are a separate
   layer.
3. **× governed rates** — the synthetic carrier rate card (carrier × state ×
   title), blended through a CLCM-sourced role mix (auto-tort median 75.5 senior /
   78 junior / 42.5 paralegal of 196 hours), mapped senior→partner,
   junior→associate, paralegal→paralegal.

All arithmetic is ``Decimal`` with fixed quantization (hours 4dp HALF_UP; cell
dollars rounded HALF_UP to integer minor units); the ``CanonicalPricedWorkPlan``
validators recompute every cell, row, and total from stored fields, so any
tampering fails closed. Candidate-only, synthetic-only, ``reference_class_only``;
no ML; the engine never invents a dollar.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import yaml

from .driver_taxonomy import (
    EXPECTED_CONTRACT_DIGEST,
    _driver_defs,
    load_driver_taxonomy,
)
from .models import (
    AppliedDriverEffect,
    CanonicalDriverProfile,
    CanonicalPricedWorkPlan,
    PricedPhaseRow,
    PricedRoleCell,
)
from .util import digest_json

RATE_CARD_REF = "config/synthetic-carrier-rate-card.yaml"

PHASES = ("L100", "L200", "L300", "L400", "L500")
_QUANTUM = Decimal("0.0001")

# Which CLCM case-type median anchors each line's baseline hours (DT5: all four
# contract lines are CLCM-mapped; each uses its own CLCM stage-share vector).
LINE_TO_CLCM_CASE_TYPE = {
    "medical_malpractice_defense": "professional_malpractice",
    "auto_bodily_injury_defense": "automobile_tort",
    "general_premises_liability_defense": "premises_liability",
    "epli_employment_defense": "employment",
}

# CLCM auto-tort median role mix (75.5 senior / 78 junior / 42.5 paralegal of 196
# total attorney hours; the only case type with published role detail). Weights
# quantized to 6dp; mapped to rate-card titles senior->partner, junior->associate.
_ROLE_WEIGHTS: dict[str, Decimal] = {
    "senior_attorney": (Decimal("75.5") / Decimal("196")).quantize(Decimal("0.000001")),
    "junior_attorney": (Decimal("78") / Decimal("196")).quantize(Decimal("0.000001")),
    "paralegal": (Decimal("42.5") / Decimal("196")).quantize(Decimal("0.000001")),
}
_ROLE_TO_TITLE = {
    "senior_attorney": "partner",
    "junior_attorney": "associate",
    "paralegal": "paralegal",
}


def _row_phase(row: str) -> str | None:
    """UTBMS row -> containing phase; E-code expense rows are excluded (None)."""

    if row.startswith("L") and len(row) >= 2 and row[1] in "12345":
        return f"L{row[1]}00"
    return None


def apply_capped_composite(
    factors: list[tuple[str, Decimal]],
    *,
    groups: list[set[str]],
    cap: Decimal,
) -> Decimal:
    """Compose multiplicative factors: within a correlated group the largest
    applies in full and the rest at sqrt; ungrouped factors multiply normally;
    the result is capped."""

    remaining = dict(factors)
    product = Decimal("1")
    for group in groups:
        members = {name: remaining.pop(name) for name in list(remaining) if name in group}
        if not members:
            continue
        largest = max(members, key=lambda name: members[name])
        product *= members.pop(largest)
        for value in members.values():
            product *= value.sqrt()
    for value in remaining.values():
        product *= value
    return min(product, cap)


def _load_rates(
    repo_root: Path, carrier_id: str | None, state: str | None
) -> tuple[str, str, dict[str, int]]:
    card = yaml.safe_load((repo_root / RATE_CARD_REF).read_text(encoding="utf-8"))
    if card.get("contains_real_negotiated_rates") is not False:
        raise ValueError("real negotiated rates are prohibited in the synthetic rate card")
    carrier = carrier_id or card["default_carrier_id"]
    resolved_state = state or card["default_state"]
    schedule = card["carriers"][carrier]["schedule"].get(resolved_state)
    if schedule is None:
        raise ValueError(f"no rate schedule for carrier {carrier!r} in state {resolved_state!r}")
    rates: dict[str, int] = {}
    for role, title in _ROLE_TO_TITLE.items():
        if title not in schedule:
            raise ValueError(f"rate card missing title {title!r} for {carrier}/{resolved_state}")
        rates[role] = int(schedule[title]) * 100
    return carrier, resolved_state, rates


def build_canonical_priced_work_plan(
    profile: CanonicalDriverProfile,
    *,
    repo_root: str | Path,
    carrier_id: str | None = None,
    state: str | None = None,
) -> CanonicalPricedWorkPlan:
    root = Path(repo_root)
    contract = load_driver_taxonomy(root)
    if profile.contract_digest != EXPECTED_CONTRACT_DIGEST:
        raise ValueError("profile was built against a different contract digest; refusing")
    defs = _driver_defs(contract, profile.line_id)

    clcm_case_type = LINE_TO_CLCM_CASE_TYPE.get(profile.line_id)
    if clcm_case_type is None:
        raise ValueError(f"no CLCM baseline mapping for line {profile.line_id!r}")
    baseline = contract["phase_baseline"]
    total_base_hours = Decimal(str(baseline["clcm_case_type_medians"][clcm_case_type]["hours"]))
    fractions = baseline["by_case_type"][clcm_case_type]["fractions"]

    composition = contract["conventions"]["composition"]
    groups = [set(group) for group in composition.get("correlated_groups", [])]
    cap = Decimal(str(composition["row_multiplier_cap"]))

    # Per-phase multiplicative factors and additive deltas from elicited drivers.
    elicited = [a for a in profile.assignments if a.status == "elicited"]
    applied: list[AppliedDriverEffect] = []
    factors_by_phase: dict[str, list[tuple[str, Decimal]]] = {p: [] for p in PHASES}
    deltas_by_phase: dict[str, Decimal] = {p: Decimal("0") for p in PHASES}
    for assignment in elicited:
        definition = defs[assignment.driver_id]
        mode = definition["mode"]
        if mode in ("posture_flag", "phase_block"):
            continue
        level_entry = next(
            entry for entry in definition["levels"] if entry["level"] == assignment.level
        )
        phases = sorted(
            {p for p in (_row_phase(row) for row in definition["utbms_rows"]) if p is not None}
        )
        if not phases:
            continue
        if mode == "multiplicative":
            factor = Decimal(str(level_entry["point"]))
            for phase in phases:
                factors_by_phase[phase].append((assignment.driver_id, factor))
            factor_repr = str(factor)
        else:  # additive
            delta = Decimal(str(level_entry["additive_delta"]))
            for phase in phases:
                deltas_by_phase[phase] += delta
            factor_repr = f"+{delta}"
        applied.append(
            AppliedDriverEffect(
                driver_id=assignment.driver_id,
                level=assignment.level or "",
                mode=mode,
                factor=factor_repr,
                phases=phases,
                confidence=definition["confidence"],
                source=definition.get("source", ""),
            )
        )

    carrier, resolved_state, rates = _load_rates(root, carrier_id, state)

    phase_rows: list[PricedPhaseRow] = []
    for phase in PHASES:
        base_hours = (total_base_hours * Decimal(str(fractions[phase]))).quantize(
            _QUANTUM, rounding=ROUND_HALF_UP
        )
        multiplier = min(
            apply_capped_composite(factors_by_phase[phase], groups=groups, cap=cap)
            + deltas_by_phase[phase],
            cap,
        )
        adjusted = (base_hours * multiplier).quantize(_QUANTUM, rounding=ROUND_HALF_UP)
        cells: list[PricedRoleCell] = []
        for role, weight in _ROLE_WEIGHTS.items():
            hours = (adjusted * weight).quantize(_QUANTUM, rounding=ROUND_HALF_UP)
            dollars = int((hours * rates[role]).to_integral_value(rounding=ROUND_HALF_UP))
            cells.append(
                PricedRoleCell(
                    role=role,  # type: ignore[arg-type]
                    weight=str(weight),
                    hours=str(hours),
                    rate_minor_units=rates[role],
                    dollars_minor_units=dollars,
                )
            )
        phase_rows.append(
            PricedPhaseRow(
                phase=phase,  # type: ignore[arg-type]
                base_hours=str(base_hours),
                multiplier=str(multiplier),
                adjusted_hours=str(adjusted),
                role_cells=cells,
                dollars_minor_units=sum(cell.dollars_minor_units for cell in cells),
            )
        )

    total_adjusted = sum(Decimal(row.adjusted_hours) for row in phase_rows)
    total_dollars = sum(row.dollars_minor_units for row in phase_rows)
    basis = {
        "profile_id": profile.profile_id,
        "contract_digest": profile.contract_digest,
        "carrier": carrier,
        "state": resolved_state,
        "phase_multipliers": [row.multiplier for row in phase_rows],
        "total_dollars": total_dollars,
    }
    return CanonicalPricedWorkPlan(
        plan_id="canonpriced-" + digest_json(basis).removeprefix("sha256:")[:16],
        line_id=profile.line_id,
        profile_id=profile.profile_id,
        contract_id=profile.contract_id,
        contract_version=profile.contract_version,
        contract_digest=profile.contract_digest,
        clcm_case_type=clcm_case_type,
        total_base_hours=str(total_base_hours),
        carrier_id=carrier,
        state=resolved_state,
        phase_rows=phase_rows,
        applied_drivers=applied,
        neutral_assumed_driver_ids=list(profile.not_elicited_driver_ids),
        posture_flags=dict(profile.posture_flags),
        total_adjusted_hours=str(total_adjusted),
        total_dollars_minor_units=total_dollars,
    )


def compare_with_legacy_sizing(
    legacy_sizing_drivers: dict[str, Any],
    *,
    repo_root: str | Path,
    base_work_plan_total_minor_units: int = 1_200_000,
) -> dict[str, Any]:
    """Side-by-side of the existing legacy sizing math and the canonical engine.

    Informational only: the legacy path is unchanged and remains authoritative for
    the pipeline; the canonical engine is the candidate successor under review.
    """

    from .case_sizing import CASE_SIZING_POLICY_REF, load_case_sizing_policy, size_work_plan
    from .driver_taxonomy import build_canonical_driver_profile

    root = Path(repo_root)
    policy = load_case_sizing_policy(root / CASE_SIZING_POLICY_REF)
    legacy_sized = size_work_plan(
        base_work_plan_total_minor_units=base_work_plan_total_minor_units,
        case_type="medical_malpractice",
        drivers=legacy_sizing_drivers,
        policy=policy,
    )
    profile = build_canonical_driver_profile(legacy_sizing_drivers, repo_root=root)
    plan = build_canonical_priced_work_plan(profile, repo_root=root)
    return {
        "same_inputs": True,
        "legacy_sized_total_minor_units": legacy_sized.sized_work_plan_total_minor_units,
        "canonical_priced_total_minor_units": plan.total_dollars_minor_units,
        "canonical_plan_id": plan.plan_id,
        "note": (
            "legacy sizing scales a given base work-plan total; the canonical engine "
            "derives hours from the CLCM baseline and prices them at governed rates - "
            "totals are not expected to match while both are candidates"
        ),
    }
