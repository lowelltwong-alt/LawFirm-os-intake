"""PR4: the demo budget is UTBMS-coded and reflects resolved case drivers."""

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run(tmp_path, repo_root):
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
    budget, _ = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget


def _line(budget, code):
    return next(line for line in budget.lines if line.external_code_candidate == code)


def test_demo_budget_uses_utbms_codes(tmp_path, repo_root):
    budget = _run(tmp_path, repo_root)
    codes = {line.external_code_candidate for line in budget.lines}
    assert {"L330", "L340", "L240", "L310"} <= codes
    assert "L450" not in codes
    assert budget.scenario_set is not None
    trial = next(
        scenario
        for scenario in budget.scenario_set.scenarios
        if scenario.scenario_id == "through_trial"
    )
    assert "L450" in trial.included_external_codes
    assert all(line.external_code_candidate.startswith("L") for line in budget.lines)
    assert budget.pricing_status == "priced"
    assert budget.total_proposed_budget is not None


def test_demo_budget_is_driver_scaled(tmp_path, repo_root):
    budget = _run(tmp_path, repo_root)
    # Policy default num_depositions = 8; family-default intensity normalizes to 1.0.
    depo = _line(budget, "L330")
    assert depo.estimated_hours == 64.0
    assert depo.estimated_expenses == 5600.0
    assert depo.estimated_expenses_min < depo.estimated_expenses
    assert depo.estimated_expenses_max > depo.estimated_expenses
    assert any("num_depositions" in note for note in depo.assumptions)
    # Pleading (L210) scales by human-confirmed represented defendants.
    assert _line(budget, "L210").estimated_hours == 16.0
    # Expert discovery (L340) scales by num_experts; default intensity is neutral.
    expert = _line(budget, "L340")
    assert expert.estimated_hours == 24.0
    assert expert.estimated_expenses == 30000.0


def test_subtotal_fees_match_lines(tmp_path, repo_root):
    budget = _run(tmp_path, repo_root)
    expected = round(
        sum(line.estimated_hours * line.hourly_rate for line in budget.lines if line.hourly_rate), 2
    )
    assert budget.subtotal_fees == expected
