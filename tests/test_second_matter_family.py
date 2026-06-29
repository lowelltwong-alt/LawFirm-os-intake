from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.drivers import load_driver_policy, resolve_case_drivers
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


AUTO_FIXTURE = "examples/synthetic/inbound/carrier-assignment-auto-bi.json"
AUTO_CONFIRMATION = (
    "examples/synthetic/confirmations/carrier-assignment-auto-bi.confirmation-template.json"
)
PROFILE = "context/synthetic-profiles/insurance-defense.yaml"


def _auto_packet_and_confirmation(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / AUTO_FIXTURE,
        repo_root / PROFILE,
        tmp_path / "preflight",
    )
    raw = load_json(repo_root / AUTO_CONFIRMATION)
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    return packet, run_dir, confirmation


def test_auto_bi_preflight_ranks_second_matter_family(tmp_path, repo_root):
    packet, _run_dir, confirmation = _auto_packet_and_confirmation(tmp_path, repo_root)

    assert packet.matter_family_candidates[0].label == "auto_liability_defense"
    assert packet.matter_family_candidates[0].source_evidence_status == "observed_support"
    assert confirmation.confirmed_matter_family == "auto_liability_defense"
    assert all(party.evidence_refs for party in confirmation.confirmed_parties)
    assert confirmation.decision_evidence_refs


def test_auto_bi_budget_uses_auto_template_and_driver_defaults(tmp_path, repo_root):
    packet, run_dir, confirmation = _auto_packet_and_confirmation(tmp_path, repo_root)
    profile = load_profile(repo_root / PROFILE)
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    drivers = resolve_case_drivers(packet, confirmation, profile, policy)

    assert drivers.matter_family == "auto_liability_defense"
    defaults = {driver.driver_id: driver.value for driver in drivers.drivers}
    assert defaults["num_depositions"] == 5
    assert defaults["num_experts"] == 2
    assert defaults["trial_days"] == 4
    assert "auto_liability_defense" in policy["matter_family_defaults"]

    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / PROFILE,
        tmp_path / "budget",
    )

    assert budget.matter_family == "auto_liability_defense"
    assert budget.pricing_status == "priced"
    assert budget.total_proposed_budget is not None
    assert budget.scenario_set is not None
    assert budget.scenario_name == "standard"
    codes = {line.external_code_candidate for line in budget.lines}
    assert {"L110", "L210", "L310", "L330", "L340"} <= codes
    assert "L450" not in codes
    trial = next(
        scenario
        for scenario in budget.scenario_set.scenarios
        if scenario.scenario_id == "through_trial"
    )
    assert "L450" in trial.included_external_codes
    assert any(effect.driver_id == "num_depositions" for effect in budget.driver_effects)
    assert any(flag.constraint_id == "total_budget_cap" for flag in budget.guideline_flags)
    assert budget.not_authorized_for_client_submission is True
    assert (budget_dir / "matter_opening_review_package.md").exists()
