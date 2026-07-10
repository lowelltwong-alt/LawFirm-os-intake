from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .calibration import (
    CalibrationLeakageProof,
    CalibrationPreflightRequest,
    build_calibration_leakage_proof,
)
from .conflicts import (
    ChineseWallProof,
    ChineseWallRequest,
    WallDecision,
    build_chinese_wall_proof,
    chinese_wall_request_digest,
)
from .lessons import (
    LessonDisclosureProof,
    LessonDisclosureRequest,
    build_lesson_disclosure_proof,
    lesson_disclosure_request_digest,
)
from .models import (
    BudgetActualComparisonReport,
    BudgetActualVarianceDriverCandidate,
    BudgetRevisionDelta,
    BudgetRevisionReport,
    CarrierRejectionLearningProposal,
    CarrierRejectionLearningReport,
    ReviewedLearningGateCandidate,
    ReviewedLearningGateCheck,
    ReviewedLearningGateReport,
)
from .outbox import (
    CrossingProof,
    CrossingRequest,
    build_crossing_proof,
    crossing_request_digest,
)
from .util import append_jsonl, digest_text, load_json, new_id, now_iso, write_json


REVIEWED_LEARNING_GATE_REPORT_FILENAME = "reviewed_learning_gate_report.json"
REVIEWED_LEARNING_GATE_NOTES_FILENAME = "reviewed_learning_gate_report.md"
REVIEWED_LEARNING_GATE_CANDIDATES_FILENAME = "reviewed_learning_gate_candidates.jsonl"

REQUIRED_NEXT_GATES = [
    "human_reviewed_outcome_evidence",
    "append_only_evidence_record",
    "synthetic_fixture_update",
    "shadow_eval",
    "owning_repo_review",
]

CARRIER_LESSON_REQUIRED_NEXT_GATES = [
    *REQUIRED_NEXT_GATES,
    "lesson_disclosure_proof_before_cross_repo_review",
    "chinese_wall_proof_before_lesson_firing",
]

CALIBRATION_LEAKAGE_PROOF_REQUIRED_GATES = [
    "valid_calibration_leakage_proof",
    "external_request_digest_anchor",
    "external_dp_release_digest_anchor_for_dp_path",
    "authoritative_zcdp_ledger_receipt_for_dp_path",
    "governed_secret_seed_authority_for_dp_path",
    "approval_evidence_identifier_shape_only",
    "owning_repo_review",
    "no_calibrated_value_publication_from_intake",
]

LESSON_DISCLOSURE_PROOF_REQUIRED_GATES = [
    "valid_lesson_disclosure_proof",
    "external_lesson_request_digest_anchor",
    "bounded_reident_under_declared_adversary_only",
    "authenticated_human_disclosure_review",
    "owning_repo_review",
    "no_lesson_publication_or_dad_crossing_from_intake",
]

CROSSING_PROOF_REQUIRED_GATES = [
    "valid_crossing_proof",
    "external_crossing_request_digest_anchor",
    "valid_bound_lesson_disclosure_proof",
    "deterministic_declared_pattern_check_not_formal_noninterference",
    "scanner_clean_and_label_at_most_candidate",
    "dad_receiver_schema_authority",
    "authenticated_human_crossing_review",
    "owning_repo_review",
    "no_send_outbox_write_or_dad_contact_from_intake",
]

