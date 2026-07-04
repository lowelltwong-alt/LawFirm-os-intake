from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import shutil
from typing import Any

from .models import SyntheticQABundleArtifact, SyntheticQABundleReport
from .synthetic_fixture_depth_audit import (
    SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME,
    run_synthetic_fixture_depth_audit,
)
from .ui_review_data_bundle import (
    UI_REVIEW_DATA_BUNDLE_FILENAME,
    build_ui_review_data_bundle,
)
from .ui_review_manifest import build_ui_review_manifest
from .util import digest_json, load_json, now_iso, write_json


SYNTHETIC_QA_BUNDLE_REPORT_FILENAME = "synthetic_qa_bundle_report.json"
SYNTHETIC_QA_BUNDLE_NOTES_FILENAME = "synthetic_qa_bundle_report.md"


@dataclass(frozen=True)
class QABundleArtifactSpec:
    artifact_id: str
    label: str
    file_name: str
    required: bool
    missing_note: str


QA_BUNDLE_ARTIFACTS = [
    QABundleArtifactSpec(
        artifact_id="budget_coherence",
        label="Budget Coherence",
        file_name="budget_coherence_report.json",
        required=True,
        missing_note="Run validate-budget-artifact against the serialized budget proposal.",
    ),
    QABundleArtifactSpec(
        artifact_id="synthetic_fixture_depth",
        label="Synthetic Fixture Depth",
        file_name=SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME,
        required=True,
        missing_note=(
            "Run audit-synthetic-fixture-depth or pass --fixture-depth-manifest so the "
            "bundle can generate it."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="budget_calibration_readiness",
        label="Budget Calibration Readiness",
        file_name="budget_calibration_readiness_report.json",
        required=True,
        missing_note=(
            "Build the synthetic calibration corpus/replay/review chain before treating "
            "budget calibration as ready."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_qa_matrix",
        label="Labor/Employment QA Matrix",
        file_name="labor_employment_qa_matrix_report.json",
        required=True,
        missing_note=(
            "Run build-labor-employment-qa-matrix so L&E critical-fact blockers and "
            "range-only review posture are visible."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_fixture_family_pack",
        label="Labor/Employment Fixture Family Pack",
        file_name="labor_employment_fixture_family_pack_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-fixture-family-pack so L&E synthetic "
            "family/variant/fact-need coverage is visible."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_executable_fixtures",
        label="Labor/Employment Executable Fixtures",
        file_name="labor_employment_executable_fixtures_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-executable-fixtures so selected L&E "
            "source bundles prove they execute through deterministic preflight."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_executable_coverage",
        label="Labor/Employment Executable Coverage",
        file_name="labor_employment_executable_coverage_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-executable-coverage so QA can see which "
            "L&E family-pack cases are not yet executable source bundles."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_executable_fact_binding",
        label="Labor/Employment Executable Fact Binding",
        file_name="labor_employment_executable_fact_binding_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-executable-fact-binding so executable "
            "preflight evidence is bound to expected L&E budget-fact gaps."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_executable_driver_binding",
        label="Labor/Employment Executable Driver Binding",
        file_name="labor_employment_executable_driver_binding_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-executable-driver-binding so executable "
            "fact-gap evidence is mapped to L&E budget-driver focus dimensions."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_executable_driver_impact",
        label="Labor/Employment Executable Driver Impact",
        file_name="labor_employment_executable_driver_impact_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-executable-driver-impact so executable "
            "driver bindings declare candidate budget blockers, range widening, "
            "scenario forks, and rate/guideline review effects."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_driver_impact_review",
        label="Labor/Employment Driver Impact Review",
        file_name="labor_employment_driver_impact_review_report.json",
        required=True,
        missing_note=(
            "Run review-labor-employment-driver-impact-slice so nonblocking "
            "driver-impact budget-gate replay is backed by reviewed synthetic evidence."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_blocked_driver_impact_review",
        label="Labor/Employment Blocked Driver Impact Review",
        file_name="labor_employment_blocked_driver_impact_review_report.json",
        required=True,
        missing_note=(
            "Run review-labor-employment-blocked-driver-impacts so blocked L&E "
            "amount-budget cases have deterministic blocker facts, follow-up actions, "
            "and candidate Lake labels."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_budget_output_expectations",
        label="Labor/Employment Budget Output Expectations",
        file_name="labor_employment_budget_output_expectations_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-budget-output-expectations so every "
            "executable L&E case has one allowed budget-output state, candidate "
            "Lake labels, and next gates before the UI treats QA as complete."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_budget_qa_gate",
        label="Labor/Employment Budget QA Gate",
        file_name="labor_employment_budget_qa_gate_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-budget-qa-gate so L&E blocked, "
            "range-only, candidate-range, coverage, and no-write states are "
            "aggregated before budget QA is trusted."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_budget_learning_fixtures",
        label="Labor/Employment Budget Learning Fixtures",
        file_name="labor_employment_budget_learning_fixtures_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-budget-learning-fixtures so L&E actuals, "
            "carrier rejection, appeal, reviewed-learning, and blocked-budget guard "
            "fixture coverage is visible before calibration work."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_budget_outcome_replay_readiness",
        label="Labor/Employment Budget Outcome Replay Readiness",
        file_name="labor_employment_budget_outcome_replay_readiness_report.json",
        required=True,
        missing_note=(
            "Run audit-labor-employment-budget-outcome-replay-readiness so L&E "
            "actuals, carrier rejection, appeal, reviewed-learning, and blocked "
            "guard fixture intents have concrete synthetic replay seeds before "
            "calibration or model comparison."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="labor_employment_budget_fact_gold",
        label="Labor/Employment Budget Fact Gold",
        file_name="labor_employment_budget_fact_gold_report.json",
        required=True,
        missing_note=(
            "Run validate-labor-employment-budget-fact-gold so L&E budget fact "
            "audit outputs are checked against reviewed synthetic gold."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="budget_learning_loop",
        label="Budget Learning Loop",
        file_name="budget_learning_loop_report.json",
        required=True,
        missing_note=(
            "Run build-budget-learning-loop-report so budget actual variance, carrier "
            "rejection, appeal outcome, and reviewed-learning gates are part of the "
            "synthetic QA proof."
        ),
    ),
    QABundleArtifactSpec(
        artifact_id="matter_linking_qa_gate",
        label="Matter-Linking QA Gate",
        file_name="matter_linking_qa_gate_report.json",
        required=True,
        missing_note=(
            "Run audit-matter-linking-qa-gate so Upfront-like matching fixtures "
            "prove ambiguous, resolved, weak-only, and conflicting-identifier states."
        ),
    ),
]


def run_synthetic_qa_bundle(
    *,
    run_root: str | Path,
    out_dir: str | Path,
    budget_coherence_report_path: str | Path | None = None,
    fixture_depth_report_path: str | Path | None = None,
    fixture_depth_manifest_path: str | Path | None = None,
    repo_root: str | Path = ".",
    budget_calibration_readiness_report_path: str | Path | None = None,
    ui_manifest_out: str | Path | None = None,
    generated_at: str | None = None,
) -> tuple[SyntheticQABundleReport, Path, dict[str, Any] | None]:
    root = Path(run_root).resolve()
    output_dir = Path(out_dir).resolve()
    if not output_dir.is_relative_to(root):
        raise ValueError("synthetic QA bundle out_dir must be under run_root")
    if fixture_depth_report_path and fixture_depth_manifest_path:
        raise ValueError("use either --fixture-depth-report or --fixture-depth-manifest, not both")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_fixture_depth_report: Path | None = None
    if fixture_depth_manifest_path:
        _, fixture_depth_dir = run_synthetic_fixture_depth_audit(
            manifest_path=fixture_depth_manifest_path,
            repo_root=repo_root,
            out_dir=output_dir,
        )
        generated_fixture_depth_report = (
            fixture_depth_dir / SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME
        )

    source_paths = {
        "budget_coherence": _resolve_artifact_source(
            root=root,
            explicit_path=budget_coherence_report_path,
            file_name="budget_coherence_report.json",
        ),
        "synthetic_fixture_depth": _resolve_artifact_source(
            root=root,
            explicit_path=fixture_depth_report_path or generated_fixture_depth_report,
            file_name=SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME,
        ),
        "budget_calibration_readiness": _resolve_artifact_source(
            root=root,
            explicit_path=budget_calibration_readiness_report_path,
            file_name="budget_calibration_readiness_report.json",
        ),
        "labor_employment_qa_matrix": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_qa_matrix_report.json",
        ),
        "labor_employment_fixture_family_pack": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_fixture_family_pack_report.json",
        ),
        "labor_employment_executable_fixtures": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_executable_fixtures_report.json",
        ),
        "labor_employment_executable_coverage": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_executable_coverage_report.json",
        ),
        "labor_employment_executable_fact_binding": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_executable_fact_binding_report.json",
        ),
        "labor_employment_executable_driver_binding": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_executable_driver_binding_report.json",
        ),
        "labor_employment_executable_driver_impact": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_executable_driver_impact_report.json",
        ),
        "labor_employment_driver_impact_review": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_driver_impact_review_report.json",
        ),
        "labor_employment_blocked_driver_impact_review": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_blocked_driver_impact_review_report.json",
        ),
        "labor_employment_budget_output_expectations": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_budget_output_expectations_report.json",
        ),
        "labor_employment_budget_qa_gate": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_budget_qa_gate_report.json",
        ),
        "labor_employment_budget_learning_fixtures": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_budget_learning_fixtures_report.json",
        ),
        "labor_employment_budget_outcome_replay_readiness": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_budget_outcome_replay_readiness_report.json",
        ),
        "labor_employment_budget_fact_gold": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="labor_employment_budget_fact_gold_report.json",
        ),
        "budget_learning_loop": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="budget_learning_loop_report.json",
        ),
        "matter_linking_qa_gate": _resolve_artifact_source(
            root=root,
            explicit_path=None,
            file_name="matter_linking_qa_gate_report.json",
        ),
    }
    artifacts = [
        _artifact_entry(
            root=root,
            output_dir=output_dir,
            spec=spec,
            source_path=source_paths[spec.artifact_id],
        )
        for spec in QA_BUNDLE_ARTIFACTS
    ]
    ui_ref = str(ui_manifest_out) if ui_manifest_out else None
    ui_data_bundle_out = (
        Path(ui_manifest_out).with_name(UI_REVIEW_DATA_BUNDLE_FILENAME) if ui_manifest_out else None
    )
    report = _build_report(
        root=root,
        output_dir=output_dir,
        artifacts=artifacts,
        ui_manifest_ref=ui_ref,
        ui_data_bundle_ref=str(ui_data_bundle_out) if ui_data_bundle_out else None,
        generated_at=generated_at,
    )
    write_json(output_dir / SYNTHETIC_QA_BUNDLE_REPORT_FILENAME, report.model_dump(mode="json"))
    (output_dir / SYNTHETIC_QA_BUNDLE_NOTES_FILENAME).write_text(
        render_synthetic_qa_bundle_report(report),
        encoding="utf-8",
    )

    ui_manifest = None
    if ui_manifest_out:
        ui_manifest = build_ui_review_manifest(
            run_root=root,
            out_path=ui_manifest_out,
            generated_at=generated_at,
        )
        if ui_data_bundle_out:
            build_ui_review_data_bundle(
                run_root=root,
                out_path=ui_data_bundle_out,
                generated_at=generated_at,
            )
    return report, output_dir, ui_manifest


