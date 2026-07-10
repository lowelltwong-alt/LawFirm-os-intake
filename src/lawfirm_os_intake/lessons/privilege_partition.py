"""Fail-closed privilege partition for candidate-only synthetic lesson atoms."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .lesson_ir import LessonAtom, SyntheticPolicyPlaceholders


class PrivilegePartitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_atoms_present: bool
    blocked: bool
    blocking_atom_keys: tuple[str, ...]


def screen_privilege_partition(
    atoms: tuple[LessonAtom, ...], policy: SyntheticPolicyPlaceholders
) -> PrivilegePartitionResult:
    """Block strategy atoms and explicit synthetic policy strategy keys; never generalize them."""
    blocking_keys = tuple(
        atom.policy_key
        for atom in atoms
        if atom.atom_class == "strategy" or atom.policy_key in policy.strategy_atom_keys
    )
    return PrivilegePartitionResult(
        strategy_atoms_present=bool(blocking_keys),
        blocked=bool(blocking_keys),
        blocking_atom_keys=blocking_keys,
    )
