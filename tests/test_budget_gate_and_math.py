from copy import deepcopy

import pytest

from lawfirm_os_intake.budget import build_budget_proposal
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
    confirmation = HumanConfirmation.model_validate(raw)
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    budget = build_budget_proposal(packet, confirmation, profile)
    assert budget.pricing_status == "priced"
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
