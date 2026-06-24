from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.drivers import (
    CaseDriverProfile,
    DriverValue,
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
