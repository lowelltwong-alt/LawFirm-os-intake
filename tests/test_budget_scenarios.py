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


def _replace_driver(
    drivers: CaseDriverProfile,
    driver_id: str,
    value: str,
    provenance: str = "human_confirmed",
) -> CaseDriverProfile:
    current = next(driver for driver in drivers.drivers if driver.driver_id == driver_id)
    replacement = DriverValue(
        driver_id=driver_id,
        driver_class=current.driver_class,
        value=value,
        unit=current.unit,
        provenance=provenance,  # type: ignore[arg-type]
        source_refs=["human-confirmation://synthetic-resolution-path-test"],
        note="test override",
    )
    return drivers.model_copy(
        update={
            "drivers": [
                replacement if driver.driver_id == driver_id else driver
                for driver in drivers.drivers
            ],
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
    assert budget.scenario_set.selected_scenario_basis == "default_standard"
    assert budget.scenario_set.standard_scenario_id == "standard"
    assert budget.scenario_set.expected_total_probability_sum == 1
    assert budget.scenario_set.expected_total is not None
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
    assert [early.probability, standard.probability, trial.probability] == [0.25, 0.5, 0.25]


def test_confirmed_resolution_path_selects_through_trial_and_expected_value(
    tmp_path,
    repo_root,
):
    packet, _run_dir, confirmation_path = _confirmed_packet(tmp_path, repo_root)
    confirmation = HumanConfirmation.model_validate(load_json(confirmation_path))
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    policy = load_driver_policy(repo_root / "config/budget-driver-policy.yaml")
    resolved = resolve_case_drivers(packet, confirmation, profile, policy)
    confirmed_trial_path = _replace_driver(resolved, "resolution_path", "through_trial")

    budget = build_budget_proposal(
        packet,
        confirmation,
        profile,
        case_drivers=confirmed_trial_path,
    )

    assert budget.scenario_name == "through_trial"
    assert budget.scenario_set is not None
    assert budget.scenario_set.selected_scenario_id == "through_trial"
    assert budget.scenario_set.standard_scenario_id == "standard"
    assert budget.scenario_set.selected_scenario_basis == "confirmed_resolution_path"
    assert budget.scenario_set.expected_total_probability_sum == 1
    assert budget.scenario_set.expected_total is not None

    standard = _scenario(budget, "standard")
    trial = _scenario(budget, "through_trial")
    assert budget.total_proposed_budget == trial.total_proposed_budget
    assert standard.total_proposed_budget < budget.total_proposed_budget
    assert "L450" in {line.external_code_candidate for line in budget.lines}

    trial_day_tasks = {
        tuple(effect.task_ids)
        for effect in budget.driver_effects
        if effect.driver_id == "trial_days" and effect.effect_type == "count_scaling"
    }
    assert ("L440",) in trial_day_tasks
    assert ("L450",) in trial_day_tasks


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
