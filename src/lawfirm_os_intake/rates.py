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

from .models import HumanConfirmation, NamedTimekeeperRate, StrictModel

# Confirmed party roles that identify the paying/instructing carrier for rate selection.
CARRIER_ROLES = ("insurance_carrier", "instructing_source", "payer")
CARRIER_ROLE_PRECEDENCE = {
    "insurance_carrier": 0,
    "instructing_source": 1,
    "payer": 2,
}


class RoleRateResolution(StrictModel):
    """Resolved per-title hourly rates plus where each dimension came from."""

    rate_card_id: str
    carrier_id: str
    carrier_matched_by: str  # carrier_alias | default_carrier | profile_flat
    state: str
    state_matched_by: str  # jurisdiction_alias | default_state | profile_flat
    effective_date: str | None = None
    role_rates: dict[str, float] = Field(default_factory=dict)
    role_rate_precedence: str = "unknown"
    named_timekeeper_overrides: dict[str, NamedTimekeeperRate] = Field(default_factory=dict)
    source: str  # carrier_rate_card | practice_profile_flat
    pricing_status: str = "priced"
    review_required: bool = False
    review_issue_codes: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
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


def _carrier_party_refs(confirmation: HumanConfirmation) -> list[tuple[str, str]]:
    return [
        (party.name, party.confirmed_role)
        for party in confirmation.confirmed_parties
        if party.confirmed_role in CARRIER_ROLES
    ]


def _match_carrier(
    card: dict[str, Any],
    confirmation: HumanConfirmation,
) -> tuple[str, str, list[str], list[str]]:
    party_refs = _carrier_party_refs(confirmation)
    carriers = card.get("carriers", {})
    matches: list[tuple[int, str, str, str]] = []
    if isinstance(carriers, dict):
        for carrier_id, spec in carriers.items():
            if not isinstance(spec, dict):
                continue
            aliases = {str(alias).casefold() for alias in spec.get("aliases", [])}
            for name, role in party_refs:
                if name.casefold() in aliases:
                    matches.append(
                        (
                            CARRIER_ROLE_PRECEDENCE.get(role, 99),
                            str(carrier_id),
                            role,
                            name,
                        )
                    )
    if not matches:
        carrier_id = str(card.get("default_carrier_id", ""))
        if party_refs:
            names = ", ".join(sorted(name for name, _role in party_refs))
            return (
                carrier_id,
                "default_carrier",
                ["carrier_role_party_unmatched_for_rates"],
                [
                    "Carrier-role parties were confirmed but none matched the synthetic "
                    f"rate-card aliases ({names}); budget must remain hours-only pending "
                    "human rate review."
                ],
            )
        return carrier_id, "default_carrier", [], []

    best_precedence = min(match[0] for match in matches)
    best_matches = [match for match in matches if match[0] == best_precedence]
    best_carriers = sorted({match[1] for match in best_matches})
    if len(best_carriers) > 1:
        matched = "; ".join(
            f"{carrier_id}:{role}:{name}"
            for _precedence, carrier_id, role, name in sorted(best_matches)
        )
        return (
            "ambiguous",
            "ambiguous_carrier_alias",
            ["ambiguous_carrier_for_rates"],
            [
                "Multiple carrier aliases matched at the same role precedence "
                f"({matched}); budget must remain hours-only pending human rate review."
            ],
        )

    carrier_id = best_carriers[0]
    distinct_carriers = {match[1] for match in matches}
    matched_by = "carrier_alias_role_precedence" if len(distinct_carriers) > 1 else "carrier_alias"
    return carrier_id, matched_by, [], []


def _match_state(
    card: dict[str, Any],
    confirmation: HumanConfirmation,
) -> tuple[str, str, list[str], list[str]]:
    jurisdiction = confirmation.confirmed_jurisdiction
    aliases = card.get("jurisdiction_aliases", {})
    if jurisdiction and isinstance(aliases, dict) and jurisdiction in aliases:
        return str(aliases[jurisdiction]), "jurisdiction_alias", [], []
    state = str(card.get("default_state", ""))
    if jurisdiction:
        return (
            state,
            "default_state",
            ["confirmed_jurisdiction_unmapped_for_rates"],
            [
                f"Confirmed jurisdiction {jurisdiction!r} did not match the synthetic "
                "rate-card jurisdiction aliases; budget must remain hours-only pending "
                "human rate review."
            ],
        )
    return state, "default_state", [], []


def _flat_resolution(profile: dict[str, Any], note: str) -> RoleRateResolution:
    return RoleRateResolution(
        rate_card_id="none",
        carrier_id="none",
        carrier_matched_by="profile_flat",
        state="none",
        state_matched_by="profile_flat",
        role_rates=_flat_rates(profile),
        role_rate_precedence="firm_default",
        source="practice_profile_flat",
        note=note,
    )


