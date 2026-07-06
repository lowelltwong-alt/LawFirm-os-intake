from copy import deepcopy

from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.rates import load_rate_card, resolve_role_rates
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def _packet_and_confirmation(tmp_path, repo_root):
    packet, _preflight_dir = run_preflight(
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
        packet,
        HumanConfirmation.model_validate(raw),
    )
    return packet, confirmation


def test_named_timekeeper_override_takes_precedence_for_tagged_task(tmp_path, repo_root):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = deepcopy(
        load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    )
    task = profile["budget_templates"]["medical_malpractice_defense"]["phases"][0]["tasks"][2]
    assert task["task_id"] == "L130"
    task["timekeeper_id"] = "synthetic-tk-harbor-partner-nv"
    rate_resolution = resolve_role_rates(
        profile=profile,
        confirmation=confirmation,
        rate_card=load_rate_card(repo_root / "config/synthetic-carrier-rate-card.yaml"),
    )

    budget = build_budget_proposal(
        packet,
        confirmation,
        profile,
        rate_resolution=rate_resolution,
    )

    named_line = next(line for line in budget.lines if line.task_id == "L130")
    ordinary_partner_line = next(line for line in budget.lines if line.task_id == "L240")

    assert named_line.timekeeper_id == "synthetic-tk-harbor-partner-nv"
    assert named_line.hourly_rate == 430.0
    assert named_line.rate_source == "synthetic_named_timekeeper_override"
    assert named_line.estimated_fees == round(named_line.estimated_hours * 430.0, 2)
    assert "synthetic named timekeeper rate" in named_line.calculation_formula
    assert any("Named synthetic timekeeper" in note for note in named_line.assumptions)

    assert ordinary_partner_line.timekeeper_id is None
    assert ordinary_partner_line.hourly_rate == 450.0
    assert ordinary_partner_line.rate_source == "synthetic_profile"
    assert budget.calculation_report is not None
    assert "synthetic_named_timekeeper_override" in budget.calculation_report.rate_sources
    assert budget.not_authorized_for_client_submission is True


def test_named_timekeeper_title_mismatch_forces_review_and_hours_only(
    tmp_path,
    repo_root,
):
    packet, confirmation = _packet_and_confirmation(tmp_path, repo_root)
    profile = deepcopy(
        load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    )
    task = profile["budget_templates"]["medical_malpractice_defense"]["phases"][0]["tasks"][0]
    assert task["task_id"] == "L110"
    assert task["staffing_role"] == "associate"
    task["timekeeper_id"] = "synthetic-tk-harbor-partner-nv"
    rate_resolution = resolve_role_rates(
        profile=profile,
        confirmation=confirmation,
        rate_card=load_rate_card(repo_root / "config/synthetic-carrier-rate-card.yaml"),
    )

    budget = build_budget_proposal(
        packet,
        confirmation,
        profile,
        rate_resolution=rate_resolution,
    )

    mismatched_line = next(line for line in budget.lines if line.task_id == "L110")
    assert mismatched_line.timekeeper_id == "synthetic-tk-harbor-partner-nv"
    assert mismatched_line.hourly_rate is None
    assert mismatched_line.rate_source == "absent"
    assert budget.pricing_status == "hours_only"
    assert budget.subtotal_fees is None
    assert budget.total_proposed_budget is None
    assert (
        "named_timekeeper_title_mismatch_for_rates"
        in budget.display_banner["rate_review_issue_codes"]
    )
    assert any("approved as partner" in unknown for unknown in budget.unknowns)
