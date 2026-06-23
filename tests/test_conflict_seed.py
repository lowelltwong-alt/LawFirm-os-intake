import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import build_conflict_seed, run_preflight


def test_conflict_seed_has_no_clearance_conclusion(tmp_path, repo_root):
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
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    seed = build_conflict_seed(packet, confirmation)
    assert seed.conclusion == "no_conflict_conclusion"
    assert "Harbor Point Insurance" in seed.instructing_sources
    assert "Dr. Maya Chen" in seed.prospective_represented_clients
    assert seed.normalized_search_terms
    assert all(term.evidence_refs for term in seed.normalized_search_terms)
    assert all(
        ref.start_offset <= ref.end_offset
        for term in seed.normalized_search_terms
        for ref in term.evidence_refs
    )


def test_conflict_seed_fails_closed_without_confirmed_party_evidence(tmp_path, repo_root):
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
    confirmation = HumanConfirmation.model_validate(raw)

    with pytest.raises(ValueError, match="lacks source-bound evidence refs"):
        build_conflict_seed(packet, confirmation)
