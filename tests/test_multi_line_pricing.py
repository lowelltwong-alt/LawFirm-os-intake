"""DT5 — multi-line canonical pricing (auto BI, GL/premises, EPLI absorbed).

Each line prices from its OWN CLCM stage-share vector and median hours; the
EPLI correlated group (plaintiff_structure / admin_posture / punitive_exposure)
exercises the capped-composite rule for real; the auto line's trial/appeal
drivers now override the universal ones (contract v1.1 fix — no double-count).
Candidate-only, synthetic-only, reference_class_only; dollars deterministic.
"""

from decimal import Decimal

from lawfirm_os_intake.canonical_pricing import build_canonical_priced_work_plan
from lawfirm_os_intake.driver_taxonomy import (
    build_explicit_canonical_profile,
    line_driver_ids,
    load_driver_taxonomy,
)


def _price(repo_root, levels, line_id):
    profile = build_explicit_canonical_profile(levels, repo_root=repo_root, line_id=line_id)
    return build_canonical_priced_work_plan(profile, repo_root=repo_root)


def test_auto_line_prices_from_its_own_clcm_baseline(repo_root):
    plan = _price(
        repo_root,
        {
            "claimant_attorney_involvement": "active_litigation_counsel",
            "injury_severity_band": "severe",
            "trial_likelihood": "high",
        },
        "auto_bodily_injury_defense",
    )
    assert plan.clcm_case_type == "automobile_tort"
    assert plan.total_base_hours == "196"
    base = {row.phase: Decimal(row.base_hours) for row in plan.phase_rows}
    assert base["L300"] == Decimal("41.1600")  # 196 * 0.21
    assert base["L400"] == Decimal("92.1200")  # 196 * 0.47
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    # L400: 2.5 (attorney) * 2.15 (severe) * 3.0 (trial) = 16.125 -> capped at 10.
    assert mult["L400"] == Decimal("10.0")
    # L300: only the attorney-involvement driver reaches discovery.
    assert mult["L300"] == Decimal("2.5")


def test_auto_line_overrides_universal_trial_and_appeal(repo_root):
    # Contract v1.1 fix: the auto line's trial/appeal drivers replace the
    # universal trial_posture/appeal so trial can never be double-counted.
    ids = line_driver_ids(load_driver_taxonomy(repo_root), "auto_bodily_injury_defense")
    assert "trial_likelihood" in ids and "appeal_likelihood" in ids
    assert "trial_posture" not in ids and "appeal" not in ids


def test_premises_line_prices_from_its_own_clcm_baseline(repo_root):
    plan = _price(
        repo_root,
        {
            "injury_severity": "catastrophic",
            "liability_clarity": "heavily_disputed_comparative",
            "notice_complexity": "constructive_notice_dispute",
        },
        "general_premises_liability_defense",
    )
    assert plan.clcm_case_type == "premises_liability"
    assert plan.total_base_hours == "218"
    base = {row.phase: Decimal(row.base_hours) for row in plan.phase_rows}
    assert base["L100"] == Decimal("37.0600")  # 218 * 0.17
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    # L100: 4.5 (catastrophic) * 1.55 (liability) * 1.7 (notice) = 11.8575 -> cap.
    assert mult["L100"] == Decimal("10.0")


def test_epli_correlated_group_uses_capped_composite(repo_root):
    plan = _price(
        repo_root,
        {
            "plaintiff_structure": "class_collective",
            "admin_posture": "eeoc_systemic",
            "punitive_exposure": "systemic",
            "claim_type": "wage_hour",
        },
        "epli_employment_defense",
    )
    assert plan.clcm_case_type == "employment"
    assert plan.total_base_hours == "374"
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    # L100 carries all three group members (6.0, 4.5, 2.5) plus ungrouped
    # claim_type 1.65: composite = 6 * sqrt(4.5) * sqrt(2.5) * 1.65 ~ 33.2 -> cap.
    assert mult["L100"] == Decimal("10.0")
    # L400 carries only plaintiff_structure from the group: largest-in-full = 6.0.
    assert mult["L400"] == Decimal("6.0")


def test_epli_partial_group_is_not_capped(repo_root):
    plan = _price(
        repo_root,
        {"plaintiff_structure": "multi_2_9", "claim_type": "harassment"},
        "epli_employment_defense",
    )
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    # Single group member applies in full (1.9); claim_type 1.5 multiplies normally.
    assert mult["L100"] == Decimal("2.85")  # 1.9 * 1.5
    assert mult["L400"] == Decimal("1.9")


def test_medmal_pricing_unchanged_by_v11_contract(repo_root):
    plan = _price(
        repo_root,
        {
            "damages_severity": "serious",
            "case_stakes": "high",
            "party_count": "2_3",
            "causation_disputed": "disputed",
        },
        "medical_malpractice_defense",
    )
    assert plan.total_base_hours == "472"
    mult = {row.phase: Decimal(row.multiplier) for row in plan.phase_rows}
    # Same pinned values as DT2: the v1.1 restructure must not move med-mal.
    assert mult["L100"] == Decimal("2.325")
    assert mult["L300"] == Decimal("3.47375")
    base = {row.phase: Decimal(row.base_hours) for row in plan.phase_rows}
    assert base["L400"] == Decimal("202.9600")