def _hours_only_review_resolution(
    *,
    rate_card: dict[str, Any],
    carrier_id: str,
    carrier_matched_by: str,
    state: str,
    state_matched_by: str,
    issue_codes: list[str],
    review_notes: list[str],
) -> RoleRateResolution:
    return RoleRateResolution(
        rate_card_id=str(rate_card.get("rate_card_id", "unknown")),
        carrier_id=carrier_id,
        carrier_matched_by=carrier_matched_by,
        state=state,
        state_matched_by=state_matched_by,
        role_rates={},
        role_rate_precedence="hours_only_pending_rate_review",
        named_timekeeper_overrides={},
        source="carrier_rate_card",
        pricing_status="hours_only_review_required",
        review_required=True,
        review_issue_codes=sorted(set(issue_codes)),
        review_notes=review_notes,
        note=(
            "Synthetic carrier rate resolution requires human review; pricing is "
            "hours-only because one or more carrier/state dimensions were defaulted "
            "or ambiguous. " + " ".join(review_notes)
        ),
    )


def _named_timekeeper_overrides(
    *,
    rate_card: dict[str, Any],
    carrier_id: str,
    state: str,
) -> dict[str, NamedTimekeeperRate]:
    carrier_spec = rate_card.get("carriers", {}).get(carrier_id, {})
    if not isinstance(carrier_spec, dict):
        return {}
    overrides = carrier_spec.get("named_timekeeper_overrides", {})
    if not isinstance(overrides, dict):
        return {}

    resolved: dict[str, NamedTimekeeperRate] = {}
    for timekeeper_id, raw_spec in overrides.items():
        if not isinstance(raw_spec, dict):
            continue
        override_state = raw_spec.get("state")
        if override_state is not None and str(override_state) != state:
            continue
        approved_rate = raw_spec.get("approved_rate")
        if approved_rate is None:
            continue
        resolved[str(timekeeper_id)] = NamedTimekeeperRate(
            timekeeper_id=str(timekeeper_id),
            title=str(raw_spec.get("title", "")),
            state=str(override_state) if override_state is not None else None,
            approved_rate=float(approved_rate),
            carrier_id=carrier_id,
            rate_card_id=str(rate_card.get("rate_card_id", "unknown")),
        )
    return resolved


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

    carrier_id, carrier_matched_by, carrier_issue_codes, carrier_review_notes = _match_carrier(
        rate_card, confirmation
    )
    state, state_matched_by, state_issue_codes, state_review_notes = _match_state(
        rate_card, confirmation
    )
    issue_codes = carrier_issue_codes + state_issue_codes
    review_notes = carrier_review_notes + state_review_notes
    if issue_codes:
        return _hours_only_review_resolution(
            rate_card=rate_card,
            carrier_id=carrier_id,
            carrier_matched_by=carrier_matched_by,
            state=state,
            state_matched_by=state_matched_by,
            issue_codes=issue_codes,
            review_notes=review_notes,
        )

    carrier_spec = rate_card.get("carriers", {}).get(carrier_id, {})
    schedule = carrier_spec.get("schedule", {}) if isinstance(carrier_spec, dict) else {}
    state_rates = schedule.get(state, {}) if isinstance(schedule, dict) else {}
    role_rates = {str(k): float(v) for k, v in state_rates.items()} if state_rates else {}
    role_rate_precedence = "carrier_state_title"
    if not role_rates and isinstance(carrier_spec, dict):
        default_title_rates = carrier_spec.get("default_title_rates", {})
        if isinstance(default_title_rates, dict) and default_title_rates:
            role_rates = {str(k): float(v) for k, v in default_title_rates.items()}
            role_rate_precedence = "carrier_title_default"
    named_overrides = _named_timekeeper_overrides(
        rate_card=rate_card,
        carrier_id=carrier_id,
        state=state,
    )

    if not role_rates:
        fallback = _flat_resolution(
            profile,
            f"Carrier rate card had no schedule for {carrier_id}/{state}; "
            "fell back to practice-profile flat rates.",
        )
        return fallback.model_copy(update={"named_timekeeper_overrides": named_overrides})

    effective_date = carrier_spec.get("effective_date")
    return RoleRateResolution(
        rate_card_id=str(rate_card.get("rate_card_id", "unknown")),
        carrier_id=carrier_id,
        carrier_matched_by=carrier_matched_by,
        state=state,
        state_matched_by=state_matched_by,
        effective_date=str(effective_date) if effective_date is not None else None,
        role_rates=role_rates,
        role_rate_precedence=role_rate_precedence,
        named_timekeeper_overrides=named_overrides,
        source="carrier_rate_card",
        note=(
            f"Synthetic carrier rate card {carrier_id} for state {state} "
            f"(carrier matched by {carrier_matched_by}, state by {state_matched_by}); "
            f"title rates resolved by {role_rate_precedence}; "
            "named timekeeper overrides, when present, take precedence only for matching "
            "synthetic task timekeeper IDs; rates are synthetic and not authorized for real billing."
        ),
    )
