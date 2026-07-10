from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class ReconstructionSmokeCheckResult:
    adversary_model: str
    recovered_rate: float
    chance_rate: float
    margin: float
    tolerance: float
    passed: bool
    target_count: int


def run_all_but_one_sum_reconstruction_smoke_check(
    *,
    matter_values: Mapping[str, float],
    released_sum: float,
    tolerance: float,
    chance_rate: float,
    margin: float,
    adversary_model: str,
) -> ReconstructionSmokeCheckResult:
    """Run a synthetic implementation smoke check, not a privacy/security evaluation."""
    if "synthetic" not in adversary_model.lower() or "placeholder" not in adversary_model.lower():
        raise ValueError("reconstruction adversary model must be a synthetic placeholder")
    if not matter_values:
        raise ValueError("reconstruction test requires synthetic matter values")
    numeric = [released_sum, tolerance, chance_rate, margin, *matter_values.values()]
    if not all(isfinite(value) for value in numeric):
        raise ValueError("reconstruction test values must be finite")
    if tolerance < 0 or margin < 0 or not 0 <= chance_rate <= 1:
        raise ValueError("reconstruction policy values are outside their valid range")

    total = sum(matter_values.values())
    recovered = 0
    for target_value in matter_values.values():
        known_others = total - target_value
        inferred_target = released_sum - known_others
        if abs(inferred_target - target_value) <= tolerance:
            recovered += 1
    recovered_rate = recovered / len(matter_values)
    return ReconstructionSmokeCheckResult(
        adversary_model=adversary_model,
        recovered_rate=recovered_rate,
        chance_rate=chance_rate,
        margin=margin,
        tolerance=tolerance,
        passed=recovered_rate <= chance_rate + margin,
        target_count=len(matter_values),
    )
