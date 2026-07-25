"""Budget-driver-taxonomy@v1 adapter — intake ↔ substrate reconciliation.

The canonical driver taxonomy is a vendored, digest-pinned candidate contract
(config/budget-driver-taxonomy.v1.json, authored in the semantic-substrate repo).
Intake does not redefine drivers: its 5 legacy sizing drivers map onto the
canonical set, and every canonical driver the intake flow cannot elicit becomes an
explicit ``not_elicited`` assumption (neutral multiplier, rule-attributed), never a
silent default. Required-but-missing drivers raise the existing
``missing_required_budget_driver`` exception trigger. Candidate-only,
synthetic-only; dollars stay deterministic; no promotion.
"""

import pytest

from lawfirm_os_intake.driver_taxonomy import (
    EXPECTED_CONTRACT_DIGEST,
    build_canonical_driver_profile,
    line_driver_ids,
    load_driver_taxonomy,
)
from lawfirm_os_intake.models import CanonicalDriverAssignment, CanonicalDriverProfile

LEGACY = {
    "party_count": 2,
    "injury_severity": "surgical",
    "liability_clarity": "disputed",
    "exposure_band": "high",
    "venue": "state_default",
}


def test_contract_loads_and_digest_is_pinned(repo_root):
    contract = load_driver_taxonomy(repo_root)
    assert contract["contract_id"] == "budget-driver-taxonomy"
    assert contract["status"] == "candidate"
    assert contract["calibrated"] is False
    assert contract["reference_class_only"] is True
    assert EXPECTED_CONTRACT_DIGEST.startswith("4fd1f971")


def test_tampered_contract_is_rejected(repo_root, tmp_path):
    original = (repo_root / "config/budget-driver-taxonomy.v1.json").read_text(encoding="utf-8")
    tampered = tmp_path / "budget-driver-taxonomy.v1.json"
    tampered.write_text(original.replace('"point": 2.6', '"point": 9.9'), encoding="utf-8")
    with pytest.raises(ValueError):
        load_driver_taxonomy(repo_root, contract_path=tampered)


def test_legacy_mapping_produces_full_profile(repo_root):
    profile = build_canonical_driver_profile(LEGACY, repo_root=repo_root)
    assert isinstance(profile, CanonicalDriverProfile)
    assert profile.line_id == "medical_malpractice_defense"
    assert profile.contract_digest == EXPECTED_CONTRACT_DIGEST

    by_id = {a.driver_id: a for a in profile.assignments}
    # Every canonical driver of the line is assigned exactly once (no silent gaps).
    assert set(by_id) == set(
        line_driver_ids(load_driver_taxonomy(repo_root), "medical_malpractice_defense")
    )

    # Legacy values landed on the right canonical drivers/levels.
    assert by_id["damages_severity"].level == "serious"
    assert by_id["damages_severity"].status == "elicited"
    assert by_id["case_stakes"].level == "high"
    assert by_id["party_count"].level == "2_3"
    assert by_id["causation_disputed"].level == "disputed"
    # Venue is a recorded posture passthrough, not a silent drop.
    assert profile.posture_flags.get("venue") == "state_default"


def test_not_elicited_drivers_are_explicit_assumptions(repo_root):
    profile = build_canonical_driver_profile(LEGACY, repo_root=repo_root)
    not_elicited = [a for a in profile.assignments if a.status == "not_elicited"]
    assert not_elicited, "intake cannot elicit the full canonical set yet"
    for assignment in not_elicited:
        assert assignment.level is None
        assert assignment.assumption_note  # never a silent default
    assert sorted(profile.not_elicited_driver_ids) == sorted(a.driver_id for a in not_elicited)


def test_required_missing_drivers_raise_exception_candidate(repo_root):
    profile = build_canonical_driver_profile(LEGACY, repo_root=repo_root)
    # implicated_specialties and trial_likelihood are required by the med-mal line
    # and not elicitable from the legacy 5 -> typed exception, not auto-block.
    assert "implicated_specialties" in profile.required_missing_driver_ids
    assert "trial_likelihood" in profile.required_missing_driver_ids
    assert "missing_required_budget_driver" in profile.exception_candidates


def test_unknown_legacy_key_is_rejected(repo_root):
    with pytest.raises(ValueError):
        build_canonical_driver_profile({**LEGACY, "mystery_driver": "x"}, repo_root=repo_root)


def test_unknown_legacy_level_is_rejected(repo_root):
    with pytest.raises(ValueError):
        build_canonical_driver_profile(
            {**LEGACY, "injury_severity": "apocalyptic"}, repo_root=repo_root
        )


def test_profile_fails_closed_on_silent_default(repo_root):
    profile = build_canonical_driver_profile(LEGACY, repo_root=repo_root)
    dumped = profile.model_dump()
    for assignment in dumped["assignments"]:
        if assignment["status"] == "not_elicited":
            assignment["assumption_note"] = ""
            break
    with pytest.raises(ValueError):
        CanonicalDriverProfile.model_validate(dumped)


def test_assignment_model_fail_closed():
    # An elicited assignment must carry a level.
    with pytest.raises(ValueError):
        CanonicalDriverAssignment(
            driver_id="damages_severity",
            layer="line",
            level=None,
            status="elicited",
            source="legacy_mapping",
        )
    # A not_elicited assignment cannot carry a level.
    with pytest.raises(ValueError):
        CanonicalDriverAssignment(
            driver_id="damages_severity",
            layer="line",
            level="minor",
            status="not_elicited",
            assumption_note="x",
        )


def test_conformance_gate_passes_on_repo(repo_root):
    from scripts.validate_driver_taxonomy_conformance import run_conformance_checks

    failures = run_conformance_checks(repo_root)
    assert failures == []


def test_conformance_gate_catches_unmapped_sizing_driver(repo_root):
    from scripts.validate_driver_taxonomy_conformance import run_conformance_checks

    contract = load_driver_taxonomy(repo_root)
    del contract["legacy_intake_mapping"]["keys"]["venue"]
    failures = run_conformance_checks(repo_root, contract_override=contract)
    assert any("venue" in failure for failure in failures)