CHINESE_WALL_PROOF_REQUIRED_GATES = [
    "valid_chinese_wall_proof",
    "external_chinese_wall_request_digest_anchor",
    "reviewed_adversity_edges_only_no_inference",
    "pinned_synthetic_firm_wide_provenance_snapshot",
    "authoritative_firm_wide_imputation",
    "counsel_adversity_class_authority",
    "authenticated_human_conflicts_review",
    "owning_repo_review",
    "no_lesson_fire_conflict_clearance_or_lake_write_from_intake",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _carrier_candidate(
    *,
    proposal: CarrierRejectionLearningProposal,
    report: CarrierRejectionLearningReport,
    report_ref: str,
) -> ReviewedLearningGateCandidate:
    return ReviewedLearningGateCandidate(
        candidate_id=_stable_id("learninggate", f"{report_ref}|{proposal.proposal_id}"),
        source_kind="carrier_rejection_learning_proposal",
        source_artifact_ref=report_ref,
        source_record_id=proposal.proposal_id,
        source_status=proposal.status,
        target_learning_loop=proposal.target_learning_loop,
        target_owner=proposal.target_owner,
        trigger_summary=(
            f"Carrier rejection learning proposal {proposal.proposal_type} "
            f"from report {report.learning_report_id}."
        ),
        before_behavior=proposal.before_behavior,
        proposed_candidate_behavior=proposal.proposed_candidate_behavior,
        support_refs=[
            report_ref,
            f"carrier-rejection-learning-report://{report.learning_report_id}",
            *proposal.source_structured_refs,
        ],
        support_count=proposal.support_count,
        required_evidence=[
            "human-reviewed rejection or appeal outcome",
            "append-only Exception Lake admission candidate",
            "source/support hashes from Orchestrator evidence packet",
        ],
        required_evaluation=list(
            dict.fromkeys(
                [
                    *proposal.required_evaluation,
                    "synthetic fixture update",
                    "shadow eval before promotion",
                    "regression check against no-silent-learning boundary",
                ]
            )
        ),
        required_next_gates=CARRIER_LESSON_REQUIRED_NEXT_GATES,
    )


def _loop_for_budget_revision(delta: BudgetRevisionDelta) -> tuple[str, str, str]:
    if delta.field == "hourly_rate":
        return (
            "timekeeper_rate",
            "LawFirm-os-intake",
            "Review whether a named-timekeeper or role-rate candidate should be proposed.",
        )
    if delta.field == "estimated_expenses":
        return (
            "budget_model",
            "LawFirm-os-intake",
            "Review whether expense drivers, ranges, or preapproval warnings should change.",
        )
    if delta.field == "estimated_hours":
        return (
            "budget_model",
            "LawFirm-os-intake",
            "Review whether phase/task hours, range drivers, or scenario assumptions should change.",
        )
    return (
        "validation_rule",
        "LawFirm-os-intake",
        "Review whether assumption or unknown handling needs a candidate validation rule.",
    )


def _revision_candidate(
    *,
    delta: BudgetRevisionDelta,
    report: BudgetRevisionReport,
    report_ref: str,
) -> ReviewedLearningGateCandidate:
    target_loop, owner, proposed_behavior = _loop_for_budget_revision(delta)
    target = "/".join(
        item
        for item in [
            delta.phase_id,
            delta.task_id,
            delta.external_code_candidate or delta.expense_code,
            delta.staffing_role,
        ]
        if item
    )
    return ReviewedLearningGateCandidate(
        candidate_id=_stable_id("learninggate", f"{report_ref}|{delta.delta_id}"),
        source_kind="budget_revision_delta",
        source_artifact_ref=report_ref,
        source_record_id=delta.delta_id,
        source_status=report.status,
        target_learning_loop=target_loop,  # type: ignore[arg-type]
        target_owner=owner,  # type: ignore[arg-type]
        trigger_summary=(
            f"Human budget review changed {delta.field} for {target or delta.target_type} "
            f"with total delta {delta.total_delta}."
        ),
        before_behavior="Budget proposal used the original deterministic candidate estimate.",
        proposed_candidate_behavior=proposed_behavior,
        support_refs=[
            report_ref,
            f"budget-revision-report://{report.budget_revision_report_id}",
            f"budget-revision-delta://{delta.delta_id}",
            *delta.structured_refs,
        ],
        support_count=1,
        required_evidence=[
            "human budget review outcome",
            "append-only budget revision record",
            "source or structured support for the changed assumption",
        ],
        required_evaluation=[
            "budget driver counterfactual",
            "synthetic fixture update",
            "shadow eval before promotion",
            "regression check against budget mutation",
        ],
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def _loop_for_actual_driver(
    driver: BudgetActualVarianceDriverCandidate,
) -> tuple[str, str, str]:
    if driver.target_learning_loop == "template_mapping":
        return (
            "template_mapping",
            "LawFirm-os-intake",
            "Review whether UTBMS/template mapping or missing-budget validation needs a candidate fixture.",
        )
    if driver.target_learning_loop == "validation_rule":
        return (
            "validation_rule",
            "LawFirm-os-intake",
            "Review whether actuals validation should surface this condition earlier.",
        )
    return (
        "budget_model",
        "LawFirm-os-intake",
        "Review whether budget drivers, ranges, or scenario assumptions explain the variance.",
    )


def _actual_variance_candidate(
    *,
    driver: BudgetActualVarianceDriverCandidate,
    report: BudgetActualComparisonReport,
    report_ref: str,
) -> ReviewedLearningGateCandidate:
    target_loop, owner, proposed_behavior = _loop_for_actual_driver(driver)
    target = driver.code or driver.phase_id or "proposal"
    return ReviewedLearningGateCandidate(
        candidate_id=_stable_id("learninggate", f"{report_ref}|{driver.candidate_id}"),
        source_kind="budget_actual_variance_driver",
        source_artifact_ref=report_ref,
        source_record_id=driver.candidate_id,
        source_status=report.status,
        target_learning_loop=target_loop,  # type: ignore[arg-type]
        target_owner=owner,  # type: ignore[arg-type]
        trigger_summary=(
            f"Budget actual variance driver {driver.driver_label} for {target} "
            f"with variance amount {driver.variance_amount}."
        ),
        before_behavior="Budget-to-actual variance is visible only as review pressure.",
        proposed_candidate_behavior=proposed_behavior,
        support_refs=[
            report_ref,
            f"budget-actual-comparison-report://{report.budget_actual_comparison_report_id}",
            f"budget-actual-variance-driver://{driver.candidate_id}",
            *(
                [f"budget-revision-report://{report.budget_revision_report_id}"]
                if report.budget_revision_report_id
                else []
            ),
        ],
        support_count=1,
        required_evidence=[
            "governed actual-cost source",
            "human-reviewed variance disposition",
            "append-only variance or outcome record",
        ],
        required_evaluation=[
            "actual-vs-budget replay",
            "synthetic fixture update",
            "shadow eval before promotion",
            "regression check against no-silent-learning boundary",
        ],
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def _check(
    check_id: str,
    passed: bool,
    message: str,
    candidate_ids: list[str] | None = None,
) -> ReviewedLearningGateCheck:
    return ReviewedLearningGateCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        candidate_ids=candidate_ids or [],
    )


def validate_lesson_disclosure_gate(
    *,
    lesson_id: str,
    lesson_disclosure_proof: LessonDisclosureProof | dict[str, Any] | None,
    lesson_disclosure_request: LessonDisclosureRequest | dict[str, Any] | None = None,
    expected_lesson_input_digest: str | None = None,
    approval_id: str | None = None,
) -> ReviewedLearningGateCheck:
    """Keep qualitative lesson review closed until proof and real human authority exist."""
    if lesson_disclosure_proof is None:
        return _check(
            "lesson_disclosure_proof_required",
            False,
            "Qualitative lesson candidates require a LessonDisclosureProof.",
        )
    parsed, error = _parse_lesson_disclosure_proof(lesson_disclosure_proof)
    if error is not None or parsed is None:
        return _check(
            "lesson_disclosure_proof_valid",
            False,
            f"LessonDisclosureProof is invalid: {error}",
        )
    if lesson_disclosure_request is None:
        return _check(
            "lesson_disclosure_request_required",
            False,
            "Lesson disclosure review requires the synthetic request for deterministic rebuild.",
            [parsed.proof_id],
        )
    if not _is_sha256_digest(expected_lesson_input_digest):
        return _check(
            "lesson_disclosure_expected_digest_required",
            False,
            "Lesson disclosure review requires an independently supplied sha256 request digest.",
            [parsed.proof_id],
        )
    rebuilt, rebuilt_request_digest, rebuild_error = _rebuild_lesson_disclosure_proof(
        lesson_disclosure_request
    )
    if rebuild_error is not None or rebuilt is None:
        return _check(
            "lesson_disclosure_request_valid",
            False,
            f"Lesson disclosure request is invalid: {rebuild_error}",
            [parsed.proof_id],
        )
    binding_failures = _lesson_proof_request_binding_failures(
        parsed,
        rebuilt,
        rebuilt_request_digest=rebuilt_request_digest,
        expected_lesson_input_digest=expected_lesson_input_digest,
    )
    if binding_failures:
        return _check(
            "lesson_disclosure_proof_request_binding",
            False,
            "Lesson disclosure proof does not match its rebuilt request: "
            + ", ".join(binding_failures),
            [parsed.proof_id],
        )
    failures = _lesson_disclosure_proof_failures(
        parsed,
        lesson_id=lesson_id,
        approval_id=approval_id,
    )
    return _check(
        "lesson_disclosure_proof_promotion_gate",
        not failures,
        (
            "Lesson disclosure evidence is ready for authenticated human and owning-repo review; "
            "this check performs no publication, DAD crossing, promotion, or mutation."
            if not failures
            else "Lesson disclosure proof blocks promotion review: " + ", ".join(failures)
        ),
        [parsed.proof_id],
    )


def _lesson_disclosure_proof_failures(
    proof: LessonDisclosureProof,
    *,
    lesson_id: str,
    approval_id: str | None,
) -> list[str]:
    failures: list[str] = []
    if proof.lesson_id != lesson_id:
        failures.append("lesson_id_mismatch")
    if proof.status != "candidate":
        failures.append(f"status={proof.status}")
    if proof.refusal_reasons:
        failures.append("refusal_reasons_present")
    if proof.guarantee != "bounded_reident_under_declared_adversary":
        failures.append("invalid_guarantee_label")
    if proof.formal_privacy_guarantee_claimed:
        failures.append("formal_privacy_guarantee_claimed")
    if proof.privilege_screen.blocked:
        failures.append("strategy_or_privilege_atom_present")
    if proof.differencing_check.suppressed:
        failures.append("cross_lesson_differencing_failed")
    if not proof.differencing_check.authoritative_publication_snapshot_verified:
        failures.append("authoritative_publication_snapshot_not_verified")
    if proof.free_text_lint.signal_bearing_free_text_present:
        failures.append("signal_bearing_free_text_present")
    if proof.anonymity.anonymity_set < proof.anonymity.K_qual:
        failures.append("anonymity_set_below_K_qual")
    if proof.anonymity.support_count < proof.anonymity.K_support:
        failures.append("support_count_below_K_support")
    if not proof.anonymity.l_diversity_ok:
        failures.append("sensitive_outcome_diversity_not_met")
    if not _approval_id_has_candidate_evidence_shape(approval_id):
        failures.append("missing_approval_id")
    if not proof.authenticated_human_disclosure_review_verified:
        failures.append("authenticated_human_disclosure_review_not_verified")
    return failures


def _parse_lesson_disclosure_proof(
    proof: LessonDisclosureProof | dict[str, Any],
) -> tuple[LessonDisclosureProof | None, str | None]:
    try:
        payload = (
            proof.model_dump(mode="json") if isinstance(proof, LessonDisclosureProof) else proof
        )
        return LessonDisclosureProof.model_validate(payload), None
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"]


def _rebuild_lesson_disclosure_proof(
    request: LessonDisclosureRequest | dict[str, Any],
) -> tuple[LessonDisclosureProof | None, str | None, str | None]:
    try:
        payload = (
            request.model_dump(mode="json")
            if isinstance(request, LessonDisclosureRequest)
            else request
        )
        parsed = LessonDisclosureRequest.model_validate(payload)
        return (
            build_lesson_disclosure_proof(parsed),
            lesson_disclosure_request_digest(parsed),
            None,
        )
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            return None, None, exc.errors()[0]["msg"]
        return None, None, str(exc)


def _lesson_proof_request_binding_failures(
    proof: LessonDisclosureProof,
    rebuilt: LessonDisclosureProof,
    *,
    rebuilt_request_digest: str,
    expected_lesson_input_digest: str,
) -> list[str]:
    failures: list[str] = []
    if rebuilt_request_digest != expected_lesson_input_digest:
        failures.append("expected_digest_does_not_match_rebuilt_request")
    if proof.proof_id != rebuilt.proof_id:
        failures.append("proof_id_mismatch")
    proof_payload = proof.model_dump(mode="json", exclude={"generated_at"})
    rebuilt_payload = rebuilt.model_dump(mode="json", exclude={"generated_at"})
    if proof_payload != rebuilt_payload:
        failures.append("proof_content_mismatch")
    return failures


def validate_crossing_gate(
    *,
    request_id: str,
    crossing_proof: CrossingProof | dict[str, Any] | None,
    crossing_request: CrossingRequest | dict[str, Any] | None = None,
    expected_crossing_request_digest: str | None = None,
    approval_id: str | None = None,
) -> ReviewedLearningGateCheck:
    """Keep DAD crossing review closed until bound proof and owner authority exist."""
    if crossing_proof is None:
        return _check(
            "crossing_proof_required",
            False,
            "Proposed lesson crossings require a CrossingProof.",
        )
    parsed, error = _parse_crossing_proof(crossing_proof)
    if error is not None or parsed is None:
        return _check(
            "crossing_proof_valid",
            False,
            f"CrossingProof is invalid: {error}",
        )
    if crossing_request is None:
        return _check(
            "crossing_request_required",
            False,
            "Crossing review requires the synthetic request for deterministic rebuild.",
            [parsed.proof_id],
        )
    if not _is_sha256_digest(expected_crossing_request_digest):
        return _check(
            "crossing_expected_digest_required",
            False,
            "Crossing review requires an independently supplied sha256 request digest.",
            [parsed.proof_id],
        )
    rebuilt, rebuilt_request_digest, rebuild_error = _rebuild_crossing_proof(crossing_request)
    if rebuild_error is not None or rebuilt is None or rebuilt_request_digest is None:
        return _check(
            "crossing_request_valid",
            False,
            f"Crossing request is invalid: {rebuild_error}",
            [parsed.proof_id],
        )
    binding_failures: list[str] = []
    if rebuilt_request_digest != expected_crossing_request_digest:
        binding_failures.append("expected_digest_does_not_match_rebuilt_request")
    if parsed.proof_id != rebuilt.proof_id:
        binding_failures.append("proof_id_mismatch")
    if parsed.model_dump(mode="json") != rebuilt.model_dump(mode="json"):
        binding_failures.append("proof_content_mismatch")
    if binding_failures:
        return _check(
            "crossing_proof_request_binding",
            False,
            "Crossing proof does not match its rebuilt request: " + ", ".join(binding_failures),
            [parsed.proof_id],
        )
    failures = _crossing_proof_failures(
        parsed,
        request_id=request_id,
        approval_id=approval_id,
    )
    return _check(
        "crossing_proof_promotion_gate",
        not failures,
        (
            "Crossing evidence is ready for DAD receiver, authenticated human, and owning-repo review; "
            "this check performs no send, outbox write, DAD contact, promotion, or mutation."
            if not failures
            else "Crossing proof blocks promotion review: " + ", ".join(failures)
        ),
        [parsed.proof_id],
    )


def _parse_crossing_proof(
    proof: CrossingProof | dict[str, Any],
) -> tuple[CrossingProof | None, str | None]:
    try:
        payload = proof.model_dump(mode="json") if isinstance(proof, CrossingProof) else proof
        return CrossingProof.model_validate_json(json.dumps(payload)), None
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"]
    except (TypeError, ValueError):
        return None, "crossing proof is not valid JSON model input"


def _rebuild_crossing_proof(
    request: CrossingRequest | dict[str, Any],
) -> tuple[CrossingProof | None, str | None, str | None]:
    try:
        payload = (
            request.model_dump(mode="json") if isinstance(request, CrossingRequest) else request
        )
        parsed = CrossingRequest.model_validate_json(json.dumps(payload))
        return build_crossing_proof(parsed), crossing_request_digest(parsed), None
    except (ValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            return None, None, exc.errors()[0]["msg"]
        if isinstance(exc, TypeError):
            return None, None, "crossing request is not valid JSON model input"
        return None, None, str(exc)


def _crossing_proof_failures(
    proof: CrossingProof,
    *,
    request_id: str,
    approval_id: str | None,
) -> list[str]:
    failures: list[str] = []
    if proof.request_id != request_id:
        failures.append("request_id_mismatch")
    if proof.overall_status != "candidate":
        failures.append(f"status={proof.overall_status}")
    if not proof.local_scanner_evidence.clean:
        failures.append("prohibited_residue_detected")
    if proof.guarantee != "deterministic_declared_pattern_residue_check":
        failures.append("invalid_crossing_guarantee_label")
    if proof.formal_noninterference_guarantee_claimed:
        failures.append("formal_noninterference_guarantee_claimed")
    if not proof.local_lattice_evidence.label_within_candidate_boundary:
        failures.append("label_above_candidate")
    if not proof.local_scanner_and_lattice_candidate:
        failures.append("local_ifc_mechanism_not_candidate")
    if proof.qrd_binding.disclosure_status != "candidate":
        failures.append("qrd_disclosure_not_candidate")
    if not proof.qrd_binding.authoritative_publication_snapshot_verified:
        failures.append("qrd_publication_snapshot_not_authoritative")
    if not proof.qrd_binding.authenticated_human_disclosure_review_verified:
        failures.append("qrd_human_review_not_authenticated")
    if not proof.dad_receiver_schema_authority_verified:
        failures.append("dad_receiver_schema_not_authoritative")
    if not proof.authenticated_human_crossing_review_verified:
        failures.append("authenticated_human_crossing_review_not_verified")
    if not proof.owning_repo_review_verified:
        failures.append("owning_repo_review_not_verified")
    if not _approval_id_has_candidate_evidence_shape(approval_id):
        failures.append("missing_approval_id")
    return failures


def validate_chinese_wall_gate(
    *,
    lesson_id: str,
    chinese_wall_proof: ChineseWallProof | dict[str, Any] | None,
    chinese_wall_request: ChineseWallRequest | dict[str, Any] | None = None,
    expected_chinese_wall_request_digest: str | None = None,
    approval_id: str | None = None,
) -> ReviewedLearningGateCheck:
    """Keep lesson firing closed until wall evidence and counsel-owned policy exist."""
    if chinese_wall_proof is None:
        return _check(
            "chinese_wall_proof_required",
            False,
            "Proposed lesson firing requires a ChineseWallProof.",
        )
    parsed, error = _parse_chinese_wall_proof(chinese_wall_proof)
    if error is not None or parsed is None:
        return _check(
            "chinese_wall_proof_valid",
            False,
            f"ChineseWallProof is invalid: {error}",
        )
    if chinese_wall_request is None:
        return _check(
            "chinese_wall_request_required",
            False,
            "Chinese-wall review requires the synthetic request for deterministic rebuild.",
            [parsed.proof_id],
        )
    if not _is_sha256_digest(expected_chinese_wall_request_digest):
        return _check(
            "chinese_wall_expected_digest_required",
            False,
            "Chinese-wall review requires an independently supplied sha256 request digest.",
            [parsed.proof_id],
        )
    rebuilt, rebuilt_request_digest, rebuild_error = _rebuild_chinese_wall_proof(
        chinese_wall_request
    )
    if rebuild_error is not None or rebuilt is None or rebuilt_request_digest is None:
        return _check(
            "chinese_wall_request_valid",
            False,
            f"Chinese-wall request is invalid: {rebuild_error}",
            [parsed.proof_id],
        )
    binding_failures: list[str] = []
    if rebuilt_request_digest != expected_chinese_wall_request_digest:
        binding_failures.append("expected_digest_does_not_match_rebuilt_request")
    if parsed.proof_id != rebuilt.proof_id:
        binding_failures.append("proof_id_mismatch")
    if parsed.model_dump(mode="json") != rebuilt.model_dump(mode="json"):
        binding_failures.append("proof_content_mismatch")
    if binding_failures:
        return _check(
            "chinese_wall_proof_request_binding",
            False,
            "Chinese-wall proof does not match its rebuilt request: " + ", ".join(binding_failures),
            [parsed.proof_id],
        )
    failures = _chinese_wall_proof_failures(
        parsed,
        lesson_id=lesson_id,
        approval_id=approval_id,
    )
    return _check(
        "chinese_wall_proof_promotion_gate",
        not failures,
        (
            "Chinese-wall evidence is ready for counsel-owned policy, authenticated human, "
            "and owning-repo review; this check performs no lesson fire, conflict clearance, "
            "Exception Lake write, promotion, or external action."
            if not failures
            else "Chinese-wall proof blocks lesson firing review: " + ", ".join(failures)
        ),
        [parsed.proof_id],
    )


def _parse_chinese_wall_proof(
    proof: ChineseWallProof | dict[str, Any],
) -> tuple[ChineseWallProof | None, str | None]:
    try:
        payload = proof.model_dump(mode="json") if isinstance(proof, ChineseWallProof) else proof
        return ChineseWallProof.model_validate_json(json.dumps(payload)), None
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"]
    except (TypeError, ValueError):
        return None, "Chinese-wall proof is not valid JSON model input"


def _rebuild_chinese_wall_proof(
    request: ChineseWallRequest | dict[str, Any],
) -> tuple[ChineseWallProof | None, str | None, str | None]:
    try:
        payload = (
            request.model_dump(mode="json") if isinstance(request, ChineseWallRequest) else request
        )
        parsed = ChineseWallRequest.model_validate_json(json.dumps(payload))
        return build_chinese_wall_proof(parsed), chinese_wall_request_digest(parsed), None
    except (ValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            return None, None, exc.errors()[0]["msg"]
        if isinstance(exc, TypeError):
            return None, None, "Chinese-wall request is not valid JSON model input"
        return None, None, str(exc)


def _chinese_wall_proof_failures(
    proof: ChineseWallProof,
    *,
    lesson_id: str,
    approval_id: str | None,
) -> list[str]:
    failures: list[str] = []
    if proof.lesson_id != lesson_id:
        failures.append("lesson_id_mismatch")
    if proof.overall_status != "candidate":
        failures.append(f"status={proof.overall_status}")
    if proof.local_evaluation.decision is WallDecision.cross_wall_block:
        failures.append("cross_wall_detected")
    elif proof.local_evaluation.decision is WallDecision.unreviewed_edge_hold:
        failures.append("unreviewed_edge_hold")
    elif proof.local_evaluation.decision is WallDecision.unknown_relation_hold:
        failures.append("unknown_relation_hold")
    if not proof.local_evaluation.local_wall_candidate:
        failures.append("local_chinese_wall_mechanism_not_candidate")
    if proof.local_evaluation.relationship_inference_performed:
        failures.append("adversity_relationship_inference_performed")
    if proof.guarantee != "brewer_nash_synthetic_policy_check":
        failures.append("invalid_chinese_wall_guarantee_label")
    if proof.formal_conflict_clearance_guarantee_claimed:
        failures.append("formal_conflict_clearance_guarantee_claimed")
    if not proof.synthetic_firm_wide_imputation_applied:
        failures.append("synthetic_firm_wide_imputation_not_applied")
    if not proof.trusted_synthetic_provenance_snapshot_pinned:
        failures.append("synthetic_firm_wide_provenance_snapshot_not_pinned")
    if not proof.authoritative_firm_wide_imputation_verified:
        failures.append("authoritative_firm_wide_imputation_not_verified")
    if not proof.counsel_adversity_classes_authority_verified:
        failures.append("counsel_adversity_classes_not_authoritative")
    if not proof.authenticated_human_conflicts_review_verified:
        failures.append("authenticated_human_conflicts_review_not_verified")
    if not proof.owning_repo_review_verified:
        failures.append("owning_repo_review_not_verified")
    if not _approval_id_has_candidate_evidence_shape(approval_id):
        failures.append("missing_approval_id")
    return failures


def validate_calibrated_parameter_gate(
    *,
    estimator_id: str,
    parameter: str,
    corpus_version_ref: str,
    screen_version: str,
    calibration_leakage_proof: CalibrationLeakageProof | dict[str, Any] | None,
    calibration_preflight_request: CalibrationPreflightRequest | dict[str, Any] | None = None,
    expected_aggregate_input_digest: str | None = None,
    expected_dp_release_digest: str | None = None,
    approval_id: str | None = None,
) -> ReviewedLearningGateCheck:
    """Fail closed unless candidate review has proof and an unverified evidence identifier."""
    proof = calibration_leakage_proof
    if proof is None:
        return _check(
            "calibration_leakage_proof_required",
            False,
            "Calibrated parameters require a CalibrationLeakageProof before promotion review.",
        )
    parsed, error = _parse_calibration_leakage_proof(proof)
    if error is not None or parsed is None:
        return _check(
            "calibration_leakage_proof_valid",
            False,
            f"CalibrationLeakageProof is invalid: {error}",
        )
    if calibration_preflight_request is None:
        return _check(
            "calibration_preflight_request_required",
            False,
            (
                "Calibration proof review requires the synthetic preflight request so the "
                "proof digest and metrics can be rebuilt instead of trusted from the proof."
            ),
            [parsed.proof_id],
        )
    if not _is_sha256_digest(expected_aggregate_input_digest):
        return _check(
            "calibration_expected_request_digest_required",
            False,
            (
                "Calibration proof review requires a sha256 request digest supplied by the "
                "calling evidence context, independently of the proof/request pair."
            ),
            [parsed.proof_id],
        )
    if parsed.path == "dp" and not _is_sha256_digest(expected_dp_release_digest):
        return _check(
            "calibration_expected_dp_release_digest_required",
            False,
            (
                "DP calibration proof review requires a sha256 release digest supplied by "
                "the calling evidence context independently of the proof/request pair."
            ),
            [parsed.proof_id],
        )
    rebuilt, rebuild_error = _rebuild_calibration_leakage_proof(calibration_preflight_request)
    if rebuild_error is not None or rebuilt is None:
        return _check(
            "calibration_preflight_request_valid",
            False,
            f"Calibration preflight request is invalid: {rebuild_error}",
            [parsed.proof_id],
        )
    binding_failures = _proof_request_binding_failures(
        parsed,
        rebuilt,
        expected_aggregate_input_digest=expected_aggregate_input_digest,
        expected_dp_release_digest=expected_dp_release_digest,
    )
    if binding_failures:
        return _check(
            "calibration_leakage_proof_request_binding",
            False,
            (
                "Calibration leakage proof does not match the rebuilt synthetic preflight "
                "request: " + ", ".join(binding_failures)
            ),
            [parsed.proof_id],
        )

    failures = _calibration_proof_failures(
        parsed,
        estimator_id=estimator_id,
        parameter=parameter,
        corpus_version_ref=corpus_version_ref,
        screen_version=screen_version,
        approval_id=approval_id,
    )
    return _check(
        "calibration_leakage_proof_promotion_gate",
        not failures,
        (
            "Calibration leakage proof and a deterministic approval evidence identifier are "
            "present for candidate promotion review. An expected request digest from the "
            "calling context matched the rebuilt request and proof, but this gate does not "
            "authenticate that context. DP releases additionally require a matching release "
            "digest and an authority-owned ledger receipt. Identifier shape only: no approval registry, "
            "reviewer identity, attorney role, or reviewer role was verified. "
            "This check does not mutate profiles, budgets, guidelines, Lake records, or canon."
            if not failures
            else "Calibration leakage proof blocks promotion review: " + ", ".join(failures)
        ),
        [parsed.proof_id],
    )


def check_calibration_leakage_proof_for_promotion(
    proof: CalibrationLeakageProof | dict[str, Any] | None,
    *,
    estimator_id: str,
    parameter: str,
    corpus_version_ref: str,
    screen_version: str,
    calibration_preflight_request: CalibrationPreflightRequest | dict[str, Any] | None = None,
    expected_aggregate_input_digest: str | None = None,
    expected_dp_release_digest: str | None = None,
    approval_id: str | None = None,
    proof_ref: str = "calibration_leakage_proof",
) -> ReviewedLearningGateCheck:
    if proof is None:
        return validate_calibrated_parameter_gate(
            estimator_id=estimator_id,
            parameter=parameter,
            corpus_version_ref=corpus_version_ref,
            screen_version=screen_version,
            calibration_leakage_proof=None,
            calibration_preflight_request=calibration_preflight_request,
            expected_aggregate_input_digest=expected_aggregate_input_digest,
            expected_dp_release_digest=expected_dp_release_digest,
            approval_id=approval_id,
        )
    parsed, error = _parse_calibration_leakage_proof(proof)
    if error is not None or parsed is None:
        return _check(
            "calibration_leakage_proof_valid",
            False,
            f"CalibrationLeakageProof is invalid for {proof_ref}: {error}",
        )

    return validate_calibrated_parameter_gate(
        estimator_id=estimator_id,
        parameter=parameter,
        corpus_version_ref=corpus_version_ref,
        screen_version=screen_version,
        calibration_leakage_proof=parsed,
        calibration_preflight_request=calibration_preflight_request,
        expected_aggregate_input_digest=expected_aggregate_input_digest,
        expected_dp_release_digest=expected_dp_release_digest,
        approval_id=approval_id,
    )


def _calibration_proof_failures(
    proof: CalibrationLeakageProof,
    *,
    estimator_id: str,
    parameter: str,
    corpus_version_ref: str,
    screen_version: str,
    approval_id: str | None,
) -> list[str]:
    failures: list[str] = []
    if proof.estimator_id != estimator_id:
        failures.append("estimator_id_mismatch")
    if proof.parameter != parameter:
        failures.append("parameter_mismatch")
    if proof.corpus_version_ref != corpus_version_ref:
        failures.append("corpus_version_ref_mismatch")
    if proof.screen_version != screen_version:
        failures.append("screen_version_mismatch")
    if proof.status != "candidate":
        failures.append(f"status={proof.status}")
    if proof.path not in {"aggregate_only", "dp"}:
        failures.append(f"path={proof.path}")
    if proof.refusal_reasons:
        failures.append("refusal_reasons_present")
    if proof.path == "aggregate_only":
        if not proof.kanon.dominance_ok:
            failures.append("kanon_dominance_not_ok")
        if not proof.lomo.dominance_ok:
            failures.append("lomo_dominance_not_ok")
    if proof.path == "dp":
        if proof.dp is None:
            failures.append("dp_release_evidence_missing")
        else:
            if not proof.dp.local_jsonl_fsync_readback_confirmed:
                failures.append("dp_local_ledger_readback_not_confirmed")
            if not proof.dp.authoritative_ledger_receipt_verified:
                failures.append("authoritative_dp_ledger_receipt_not_verified")
            if not proof.dp.seed_is_synthetic_replay_only:
                failures.append("dp_seed_scope_not_synthetic_replay")
            if not proof.dp.secret_seed_authority_verified:
                failures.append("governed_secret_seed_authority_not_verified")
            if proof.dp.production_privacy_guarantee_claimed:
                failures.append("production_privacy_guarantee_claimed")
            if proof.dp.calibrated_value_included:
                failures.append("dp_calibrated_value_included")
        if proof.utility.get("utility_floor_ok") is not True:
            failures.append("dp_utility_floor_not_met")
        if not proof.reconstruction.computed_adversary_test_performed:
            failures.append("dp_reconstruction_smoke_check_not_computed")
    if not proof.reconstruction.passed:
        failures.append("reconstruction_not_passed")
    if not proof.determinism.rebuilt:
        failures.append("determinism_not_rebuilt")
    if proof.path == "aggregate_only" and not proof.determinism.aggregate_byte_identical:
        failures.append("aggregate_rebuild_not_byte_identical")
    if proof.path == "dp" and not proof.determinism.dp_seed_hash:
        failures.append("dp_seed_hash_missing")
    if proof.calibrated_value_published:
        failures.append("calibrated_value_published")
    if not proof.candidate_only:
        failures.append("not_candidate_only")
    if not proof.human_review_required:
        failures.append("human_review_not_required")
    if not _approval_id_has_candidate_evidence_shape(approval_id):
        failures.append("missing_approval_id")
    return failures


def _parse_calibration_leakage_proof(
    proof: CalibrationLeakageProof | dict[str, Any],
) -> tuple[CalibrationLeakageProof | None, str | None]:
    try:
        payload = (
            proof.model_dump(mode="json") if isinstance(proof, CalibrationLeakageProof) else proof
        )
        return CalibrationLeakageProof.model_validate(payload), None
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"]


def _rebuild_calibration_leakage_proof(
    request: CalibrationPreflightRequest | dict[str, Any],
) -> tuple[CalibrationLeakageProof | None, str | None]:
    try:
        payload = (
            request.model_dump(mode="json")
            if isinstance(request, CalibrationPreflightRequest)
            else request
        )
        parsed = CalibrationPreflightRequest.model_validate(payload)
        return build_calibration_leakage_proof(parsed), None
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"]


def _proof_request_binding_failures(
    proof: CalibrationLeakageProof,
    rebuilt: CalibrationLeakageProof,
    *,
    expected_aggregate_input_digest: str,
    expected_dp_release_digest: str | None,
) -> list[str]:
    failures: list[str] = []
    if rebuilt.determinism.aggregate_input_digest != expected_aggregate_input_digest:
        failures.append("expected_digest_does_not_match_rebuilt_request")
    if proof.determinism.aggregate_input_digest != expected_aggregate_input_digest:
        failures.append("proof_digest_does_not_match_expected_digest")
    if proof.determinism.aggregate_input_digest != rebuilt.determinism.aggregate_input_digest:
        failures.append("aggregate_input_digest_mismatch")
    if proof.path == "aggregate_only":
        if proof.proof_id != rebuilt.proof_id:
            failures.append("proof_id_mismatch")
        proof_payload = proof.model_dump(mode="json", exclude={"generated_at"})
        rebuilt_payload = rebuilt.model_dump(mode="json", exclude={"generated_at"})
        if proof_payload != rebuilt_payload:
            failures.append("proof_content_mismatch")
    elif proof.path == "dp":
        if proof.dp is None:
            failures.append("dp_release_evidence_missing")
        elif proof.dp.release_digest != expected_dp_release_digest:
            failures.append("dp_release_digest_does_not_match_expected_digest")
        for field in [
            "request_id",
            "estimator_id",
            "parameter",
            "corpus_version_ref",
            "screen_version",
        ]:
            if getattr(proof, field) != getattr(rebuilt, field):
                failures.append(f"{field}_request_binding_mismatch")
        if proof.methodology != rebuilt.methodology:
            failures.append("methodology_request_binding_mismatch")
        if proof.kanon != rebuilt.kanon:
            failures.append("kanon_request_binding_mismatch")
        if proof.lomo != rebuilt.lomo:
            failures.append("lomo_request_binding_mismatch")
        if proof.group_privacy.unit != rebuilt.group_privacy.unit:
            failures.append("group_privacy_unit_request_binding_mismatch")
        if proof.group_privacy.max_group_size != rebuilt.group_privacy.max_group_size:
            failures.append("group_size_request_binding_mismatch")
    return failures


def _is_sha256_digest(value: str | None) -> bool:
    if value is None or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _approval_id_has_candidate_evidence_shape(approval_id: str | None) -> bool:
    if approval_id is None:
        return False
    cleaned = approval_id.strip()
    if cleaned != approval_id or not cleaned:
        return False
    lowered = cleaned.lower()
    if "synthetic" in lowered or "placeholder" in lowered:
        return False
    return cleaned.startswith("approval:")


def _calibration_gate_checks(
    requests: list[dict[str, Any]],
) -> list[ReviewedLearningGateCheck]:
    checks: list[ReviewedLearningGateCheck] = []
    required = [
        "estimator_id",
        "parameter",
        "corpus_version_ref",
        "screen_version",
        "calibration_leakage_proof",
        "calibration_preflight_request",
        "expected_aggregate_input_digest",
    ]
    for index, request in enumerate(requests):
        missing = [field for field in required if not request.get(field)]
        if missing:
            checks.append(
                _check(
                    "calibration_leakage_gate_request_complete",
                    False,
                    (
                        f"Calibration gate request {index} is missing required fields: "
                        + ", ".join(missing)
                    ),
                )
            )
            continue
        checks.append(
            validate_calibrated_parameter_gate(
                estimator_id=str(request["estimator_id"]),
                parameter=str(request["parameter"]),
                corpus_version_ref=str(request["corpus_version_ref"]),
                screen_version=str(request["screen_version"]),
                calibration_leakage_proof=request["calibration_leakage_proof"],
                calibration_preflight_request=request["calibration_preflight_request"],
                expected_aggregate_input_digest=str(request["expected_aggregate_input_digest"]),
                expected_dp_release_digest=(
                    str(request["expected_dp_release_digest"])
                    if request.get("expected_dp_release_digest") is not None
                    else None
                ),
                approval_id=(
                    str(request["approval_id"]) if request.get("approval_id") is not None else None
                ),
            )
        )
    return checks


def _lesson_disclosure_gate_checks(
    requests: list[dict[str, Any]],
) -> list[ReviewedLearningGateCheck]:
    checks: list[ReviewedLearningGateCheck] = []
    required = [
        "lesson_id",
        "lesson_disclosure_proof",
        "lesson_disclosure_request",
        "expected_lesson_input_digest",
    ]
    for index, request in enumerate(requests):
        missing = [field for field in required if not request.get(field)]
        if missing:
            checks.append(
                _check(
                    "lesson_disclosure_gate_request_complete",
                    False,
                    f"Lesson disclosure gate request {index} is missing: " + ", ".join(missing),
                )
            )
            continue
        checks.append(
            validate_lesson_disclosure_gate(
                lesson_id=str(request["lesson_id"]),
                lesson_disclosure_proof=request["lesson_disclosure_proof"],
                lesson_disclosure_request=request["lesson_disclosure_request"],
                expected_lesson_input_digest=str(request["expected_lesson_input_digest"]),
                approval_id=(
                    str(request["approval_id"]) if request.get("approval_id") is not None else None
                ),
            )
        )
    return checks


def _crossing_gate_checks(
    requests: list[dict[str, Any]],
) -> list[ReviewedLearningGateCheck]:
    checks: list[ReviewedLearningGateCheck] = []
    required = [
        "request_id",
        "crossing_proof",
        "crossing_request",
        "expected_crossing_request_digest",
    ]
    for index, request in enumerate(requests):
        missing = [field for field in required if not request.get(field)]
        if missing:
            checks.append(
                _check(
                    "crossing_gate_request_complete",
                    False,
                    f"Crossing gate request {index} is missing: " + ", ".join(missing),
                )
            )
            continue
        checks.append(
            validate_crossing_gate(
                request_id=str(request["request_id"]),
                crossing_proof=request["crossing_proof"],
                crossing_request=request["crossing_request"],
                expected_crossing_request_digest=str(request["expected_crossing_request_digest"]),
                approval_id=(
                    str(request["approval_id"]) if request.get("approval_id") is not None else None
                ),
            )
        )
    return checks


def _chinese_wall_gate_checks(
    requests: list[dict[str, Any]],
) -> list[ReviewedLearningGateCheck]:
    checks: list[ReviewedLearningGateCheck] = []
    required = [
        "lesson_id",
        "chinese_wall_proof",
        "chinese_wall_request",
        "expected_chinese_wall_request_digest",
    ]
    for index, request in enumerate(requests):
        missing = [field for field in required if not request.get(field)]
        if missing:
            checks.append(
                _check(
                    "chinese_wall_gate_request_complete",
                    False,
                    f"Chinese-wall gate request {index} is missing: " + ", ".join(missing),
                )
            )
            continue
        checks.append(
            validate_chinese_wall_gate(
                lesson_id=str(request["lesson_id"]),
                chinese_wall_proof=request["chinese_wall_proof"],
                chinese_wall_request=request["chinese_wall_request"],
                expected_chinese_wall_request_digest=str(
                    request["expected_chinese_wall_request_digest"]
                ),
                approval_id=(
                    str(request["approval_id"]) if request.get("approval_id") is not None else None
                ),
            )
        )
    return checks


def _carrier_lesson_boundary_coverage_checks(
    candidates: list[ReviewedLearningGateCandidate],
    lesson_requests: list[dict[str, Any]],
    wall_requests: list[dict[str, Any]],
) -> list[ReviewedLearningGateCheck]:
    carrier_ids = {
        candidate.source_record_id
        for candidate in candidates
        if candidate.source_kind == "carrier_rejection_learning_proposal"
    }
    if not carrier_ids:
        return []
    lesson_covered = {
        str(request["source_record_id"])
        for request in lesson_requests
        if request.get("source_record_id")
    }
    wall_covered = {
        str(request["source_record_id"])
        for request in wall_requests
        if request.get("source_record_id")
    }
    missing_lesson = sorted(carrier_ids - lesson_covered)
    missing_wall = sorted(carrier_ids - wall_covered)
    return [
        _check(
            "carrier_lesson_disclosure_gate_coverage",
            not missing_lesson,
            (
                "Every carrier learning proposal has a source-record-bound lesson disclosure "
                "gate request."
                if not missing_lesson
                else "Carrier learning proposals missing lesson disclosure gate requests: "
                + ", ".join(missing_lesson)
            ),
            sorted(carrier_ids),
        ),
        _check(
            "carrier_chinese_wall_gate_coverage",
            not missing_wall,
            (
                "Every carrier learning proposal has a source-record-bound Chinese-wall gate "
                "request."
                if not missing_wall
                else "Carrier learning proposals missing Chinese-wall gate requests: "
                + ", ".join(missing_wall)
            ),
            sorted(carrier_ids),
        ),
    ]


def build_reviewed_learning_gate_report(
    *,
    carrier_rejection_learning_report: CarrierRejectionLearningReport | None = None,
    carrier_rejection_learning_report_ref: str | None = None,
    budget_revision_report: BudgetRevisionReport | None = None,
    budget_revision_report_ref: str | None = None,
    budget_actual_comparison_report: BudgetActualComparisonReport | None = None,
    budget_actual_comparison_report_ref: str | None = None,
    calibrated_parameter_gate_requests: list[dict[str, Any]] | None = None,
    lesson_disclosure_gate_requests: list[dict[str, Any]] | None = None,
    crossing_gate_requests: list[dict[str, Any]] | None = None,
    chinese_wall_gate_requests: list[dict[str, Any]] | None = None,
) -> ReviewedLearningGateReport:
    calibration_gate_requests = calibrated_parameter_gate_requests or []
    lesson_gate_requests = lesson_disclosure_gate_requests or []
    crossing_requests = crossing_gate_requests or []
    wall_requests = chinese_wall_gate_requests or []
    calibration_refs = [
        str(
            request.get("proof_ref")
            or request.get("corpus_version_ref")
            or f"calibrated_parameter_gate_request:{index}"
        )
        for index, request in enumerate(calibration_gate_requests)
    ]
    lesson_refs = [
        str(
            request.get("proof_ref")
            or request.get("lesson_id")
            or f"lesson_disclosure_gate_request:{index}"
        )
        for index, request in enumerate(lesson_gate_requests)
    ]
    crossing_refs = [
        str(
            request.get("proof_ref")
            or request.get("request_id")
            or f"crossing_gate_request:{index}"
        )
        for index, request in enumerate(crossing_requests)
    ]
    wall_refs = [
        str(
            request.get("proof_ref")
            or request.get("lesson_id")
            or f"chinese_wall_gate_request:{index}"
        )
        for index, request in enumerate(wall_requests)
    ]
    source_refs = [
        ref
        for ref in [
            carrier_rejection_learning_report_ref,
            budget_revision_report_ref,
            budget_actual_comparison_report_ref,
            *calibration_refs,
            *lesson_refs,
            *crossing_refs,
            *wall_refs,
        ]
        if ref
    ]
    if not source_refs:
        raise ValueError("reviewed learning gate requires at least one source report")

    candidates: list[ReviewedLearningGateCandidate] = []
    carrier_count = 0
    revision_count = 0
    actual_count = 0

    if carrier_rejection_learning_report is not None:
        report_ref = carrier_rejection_learning_report_ref or "carrier_rejection_learning_report"
        for proposal in carrier_rejection_learning_report.proposals:
            candidates.append(
                _carrier_candidate(
                    proposal=proposal,
                    report=carrier_rejection_learning_report,
                    report_ref=report_ref,
                )
            )
        carrier_count = len(carrier_rejection_learning_report.proposals)

    if budget_revision_report is not None:
        report_ref = budget_revision_report_ref or "budget_revision_report"
        for delta in budget_revision_report.deltas:
            candidates.append(
                _revision_candidate(
                    delta=delta, report=budget_revision_report, report_ref=report_ref
                )
            )
        revision_count = len(budget_revision_report.deltas)

    if budget_actual_comparison_report is not None:
        report_ref = budget_actual_comparison_report_ref or "budget_actual_comparison_report"
        for driver in budget_actual_comparison_report.variance_driver_candidates:
            candidates.append(
                _actual_variance_candidate(
                    driver=driver,
                    report=budget_actual_comparison_report,
                    report_ref=report_ref,
                )
            )
        actual_count = len(budget_actual_comparison_report.variance_driver_candidates)

    candidate_ids = [candidate.candidate_id for candidate in candidates]
    candidates_blocked = all(
        candidate.status == "blocked_until_reviewed_learning_gate"
        and candidate.human_review_required
        and candidate.shadow_eval_required
        and candidate.owning_repo_review_required
        for candidate in candidates
    )
    no_mutations = all(
        not any(
            [
                candidate.profile_mutation_performed,
                candidate.template_mutation_performed,
                candidate.connector_mutation_performed,
                candidate.budget_mutation_performed,
                candidate.carrier_guideline_mutation_performed,
                candidate.lake_write_performed,
                candidate.external_writes_performed,
                candidate.silent_learning_performed,
            ]
        )
        for candidate in candidates
    )
    required_evals_present = all(
        "synthetic fixture update" in candidate.required_evaluation
        and "shadow eval before promotion" in candidate.required_evaluation
        for candidate in candidates
    )
    support_refs_present = all(candidate.support_refs for candidate in candidates)
    required_gates_present = all(
        set(REQUIRED_NEXT_GATES).issubset(set(candidate.required_next_gates))
        for candidate in candidates
    )
    calibration_checks = _calibration_gate_checks(calibration_gate_requests)
    lesson_checks = _lesson_disclosure_gate_checks(lesson_gate_requests)
    crossing_checks = _crossing_gate_checks(crossing_requests)
    wall_checks = _chinese_wall_gate_checks(wall_requests)
    carrier_boundary_coverage_checks = _carrier_lesson_boundary_coverage_checks(
        candidates,
        lesson_gate_requests,
        wall_requests,
    )
    calibration_proof_ids = list(
        dict.fromkeys(
            candidate_id for check in calibration_checks for candidate_id in check.candidate_ids
        )
    )
    calibration_visibility_checks = (
        [
            _check(
                "calibration_gate_review_inputs_visible",
                True,
                (
                    "Calibration proof review input is visible as candidate-only gate evidence; "
                    "it is not an ordinary learning candidate and performs no promotion."
                ),
                calibration_proof_ids,
            )
        ]
        if calibration_gate_requests
        else []
    )
    lesson_proof_ids = list(
        dict.fromkeys(
            candidate_id for check in lesson_checks for candidate_id in check.candidate_ids
        )
    )
    lesson_visibility_checks = (
        [
            _check(
                "lesson_disclosure_gate_review_inputs_visible",
                True,
                (
                    "Lesson disclosure proof is visible as candidate-only review evidence; "
                    "it is not an ordinary learning candidate and performs no publication."
                ),
                lesson_proof_ids,
            )
        ]
        if lesson_gate_requests
        else []
    )
    crossing_proof_ids = list(
        dict.fromkeys(
            candidate_id for check in crossing_checks for candidate_id in check.candidate_ids
        )
    )
    crossing_visibility_checks = (
        [
            _check(
                "crossing_gate_review_inputs_visible",
                True,
                (
                    "Crossing proof is visible as candidate-only review evidence; it is not an "
                    "ordinary learning candidate and performs no send, outbox write, or DAD contact."
                ),
                crossing_proof_ids,
            )
        ]
        if crossing_requests
        else []
    )
    wall_proof_ids = list(
        dict.fromkeys(candidate_id for check in wall_checks for candidate_id in check.candidate_ids)
    )
    wall_visibility_checks = (
        [
            _check(
                "chinese_wall_gate_review_inputs_visible",
                True,
                (
                    "Chinese-wall proof is visible as candidate-only review evidence; it is "
                    "not an ordinary learning candidate and performs no lesson fire, conflict "
                    "clearance, Exception Lake write, or external action."
                ),
                wall_proof_ids,
            )
        ]
        if wall_requests
        else []
    )
    checks = [
        _check(
            "source_reports_present",
            bool(source_refs),
            "At least one source learning, revision, or variance report is present.",
        ),
        _check(
            "candidates_blocked_until_review",
            candidates_blocked,
            "Every learning candidate is blocked until human review, shadow eval, and owning-repo review.",
            candidate_ids,
        ),
        _check(
            "no_mutations_or_external_writes",
            no_mutations,
            "Learning gate performs no profile, template, connector, budget, guideline, Lake, or external mutation.",
            candidate_ids,
        ),
        _check(
            "required_evaluations_declared",
            required_evals_present,
            "Every candidate declares synthetic fixture and shadow-eval requirements.",
            candidate_ids,
        ),
        _check(
            "support_refs_declared",
            support_refs_present,
            "Every candidate carries source artifact or structured support refs.",
            candidate_ids,
        ),
        _check(
            "required_gates_declared",
            required_gates_present,
            "Every candidate carries the reviewed-learning gate sequence.",
            candidate_ids,
        ),
        *calibration_visibility_checks,
        *calibration_checks,
        *lesson_visibility_checks,
        *lesson_checks,
        *crossing_visibility_checks,
        *crossing_checks,
        *wall_visibility_checks,
        *wall_checks,
        *carrier_boundary_coverage_checks,
    ]
    failed = [check for check in checks if check.status == "failed"]
    if failed:
        status = "failed"
    elif (
        candidates
        or calibration_gate_requests
        or lesson_gate_requests
        or crossing_requests
        or wall_requests
    ):
        status = "candidate_learning_gate_ready"
    else:
        status = "no_learning_candidates"

    run_id = new_id("learninggaterun")
    if carrier_rejection_learning_report is not None:
        run_id = carrier_rejection_learning_report.run_id
    elif budget_revision_report is not None:
        run_id = budget_revision_report.run_id
    elif budget_actual_comparison_report is not None:
        run_id = budget_actual_comparison_report.run_id

    return ReviewedLearningGateReport(
        reviewed_learning_gate_report_id=new_id("reviewedlearninggate"),
        run_id=run_id,
        status=status,  # type: ignore[arg-type]
        source_report_refs=source_refs,
        carrier_rejection_learning_report_ref=carrier_rejection_learning_report_ref,
        budget_revision_report_ref=budget_revision_report_ref,
        budget_actual_comparison_report_ref=budget_actual_comparison_report_ref,
        candidate_count=len(candidates),
        carrier_learning_candidate_count=carrier_count,
        budget_revision_candidate_count=revision_count,
        budget_actual_variance_candidate_count=actual_count,
        target_learning_loops=sorted({candidate.target_learning_loop for candidate in candidates}),
        target_owners=sorted({candidate.target_owner for candidate in candidates}),
        candidates=candidates,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_reviewed_learning_gate_report(report: ReviewedLearningGateReport) -> str:
    lines = [
        "# Reviewed Learning Gate Report",
        "",
        f"**Report ID:** {report.reviewed_learning_gate_report_id}",
        f"**Status:** {report.status}",
        f"**Candidate count:** {report.candidate_count}",
        "",
        "## Inputs",
        "",
        *(f"- {ref}" for ref in report.source_report_refs),
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Reviewed outcome required: {report.reviewed_outcome_required}",
        f"- Append-only evidence required: {report.append_only_evidence_required}",
        f"- Synthetic fixture update required: {report.synthetic_fixture_update_required}",
        f"- Shadow eval required: {report.shadow_eval_required}",
        f"- Owning repo review required: {report.owning_repo_review_required}",
        f"- Profile mutation performed: {report.profile_mutation_performed}",
        f"- Template mutation performed: {report.template_mutation_performed}",
        f"- Connector mutation performed: {report.connector_mutation_performed}",
        f"- Budget mutation performed: {report.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {item}" for item in report.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(
        [
            "",
            "## Candidates",
            "",
        ]
    )
    if not report.candidates:
        lines.append("- none")
    for candidate in report.candidates:
        lines.extend(
            [
                f"- `{candidate.candidate_id}`: {candidate.source_kind}; "
                f"loop={candidate.target_learning_loop}; owner={candidate.target_owner}; "
                f"status={candidate.status}",
                f"  Trigger: {candidate.trigger_summary}",
                f"  Candidate behavior: {candidate.proposed_candidate_behavior}",
                "  Required evidence:",
                *(f"  - {item}" for item in candidate.required_evidence),
                "  Required evaluation:",
                *(f"  - {item}" for item in candidate.required_evaluation),
                "  Support refs:",
                *(f"  - {item}" for item in candidate.support_refs),
            ]
        )
    lines.extend(
        [
            "",
            "This report routes candidate learning pressure only. It does not mutate profiles, templates, connectors, budgets, carrier guidelines, Lake records, or canonical contracts.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_gate_request_paths(
    paths: list[str | Path] | None,
    *,
    label: str,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for raw_path in paths or []:
        path = Path(raw_path)
        payload = load_json(path)
        items = payload if isinstance(payload, list) else [payload]
        if not items or not all(isinstance(item, dict) for item in items):
            raise ValueError(f"{label} gate request file must contain an object or object list")
        for item in items:
            request = dict(item)
            request.setdefault("proof_ref", str(path))
            requests.append(request)
    return requests


def run_reviewed_learning_gate(
    *,
    out_dir: str | Path,
    carrier_rejection_learning_report_path: str | Path | None = None,
    budget_revision_report_path: str | Path | None = None,
    budget_actual_comparison_report_path: str | Path | None = None,
    lesson_disclosure_gate_request_paths: list[str | Path] | None = None,
    chinese_wall_gate_request_paths: list[str | Path] | None = None,
) -> tuple[ReviewedLearningGateReport, Path]:
    carrier_report = None
    carrier_ref = None
    if carrier_rejection_learning_report_path is not None:
        carrier_path = Path(carrier_rejection_learning_report_path)
        carrier_report = CarrierRejectionLearningReport.model_validate(load_json(carrier_path))
        carrier_ref = str(carrier_path)

    revision_report = None
    revision_ref = None
    if budget_revision_report_path is not None:
        revision_path = Path(budget_revision_report_path)
        revision_report = BudgetRevisionReport.model_validate(load_json(revision_path))
        revision_ref = str(revision_path)

    actuals_report = None
    actuals_ref = None
    if budget_actual_comparison_report_path is not None:
        actuals_path = Path(budget_actual_comparison_report_path)
        actuals_report = BudgetActualComparisonReport.model_validate(load_json(actuals_path))
        actuals_ref = str(actuals_path)

    lesson_gate_requests = _load_gate_request_paths(
        lesson_disclosure_gate_request_paths,
        label="lesson disclosure",
    )
    wall_gate_requests = _load_gate_request_paths(
        chinese_wall_gate_request_paths,
        label="Chinese-wall",
    )

    report = build_reviewed_learning_gate_report(
        carrier_rejection_learning_report=carrier_report,
        carrier_rejection_learning_report_ref=carrier_ref,
        budget_revision_report=revision_report,
        budget_revision_report_ref=revision_ref,
        budget_actual_comparison_report=actuals_report,
        budget_actual_comparison_report_ref=actuals_ref,
        lesson_disclosure_gate_requests=lesson_gate_requests,
        chinese_wall_gate_requests=wall_gate_requests,
    )

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / REVIEWED_LEARNING_GATE_REPORT_FILENAME
    notes_path = run_dir / REVIEWED_LEARNING_GATE_NOTES_FILENAME
    candidates_path = run_dir / REVIEWED_LEARNING_GATE_CANDIDATES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_reviewed_learning_gate_report(report), encoding="utf-8")
    candidates_path.touch()
    for candidate in report.candidates:
        append_jsonl(candidates_path, candidate.model_dump(mode="json"))
    return report, run_dir
