from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .calibration import CalibrationLeakageProof
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

CALIBRATION_LEAKAGE_PROOF_REQUIRED_GATES = [
    "valid_calibration_leakage_proof",
    "human_calibration_approval_id",
    "owning_repo_review",
    "no_calibrated_value_publication_from_intake",
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
        required_next_gates=REQUIRED_NEXT_GATES,
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


def validate_calibrated_parameter_gate(
    *,
    estimator_id: str,
    parameter: str,
    corpus_version_ref: str,
    screen_version: str,
    calibration_leakage_proof: CalibrationLeakageProof | dict[str, Any] | None,
    approval_id: str | None,
) -> ReviewedLearningGateCheck:
    """Fail closed unless a calibrated parameter has proof and a human approval id."""
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
            "Calibration leakage proof and approval id are present for promotion review; "
            "this check does not mutate profiles, budgets, guidelines, Lake records, or canon."
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
    if proof.path != "aggregate_only":
        failures.append(f"path={proof.path}")
    if proof.refusal_reasons:
        failures.append("refusal_reasons_present")
    if not proof.kanon.dominance_ok:
        failures.append("kanon_dominance_not_ok")
    if not proof.lomo.dominance_ok:
        failures.append("lomo_dominance_not_ok")
    if not proof.reconstruction.passed:
        failures.append("reconstruction_not_passed")
    if not proof.determinism.rebuilt:
        failures.append("determinism_not_rebuilt")
    if not proof.determinism.aggregate_byte_identical:
        failures.append("aggregate_rebuild_not_byte_identical")
    if proof.calibrated_value_published:
        failures.append("calibrated_value_published")
    if not proof.candidate_only:
        failures.append("not_candidate_only")
    if not proof.human_review_required:
        failures.append("human_review_not_required")
    if not _approval_id_is_reviewed(approval_id):
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


def _approval_id_is_reviewed(approval_id: str | None) -> bool:
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
                approval_id=(
                    str(request["approval_id"]) if request.get("approval_id") is not None else None
                ),
            )
        )
    return checks


def build_reviewed_learning_gate_report(
    *,
    carrier_rejection_learning_report: CarrierRejectionLearningReport | None = None,
    carrier_rejection_learning_report_ref: str | None = None,
    budget_revision_report: BudgetRevisionReport | None = None,
    budget_revision_report_ref: str | None = None,
    budget_actual_comparison_report: BudgetActualComparisonReport | None = None,
    budget_actual_comparison_report_ref: str | None = None,
    calibrated_parameter_gate_requests: list[dict[str, Any]] | None = None,
) -> ReviewedLearningGateReport:
    calibration_gate_requests = calibrated_parameter_gate_requests or []
    calibration_refs = [
        str(
            request.get("proof_ref")
            or request.get("corpus_version_ref")
            or f"calibrated_parameter_gate_request:{index}"
        )
        for index, request in enumerate(calibration_gate_requests)
    ]
    source_refs = [
        ref
        for ref in [
            carrier_rejection_learning_report_ref,
            budget_revision_report_ref,
            budget_actual_comparison_report_ref,
            *calibration_refs,
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
        *calibration_checks,
    ]
    failed = [check for check in checks if check.status == "failed"]
    if failed:
        status = "failed"
    elif candidates:
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


def run_reviewed_learning_gate(
    *,
    out_dir: str | Path,
    carrier_rejection_learning_report_path: str | Path | None = None,
    budget_revision_report_path: str | Path | None = None,
    budget_actual_comparison_report_path: str | Path | None = None,
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

    report = build_reviewed_learning_gate_report(
        carrier_rejection_learning_report=carrier_report,
        carrier_rejection_learning_report_ref=carrier_ref,
        budget_revision_report=revision_report,
        budget_revision_report_ref=revision_ref,
        budget_actual_comparison_report=actuals_report,
        budget_actual_comparison_report_ref=actuals_ref,
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
