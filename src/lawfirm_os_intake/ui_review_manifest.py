from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import digest_json, load_json, now_iso, write_json


BOUNDARY_FLAGS = {
    "readOnly": True,
    "localJsonOnly": True,
    "networkCallsAllowed": False,
    "mutationCommandsAllowed": False,
    "exceptionLakeWritesAllowed": False,
    "sqliteWritesAllowed": False,
    "publicRuntimeIngestionAllowed": False,
    "budgetSubmissionAllowed": False,
    "matterOpeningAllowed": False,
}


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_id: str
    label: str
    file_name: str
    owner: str
    default_missing_status: str = "missing"


ARTIFACT_SPECS = [
    ArtifactSpec(
        "preflight", "Intake Preflight", "intake_preflight_packet.json", "intake-reference"
    ),
    ArtifactSpec(
        "human-gate",
        "Human Gate",
        "human_gate_status_report.json",
        "human-reviewer",
        "blocked",
    ),
    ArtifactSpec(
        "conflict-seed",
        "Conflict Seed",
        "conflict_search_seed_packet.json",
        "intake-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "budget-proposal",
        "Budget Proposal",
        "legal_budget_proposal.json",
        "pricing-review",
        "blocked",
    ),
    ArtifactSpec(
        "matter-opening",
        "Matter Opening",
        "matter_opening_readiness.json",
        "orchestrator-future-owner",
        "blocked",
    ),
    ArtifactSpec(
        "submission-guard",
        "Budget Submission Guard",
        "budget_submission_guard_report.json",
        "intake-reference",
    ),
    ArtifactSpec(
        "lake-handoff",
        "Lake Handoff",
        "exception_lake_handoff_manifest.json",
        "exception-lake-future-owner",
        "pending_review",
    ),
    ArtifactSpec(
        "run-ledger",
        "Run Ledger Integrity",
        "run_ledger_integrity_report.json",
        "intake-reference",
    ),
    ArtifactSpec(
        "budget-coherence",
        "Budget Coherence",
        "budget_coherence_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "synthetic-qa-bundle",
        "Synthetic QA Bundle",
        "synthetic_qa_bundle_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "synthetic-qa-review-run",
        "Synthetic QA Review Run",
        "synthetic_qa_review_run_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "synthetic-confidence-summary",
        "Synthetic Confidence Summary",
        "synthetic_confidence_summary_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "synthetic-qa-blocker-report",
        "Synthetic QA Blocker Report",
        "synthetic_qa_blocker_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "poc-qa-triage",
        "POC QA Triage",
        "poc_qa_triage_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "matter-linking-preflight",
        "Matter-Linking Preflight",
        "matter_linking_preflight_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "matter-linking-review-outcome",
        "Matter-Linking Review Outcome",
        "matter_linking_review_outcome_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "matter-linking-qa-gate",
        "Matter-Linking QA Gate",
        "matter_linking_qa_gate_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "fixture-depth",
        "Synthetic Fixture Depth",
        "synthetic_fixture_depth_audit_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "calibration-readiness",
        "Calibration Readiness",
        "budget_calibration_readiness_report.json",
        "pricing-review",
        "blocked",
    ),
    ArtifactSpec(
        "calibration-starter-pack",
        "Calibration Starter Pack",
        "budget_calibration_starter_pack_report.json",
        "pricing-review",
        "pending_review",
    ),
    ArtifactSpec(
        "labor-employment-qa-matrix",
        "L&E QA Matrix",
        "labor_employment_qa_matrix_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-fixture-family-pack",
        "L&E Fixture Family Pack",
        "labor_employment_fixture_family_pack_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-executable-fixtures",
        "L&E Executable Fixtures",
        "labor_employment_executable_fixtures_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-executable-coverage",
        "L&E Executable Coverage",
        "labor_employment_executable_coverage_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-executable-fact-binding",
        "L&E Executable Fact Binding",
        "labor_employment_executable_fact_binding_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-executable-driver-binding",
        "L&E Executable Driver Binding",
        "labor_employment_executable_driver_binding_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-executable-driver-impact",
        "L&E Executable Driver Impact",
        "labor_employment_executable_driver_impact_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-driver-impact-review",
        "L&E Driver Impact Review",
        "labor_employment_driver_impact_review_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-blocked-driver-impact-review",
        "L&E Blocked Driver Impact Review",
        "labor_employment_blocked_driver_impact_review_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-budget-output-expectations",
        "L&E Budget Output Expectations",
        "labor_employment_budget_output_expectations_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "labor-employment-budget-fact-gold",
        "L&E Budget Fact Gold",
        "labor_employment_budget_fact_gold_report.json",
        "qa-reference",
        "blocked",
    ),
    ArtifactSpec(
        "validation-suite-evidence",
        "Validation Suite Evidence",
        "validation_suite_evidence_report.json",
        "qa-reference",
        "pending_review",
    ),
    ArtifactSpec(
        "budget-human-review",
        "Budget Human Review",
        "budget_human_review_packet.json",
        "pricing-review",
        "pending_review",
    ),
    ArtifactSpec(
        "carrier-rejection-ledger",
        "Carrier Rejection Ledger",
        "carrier_rejection_decision_ledger_report.json",
        "carrier-response-review",
        "pending_review",
    ),
    ArtifactSpec(
        "actual-variance",
        "Actual Variance Ledger",
        "budget_actual_variance_ledger_report.json",
        "pricing-review",
        "pending_review",
    ),
    ArtifactSpec(
        "public-methodology",
        "Public Methodology",
        "public_source_methodology_report.json",
        "methodology-review",
        "pending_review",
    ),
    ArtifactSpec(
        "public-cache",
        "Public Data Cache",
        "public_data_cache_audit_report.json",
        "methodology-review",
        "pending_review",
    ),
]


