from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def test_missing_rates_produces_hours_only_not_invented_money(tmp_path, repo_root):
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
    profile["synthetic_hourly_rates"] = {}
    budget = build_budget_proposal(packet, confirmation, profile)
    assert budget.pricing_status == "hours_only"
    assert budget.total_proposed_budget is None
    assert all(line.hourly_rate is None for line in budget.lines)
