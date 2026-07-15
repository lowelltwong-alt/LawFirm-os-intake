from __future__ import annotations

from pathlib import Path

from .models import (
    CrosswalkAuditReport,
    CrosswalkAuditSummary,
    OCGRuleIRAdoptionReport,
    OCGRuleIRAdoptionSummary,
    QAProductConfidenceGate,
    QAProductConfidenceReport,
    QAReadinessCheck,
    QAReadinessReport,
    UIReviewDataBundle,
)
from .util import digest_json, load_json, now_iso, write_json

QA_READINESS_REPORT_FILENAME = "qa_readiness_report.json"
QA_PRODUCT_CONFIDENCE_REPORT_FILENAME = "qa_product_confidence_report.json"
SUBSTRATE_OWNER = "LawFirm-os-semantic-substrate"


def build_crosswalk_audit_summary(report: CrosswalkAuditReport) -> CrosswalkAuditSummary:
    return CrosswalkAuditSummary(
        report_id=report.report_id,
        status=report.status,
        acceptance_gate_status=report.acceptance_gate_status,
        crosswalk_count=report.crosswalk_count,
        entry_count=report.entry_count,
        mapped_entry_count=report.mapped_entry_count,
        unmapped_entry_count=report.unmapped_entry_count,
        canonical_claim_count=report.canonical_claim_count,
        guessed_mapping_count=report.guessed_mapping_count,
        high_confidence_dual_review_violation_count=report.high_confidence_dual_review_violation_count,
        utbms_like_candidate_family_label_count=report.utbms_like_candidate_family_label_count,
        unverified_pinned_target_count=report.unverified_pinned_target_count,
        candidate_target_prefix_violation_count=report.candidate_target_prefix_violation_count,
        workflow_dependency_violation_count=report.workflow_dependency_violation_count,
        display_banner=report.display_banner,
        prohibited_actions=list(report.prohibited_actions),
        not_authorized_for_canonical_use=report.not_authorized_for_canonical_use,
        not_authorized_for_budget_logic=report.not_authorized_for_budget_logic,
        exact_standard_code_verified=report.exact_standard_code_verified,
        candidate_only=report.candidate_only,
    )


def build_ocg_rule_ir_adoption_summary(
    report: OCGRuleIRAdoptionReport,
) -> OCGRuleIRAdoptionSummary:
    return OCGRuleIRAdoptionSummary(
        report_id=report.report_id,
        status=report.status,
        acceptance_gate_status=report.acceptance_gate_status,
        rule_ir_id=report.rule_ir_id,
        source_owner=report.source_owner,
        source_artifact_ref=report.source_artifact_ref,
        carrier_projection_id=report.carrier_projection_id,
        budget_proposal_id=report.budget_proposal_id,
        proposed_total_before=report.proposed_total_before,
        carrier_compliant_total=report.carrier_compliant_total,
        projection_total_delta=report.projection_total_delta,
        rule_count=report.rule_count,
        impact_line_count=report.impact_line_count,
        canonical_rule_id_violation_count=report.canonical_rule_id_violation_count,
        rewrite_budget_violation_count=report.rewrite_budget_violation_count,
        real_guideline_or_rate_violation_count=report.real_guideline_or_rate_violation_count,
        budget_projection_mismatch_count=report.budget_projection_mismatch_count,
        display_banner=report.display_banner,
        prohibited_actions=list(report.prohibited_actions),
        read_only_consumption=report.read_only_consumption,
        candidate_only=report.candidate_only,
        not_promoted_canon=report.not_promoted_canon,
        not_authorized_for_canonical_use=report.not_authorized_for_canonical_use,
        not_authorized_for_budget_rewrite=report.not_authorized_for_budget_rewrite,
        not_authorized_for_external_submission=report.not_authorized_for_external_submission,
    )


def load_crosswalk_audit_report(path: str | Path) -> CrosswalkAuditReport:
    return CrosswalkAuditReport.model_validate(load_json(path))


def load_ocg_rule_ir_adoption_report(path: str | Path) -> OCGRuleIRAdoptionReport:
    return OCGRuleIRAdoptionReport.model_validate(load_json(path))