QUALITY_GATE_SPECS = {
    "budget_coherence": (
        "Budget Coherence",
        "budget_coherence_report.json",
        "qa-reference",
        "Serialized artifact math and no-submission display boundary are checked before demo acceptance.",
        "blocked",
    ),
    "synthetic_qa_bundle": (
        "Synthetic QA Bundle",
        "synthetic_qa_bundle_report.json",
        "qa-reference",
        "Budget coherence, fixture depth, calibration readiness, and UI evidence are bundled for QA review.",
        "blocked",
    ),
    "synthetic_qa_review_run": (
        "Synthetic QA Review Run",
        "synthetic_qa_review_run_report.json",
        "qa-reference",
        "The one-command synthetic QA recipe must prove each generated QA/UI artifact step before the frontend treats the run as review-ready.",
        "pending_review",
    ),
    "synthetic_confidence_summary": (
        "Synthetic Confidence Summary",
        "synthetic_confidence_summary_report.json",
        "qa-reference",
        "The aggregate synthetic QA confidence banner must make review readiness, blockers, and no-production-authority boundaries visible.",
        "pending_review",
    ),
    "synthetic_qa_blocker_report": (
        "Synthetic QA Blocker Report",
        "synthetic_qa_blocker_report.json",
        "qa-reference",
        "The synthetic QA blocker queue must be emitted as deterministic local JSON before the review UI relies on it.",
        "pending_review",
    ),
    "poc_qa_triage": (
        "POC QA Triage",
        "poc_qa_triage_report.json",
        "qa-reference",
        "The POC QA triage queue must reconcile validation, synthetic QA, L&E budget gates, and UI evidence before readiness is claimed.",
        "pending_review",
    ),
    "matter_linking_preflight": (
        "Matter-Linking Preflight",
        "matter_linking_preflight_report.json",
        "qa-reference",
        "Upfront-like document clusters must stay human-gated and no-write before budget or matter-opening workflows rely on them.",
        "pending_review",
    ),
    "matter_linking_review_outcome": (
        "Matter-Linking Review Outcome",
        "matter_linking_review_outcome_report.json",
        "qa-reference",
        "Human matter-linking decisions must be append-only local evidence and cannot authorize budgets, matter opening, Lake admission, or learning.",
        "pending_review",
    ),
    "matter_linking_qa_gate": (
        "Matter-Linking QA Gate",
        "matter_linking_qa_gate_report.json",
        "qa-reference",
        "Upfront-like matter-linking fixtures must cover ambiguous multi-case sender risk, resolved follow-up, weak-only blocking, conflicting identifiers, and no-write boundaries.",
        "pending_review",
    ),
    "synthetic_fixture_depth": (
        "Synthetic Fixture Depth",
        "synthetic_fixture_depth_audit_report.json",
        "qa-reference",
        "Fixture-family depth remains visible before synthetic QA coverage is trusted.",
        "pending_review",
    ),
    "budget_calibration_readiness": (
        "Calibration Readiness",
        "budget_calibration_readiness_report.json",
        "pricing-review",
        "Budget calibration stays blocked until reviewed gold, replay outputs, and variance evidence exist.",
        "blocked",
    ),
    "labor_employment_qa_matrix": (
        "L&E QA Matrix",
        "labor_employment_qa_matrix_report.json",
        "qa-reference",
        "L&E synthetic fact fixtures must prove critical blockers and range-only review posture.",
        "blocked",
    ),
    "labor_employment_fixture_family_pack": (
        "L&E Fixture Family Pack",
        "labor_employment_fixture_family_pack_report.json",
        "qa-reference",
        "L&E synthetic fixtures must cover required families, variants, fact needs, and budget-driver dimensions.",
        "blocked",
    ),
    "labor_employment_executable_fixtures": (
        "L&E Executable Fixtures",
        "labor_employment_executable_fixtures_report.json",
        "qa-reference",
        "Selected L&E source bundles must execute through deterministic preflight before fixture generation is trusted.",
        "blocked",
    ),
    "labor_employment_executable_coverage": (
        "L&E Executable Coverage",
        "labor_employment_executable_coverage_report.json",
        "qa-reference",
        "QA must show which L&E fixture-family pack cases are executable today and which remain planned coverage gaps.",
        "blocked",
    ),
    "labor_employment_executable_fact_binding": (
        "L&E Executable Fact Binding",
        "labor_employment_executable_fact_binding_report.json",
        "qa-reference",
        "Executable L&E preflight packets must bind expected budget-fact gaps to source evidence, source inventory, or dry-run exception labels.",
        "blocked",
    ),
    "labor_employment_executable_driver_binding": (
        "L&E Executable Driver Binding",
        "labor_employment_executable_driver_binding_report.json",
        "qa-reference",
        "Executable L&E fact-gap evidence must map to budget-driver focus dimensions before budget-driver QA is trusted.",
        "blocked",
    ),
    "labor_employment_executable_driver_impact": (
        "L&E Executable Driver Impact",
        "labor_employment_executable_driver_impact_report.json",
        "qa-reference",
        "Executable L&E driver bindings must declare candidate budget blockers, range widening, scenario forks, and rate/guideline review effects before budget math can consume them.",
        "blocked",
    ),
    "labor_employment_driver_impact_review": (
        "L&E Driver Impact Review",
        "labor_employment_driver_impact_review_report.json",
        "qa-reference",
        "Nonblocking L&E driver-impact budget-gate replay must be backed by reviewed synthetic evidence, not hand-filtered test data.",
        "blocked",
    ),
    "labor_employment_blocked_driver_impact_review": (
        "L&E Blocked Driver Impact Review",
        "labor_employment_blocked_driver_impact_review_report.json",
        "qa-reference",
        "Blocked L&E amount-budget cases must explain blocker facts, follow-up actions, and candidate Lake labels before QA trusts budget gating.",
        "blocked",
    ),
    "labor_employment_budget_output_expectations": (
        "L&E Budget Output Expectations",
        "labor_employment_budget_output_expectations_report.json",
        "qa-reference",
        "Every executable L&E case must have one allowed budget-output state, next gates, and candidate Lake labels before budget QA can rely on it.",
        "blocked",
    ),
    "labor_employment_budget_fact_gold": (
        "L&E Budget Fact Gold",
        "labor_employment_budget_fact_gold_report.json",
        "qa-reference",
        "L&E budget fact audit outputs must match reviewed synthetic gold before calibration or model comparison.",
        "blocked",
    ),
    "validation_suite_evidence": (
        "Validation Suite Evidence",
        "validation_suite_evidence_report.json",
        "qa-reference",
        "Wrapper-based validation suite evidence must prove the current QA checks before the frontend treats the run as POC QA-ready.",
        "pending_review",
    ),
    "full_pytest": (
        "Full Pytest",
        "validation_suite_evidence_report.json",
        "qa-reference",
        "Validation evidence must include a passed full_pytest step from scripts/run_full_pytest.py.",
        "pending_review",
    ),
    "smoke_demo": (
        "North-Star Smoke",
        "validation_suite_evidence_report.json",
        "qa-reference",
        "Validation evidence must include a passed smoke_demo step from scripts/smoke_demo.sh.",
        "pending_review",
    ),
}


