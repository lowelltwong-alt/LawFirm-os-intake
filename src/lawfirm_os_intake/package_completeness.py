from __future__ import annotations

from pathlib import Path

from .models import (
    ExceptionLakeReadinessReport,
    ReviewPackageCompletenessCheck,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
    SafetyGateReport,
)
from .util import new_id, now_iso


REQUIRED_REVIEW_SECTIONS = [
    "# Matter Opening Review Package",
    "## Authority And Preconditions",
    "### Contract State",
    "### Human Review Outcome",
    "### Budget Preconditions",
    "## Source Inventory",
    "## What Is Known",
    "## Candidate Alternatives",
    "## What Still Needs Human Review",
    "## Required Human Gates",
    "## Conflict Search Seed",
    "## Budget Proposal",
    "### Calculation Summary",
    "### Budget Lines",
    "### Budget Supports",
    "## Exception And Escalation Records",
    "### Exception Lake Readiness",
    "### Exception Candidate Details",
    "## Safety Gate",
    "## Matter-Opening Blockers",
    "## Evidence Graph Summary",
    "## Run Ledger Summary",
    "## Artifact References",
]

REQUIRED_LINKED_REVIEW_FORM_SECTIONS = {
    "preflight_intake_review_form": [
        "# Intake Review Form",
        "## Source Coverage",
        "## Candidate Review",
        "## Reviewer Decision",
        "## Review Outcome Handling",
        "## Prohibited Next Steps",
    ],
    "legal_budget_review_form": [
        "# Proposed Legal Budget Review Form",
        "## Calculation Report",
        "## Budget Lines",
        "## Evidence-Bound Budget Supports",
        "## Review Checks",
        "## Submission Boundary",
    ],
}

REQUIRED_ARTIFACT_KEYS = [
    "preflight_packet",
    "preflight_source_inventory",
    "preflight_segments",
    "preflight_ingestion_result",
    "preflight_rust_ingestion_readiness_report",
    "preflight_intake_review_form",
    "human_confirmation",
    "conflict_search_seed",
    "legal_budget_proposal",
    "legal_budget_review_form",
    "matter_opening_readiness",
    "budget_evidence_graph",
    "preflight_evidence_graph",
    "preflight_exception_candidates",
    "preflight_exception_lake_readiness_report",
    "budget_exception_candidates",
    "budget_exception_lake_readiness_report",
    "budget_run_ledger",
    "preflight_run_ledger",
    "human_review_outcome",
    "human_confirmation_history",
    "contract_state_report",
    "budget_precondition_report",
    "safety_gate_report",
    "matter_opening_review_package",
    "review_package_manifest",
    "review_package_completeness_report",
]

REQUIRED_HUMAN_GATES = {
    "human_intake_confirmation",
    "human_conflicts_clearance",
    "human_engagement_authorization",
    "human_budget_review",
    "human_matter_opening_authorization",
}

REQUIRED_FINAL_BLOCKERS = {
    "conflicts_not_cleared",
    "engagement_not_authorized",
    "matter_opening_not_approved",
}

REQUIRED_PROHIBITED_ACTIONS = {
    "do_not_open_imanage",
    "do_not_create_matter",
    "do_not_submit_budget",
}

BOUNDARY_PHRASES = [
    "This package does not clear conflicts",
    "open a matter",
    "submit a budget",
]

_SELF_REPORT_KEY = "review_package_completeness_report"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    artifact_refs: list[str] | None = None,
    details: dict[str, object] | None = None,
) -> ReviewPackageCompletenessCheck:
    return ReviewPackageCompletenessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        details=details or {},
    )


def _artifact_refs_are_local(artifact_refs: dict[str, str]) -> bool:
    external_prefixes = ("http://", "https://", "imap://", "smtp://", "s3://", "gs://")
    forbidden_terms = (
        "imanage",
        "gmail",
        "outlook",
        "conflicts_system",
        "carrier_portal",
        "court",
        "billing",
    )
    for value in artifact_refs.values():
        lowered = value.casefold()
        if lowered.startswith(external_prefixes):
            return False
        if any(term in lowered for term in forbidden_terms):
            return False
    return True


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _manifest_ref(manifest: ReviewPackageManifest) -> str:
    return manifest.artifact_refs.get("review_package_manifest", "")


