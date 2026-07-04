from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    LaborEmploymentBlockedDriverImpactReviewReport,
    LaborEmploymentBudgetOutputExpectationReport,
    LaborEmploymentBudgetQAGateReport,
    LaborEmploymentQAMatrixReport,
    MatterLinkingPreflightReport,
    POCQATriageItem,
    POCQATriageReport,
    SyntheticConfidenceSummaryReport,
    SyntheticQABlockerReport,
    SyntheticQAReviewRunReport,
    UIReviewDataBundle,
    ValidationSuiteEvidenceReport,
)
from .util import digest_json, load_json, now_iso, write_json


POC_QA_TRIAGE_REPORT_FILENAME = "poc_qa_triage_report.json"


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _manifest_artifact(manifest: dict[str, Any], file_name: str) -> dict[str, Any] | None:
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        return None
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("fileName") == file_name:
            return artifact
    return None


def _manifest_gate(manifest: dict[str, Any], gate_id: str) -> dict[str, Any] | None:
    gates = manifest.get("qualityGates", [])
    if not isinstance(gates, list):
        return None
    for gate in gates:
        if isinstance(gate, dict) and gate.get("gateId") == gate_id:
            return gate
    return None


def _all_no_write(*reports: Any) -> bool:
    return all(
        getattr(report, "budget_submission_authorized", False) is False
        and getattr(report, "matter_opening_authorized", False) is False
        and getattr(report, "lake_write_performed", False) is False
        and getattr(report, "sqlite_write_performed", False) is False
        and getattr(report, "external_writes_performed", False) is False
        and getattr(report, "silent_learning_performed", False) is False
        for report in reports
    )


def _validation_step_passed(
    validation_evidence: ValidationSuiteEvidenceReport | None, step_id: str
) -> bool:
    if validation_evidence is None or validation_evidence.status != "validation_suite_passed":
        return False
    return any(
        step.step_id == step_id and step.status == "passed" for step in validation_evidence.steps
    )


def _item(
    *,
    item_id: str,
    category: str,
    priority: str,
    status: str,
    summary: str,
    recommended_next_action: str,
    evidence_refs: list[str],
    candidate_exception_lake_labels: list[str] | None = None,
) -> POCQATriageItem:
    return POCQATriageItem(
        item_id=item_id,
        category=category,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        summary=summary,
        recommended_next_action=recommended_next_action,
        evidence_refs=evidence_refs,
        candidate_exception_lake_labels=candidate_exception_lake_labels or [],
    )


