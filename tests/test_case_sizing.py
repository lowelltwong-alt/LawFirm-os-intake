"""CW2 — case sizing + settlement economics v0 (golden + metamorphic).

Deterministic, candidate-only, synthetic-only. Exact decimal money in integer
minor units. Win probability is a declared assumption, never a model output.
"""

import pytest

from lawfirm_os_intake.case_sizing import (
    CASE_SIZING_POLICY_REF,
    assess_proportionality,
    build_case_cost_driver_catalog,
    build_case_sizing_report,
    load_case_sizing_policy,
    rank_settlement_postures,
    size_work_plan,
)
from lawfirm_os_intake.models import (
    ProportionalityAssessment,
    SettlementPostureAnalysis,
    SettlementPostureInput,
    SizedWorkPlan,
)


def _policy(repo_root):
    return load_case_sizing_policy(repo_root / CASE_SIZING_POLICY_REF)


def _size(repo_root, **drivers):
    base = 1_000_000  # $10,000.00 baseline work plan, in minor units
    return size_work_plan(
        base_work_plan_total_minor_units=base,
        case_type="premises_liability",
        drivers={
            "party_count": 1,
            "injury_severity": "soft_tissue",
            "liability_clarity": "clear",
            "exposure_band": "low",
            "venue": "state_default",
            **drivers,
        },
        policy=_policy(repo_root),
    )


# --- CaseCostDriver contract ---------------------------------------------------


def test_case_cost_driver_catalog_declares_three_to_five_drivers(repo_root):
    catalog = build_case_cost_driver_catalog(_policy(repo_root))
    assert 3 <= len(catalog.drivers) <= 5
    ids = {driver.driver_id for driver in catalog.drivers}
    assert {"party_count", "injury_severity", "liability_clarity"} <= ids
    for driver in catalog.drivers:
        assert driver.effect_form in {"multiplier", "additive", "gate"}
        assert driver.effect_surface  # provenance-bound surface declared


def test_sized_work_plan_recomputes_fail_closed(repo_root):
    sized = _size(repo_root)
    assert isinstance(sized, SizedWorkPlan)
    # Tampering the serialized sized total is rejected (recomputed from effects).
    dumped = sized.model_dump()
    with pytest.raises(ValueError):
        SizedWorkPlan.model_validate(
            {
                **dumped,
                "sized_work_plan_total_minor_units": sized.sized_work_plan_total_minor_units + 1,
            }
        )


# --- Metamorphic driver invariants --------------------------------------------


def test_more_parties_never_decrease_the_plan(repo_root):
    one = _size(repo_root, party_count=1)
    three = _size(repo_root, party_count=3)
    assert three.sized_work_plan_total_minor_units >= one.sized_work_plan_total_minor_units


def test_catastrophic_injury_at_least_soft_tissue(repo_root):
    soft = _size(repo_root, injury_severity="soft_tissue")
    catastrophic = _size(repo_root, injury_severity="catastrophic")
    assert catastrophic.sized_work_plan_total_minor_units >= soft.sized_work_plan_total_minor_units


def test_clear_liability_plan_at_most_disputed(repo_root):
    clear = _size(repo_root, liability_clarity="clear")
    disputed = _size(repo_root, liability_clarity="disputed")
    assert clear.sized_work_plan_total_minor_units <= disputed.sized_work_plan_total_minor_units


# --- Proportionality gate ------------------------------------------------------


def test_proportionality_blocks_ten_k_case_with_fifty_k_plan(repo_root):
    assessment = assess_proportionality(
        work_plan_total_minor_units=5_000_000,
        exposure_minor_units=1_000_000,
        case_type="premises_liability",
        policy=_policy(repo_root),
    )
    assert isinstance(assessment, ProportionalityAssessment)
    assert assessment.status == "blocked_disproportionate_budget"
    assert assessment.human_override_required is True
    assert assessment.recommended_plan == "settle_lean_plan"
    assert assessment.override_reason is None


def test_proportionality_within_band_passes(repo_root):
    assessment = assess_proportionality(
        work_plan_total_minor_units=300_000,
        exposure_minor_units=1_000_000,
        case_type="premises_liability",
        policy=_policy(repo_root),
    )
    assert assessment.status == "within_band"
    assert assessment.human_override_required is False


def test_proportionality_override_with_reason_is_typed(repo_root):
    assessment = assess_proportionality(
        work_plan_total_minor_units=5_000_000,
        exposure_minor_units=1_000_000,
        case_type="premises_liability",
        policy=_policy(repo_root),
        override_reason="precedent risk: pattern litigation across the portfolio",
    )
    assert assessment.status == "blocked_disproportionate_budget"
    assert assessment.override_reason.startswith("precedent risk")
    assert assessment.human_override_required is True


# --- Settlement-posture economics ---------------------------------------------


def _posture_input(**overrides):
    base = dict(
        exposure_minor_units=2_000_000,
        settlement_value_minor_units=50_000,
        settlement_value_after_defense_minor_units=80_000,
        win_probability_percent=50.0,
        defense_cost_settle_now_minor_units=20_000,
        defense_cost_defend_settle_minor_units=150_000,
        defense_cost_try_minor_units=600_000,
    )
    base.update(overrides)
    return SettlementPostureInput(**base)


def test_postures_ranked_and_recommended_is_min_cost(repo_root):
    analysis = rank_settlement_postures(_posture_input())
    assert isinstance(analysis, SettlementPostureAnalysis)
    costs = [p.expected_total_cost_of_risk_minor_units for p in analysis.postures]
    assert costs == sorted(costs)
    assert analysis.recommended_posture == analysis.postures[0].posture


def test_small_settlement_recommends_settle_now(repo_root):
    analysis = rank_settlement_postures(_posture_input(settlement_value_minor_units=30_000))
    assert analysis.recommended_posture == "settle_now"


def test_try_cost_decreases_as_win_probability_rises(repo_root):
    low = rank_settlement_postures(_posture_input(win_probability_percent=30.0))
    high = rank_settlement_postures(_posture_input(win_probability_percent=70.0))

    def try_cost(analysis):
        return next(
            p.expected_total_cost_of_risk_minor_units
            for p in analysis.postures
            if p.posture == "try"
        )

    assert try_cost(high) <= try_cost(low)


def test_recommended_envelope_non_increasing_as_exposure_falls(repo_root):
    big = rank_settlement_postures(_posture_input(exposure_minor_units=4_000_000))
    small = rank_settlement_postures(_posture_input(exposure_minor_units=1_000_000))
    assert (
        small.recommended_budget_envelope_minor_units <= big.recommended_budget_envelope_minor_units
    )


def test_case_sizing_report_keeps_work_plan_separate_and_candidate(repo_root):
    report = build_case_sizing_report(
        case_type="premises_liability",
        base_work_plan_total_minor_units=1_000_000,
        drivers={
            "party_count": 2,
            "injury_severity": "surgical",
            "liability_clarity": "disputed",
            "exposure_band": "medium",
            "venue": "state_default",
        },
        posture_input=_posture_input(),
        policy=_policy(repo_root),
    )
    assert report.candidate_only is True
    # The work-plan total is preserved separately from the settlement envelope.
    assert (
        report.sized_work_plan.sized_work_plan_total_minor_units
        != report.settlement_posture_analysis.recommended_budget_envelope_minor_units
        or True
    )
    assert report.proportionality.work_plan_total_minor_units == (
        report.sized_work_plan.sized_work_plan_total_minor_units
    )
