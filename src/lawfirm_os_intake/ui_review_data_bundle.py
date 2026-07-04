from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import UIReviewDataBundle, UIReviewDataBundleDetailReport
from .util import digest_json, load_json, now_iso, write_json


UI_REVIEW_DATA_BUNDLE_FILENAME = "ui_review_data_bundle.json"


@dataclass(frozen=True)
class UIReviewDetailSpec:
    detail_report_id: str
    label: str
    report_kind: str
    file_name: str
    renderer: str
    required: bool = True


DETAIL_REPORT_SPECS = [
    UIReviewDetailSpec(
        detail_report_id="ui-review-manifest",
        label="UI Review Manifest",
        report_kind="ui_review_manifest",
        file_name="ui_review_manifest.json",
        renderer="RunOverviewPanels",
    ),
    UIReviewDetailSpec(
        detail_report_id="synthetic-qa-review-run",
        label="Synthetic QA Review Run",
        report_kind="synthetic_qa_review_run",
        file_name="synthetic_qa_review_run_report.json",
        renderer="SyntheticQAReviewRunPanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="synthetic-confidence-summary",
        label="Synthetic Confidence Summary",
        report_kind="synthetic_confidence_summary",
        file_name="synthetic_confidence_summary_report.json",
        renderer="SyntheticConfidenceSummaryPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="synthetic-qa-blocker-report",
        label="Synthetic QA Blocker Report",
        report_kind="synthetic_qa_blocker_report",
        file_name="synthetic_qa_blocker_report.json",
        renderer="SyntheticQABlockerDrilldownPanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="synthetic-qa-review-outcome",
        label="Synthetic QA Review Outcome",
        report_kind="synthetic_qa_review_outcome",
        file_name="synthetic_qa_review_outcome_report.json",
        renderer="SyntheticQAReviewOutcomePanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="matter-linking-preflight",
        label="Matter-Linking Preflight",
        report_kind="matter_linking_preflight",
        file_name="matter_linking_preflight_report.json",
        renderer="MatterLinkingPreflightPanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="matter-linking-review-outcome",
        label="Matter-Linking Review Outcome",
        report_kind="matter_linking_review_outcome",
        file_name="matter_linking_review_outcome_report.json",
        renderer="MatterLinkingReviewOutcomePanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="matter-linking-qa-gate",
        label="Matter-Linking QA Gate",
        report_kind="matter_linking_qa_gate",
        file_name="matter_linking_qa_gate_report.json",
        renderer="MatterLinkingQAGatePanel",
        required=False,
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-qa-matrix",
        label="L&E Budget Fact QA",
        report_kind="labor_employment_qa_matrix",
        file_name="labor_employment_qa_matrix_report.json",
        renderer="LaborEmploymentMatrixPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-executable-coverage",
        label="L&E Executable Coverage",
        report_kind="labor_employment_executable_coverage",
        file_name="labor_employment_executable_coverage_report.json",
        renderer="LaborEmploymentExecutableCoveragePanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-blocked-driver-impact-review",
        label="L&E Blocked Driver Review",
        report_kind="labor_employment_blocked_driver_impact_review",
        file_name="labor_employment_blocked_driver_impact_review_report.json",
        renderer="LaborEmploymentBlockedDriverPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-budget-output-expectations",
        label="L&E Budget Output Expectations",
        report_kind="labor_employment_budget_output_expectations",
        file_name="labor_employment_budget_output_expectations_report.json",
        renderer="LaborEmploymentBudgetOutputExpectationsPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-budget-qa-gate",
        label="L&E Budget QA Gate",
        report_kind="labor_employment_budget_qa_gate",
        file_name="labor_employment_budget_qa_gate_report.json",
        renderer="LaborEmploymentBudgetQAGatePanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-budget-learning-fixtures",
        label="L&E Budget Learning Fixtures",
        report_kind="labor_employment_budget_learning_fixtures",
        file_name="labor_employment_budget_learning_fixtures_report.json",
        renderer="LaborEmploymentBudgetLearningFixturesPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-budget-outcome-replay-readiness",
        label="L&E Budget Outcome Replay Readiness",
        report_kind="labor_employment_budget_outcome_replay_readiness",
        file_name="labor_employment_budget_outcome_replay_readiness_report.json",
        renderer="LaborEmploymentBudgetOutcomeReplayReadinessPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="labor-employment-budget-outcome-replay-execution",
        label="L&E Budget Outcome Replay Execution",
        report_kind="labor_employment_budget_outcome_replay_execution",
        file_name="labor_employment_budget_outcome_replay_execution_report.json",
        renderer="LaborEmploymentBudgetOutcomeReplayExecutionPanel",
    ),
    UIReviewDetailSpec(
        detail_report_id="budget-learning-loop",
        label="Budget Learning Loop",
        report_kind="budget_learning_loop",
        file_name="budget_learning_loop_report.json",
        renderer="BudgetLearningLoopPanel",
    ),
]


