"""Synthetic-only adversity graph primitives with no inferred conflict authority."""

from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EdgeReviewStatus(str, Enum):
    synthetic_fixture_reviewed = "synthetic_fixture_reviewed"
    unreviewed_fixture = "unreviewed_fixture"


class AdversityRelationship(str, Enum):
    same_side = "same_side"
    reviewed_adverse = "reviewed_adverse"
    unreviewed_hold = "unreviewed_hold"
    unknown_hold = "unknown_hold"


class SyntheticConflictClass(_StrictModel):
    class_id: str = Field(pattern=r"^synthetic-coi-class-[a-z0-9-]+$")
    definition_status: Literal["synthetic_policy_placeholder"]
    member_ref_count: int = Field(ge=1)
    member_refs_included: Literal[False] = False
    counsel_classification_authority_verified: Literal[False] = False


class SyntheticAdversityEdge(_StrictModel):
    edge_id: str = Field(pattern=r"^synthetic-adversity-edge-[a-z0-9-]+$")
    class_ids: tuple[str, str] = Field(min_length=2, max_length=2)
    review_status: EdgeReviewStatus
    source_ref: str = Field(pattern=r"^synthetic-policy-ref:[a-z0-9-]+$")
    counsel_adversity_authority_verified: Literal[False] = False
    inferred_from_similarity: Literal[False] = False

    @model_validator(mode="after")
    def edge_is_deterministic_and_nonreflexive(self) -> "SyntheticAdversityEdge":
        if len(set(self.class_ids)) != 2:
            raise ValueError("adversity edge must connect two distinct classes")
        if tuple(sorted(self.class_ids)) != self.class_ids:
            raise ValueError("adversity edge class IDs must be sorted")
        return self


class SyntheticAdversityGraph(_StrictModel):
    graph_id: str = Field(pattern=r"^synthetic-adversity-graph-[a-z0-9-]+$")
    graph_version: Literal["synthetic-policy-placeholder-v1"]
    data_class: Literal["synthetic_fixture"]
    runtime_scope: Literal["synthetic_candidate"]
    candidate_only: Literal[True]
    policy_status: Literal["synthetic_policy_placeholder"]
    conflict_classes: tuple[SyntheticConflictClass, ...] = Field(min_length=2)
    adversity_edges: tuple[SyntheticAdversityEdge, ...]
    firm_wide_imputation_required: Literal[True]
    counsel_adversity_classes_authority_verified: Literal[False]
    adversity_inference_performed: Literal[False]
    contains_real_data: Literal[False]
    contains_private_data: Literal[False]
    contains_client_data: Literal[False]
    contains_matter_data: Literal[False]
    contains_real_carrier_data: Literal[False]
    contains_privileged_content: Literal[False]
    contains_work_product: Literal[False]

    @model_validator(mode="after")
    def graph_is_closed_and_reference_valid(self) -> "SyntheticAdversityGraph":
        class_ids = [item.class_id for item in self.conflict_classes]
        if class_ids != sorted(class_ids):
            raise ValueError("synthetic conflict classes must be sorted by class ID")
        if len(class_ids) != len(set(class_ids)):
            raise ValueError("synthetic conflict class IDs must be unique")
        known = set(class_ids)
        edge_ids: set[str] = set()
        edge_pairs: set[tuple[str, str]] = set()
        for edge in self.adversity_edges:
            if edge.edge_id in edge_ids:
                raise ValueError("synthetic adversity edge IDs must be unique")
            if edge.class_ids in edge_pairs:
                raise ValueError("synthetic adversity class pairs must be unique")
            if not set(edge.class_ids).issubset(known):
                raise ValueError("synthetic adversity edge references an unknown class")
            edge_ids.add(edge.edge_id)
            edge_pairs.add(edge.class_ids)
        return self


def adversity_relationship(
    graph: SyntheticAdversityGraph,
    left_class_id: str,
    right_class_id: str,
) -> AdversityRelationship:
    """Return only exact declared relationships; never infer or auto-clear adversity."""
    known = {item.class_id for item in graph.conflict_classes}
    if left_class_id not in known or right_class_id not in known:
        return AdversityRelationship.unknown_hold
    if left_class_id == right_class_id:
        return AdversityRelationship.same_side
    pair = tuple(sorted((left_class_id, right_class_id)))
    edge = next((item for item in graph.adversity_edges if item.class_ids == pair), None)
    if edge is None:
        return AdversityRelationship.unknown_hold
    if edge.review_status is EdgeReviewStatus.synthetic_fixture_reviewed:
        return AdversityRelationship.reviewed_adverse
    return AdversityRelationship.unreviewed_hold


def adversity_graph_digest(graph: SyntheticAdversityGraph | dict[str, Any]) -> str:
    parsed = (
        graph
        if isinstance(graph, SyntheticAdversityGraph)
        else SyntheticAdversityGraph.model_validate_json(_canonical_json(graph))
    )
    return (
        "sha256:"
        + sha256(_canonical_json(parsed.model_dump(mode="json")).encode("ascii")).hexdigest()
    )


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
