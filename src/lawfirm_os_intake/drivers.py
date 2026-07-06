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

from copy import deepcopy
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
    intensity_normalization_mode: Literal["raw", "baseline_relative"] = "raw"
    intensity_baseline_by_driver: dict[str, str] = Field(default_factory=dict)
    raw_intensity_multiplier_policy: dict[str, Any] = Field(default_factory=dict)
    effective_intensity_multiplier_policy: dict[str, Any] = Field(default_factory=dict)
    intensity_multiplier_policy: dict[str, Any] = Field(default_factory=dict)
    coverage_posture_policy: dict[str, Any] = Field(default_factory=dict)
    synthetic_guideline_constraints: dict[str, Any] = Field(default_factory=dict)
    count_driver_range_policy: dict[str, Any] = Field(default_factory=dict)
    scenario_policy: list[dict[str, Any]] = Field(default_factory=list)
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


def _budget_template_for_family(profile: dict[str, Any], matter_family: str) -> dict[str, Any]:
    templates = profile.get("budget_templates", {})
    template = templates.get(matter_family, {}) if isinstance(templates, dict) else {}
    return template if isinstance(template, dict) else {}


def _template_baseline_intensity(profile: dict[str, Any], matter_family: str) -> dict[str, Any]:
    template = _budget_template_for_family(profile, matter_family)
    baseline = template.get("baseline_intensity", {})
    return baseline if isinstance(baseline, dict) else {}


def _raw_multiplier_for_phase(
    effects_by_driver: dict[str, Any],
    driver_id: str,
    tier: str | None,
    phase_id: str,
) -> float:
    if tier is None:
        return 1.0
    driver_effects = effects_by_driver.get(driver_id)
    if not isinstance(driver_effects, dict):
        return 1.0
    effect = driver_effects.get(str(tier))
    if not isinstance(effect, dict):
        return 1.0
    phase_ids = [str(item) for item in effect.get("phase_ids", [])]
    if phase_ids and phase_id not in phase_ids:
        return 1.0
    return float(effect.get("multiplier", 1.0))


def build_effective_intensity_multiplier_policy(
    raw_policy: dict[str, Any],
    *,
    matter_family: str,
    profile: dict[str, Any],
    family_defaults: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Return the effective intensity policy plus the baseline tiers used.

    ``normalization: raw`` is intentionally behavior-preserving. ``baseline_relative``
    divides each tier's raw multiplier by the raw multiplier of the template baseline
    tier for the same driver and phase.
    """

    effective_policy = deepcopy(raw_policy) if isinstance(raw_policy, dict) else {}
    mode = str(effective_policy.get("normalization", "raw"))
    if mode not in {"raw", "baseline_relative"}:
        raise ValueError(f"unsupported intensity normalization mode: {mode}")
    effective_policy["normalization"] = mode
    effects_by_driver = effective_policy.get("effects", {})
    if not isinstance(effects_by_driver, dict):
        return effective_policy, {}

    declared_baseline = _template_baseline_intensity(profile, matter_family)
    baseline_by_driver = {
        str(driver_id): str(declared_baseline.get(driver_id, family_defaults.get(driver_id)))
        for driver_id in effects_by_driver
        if declared_baseline.get(driver_id, family_defaults.get(driver_id)) is not None
    }
    if mode == "raw":
        for driver_id, value_effects in effects_by_driver.items():
            if not isinstance(value_effects, dict):
                continue
            for effect in value_effects.values():
                if isinstance(effect, dict):
                    raw_multiplier = float(effect.get("multiplier", 1.0))
                    effect["raw_multiplier"] = raw_multiplier
                    effect["effective_multiplier"] = raw_multiplier
        return effective_policy, baseline_by_driver

    for driver_id, value_effects in effects_by_driver.items():
        if not isinstance(value_effects, dict):
            continue
        baseline_tier = baseline_by_driver.get(str(driver_id))
        for effect in value_effects.values():
            if not isinstance(effect, dict):
                continue
            raw_multiplier = float(effect.get("multiplier", 1.0))
            phase_ids = [str(item) for item in effect.get("phase_ids", [])]
            effective_by_phase = {
                phase_id: round(
                    raw_multiplier
                    / _raw_multiplier_for_phase(
                        effects_by_driver,
                        str(driver_id),
                        baseline_tier,
                        phase_id,
                    ),
                    4,
                )
                for phase_id in phase_ids
            }
            effect["raw_multiplier"] = raw_multiplier
            effect["effective_multipliers_by_phase"] = effective_by_phase
            if len(set(effective_by_phase.values())) == 1:
                effect["effective_multiplier"] = next(iter(effective_by_phase.values()))
    return effective_policy, baseline_by_driver


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
    raw_intensity_policy = policy.get("intensity_multiplier_policy", {})
    effective_intensity_policy, baseline_by_driver = build_effective_intensity_multiplier_policy(
        raw_intensity_policy,
        matter_family=matter_family,
        profile=profile,
        family_defaults=defaults,
    )
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
        intensity_normalization_mode=str(effective_intensity_policy.get("normalization", "raw")),  # type: ignore[arg-type]
        intensity_baseline_by_driver=baseline_by_driver,
        raw_intensity_multiplier_policy=(
            raw_intensity_policy if isinstance(raw_intensity_policy, dict) else {}
        ),
        effective_intensity_multiplier_policy=effective_intensity_policy,
        intensity_multiplier_policy=effective_intensity_policy,
        coverage_posture_policy=policy.get("coverage_posture_policy", {}),
        synthetic_guideline_constraints=policy.get("synthetic_guideline_constraints", {}),
        count_driver_range_policy=policy.get("count_driver_ranges", {}),
        scenario_policy=policy.get("scenarios", []),
    )
