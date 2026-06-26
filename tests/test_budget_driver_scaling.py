"""Slice 2: driver-scaled budget hours/expenses, with exact back-compat when no drivers."""

from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.drivers import CaseDriverProfile, DriverValue
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight

MATTER_FAMILY = "medical_malpractice_defense"


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


def _scaling_profile():
    # A self-contained synthetic profile: one fixed task and one deposition-scaled task.
    return {
        "profile_id": "synthetic-scaling-test",
        "synthetic_hourly_rates": {"associate": 250, "senior_associate": 325},
        "budget_templates": {
            MATTER_FAMILY: {
                "template_id": "synthetic-scaling-test-v1",
                "contingency_percent": 0,
                "phases": [
                    {
                        "phase_id": "P300",
                        "phase_name": "Discovery",
                        "tasks": [
                            {
                                "task_id": "P310",
                                "task_name": "Written discovery",
                                "staffing_role": "associate",
                                "estimated_hours": 40,
                                "estimated_expenses": 100,
                            },
                            {
                                "task_id": "P320",
                                "task_name": "Depositions",
                                "staffing_role": "senior_associate",
                                "estimated_hours": 50,
                                "estimated_expenses": 200,
                                "scaling_driver": "num_depositions",
                                "hours_per_unit": 6,
                                "expense_per_unit": 600,
                            },
                        ],
                    }
                ],
            }
        },
    }


def _drivers(packet, confirmation, num_depositions, provenance="human_confirmed"):
    value = None if num_depositions is None else num_depositions
    prov = "unknown" if num_depositions is None else provenance
    return CaseDriverProfile(
        case_driver_profile_id="casedrivers-test",
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        matter_family=MATTER_FAMILY,
        policy_id="synthetic-budget-driver-policy",
        policy_version="0.1",
        drivers=[
            DriverValue(
                driver_id="num_depositions",
                driver_class="count",
                value=value,
                unit="depositions",
                provenance=prov,
                source_refs=["human-confirmation://test"] if prov != "unknown" else [],
            )
        ],
        count_driver_range_policy={"num_depositions": {"min": 3, "likely": 8, "max": 12}},
    )


def _line(budget, task_id):
    return next(line for line in budget.lines if line.task_id == task_id)


def test_scaled_task_uses_driver_count(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = _scaling_profile()
    budget = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, 8)
    )
    depo = _line(budget, "P320")
    assert depo.estimated_hours == 48.0  # 6 hours/unit * 8 depositions
    assert depo.estimated_expenses == 5000.0  # 200 base + 600/unit * 8
    assert "num_depositions" in (depo.calculation_formula or "")
    assert any("num_depositions=8" in note for note in depo.assumptions)
    # Non-scaled task is untouched.
    written = _line(budget, "P310")
    assert written.estimated_hours == 40.0
    assert written.estimated_expenses == 100.0


def test_more_depositions_means_more_hours(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = _scaling_profile()
    fewer = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, 4)
    )
    more = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, 10)
    )
    assert _line(fewer, "P320").estimated_hours == 24.0
    assert _line(more, "P320").estimated_hours == 60.0
    assert more.total_proposed_budget > fewer.total_proposed_budget


def test_unknown_driver_falls_back_to_template_hours(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = _scaling_profile()
    budget = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, None)
    )
    depo = _line(budget, "P320")
    assert depo.estimated_hours == 50.0  # template fallback, not invented
    assert depo.estimated_expenses == 200.0
    assert depo.estimated_hours_min == 18.0
    assert depo.estimated_hours_max == 72.0
    assert depo.estimated_expenses_min == 200.0
    assert depo.estimated_expenses_max == 7400.0


def test_unknown_driver_range_is_wider_than_confirmed_driver_range(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = _scaling_profile()
    confirmed = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, 8)
    )
    unknown = build_budget_proposal(
        packet, confirmation, profile, case_drivers=_drivers(packet, confirmation, None)
    )

    confirmed_depo = _line(confirmed, "P320")
    unknown_depo = _line(unknown, "P320")
    confirmed_width = confirmed_depo.estimated_hours_max - confirmed_depo.estimated_hours_min
    unknown_width = unknown_depo.estimated_hours_max - unknown_depo.estimated_hours_min

    assert confirmed_width == 0
    assert unknown_width > confirmed_width
    assert unknown.scenario_set is not None
    standard = next(
        scenario
        for scenario in unknown.scenario_set.scenarios
        if scenario.scenario_id == "standard"
    )
    assert standard.total_budget_max > standard.total_budget_min


def test_no_drivers_is_exact_back_compat(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = _scaling_profile()
    without = build_budget_proposal(packet, confirmation, profile)
    explicit_none = build_budget_proposal(packet, confirmation, profile, case_drivers=None)
    depo = _line(without, "P320")
    assert depo.estimated_hours == 50.0
    assert depo.estimated_expenses == 200.0
    assert depo.calculation_formula == "50.0 hours * 325.0 synthetic hourly rate"
    assert [line.model_dump() for line in without.lines] == [
        line.model_dump() for line in explicit_none.lines
    ]
