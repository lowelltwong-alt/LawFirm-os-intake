from __future__ import annotations

from pathlib import Path

from .models import (
    ContextBoundaryReport,
    EvidenceCompletenessReport,
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
    "### Data Scope Gate",
    "### Model Adapter Boundary",
    "### Evidence Completeness",
    "### Context Boundary",
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
    "### Driver Profile Summary",
    "### Scenario Comparison",
    "### Carrier-Compliant Projection",
    "### Workbook Mapping Status",
    "### Unresolved Budget Assumptions",
    "## Exception And Escalation Records",
    "### Exception Lake Readiness",
    "### Exception Lake Handoff",
    "### Exception Lake Mapping Package",
    "### Exception Candidate Details",
    "### Budget Actual Comparison",
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
        "## Driver Profile Summary",
        "## Scenario Comparison",
        "## Carrier-Compliant Projection",
        "## Workbook Mapping Status",
        "## Unresolved Budget Assumptions",
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
    "data_scope_gate_report",
    "preflight_source_inventory",
    "preflight_segments",
    "preflight_ingestion_result",
    "preflight_ingestion_volume_profile",
    "preflight_rust_ingestion_readiness_report",
    "preflight_model_adapter_report",
    "preflight_evidence_completeness_report",
    "preflight_context_boundary_report",
    "preflight_intake_review_form",
    "preflight_deadline_docketing_guard_report",
    "human_confirmation",
    "conflict_search_seed",
    "case_driver_profile",
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
    "budget_exception_lake_mapping_package",
    "budget_actual_comparison_report",
    "budget_run_ledger",
    "preflight_run_ledger",
    "preflight_run_ledger_integrity_report",
    "budget_run_ledger_integrity_report",
    "human_review_outcome",
    "human_confirmation_history",
    "human_gate_status_report",
    "budget_submission_guard_report",
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
    exception_mapping_package = _read_json(
        Path(artifact_refs.get("budget_exception_lake_mapping_package", ""))
    )
    budget_actual_comparison_report = _read_json(
        Path(artifact_refs.get("budget_actual_comparison_report", ""))
    )
    preflight_packet = _read_json(Path(artifact_refs.get("preflight_packet", "")))
    data_scope_gate_report = _read_json(Path(artifact_refs.get("data_scope_gate_report", "")))
    matter_opening_readiness = _read_json(Path(artifact_refs.get("matter_opening_readiness", "")))
    human_gate_status_report = _read_json(Path(artifact_refs.get("human_gate_status_report", "")))
    budget_submission_guard_report = _read_json(
        Path(artifact_refs.get("budget_submission_guard_report", ""))
    )
    legal_budget_proposal = _read_json(Path(artifact_refs.get("legal_budget_proposal", "")))
    case_driver_profile = _read_json(Path(artifact_refs.get("case_driver_profile", "")))
    deadline_docketing_guard_report = _read_json(
        Path(artifact_refs.get("preflight_deadline_docketing_guard_report", ""))
    )
    evidence_completeness_report_payload = _read_json(
        Path(artifact_refs.get("preflight_evidence_completeness_report", ""))
    )
    context_boundary_report_payload = _read_json(
        Path(artifact_refs.get("preflight_context_boundary_report", ""))
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
    data_scope_gate_report_complete = (
        isinstance(data_scope_gate_report, dict)
        and data_scope_gate_report.get("status") == "passed"
        and data_scope_gate_report.get("runtime_mode") == "synthetic_only"
        and data_scope_gate_report.get("data_origin") == "synthetic"
        and data_scope_gate_report.get("contains_real_client_data") is False
        and data_scope_gate_report.get("contains_real_matter_data") is False
        and data_scope_gate_report.get("contains_privileged_data") is False
        and data_scope_gate_report.get("raw_payload_written") is False
        and data_scope_gate_report.get("public_data_direct_ingestion_allowed") is False
        and data_scope_gate_report.get("external_writes_performed") is False
        and data_scope_gate_report.get("non_authoritative") is True
        and artifact_refs.get("data_scope_gate_report") == manifest.data_scope_gate_report_ref
        and "Data scope gate status: passed" in review_text
        and "Runtime mode: synthetic_only" in review_text
        and "Data origin: synthetic" in review_text
        and "Contains real client data: False" in review_text
        and "Raw payload written before gate: False" in review_text
    )
    budget_submission_guard_checks = (
        budget_submission_guard_report.get("checks")
        if isinstance(budget_submission_guard_report, dict)
        else None
    )
    budget_submission_guard_passed_checks = {
        str(item.get("check_id"))
        for item in budget_submission_guard_checks or []
        if isinstance(item, dict) and item.get("status") == "passed" and item.get("check_id")
    }
    budget_submission_guard_actions = (
        {str(item) for item in (budget_submission_guard_report or {}).get("guarded_actions", [])}
        if isinstance(budget_submission_guard_report, dict)
        else set()
    )
    budget_submission_guard_complete = (
        isinstance(budget_submission_guard_report, dict)
        and budget_submission_guard_report.get("status") == "passed"
        and budget_submission_guard_report.get("approval_state") == "proposed_for_human_review"
        and budget_submission_guard_report.get("not_authorized_for_client_submission") is True
        and budget_submission_guard_report.get("client_submission_performed") is False
        and budget_submission_guard_report.get("carrier_submission_performed") is False
        and budget_submission_guard_report.get("billing_handoff_performed") is False
        and budget_submission_guard_report.get("external_writes_performed") is False
        and budget_submission_guard_report.get("non_authoritative") is True
        and budget_submission_guard_report.get("required_human_gate") == "human_budget_review"
        and artifact_refs.get("budget_submission_guard_report")
        == manifest.budget_submission_guard_report_ref
        and {
            "client_budget_submission",
            "carrier_budget_submission",
            "billing_handoff",
        }.issubset(budget_submission_guard_actions)
        and {
            "budget_proposal_review_only",
            "human_budget_review_gate_pending",
            "readiness_blocks_budget_submission",
            "no_submission_or_billing_handoff_performed",
            "controlled_artifacts_are_local",
        }.issubset(budget_submission_guard_passed_checks)
        and "Budget submission guard report:" in review_text
        and "Budget submission guard status: passed" in review_text
        and "Client submission performed: False" in review_text
        and "Carrier submission performed: False" in review_text
        and "Billing handoff performed: False" in review_text
        and "human_budget_review" in review_text
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
    evidence_completeness_report: EvidenceCompletenessReport | None = None
    if isinstance(evidence_completeness_report_payload, dict):
        try:
            evidence_completeness_report = EvidenceCompletenessReport.model_validate(
                evidence_completeness_report_payload
            )
        except ValueError:
            evidence_completeness_report = None
    evidence_completeness_report_complete = (
        evidence_completeness_report is not None
        and evidence_completeness_report.status == "passed"
        and evidence_completeness_report.strict_evidence_required is True
        and evidence_completeness_report.human_confirmation_required is True
        and evidence_completeness_report.evidence_ref_count > 0
        and evidence_completeness_report.external_writes_performed is False
        and evidence_completeness_report.non_authoritative is True
        and all(check.status == "passed" for check in evidence_completeness_report.checks)
        and artifact_refs.get("preflight_evidence_completeness_report")
        == manifest.evidence_completeness_report_ref
        and "Evidence completeness status: passed" in review_text
        and "Evidence refs checked:" in review_text
        and "classification_candidates_source_bound" in review_text
        and "evidence_refs_match_segments" in review_text
        and "human_review_boundary_present" in review_text
    )
    context_boundary_report: ContextBoundaryReport | None = None
    if isinstance(context_boundary_report_payload, dict):
        try:
            context_boundary_report = ContextBoundaryReport.model_validate(
                context_boundary_report_payload
            )
        except ValueError:
            context_boundary_report = None
    context_boundary_report_complete = (
        context_boundary_report is not None
        and context_boundary_report.status == "passed"
        and context_boundary_report.observed_source_evidence_precedence is True
        and context_boundary_report.practice_context_is_observed_evidence is False
        and context_boundary_report.human_confirmation_required is True
        and context_boundary_report.external_writes_performed is False
        and context_boundary_report.non_authoritative is True
        and all(check.status == "passed" for check in context_boundary_report.checks)
        and artifact_refs.get("preflight_context_boundary_report")
        == manifest.context_boundary_report_ref
        and "Context boundary status: passed" in review_text
        and "Observed source evidence precedence: True" in review_text
        and "Practice context is observed evidence: False" in review_text
        and "context_influence_not_observed_fact" in review_text
        and "human_confirmation_required_for_context_ranked_candidates" in review_text
    )
    driver_profile_summary = (
        legal_budget_proposal.get("driver_profile_summary")
        if isinstance(legal_budget_proposal, dict)
        else None
    )
    workbook_mapping_visible = (
        "### Workbook Mapping Status" in review_text
        and "Workbook submission authorized: False" in review_text
        and (
            "Mapping report available: False" in review_text
            or "Mapping report status:" in review_text
        )
        and "Required before relying on filled carrier form:" in review_text
    )
    carrier_projection = (
        legal_budget_proposal.get("carrier_compliant_projection")
        if isinstance(legal_budget_proposal, dict)
        else None
    )
    carrier_projection_object_valid = (
        isinstance(carrier_projection, dict)
        and carrier_projection.get("rewrites_budget") is False
        and carrier_projection.get("not_authorized_for_client_submission") is True
        and carrier_projection.get("external_writes_performed") is False
    )
    carrier_projection_unavailable_visible = (
        not isinstance(carrier_projection, dict)
        and "Carrier-compliant projection available: False" in review_text
    )
    carrier_projection_visible = (
        "### Carrier-Compliant Projection" in review_text
        and "Proposal lines unchanged: True" in review_text
        and "Client/carrier submission authorized: False" in review_text
        and (
            ("Projection rewrites budget: False" in review_text and carrier_projection_object_valid)
            or carrier_projection_unavailable_visible
        )
    )
    budget_review_hardening_complete = (
        isinstance(driver_profile_summary, dict)
        and isinstance(case_driver_profile, dict)
        and driver_profile_summary.get("case_driver_profile_id")
        == case_driver_profile.get("case_driver_profile_id")
        and driver_profile_summary.get("profile_defaults_are_observed_facts") is False
        and driver_profile_summary.get("context_priors_are_observed_facts") is False
        and driver_profile_summary.get("requires_human_review") is True
        and driver_profile_summary.get("not_authoritative") is True
        and artifact_refs.get("case_driver_profile")
        and "### Driver Profile Summary" in review_text
        and "### Scenario Comparison" in review_text
        and carrier_projection_visible
        and workbook_mapping_visible
        and "### Unresolved Budget Assumptions" in review_text
        and "Profile defaults treated as observed facts: False" in review_text
        and "Context priors treated as observed facts: False" in review_text
        and "Human budget review required: True" in review_text
        and "budget unknown:" in review_text
    )
    required_mapping_issue_families = {
        "broken_template_formula",
        "missing_budget_code_mapping",
        "unknown_budget_driver",
        "guideline_or_cap_issue",
        "human_budget_change",
        "budget_actual_cost_variance",
    }
    mapping_rules = (
        exception_mapping_package.get("rules")
        if isinstance(exception_mapping_package, dict)
        else None
    )
    mapping_issue_families = {
        str(rule.get("issue_family"))
        for rule in mapping_rules or []
        if isinstance(rule, dict) and rule.get("issue_family")
    }
    exception_mapping_package_complete = (
        isinstance(exception_mapping_package, dict)
        and exception_mapping_package.get("status") == "passed"
        and exception_mapping_package.get("admission_state") == "dry_run_not_admitted"
        and exception_mapping_package.get("target_runtime_repo")
        == "LawFirm-os-exceptions-lake-runtime"
        and exception_mapping_package.get("sqlite_write_performed") is False
        and exception_mapping_package.get("external_writes_performed") is False
        and exception_mapping_package.get("raw_payload_included") is False
        and exception_mapping_package.get("canonical_promotion_required") is True
        and required_mapping_issue_families.issubset(mapping_issue_families)
        and "### Exception Lake Mapping Package" in review_text
        and "budget_human_change_recorded" in review_text
        and "budget_actual_cost_variance_requires_review" in review_text
    )
    actual_comparison_complete = (
        isinstance(budget_actual_comparison_report, dict)
        and budget_actual_comparison_report.get("comparison_scope") == "phase"
        and budget_actual_comparison_report.get("billing_connector_read_performed") is False
        and budget_actual_comparison_report.get("billing_connector_write_performed") is False
        and budget_actual_comparison_report.get("external_writes_performed") is False
        and isinstance(budget_actual_comparison_report.get("phase_comparisons"), list)
        and "### Budget Actual Comparison" in review_text
        and "Billing connector read performed: False" in review_text
        and "Billing connector write performed: False" in review_text
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
            "data_scope_gate_report_complete",
            bool(data_scope_gate_report_complete),
            "Data-scope gate report proves synthetic-only scope and no raw payload write before the gate.",
            [
                artifact_refs.get("data_scope_gate_report", ""),
                str(review_package_path),
            ],
            {
                "status": (
                    data_scope_gate_report.get("status")
                    if isinstance(data_scope_gate_report, dict)
                    else None
                ),
                "data_origin": (
                    data_scope_gate_report.get("data_origin")
                    if isinstance(data_scope_gate_report, dict)
                    else None
                ),
            },
        ),
        _check(
            "budget_submission_guard_report_complete",
            bool(budget_submission_guard_complete),
            "Budget submission guard report preserves review-only budget, pending budget gate, and no submission or billing handoff.",
            [
                artifact_refs.get("budget_submission_guard_report", ""),
                str(review_package_path),
            ],
            {
                "guarded_actions": sorted(budget_submission_guard_actions),
                "passed_checks": sorted(budget_submission_guard_passed_checks),
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
            "evidence_completeness_report_complete",
            bool(evidence_completeness_report_complete),
            "Evidence completeness report proves candidate evidence refs, unknown options, and human-review boundary.",
            [
                artifact_refs.get("preflight_evidence_completeness_report", ""),
                str(review_package_path),
            ],
            {
                "status": (
                    evidence_completeness_report.status if evidence_completeness_report else None
                ),
                "strict_evidence_required": (
                    evidence_completeness_report.strict_evidence_required
                    if evidence_completeness_report
                    else None
                ),
                "evidence_ref_count": (
                    evidence_completeness_report.evidence_ref_count
                    if evidence_completeness_report
                    else None
                ),
            },
        ),
        _check(
            "context_boundary_report_complete",
            bool(context_boundary_report_complete),
            "Context boundary report proves practice context stayed separate from observed evidence.",
            [
                artifact_refs.get("preflight_context_boundary_report", ""),
                str(review_package_path),
            ],
            {
                "status": context_boundary_report.status if context_boundary_report else None,
                "context_signal_candidate_count": (
                    context_boundary_report.context_signal_candidate_count
                    if context_boundary_report
                    else None
                ),
                "practice_context_is_observed_evidence": (
                    context_boundary_report.practice_context_is_observed_evidence
                    if context_boundary_report
                    else None
                ),
            },
        ),
        _check(
            "budget_review_hardening_complete",
            bool(budget_review_hardening_complete),
            "Budget review package renders driver profile, scenario comparison, carrier projection, workbook mapping posture, and unresolved assumptions.",
            [
                artifact_refs.get("legal_budget_proposal", ""),
                artifact_refs.get("case_driver_profile", ""),
                str(review_package_path),
            ],
            {
                "driver_profile_summary_present": isinstance(driver_profile_summary, dict),
                "case_driver_profile_ref": artifact_refs.get("case_driver_profile", ""),
                "carrier_projection_visible": carrier_projection_visible,
                "workbook_mapping_visible": workbook_mapping_visible,
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
            "exception_lake_mapping_package_complete",
            bool(exception_mapping_package_complete),
            "Final package carries dry-run mappings for budget template, code, driver, guideline, human-change, and actual-variance issues.",
            [
                artifact_refs.get("budget_exception_lake_mapping_package", ""),
                str(review_package_path),
            ],
            {
                "issue_families": sorted(mapping_issue_families),
                "missing_issue_families": sorted(
                    required_mapping_issue_families - mapping_issue_families
                ),
            },
        ),
        _check(
            "budget_actual_comparison_report_complete",
            bool(actual_comparison_complete),
            "Budget actual comparison report preserves phase-level comparison posture without billing connector reads or writes.",
            [
                artifact_refs.get("budget_actual_comparison_report", ""),
                str(review_package_path),
            ],
            {
                "status": (
                    budget_actual_comparison_report.get("status")
                    if isinstance(budget_actual_comparison_report, dict)
                    else None
                ),
                "phase_count": (
                    len(budget_actual_comparison_report.get("phase_comparisons", []))
                    if isinstance(budget_actual_comparison_report, dict)
                    else 0
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
