from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .differencing import DifferencingCheck, PublishedLessonProjection, check_differencing
from .generalization_lattice import GeneralizationLattice, GeneralizationStep
from .kanon_universe import ReviewedSyntheticUniverse
from .lesson_ir import (
    AdversaryCapability,
    ContextCode,
    Dimension,
    LessonAtom,
    LessonIR,
    RuleClaimCode,
    SyntheticPolicyPlaceholders,
)
from .privilege_partition import PrivilegePartitionResult, screen_privilege_partition


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


DisclosureStatus = Literal["candidate", "suppressed", "blocked"]
DisclosureGuarantee = Literal["bounded_reident_under_declared_adversary"]
DisclosureRefusalReason = Literal[
    "authoritative_publication_snapshot_not_verified",
    "strategy_atom_blocked_not_generalized",
    "signal_bearing_free_text_blocked",
    "support_count_below_K_support",
    "support_matter_does_not_match_lesson_atoms",
    "published_projection_contains_strategy_atom",
    "published_projection_below_disclosure_policy",
    "unknown_or_invalid_reviewed_universe",
    "generalization_entered_strategy_partition",
    "top_of_lattice_below_K_qual",
    "top_of_lattice_below_sensitive_outcome_diversity",
    "cross_lesson_differencing_below_K_qual",
]
TRUSTED_SYNTHETIC_CONTEXT_DIGEST = (
    "sha256:c6b440e60be46ad0982ffd25de45e43fbc21638d7042aa040c681fff6c731da7"
)
TRUSTED_SYNTHETIC_LESSON_DIGESTS = frozenset(
    {
        "sha256:094ad7065bab81ac18dc623c880a81160126213bcc9243bfda8357ae3bbfbf51",
        "sha256:1aed72b9f8974e30bb46c37d570c11bc64e7e93ea6950f94eaa1426458fd249a",
        "sha256:5aa2c0cd92c1d8b134935347fa598526b339b4d200470c44dbec90f7ceced592",
        "sha256:f3cfe72bdc47f640d6eacf1434b881a2463285ee05ed9e2a462d9553373fb16d",
    }
)
SENSITIVE_OUTCOME_ATTRIBUTE_ID = "synthetic_outcome_code"


class LessonDisclosureRequest(_StrictModel):
    request_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    lesson: LessonIR
    policy: SyntheticPolicyPlaceholders
    lattice: GeneralizationLattice
    universe: ReviewedSyntheticUniverse
    synthetic_lesson_fixture_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    synthetic_context_digest: Literal[
        "sha256:c6b440e60be46ad0982ffd25de45e43fbc21638d7042aa040c681fff6c731da7"
    ]
    publication_snapshot_id: str = Field(min_length=1, pattern=r"^synthetic-[a-z0-9-]+$")
    publication_snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authoritative_publication_snapshot_verified: Literal[False]
    published_lessons: tuple[PublishedLessonProjection, ...]

    @model_validator(mode="after")
    def request_is_bound_to_synthetic_policy_and_universe(self) -> "LessonDisclosureRequest":
        if not self.request_id.strip():
            raise ValueError("lesson disclosure request_id must not be whitespace")
        self.lesson.validate_against_policy(self.policy)
        actual_lesson_digest = synthetic_lesson_fixture_digest(self.lesson)
        if actual_lesson_digest != self.synthetic_lesson_fixture_digest:
            raise ValueError("lesson does not match its synthetic fixture digest")
        if actual_lesson_digest not in TRUSTED_SYNTHETIC_LESSON_DIGESTS:
            raise ValueError("lesson is not present in the pinned synthetic fixture manifest")
        if _synthetic_context_digest(self) != self.synthetic_context_digest:
            raise ValueError(
                "lesson disclosure context does not match the pinned synthetic fixture"
            )
        if (
            published_projection_snapshot_digest(self.published_lessons)
            != self.publication_snapshot_digest
        ):
            raise ValueError("published lesson projections do not match their snapshot digest")
        for strategy_key in self.policy.strategy_atom_keys:
            dimension, value = strategy_key.split(":", maxsplit=1)
            if dimension not in self.lattice.parents:
                raise ValueError("strategy atom key uses an unknown closed dimension")
            if value not in self.lattice.parents[dimension]:
                raise ValueError("strategy atom key uses a value outside the reviewed lattice")
        universe_ids = {matter.matter_id for matter in self.universe.matters}
        if not set(self.lesson.support_matter_ids).issubset(universe_ids):
            raise ValueError(
                "lesson support matter IDs must exist in the reviewed synthetic universe"
            )
        if len({item.lesson_id for item in self.published_lessons}) != len(self.published_lessons):
            raise ValueError("published lesson projection IDs must be unique")
        return self


