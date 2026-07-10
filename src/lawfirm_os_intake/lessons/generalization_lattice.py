"""Validated, deterministic parent lattices for synthetic lesson atoms."""

from __future__ import annotations

from collections import deque
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .kanon_universe import ReviewedSyntheticUniverse
from .lesson_ir import DIMENSION_ORDER, Dimension, LessonAtom


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GeneralizationStep(_StrictModel):
    dimension: Dimension
    from_value: str
    to_value: str


class GeneralizationResult(_StrictModel):
    atoms: tuple[LessonAtom, ...]
    anonymity_set: tuple[str, ...]
    sensitive_outcome_diversity: int
    path: tuple[GeneralizationStep, ...]
    suppressed: bool


class GeneralizationLattice(_StrictModel):
    policy_label: str = Field(min_length=1)
    parents: dict[Dimension, dict[str, str | None]]

    @model_validator(mode="after")
    def lattice_is_complete_and_acyclic(self) -> "GeneralizationLattice":
        if not self.policy_label.strip():
            raise ValueError("lattice requires a nonblank synthetic policy label")
        normalized_label = self.policy_label.casefold()
        if "synthetic" not in normalized_label or "placeholder" not in normalized_label:
            raise ValueError("lattice policy_label must identify a synthetic policy placeholder")
        if set(self.parents) != set(DIMENSION_ORDER):
            raise ValueError("lattice must define every closed dimension")
        for dimension in DIMENSION_ORDER:
            parent_map = self.parents[dimension]
            if not parent_map:
                raise ValueError(f"lattice dimension {dimension} must not be empty")
            if any(not value.strip() for value in parent_map):
                raise ValueError(f"lattice dimension {dimension} contains a blank value")
            if any(not re.fullmatch(r"[a-z0-9_:-]{1,80}", value) for value in parent_map):
                raise ValueError(f"lattice dimension {dimension} contains a non-closed value")
            if any(parent is not None and not parent.strip() for parent in parent_map.values()):
                raise ValueError(f"lattice dimension {dimension} contains a blank parent")
            if any(
                parent is not None and parent not in parent_map for parent in parent_map.values()
            ):
                raise ValueError(f"lattice dimension {dimension} has an unknown parent")
            for start in parent_map:
                seen: set[str] = set()
                value: str | None = start
                while value is not None:
                    if value in seen:
                        raise ValueError(f"lattice dimension {dimension} contains a cycle")
                    seen.add(value)
                    value = parent_map[value]
        return self

    def parent_of(self, dimension: Dimension, value: str) -> str:
        try:
            parent = self.parents[dimension][value]
        except KeyError as exc:
            raise ValueError(f"unknown lattice value for {dimension}: {value}") from exc
        if parent is None:
            raise ValueError(f"top-of-lattice has no parent for {dimension}: {value}")
        return parent

    def _validate_atoms(self, atoms: tuple[LessonAtom, ...]) -> None:
        if not atoms:
            raise ValueError("generalization requires at least one atom")
        if len({atom.dimension for atom in atoms}) != len(atoms):
            raise ValueError("generalization rejects duplicate atom dimensions")
        for atom in atoms:
            if atom.value not in self.parents[atom.dimension]:
                raise ValueError(f"unknown lattice value for {atom.dimension}: {atom.value}")

    def matches(self, dimension: Dimension, matter_value: str, predicate_value: str) -> bool:
        """Return whether a leaf or ancestor value satisfies a generalized predicate."""
        parent_map = self.parents[dimension]
        if matter_value not in parent_map or predicate_value not in parent_map:
            raise ValueError(f"unknown lattice value for {dimension}")
        current: str | None = matter_value
        while current is not None:
            if current == predicate_value:
                return True
            current = parent_map[current]
        return False

    def minimal_generalization(
        self,
        atoms: tuple[LessonAtom, ...],
        universe: ReviewedSyntheticUniverse,
        k_qual: int,
        minimum_sensitive_outcome_diversity: int,
    ) -> GeneralizationResult:
        """Find the minimum-hop generalization satisfying synthetic k and diversity."""
        if k_qual < 1 or minimum_sensitive_outcome_diversity < 1:
            raise ValueError("generalization thresholds must be positive synthetic inputs")
        self._validate_atoms(atoms)
        ordered_atoms = tuple(sorted(atoms, key=lambda atom: DIMENSION_ORDER.index(atom.dimension)))
        queue: deque[tuple[tuple[LessonAtom, ...], tuple[GeneralizationStep, ...]]] = deque(
            [(ordered_atoms, ())]
        )
        seen: set[tuple[tuple[Dimension, str, str], ...]] = set()
        best: (
            tuple[tuple[LessonAtom, ...], tuple[str, ...], int, tuple[GeneralizationStep, ...]]
            | None
        ) = None
        while queue:
            candidate_atoms, path = queue.popleft()
            key = tuple((atom.dimension, atom.value, atom.atom_class) for atom in candidate_atoms)
            if key in seen:
                continue
            seen.add(key)
            anonymity_set = universe.anonymity_set(candidate_atoms, lattice=self)
            sensitive_outcome_diversity = universe.sensitive_outcome_diversity(
                candidate_atoms, lattice=self
            )
            candidate_score = (len(anonymity_set), sensitive_outcome_diversity, -len(path))
            if best is None or candidate_score > (len(best[1]), best[2], -len(best[3])):
                best = (candidate_atoms, anonymity_set, sensitive_outcome_diversity, path)
            if (
                len(anonymity_set) >= k_qual
                and sensitive_outcome_diversity >= minimum_sensitive_outcome_diversity
            ):
                return GeneralizationResult(
                    atoms=candidate_atoms,
                    anonymity_set=anonymity_set,
                    sensitive_outcome_diversity=sensitive_outcome_diversity,
                    path=path,
                    suppressed=False,
                )
            for index, atom in enumerate(candidate_atoms):
                parent = self.parents[atom.dimension][atom.value]
                if parent is None:
                    continue
                replacement = LessonAtom(
                    dimension=atom.dimension, value=parent, atom_class=atom.atom_class
                )
                next_atoms = candidate_atoms[:index] + (replacement,) + candidate_atoms[index + 1 :]
                queue.append(
                    (
                        next_atoms,
                        path
                        + (
                            GeneralizationStep(
                                dimension=atom.dimension,
                                from_value=atom.value,
                                to_value=parent,
                            ),
                        ),
                    )
                )
        assert best is not None
        return GeneralizationResult(
            atoms=best[0],
            anonymity_set=best[1],
            sensitive_outcome_diversity=best[2],
            path=best[3],
            suppressed=True,
        )
