from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from .models import EffectiveContext
from .util import digest_json, new_id


DEFAULT_PRECEDENCE = [
    "observed_source_evidence",
    "human_confirmed_matter_facts",
    "client_or_referral_source_profile",
    "practice_group_profile",
    "firm_defaults",
]


def load_profile(path: str | Path) -> dict[str, Any]:
    profile = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("practice profile must be a mapping")
    if profile.get("contains_real_firm_data", False):
        raise ValueError("real firm profiles are prohibited in this starter repository")
    return profile


def build_effective_context(profile: dict[str, Any]) -> EffectiveContext:
    return EffectiveContext(
        context_id=new_id("ctx"),
        profile_id=str(profile["profile_id"]),
        profile_version=str(profile.get("version", "0.1")),
        profile_sha256=digest_json(profile),
        applied_layers=list(profile.get("applied_layers", ["synthetic_firm", "practice_group"])),
        active_practices=list(profile.get("active_practices", [])),
        default_side=str(profile.get("default_side", "varies")),
        typical_inbound_sources={
            str(k): float(v) for k, v in profile.get("typical_inbound_sources", {}).items()
        },
        matter_family_priors={
            str(k): float(v) for k, v in profile.get("matter_family_priors", {}).items()
        },
        required_intake_fields=list(profile.get("required_intake_fields", [])),
        budget_template_ids=list(profile.get("budget_template_ids", [])),
        context_precedence=list(profile.get("context_precedence", DEFAULT_PRECEDENCE)),
    )
