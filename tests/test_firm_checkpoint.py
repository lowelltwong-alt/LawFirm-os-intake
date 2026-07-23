"""CW5 — firm checkpoint packet (three synthetic cases end-to-end, placeholder dispositions)."""

import pytest

from lawfirm_os_intake.firm_checkpoint import build_firm_checkpoint_packet
from lawfirm_os_intake.models import FirmCheckpointPacket


def _packet(repo_root):
    return build_firm_checkpoint_packet(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")


def test_packet_has_three_cases_and_requires_firm_dispositions(repo_root):
    packet = _packet(repo_root)
    assert isinstance(packet, FirmCheckpointPacket)
    assert len(packet.cases) == 3
    assert packet.requires_firm_dispositions is True
    assert packet.real_firm_validation_status == "open_pending_firm_review"
    # Placeholder dispositions are explicitly labeled and never real firm validation.
    assert packet.synthetic_placeholder_dispositions_used is True
    for case in packet.cases:
        assert case.disposition.is_synthetic_placeholder is True
        assert case.disposition.disposition == "pending_firm_review"


def test_slip_and_fall_trips_proportionality_and_recommends_settle(repo_root):
    case = next(c for c in _packet(repo_root).cases if c.case_id == "slip-and-fall")
    assert case.trips_proportionality_gate is True
    assert case.case_sizing_report.proportionality.status == "blocked_disproportionate_budget"
    assert case.recommended_posture == "settle_now"
    assert case.routed_decision == "route"
    assert case.routed_family == "general_liability_defense"


def test_epli_case_trips_expert_preapproval_within_band(repo_root):
    case = next(c for c in _packet(repo_root).cases if c.case_id == "epli")
    assert case.expected_preapproval_trip is True
    assert case.trips_proportionality_gate is False
    assert case.routed_family == "discrimination_harassment"


def test_labor_employment_case_present_and_routed(repo_root):
    case = next(c for c in _packet(repo_root).cases if c.case_id == "wage-hour")
    assert case.matter_family == "wage_hour_flsa_state"
    assert case.routed_decision == "route"
    assert case.trips_proportionality_gate is False


def test_packet_is_deterministic(repo_root):
    first = _packet(repo_root)
    second = _packet(repo_root)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_packet_case_validator_rejects_inconsistent_proportionality(repo_root):
    packet = _packet(repo_root)
    dumped = packet.model_dump()
    # Flip the proportionality trip flag away from the sizing report -> fail-closed.
    dumped["cases"][0]["trips_proportionality_gate"] = not dumped["cases"][0][
        "trips_proportionality_gate"
    ]
    with pytest.raises(ValueError):
        FirmCheckpointPacket.model_validate(dumped)
