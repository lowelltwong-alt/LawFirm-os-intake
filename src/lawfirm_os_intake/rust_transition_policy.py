from __future__ import annotations

from pathlib import Path

from .models import RustTransitionPolicy
from .util import load_json


RUST_TRANSITION_POLICY_REF = "config/rust-ingestion-transition-policy.json"
ROOT = Path(__file__).resolve().parents[2]


def load_rust_transition_policy() -> RustTransitionPolicy:
    return RustTransitionPolicy.model_validate(load_json(ROOT / RUST_TRANSITION_POLICY_REF))
