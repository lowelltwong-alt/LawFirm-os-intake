from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmed_packet(tmp_path, repo_root):
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
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    return packet, run_dir, confirmation_path


def _budget(tmp_path, repo_root, profile_name="insurance-defense.yaml"):
    _packet, run_dir, confirmation_path = _confirmed_packet(tmp_path, repo_root)
    budget, _ = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / f"context/synthetic-profiles/{profile_name}",
        tmp_path / "budget",
    )
    return budget


def _scenario(budget, scenario_id):
    assert budget.scenario_set is not None
    return next(
        scenario
        for scenario in budget.scenario_set.scenarios
        if scenario.scenario_id == scenario_id
    )


def test_budget_emits_monotonic_scenario_set_and_selects_standard(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)

    assert budget.scenario_name == "standard"
    assert budget.scenario_set is not None
    assert [scenario.scenario_id for scenario in budget.scenario_set.scenarios] == [
        "early_resolution",
        "standard",
        "through_trial",
    ]
    assert budget.scenario_set.selected_scenario_id == "standard"
    assert budget.scenario_set.monotonic_total_order is True
    assert budget.scenario_set.not_authorized_for_client_submission is True
    assert budget.scenario_set.external_writes_performed is False

    early = _scenario(budget, "early_resolution")
    standard = _scenario(budget, "standard")
    trial = _scenario(budget, "through_trial")
    assert early.resolution_phase == "L200"
    assert standard.resolution_phase == "L300"
    assert trial.resolution_phase == "L400"
    assert (
        early.total_proposed_budget <= standard.total_proposed_budget <= trial.total_proposed_budget
    )


def test_legacy_budget_surface_maps_to_standard_scenario(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    standard = _scenario(budget, "standard")
    trial = _scenario(budget, "through_trial")

    assert budget.total_proposed_budget == standard.total_proposed_budget
    assert budget.subtotal_fees == standard.subtotal_fees
    assert budget.subtotal_expenses == standard.subtotal_expenses
    assert budget.calculation_report is not None
    assert budget.calculation_report.total_hours == standard.total_hours
    assert {line.phase_id for line in budget.lines} == set(standard.included_phase_ids)
    assert "L450" not in {line.external_code_candidate for line in budget.lines}
    assert "L450" in trial.included_external_codes


def test_hours_only_scenarios_are_monotonic_by_hours(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root, "insurance-defense-hours-only.yaml")
    early = _scenario(budget, "early_resolution")
    standard = _scenario(budget, "standard")
    trial = _scenario(budget, "through_trial")

    assert budget.pricing_status == "hours_only"
    assert budget.total_proposed_budget is None
    assert budget.scenario_set is not None
    assert budget.scenario_set.total_order_basis == "total_hours"
    assert budget.scenario_set.monotonic_total_order is True
    assert early.total_proposed_budget is None
    assert standard.total_proposed_budget is None
    assert trial.total_proposed_budget is None
    assert early.total_hours <= standard.total_hours <= trial.total_hours


def test_policy_scenario_cutoffs_match_utbms_profile(repo_root):
    policy = load_profile(repo_root / "config/budget-driver-policy.yaml")
    assert [scenario["resolution_phase"] for scenario in policy["scenarios"]] == [
        "L200",
        "L300",
        "L400",
    ]