class LessonAnonymityRecord(_StrictModel):
    anonymity_set: int = Field(ge=0)
    K_qual: int = Field(ge=1)
    support_count: int = Field(ge=1)
    K_support: int = Field(ge=1)
    sensitive_outcome_attribute: Literal["synthetic_outcome_code"] = "synthetic_outcome_code"
    sensitive_outcome_diversity: int = Field(ge=0)
    minimum_sensitive_outcome_diversity: int = Field(ge=1)
    l_diversity_ok: bool


class DifferencingIntersectionSummary(_StrictModel):
    published_lesson_ids: tuple[str, ...]
    anonymity_set: int = Field(ge=1)


class LessonDifferencingRecord(_StrictModel):
    publication_snapshot_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    publication_snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authoritative_publication_snapshot_verified: Literal[False] = False
    published_lesson_count: int = Field(ge=0)
    narrows_below_K: bool
    suppressed: bool
    intersections: tuple[DifferencingIntersectionSummary, ...]
    support_matter_ids_included: Literal[False] = False


class LessonFreeTextLint(_StrictModel):
    signal_bearing_free_text_present: bool
    free_text_included_in_proof: Literal[False] = False
    free_text_consumed_as_signal: Literal[False] = False


class LessonGeneralizationStep(_StrictModel):
    dimension: Dimension
    to_value: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_:-]+$")
    from_value_included: Literal[False] = False


class LessonPrivilegeRecord(_StrictModel):
    strategy_atoms_present: bool
    blocked: bool
    blocking_atom_count: int = Field(ge=0)
    blocking_atom_keys_included: Literal[False] = False


