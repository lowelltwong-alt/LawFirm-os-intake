"""Candidate-only IFC crossing evidence with no outbox or external side effects."""

from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lawfirm_os_intake.lessons import (
    LessonDisclosureProof,
    LessonDisclosureRequest,
    build_lesson_disclosure_proof,
    lesson_disclosure_request_digest,
)

from .label_lattice import SensitivityLabel, is_candidate_crossing_label, join_labels
from .residue_scanner import ResidueScanResult, scan_residue


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CrossingRequest(_StrictModel):
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    data_class: Literal["synthetic_fixture"]
    runtime_scope: Literal["synthetic_candidate"]
    candidate_only: Literal[True]
    lesson_disclosure_proof: LessonDisclosureProof
    lesson_disclosure_request: LessonDisclosureRequest
    content_labels: tuple[SensitivityLabel, ...] = Field(min_length=1)
    contains_real_data: Literal[False]
    contains_private_data: Literal[False]
    contains_client_data: Literal[False]
    contains_matter_data: Literal[False]
    contains_real_carrier_data: Literal[False]
    contains_privileged_content: Literal[False]
    contains_work_product: Literal[False]
    scope_known: Literal[True]

    @model_validator(mode="after")
    def request_is_synthetic_only(self) -> "CrossingRequest":
        if not self.request_id.strip():
            raise ValueError("crossing request ID must not be blank")
        if len(set(self.content_labels)) != len(self.content_labels):
            raise ValueError("crossing request content labels must be unique")
        rebuilt = build_lesson_disclosure_proof(
            self.lesson_disclosure_request,
            generated_at=self.lesson_disclosure_proof.generated_at,
        )
        if rebuilt != self.lesson_disclosure_proof:
            raise ValueError("crossing request QRD proof does not match its rebuilt request")
        return self


class LatticeEvidence(_StrictModel):
    source_labels: tuple[SensitivityLabel, ...] = Field(min_length=1)
    effective_label: SensitivityLabel
    candidate_crossing_max: Literal[SensitivityLabel.candidate] = SensitivityLabel.candidate
    label_within_candidate_boundary: bool

    @model_validator(mode="after")
    def lattice_evidence_is_consistent(self) -> "LatticeEvidence":
        if len(set(self.source_labels)) != len(self.source_labels):
            raise ValueError("crossing lattice source labels must be unique")
        if join_labels(self.source_labels) is not self.effective_label:
            raise ValueError("crossing lattice effective label is inconsistent")
        if self.label_within_candidate_boundary != is_candidate_crossing_label(
            self.effective_label
        ):
            raise ValueError("crossing lattice boundary flag is inconsistent")
        return self


class QRDBindingEvidence(_StrictModel):
    lesson_disclosure_proof_id: str = Field(pattern=r"^lessondisclosureproof_[0-9a-f]{20}$")
    lesson_disclosure_safe_output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    local_mechanism_candidate: bool
    disclosure_status: Literal["blocked", "suppressed", "candidate"]
    authoritative_publication_snapshot_verified: Literal[False]
    authenticated_human_disclosure_review_verified: Literal[False]
    actual_qrd_crossing_authorized: Literal[False] = False


class CrossingBlockingReason(str, Enum):
    residue_detected = "residue_detected"
    label_above_candidate = "label_above_candidate"
    qrd_disclosure_not_candidate = "qrd_disclosure_not_candidate"
    qrd_publication_snapshot_not_authoritative = "qrd_publication_snapshot_not_authoritative"
    qrd_human_review_not_authenticated = "qrd_human_review_not_authenticated"
    dad_receiver_schema_not_authoritative = "dad_receiver_schema_not_authoritative"
    human_crossing_review_not_authenticated = "human_crossing_review_not_authenticated"
    owning_repo_review_not_verified = "owning_repo_review_not_verified"