def render_synthetic_qa_bundle_report(report: SyntheticQABundleReport) -> str:
    lines = [
        "# Synthetic QA Bundle Report",
        "",
        f"**Report ID:** {report.synthetic_qa_bundle_report_id}",
        f"**Status:** {report.status}",
        f"**Run root:** `{report.run_root_ref}`",
        f"**Output directory:** `{report.out_dir_ref}`",
        "",
        "## Summary",
        "",
        f"- Artifacts: {report.artifact_count}",
        f"- Required artifacts: {report.required_artifact_count}",
        f"- Missing required artifacts: {report.missing_required_artifact_count}",
        f"- Blocked artifacts: {report.blocked_artifact_count}",
        f"- Pending review artifacts: {report.pending_artifact_count}",
        f"- Failed artifacts: {report.failed_artifact_count}",
        "",
        "## Artifacts",
        "",
    ]
    for artifact in report.artifacts:
        lines.extend(
            [
                f"### {artifact.label}",
                "",
                f"- File: `{artifact.file_name}`",
                f"- Status: {artifact.status}",
                f"- Required: {artifact.required}",
                f"- Present: {artifact.present}",
                f"- Source: `{artifact.artifact_ref or 'missing'}`",
                f"- Copied to: `{artifact.copied_to_ref or 'not copied'}`",
                f"- Source SHA-256: `{artifact.source_sha256 or 'missing'}`",
                f"- Notes: {' '.join(artifact.notes)}",
                "",
            ]
        )
    lines.extend(["## Required Next Actions", ""])
    lines.extend(f"- {action}" for action in report.required_next_actions)
    lines.extend(
        [
            "",
            "This bundle is candidate-only local QA evidence. It does not mutate fixtures, "
            "apply calibration, write Lake/SQLite records, submit budgets, open matters, "
            "or authorize production automation.",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_artifact_source(
    *,
    root: Path,
    explicit_path: str | Path | None,
    file_name: str,
) -> Path | None:
    if explicit_path:
        path = Path(explicit_path)
        return path if path.is_file() else None
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


def _artifact_entry(
    *,
    root: Path,
    output_dir: Path,
    spec: QABundleArtifactSpec,
    source_path: Path | None,
) -> SyntheticQABundleArtifact:
    if source_path is None:
        return SyntheticQABundleArtifact(
            artifact_id=spec.artifact_id,
            label=spec.label,
            file_name=spec.file_name,
            required=spec.required,
            present=False,
            status="missing",
            gate_state="missing",
            notes=[spec.missing_note],
        )
    payload = _safe_load_json(source_path)
    status = _status_from_payload(payload)
    copied_to = _copy_to_bundle_dir(source_path=source_path, output_dir=output_dir, spec=spec)
    return SyntheticQABundleArtifact(
        artifact_id=spec.artifact_id,
        label=spec.label,
        file_name=spec.file_name,
        required=spec.required,
        present=True,
        status=status,
        gate_state=status,
        artifact_ref=str(source_path),
        copied_to_ref=str(copied_to),
        source_sha256=_sha256_file(source_path),
        notes=[_note_for_payload(source_path, payload, status)],
    )


def _copy_to_bundle_dir(
    *,
    source_path: Path,
    output_dir: Path,
    spec: QABundleArtifactSpec,
) -> Path:
    destination = output_dir / spec.file_name
    if source_path.resolve() != destination.resolve():
        shutil.copy2(source_path, destination)
    return destination


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
    status = str(payload.get("status") or payload.get("overallStatus") or "").casefold()
    if "failed" in status:
        return "failed"
    if status.startswith("blocked"):
        return "blocked"
    if "ready_for_review" in status or "ready_for_budget_gate_replay" in status:
        return "pending_review"
    if "pending" in status or "review" in status:
        return "pending_review"
    if "blocked" in status or "gaps" in status:
        return "blocked"
    if status == "passed" or "passed" in status:
        return "passed"
    return "pending_review"


def _note_for_payload(path: Path, payload: dict[str, Any], status: str) -> str:
    if payload.get("load_error"):
        return str(payload["load_error"])
    payload_status = payload.get("status") or payload.get("overallStatus") or "status not declared"
    return f"Found {path.name}; source status={payload_status}; bundle status={status}."


def _build_report(
    *,
    root: Path,
    output_dir: Path,
    artifacts: list[SyntheticQABundleArtifact],
    ui_manifest_ref: str | None,
    ui_data_bundle_ref: str | None,
    generated_at: str | None,
) -> SyntheticQABundleReport:
    required = [artifact for artifact in artifacts if artifact.required]
    missing_required = [
        artifact for artifact in required if not artifact.present or artifact.status == "missing"
    ]
    blocked = [artifact for artifact in artifacts if artifact.status == "blocked"]
    pending = [artifact for artifact in artifacts if artifact.status == "pending_review"]
    failed = [artifact for artifact in artifacts if artifact.status == "failed"]
    if failed:
        status = "failed"
    elif missing_required or blocked:
        status = "blocked"
    elif pending:
        status = "pending_review"
    else:
        status = "passed"
    report_core = {
        "status": status,
        "run_root_ref": str(root),
        "out_dir_ref": str(output_dir),
        "artifact_refs": [
            {
                "artifact_id": artifact.artifact_id,
                "status": artifact.status,
                "source_sha256": artifact.source_sha256,
            }
            for artifact in artifacts
        ],
        "ui_manifest_ref": ui_manifest_ref,
        "ui_data_bundle_ref": ui_data_bundle_ref,
    }
    return SyntheticQABundleReport(
        synthetic_qa_bundle_report_id="synthetic_qa_bundle_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 12],
        status=status,
        run_root_ref=str(root),
        out_dir_ref=str(output_dir),
        artifact_count=len(artifacts),
        required_artifact_count=len(required),
        missing_required_artifact_count=len(missing_required),
        blocked_artifact_count=len(blocked),
        pending_artifact_count=len(pending),
        failed_artifact_count=len(failed),
        artifacts=artifacts,
        ui_manifest_ref=ui_manifest_ref,
        ui_data_bundle_ref=ui_data_bundle_ref,
        required_next_actions=_required_next_actions(
            missing_required=missing_required,
            blocked=blocked,
            pending=pending,
            failed=failed,
        ),
        generated_at=generated_at or now_iso(),
    )


def _required_next_actions(
    *,
    missing_required: list[SyntheticQABundleArtifact],
    blocked: list[SyntheticQABundleArtifact],
    pending: list[SyntheticQABundleArtifact],
    failed: list[SyntheticQABundleArtifact],
) -> list[str]:
    if failed:
        return [
            f"Repair unreadable or failed QA artifact: {artifact.file_name}" for artifact in failed
        ]
    if missing_required:
        return [
            f"Generate required QA artifact {artifact.file_name}: {' '.join(artifact.notes)}"
            for artifact in missing_required
        ]
    if blocked:
        return [
            f"Resolve blocked QA artifact {artifact.file_name} before relying on calibration."
            for artifact in blocked
        ]
    if pending:
        return [
            "Route pending QA artifacts for human/owner review; do not treat review-ready as calibrated."
        ]
    return ["Synthetic QA bundle is locally coherent; continue with reviewed-gold expansion."]


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()
