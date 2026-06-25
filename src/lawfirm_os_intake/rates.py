"""Carrier x state x title rate resolution (slice A of the rate/guideline layer).

Replaces the flat ``synthetic_hourly_rates`` lookup with a deterministic resolution over
a synthetic carrier rate card: the matter's carrier (from the confirmed insurance carrier
party) and state (from the confirmed jurisdiction) select a per-title rate schedule. Every
resolution carries provenance so a defaulted carrier/state never looks like a confirmed
fact.

Scope of this slice: rate *resolution* only. The rate card is the authorized rate
schedule, not a guideline rate cap. Guideline caps, staffing/leverage reshaping, and the
proposed-vs-compliant projection are a separate future layer (see
``docs/carrier-rate-and-guideline-layer-design.md``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from .models import HumanConfirmation, StrictModel

# Confirmed party roles that identify the paying/instructing carrier for rate selection.
CARRIER_ROLES = ("insurance_carrier", "instructing_source", "payer")


class RoleRateResolution(StrictModel):
    """Resolved per-title hourly rates plus where each dimension came from."""

    rate_card_id: str
    carrier_id: str
    carrier_matched_by: str  # carrier_alias | default_carrier | profile_flat
    state: str
    state_matched_by: str  # jurisdiction_alias | default_state | profile_flat
    effective_date: str | None = None
    role_rates: dict[str, float] = Field(default_factory=dict)
    source: str  # carrier_rate_card | practice_profile_flat
    note: str | None = None


def load_rate_card(path: str | Path) -> dict[str, Any]:
    """Load the synthetic carrier rate card, refusing real firm/carrier content."""

    card = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(card, dict):
        raise ValueError("carrier rate card must be a mapping")
    if card.get("contains_real_firm_data", False):
        raise ValueError("real firm/carrier rate cards are prohibited in this starter repository")
    return card


def _flat_rates(profile: dict[str, Any]) -> dict[str, float]:
    return {str(k): float(v) for k, v in profile.get("synthetic_hourly_rates", {}).items()}


def _carrier_party_names(confirmation: HumanConfirmation) -> list[str]:
    return [
        party.name
        for party in confirmation.confirmed_parties
        if party.confirmed_role in CARRIER_ROLES
    ]


def _match_carrier(card: dict[str, Any], confirmation: HumanConfirmation) -> tuple[str, str]:
    names = {name.casefold() for name in _carrier_party_names(confirmation)}
    carriers = card.get("carriers", {})
    if isinstance(carriers, dict):
        for carrier_id, spec in carriers.items():
            if not isinstance(spec, dict):
                continue
            aliases = {str(alias).casefold() for alias in spec.get("aliases", [])}
            if names & aliases:
                return str(carrier_id), "carrier_alias"
    return str(card.get("default_carrier_id", "")), "default_carrier"


def _match_state(card: dict[str, Any], confirmation: HumanConfirmation) -> tuple[str, str]:
    jurisdiction = confirmation.confirmed_jurisdiction
    aliases = card.get("jurisdiction_aliases", {})
    if jurisdiction and isinstance(aliases, dict) and jurisdiction in aliases:
        return str(aliases[jurisdiction]), "jurisdiction_alias"
    return str(card.get("default_state", "")), "default_state"


def _flat_resolution(profile: dict[str, Any], note: str) -> RoleRateResolution:
    return RoleRateResolution(
        rate_card_id="none",
        carrier_id="none",
        carrier_matched_by="profile_flat",
        state="none",
        state_matched_by="profile_flat",
        role_rates=_flat_rates(profile),
        source="practice_profile_flat",
        note=note,
    )


def resolve_role_rates(
    *,
    profile: dict[str, Any],
    confirmation: HumanConfirmation,
    rate_card: dict[str, Any] | None = None,
) -> RoleRateResolution:
    """Resolve per-title rates from the carrier rate card, falling back to flat rates.

    Deterministic and side-effect free. When no card is supplied, or the card has no
    schedule for the resolved carrier/state, the practice-profile flat rates are used so
    existing behavior is preserved.
    """

    if rate_card is None:
        return _flat_resolution(
            profile, "No carrier rate card referenced; using practice-profile flat rates."
        )

    carrier_id, carrier_matched_by = _match_carrier(rate_card, confirmation)
    state, state_matched_by = _match_state(rate_card, confirmation)
    carrier_spec = rate_card.get("carriers", {}).get(carrier_id, {})
    schedule = carrier_spec.get("schedule", {}) if isinstance(carrier_spec, dict) else {}
    state_rates = schedule.get(state, {}) if isinstance(schedule, dict) else {}
    role_rates = {str(k): float(v) for k, v in state_rates.items()} if state_rates else {}

    if not role_rates:
        return _flat_resolution(
            profile,
            f"Carrier rate card had no schedule for {carrier_id}/{state}; "
            "fell back to practice-profile flat rates.",
        )

    effective_date = carrier_spec.get("effective_date")
    return RoleRateResolution(
        rate_card_id=str(rate_card.get("rate_card_id", "unknown")),
        carrier_id=carrier_id,
        carrier_matched_by=carrier_matched_by,
        state=state,
        state_matched_by=state_matched_by,
        effective_date=str(effective_date) if effective_date is not None else None,
        role_rates=role_rates,
        source="carrier_rate_card",
        note=(
            f"Synthetic carrier rate card {carrier_id} for state {state} "
            f"(carrier matched by {carrier_matched_by}, state by {state_matched_by}); "
            "rates are synthetic and not authorized for real billing."
        ),
    )