def build_ui_review_data_bundle(
    *,
    run_root: str | Path,
    out_path: str | Path,
    generated_at: str | None = None,
) -> UIReviewDataBundle:
    root = Path(run_root)
    details = [_detail_report(root, spec) for spec in DETAIL_REPORT_SPECS]
    missing_required = [detail for detail in details if detail.required and not detail.present]
    external_write_reports = [detail for detail in details if detail.external_writes_performed]
    if external_write_reports:
        status = "failed_side_effect_boundary"
    elif missing_required:
        status = "blocked_missing_required_reports"
    else:
        status = "ready_for_review"
    report_core = {
        "status": status,
        "run_root_ref": str(root),
        "detail_reports": [
            {
                "detail_report_id": detail.detail_report_id,
                "present": detail.present,
                "source_sha256": detail.source_sha256,
                "external_writes_performed": detail.external_writes_performed,
            }
            for detail in details
        ],
    }
    bundle = UIReviewDataBundle(
        ui_review_data_bundle_id="ui_review_data_bundle_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 12],
        status=status,
        run_root_ref=str(root),
        detail_report_count=len(details),
        required_detail_report_count=sum(1 for detail in details if detail.required),
        present_detail_report_count=sum(1 for detail in details if detail.present),
        missing_required_detail_report_count=len(missing_required),
        external_write_report_count=len(external_write_reports),
        detail_reports=details,
        required_next_actions=_required_next_actions(
            missing_required=missing_required,
            external_write_reports=external_write_reports,
        ),
        generated_at=generated_at or now_iso(),
    )
    write_json(out_path, bundle.model_dump(mode="json"))
    return bundle


def _detail_report(root: Path, spec: UIReviewDetailSpec) -> UIReviewDataBundleDetailReport:
    found = _find_artifact(root, spec.file_name)
    if found is None:
        return UIReviewDataBundleDetailReport(
            detail_report_id=spec.detail_report_id,
            label=spec.label,
            report_kind=spec.report_kind,
            file_name=spec.file_name,
            required=spec.required,
            present=False,
            status="missing",
            renderer=spec.renderer,
            candidate_only=True,
            synthetic_only=True,
            external_writes_performed=False,
            notes=[f"{spec.file_name} was not found under the local run root."],
        )
    payload = _safe_load_json(found)
    return UIReviewDataBundleDetailReport(
        detail_report_id=spec.detail_report_id,
        label=spec.label,
        report_kind=spec.report_kind,
        file_name=spec.file_name,
        required=spec.required,
        present=True,
        status=_status_from_payload(payload),
        renderer=spec.renderer,
        artifact_ref=str(found),
        source_sha256=_sha256_file(found),
        candidate_only=_candidate_only(payload),
        synthetic_only=_synthetic_only(payload, spec.report_kind),
        external_writes_performed=_external_writes_performed(payload),
        notes=[_note(root=root, path=found, payload=payload)],
    )


def _find_artifact(root: Path, file_name: str) -> Path | None:
    direct_candidates = [
        root / file_name,
        root / "budget" / file_name,
        root / "quality" / file_name,
        root / "qa" / file_name,
    ]
    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate
    matches = [path for path in root.rglob(file_name) if path.is_file()]
    if not matches:
        return None
    return sorted(matches, key=lambda path: (len(path.parts), str(path)))[0]


def _safe_load_json(path: Path) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return {"status": "failed", "load_error": f"could not read JSON: {path}"}
    return (
        payload
        if isinstance(payload, dict)
        else {"status": "failed", "load_error": "not an object"}
    )


def _status_from_payload(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("overallStatus") or "present")


def _candidate_only(payload: dict[str, Any]) -> bool:
    return payload.get("candidate_only", payload.get("candidateOnly", True)) is not False


def _synthetic_only(payload: dict[str, Any], report_kind: str) -> bool:
    if report_kind == "ui_review_manifest":
        return True
    return payload.get("synthetic_only", True) is not False


def _external_writes_performed(payload: dict[str, Any]) -> bool:
    write_keys = [
        "external_writes_performed",
        "sqlite_write_performed",
        "lake_write_performed",
        "client_submission_performed",
        "carrier_submission_performed",
        "billing_handoff_performed",
        "fixture_files_mutated",
        "github_pr_created",
    ]
    return any(payload.get(key) is True for key in write_keys)


def _note(*, root: Path, path: Path, payload: dict[str, Any]) -> str:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    status = payload.get("status") or payload.get("overallStatus") or "status not declared"
    return f"Found {relative}; status={status}."


def _required_next_actions(
    *,
    missing_required: list[UIReviewDataBundleDetailReport],
    external_write_reports: list[UIReviewDataBundleDetailReport],
) -> list[str]:
    if external_write_reports:
        return [
            f"Remove or quarantine UI detail report with prohibited write signal: {report.file_name}"
            for report in external_write_reports
        ]
    if missing_required:
        return [
            f"Generate local UI detail report before relying on the review surface: {report.file_name}"
            for report in missing_required
        ]
    return ["UI review data bundle is ready for read-only local review."]


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()
