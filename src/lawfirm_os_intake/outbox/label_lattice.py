"""Closed IFC sensitivity lattice for candidate outbox evidence."""

from __future__ import annotations

from enum import Enum


class SensitivityLabel(str, Enum):
    """The closed order is public < candidate < internal < privileged."""

    public = "public"
    candidate = "candidate"
    internal = "internal"
    privileged = "privileged"


_LABEL_RANK = {
    SensitivityLabel.public: 0,
    SensitivityLabel.candidate: 1,
    SensitivityLabel.internal: 2,
    SensitivityLabel.privileged: 3,
}


def join_labels(labels: tuple[SensitivityLabel, ...]) -> SensitivityLabel:
    """Return the lattice join, failing closed when no labels are supplied."""
    if not labels:
        raise ValueError("at least one sensitivity label is required")
    return max(labels, key=_LABEL_RANK.__getitem__)


def is_candidate_crossing_label(label: SensitivityLabel) -> bool:
    """DAD candidate crossings may carry no label higher than candidate."""
    return _LABEL_RANK[label] <= _LABEL_RANK[SensitivityLabel.candidate]
