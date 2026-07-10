from __future__ import annotations

from math import isfinite
from typing import Iterable


def max_leave_one_matter_out_mean_delta(values: Iterable[float]) -> float | None:
    matter_values = list(values)
    if not all(isfinite(value) for value in matter_values):
        raise ValueError("LOMO values must be finite")
    if len(matter_values) < 2:
        return None
    full_mean = sum(matter_values) / len(matter_values)
    return max(
        abs(full_mean - ((sum(matter_values) - value) / (len(matter_values) - 1)))
        for value in matter_values
    )


def top1_protected_unit_leverage(values: Iterable[float]) -> float:
    unit_values = list(values)
    if not all(isfinite(value) for value in unit_values):
        raise ValueError("leverage values must be finite")
    total_abs = sum(abs(value) for value in unit_values)
    if total_abs == 0:
        return 0.0
    return max((abs(value) / total_abs for value in unit_values), default=0.0)
