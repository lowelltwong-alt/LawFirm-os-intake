"""Case-driver capture for the driver-based budget model.

This module resolves the litigation cost drivers for a confirmed intake, each with
explicit provenance, and records them as a candidate ``CaseDriverProfile``. It does
feed deterministic budget math while preserving visible provenance.

Governance:

- driver taxonomy and per-matter-family defaults live in a versioned, hashed synthetic
  policy (``config/budget-driver-policy.yaml``), never hidden in code;
- every driver value carries a provenance channel so a profile default never
  masquerades as an observed case fact, and unknowns stay explicitly unknown;
- resolution is deterministic and side-effect free.

See ``docs/driver-based-budget-model-design.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field

from .models import HumanConfirmation, IntakePreflightPacket, StrictModel
from .util import new_id

DriverProvenance = Literal[
    "observed_support",
    "human_confirmed",
    "profile_default",
    "unknown",
]

# Confirmed party roles that map to defended/insured parties and to adverse parties.
REPRESENTED_DEFENDANT_ROLES = {
    "prospective_represented_client",
    "represented_client",
    "insured",
}
ADVERSE_ROLES = {"adverse_party", "claimant"}

# Drivers that can be derived from human-confirmed party roles in slice 1.
DERIVED_PARTY_DRIVERS: dict[str, set[str]] = {
    "num_represented_defendants": REPRESENTED_DEFENDANT_ROLES,
    "num_adverse_parties": ADVERSE_ROLES,
}


class DriverValue(StrictModel):
    """A single resolved cost driver and where its value came from."""

    driver_id: str
    driver_class: str
    value: int | float | str | None = None
    unit: str | None = None
    provenance: DriverProvenance
    source_refs: list[str] = Field(default_factory=list)
    note: str | None = None


class CaseDriverProfile(StrictModel):
    """Resolved cost drivers for one confirmed intake. Candidate and provenance-bound."""

    schema_version: str = "0.1"
    case_driver_profile_id: str
    preflight_packet_id: str
    confirmation_id: str
    matter_family: str
    policy_id: str
    policy_version: str
    drivers: list[DriverValue]
    observed_or_confirmed_driver_ids: list[str] = Field(default_factory=list)
    default_driver_ids: list[str] = Field(default_factory=list)
    unknown_driver_ids: list[str] = Field(default_factory=list)
    intensity_multiplier_policy: dict[str, Any] = Field(default_factory=dict)
    coverage_posture_policy: dict[str, Any] = Field(default_factory=dict)
    synthetic_guideline_constraints: dict[str, Any] = Field(default_factory=dict)
    status: Literal["candidate"] = "candidate"
    not_applied_to_math: bool = False


def load_driver_policy(path: str | Path) -> dict[str, Any]:
    """Load the synthetic budget-driver policy, refusing real-firm content."""

    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("budget driver policy must be a mapping")
    if policy.get("contains_real_firm_data", False):
        raise ValueError("real firm driver policies are prohibited in this starter repository")
    return policy


def _confirmation_ref(confirmation: HumanConfirmation) -> str:
    return f"human-confirmation://{confirmation.confirmation_id}"


def _policy_default_ref(policy_id: str, matter_family: str, driver_id: str) -> str:
    return f"budget-driver-policy://{policy_id}/matter_family_defaults/{matter_family}/{driver_id}"


def _count_confirmed_roles(confirmation: HumanConfirmation, roles: set[str]) -> int:
    return sum(1 for party in confirmation.confirmed_parties if party.confirmed_role in roles)


def resolve_case_drivers(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    profile: dict[str, Any],
    policy: dict[str, Any],
) -> CaseDriverProfile:
    """Resolve every driver in the policy taxonomy with explicit provenance.

    Precedence per driver: human-confirmed party-derived value, then a synthetic
    profile default, otherwise ``unknown``. The function is deterministic and does
    not mutate any input.
    """

    matter_family = confirmation.confirmed_matter_family or ""
    taxonomy: dict[str, Any] = policy.get("drivers", {})
    defaults: dict[str, Any] = policy.get("matter_family_defaults", {}).get(matter_family, {})
    policy_id = str(policy.get("policy_id", "unknown"))
    has_parties = bool(confirmation.confirmed_parties)

    resolved: list[DriverValue] = []
    for driver_id, spec in taxonomy.items():
        spec = spec if isinstance(spec, dict) else {}
        driver_class = str(spec.get("class", "unspecified"))
        unit = spec.get("unit")

        if driver_id in DERIVED_PARTY_DRIVERS and has_parties:
            resolved.append(
                DriverValue(
                    driver_id=driver_id,
                    driver_class=driver_class,
                    value=_count_confirmed_roles(confirmation, DERIVED_PARTY_DRIVERS[driver_id]),
                    unit=unit,
                    provenance="human_confirmed",
                    source_refs=[_confirmation_ref(confirmation)],
                    note="derived from human-confirmed party roles",
                )
            )
        elif driver_id in defaults:
            resolved.append(
                DriverValue(
                    driver_id=driver_id,
                    driver_class=driver_class,
                    value=defaults[driver_id],
                    unit=unit,
                    provenance="profile_default",
                    source_refs=[_policy_default_ref(policy_id, matter_family, driver_id)],
                    note="synthetic profile default; an assumption, not an observed case fact",
                )
            )
        else:
            resolved.append(
                DriverValue(
                    driver_id=driver_id,
                    driver_class=driver_class,
                    value=None,
                    unit=unit,
                    provenance="unknown",
                    note="no observed evidence, confirmation, or profile default; left unknown",
                )
            )

    resolved.sort(key=lambda driver: driver.driver_id)
    return CaseDriverProfile(
        case_driver_profile_id=new_id("casedrivers"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        matter_family=matter_family,
        policy_id=policy_id,
        policy_version=str(policy.get("version", "0.1")),
        drivers=resolved,
        observed_or_confirmed_driver_ids=[
            driver.driver_id
            for driver in resolved
            if driver.provenance in ("observed_support", "human_confirmed")
        ],
        default_driver_ids=[
            driver.driver_id for driver in resolved if driver.provenance == "profile_default"
        ],
        unknown_driver_ids=[
            driver.driver_id for driver in resolved if driver.provenance == "unknown"
        ],
        intensity_multiplier_policy=policy.get("intensity_multiplier_policy", {}),
        coverage_posture_policy=policy.get("coverage_posture_policy", {}),
        synthetic_guideline_constraints=policy.get("synthetic_guideline_constraints", {}),
    )