def build_ui_review_manifest(
    *,
    run_root: str | Path,
    out_path: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(run_root)
    artifacts = [_artifact_entry(root, spec) for spec in ARTIFACT_SPECS]
    quality_gates = [_quality_gate_entry(root, gate_id) for gate_id in QUALITY_GATE_SPECS]
    manifest_core = {
        "generatedAt": generated_at or now_iso(),
        "runLabel": _run_label(root),
        "practiceArea": _practice_area(root),
        "matterFamily": _matter_family(root),
        "overallStatus": _overall_status(artifacts, quality_gates),
        "boundaryFlags": BOUNDARY_FLAGS,
        "artifacts": artifacts,
        "qualityGates": quality_gates,
        "blockerSummary": _blocker_summary(artifacts, quality_gates),
        "redTeamNotes": [
            "Generated from local artifacts only; missing QA evidence is not treated as passing.",
            "The UI manifest is display evidence only and cannot submit budgets, open matters, or write Lake records.",
            "Synthetic QA gates remain candidate-only until reviewed by the appropriate owner.",
        ],
    }
    manifest = {
        "manifestId": "ui_review_manifest_"
        + digest_json(manifest_core)[len("sha256:") : len("sha256:") + 12],
        **manifest_core,
    }
    write_json(out_path, manifest)
    return manifest


def _artifact_entry(root: Path, spec: ArtifactSpec) -> dict[str, Any]:
    found = _find_artifact(root, spec.file_name)
    if found is None:
        return {
            "artifactId": spec.artifact_id,
            "label": spec.label,
            "fileName": spec.file_name,
            "status": spec.default_missing_status,
            "owner": spec.owner,
            "gateState": _missing_gate_state(spec.default_missing_status),
            "candidateOnly": True,
            "externalWritesPerformed": False,
            "notes": [f"{spec.file_name} was not found under the local run root."],
        }
    payload = _safe_load_json(found)
    gate_state = _gate_state_from_payload(payload)
    return {
        "artifactId": spec.artifact_id,
        "label": spec.label,
        "fileName": spec.file_name,
        "status": _artifact_status_from_gate(gate_state),
        "owner": spec.owner,
        "gateState": gate_state,
        "candidateOnly": True,
        "externalWritesPerformed": _external_writes_performed(payload),
        "notes": [_artifact_note(root, found, payload)],
    }


def _quality_gate_entry(root: Path, gate_id: str) -> dict[str, Any]:
    label, file_name, owner, note, missing_status = QUALITY_GATE_SPECS[gate_id]
    found = _find_artifact(root, file_name)
    status = missing_status
    if found is not None:
        status = _quality_status_from_payload(_safe_load_json(found))
    return {
        "gateId": gate_id,
        "label": label,
        "status": status,
        "evidenceFile": file_name,
        "owner": owner,
        "notes": [note if found is not None else f"{file_name} is missing; {note}"],
    }


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


def _safe_load_json(path: Path | None) -> dict[str, Any]:
    if path is None or path.suffix.lower() != ".json":
        return {}
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _gate_state_from_payload(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or payload.get("overallStatus") or "").casefold()
    if "failed" in status:
        return "failed"
    if status.startswith("blocked") or payload.get("client_submission_performed") is True:
        return "blocked"
    if status == "synthetic_qa_review_run_ready":
        return "passed"
    if "ready_for_review" in status or "ready_for_budget_gate_replay" in status:
        return "pending"
    if "pending" in status or "review" in status:
        return "pending"
    if "blocked" in status:
        return "blocked"
    return "passed"


def _artifact_status_from_gate(gate_state: str) -> str:
    if gate_state == "failed":
        return "blocked"
    if gate_state == "blocked":
        return "blocked"
    if gate_state == "pending":
        return "pending_review"
    return "present"


def _quality_status_from_payload(payload: dict[str, Any]) -> str:
    gate_state = _gate_state_from_payload(payload)
    if gate_state == "passed":
        return "passed"
    if gate_state == "failed":
        return "failed"
    if gate_state == "blocked":
        return "blocked"
    return "pending_review"


def _missing_gate_state(status: str) -> str:
    if status == "blocked":
        return "blocked"
    if status == "pending_review":
        return "pending"
    return "failed"


def _artifact_note(root: Path, path: Path, payload: dict[str, Any]) -> str:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    status = payload.get("status")
    if status:
        return f"Found {relative}; status={status}."
    return f"Found {relative}; local artifact present."


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


def _overall_status(artifacts: list[dict[str, Any]], quality_gates: list[dict[str, Any]]) -> str:
    if any(artifact["externalWritesPerformed"] for artifact in artifacts):
        return "failed"
    if any(gate["status"] == "failed" for gate in quality_gates):
        return "failed"
    if any(artifact["status"] == "blocked" for artifact in artifacts) or any(
        gate["status"] == "blocked" for gate in quality_gates
    ):
        return "blocked"
    if any(gate["status"] == "pending_review" for gate in quality_gates):
        return "pending"
    return "passed"


def _blocker_summary(
    artifacts: list[dict[str, Any]], quality_gates: list[dict[str, Any]]
) -> list[str]:
    blockers = [
        f"{artifact['label']}: {artifact['notes'][0]}"
        for artifact in artifacts
        if artifact["status"] in {"missing", "blocked"}
    ]
    blockers.extend(
        f"{gate['label']}: {gate['notes'][0]}"
        for gate in quality_gates
        if gate["status"] in {"blocked", "failed"}
    )
    return blockers or ["No blocking local QA gates were found in this manifest."]


def _budget_payload(root: Path) -> dict[str, Any]:
    return _safe_load_json(_find_artifact(root, "legal_budget_proposal.json"))


def _run_label(root: Path) -> str:
    return f"Local intake QA review: {root.name}"


def _practice_area(root: Path) -> str:
    matter_family = _matter_family(root)
    if matter_family.startswith("employment") or "labor" in matter_family:
        return "labor_and_employment"
    return "synthetic_intake"


def _matter_family(root: Path) -> str:
    payload = _budget_payload(root)
    value = payload.get("matter_family")
    return str(value) if value else "unknown"
