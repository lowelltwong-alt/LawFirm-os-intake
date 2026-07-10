"""Brewer-Nash-style synthetic wall evaluation without legal conflict conclusions."""

from __future__ import annotations

import json
import re
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .adversity_graph import (
    AdversityRelationship,
    SyntheticAdversityGraph,
    adversity_graph_digest,
    adversity_relationship,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


TRUSTED_SYNTHETIC_ADVERSITY_GRAPH_DIGEST = (
    "sha256:355b0c259de100e4000211e26e4c38b9b69c0e3c4f9a6927c8d5ff5e34b762a4"
)
TRUSTED_SYNTHETIC_CHINESE_WALL_CASES_DIGEST = (
    "sha256:6777f21c501303c56568d6fc7a506335bce625dbfac2a1a7dfa8b8bb8b7adafa"
)

_TRUSTED_SYNTHETIC_CASES = {
    "synthetic-chw-cross-wall": (
        "synthetic-lesson-cross-wall",
        ("synthetic-coi-class-alpha",),
        ("synthetic-coi-class-beta",),
    ),
    "synthetic-chw-firm-wide-imputation": (
        "synthetic-lesson-firm-wide-imputation",
        ("synthetic-coi-class-alpha",),
        ("synthetic-coi-class-beta",),
    ),
    "synthetic-chw-same-side": (
        "synthetic-lesson-same-side",
        ("synthetic-coi-class-alpha",),
        ("synthetic-coi-class-alpha",),
    ),
    "synthetic-chw-unknown-relation": (
        "synthetic-lesson-unknown-relation",
        ("synthetic-coi-class-alpha",),
        ("synthetic-coi-class-gamma",),
    ),
    "synthetic-chw-unreviewed-edge": (
        "synthetic-lesson-unreviewed-edge",
        ("synthetic-coi-class-delta",),
        ("synthetic-coi-class-gamma",),
    ),
}


class WallDecision(str, Enum):
    same_side_candidate = "same_side_candidate"
    cross_wall_block = "cross_wall_block"
    unreviewed_edge_hold = "unreviewed_edge_hold"
    unknown_relation_hold = "unknown_relation_hold"


class ChineseWallRequest(_StrictModel):
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    lesson_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    data_class: Literal["synthetic_fixture"]
    runtime_scope: Literal["synthetic_candidate"]
    candidate_only: Literal[True]
    lesson_status: Literal["candidate"]
    adversity_graph: SyntheticAdversityGraph
    synthetic_adversity_graph_digest: Literal[
        "sha256:355b0c259de100e4000211e26e4c38b9b69c0e3c4f9a6927c8d5ff5e34b762a4"
    ]
    synthetic_case_manifest_digest: Literal[
        "sha256:6777f21c501303c56568d6fc7a506335bce625dbfac2a1a7dfa8b8bb8b7adafa"
    ]
    lesson_provenance_class_ids: tuple[str, ...] = Field(min_length=1)
    consuming_matter_class_ids: tuple[str, ...] = Field(min_length=1)
    provenance_scope: Literal["synthetic_firm_wide_fixture"]
    synthetic_firm_wide_provenance_snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trusted_synthetic_firm_wide_provenance_snapshot_pinned: Literal[True]
    synthetic_firm_wide_imputation_required: Literal[True]
    authoritative_firm_wide_provenance_manifest_verified: Literal[False]
    consuming_context_scope_known: Literal[True]
    contains_real_data: Literal[False]
    contains_private_data: Literal[False]
    contains_client_data: Literal[False]
    contains_matter_data: Literal[False]
    contains_real_carrier_data: Literal[False]
    contains_privileged_content: Literal[False]
    contains_work_product: Literal[False]

    @model_validator(mode="after")
    def request_is_closed_synthetic_scope(self) -> "ChineseWallRequest":
        if not self.adversity_graph.firm_wide_imputation_required:
            raise ValueError("adversity graph must require firm-wide imputation")
        if adversity_graph_digest(self.adversity_graph) != self.synthetic_adversity_graph_digest:
            raise ValueError("Chinese-wall request does not use the pinned synthetic graph")
        if _trusted_case_manifest_digest() != self.synthetic_case_manifest_digest:
            raise ValueError("Chinese-wall trusted synthetic case manifest digest is inconsistent")
        expected_case = _TRUSTED_SYNTHETIC_CASES.get(self.request_id)
        actual_case = (
            self.lesson_id,
            self.lesson_provenance_class_ids,
            self.consuming_matter_class_ids,
        )
        if expected_case is None or actual_case != expected_case:
            raise ValueError("Chinese-wall request is not in the pinned synthetic case manifest")
        expected_provenance_digest = _synthetic_provenance_snapshot_digest(
            self.lesson_id,
            self.lesson_provenance_class_ids,
        )
        if self.synthetic_firm_wide_provenance_snapshot_digest != expected_provenance_digest:
            raise ValueError("Chinese-wall synthetic firm-wide provenance snapshot is not pinned")
        known = {item.class_id for item in self.adversity_graph.conflict_classes}
        for label, class_ids in (
            ("lesson provenance", self.lesson_provenance_class_ids),
            ("consuming matter", self.consuming_matter_class_ids),
        ):
            if len(class_ids) != len(set(class_ids)) or tuple(sorted(class_ids)) != class_ids:
                raise ValueError(f"{label} class IDs must be unique and sorted")
            if any(
                re.fullmatch(r"synthetic-coi-class-[a-z0-9-]+", class_id) is None
                for class_id in class_ids
            ):
                raise ValueError(f"{label} class IDs must be closed synthetic identifiers")
            if not set(class_ids).issubset(known):
                raise ValueError(f"{label} references a class outside the pinned graph")
        return self


class ChineseWallEvaluation(_StrictModel):
    decision: WallDecision
    local_wall_candidate: bool
    same_side_pair_count: int = Field(ge=0)
    reviewed_adverse_pair_count: int = Field(ge=0)
    unreviewed_pair_count: int = Field(ge=0)
    unknown_pair_count: int = Field(ge=0)
    synthetic_firm_wide_imputation_applied: Literal[True]
    trusted_synthetic_provenance_snapshot_pinned: Literal[True]
    authoritative_firm_wide_imputation_verified: Literal[False]
    relationship_inference_performed: Literal[False] = False

    @model_validator(mode="after")
    def evaluation_matches_counts(self) -> "ChineseWallEvaluation":
        expected = _decision_from_counts(
            reviewed_adverse=self.reviewed_adverse_pair_count,
            unreviewed=self.unreviewed_pair_count,
            unknown=self.unknown_pair_count,
        )
        if self.decision is not expected:
            raise ValueError("Chinese-wall decision is inconsistent with relation counts")
        if self.local_wall_candidate != (self.decision is WallDecision.same_side_candidate):
            raise ValueError("Chinese-wall local candidate flag is inconsistent")
        return self


def evaluate_chinese_wall(
    request: ChineseWallRequest | dict[str, Any],
) -> ChineseWallEvaluation:
    parsed = parse_chinese_wall_request(request)
    counts = {relationship: 0 for relationship in AdversityRelationship}
    for provenance_class_id in parsed.lesson_provenance_class_ids:
        for consuming_class_id in parsed.consuming_matter_class_ids:
            relationship = adversity_relationship(
                parsed.adversity_graph,
                provenance_class_id,
                consuming_class_id,
            )
            counts[relationship] += 1
    decision = _decision_from_counts(
        reviewed_adverse=counts[AdversityRelationship.reviewed_adverse],
        unreviewed=counts[AdversityRelationship.unreviewed_hold],
        unknown=counts[AdversityRelationship.unknown_hold],
    )
    return ChineseWallEvaluation(
        decision=decision,
        local_wall_candidate=decision is WallDecision.same_side_candidate,
        same_side_pair_count=counts[AdversityRelationship.same_side],
        reviewed_adverse_pair_count=counts[AdversityRelationship.reviewed_adverse],
        unreviewed_pair_count=counts[AdversityRelationship.unreviewed_hold],
        unknown_pair_count=counts[AdversityRelationship.unknown_hold],
        synthetic_firm_wide_imputation_applied=True,
        trusted_synthetic_provenance_snapshot_pinned=True,
        authoritative_firm_wide_imputation_verified=False,
    )


def parse_chinese_wall_request(
    request: ChineseWallRequest | dict[str, Any],
) -> ChineseWallRequest:
    if isinstance(request, ChineseWallRequest):
        return request
    return ChineseWallRequest.model_validate_json(
        json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )


def _decision_from_counts(*, reviewed_adverse: int, unreviewed: int, unknown: int) -> WallDecision:
    if reviewed_adverse:
        return WallDecision.cross_wall_block
    if unreviewed:
        return WallDecision.unreviewed_edge_hold
    if unknown:
        return WallDecision.unknown_relation_hold
    return WallDecision.same_side_candidate


def _synthetic_provenance_snapshot_digest(
    lesson_id: str,
    provenance_class_ids: tuple[str, ...],
) -> str:
    payload = {
        "lesson_id": lesson_id,
        "provenance_class_ids": sorted(provenance_class_ids),
        "scope": "synthetic_firm_wide_fixture",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + sha256(canonical.encode("ascii")).hexdigest()


def _trusted_case_manifest_digest() -> str:
    cases = [
        {
            "request_id": request_id,
            "lesson_id": values[0],
            "provenance": list(values[1]),
            "consumer": list(values[2]),
        }
        for request_id, values in sorted(_TRUSTED_SYNTHETIC_CASES.items())
    ]
    payload = {
        "graph_digest": TRUSTED_SYNTHETIC_ADVERSITY_GRAPH_DIGEST,
        "cases": cases,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + sha256(canonical.encode("ascii")).hexdigest()