class LessonDisclosureProof(_StrictModel):
    proof_id: str = Field(pattern=r"^lessondisclosureproof_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    safe_output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sensitive_request_digest_included: Literal[False] = False
    lesson_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    status: DisclosureStatus
    refusal_reasons: tuple[DisclosureRefusalReason, ...]
    atoms: tuple[LessonAtom, ...]
    claim_before_code: RuleClaimCode
    claim_after_code: RuleClaimCode
    applies_when: tuple[ContextCode, ...]
    does_not_apply_when: tuple[ContextCode, ...]
    danger_if_misapplied: ContextCode
    anonymity: LessonAnonymityRecord
    generalization_path: tuple[LessonGeneralizationStep, ...]
    privilege_screen: LessonPrivilegeRecord
    differencing_check: LessonDifferencingRecord
    free_text_lint: LessonFreeTextLint
    adversary_model: str = Field(min_length=1, pattern=r"^[a-z0-9_:-]+$")
    adversary_capabilities: tuple[AdversaryCapability, ...] = Field(min_length=1)
    synthetic_context_digest: Literal[
        "sha256:c6b440e60be46ad0982ffd25de45e43fbc21638d7042aa040c681fff6c731da7"
    ]
    trusted_synthetic_context_pinned: Literal[True] = True
    synthetic_lesson_fixture_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trusted_synthetic_lesson_fixture_pinned: Literal[True] = True
    local_mechanism_candidate: bool
    guarantee: DisclosureGuarantee = "bounded_reident_under_declared_adversary"
    formal_privacy_guarantee_claimed: Literal[False] = False
    support_matter_ids_included: Literal[False] = False
    strategy_atoms_generalized: Literal[False] = False
    candidate_only: Literal[True] = True
    human_review_required: Literal[True] = True
    authenticated_human_disclosure_review_verified: Literal[False] = False
    approval_id: None = None
    generated_at: str

    @model_validator(mode="after")
    def proof_is_internally_consistent(self) -> "LessonDisclosureProof":
        if _safe_output_digest(_proof_safe_payload(self)) != self.safe_output_digest:
            raise ValueError("lesson disclosure safe output digest is inconsistent")
        if self.proof_id != _proof_id(self.safe_output_digest):
            raise ValueError("lesson disclosure proof_id does not match its safe output digest")
        l_diversity_ok = (
            self.anonymity.sensitive_outcome_diversity
            >= self.anonymity.minimum_sensitive_outcome_diversity
        )
        if self.anonymity.l_diversity_ok != l_diversity_ok:
            raise ValueError("lesson disclosure l-diversity flag is inconsistent")
        if (
            not self.differencing_check.authoritative_publication_snapshot_verified
            and "authoritative_publication_snapshot_not_verified" not in self.refusal_reasons
        ):
            raise ValueError("lesson disclosure proof omits its publication-snapshot blocker")
        if self.local_mechanism_candidate:
            if not self.atoms:
                raise ValueError("local lesson mechanism candidate requires generalized atoms")
            if self.anonymity.anonymity_set < self.anonymity.K_qual:
                raise ValueError("local lesson mechanism candidate is below K_qual")
            if self.anonymity.support_count < self.anonymity.K_support:
                raise ValueError("local lesson mechanism candidate is below K_support")
            if not self.anonymity.l_diversity_ok:
                raise ValueError("local lesson mechanism candidate fails l-diversity")
            if self.privilege_screen.blocked or self.differencing_check.suppressed:
                raise ValueError("local lesson mechanism candidate fails a disclosure screen")
            if self.free_text_lint.signal_bearing_free_text_present:
                raise ValueError("local lesson mechanism candidate contains free text")
        if self.status == "candidate":
            if self.refusal_reasons:
                raise ValueError("candidate lesson disclosure proof cannot have refusal reasons")
            if not self.atoms:
                raise ValueError("candidate lesson disclosure proof requires generalized atoms")
            if self.anonymity.anonymity_set < self.anonymity.K_qual:
                raise ValueError("candidate lesson disclosure proof is below K_qual")
            if self.anonymity.support_count < self.anonymity.K_support:
                raise ValueError("candidate lesson disclosure proof is below K_support")
            if not self.anonymity.l_diversity_ok:
                raise ValueError("candidate lesson disclosure proof fails claim diversity")
            if self.privilege_screen.blocked:
                raise ValueError("candidate lesson disclosure proof contains strategy atoms")
            if self.differencing_check.suppressed:
                raise ValueError("candidate lesson disclosure proof fails differencing")
            if self.free_text_lint.signal_bearing_free_text_present:
                raise ValueError("candidate lesson disclosure proof contains free text")
            if not self.differencing_check.authoritative_publication_snapshot_verified:
                raise ValueError(
                    "candidate lesson proof lacks an authoritative publication snapshot"
                )
        elif not self.refusal_reasons:
            raise ValueError("suppressed or blocked lesson proof requires refusal reasons")
        return self


def build_lesson_disclosure_proof(
    request: LessonDisclosureRequest | dict,
    *,
    generated_at: str | None = None,
) -> LessonDisclosureProof:
    parsed = (
        request
        if isinstance(request, LessonDisclosureRequest)
        else LessonDisclosureRequest.model_validate(request)
    )
    lesson = parsed.lesson
    policy = parsed.policy
    privilege = screen_privilege_partition(lesson.atoms, policy)
    free_text_present = not lesson.free_text_is_signal_free()
    free_text_lint = LessonFreeTextLint(signal_bearing_free_text_present=free_text_present)
    base_reasons: list[DisclosureRefusalReason] = [
        "authoritative_publication_snapshot_not_verified"
    ]
    if privilege.blocked:
        base_reasons.append("strategy_atom_blocked_not_generalized")
    if free_text_present:
        base_reasons.append("signal_bearing_free_text_blocked")
    if lesson.support_count < policy.k_support:
        base_reasons.append("support_count_below_K_support")

    if privilege.blocked or free_text_present:
        return _build_proof(
            parsed,
            status="blocked",
            reasons=base_reasons,
            atoms=(),
            anonymity_set=0,
            sensitive_outcome_diversity=0,
            generalization_path=(),
            privilege=privilege,
            differencing=_empty_differencing(parsed),
            free_text_lint=free_text_lint,
            generated_at=generated_at,
            local_mechanism_candidate=False,
        )

    try:
        support_match_ids = set(parsed.universe.anonymity_set(lesson.atoms, lattice=parsed.lattice))
        if not set(lesson.support_matter_ids).issubset(support_match_ids):
            return _build_proof(
                parsed,
                status="blocked",
                reasons=[*base_reasons, "support_matter_does_not_match_lesson_atoms"],
                atoms=(),
                anonymity_set=0,
                sensitive_outcome_diversity=0,
                generalization_path=(),
                privilege=privilege,
                differencing=_empty_differencing(parsed),
                free_text_lint=free_text_lint,
                generated_at=generated_at,
                local_mechanism_candidate=False,
            )
        for projection in parsed.published_lessons:
            if screen_privilege_partition(projection.atoms, policy).blocked:
                return _build_proof(
                    parsed,
                    status="blocked",
                    reasons=[*base_reasons, "published_projection_contains_strategy_atom"],
                    atoms=(),
                    anonymity_set=0,
                    sensitive_outcome_diversity=0,
                    generalization_path=(),
                    privilege=privilege,
                    differencing=_empty_differencing(parsed),
                    free_text_lint=free_text_lint,
                    generated_at=generated_at,
                    local_mechanism_candidate=False,
                )
            published_count = len(
                parsed.universe.anonymity_set(projection.atoms, lattice=parsed.lattice)
            )
            published_diversity = parsed.universe.sensitive_outcome_diversity(
                projection.atoms, lattice=parsed.lattice
            )
            if (
                published_count < policy.k_qual
                or published_diversity < policy.minimum_sensitive_outcome_diversity
            ):
                return _build_proof(
                    parsed,
                    status="blocked",
                    reasons=[*base_reasons, "published_projection_below_disclosure_policy"],
                    atoms=(),
                    anonymity_set=0,
                    sensitive_outcome_diversity=0,
                    generalization_path=(),
                    privilege=privilege,
                    differencing=_empty_differencing(parsed),
                    free_text_lint=free_text_lint,
                    generated_at=generated_at,
                    local_mechanism_candidate=False,
                )
        generalized = parsed.lattice.minimal_generalization(
            lesson.atoms,
            parsed.universe,
            policy.k_qual,
            policy.minimum_sensitive_outcome_diversity,
        )
    except ValueError:
        return _build_proof(
            parsed,
            status="blocked",
            reasons=[*base_reasons, "unknown_or_invalid_reviewed_universe"],
            atoms=(),
            anonymity_set=0,
            sensitive_outcome_diversity=0,
            generalization_path=(),
            privilege=privilege,
            differencing=_empty_differencing(parsed),
            free_text_lint=free_text_lint,
            generated_at=generated_at,
            local_mechanism_candidate=False,
        )

    reasons = list(base_reasons)
    generalized_privilege = screen_privilege_partition(generalized.atoms, policy)
    if generalized_privilege.blocked:
        return _build_proof(
            parsed,
            status="blocked",
            reasons=[*base_reasons, "generalization_entered_strategy_partition"],
            atoms=(),
            anonymity_set=0,
            sensitive_outcome_diversity=0,
            generalization_path=(),
            privilege=generalized_privilege,
            differencing=_empty_differencing(parsed),
            free_text_lint=free_text_lint,
            generated_at=generated_at,
            local_mechanism_candidate=False,
        )
    if generalized.suppressed:
        if len(generalized.anonymity_set) < policy.k_qual:
            reasons.append("top_of_lattice_below_K_qual")
        if generalized.sensitive_outcome_diversity < policy.minimum_sensitive_outcome_diversity:
            reasons.append("top_of_lattice_below_sensitive_outcome_diversity")

    differencing_check = check_differencing(
        candidate_atoms=generalized.atoms,
        published_lessons=parsed.published_lessons,
        universe=parsed.universe,
        lattice=parsed.lattice,
        k_qual=policy.k_qual,
    )
    differencing = _summarize_differencing(parsed, differencing_check)
    if differencing.suppressed:
        reasons.append("cross_lesson_differencing_below_K_qual")

    local_mechanism_candidate = reasons == ["authoritative_publication_snapshot_not_verified"]
    return _build_proof(
        parsed,
        status="blocked",
        reasons=reasons,
        atoms=generalized.atoms,
        anonymity_set=len(generalized.anonymity_set),
        sensitive_outcome_diversity=generalized.sensitive_outcome_diversity,
        generalization_path=generalized.path,
        privilege=privilege,
        differencing=differencing,
        free_text_lint=free_text_lint,
        generated_at=generated_at,
        local_mechanism_candidate=local_mechanism_candidate,
    )


def _build_proof(
    request: LessonDisclosureRequest,
    *,
    status: DisclosureStatus,
    reasons: list[DisclosureRefusalReason],
    atoms: tuple[LessonAtom, ...],
    anonymity_set: int,
    sensitive_outcome_diversity: int,
    generalization_path: tuple[GeneralizationStep, ...],
    privilege: PrivilegePartitionResult,
    differencing: LessonDifferencingRecord,
    free_text_lint: LessonFreeTextLint,
    generated_at: str | None,
    local_mechanism_candidate: bool,
) -> LessonDisclosureProof:
    policy = request.policy
    refusal_reasons = tuple(dict.fromkeys(reasons))
    anonymity = LessonAnonymityRecord(
        anonymity_set=anonymity_set,
        K_qual=policy.k_qual,
        support_count=request.lesson.support_count,
        K_support=policy.k_support,
        sensitive_outcome_diversity=sensitive_outcome_diversity,
        minimum_sensitive_outcome_diversity=(policy.minimum_sensitive_outcome_diversity),
        l_diversity_ok=(sensitive_outcome_diversity >= policy.minimum_sensitive_outcome_diversity),
    )
    path = tuple(
        LessonGeneralizationStep(dimension=step.dimension, to_value=step.to_value)
        for step in generalization_path
    )
    privilege_record = LessonPrivilegeRecord(
        strategy_atoms_present=privilege.strategy_atoms_present,
        blocked=privilege.blocked,
        blocking_atom_count=len(privilege.blocking_atom_keys),
    )
    safe_output_digest = _safe_output_digest(
        {
            "request_id": request.request_id,
            "lesson_id": request.lesson.lesson_id,
            "status": status,
            "refusal_reasons": refusal_reasons,
            "atoms": [atom.model_dump(mode="json") for atom in atoms],
            "claim_before_code": request.lesson.claim.before_code,
            "claim_after_code": request.lesson.claim.after_code,
            "applies_when": sorted(request.lesson.applies_when),
            "does_not_apply_when": sorted(request.lesson.does_not_apply_when),
            "danger_if_misapplied": request.lesson.danger_if_misapplied,
            "anonymity": anonymity.model_dump(mode="json"),
            "generalization_path": [item.model_dump(mode="json") for item in path],
            "privilege_screen": privilege_record.model_dump(mode="json"),
            "differencing_check": differencing.model_dump(mode="json"),
            "free_text_lint": free_text_lint.model_dump(mode="json"),
            "adversary_model": policy.adversary_model,
            "adversary_capabilities": sorted(policy.adversary_capabilities),
            "synthetic_context_digest": request.synthetic_context_digest,
            "synthetic_lesson_fixture_digest": request.synthetic_lesson_fixture_digest,
            "local_mechanism_candidate": local_mechanism_candidate,
            "guarantee": "bounded_reident_under_declared_adversary",
        }
    )
    return LessonDisclosureProof(
        proof_id=_proof_id(safe_output_digest),
        request_id=request.request_id,
        safe_output_digest=safe_output_digest,
        lesson_id=request.lesson.lesson_id,
        status=status,
        refusal_reasons=refusal_reasons,
        atoms=atoms,
        claim_before_code=request.lesson.claim.before_code,
        claim_after_code=request.lesson.claim.after_code,
        applies_when=request.lesson.applies_when,
        does_not_apply_when=request.lesson.does_not_apply_when,
        danger_if_misapplied=request.lesson.danger_if_misapplied,
        anonymity=anonymity,
        generalization_path=path,
        privilege_screen=privilege_record,
        differencing_check=differencing,
        free_text_lint=free_text_lint,
        adversary_model=policy.adversary_model,
        adversary_capabilities=tuple(sorted(policy.adversary_capabilities)),
        synthetic_context_digest=request.synthetic_context_digest,
        synthetic_lesson_fixture_digest=request.synthetic_lesson_fixture_digest,
        local_mechanism_candidate=local_mechanism_candidate,
        generated_at=generated_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def _empty_differencing(request: LessonDisclosureRequest) -> LessonDifferencingRecord:
    return LessonDifferencingRecord(
        publication_snapshot_id=request.publication_snapshot_id,
        publication_snapshot_digest=request.publication_snapshot_digest,
        authoritative_publication_snapshot_verified=(
            request.authoritative_publication_snapshot_verified
        ),
        published_lesson_count=len(request.published_lessons),
        narrows_below_K=False,
        suppressed=False,
        intersections=(),
    )


def _summarize_differencing(
    request: LessonDisclosureRequest,
    check: DifferencingCheck,
) -> LessonDifferencingRecord:
    return LessonDifferencingRecord(
        publication_snapshot_id=request.publication_snapshot_id,
        publication_snapshot_digest=request.publication_snapshot_digest,
        authoritative_publication_snapshot_verified=(
            request.authoritative_publication_snapshot_verified
        ),
        published_lesson_count=len(request.published_lessons),
        narrows_below_K=check.narrows_below_k,
        suppressed=check.suppressed,
        intersections=tuple(
            DifferencingIntersectionSummary(
                published_lesson_ids=item.published_lesson_ids,
                anonymity_set=len(item.matter_ids),
            )
            for item in check.intersections
        ),
    )


def lesson_disclosure_request_digest(request: LessonDisclosureRequest | dict) -> str:
    parsed = (
        request
        if isinstance(request, LessonDisclosureRequest)
        else LessonDisclosureRequest.model_validate(request)
    )
    payload = parsed.model_dump(mode="json")
    payload["lesson"]["atoms"] = sorted(
        payload["lesson"]["atoms"], key=lambda atom: atom["dimension"]
    )
    for field in ["applies_when", "does_not_apply_when", "support_matter_ids"]:
        payload["lesson"][field] = sorted(payload["lesson"][field])
    for field in [
        "adversary_capabilities",
        "allowed_claim_codes",
        "allowed_context_codes",
        "strategy_atom_keys",
    ]:
        payload["policy"][field] = sorted(payload["policy"][field])
    payload["universe"]["matters"] = sorted(
        payload["universe"]["matters"], key=lambda matter: matter["matter_id"]
    )
    payload["published_lessons"] = sorted(
        payload["published_lessons"], key=lambda lesson: lesson["lesson_id"]
    )
    for projection in payload["published_lessons"]:
        projection["atoms"] = sorted(projection["atoms"], key=lambda atom: atom["dimension"])
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{sha256(encoded.encode('utf-8')).hexdigest()}"


def published_projection_snapshot_digest(
    published_lessons: tuple[PublishedLessonProjection, ...] | list[dict],
) -> str:
    parsed = tuple(
        item
        if isinstance(item, PublishedLessonProjection)
        else PublishedLessonProjection.model_validate(item)
        for item in published_lessons
    )
    payload = [item.model_dump(mode="json") for item in sorted(parsed, key=lambda x: x.lesson_id)]
    for projection in payload:
        projection["atoms"] = sorted(projection["atoms"], key=lambda atom: atom["dimension"])
    return _safe_output_digest(payload)


def synthetic_lesson_fixture_digest(lesson: LessonIR | dict) -> str:
    parsed = lesson if isinstance(lesson, LessonIR) else LessonIR.model_validate(lesson)
    payload = parsed.model_dump(mode="json")
    payload["atoms"] = sorted(payload["atoms"], key=lambda atom: atom["dimension"])
    for field in ["applies_when", "does_not_apply_when", "support_matter_ids"]:
        payload[field] = sorted(payload[field])
    return _safe_output_digest(payload)


def _synthetic_context_digest(request: LessonDisclosureRequest) -> str:
    payload = {
        "policy": request.policy.model_dump(mode="json"),
        "lattice": request.lattice.model_dump(mode="json"),
        "universe": request.universe.model_dump(mode="json"),
    }
    for field in [
        "adversary_capabilities",
        "allowed_claim_codes",
        "allowed_context_codes",
        "strategy_atom_keys",
    ]:
        payload["policy"][field] = sorted(payload["policy"][field])
    payload["universe"]["matters"] = sorted(
        payload["universe"]["matters"], key=lambda matter: matter["matter_id"]
    )
    return _safe_output_digest(payload)


def _proof_safe_payload(proof: LessonDisclosureProof) -> dict[str, Any]:
    return {
        "request_id": proof.request_id,
        "lesson_id": proof.lesson_id,
        "status": proof.status,
        "refusal_reasons": proof.refusal_reasons,
        "atoms": [atom.model_dump(mode="json") for atom in proof.atoms],
        "claim_before_code": proof.claim_before_code,
        "claim_after_code": proof.claim_after_code,
        "applies_when": sorted(proof.applies_when),
        "does_not_apply_when": sorted(proof.does_not_apply_when),
        "danger_if_misapplied": proof.danger_if_misapplied,
        "anonymity": proof.anonymity.model_dump(mode="json"),
        "generalization_path": [item.model_dump(mode="json") for item in proof.generalization_path],
        "privilege_screen": proof.privilege_screen.model_dump(mode="json"),
        "differencing_check": proof.differencing_check.model_dump(mode="json"),
        "free_text_lint": proof.free_text_lint.model_dump(mode="json"),
        "adversary_model": proof.adversary_model,
        "adversary_capabilities": sorted(proof.adversary_capabilities),
        "synthetic_context_digest": proof.synthetic_context_digest,
        "synthetic_lesson_fixture_digest": proof.synthetic_lesson_fixture_digest,
        "local_mechanism_candidate": proof.local_mechanism_candidate,
        "guarantee": proof.guarantee,
    }


def _safe_output_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{sha256(encoded.encode('utf-8')).hexdigest()}"


def _proof_id(safe_output_digest: str) -> str:
    return "lessondisclosureproof_" + sha256(safe_output_digest.encode("utf-8")).hexdigest()[:20]