def _check(
    check_id: str,
    label: str,
    status: str,
    summary: str,
    *,
    evidence_refs: list[str] | None = None,
    candidate_exception_labels: list[str] | None = None,
) -> QAReadinessCheck:
    return QAReadinessCheck(
        check_id=check_id,
        label=label,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        evidence_refs=evidence_refs or [],
        candidate_exception_labels=candidate_exception_labels or [],
    )


def crosswalk_readiness_checks(
    report: CrosswalkAuditReport | None,
    *,
    evidence_ref: str | None = None,
    required: bool = True,
) -> list[QAReadinessCheck]:
    if report is None:
        if not required:
            return []
        return [
            _check(
                "crosswalk_audit_present",
                "Crosswalk audit report attached",
                "blocked",
                "Crosswalk audit report is missing from the UI/QA evidence bundle.",
            )
        ]
    refs = [evidence_ref] if evidence_ref else []
    checks = [
        _check(
            "crosswalk_audit_status_passed",
            "Crosswalk audit passed",
            "passed" if report.status == "passed" else "blocked",
            f"Crosswalk audit status is {report.status}.",
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_acceptance_gate_restricted",
            "Crosswalk acceptance gate accepted_with_restrictions",
            "passed"
            if report.acceptance_gate_status == "accepted_with_restrictions"
            else "blocked",
            f"Crosswalk acceptance gate is {report.acceptance_gate_status}.",
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_no_canonical_or_guessed_mappings",
            "Crosswalk has zero canonical claims and guessed mappings",
            "passed"
            if report.canonical_claim_count == 0 and report.guessed_mapping_count == 0
            else "blocked",
            (
                f"canonical_claim_count={report.canonical_claim_count}, "
                f"guessed_mapping_count={report.guessed_mapping_count}."
            ),
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_no_pinned_or_workflow_violations",
            "Crosswalk has zero pinned-target and workflow dependency violations",
            "passed"
            if report.unverified_pinned_target_count == 0
            and report.candidate_target_prefix_violation_count == 0
            and report.workflow_dependency_violation_count == 0
            else "blocked",
            (
                "unverified_pinned_target_count="
                f"{report.unverified_pinned_target_count}, "
                "candidate_target_prefix_violation_count="
                f"{report.candidate_target_prefix_violation_count}, "
                "workflow_dependency_violation_count="
                f"{report.workflow_dependency_violation_count}."
            ),
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_no_authority_flags",
            "Crosswalk report preserves no-authority flags",
            "passed"
            if report.not_authorized_for_canonical_use
            and report.not_authorized_for_budget_logic
            and report.candidate_only
            and report.not_promoted_canon
            else "blocked",
            "Crosswalk report must remain candidate-only with explicit no-authority flags.",
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_exact_standard_code_unverified",
            "Crosswalk UTBMS-like labels remain unverified (exact_standard_code_verified=false)",
            "passed" if report.exact_standard_code_verified is False else "blocked",
            (
                f"exact_standard_code_verified={report.exact_standard_code_verified}; "
                f"utbms_like_candidate_family_label_count="
                f"{report.utbms_like_candidate_family_label_count}."
            ),
            evidence_refs=refs,
        ),
        _check(
            "crosswalk_zero_high_confidence_dual_review_violations",
            "Crosswalk has zero high-confidence dual-review violations",
            "passed" if report.high_confidence_dual_review_violation_count == 0 else "blocked",
            (
                "high_confidence_dual_review_violation_count="
                f"{report.high_confidence_dual_review_violation_count}."
            ),
            evidence_refs=refs,
        ),
    ]
    return checks