class CrossingProof(_StrictModel):
    proof_id: str = Field(pattern=r"^crossingproof_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^synthetic-[a-z0-9-]+$")
    safe_output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sensitive_crossing_request_digest_included: Literal[False] = False
    candidate_only: Literal[True] = True
    local_scanner_evidence: ResidueScanResult
    local_lattice_evidence: LatticeEvidence
    local_scanner_and_lattice_candidate: bool
    qrd_binding: QRDBindingEvidence
    blocking_reasons: tuple[CrossingBlockingReason, ...] = Field(min_length=1)
    guarantee: Literal["deterministic_declared_pattern_residue_check"] = (
        "deterministic_declared_pattern_residue_check"
    )
    formal_noninterference_guarantee_claimed: Literal[False] = False
    overall_status: Literal["blocked"] = "blocked"
    actual_crossing_asserted: Literal[False] = False
    dad_receiver_schema_authority_verified: Literal[False] = False
    authenticated_human_crossing_review_verified: Literal[False] = False
    owning_repo_review_verified: Literal[False] = False
    outbox_mutation_performed: Literal[False] = False
    send_performed: Literal[False] = False
    dad_contact_performed: Literal[False] = False
    network_access_performed: Literal[False] = False
    sibling_write_performed: Literal[False] = False
    auto_promotion_performed: Literal[False] = False
    legal_or_compliance_authority_exercised: Literal[False] = False
    support_ids_included: Literal[False] = False
    original_rare_values_included: Literal[False] = False
    free_text_included: Literal[False] = False
    prohibited_text_included: Literal[False] = False

    @model_validator(mode="after")
    def proof_is_permanently_non_crossing(self) -> "CrossingProof":
        if _safe_output_digest(_proof_safe_payload(self)) != self.safe_output_digest:
            raise ValueError("crossing safe output digest is inconsistent")
        expected_id = _proof_id(self.safe_output_digest)
        if self.proof_id != expected_id:
            raise ValueError("crossing proof ID does not match its safe output digest")
        local_candidate = (
            self.local_scanner_evidence.clean
            and self.local_lattice_evidence.label_within_candidate_boundary
        )
        if self.local_scanner_and_lattice_candidate != local_candidate:
            raise ValueError("crossing local scanner/lattice candidate flag is inconsistent")
        expected_reasons = _blocking_reasons(
            self.local_scanner_evidence,
            self.local_lattice_evidence,
            self.qrd_binding,
        )
        if self.blocking_reasons != expected_reasons:
            raise ValueError("crossing proof blocking reasons are inconsistent")
        return self


def build_crossing_proof(request: CrossingRequest | dict[str, Any]) -> CrossingProof:
    """Build local IFC evidence; this function never authorizes or performs a crossing."""
    parsed = _parse_request(request)
    effective_label = join_labels(parsed.content_labels)
    qrd_proof = parsed.lesson_disclosure_proof
    scanner_evidence = scan_residue(
        _structured_string_tokens(qrd_proof.model_dump(mode="json")),
        classify_as_free_text=False,
        scope_confirmed_synthetic=True,
    )
    lattice_evidence = LatticeEvidence(
        source_labels=tuple(sorted(parsed.content_labels, key=lambda label: label.value)),
        effective_label=effective_label,
        label_within_candidate_boundary=is_candidate_crossing_label(effective_label),
    )
    qrd_binding = QRDBindingEvidence(
        lesson_disclosure_proof_id=qrd_proof.proof_id,
        lesson_disclosure_safe_output_digest=qrd_proof.safe_output_digest,
        local_mechanism_candidate=qrd_proof.local_mechanism_candidate,
        disclosure_status=qrd_proof.status,
        authoritative_publication_snapshot_verified=(
            qrd_proof.differencing_check.authoritative_publication_snapshot_verified
        ),
        authenticated_human_disclosure_review_verified=(
            qrd_proof.authenticated_human_disclosure_review_verified
        ),
    )
    blocking_reasons = _blocking_reasons(scanner_evidence, lattice_evidence, qrd_binding)
    safe_payload = {
        "request_id": parsed.request_id,
        "local_scanner_evidence": scanner_evidence.model_dump(mode="json"),
        "local_lattice_evidence": lattice_evidence.model_dump(mode="json"),
        "local_scanner_and_lattice_candidate": scanner_evidence.clean
        and lattice_evidence.label_within_candidate_boundary,
        "qrd_binding": qrd_binding.model_dump(mode="json"),
        "blocking_reasons": [reason.value for reason in blocking_reasons],
        "guarantee": "deterministic_declared_pattern_residue_check",
    }
    safe_output_digest = _safe_output_digest(safe_payload)
    return CrossingProof(
        proof_id=_proof_id(safe_output_digest),
        request_id=parsed.request_id,
        safe_output_digest=safe_output_digest,
        local_scanner_evidence=scanner_evidence,
        local_lattice_evidence=lattice_evidence,
        local_scanner_and_lattice_candidate=(
            scanner_evidence.clean and lattice_evidence.label_within_candidate_boundary
        ),
        qrd_binding=qrd_binding,
        blocking_reasons=blocking_reasons,
    )


