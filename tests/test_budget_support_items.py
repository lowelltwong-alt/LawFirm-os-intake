from copy import deepcopy

from lawfirm_os_intake.budget import build_budget_proposal
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def _support_texts(budget, item_type):
    return {item.text for item in budget.budget_support_items if item.item_type == item_type}


def test_budget_assumptions_exclusions_and_unknowns_are_source_bound(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    budget = build_budget_proposal(packet, _confirmation(packet, repo_root), profile)

    assert budget.budget_support_items
    assert all(item.evidence_refs or item.structured_ref for item in budget.budget_support_items)
    assert set(budget.assumptions).issubset(_support_texts(budget, "assumption"))
    assert set(budget.exclusions).issubset(_support_texts(budget, "exclusion"))
    assert set(budget.unknowns).issubset(_support_texts(budget, "unknown"))
    assert any(
        item.source_kind == "observed_evidence" and item.evidence_refs
        for item in budget.budget_support_items
    )
    assert any(
        item.source_kind == "human_confirmation" and item.structured_ref
        for item in budget.budget_support_items
    )
    assert any(
        item.source_kind == "synthetic_practice_profile" and item.structured_ref
        for item in budget.budget_support_items
    )
    assert any(
        item.source_kind == "workflow_policy" and item.structured_ref
        for item in budget.budget_support_items
    )


def test_missing_budget_template_records_supported_unknown(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    confirmation = _confirmation(packet, repo_root)
    raw = confirmation.model_dump(mode="json")
    raw["confirmed_matter_family"] = "unsupported_synthetic_matter"
    unsupported = HumanConfirmation.model_validate(raw)
    no_template_profile = deepcopy(profile)
    no_template_profile["budget_templates"] = {}

    budget = build_budget_proposal(packet, unsupported, no_template_profile)

    assert budget.pricing_status == "insufficient_information"
    assert budget.unknowns
    assert set(budget.unknowns).issubset(_support_texts(budget, "unknown"))
    assert all(item.evidence_refs or item.structured_ref for item in budget.budget_support_items)
    assert any(item.source_kind == "missing_template" for item in budget.budget_support_items)