def ocg_adoption_readiness_checks(
    report: OCGRuleIRAdoptionReport | None,
    *,
    evidence_ref: str | None = None,
    required: bool = True,
) -> list[QAReadinessCheck]:
    if report is None:
        if not required:
            return []
        return [
            _check(
                "ocg_adoption_present",
                "OCG rule IR adoption report attached",
                "blocked",
                "OCG rule IR adoption report is missing from the UI/QA evidence bundle.",
            )
        ]
    refs = [evidence_ref] if evidence_ref else []
    checks = [
        _check(
            "ocg_adoption_status_candidate",
            "OCG adoption accepted_as_read_only_candidate",
            "passed" if report.status == "accepted_as_read_only_candidate" else "blocked",
            f"OCG adoption status is {report.status}.",
            evidence_refs=refs,
        ),
        _check(
            "ocg_source_owner_substrate",
            "OCG source owner is semantic substrate",
            "passed" if report.source_owner == SUBSTRATE_OWNER else "blocked",
            f"OCG source_owner is {report.source_owner}.",
            evidence_refs=refs,
        ),
        _check(
            "ocg_adoption_zero_violations",
            "OCG adoption has zero canonical/rewrite/real-data/projection violations",
            "passed"
            if report.canonical_rule_id_violation_count == 0
            and report.rewrite_budget_violation_count == 0
            and report.real_guideline_or_rate_violation_count == 0
            and report.budget_projection_mismatch_count == 0
            else "blocked",
            (
                f"canonical_rule_id_violation_count={report.canonical_rule_id_violation_count}, "
                f"rewrite_budget_violation_count={report.rewrite_budget_violation_count}, "
                f"real_guideline_or_rate_violation_count="
                f"{report.real_guideline_or_rate_violation_count}, "
                f"budget_projection_mismatch_count={report.budget_projection_mismatch_count}."
            ),
            evidence_refs=refs,
        ),
        _check(
            "ocg_no_authority_flags",
            "OCG adoption preserves no-write/no-authority flags",
            "passed"
            if report.read_only_consumption
            and report.candidate_only
            and report.not_promoted_canon
            and report.not_authorized_for_canonical_use
            and report.not_authorized_for_budget_rewrite
            and report.not_authorized_for_external_submission
            and report.not_authorized_for_lake_write
            else "blocked",
            "OCG adoption report must remain read-only candidate evidence only.",
            evidence_refs=refs,
        ),
    ]
    return checks


def build_qa_readiness_report(
    *,
    ui_review_data_bundle_path: str | Path,
    crosswalk_audit_path: str | Path | None = None,
    ocg_rule_ir_adoption_path: str | Path | None = None,
    require_crosswalk_ocg: bool = False,
    generated_at: str | None = None,
) -> QAReadinessReport:
    bundle = UIReviewDataBundle.model_validate(load_json(ui_review_data_bundle_path))
    crosswalk_ref = (
        str(crosswalk_audit_path) if crosswalk_audit_path else bundle.crosswalk_audit_ref
    )
    ocg_ref = (
        str(ocg_rule_ir_adoption_path)
        if ocg_rule_ir_adoption_path
        else bundle.ocg_rule_ir_adoption_ref
    )
    crosswalk_report = load_crosswalk_audit_report(crosswalk_ref) if crosswalk_ref else None
    ocg_report = load_ocg_rule_ir_adoption_report(ocg_ref) if ocg_ref else None
    require = require_crosswalk_ocg or bool(crosswalk_ref or ocg_ref)
    checks: list[QAReadinessCheck] = [
        _check(
            "ui_bundle_no_write_boundary",
            "UI review bundle has no external write signals",
            "passed"
            if bundle.external_write_report_count == 0
            and bundle.unproven_detail_boundary_count == 0
            and bundle.status == "ready_for_review"
            else "blocked",
            (
                f"external_write_report_count={bundle.external_write_report_count}, "
                "unproven_detail_boundary_count="
                f"{bundle.unproven_detail_boundary_count}, status={bundle.status}."
            ),
            evidence_refs=[str(ui_review_data_bundle_path)],
        ),
        *crosswalk_readiness_checks(
            crosswalk_report,
            evidence_ref=crosswalk_ref,
            required=require,
        ),
        *ocg_adoption_readiness_checks(
            ocg_report,
            evidence_ref=ocg_ref,
            required=require,
        ),
    ]
    blocker_count = sum(1 for check in checks if check.status == "blocked")
    warning_count = sum(1 for check in checks if check.status == "warning")
    passed_check_count = sum(1 for check in checks if check.status == "passed")
    if blocker_count:
        status = "blocked"
    elif warning_count:
        status = "ready_with_warnings"
    else:
        status = "ready_for_review"
    report_core = {
        "status": status,
        "ui_review_data_bundle_id": bundle.ui_review_data_bundle_id,
        "crosswalk_audit_report_id": crosswalk_report.report_id if crosswalk_report else None,
        "ocg_rule_ir_adoption_report_id": ocg_report.report_id if ocg_report else None,
        "blocker_count": blocker_count,
    }
    return QAReadinessReport(
        report_id="qa_readiness_" + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        generated_at=generated_at or now_iso(),
        status=status,
        ui_review_data_bundle_id=bundle.ui_review_data_bundle_id,
        crosswalk_audit_report_id=crosswalk_report.report_id if crosswalk_report else None,
        ocg_rule_ir_adoption_report_id=ocg_report.report_id if ocg_report else None,
        checks=checks,
        passed_check_count=passed_check_count,
        warning_count=warning_count,
        blocker_count=blocker_count,
        recommended_next_actions=_recommended_next_actions(checks),
        display_banner={
            "candidate_only": True,
            "synthetic_only": True,
            "read_only_evidence": True,
            "not_canon": True,
            "warning": (
                "Crosswalk and OCG adoption artifacts are candidate-only review evidence. "
                "They are not budget logic, carrier canon, or authorized for external submission."
            ),
            "status": status,
        },
    )


