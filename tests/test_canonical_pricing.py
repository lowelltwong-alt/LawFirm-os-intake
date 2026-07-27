"""DT2 — deterministic canonical pricing engine.

Prices a ``CanonicalDriverProfile`` into exact minor-unit dollars:
CLCM-sourced phase-baseline hours × contract driver multipliers × governed rates.
Deterministic, fail-closed, candidate-only, ``reference_class_only``; no ML; the
engine never invents a dollar — every cell is recomputable from stored fields.
"""

from decimal import Decimal

import pytest

from lawfirm_os_intake.canonical_pricing import (
    apply_capped_composite,
    build_canonical_priced_work_plan,
    compare_with_legacy_sizing,
)
from lawfirm_os_intake.driver_taxonomy import build_canonical_driver_profile
from lawfirm_os_intake.models import CanonicalPricedWorkPlan

LEGACY = {
    "party_count": 2,
    "injury_severity": "surgical",
    "liability_clarity": "disputed",
    "exposure_band": "high",
    "venue": "state_default",
}


def _plan(repo_root, legacy=None):
    profile = build_canonical_driver_profile(legacy or LEGACY, repo_root=repo_root)
    return build_canonical_priced_work_plan(profile, repo_root=repo_root)


def test_plan_prices_and_is_deterministic(repo_root):
    first = _plan(repo_root)
    second = _plan(repo_root)
    assert isinstance(first, CanonicalPricedWorkPlan)
    assert first.total_dollars_minor_units > 0
    assert first.model_dump() == second.model_dump()
    assert first.reference_class_only is True
    assert first.calibrated is False
    assert first.dollars_remain_deterministic is True


def test_phase_multipliers_compose_exactly(repo_root):
    # Elicited from LEGACY: damages_severity serious 1.5 (L100,L300);
    # case_stakes high 1.55 (all); party_count 2_3 1.15 (L200,L300);
    # causation_disputed +0.8 additive (L300). Everything else neutral 1.0.
    plan = _plan(repo_root)
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    assert mult["L100"] == Decimal("2.325")  # 1.5 * 1.55
    assert mult["L200"] == Decimal("1.7825")  # 1.55 * 1.15
    assert mult["L300"] == Decimal("3.47375")  # 1.5*1.55*1.15 + 0.8
    assert mult["L400"] == Decimal("1.55")
    assert mult["L500"] == Decimal("1.55")


def test_not_elicited_drivers_price_neutral(repo_root):
    # Dropping liability_clarity -> causation_disputed becomes not_elicited ->
    # its +0.8 additive delta must NOT be applied (neutral, rule-attributed).
    legacy = {k: v for k, v in LEGACY.items() if k != "liability_clarity"}
    plan = _plan(repo_root, legacy)
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    assert mult["L300"] == Decimal("2.67375")  # 1.5*1.55*1.15, no +0.8
    assert "causation_disputed" in plan.neutral_assumed_driver_ids


def test_baseline_hours_are_clcm_sourced(repo_root):
    plan = _plan(repo_root)
    assert plan.total_base_hours == "472"
    base = {row.phase: Decimal(row.base_hours) for row in plan.phase_rows}
    assert base["L100"] == Decimal("66.0800")  # 472 * 0.14
    assert base["L400"] == Decimal("202.9600")  # 472 * 0.43


def test_governed_rates_resolve_from_rate_card(repo_root):
    # Default carrier synthetic-carrier-a, state NV:
    # partner 450 -> 45000; associate 250 -> 25000; paralegal 160 -> 16000.
    plan = _plan(repo_root)
    rates = {cell.role: cell.rate_minor_units for cell in plan.phase_rows[0].role_cells}
    assert rates == {"senior_attorney": 45000, "junior_attorney": 25000, "paralegal": 16000}


def test_totals_recompute_fail_closed(repo_root):
    plan = _plan(repo_root)
    dumped = plan.model_dump()
    dumped["total_dollars_minor_units"] += 1
    with pytest.raises(ValueError):
        CanonicalPricedWorkPlan.model_validate(dumped)


def test_cell_tamper_rejected(repo_root):
    plan = _plan(repo_root)
    dumped = plan.model_dump()
    dumped["phase_rows"][0]["role_cells"][0]["dollars_minor_units"] += 100
    with pytest.raises(ValueError):
        CanonicalPricedWorkPlan.model_validate(dumped)


def test_capped_composite_rule():
    # Within a correlated group: largest applies in full, others sqrt.
    # Ungrouped factors multiply normally; result capped at the row cap.
    result = apply_capped_composite(
        [("a", Decimal("4.0")), ("b", Decimal("2.25"))],
        groups=[{"a", "b"}],
        cap=Decimal("10.0"),
    )
    assert result == Decimal("6.0")  # 4.0 * sqrt(2.25)
    capped = apply_capped_composite(
        [("a", Decimal("9.0")), ("c", Decimal("5.0"))],
        groups=[],
        cap=Decimal("10.0"),
    )
    assert capped == Decimal("10.0")


def test_applied_drivers_carry_confidence(repo_root):
    plan = _plan(repo_root)
    applied = {d.driver_id: d for d in plan.applied_drivers}
    assert applied["damages_severity"].confidence == "sourced_medium"
    assert applied["case_stakes"].confidence == "sourced_high"
    assert applied["damages_severity"].level == "serious"


def test_comparison_with_legacy_sizing(repo_root):
    comparison = compare_with_legacy_sizing(LEGACY, repo_root=repo_root)
    assert comparison["legacy_sized_total_minor_units"] > 0
    assert comparison["canonical_priced_total_minor_units"] > 0
    assert comparison["same_inputs"] is True
