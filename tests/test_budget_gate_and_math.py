from copy import deepcopy

import pytest

from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def test_budget_requires_human_confirmation_and_calculates(tmp_path, repo_root):
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
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    budget = build_budget_proposal(packet, confirmation, profile)
    assert budget.pricing_status == "priced"
    confirmed_matter_candidate = next(
        candidate
        for candidate in packet.matter_family_candidates
        if candidate.label == confirmation.confirmed_matter_family
    )
    assert confirmed_matter_candidate.source_evidence_status == "observed_support"
    assert all(line.evidence_refs == [] for line in budget.lines)
    assert all(line.estimate_basis_refs for line in budget.lines)
    assert any(
        item.source_kind == "observed_evidence"
        and item.evidence_refs == confirmed_matter_candidate.observed_evidence_refs[:3]
        for item in budget.budget_support_items
    )
    expected_fees = round(
        sum(line.estimated_hours * line.hourly_rate for line in budget.lines if line.hourly_rate), 2
    )
    assert budget.subtotal_fees == expected_fees
    assert budget.total_proposed_budget is not None
    assert budget.not_authorized_for_client_submission is True

    not_confirmed = deepcopy(raw)
    not_confirmed["status"] = "needs_more_information"
    with pytest.raises(ValueError):
        build_budget_proposal(packet, HumanConfirmation.model_validate(not_confirmed), profile)
