from copy import deepcopy

from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.drivers import (
    CaseDriverProfile,
    DriverValue,
    build_effective_intensity_multiplier_policy,
    load_driver_policy,
    resolve_case_drivers,
)
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _packet_confirmation_profile_policy(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    return packet, run_dir, confirmation, profile, policy


def _run_budget(tmp_path, repo_root):
    packet, run_dir, confirmation, _profile, _policy = _packet_confirmation_profile_policy(
        tmp_path,
        repo_root,
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, _ = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget


def _replace_driver(
    drivers: CaseDriverProfile,
    driver_id: str,
    value: str,
    provenance: str = "human_confirmed",
) -> CaseDriverProfile:
    replacement = DriverValue(
        driver_id=driver_id,
        driver_class=next(
            driver.driver_class for driver in drivers.drivers if driver.driver_id == driver_id
        ),
        value=value,
        unit=next(driver.unit for driver in drivers.drivers if driver.driver_id == driver_id),
        provenance=provenance,  # type: ignore[arg-type]
        source_refs=["human-confirmation://synthetic-driver-test"],
        note="test override",
    )
    updated = [
        replacement if driver.driver_id == driver_id else driver for driver in drivers.drivers
    ]
    return drivers.model_copy(
        update={
            "drivers": updated,
            "observed_or_confirmed_driver_ids": sorted(
                {
                    *drivers.observed_or_confirmed_driver_ids,
                    driver_id,
                }
            ),
            "default_driver_ids": [
                item for item in drivers.default_driver_ids if item != driver_id
            ],
            "unknown_driver_ids": [
                item for item in drivers.unknown_driver_ids if item != driver_id
            ],
        }
    )


def test_profile_default_intensity_effects_are_visible_not_observed(tmp_path, repo_root):
    budget = _run_budget(tmp_path, repo_root)

    effects_by_driver = {effect.driver_id: effect for effect in budget.driver_effects}
    for driver_id in ("severity_tier", "liability_dispute", "venue_difficulty"):
        effect = effects_by_driver[driver_id]
        assert effect.effect_type == "intensity_multiplier"
        assert effect.provenance == "profile_default"
        assert effect.applied is True
        assert effect.default_used_as_observed_fact is False
        assert "effective intensity" in effect.note
        assert "normalization raw" in effect.note
        assert "not observed source evidence" in effect.note

    coverage_effect = effects_by_driver["coverage_posture"]
    assert coverage_effect.effect_type == "unknown_driver"
    assert coverage_effect.applied is False
    assert any("coverage_posture is unknown" in unknown for unknown in budget.unknowns)
    assert any(item.source_kind == "budget_driver_policy" for item in budget.budget_support_items)


def test_human_confirmed_higher_severity_increases_budget(tmp_path, repo_root):
    packet, _run_dir, confirmation, profile, policy = _packet_confirmation_profile_policy(
        tmp_path,
        repo_root,
    )
    resolved = resolve_case_drivers(packet, confirmation, profile, policy)

    soft = build_budget_proposal(
        packet,
        confirmation,
        profile,
        case_drivers=_replace_driver(resolved, "severity_tier", "soft_tissue"),
    )
    catastrophic = build_budget_proposal(
        packet,
        confirmation,
        profile,
        case_drivers=_replace_driver(resolved, "severity_tier", "catastrophic_or_death"),
    )

    assert soft.total_proposed_budget is not None
    assert catastrophic.total_proposed_budget is not None
    assert catastrophic.total_proposed_budget > soft.total_proposed_budget
    catastrophic_severity = next(
        effect for effect in catastrophic.driver_effects if effect.driver_id == "severity_tier"
    )
    assert catastrophic_severity.provenance == "human_confirmed"
    assert "not observed source evidence" not in catastrophic_severity.note


def test_guideline_flags_do_not_rewrite_budget_rates(tmp_path, repo_root):
    budget = _run_budget(tmp_path, repo_root)

    partner_lines = [line for line in budget.lines if line.staffing_role == "partner"]
    assert partner_lines
    assert {line.hourly_rate for line in partner_lines} == {450.0}
    partner_cap = next(
        flag for flag in budget.guideline_flags if flag.constraint_id == "role_rate_cap:partner"
    )
    assert partner_cap.status == "flagged_for_human_review"
    assert partner_cap.current_value == 450.0
    assert partner_cap.threshold_value == 425.0
    assert partner_cap.rewrites_budget is False
    assert any(partner_cap.note in unknown for unknown in budget.unknowns)


def test_raw_intensity_normalization_preserves_current_multipliers(tmp_path, repo_root):
    packet, _run_dir, confirmation, profile, policy = _packet_confirmation_profile_policy(
        tmp_path,
        repo_root,
    )
    resolved = resolve_case_drivers(packet, confirmation, profile, policy)

    assert resolved.intensity_normalization_mode == "raw"
    assert resolved.intensity_baseline_by_driver == {
        "liability_dispute": "disputed",
        "severity_tier": "significant",
        "venue_difficulty": "neutral",
    }
    severity = resolved.effective_intensity_multiplier_policy["effects"]["severity_tier"]
    liability = resolved.effective_intensity_multiplier_policy["effects"]["liability_dispute"]
    assert severity["significant"]["effective_multiplier"] == 1.08
    assert liability["disputed"]["effective_multiplier"] == 1.05


def test_baseline_relative_intensity_default_tiers_are_neutral(tmp_path, repo_root):
    packet, _run_dir, confirmation, profile, policy = _packet_confirmation_profile_policy(
        tmp_path,
        repo_root,
    )
    policy = deepcopy(policy)
    policy["intensity_multiplier_policy"]["normalization"] = "baseline_relative"
    resolved = resolve_case_drivers(packet, confirmation, profile, policy)
    effects = resolved.effective_intensity_multiplier_policy["effects"]

    assert resolved.intensity_normalization_mode == "baseline_relative"
    assert effects["severity_tier"]["significant"]["effective_multipliers_by_phase"] == {
        "L300": 1.0,
        "L400": 1.0,
    }
    assert effects["liability_dispute"]["disputed"]["effective_multipliers_by_phase"] == {
        "L200": 1.0,
        "L300": 1.0,
    }
    assert effects["venue_difficulty"]["neutral"]["effective_multipliers_by_phase"] == {
        "L200": 1.0,
        "L300": 1.0,
        "L400": 1.0,
    }


def test_baseline_relative_intensity_uses_phase_specific_raw_ratios(repo_root):
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    policy["intensity_multiplier_policy"]["normalization"] = "baseline_relative"
    effective_policy, baseline_by_driver = build_effective_intensity_multiplier_policy(
        policy["intensity_multiplier_policy"],
        matter_family="medical_malpractice_defense",
        profile=profile,
        family_defaults=policy["matter_family_defaults"]["medical_malpractice_defense"],
    )
    effects = effective_policy["effects"]

    assert baseline_by_driver["severity_tier"] == "significant"
    assert effects["severity_tier"]["catastrophic_or_death"]["effective_multipliers_by_phase"] == {
        "L300": 1.1296,
        "L400": 1.1296,
    }
    # Baseline disputed liability does not apply to L400, so hotly contested keeps raw 1.18 there.
    assert effects["liability_dispute"]["hotly_contested"]["effective_multipliers_by_phase"] == {
        "L200": 1.1238,
        "L300": 1.1238,
        "L400": 1.18,
    }


def test_template_declared_baseline_overrides_family_default(repo_root):
    profile = deepcopy(
        load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    )
    profile["budget_templates"]["medical_malpractice_defense"]["baseline_intensity"] = {
        "severity_tier": "soft_tissue",
        "liability_dispute": "disputed",
        "venue_difficulty": "neutral",
    }
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    policy["intensity_multiplier_policy"]["normalization"] = "baseline_relative"

    effective_policy, baseline_by_driver = build_effective_intensity_multiplier_policy(
        policy["intensity_multiplier_policy"],
        matter_family="medical_malpractice_defense",
        profile=profile,
        family_defaults=policy["matter_family_defaults"]["medical_malpractice_defense"],
    )
    severity = effective_policy["effects"]["severity_tier"]

    assert baseline_by_driver["severity_tier"] == "soft_tissue"
    assert severity["soft_tissue"]["effective_multipliers_by_phase"] == {
        "L300": 1.0,
        "L400": 1.0,
    }
    assert severity["significant"]["effective_multipliers_by_phase"] == {
        "L300": 1.1368,
        "L400": 1.1368,
    }
