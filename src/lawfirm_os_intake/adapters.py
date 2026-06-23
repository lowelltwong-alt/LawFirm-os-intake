from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AdapterName = Literal["deterministic", "structured-model"]


@dataclass(frozen=True)
class AdapterDecision:
    name: AdapterName
    mode: Literal["deterministic", "dry_run"]
    model_calls_allowed: bool
    external_tools_allowed: bool
    notes: str


def resolve_adapter(name: str) -> AdapterDecision:
    if name == "deterministic":
        return AdapterDecision(
            name="deterministic",
            mode="deterministic",
            model_calls_allowed=False,
            external_tools_allowed=False,
            notes="Deterministic local worker implementation.",
        )
    if name == "structured-model":
        return AdapterDecision(
            name="structured-model",
            mode="dry_run",
            model_calls_allowed=False,
            external_tools_allowed=False,
            notes=(
                "Synthetic-only structured-output adapter boundary. No provider call is made; "
                "deterministic workers remain the execution source."
            ),
        )
    raise ValueError(f"unsupported adapter: {name}")