def build_poc_qa_triage_report(
    *,
    ui_manifest_path: str | Path,
    synthetic_confidence_summary_path: str | Path,
    synthetic_qa_review_run_path: str | Path,
    synthetic_qa_blocker_report_path: str | Path,
    ui_review_data_bundle_path: str | Path,
    matter_linking_preflight_path: str | Path,
    labor_employment_qa_matrix_path: str | Path,
    blocked_driver_impact_review_path: str | Path,
    budget_output_expectations_path: str | Path,
    budget_qa_gate_path: str | Path,
    validation_suite_evidence_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    generated_at: str | None = None,
) -> POCQATriageReport:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    paths = {
        "ui_manifest": Path(ui_manifest_path),
        "confidence": Path(synthetic_confidence_summary_path),
        "review_run": Path(synthetic_qa_review_run_path),
        "blocker": Path(synthetic_qa_blocker_report_path),
        "bundle": Path(ui_review_data_bundle_path),
        "matter": Path(matter_linking_preflight_path),
        "matrix": Path(labor_employment_qa_matrix_path),
        "blocked_driver": Path(blocked_driver_impact_review_path),
        "budget_output": Path(budget_output_expectations_path),
        "budget_qa_gate": Path(budget_qa_gate_path),
    }
    if validation_suite_evidence_path is not None:
        paths["validation"] = Path(validation_suite_evidence_path)
    refs = {key: _relative(path, root) for key, path in paths.items()}

    manifest = load_json(paths["ui_manifest"])
    if not isinstance(manifest, dict):
        raise ValueError("UI manifest must be a JSON object")
    confidence = SyntheticConfidenceSummaryReport.model_validate(load_json(paths["confidence"]))
    review_run = SyntheticQAReviewRunReport.model_validate(load_json(paths["review_run"]))
    blocker = SyntheticQABlockerReport.model_validate(load_json(paths["blocker"]))
    bundle = UIReviewDataBundle.model_validate(load_json(paths["bundle"]))
    matter = MatterLinkingPreflightReport.model_validate(load_json(paths["matter"]))
    matrix = LaborEmploymentQAMatrixReport.model_validate(load_json(paths["matrix"]))
    blocked_driver = LaborEmploymentBlockedDriverImpactReviewReport.model_validate(
        load_json(paths["blocked_driver"])
    )
    budget_output = LaborEmploymentBudgetOutputExpectationReport.model_validate(
        load_json(paths["budget_output"])
    )
    budget_qa_gate = LaborEmploymentBudgetQAGateReport.model_validate(
        load_json(paths["budget_qa_gate"])
    )
    validation_evidence = (
        ValidationSuiteEvidenceReport.model_validate(load_json(paths["validation"]))
        if "validation" in paths
        else None
    )

    boundary_flags = manifest.get("boundaryFlags", {})
    if not isinstance(boundary_flags, dict):
        boundary_flags = {}
    matter_opening_artifact = _manifest_artifact(manifest, "matter_opening_readiness.json")
    full_pytest_gate = _manifest_gate(manifest, "full_pytest")
    smoke_demo_gate = _manifest_gate(manifest, "smoke_demo")
    validation_evidence_gate = _manifest_gate(manifest, "validation_suite_evidence")
    public_cache_artifact = _manifest_artifact(manifest, "public_data_cache_audit_report.json")

    blocked_budget_cases = [
        case
        for case in budget_output.cases
        if case.final_allowed_budget_output == "blocked_amount_budget"
    ]
    candidate_range_cases = [
        case
        for case in budget_output.cases
        if case.final_allowed_budget_output == "candidate_range_after_review_pending_human_review"
    ]
    matrix_has_blocking_case = any(
        case.actual_budget_gate_effect == "block_amount_budget_before_proposal"
        for case in matrix.cases
    )
    matrix_has_range_case = any(
        case.actual_budget_gate_effect == "allow_range_or_hours_only_pending_review"
        for case in matrix.cases
    )
    validation_evidence_ready = (
        full_pytest_gate is not None
        and full_pytest_gate.get("status") == "passed"
        and smoke_demo_gate is not None
        and smoke_demo_gate.get("status") == "passed"
        and validation_evidence_gate is not None
        and validation_evidence_gate.get("status") == "passed"
        and _validation_step_passed(validation_evidence, "full_pytest")
        and _validation_step_passed(validation_evidence, "smoke_demo")
        and validation_evidence is not None
        and validation_evidence.failed_step_count == 0
        and validation_evidence.timed_out_step_count == 0
        and _all_no_write(validation_evidence)
    )

    items = [
        _item(
            item_id="synthetic_qa_recipe_green",
            category="synthetic_qa",
            priority="p0",
            status=(
                "passed"
                if confidence.status == "synthetic_confidence_summary_ready_for_review"
                and review_run.status == "synthetic_qa_review_run_ready"
                and review_run.failed_step_count == 0
                and confidence.top_blockers == []
                else "blocked"
            ),
            summary=(
                "Synthetic QA review run and confidence summary are green."
                if review_run.failed_step_count == 0 and confidence.top_blockers == []
                else "Synthetic QA review run or confidence summary has blockers."
            ),
            recommended_next_action=(
                "Use the read-only dashboard as the synthetic QA starting point."
                if review_run.failed_step_count == 0 and confidence.top_blockers == []
                else "Repair failed synthetic QA steps before expanding the corpus."
            ),
            evidence_refs=[refs["confidence"], refs["review_run"]],
            candidate_exception_lake_labels=["synthetic_qa_recipe_blocked"],
        ),
        _item(
            item_id="qa_review_queue_visible",
            category="review_queue",
            priority="p0",
            status=(
                "needs_review"
                if blocker.status == "synthetic_qa_blocker_report_ready_for_review"
                and blocker.failed_row_count == 0
                and blocker.blocked_row_count == 0
                and blocker.needs_review_action_count == blocker.pending_review_row_count
                and blocker.pending_review_row_count > 0
                else "blocked"
            ),
            summary=(
                f"{blocker.pending_review_row_count} synthetic QA rows are queued for review."
            ),
            recommended_next_action=(
                "Review pending rows as candidate QA decisions; do not treat them as calibration or production approval."
            ),
            evidence_refs=[refs["blocker"]],
            candidate_exception_lake_labels=[
                "synthetic_qa_pending_human_review",
                "candidate_review_queue_visible",
            ],
        ),
        _item(
            item_id="ui_review_bundle_ready",
            category="review_queue",
            priority="p1",
            status=(
                "passed"
                if bundle.status == "ready_for_review"
                and bundle.missing_required_detail_report_count == 0
                and bundle.external_write_report_count == 0
                else "blocked"
            ),
            summary="Read-only UI review bundle has required detail reports and no external-write reports.",
            recommended_next_action="Keep UI inputs local JSON only and regenerate the bundle after any report changes.",
            evidence_refs=[refs["bundle"]],
            candidate_exception_lake_labels=["ui_review_bundle_gap"],
        ),
        _item(
            item_id="matter_linking_requires_human_confirmation",
            category="matter_linking",
            priority="p0",
            status=(
                "needs_review"
                if matter.requires_human_confirmation
                and matter.cluster_count >= 2
                and not matter.matter_opening_authorized
                and not matter.budget_amount_output_authorized
                else "blocked"
            ),
            summary=(
                "Upfront-like matter linking produces split candidate clusters and requires human confirmation."
            ),
            recommended_next_action="Use this as the no-matter-number follow-up queue before budget or matter-opening work.",
            evidence_refs=[refs["matter"]],
            candidate_exception_lake_labels=list(matter.candidate_exception_lake_labels),
        ),
        _item(
            item_id="labor_employment_fact_gates_visible",
            category="labor_employment_budget_facts",
            priority="p0",
            status=(
                "needs_review"
                if matrix.status == "labor_employment_qa_matrix_ready_for_review"
                and matrix.failed_case_count == 0
                and matrix_has_blocking_case
                and matrix_has_range_case
                else "blocked"
            ),
            summary="L&E fact QA shows both amount-blocking critical gaps and range-only review states.",
            recommended_next_action="Expand from this matrix into broader L&E synthetic fixtures before real-document pilots.",
            evidence_refs=[refs["matrix"]],
            candidate_exception_lake_labels=[
                "labor_employment_budget_fact_review_required",
                "labor_employment_critical_budget_fact_block",
            ],
        ),
        _item(
            item_id="blocked_driver_review_queue_visible",
            category="labor_employment_budget_facts",
            priority="p0",
            status=(
                "needs_review"
                if blocked_driver.status
                == "labor_employment_blocked_driver_impacts_ready_for_review"
                and blocked_driver.blocked_case_count > 0
                and blocked_driver.block_amount_budget_impact_count > 0
                else "blocked"
            ),
            summary=(
                f"{blocked_driver.blocked_case_count} L&E cases block amount budgets until driver facts are resolved."
            ),
            recommended_next_action="Treat these as the first budget-driver review queue and follow-up action seeds.",
            evidence_refs=[refs["blocked_driver"]],
            candidate_exception_lake_labels=list(blocked_driver.candidate_exception_lake_labels),
        ),
        _item(
            item_id="budget_output_partition_visible",
            category="budget_output",
            priority="p0",
            status=(
                "needs_review"
                if budget_output.status
                == "labor_employment_budget_output_expectations_ready_for_review"
                and budget_output.failed_case_count == 0
                and len(blocked_budget_cases) == budget_output.blocked_amount_budget_case_count
                and len(candidate_range_cases)
                == budget_output.candidate_range_after_review_case_count
                and _all_no_write(budget_output)
                else "blocked"
            ),
            summary=(
                f"{budget_output.blocked_amount_budget_case_count} cases block amount budgets; "
                f"{budget_output.candidate_range_after_review_case_count} cases allow candidate ranges after review."
            ),
            recommended_next_action="Only consume reviewed nonblocking slices for budget generation; keep blocked cases as follow-up queues.",
            evidence_refs=[refs["budget_output"]],
            candidate_exception_lake_labels=list(budget_output.candidate_exception_lake_labels),
        ),
        _item(
            item_id="labor_employment_budget_qa_gate_ready",
            category="budget_qa_gate",
            priority="p0",
            status=(
                "needs_review"
                if budget_qa_gate.status == "labor_employment_budget_qa_gate_ready_for_review"
                and all(check.status == "passed" for check in budget_qa_gate.checks)
                and budget_qa_gate.source_budget_output_expectations_report_id
                == budget_output.budget_output_expectation_report_id
                and budget_qa_gate.source_blocked_driver_impact_review_report_id
                == blocked_driver.blocked_driver_impact_review_report_id
                and budget_qa_gate.blocked_amount_budget_case_count
                == budget_output.blocked_amount_budget_case_count
                and budget_qa_gate.range_or_hours_only_case_count
                == budget_output.range_or_hours_only_case_count
                and budget_qa_gate.candidate_range_after_review_case_count
                == budget_output.candidate_range_after_review_case_count
                and _all_no_write(budget_qa_gate)
                else "blocked"
            ),
            summary=(
                "Aggregate L&E budget QA gate is ready and directly ties output, blocked-driver, and coverage evidence."
            ),
            recommended_next_action=(
                "Use this aggregate gate as the top-level budget QA checkpoint before fixture expansion, benchmark replay, or UI review."
            ),
            evidence_refs=[refs["budget_qa_gate"]],
            candidate_exception_lake_labels=list(budget_qa_gate.candidate_exception_lake_labels),
        ),
        _item(
            item_id="public_data_boundary_not_runtime",
            category="public_data_boundary",
            priority="watch",
            status="watch",
            summary=(
                "Public-data cache evidence is still a pending methodology gate and public records are not runtime intake."
            ),
            recommended_next_action="Keep public datasets in ignored caches and convert only reviewed structures into synthetic fixtures.",
            evidence_refs=[refs["ui_manifest"]],
            candidate_exception_lake_labels=(
                ["public_data_cache_review_pending"]
                if public_cache_artifact is None
                or public_cache_artifact.get("gateState") != "passed"
                else []
            ),
        ),
        _item(
            item_id="validation_evidence_not_fresh_in_ui_bundle",
            category="review_queue",
            priority="p0",
            status="passed" if validation_evidence_ready else "blocked",
            summary=(
                "Fresh wrapper-based validation evidence is attached to the UI manifest."
                if validation_evidence_ready
                else "The UI manifest does not yet prove fresh full-pytest and smoke-demo validation evidence."
            ),
            recommended_next_action=(
                "Keep regenerating validation_suite_evidence_report.json after substantial QA, schema, or UI changes."
                if validation_evidence_ready
                else "Run the wrapper-based validation suite with the long timeout ceiling and regenerate UI/triage fixtures from that run."
            ),
            evidence_refs=[
                refs["ui_manifest"],
                *([refs["validation"]] if "validation" in refs else []),
                "scripts/run_full_pytest.py",
                "scripts/smoke_demo.sh",
            ],
            candidate_exception_lake_labels=(
                []
                if validation_evidence_ready
                else [
                    "qa_validation_evidence_stale_or_missing",
                    "ui_manifest_validation_gap",
                ]
            ),
        ),
        _item(
            item_id="production_actions_stay_blocked",
            category="production_boundary",
            priority="watch",
            status="watch",
            summary="Production actions remain blocked: no Lake write, budget submission, matter opening, or public runtime ingestion.",
            recommended_next_action="Promote contracts through owner repos before adding connectors or production authority.",
            evidence_refs=[refs["ui_manifest"], refs["confidence"]],
            candidate_exception_lake_labels=[
                "real_data_pilot_not_authorized",
                "production_release_not_authorized",
            ],
        ),
    ]

    if boundary_flags.get("publicRuntimeIngestionAllowed") is not False:
        items.append(
            _item(
                item_id="public_runtime_ingestion_boundary_failed",
                category="public_data_boundary",
                priority="p0",
                status="blocked",
                summary="UI manifest allows public runtime ingestion.",
                recommended_next_action="Restore publicRuntimeIngestionAllowed=false before using any public methodology fixture.",
                evidence_refs=[refs["ui_manifest"]],
                candidate_exception_lake_labels=["public_runtime_ingestion_boundary_failed"],
            )
        )
    if matter_opening_artifact and matter_opening_artifact.get("gateState") != "blocked":
        items.append(
            _item(
                item_id="matter_opening_boundary_failed",
                category="production_boundary",
                priority="p0",
                status="blocked",
                summary="Matter-opening readiness is not blocked in the UI manifest.",
                recommended_next_action="Restore the matter-opening blocker until conflicts and engagement authority exist.",
                evidence_refs=[refs["ui_manifest"]],
                candidate_exception_lake_labels=["matter_opening_boundary_failed"],
            )
        )

    blocked_count = sum(1 for item in items if item.status == "blocked")
    needs_review_count = sum(1 for item in items if item.status == "needs_review")
    watch_count = sum(1 for item in items if item.status == "watch")
    passed_count = sum(1 for item in items if item.status == "passed")
    p0_blocked_count = sum(
        1 for item in items if item.status == "blocked" and item.priority == "p0"
    )
    status = "blocked_by_poc_qa_triage" if blocked_count else "poc_qa_ready_for_review"
    generated = generated_at or now_iso()
    blocked_action = (
        "Resolve blocked triage items before calling this POC QA-ready."
        if blocked_count
        else "No blocked POC QA triage items remain; review needs-review items as candidate QA decisions."
    )
    report_basis = {
        "generated_at": generated,
        "status": status,
        "items": [(item.item_id, item.status) for item in items],
    }

    return POCQATriageReport(
        poc_qa_triage_report_id="poc_qa_triage_"
        + digest_json(report_basis).removeprefix("sha256:")[:16],
        status=status,
        source_ui_manifest_id=str(manifest.get("manifestId")),
        source_synthetic_confidence_summary_report_id=(
            confidence.synthetic_confidence_summary_report_id
        ),
        source_synthetic_qa_review_run_report_id=review_run.synthetic_qa_review_run_report_id,
        source_synthetic_qa_blocker_report_id=blocker.synthetic_qa_blocker_report_id,
        source_matter_linking_preflight_report_id=matter.matter_linking_preflight_report_id,
        source_labor_employment_qa_matrix_report_id=matrix.labor_employment_qa_matrix_report_id,
        source_blocked_driver_impact_review_report_id=(
            blocked_driver.blocked_driver_impact_review_report_id
        ),
        source_budget_output_expectation_report_id=(
            budget_output.budget_output_expectation_report_id
        ),
        source_budget_qa_gate_report_id=budget_qa_gate.budget_qa_gate_report_id,
        source_validation_suite_evidence_report_id=(
            validation_evidence.validation_suite_evidence_report_id
            if validation_evidence is not None
            else None
        ),
        item_count=len(items),
        passed_item_count=passed_count,
        needs_review_item_count=needs_review_count,
        watch_item_count=watch_count,
        blocked_item_count=blocked_count,
        p0_blocked_item_count=p0_blocked_count,
        items=items,
        required_next_actions=[
            blocked_action,
            "Review needs-review items as candidate QA decisions, not production approval.",
            "Keep watch items on the roadmap for real-data, owner-adoption, and production gates.",
            "Regenerate this report whenever synthetic QA, UI, or validation evidence changes.",
        ],
        display_banner={
            "summary": "POC QA triage over local synthetic evidence.",
            "status": status,
            "candidate_only": True,
            "synthetic_only": True,
            "not_production_ready": True,
            "blocked_actions": [
                "lake_write",
                "sqlite_write",
                "budget_submission",
                "matter_opening",
                "conflict_conclusion",
                "public_runtime_ingestion",
                "model_training",
            ],
        },
        generated_at=generated,
    )


