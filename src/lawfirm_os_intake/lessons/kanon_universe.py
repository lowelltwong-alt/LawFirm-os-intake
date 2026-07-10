"""Reviewed synthetic matter universe matching for qualitative-rule candidates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .lesson_ir import DIMENSION_ORDER, Dimension, LessonAtom

if TYPE_CHECKING:
    from .generalization_lattice import GeneralizationLattice


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


SyntheticSensitiveOutcomeCode = Literal[
    "synthetic_outcome_a",
    "synthetic_outcome_b",
    "synthetic_outcome_c",
    "synthetic_outcome_d",
]


class SyntheticMatter(_StrictModel):
    matter_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    attributes: dict[Dimension, str]
    sensitive_outcome_code: SyntheticSensitiveOutcomeCode

    @model_validator(mode="after")
    def attributes_are_complete_and_nonblank(self) -> "SyntheticMatter":
        if not self.matter_id.strip():
            raise ValueError("synthetic matter ID must not be whitespace")
        if set(self.attributes) != set(DIMENSION_ORDER):
            raise ValueError("synthetic matter attributes must provide every closed dimension")
        if any(not value.strip() for value in self.attributes.values()):
            raise ValueError("synthetic matter attribute values must not be whitespace")
        if any(not re.fullmatch(r"[a-z0-9_:-]{1,80}", value) for value in self.attributes.values()):
            raise ValueError("synthetic matter attributes must use closed identifier values")
        return self


class ReviewedSyntheticUniverse(_StrictModel):
    universe_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    data_class: Literal["synthetic_fixture"]
    runtime_scope: Literal["synthetic_candidate"]
    candidate_only: Literal[True]
    matters: tuple[SyntheticMatter, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def universe_is_exactly_scoped_and_has_unique_matters(self) -> "ReviewedSyntheticUniverse":
        if not self.universe_id.strip():
            raise ValueError("universe_id must not be whitespace")
        if len({matter.matter_id for matter in self.matters}) != len(self.matters):
            raise ValueError("reviewed synthetic universe matter IDs must be unique")
        return self

    def matching_matters(
        self,
        atoms: tuple[LessonAtom, ...],
        *,
        lattice: "GeneralizationLattice | None" = None,
    ) -> tuple[SyntheticMatter, ...]:
        if not atoms:
            raise ValueError("anonymity matching requires at least one atom")
        if len({atom.dimension for atom in atoms}) != len(atoms):
            raise ValueError("anonymity matching rejects duplicate atom dimensions")
        return tuple(
            matter
            for matter in self.matters
            if all(
                (
                    matter.attributes[atom.dimension] == atom.value
                    if lattice is None
                    else lattice.matches(
                        atom.dimension, matter.attributes[atom.dimension], atom.value
                    )
                )
                for atom in atoms
            )
        )

    def anonymity_set(
        self,
        atoms: tuple[LessonAtom, ...],
        *,
        lattice: "GeneralizationLattice | None" = None,
    ) -> tuple[str, ...]:
        return tuple(matter.matter_id for matter in self.matching_matters(atoms, lattice=lattice))

    def sensitive_outcome_diversity(
        self,
        atoms: tuple[LessonAtom, ...],
        *,
        lattice: "GeneralizationLattice | None" = None,
    ) -> int:
        return len(
            {
                matter.sensitive_outcome_code
                for matter in self.matching_matters(atoms, lattice=lattice)
            }
        )
