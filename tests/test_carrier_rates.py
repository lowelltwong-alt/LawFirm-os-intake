"""Slice A: carrier x state x title rate resolution from a synthetic rate card."""

from copy import deepcopy

import pytest
import yaml

from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.rates import load_rate_card, resolve_role_rates

TEMPLATE_ROLES = {"partner", "senior_associate", "associate", "paralegal"}


def _profile(repo_root):
    return load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")


def _card(repo_root):
    return load_rate_card(repo_root / "config/synthetic-carrier-rate-card.yaml")


def _confirmation(carrier_name: str, jurisdiction: str) -> HumanConfirmation:
    return _confirmation_with_parties(
        [{"name": carrier_name, "confirmed_role": "insurance_carrier"}],
        jurisdiction,
    )


def _confirmation_with_parties(
    parties: list[dict[str, str]],
    jurisdiction: str,
) -> HumanConfirmation:
    return HumanConfirmation.model_validate(
        {
            "confirmation_id": "hc-test",
            "preflight_packet_id": "pf-test",
            "status": "confirmed",
            "confirmed_matter_family": "medical_malpractice_defense",
            "confirmed_representation_posture": "defense_of_insured",
            "confirmed_parties": [
                *parties,
                {"name": "Dr. Maya Chen", "confirmed_role": "prospective_represented_client"},
            ],
            "confirmed_jurisdiction": jurisdiction,
            "reviewer_id": "synthetic-human-reviewer",
            "reviewed_at": "2026-06-24T00:00:00Z",
        }
    )


def test_resolves_carrier_state_and_title(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    assert resolution.source == "carrier_rate_card"
    assert resolution.carrier_id == "synthetic-carrier-a"
    assert resolution.carrier_matched_by == "carrier_alias"
    assert resolution.state == "NV"
    assert resolution.state_matched_by == "jurisdiction_alias"
    assert resolution.effective_date == "2026-01-01"
    # Demo NV rates reproduce the prior flat rates (back-compat for the demo budget).
    assert resolution.role_rates["partner"] == 450.0
    assert resolution.role_rate_precedence == "carrier_state_title"
    assert TEMPLATE_ROLES <= set(resolution.role_rates)  # stays priced


def test_resolves_named_timekeeper_overrides_for_matching_state(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    override = resolution.named_timekeeper_overrides["synthetic-tk-harbor-partner-nv"]

    assert override.title == "partner"
    assert override.state == "NV"
    assert override.approved_rate == 430.0
    assert override.precedence_tier == "named_timekeeper_override"
    assert override.contains_real_firm_data is False
    assert override.candidate_only is True

    ca_resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "California"),
        rate_card=_card(repo_root),
    )
    assert "synthetic-tk-harbor-partner-nv" not in ca_resolution.named_timekeeper_overrides


def test_rate_varies_by_state(tmp_path, repo_root):
    nv = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    ca = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "California"),
        rate_card=_card(repo_root),
    )
    assert ca.state == "CA"
    assert ca.role_rates["partner"] == 520.0
    assert ca.role_rates["partner"] > nv.role_rates["partner"]


def test_rate_varies_by_carrier(tmp_path, repo_root):
    carrier_a = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    carrier_b = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Cascade Mutual", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    assert carrier_b.carrier_id == "synthetic-carrier-b"
    assert carrier_b.role_rates["partner"] == 395.0
    assert carrier_b.role_rates["partner"] != carrier_a.role_rates["partner"]


def test_unknown_carrier_role_party_requires_hours_only_review(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Unrecognized Mutual", "Synthetic State Court"),
        rate_card=_card(repo_root),
    )
    assert resolution.carrier_id == "synthetic-carrier-a"
    assert resolution.carrier_matched_by == "default_carrier"
    assert resolution.review_required is True
    assert resolution.pricing_status == "hours_only_review_required"
    assert resolution.role_rates == {}
    assert resolution.named_timekeeper_overrides == {}
    assert "carrier_role_party_unmatched_for_rates" in resolution.review_issue_codes


