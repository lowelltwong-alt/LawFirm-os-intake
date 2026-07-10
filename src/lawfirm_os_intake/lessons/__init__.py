"""Candidate-only, synthetic-only qualitative-rule disclosure primitives."""

from .differencing import DifferencingCheck, PublishedLessonProjection, check_differencing
from .disclosure_proof import (
    TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
    TRUSTED_SYNTHETIC_LESSON_DIGESTS,
    LessonDisclosureProof,
    LessonDisclosureRequest,
    build_lesson_disclosure_proof,
    lesson_disclosure_request_digest,
    published_projection_snapshot_digest,
    synthetic_lesson_fixture_digest,
)
from .generalization_lattice import GeneralizationLattice, GeneralizationResult
from .kanon_universe import ReviewedSyntheticUniverse, SyntheticMatter
from .lesson_ir import LessonAtom, LessonClaim, LessonIR, SyntheticPolicyPlaceholders
from .privilege_partition import PrivilegePartitionResult, screen_privilege_partition

__all__ = [
    "DifferencingCheck",
    "GeneralizationLattice",
    "GeneralizationResult",
    "LessonAtom",
    "LessonClaim",
    "LessonDisclosureProof",
    "LessonDisclosureRequest",
    "LessonIR",
    "PrivilegePartitionResult",
    "PublishedLessonProjection",
    "ReviewedSyntheticUniverse",
    "SyntheticMatter",
    "SyntheticPolicyPlaceholders",
    "TRUSTED_SYNTHETIC_CONTEXT_DIGEST",
    "TRUSTED_SYNTHETIC_LESSON_DIGESTS",
    "check_differencing",
    "build_lesson_disclosure_proof",
    "lesson_disclosure_request_digest",
    "published_projection_snapshot_digest",
    "screen_privilege_partition",
    "synthetic_lesson_fixture_digest",
]