def build_review_package_completeness_report(
    *,
    manifest: ReviewPackageManifest,
    review_package_path: Path,
    safety_report: SafetyGateReport,
    exception_readiness_report: ExceptionLakeReadinessReport,
) -> ReviewPackageCompletenessReport:
    artifact_refs = manifest.artifact_refs
    review_text = _read_text(review_package_path)
    linked_review_form_missing_sections: dict[str, list[str]] = {}
    for key, required_sections in REQUIRED_LINKED_REVIEW_FORM_SECTIONS.items():
        form_text = _read_text(Path(artifact_refs.get(key, "")))
        missing = [section for section in required_sections if section not in form_text]
        if missing:
            linked_review_form_missing_sections[key] = missing
    missing_keys = [key for key in REQUIRED_ARTIFACT_KEYS if not artifact_refs.get(key)]
    paths_missing = [
        key
        for key, value in artifact_refs.items()
        if key != _SELF_REPORT_KEY and value and not Path(value).exists()
    ]
    missing_sections = [
        section for section in REQUIRED_REVIEW_SECTIONS if section not in review_text
    ]
    missing_boundary_phrases = [phrase for phrase in BOUNDARY_PHRASES if phrase not in review_text]
    missing_gates = sorted(REQUIRED_HUMAN_GATES - set(manifest.required_human_gates))
    missing_blockers = sorted(REQUIRED_FINAL_BLOCKERS - set(manifest.final_blockers))
    missing_prohibited = sorted(REQUIRED_PROHIBITED_ACTIONS - set(manifest.prohibited_actions))

    review_package_ref = artifact_refs.get("matter_opening_review_package", "")
    manifest_ref = _manifest_ref(manifest)
    completeness_ref = artifact_refs.get(_SELF_REPORT_KEY, "")

    checks = [
        _check(
            "required_artifact_keys_present",
            not missing_keys,
            "Manifest includes every artifact required for final package review.",
            sorted(artifact_refs.values()),
            {"missing_keys": missing_keys},
        ),
        _check(
            "artifact_refs_are_local",
            _artifact_refs_are_local(artifact_refs),
            "Artifact references stay local and do not target external connectors.",
            sorted(artifact_refs.values()),
        ),
        _check(
            "referenced_artifacts_exist",
            not paths_missing,
            "Every referenced artifact exists before package acceptance, except the report being written.",
            sorted(artifact_refs.values()),
            {"missing_artifact_keys": paths_missing},
        ),
        _check(
            "manifest_links_review_package",
            manifest.human_readable_review_ref == str(review_package_path)
            and review_package_ref == str(review_package_path)
            and manifest.review_package_completeness_report_ref == completeness_ref
            and bool(manifest_ref)
            and bool(completeness_ref),
            "Manifest links the human-readable package, manifest file, and completeness report.",
            [
                manifest.human_readable_review_ref,
                review_package_ref,
                manifest_ref,
                completeness_ref,
            ],
            {
                "human_readable_review_ref": manifest.human_readable_review_ref,
                "artifact_review_ref": review_package_ref,
                "manifest_ref": manifest_ref,
                "completeness_ref": completeness_ref,
            },
        ),
        _check(
            "required_review_sections_present",
            not missing_sections and not missing_boundary_phrases,
            "Human-readable review package contains all required review sections and boundary text.",
            [str(review_package_path)],
            {
                "missing_sections": missing_sections,
                "missing_boundary_phrases": missing_boundary_phrases,
            },
        ),
        _check(
            "linked_review_forms_complete",
            not linked_review_form_missing_sections,
            "Linked intake and budget review forms preserve required human-review sections.",
            [
                artifact_refs.get("preflight_intake_review_form", ""),
                artifact_refs.get("legal_budget_review_form", ""),
            ],
            {"missing_sections_by_form": linked_review_form_missing_sections},
        ),
        _check(
            "required_human_gates_present",
            not missing_gates,
            "Manifest preserves all required human gates.",
            [manifest_ref],
            {"missing_gates": missing_gates},
        ),
        _check(
            "final_blockers_present",
            not missing_blockers and manifest.status == "blocked_pending_conflicts_and_engagement",
            "Manifest keeps conflicts, engagement, and matter opening as final blockers.",
            [manifest_ref],
            {"missing_blockers": missing_blockers, "status": manifest.status},
        ),
        _check(
            "prohibited_actions_present",
            not missing_prohibited,
            "Manifest preserves prohibited matter-opening and budget-submission actions.",
            [manifest_ref],
            {"missing_prohibited_actions": missing_prohibited},
        ),
        _check(
            "boundary_flags_preserved",
            manifest.no_conflict_conclusion is True
            and manifest.budget_not_authorized_for_client_submission is True
            and manifest.contains_raw_payload is False
            and manifest.external_writes_performed is False,
            "Manifest boundary flags prohibit conflict conclusions, client submission, raw payloads, and external writes.",
            [manifest_ref],
        ),
        _check(
            "safety_gate_passed",
            safety_report.status == "passed"
            and safety_report.final_boundary == manifest.status
            and manifest.safety_gate_report_ref == artifact_refs.get("safety_gate_report"),
            "Final package carries a passing safety gate with the blocked final boundary.",
            [manifest.safety_gate_report_ref],
            {
                "safety_status": safety_report.status,
                "safety_final_boundary": safety_report.final_boundary,
            },
        ),
        _check(
            "exception_lake_readiness_passed",
            exception_readiness_report.status == "passed"
            and exception_readiness_report.admission_state == "dry_run_not_admitted"
            and manifest.exception_lake_readiness_report_ref
            == artifact_refs.get("budget_exception_lake_readiness_report")
            and bool(manifest.exception_candidate_refs),
            "Final package carries passing dry-run Exception Lake readiness and candidate refs.",
            [manifest.exception_lake_readiness_report_ref or ""],
            {
                "exception_readiness_status": exception_readiness_report.status,
                "admission_state": exception_readiness_report.admission_state,
                "exception_candidate_refs": manifest.exception_candidate_refs,
            },
        ),
        _check(
            "run_ledgers_present",
            len(manifest.run_ledger_refs) >= 2
            and all(Path(ref).exists() for ref in manifest.run_ledger_refs),
            "Manifest points to both preflight and budget run ledgers.",
            manifest.run_ledger_refs,
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ReviewPackageCompletenessReport(
        review_package_completeness_report_id=new_id("reviewpkgcomplete"),
        run_id=manifest.run_id,
        preflight_packet_id=manifest.preflight_packet_id,
        review_package_id=manifest.review_package_id,
        status=status,
        human_readable_review_ref=manifest.human_readable_review_ref,
        review_package_manifest_ref=manifest_ref,
        required_sections=REQUIRED_REVIEW_SECTIONS,
        required_artifact_keys=REQUIRED_ARTIFACT_KEYS,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_review_package_completeness(
    report: ReviewPackageCompletenessReport,
) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("review package completeness failed: " + ", ".join(failed))
