"""Slice 1: case-driver capture with provenance, not yet applied to budget math."""

from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.drivers import (
    CaseDriverProfile,
    load_driver_policy,
    resolve_case_drivers,
)
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def _packet_and_confirmation(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return packet, HumanConfirmation.model_validate(raw)


def _resolve(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    return resolve_case_drivers(packet, confirmation, profile, policy)


def test_driver_resolution_has_provenance_spectrum(tmp_path, repo_root):
    drivers_profile = _resolve(tmp_path, repo_root)
    assert isinstance(drivers_profile, CaseDriverProfile)
    assert drivers_profile.matter_family == "medical_malpractice_defense"
    assert drivers_profile.status == "candidate"
    # Slice 1 records drivers but must not yet feed budget math.
    assert drivers_profile.not_applied_to_math is True

    provenances = {driver.driver_id: driver.provenance for driver in drivers_profile.drivers}
    assert "profile_default" in provenances.values()
    assert "unknown" in provenances.values()
    assert provenances.get("num_represented_defendants") == "human_confirmed"
    assert provenances.get("num_adverse_parties") == "human_confirmed"


def test_confirmed_party_counts_match_confirmation(tmp_path, repo_root):
    drivers_profile = _resolve(tmp_path, repo_root)
    by_id = {driver.driver_id: driver for driver in drivers_profile.drivers}
    # Demo confirmation: Dr. Maya Chen + Valley Medical Center represented; John Smith adverse.
    assert by_id["num_represented_defendants"].value == 2
    assert by_id["num_adverse_parties"].value == 1


def test_no_value_is_labeled_observed_without_a_source_ref(tmp_path, repo_root):
    drivers_profile = _resolve(tmp_path, repo_root)
    for driver in drivers_profile.drivers:
        if driver.provenance in ("observed_support", "human_confirmed"):
            assert driver.source_refs, f"{driver.driver_id} claims {driver.provenance} with no ref"
        if driver.provenance == "unknown":
            assert driver.value is None
        if driver.provenance == "profile_default":
            assert driver.value is not None


def test_unknown_drivers_are_listed_and_include_coverage(tmp_path, repo_root):
    drivers_profile = _resolve(tmp_path, repo_root)
    listed = set(drivers_profile.unknown_driver_ids)
    from_drivers = {
        driver.driver_id for driver in drivers_profile.drivers if driver.provenance == "unknown"
    }
    assert listed == from_drivers
    assert "coverage_posture" in listed


def test_resolution_is_deterministic(tmp_path, repo_root):
    first = _resolve(tmp_path, repo_root)
    second = _resolve(tmp_path, repo_root)
    # Ignore the random profile id; compare resolved driver content.
    assert [driver.model_dump() for driver in first.drivers] == [
        driver.model_dump() for driver in second.drivers
    ]
