from __future__ import annotations

from pathlib import Path

from .models import (
    ExceptionLakeReadinessReport,
    ReviewPackageCompletenessCheck,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
    SafetyGateReport,
)
from .util import load_json, new_id, now_iso


REQUIRED_REVIEW_SECTIONS = [
    "# Matter Opening Review Package",
    "## Authority And Preconditions",
    "### Contract State",
    "### Model Adapter Boundary",
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
    "### Exception Lake Handoff",
    "### Exception Candidate Details",
    "## Safety Gate",
    "## Matter-Opening Blockers",
    "## Evidence Graph Summary",
    "## Run Ledger Summary",
    "### Run Ledger Integrity",
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

REQUIRED_LINKED_REVIEW_FORM_CONTENT = {
    "preflight_intake_review_form": [
        "This form does not clear conflicts",
        "docket deadlines",
        "open a matter",
    ],
    "legal_budget_review_form": [
        "Client/carrier submission authorized: False",
        "The generated proposal is not authorized for client or carrier submission.",
    ],
}

LINKED_REVIEW_FORM_SOURCE_ARTIFACT_KEYS = {
    "preflight_intake_review_form": "preflight_packet",
    "legal_budget_review_form": "legal_budget_proposal",
}

SOURCE_BOUND_EVIDENCE_MARKER = "] sha=sha256:"
SOURCE_BOUND_EVIDENCE_REF_KEYS = {
    "evidence_refs",
    "observed_evidence_refs",
    "decision_evidence_refs",
    "confirmed_party_evidence_refs",
    "segment_evidence_refs",
}

REQUIRED_ARTIFACT_KEYS = [
    "preflight_packet",
    "preflight_source_inventory",
    "preflight_segments",
    "preflight_ingestion_result",
    "preflight_ingestion_volume_profile",
    "preflight_rust_ingestion_readiness_report",
    "preflight_model_adapter_report",
    "preflight_intake_review_form",
    "preflight_deadline_docketing_guard_report",
    "human_confirmation",
    "conflict_search_seed",
    "legal_budget_proposal",
    "legal_budget_review_form",
    "matter_opening_readiness",
    "budget_evidence_graph",
    "preflight_evidence_graph",
    "preflight_exception_candidates",
    "preflight_exception_lake_readiness_report",
    "preflight_exception_lake_handoff_manifest",
    "budget_exception_candidates",
    "budget_exception_lake_readiness_report",
    "budget_exception_lake_handoff_manifest",
    "budget_run_ledger",
    "preflight_run_ledger",
    "preflight_run_ledger_integrity_report",
    "budget_run_ledger_integrity_report",
    "human_review_outcome",
    "human_confirmation_history",
    "human_gate_status_report",
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


def _read_json(path: Path) -> object | None:
    if str(path) == "." or not path.exists() or not path.is_file():
        return None
    try:
        return load_json(path)
    except (OSError, ValueError):
        return None


def _is_source_bound_evidence_ref(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(
        value.get("source_id")
        and value.get("segment_id")
        and value.get("sha256")
        and value.get("start_offset") is not None
        and value.get("end_offset") is not None
    )


def _has_source_bound_evidence_refs(value: object) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in SOURCE_BOUND_EVIDENCE_REF_KEYS and isinstance(nested, list):
                if any(_is_source_bound_evidence_ref(item) for item in nested):
                    return True
            if _has_source_bound_evidence_refs(nested):
                return True
    if isinstance(value, list):
        return any(_has_source_bound_evidence_refs(item) for item in value)
    return False


def _linked_form_expected_content(key: str, artifact_refs: dict[str, str]) -> list[str]:
    required = list(REQUIRED_LINKED_REVIEW_FORM_CONTENT.get(key, []))
    source_artifact_key = LINKED_REVIEW_FORM_SOURCE_ARTIFACT_KEYS.get(key)
    if source_artifact_key:
        source_artifact = _read_json(Path(artifact_refs.get(source_artifact_key, "")))
        if _has_source_bound_evidence_refs(source_artifact):
            required.append(SOURCE_BOUND_EVIDENCE_MARKER)
    return required


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
    linked_review_form_texts = {
        key: _read_text(Path(artifact_refs.get(key, "")))
        for key in REQUIRED_LINKED_REVIEW_FORM_SECTIONS
    }
    exception_handoff_manifest = _read_json(
        Path(artifact_refs.get("budget_exception_lake_handoff_manifest", ""))
    )
    preflight_packet = _read_json(Path(artifact_refs.get("preflight_packet", "")))
    matter_opening_readiness = _read_json(Path(artifact_refs.get("matter_opening_readiness", "")))
    human_gate_status_report = _read_json(Path(artifact_refs.get("human_gate_status_report", "")))
    deadline_docketing_guard_report = _read_json(
        Path(artifact_refs.get("preflight_deadline_docketing_guard_report", ""))
    )
    preflight_ledger_integrity = _read_json(
        Path(artifact_refs.get("preflight_run_ledger_integrity_report", ""))
    )
    budget_ledger_integrity = _read_json(
        Path(artifact_refs.get("budget_run_ledger_integrity_report", ""))
    )
    linked_review_form_missing_sections: dict[str, list[str]] = {}
    for key, required_sections in REQUIRED_LINKED_REVIEW_FORM_SECTIONS.items():
        form_text = linked_review_form_texts[key]
        missing = [section for section in required_sections if section not in form_text]
        if missing:
            linked_review_form_missing_sections[key] = missing
    linked_review_form_missing_content: dict[str, list[str]] = {}
    for key in REQUIRED_LINKED_REVIEW_FORM_CONTENT:
        form_text = linked_review_form_texts.get(key, "")
        required_phrases = _linked_form_expected_content(key, artifact_refs)
        missing = [phrase for phrase in required_phrases if phrase not in form_text]
        if missing:
            linked_review_form_missing_content[key] = missing
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
    human_gate_rows = (
        human_gate_status_report.get("gates")
        if isinstance(human_gate_status_report, dict)
        else None
    )
    human_gate_ids = {
        str(item.get("gate_id"))
        for item in human_gate_rows or []
        if isinstance(item, dict) and item.get("gate_id")
    }
    human_gate_statuses = {
        str(item.get("gate_id")): str(item.get("status"))
        for item in human_gate_rows or []
        if isinstance(item, dict) and item.get("gate_id")
    }
    human_gate_report_complete = (
        isinstance(human_gate_status_report, dict)
        and human_gate_status_report.get("status") == "pending_human_gates"
        and human_gate_status_report.get("external_writes_performed") is False
        and artifact_refs.get("human_gate_status_report") == manifest.human_gate_status_report_ref
        and REQUIRED_HUMAN_GATES.issubset(human_gate_ids)
        and human_gate_statuses.get("human_intake_confirmation") == "completed"
        and all(
            human_gate_statuses.get(gate_id) == "pending"
            for gate_id in REQUIRED_HUMAN_GATES - {"human_intake_confirmation"}
        )
        and all(gate_id in review_text for gate_id in REQUIRED_HUMAN_GATES)
        and "Human gate status report:" in review_text
    )
    deadline_guard_items = (
        deadline_docketing_guard_report.get("candidate_items")
        if isinstance(deadline_docketing_guard_report, dict)
        else None
    )
    deadline_guard_checks = (
        deadline_docketing_guard_report.get("checks")
        if isinstance(deadline_docketing_guard_report, dict)
        else None
    )
    deadline_guard_candidate_count = (
        deadline_docketing_guard_report.get("candidate_count")
        if isinstance(deadline_docketing_guard_report, dict)
        else None
    )
    deadline_guard_review_required_count = (
        deadline_docketing_guard_report.get("review_required_count")
        if isinstance(deadline_docketing_guard_report, dict)
        else None
    )
    deadline_guard_item_ids = {
        str(item.get("deadline_candidate_id"))
        for item in deadline_guard_items or []
        if isinstance(item, dict) and item.get("deadline_candidate_id")
    }
    packet_deadline_rows = (
        preflight_packet.get("deadline_candidates") if isinstance(preflight_packet, dict) else None
    )
    packet_deadline_ids = {
        str(item.get("deadline_candidate_id"))
        for item in packet_deadline_rows or []
        if isinstance(item, dict) and item.get("deadline_candidate_id")
    }
    deadline_guard_passed_checks = {
        str(item.get("check_id"))
        for item in deadline_guard_checks or []
        if isinstance(item, dict) and item.get("status") == "passed" and item.get("check_id")
    }
    deadline_guard_report_complete = (
        isinstance(deadline_docketing_guard_report, dict)
        and deadline_docketing_guard_report.get("status") == "passed"
        and deadline_docketing_guard_report.get("docketing_action_performed") is False
        and deadline_docketing_guard_report.get("docketing_action_allowed") is False
        and deadline_docketing_guard_report.get("external_writes_performed") is False
        and deadline_docketing_guard_report.get("non_authoritative") is True
        and deadline_docketing_guard_report.get("proposed_next_gate") == "human_deadline_review"
        and deadline_guard_candidate_count == deadline_guard_review_required_count
        and deadline_guard_candidate_count == len(packet_deadline_ids)
        and deadline_guard_item_ids == packet_deadline_ids
        and isinstance(deadline_guard_items, list)
        and isinstance(deadline_guard_checks, list)
        and {
            "deadline_candidates_source_bound",
            "deadline_candidates_require_human_review",
            "deadline_docketing_forbidden_by_policy",
            "deadline_docketing_not_performed",
        }.issubset(deadline_guard_passed_checks)
        and all(
            isinstance(item, dict)
            and item.get("requires_human_verification") is True
            and item.get("proposed_next_gate") == "human_deadline_review"
            and item.get("source_evidence_status") == "source_bound_candidate"
            and item.get("evidence_refs")
            and str(item.get("expression")) in review_text
            for item in deadline_guard_items
        )
        and "Deadline docketing guard report:" in review_text
        and "Docketing action performed: False" in review_text
        and "Docketing action allowed: False" in review_text
        and "human_deadline_review" in review_text
    )
    missing_blockers = sorted(REQUIRED_FINAL_BLOCKERS - set(manifest.final_blockers))
    missing_prohibited = sorted(REQUIRED_PROHIBITED_ACTIONS - set(manifest.prohibited_actions))
    blocker_detail_rows = (
        matter_opening_readiness.get("blocker_details")
        if isinstance(matter_opening_readiness, dict)
        else None
    )
    prohibited_detail_rows = (
        matter_opening_readiness.get("prohibited_action_details")
        if isinstance(matter_opening_readiness, dict)
        else None
    )
    blocker_detail_rendered = (
        isinstance(blocker_detail_rows, list)
        and bool(blocker_detail_rows)
        and all(
            isinstance(item, dict)
            and item.get("blocker_code")
            and item.get("structured_ref")
            and str(item["blocker_code"]) in review_text
            and str(item["structured_ref"]) in review_text
            for item in blocker_detail_rows
        )
    )
    prohibited_detail_rendered = (
        isinstance(prohibited_detail_rows, list)
        and bool(prohibited_detail_rows)
        and all(
            isinstance(item, dict)
            and item.get("action_code")
            and item.get("structured_ref")
            and str(item["action_code"]) in review_text
            and str(item["structured_ref"]) in review_text
            for item in prohibited_detail_rows
        )
    )

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
            "linked_review_forms_preserve_evidence_and_boundaries",
            not linked_review_form_missing_content,
            "Linked intake and budget review forms preserve evidence hashes and non-authorization boundary text.",
            [
                artifact_refs.get("preflight_intake_review_form", ""),
                artifact_refs.get("legal_budget_review_form", ""),
            ],
            {"missing_content_by_form": linked_review_form_missing_content},
        ),
        _check(
            "required_human_gates_present",
            not missing_gates,
            "Manifest preserves all required human gates.",
            [manifest_ref],
            {"missing_gates": missing_gates},
        ),
        _check(
            "human_gate_status_report_complete",
            bool(human_gate_report_complete),
            "Human-gate status report preserves completed intake confirmation and pending approval gates.",
            [
                artifact_refs.get("human_gate_status_report", ""),
                str(review_package_path),
            ],
            {
                "gate_ids": sorted(human_gate_ids),
                "gate_statuses": human_gate_statuses,
            },
        ),
        _check(
            "deadline_docketing_guard_report_complete",
            bool(deadline_guard_report_complete),
            "Deadline guard report preserves source-bound review-only candidates and no docketing.",
            [
                artifact_refs.get("preflight_deadline_docketing_guard_report", ""),
                str(review_package_path),
            ],
            {
                "deadline_candidate_ids": sorted(deadline_guard_item_ids),
                "packet_deadline_candidate_ids": sorted(packet_deadline_ids),
                "candidate_count": deadline_guard_candidate_count,
                "review_required_count": deadline_guard_review_required_count,
                "passed_checks": sorted(deadline_guard_passed_checks),
            },
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
            "readiness_blocker_details_rendered",
            bool(blocker_detail_rendered and prohibited_detail_rendered),
            "Review package renders structured blocker and prohibited-action support details.",
            [
                artifact_refs.get("matter_opening_readiness", ""),
                str(review_package_path),
            ],
            {
                "blocker_detail_count": (
                    len(blocker_detail_rows) if isinstance(blocker_detail_rows, list) else 0
                ),
                "prohibited_action_detail_count": (
                    len(prohibited_detail_rows) if isinstance(prohibited_detail_rows, list) else 0
                ),
            },
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
            "exception_lake_handoff_manifest_preserved",
            isinstance(exception_handoff_manifest, dict)
            and exception_handoff_manifest.get("status") == "dry_run_ready_not_admitted"
            and exception_handoff_manifest.get("admission_state") == "dry_run_not_admitted"
            and exception_handoff_manifest.get("target_runtime_repo")
            == "LawFirm-os-exceptions-lake-runtime"
            and exception_handoff_manifest.get("sqlite_write_performed") is False
            and exception_handoff_manifest.get("external_writes_performed") is False
            and manifest.exception_lake_handoff_manifest_ref
            == artifact_refs.get("budget_exception_lake_handoff_manifest"),
            "Final package carries the dry-run Exception Lake handoff manifest without SQLite or external writes.",
            [artifact_refs.get("budget_exception_lake_handoff_manifest", "")],
            {
                "handoff_status": (
                    exception_handoff_manifest.get("status")
                    if isinstance(exception_handoff_manifest, dict)
                    else None
                ),
                "sqlite_write_performed": (
                    exception_handoff_manifest.get("sqlite_write_performed")
                    if isinstance(exception_handoff_manifest, dict)
                    else None
                ),
            },
        ),
        _check(
            "run_ledgers_present",
            len(manifest.run_ledger_refs) >= 2
            and all(Path(ref).exists() for ref in manifest.run_ledger_refs),
            "Manifest points to both preflight and budget run ledgers.",
            manifest.run_ledger_refs,
        ),
        _check(
            "run_ledger_integrity_reports_passed",
            isinstance(preflight_ledger_integrity, dict)
            and preflight_ledger_integrity.get("status") == "passed"
            and preflight_ledger_integrity.get("external_writes_performed") is False
            and preflight_ledger_integrity.get("local_artifact_refs_only") is True
            and isinstance(budget_ledger_integrity, dict)
            and budget_ledger_integrity.get("status") == "passed"
            and budget_ledger_integrity.get("external_writes_performed") is False
            and budget_ledger_integrity.get("local_artifact_refs_only") is True
            and set(manifest.run_ledger_integrity_report_refs)
            == {
                artifact_refs.get("preflight_run_ledger_integrity_report", ""),
                artifact_refs.get("budget_run_ledger_integrity_report", ""),
            },
            "Preflight and budget run-ledger integrity reports pass and stay local.",
            [
                artifact_refs.get("preflight_run_ledger_integrity_report", ""),
                artifact_refs.get("budget_run_ledger_integrity_report", ""),
            ],
            {
                "preflight_status": (
                    preflight_ledger_integrity.get("status")
                    if isinstance(preflight_ledger_integrity, dict)
                    else None
                ),
                "budget_status": (
                    budget_ledger_integrity.get("status")
                    if isinstance(budget_ledger_integrity, dict)
                    else None
                ),
            },
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
