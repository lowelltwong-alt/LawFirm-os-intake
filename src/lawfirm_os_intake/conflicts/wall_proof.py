"""Sanitized Chinese-wall proof artifacts that remain blocked pending owner authority."""

from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .adversity_graph import adversity_graph_digest
from .chinese_wall import (
    ChineseWallEvaluation,
    ChineseWallRequest,
    WallDecision,
    evaluate_chinese_wall,
    parse_chinese_wall_request,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WallBlockingReason(str, Enum):
    cross_wall_detected = "cross_wall_detected"
    unreviewed_edge_hold = "unreviewed_edge_hold"
    unknown_relation_hold = "unknown_relation_hold"
    authoritative_firm_wide_imputation_not_verified = (
        "authoritative_firm_wide_imputation_not_verified"
    )
    counsel_adversity_classes_not_authoritative = "counsel_adversity_classes_not_authoritative"
    authenticated_human_conflicts_review_not_verified = (
        "authenticated_human_conflicts_review_not_verified"
    )
    owning_repo_review_not_verified = "owning_repo_review_not_verified"


class ChineseWallProof(_StrictModel):
    proof_id: str = Field(pattern=r"^chinesewallproof_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    lesson_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    safe_output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    adversity_graph_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provenance_class_set_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    consuming_class_set_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sensitive_request_digest_included: Literal[False] = False
    class_ids_included: Literal[False] = False
    candidate_only: Literal[True] = True
    local_evaluation: ChineseWallEvaluation
    blocking_reasons: tuple[WallBlockingReason, ...] = Field(min_length=1)
    guarantee: Literal["brewer_nash_synthetic_policy_check"] = "brewer_nash_synthetic_policy_check"
    formal_conflict_clearance_guarantee_claimed: Literal[False] = False
    overall_status: Literal["blocked"] = "blocked"
    synthetic_firm_wide_imputation_applied: Literal[True] = True
    trusted_synthetic_provenance_snapshot_pinned: Literal[True] = True
    authoritative_firm_wide_imputation_verified: Literal[False] = False
    counsel_adversity_classes_authority_verified: Literal[False] = False
    authenticated_human_conflicts_review_verified: Literal[False] = False
    owning_repo_review_verified: Literal[False] = False
    actual_lesson_fire_authorized: Literal[False] = False
    lesson_fire_performed: Literal[False] = False
    conflict_clearance_asserted: Literal[False] = False
    exception_lake_write_performed: Literal[False] = False
    external_action_performed: Literal[False] = False
    auto_promotion_performed: Literal[False] = False
    legal_or_compliance_authority_exercised: Literal[False] = False
    support_ids_included: Literal[False] = False
    free_text_included: Literal[False] = False

    @model_validator(mode="after")
    def proof_is_bound_and_permanently_nonfiring(self) -> "ChineseWallProof":
        if _safe_output_digest(_proof_safe_payload(self)) != self.safe_output_digest:
            raise ValueError("Chinese-wall safe output digest is inconsistent")
        if self.proof_id != _proof_id(self.safe_output_digest):
            raise ValueError("Chinese-wall proof ID does not match safe output digest")
        if self.blocking_reasons != _blocking_reasons(self.local_evaluation):
            raise ValueError("Chinese-wall proof blocking reasons are inconsistent")
        if (
            self.synthetic_firm_wide_imputation_applied
            != self.local_evaluation.synthetic_firm_wide_imputation_applied
        ):
            raise ValueError("Chinese-wall imputation evidence is inconsistent")
        if (
            self.authoritative_firm_wide_imputation_verified
            != self.local_evaluation.authoritative_firm_wide_imputation_verified
        ):
            raise ValueError("Chinese-wall authoritative imputation evidence is inconsistent")
        return self


class ChineseWallViolationCandidate(_StrictModel):
    candidate_id: str = Field(pattern=r"^chinesewallviolation_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    proof_id: str = Field(pattern=r"^chinesewallproof_[0-9a-f]{20}$")
    proof_safe_output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reason_code: Literal["synthetic_chinese_wall_violation_candidate"]
    reviewed_adverse_pair_count: int = Field(ge=1)
    candidate_only: Literal[True] = True
    human_review_required: Literal[True] = True
    exception_lake_write_performed: Literal[False] = False
    external_action_performed: Literal[False] = False
    class_ids_included: Literal[False] = False
    free_text_included: Literal[False] = False


def build_chinese_wall_proof(
    request: ChineseWallRequest | dict[str, Any],
) -> ChineseWallProof:
    """Build local synthetic wall evidence; never clear a conflict or fire a lesson."""
    parsed = parse_chinese_wall_request(request)
    evaluation = evaluate_chinese_wall(parsed)
    safe_payload = {
        "request_id": parsed.request_id,
        "lesson_id": parsed.lesson_id,
        "adversity_graph_digest": adversity_graph_digest(parsed.adversity_graph),
        "provenance_class_set_digest": _class_set_digest(parsed.lesson_provenance_class_ids),
        "consuming_class_set_digest": _class_set_digest(parsed.consuming_matter_class_ids),
        "local_evaluation": evaluation.model_dump(mode="json"),
        "blocking_reasons": [reason.value for reason in _blocking_reasons(evaluation)],
        "guarantee": "brewer_nash_synthetic_policy_check",
    }
    safe_output_digest = _safe_output_digest(safe_payload)
    return ChineseWallProof(
        proof_id=_proof_id(safe_output_digest),
        request_id=parsed.request_id,
        lesson_id=parsed.lesson_id,
        safe_output_digest=safe_output_digest,
        adversity_graph_digest=safe_payload["adversity_graph_digest"],
        provenance_class_set_digest=safe_payload["provenance_class_set_digest"],
        consuming_class_set_digest=safe_payload["consuming_class_set_digest"],
        local_evaluation=evaluation,
        blocking_reasons=_blocking_reasons(evaluation),
    )


def build_chinese_wall_violation_candidate(
    proof: ChineseWallProof,
) -> ChineseWallViolationCandidate | None:
    if proof.local_evaluation.decision is not WallDecision.cross_wall_block:
        return None
    candidate_suffix = sha256(proof.proof_id.encode("ascii")).hexdigest()[:20]
    return ChineseWallViolationCandidate(
        candidate_id=f"chinesewallviolation_{candidate_suffix}",
        request_id=proof.request_id,
        proof_id=proof.proof_id,
        proof_safe_output_digest=proof.safe_output_digest,
        reason_code="synthetic_chinese_wall_violation_candidate",
        reviewed_adverse_pair_count=proof.local_evaluation.reviewed_adverse_pair_count,
    )


def chinese_wall_request_digest(request: ChineseWallRequest | dict[str, Any]) -> str:
    parsed = parse_chinese_wall_request(request)
    return (
        "sha256:"
        + sha256(_canonical_json(parsed.model_dump(mode="json")).encode("ascii")).hexdigest()
    )


def _blocking_reasons(
    evaluation: ChineseWallEvaluation,
) -> tuple[WallBlockingReason, ...]:
    reasons: list[WallBlockingReason] = []
    if evaluation.decision is WallDecision.cross_wall_block:
        reasons.append(WallBlockingReason.cross_wall_detected)
    elif evaluation.decision is WallDecision.unreviewed_edge_hold:
        reasons.append(WallBlockingReason.unreviewed_edge_hold)
    elif evaluation.decision is WallDecision.unknown_relation_hold:
        reasons.append(WallBlockingReason.unknown_relation_hold)
    reasons.extend(
        (
            WallBlockingReason.authoritative_firm_wide_imputation_not_verified,
            WallBlockingReason.counsel_adversity_classes_not_authoritative,
            WallBlockingReason.authenticated_human_conflicts_review_not_verified,
            WallBlockingReason.owning_repo_review_not_verified,
        )
    )
    return tuple(reasons)


def _proof_safe_payload(proof: ChineseWallProof) -> dict[str, Any]:
    return {
        "request_id": proof.request_id,
        "lesson_id": proof.lesson_id,
        "adversity_graph_digest": proof.adversity_graph_digest,
        "provenance_class_set_digest": proof.provenance_class_set_digest,
        "consuming_class_set_digest": proof.consuming_class_set_digest,
        "local_evaluation": proof.local_evaluation.model_dump(mode="json"),
        "blocking_reasons": [reason.value for reason in proof.blocking_reasons],
        "guarantee": proof.guarantee,
    }


def _class_set_digest(class_ids: tuple[str, ...]) -> str:
    return _safe_output_digest(sorted(class_ids))


def _safe_output_digest(payload: Any) -> str:
    return "sha256:" + sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _proof_id(safe_output_digest: str) -> str:
    return "chinesewallproof_" + sha256(safe_output_digest.encode("ascii")).hexdigest()[:20]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