def run_poc_qa_triage_report(
    *,
    out_dir: str | Path,
    ui_manifest_path: str | Path,
    synthetic_confidence_summary_path: str | Path,
    synthetic_qa_review_run_path: str | Path,
    synthetic_qa_blocker_report_path: str | Path,
    ui_review_data_bundle_path: str | Path,
    matter_linking_preflight_path: str | Path,
    labor_employment_qa_matrix_path: str | Path,
    blocked_driver_impact_review_path: str | Path,
    budget_output_expectations_path: str | Path,
    budget_qa_gate_path: str | Path,
    validation_suite_evidence_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    generated_at: str | None = None,
) -> tuple[POCQATriageReport, Path]:
    report = build_poc_qa_triage_report(
        ui_manifest_path=ui_manifest_path,
        synthetic_confidence_summary_path=synthetic_confidence_summary_path,
        synthetic_qa_review_run_path=synthetic_qa_review_run_path,
        synthetic_qa_blocker_report_path=synthetic_qa_blocker_report_path,
        ui_review_data_bundle_path=ui_review_data_bundle_path,
        matter_linking_preflight_path=matter_linking_preflight_path,
        labor_employment_qa_matrix_path=labor_employment_qa_matrix_path,
        blocked_driver_impact_review_path=blocked_driver_impact_review_path,
        budget_output_expectations_path=budget_output_expectations_path,
        budget_qa_gate_path=budget_qa_gate_path,
        validation_suite_evidence_path=validation_suite_evidence_path,
        repo_root=repo_root,
        generated_at=generated_at,
    )
    run_dir = Path(out_dir)
    write_json(run_dir / POC_QA_TRIAGE_REPORT_FILENAME, report.model_dump(mode="json"))
    return report, run_dir
