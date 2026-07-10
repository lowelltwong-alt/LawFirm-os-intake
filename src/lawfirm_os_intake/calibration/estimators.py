from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable, Protocol


class ScalarMatterContribution(Protocol):
    matter_id: str
    protected_unit_id: str
    contribution: float


@dataclass(frozen=True)
class SufficientStatContribution:
    matter_id: str
    protected_unit_id: str
    values: tuple[float, ...]
    pre_clip_norm: float
    clipped: bool


def mean_sufficient_stat_contributions(
    matters: Iterable[ScalarMatterContribution],
) -> list[SufficientStatContribution]:
    """Reduce scalar means to per-matter (sum, count) sufficient statistics."""
    contributions: list[SufficientStatContribution] = []
    for matter in matters:
        values = (float(matter.contribution), 1.0)
        if not all(isfinite(value) for value in values):
            raise ValueError("sufficient-stat contribution must be finite")
        contributions.append(
            SufficientStatContribution(
                matter_id=matter.matter_id,
                protected_unit_id=matter.protected_unit_id,
                values=values,
                pre_clip_norm=l2_norm(values),
                clipped=False,
            )
        )
    if not contributions:
        raise ValueError("at least one sufficient-stat contribution is required")
    return contributions


def clip_sufficient_stat_contributions(
    contributions: Iterable[SufficientStatContribution],
    *,
    clip_norm: float,
) -> list[SufficientStatContribution]:
    if not isfinite(clip_norm) or clip_norm <= 0:
        raise ValueError("clip_norm must be finite and positive")
    clipped: list[SufficientStatContribution] = []
    for contribution in contributions:
        norm = l2_norm(contribution.values)
        scale = min(1.0, clip_norm / norm) if norm else 1.0
        clipped.append(
            SufficientStatContribution(
                matter_id=contribution.matter_id,
                protected_unit_id=contribution.protected_unit_id,
                values=tuple(value * scale for value in contribution.values),
                pre_clip_norm=norm,
                clipped=scale < 1.0,
            )
        )
    return clipped


def pool_sufficient_stats(
    contributions: Iterable[SufficientStatContribution],
) -> tuple[float, ...]:
    rows = list(contributions)
    if not rows:
        raise ValueError("at least one sufficient-stat contribution is required")
    width = len(rows[0].values)
    if width == 0 or any(len(row.values) != width for row in rows):
        raise ValueError("sufficient-stat vectors must have one stable non-empty width")
    return tuple(sum(row.values[index] for row in rows) for index in range(width))


def l2_norm(values: Iterable[float]) -> float:
    vector = tuple(values)
    if not all(isfinite(value) for value in vector):
        raise ValueError("vector values must be finite")
    return sqrt(sum(value * value for value in vector))