def build_qa_product_confidence_report(
    *,
    ui_review_data_bundle_path: str | Path,
    qa_readiness_report_path: str | Path,
    crosswalk_audit_path: str | Path | None = None,
    ocg_rule_ir_adoption_path: str | Path | None = None,
    generated_at: str | None = None,
) -> QAProductConfidenceReport:
    bundle = UIReviewDataBundle.model_validate(load_json(ui_review_data_bundle_path))
    readiness = QAReadinessReport.model_validate(load_json(qa_readiness_report_path))
    crosswalk_ref = (
        str(crosswalk_audit_path) if crosswalk_audit_path else bundle.crosswalk_audit_ref
    )
    ocg_ref = (
        str(ocg_rule_ir_adoption_path)
        if ocg_rule_ir_adoption_path
        else bundle.ocg_rule_ir_adoption_ref
    )
    gates: list[QAProductConfidenceGate] = [
        QAProductConfidenceGate(
            gate_id="qa_readiness_clear",
            label="QA readiness report clear",
            status="passed" if readiness.status != "blocked" else "blocked",
            summary=f"QA readiness status is {readiness.status}.",
            evidence_refs=[str(qa_readiness_report_path)],
        ),
        QAProductConfidenceGate(
            gate_id="crosswalk_evidence_gate",
            label="Standard crosswalk evidence gate",
            status=_gate_status_for_checks(
                [check for check in readiness.checks if check.check_id.startswith("crosswalk_")]
            ),
            summary="Crosswalk audit must pass with accepted_with_restrictions and zero violations.",
            evidence_refs=[crosswalk_ref] if crosswalk_ref else [],
        ),
        QAProductConfidenceGate(
            gate_id="ocg_adoption_evidence_gate",
            label="OCG rule IR adoption evidence gate",
            status=_gate_status_for_checks(
                [check for check in readiness.checks if check.check_id.startswith("ocg_")]
            ),
            summary="OCG adoption must be accepted_as_read_only_candidate from substrate owner.",
            evidence_refs=[ocg_ref] if ocg_ref else [],
        ),
        QAProductConfidenceGate(
            gate_id="ui_bundle_read_only_boundary",
            label="UI bundle read-only boundary",
            status=(
                "passed"
                if bundle.external_write_report_count == 0
                and bundle.unproven_detail_boundary_count == 0
                and bundle.status == "ready_for_review"
                else "blocked"
            ),
            summary=(
                "UI review bundle must have no prohibited write signals and every "
                "present detail must prove its candidate, synthetic, and no-write boundaries."
            ),
            evidence_refs=[str(ui_review_data_bundle_path)],
        ),
    ]
    blocker_count = sum(1 for gate in gates if gate.status == "blocked")
    passed_gate_count = sum(1 for gate in gates if gate.status == "passed")
    status = "ready_for_poc_review" if blocker_count == 0 else "blocked"
    report_core = {
        "status": status,
        "ui_review_data_bundle_id": bundle.ui_review_data_bundle_id,
        "qa_readiness_report_id": readiness.report_id,
        "blocker_count": blocker_count,
    }
    return QAProductConfidenceReport(
        report_id="qa_product_confidence_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        generated_at=generated_at or now_iso(),
        status=status,
        ui_review_data_bundle_id=bundle.ui_review_data_bundle_id,
        qa_readiness_report_id=readiness.report_id,
        crosswalk_audit_report_id=readiness.crosswalk_audit_report_id,
        ocg_rule_ir_adoption_report_id=readiness.ocg_rule_ir_adoption_report_id,
        gates=gates,
        passed_gate_count=passed_gate_count,
        blocker_count=blocker_count,
        recommended_next_actions=_recommended_next_actions_from_gates(gates),
        display_banner={
            "candidate_only": True,
            "synthetic_only": True,
            "not_production_ready": True,
            "crosswalk_and_ocg_are_review_evidence_only": True,
            "status": status,
        },
    )