def crossing_request_digest(request: CrossingRequest | dict[str, Any]) -> str:
    """Hash canonical request material without placing it in the crossing proof."""
    parsed = _parse_request(request)
    payload = {
        "request_id": parsed.request_id,
        "lesson_disclosure_proof_id": parsed.lesson_disclosure_proof.proof_id,
        "lesson_disclosure_safe_output_digest": parsed.lesson_disclosure_proof.safe_output_digest,
        "lesson_disclosure_request_digest": lesson_disclosure_request_digest(
            parsed.lesson_disclosure_request
        ),
        "content_labels": sorted(label.name for label in parsed.content_labels),
        "scope_flags": {
            "contains_real_data": parsed.contains_real_data,
            "contains_private_data": parsed.contains_private_data,
            "contains_client_data": parsed.contains_client_data,
            "contains_matter_data": parsed.contains_matter_data,
            "contains_real_carrier_data": parsed.contains_real_carrier_data,
            "contains_privileged_content": parsed.contains_privileged_content,
            "contains_work_product": parsed.contains_work_product,
            "scope_known": parsed.scope_known,
        },
    }
    return "sha256:" + sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _parse_request(request: CrossingRequest | dict[str, Any]) -> CrossingRequest:
    if isinstance(request, CrossingRequest):
        return request
    return CrossingRequest.model_validate_json(
        json.dumps(
            request,
            default=lambda value: value.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )


def _structured_string_tokens(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(token for item in value.values() for token in _structured_string_tokens(item))
    if isinstance(value, (list, tuple)):
        return tuple(token for item in value for token in _structured_string_tokens(item))
    return ()


def _blocking_reasons(
    scanner_evidence: ResidueScanResult,
    lattice_evidence: LatticeEvidence,
    qrd_binding: QRDBindingEvidence,
) -> tuple[CrossingBlockingReason, ...]:
    reasons: list[CrossingBlockingReason] = []
    if not scanner_evidence.clean:
        reasons.append(CrossingBlockingReason.residue_detected)
    if not lattice_evidence.label_within_candidate_boundary:
        reasons.append(CrossingBlockingReason.label_above_candidate)
    if qrd_binding.disclosure_status != "candidate":
        reasons.append(CrossingBlockingReason.qrd_disclosure_not_candidate)
    if not qrd_binding.authoritative_publication_snapshot_verified:
        reasons.append(CrossingBlockingReason.qrd_publication_snapshot_not_authoritative)
    if not qrd_binding.authenticated_human_disclosure_review_verified:
        reasons.append(CrossingBlockingReason.qrd_human_review_not_authenticated)
    reasons.extend(
        (
            CrossingBlockingReason.dad_receiver_schema_not_authoritative,
            CrossingBlockingReason.human_crossing_review_not_authenticated,
            CrossingBlockingReason.owning_repo_review_not_verified,
        )
    )
    return tuple(reasons)


def _proof_safe_payload(proof: CrossingProof) -> dict[str, Any]:
    return {
        "request_id": proof.request_id,
        "local_scanner_evidence": proof.local_scanner_evidence.model_dump(mode="json"),
        "local_lattice_evidence": proof.local_lattice_evidence.model_dump(mode="json"),
        "local_scanner_and_lattice_candidate": proof.local_scanner_and_lattice_candidate,
        "qrd_binding": proof.qrd_binding.model_dump(mode="json"),
        "blocking_reasons": [reason.value for reason in proof.blocking_reasons],
        "guarantee": proof.guarantee,
    }


def _safe_output_digest(payload: Any) -> str:
    return "sha256:" + sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _proof_id(safe_output_digest: str) -> str:
    return "crossingproof_" + sha256(safe_output_digest.encode("ascii")).hexdigest()[:20]