def test_missing_carrier_role_party_requires_hours_only_review(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation_with_parties(
            [{"name": "Dr. Maya Chen", "confirmed_role": "prospective_represented_client"}],
            "Synthetic State Court",
        ),
        rate_card=_card(repo_root),
    )

    assert resolution.carrier_id == "synthetic-carrier-a"
    assert resolution.carrier_matched_by == "default_carrier"
    assert resolution.review_required is True
    assert resolution.pricing_status == "hours_only_review_required"
    assert resolution.role_rates == {}
    assert resolution.named_timekeeper_overrides == {}
    assert "confirmed_carrier_role_missing_for_rates" in resolution.review_issue_codes


def test_unmapped_confirmed_jurisdiction_requires_hours_only_review(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Arizona"),
        rate_card=_card(repo_root),
    )

    assert resolution.carrier_id == "synthetic-carrier-a"
    assert resolution.carrier_matched_by == "carrier_alias"
    assert resolution.state == "NV"
    assert resolution.state_matched_by == "default_state"
    assert resolution.review_required is True
    assert resolution.role_rates == {}
    assert "confirmed_jurisdiction_unmapped_for_rates" in resolution.review_issue_codes


def test_same_role_multiple_carrier_matches_block_rate_pricing(tmp_path, repo_root):
    card = deepcopy(_card(repo_root))
    card["carriers"]["synthetic-carrier-a"]["aliases"].append("Dual Carrier")
    card["carriers"]["synthetic-carrier-b"]["aliases"].append("Dual Carrier")

    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Dual Carrier", "Synthetic State Court"),
        rate_card=card,
    )

    assert resolution.carrier_id == "ambiguous"
    assert resolution.carrier_matched_by == "ambiguous_carrier_alias"
    assert resolution.review_required is True
    assert resolution.role_rates == {}
    assert "ambiguous_carrier_for_rates" in resolution.review_issue_codes


def test_carrier_role_precedence_breaks_different_role_matches(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation_with_parties(
            [
                {"name": "Cascade Mutual", "confirmed_role": "insurance_carrier"},
                {"name": "Harbor Point Insurance", "confirmed_role": "payer"},
            ],
            "Synthetic State Court",
        ),
        rate_card=_card(repo_root),
    )

    assert resolution.carrier_id == "synthetic-carrier-b"
    assert resolution.carrier_matched_by == "carrier_alias_role_precedence"
    assert resolution.review_required is False
    assert resolution.role_rates["partner"] == 395.0


def test_no_card_uses_profile_flat_rates(tmp_path, repo_root):
    resolution = resolve_role_rates(
        profile=_profile(repo_root),
        confirmation=_confirmation("Harbor Point Insurance", "Synthetic State Court"),
        rate_card=None,
    )
    assert resolution.source == "practice_profile_flat"
    assert resolution.role_rates["partner"] == 450.0


def test_resolution_is_deterministic(tmp_path, repo_root):
    confirmation = _confirmation("Harbor Point Insurance", "California")
    first = resolve_role_rates(
        profile=_profile(repo_root), confirmation=confirmation, rate_card=_card(repo_root)
    )
    second = resolve_role_rates(
        profile=_profile(repo_root), confirmation=confirmation, rate_card=_card(repo_root)
    )
    assert first.model_dump() == second.model_dump()


def test_rate_card_loader_rejects_real_or_non_candidate_declarations(tmp_path, repo_root):
    card = _card(repo_root)
    card["contains_real_negotiated_rates"] = True
    real_declared = tmp_path / "real-declared.yaml"
    real_declared.write_text(yaml.safe_dump(card), encoding="utf-8")
    with pytest.raises(ValueError, match="real firm/carrier"):
        load_rate_card(real_declared)

    card = _card(repo_root)
    card["status"] = "reviewed"
    non_candidate = tmp_path / "non-candidate.yaml"
    non_candidate.write_text(yaml.safe_dump(card), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic candidate-only"):
        load_rate_card(non_candidate)