def run_qa_readiness_report(
    *,
    ui_review_data_bundle_path: str | Path,
    out_dir: str | Path,
    crosswalk_audit_path: str | Path | None = None,
    ocg_rule_ir_adoption_path: str | Path | None = None,
    require_crosswalk_ocg: bool = False,
    generated_at: str | None = None,
) -> tuple[QAReadinessReport, Path]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_qa_readiness_report(
        ui_review_data_bundle_path=ui_review_data_bundle_path,
        crosswalk_audit_path=crosswalk_audit_path,
        ocg_rule_ir_adoption_path=ocg_rule_ir_adoption_path,
        require_crosswalk_ocg=require_crosswalk_ocg,
        generated_at=generated_at,
    )
    out_path = output_dir / QA_READINESS_REPORT_FILENAME
    write_json(out_path, report.model_dump(mode="json"))
    return report, out_path


def run_qa_product_confidence_report(
    *,
    ui_review_data_bundle_path: str | Path,
    qa_readiness_report_path: str | Path,
    out_dir: str | Path,
    crosswalk_audit_path: str | Path | None = None,
    ocg_rule_ir_adoption_path: str | Path | None = None,
    generated_at: str | None = None,
) -> tuple[QAProductConfidenceReport, Path]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_qa_product_confidence_report(
        ui_review_data_bundle_path=ui_review_data_bundle_path,
        qa_readiness_report_path=qa_readiness_report_path,
        crosswalk_audit_path=crosswalk_audit_path,
        ocg_rule_ir_adoption_path=ocg_rule_ir_adoption_path,
        generated_at=generated_at,
    )
    out_path = output_dir / QA_PRODUCT_CONFIDENCE_REPORT_FILENAME
    write_json(out_path, report.model_dump(mode="json"))
    return report, out_path


def _gate_status_for_checks(checks: list[QAReadinessCheck]) -> str:
    if not checks:
        return "blocked"
    if any(check.status == "blocked" for check in checks):
        return "blocked"
    return "passed"


def _recommended_next_actions(checks: list[QAReadinessCheck]) -> list[str]:
    blocked = [check for check in checks if check.status == "blocked"]
    if not blocked:
        return ["Crosswalk and OCG adoption evidence are attached for read-only UI review."]
    return [f"Resolve blocked check: {check.check_id} — {check.summary}" for check in blocked]


def _recommended_next_actions_from_gates(gates: list[QAProductConfidenceGate]) -> list[str]:
    blocked = [gate for gate in gates if gate.status == "blocked"]
    if not blocked:
        return ["Product-confidence gates include crosswalk and OCG adoption evidence."]
    return [f"Resolve blocked gate: {gate.gate_id} — {gate.summary}" for gate in blocked]
