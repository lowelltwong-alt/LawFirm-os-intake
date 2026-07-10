"""Cross-published-lesson differencing suppression for synthetic candidates."""

from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .kanon_universe import ReviewedSyntheticUniverse
from .generalization_lattice import GeneralizationLattice
from .lesson_ir import DIMENSION_ORDER, LessonAtom


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublishedLessonProjection(_StrictModel):
    lesson_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    atoms: tuple[LessonAtom, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def projection_is_unambiguous(self) -> "PublishedLessonProjection":
        if not self.lesson_id.strip():
            raise ValueError("published projection lesson_id must not be whitespace")
        if len({atom.dimension for atom in self.atoms}) != len(self.atoms):
            raise ValueError("published projection may contain at most one atom per dimension")
        return self


class DifferencingIntersection(_StrictModel):
    published_lesson_ids: tuple[str, ...]
    matter_ids: tuple[str, ...]


class DifferencingCheck(_StrictModel):
    narrows_below_k: bool
    suppressed: bool
    intersections: tuple[DifferencingIntersection, ...]


def check_differencing(
    *,
    candidate_atoms: tuple[LessonAtom, ...],
    published_lessons: tuple[PublishedLessonProjection, ...],
    universe: ReviewedSyntheticUniverse,
    lattice: GeneralizationLattice,
    k_qual: int,
) -> DifferencingCheck:
    """Suppress when a nonempty published-projection intersection falls below synthetic k."""
    if k_qual < 1:
        raise ValueError("k_qual must be an explicit positive synthetic policy input")
    if len({lesson.lesson_id for lesson in published_lessons}) != len(published_lessons):
        raise ValueError("published lesson IDs must be unique")
    intersections: list[DifferencingIntersection] = []
    ordered_lessons = tuple(sorted(published_lessons, key=lambda item: item.lesson_id))
    for size in range(1, len(ordered_lessons) + 1):
        for projection_set in combinations(ordered_lessons, size):
            combined = candidate_atoms + tuple(
                atom for lesson in projection_set for atom in lesson.atoms
            )
            atoms_by_dimension: dict[str, LessonAtom] = {}
            conflicting = False
            for atom in combined:
                existing = atoms_by_dimension.get(atom.dimension)
                if existing is None or existing.value == atom.value:
                    atoms_by_dimension[atom.dimension] = atom
                    continue
                if lattice.matches(atom.dimension, existing.value, atom.value):
                    atoms_by_dimension[atom.dimension] = existing
                    continue
                if lattice.matches(atom.dimension, atom.value, existing.value):
                    atoms_by_dimension[atom.dimension] = atom
                    continue
                conflicting = True
                break
            if conflicting:
                continue
            merged_atoms = tuple(
                atoms_by_dimension[dimension]
                for dimension in DIMENSION_ORDER
                if dimension in atoms_by_dimension
            )
            matter_ids = universe.anonymity_set(merged_atoms, lattice=lattice)
            if matter_ids:
                intersections.append(
                    DifferencingIntersection(
                        published_lesson_ids=tuple(lesson.lesson_id for lesson in projection_set),
                        matter_ids=matter_ids,
                    )
                )
    narrows_below_k = any(len(item.matter_ids) < k_qual for item in intersections)
    return DifferencingCheck(
        narrows_below_k=narrows_below_k,
        suppressed=narrows_below_k,
        intersections=tuple(intersections),
    )
