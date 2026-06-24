from __future__ import annotations

from pathlib import Path
from typing import Any

from .ingestion import validate_ingestion_result
from .models import (
    BudgetPreconditionReport,
    BudgetProposal,
    BudgetSubmissionGuardReport,
    ConflictSeedPacket,
    ContractStateReport,
    DeadlineDocketingGuardReport,
    EvidenceGraph,
    ExceptionLakeHandoffManifest,
    ExceptionLakeReadinessReport,
    FixtureGoldReport,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IngestionResult,
    IngestionVolumeProfile,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    ModelAdapterReport,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
    RunLedgerIntegrityReport,
    RustIngestionReadinessReport,
    SafetyGateReport,
    StarterReleaseAuditCheck,
    StarterReleaseAuditReport,
)
from .util import load_json, load_jsonl, new_id, now_iso
from .workflow import _validate_refs


REQUIRED_ROOT_FILES = [
    "README.md",
    "AI_WORK_START_HERE.md",
    "AGENTS.md",
    "DATA_FLOW_MAP.md",
    "DEFINITION_OF_DONE.md",
    "GOVERNANCE_BOUNDARY.md",
    "NON_GOALS.md",
    "ROADMAP.md",
]

REQUIRED_PREFLIGHT_ARTIFACTS = {
    "raw_input": "raw_input.json",
    "contract_state_report": "contract_state_report.json",
    "model_adapter_report": "model_adapter_report.json",
    "ingestion_result": "ingestion_result.json",
    "ingestion_volume_profile": "ingestion_volume_profile.json",
    "rust_ingestion_readiness_report": "rust_ingestion_readiness_report.json",
    "source_inventory": "source_inventory.json",
    "segments": "segments.json",
    "effective_context": "effective_context.json",
    "preflight_packet": "intake_preflight_packet.json",
    "intake_review_form": "intake_review_form.md",
    "deadline_docketing_guard_report": "deadline_docketing_guard_report.json",
    "preflight_exception_candidates": "exception_lake_candidates.jsonl",
    "preflight_exception_lake_readiness_report": "exception_lake_readiness_report.json",
    "preflight_exception_lake_handoff_manifest": "exception_lake_handoff_manifest.json",
    "preflight_evidence_graph": "evidence_graph.json",
    "preflight_fixture_gold_report": "fixture_gold_report.json",
    "preflight_run_ledger": "run_ledger.jsonl",
    "preflight_run_ledger_integrity_report": "run_ledger_integrity_report.json",
}

REQUIRED_BUDGET_ARTIFACTS = {
    "human_confirmation": "human_confirmation.json",
    "human_review_outcome": "human_review_outcome",
    "human_confirmation_history": "human_confirmation_history.jsonl",
    "budget_precondition_report": "budget_precondition_report.json",
    "budget_submission_guard_report": "budget_submission_guard_report.json",
    "conflict_search_seed": "conflict_search_seed_packet.json",
    "legal_budget_proposal": "legal_budget_proposal.json",
    "legal_budget_review_form": "legal_budget_review_form.md",
    "matter_opening_readiness": "matter_opening_readiness.json",
    "budget_exception_candidates": "exception_lake_candidates.jsonl",
    "budget_exception_lake_readiness_report": "exception_lake_readiness_report.json",
    "budget_exception_lake_handoff_manifest": "exception_lake_handoff_manifest.json",
    "safety_gate_report": "safety_gate_report.json",
    "review_package": "matter_opening_review_package.md",
    "review_package_manifest": "review_package_manifest.json",
    "review_package_completeness_report": "review_package_completeness_report.json",
    "budget_evidence_graph": "evidence_graph.json",
    "budget_fixture_gold_report": "fixture_gold_report.json",
    "budget_run_ledger": "run_ledger.jsonl",
    "budget_run_ledger_integrity_report": "run_ledger_integrity_report.json",
}

EXPECTED_PREFLIGHT_EXCEPTION_LABELS = {
    "source_missing",
    "duplicate_source_detected",
    "prompt_injection_source_content",
    "critic_role_candidates_ambiguous",
    "prohibited_transition_attempted_conflicts_cleared",
    "prohibited_transition_attempted_deadline_docketed",
    "prohibited_transition_attempted_matter_opened",
}

EXPECTED_BUDGET_EXCEPTION_LABELS = {
    "matter_opening_blocked_pending_conflicts_and_engagement",
    "budget_unknowns_require_review",
}

REQUIRED_PACKET_CANDIDATE_FIELDS = {
    "party_candidates",
    "inbound_event_candidates",
    "matter_family_candidates",
    "representation_posture_candidates",
    "deadline_candidates",
    "missing_information_candidates",
    "critic_findings",
}

REQUIRED_SOURCE_COVERAGE_STATES = {"read", "missing"}
REQUIRED_SOURCE_AVAILABILITY_STATES = {"available", "missing", "duplicate"}

REQUIRED_BUDGET_GRAPH_NODE_TYPES = {
    "source",
    "segment",
    "party_candidate",
    "party_role_candidate",
    "inbound_event_candidate",
    "matter_family_candidate",
    "representation_posture_candidate",
    "deadline_candidate",
    "missing_information_candidate",
    "critic_finding",
    "human_confirmation",
    "human_review_outcome",
    "conflict_seed_packet",
    "conflict_search_term",
    "budget_proposal",
    "budget_line",
    "budget_support_item",
    "matter_opening_readiness",
    "matter_opening_blocker",
    "prohibited_action_guardrail",
    "structured_ref",
}

REQUIRED_BUDGET_GRAPH_RELATIONSHIPS = {
    "contains",
    "supports_party_candidate",
    "supports_party_role_candidate",
    "supports_matter_candidate",
    "supports_representation_posture_candidate",
    "supports_deadline_candidate",
    "supports_missing_information_candidate",
    "supports_critic_finding",
    "supports_human_confirmation",
    "recorded_as_human_review_outcome",
    "supports_conflict_search_term",
    "included_in_conflict_seed",
    "authorizes_budget_proposal_generation",
    "supports_budget_line",
    "supports_budget_support_item",
    "blocks_matter_opening_readiness",
    "supports_matter_opening_blocker",
    "supports_prohibited_action_guardrail",
    "guards_matter_opening_readiness",
}

REQUIRED_REVIEW_PACKAGE_PHRASES = {
    "# Matter Opening Review Package",
    "## Source Inventory",
    "## Candidate Alternatives",
    "## Conflict Search Seed",
    "## Budget Proposal",
    "## Exception And Escalation Records",
    "## Run Ledger Summary",
    "blocked_pending_conflicts_and_engagement",
    "This package does not clear conflicts",
    "submit a budget",
}

REQUIRED_PREFLIGHT_LEDGER_STEPS = {
    "run_started",
    "adapter_selected",
    "contract_state_gate",
    "data_origin_gate",
    "context_resolution",
    "python_reference_ingestion",
    "specialist_workers",
    "preflight_packet_built",
    "fixture_gold_evaluated",
}

REQUIRED_BUDGET_LEDGER_STEPS = {
    "budget_run_started",
    "human_review_outcome_recorded",
    "budget_precondition_gate",
    "human_confirmation_consumed",
    "conflict_seed_and_budget_proposal_built",
    "fixture_gold_evaluated",
    "matter_opening_review_package_built",
}

CURRENCY_TOLERANCE = 0.01


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    requirement_refs: list[str] | None = None,
    artifact_refs: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> StarterReleaseAuditCheck:
    return StarterReleaseAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        requirement_refs=requirement_refs or [],
        message=message,
        artifact_refs=artifact_refs or [],
        details=details or {},
    )


def _find_preflight_dir(demo_dir: Path) -> Path | None:
    preflight_root = demo_dir / "preflight"
    if not preflight_root.exists():
        return None
    candidates = [path for path in preflight_root.iterdir() if path.is_dir()]
    return candidates[0] if len(candidates) == 1 else None


def _json_or_none(path: Path) -> Any | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return load_json(path)
    except (OSError, ValueError):
        return None


def _model_or_none(model: type, path: Path) -> Any | None:
    payload = _json_or_none(path)
    if payload is None:
        return None
    try:
        return model.model_validate(payload)
    except ValueError:
        return None


def _text_or_empty(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _human_review_outcome_path(budget_dir: Path) -> Path | None:
    matches = sorted(budget_dir.glob("human_review_outcome.*.json"))
    return matches[0] if len(matches) == 1 else None


def _artifact_paths(
    demo_dir: Path, preflight_dir: Path | None, budget_dir: Path
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if preflight_dir:
        paths.update(
            {
                key: preflight_dir / filename
                for key, filename in REQUIRED_PREFLIGHT_ARTIFACTS.items()
            }
        )
    paths.update(
        {
            key: budget_dir / filename
            for key, filename in REQUIRED_BUDGET_ARTIFACTS.items()
            if key != "human_review_outcome"
        }
    )
    outcome_path = _human_review_outcome_path(budget_dir)
    if outcome_path:
        paths["human_review_outcome"] = outcome_path
    else:
        paths["human_review_outcome"] = budget_dir / "human_review_outcome.*.json"
    paths["demo_dir"] = demo_dir
    return paths


def _artifact_refs(paths: dict[str, Path], keys: list[str]) -> list[str]:
    return [str(paths[key]) for key in keys if key in paths]


def _labels(candidates: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("local_event_label")) for item in candidates}


def _step_names(events: list[dict[str, Any]]) -> set[str]:
    return {str(event.get("step_name")) for event in events if event.get("step_name")}


def _all_candidate_registry_files_are_noncanonical(repo_root: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for path in sorted((repo_root / "contracts/candidate").glob("*.json")):
        payload = _json_or_none(path)
        if not isinstance(payload, dict) or payload.get("canonical") is not False:
            failures.append(str(path))
    return not failures, failures


def _artifact_refs_are_local(refs: list[str]) -> bool:
    external_prefixes = ("http://", "https://", "imap://", "smtp://", "s3://", "gs://")
    forbidden_terms = (
        "gmail",
        "outlook",
        "imanage",
        "conflicts_system",
        "carrier_portal",
        "court_connector",
        "billing_system",
    )
    for ref in refs:
        lowered = ref.casefold()
        if lowered.startswith(external_prefixes):
            return False
        if any(term in lowered for term in forbidden_terms):
            return False
    return True


def _candidate_refs_are_valid(packet: IntakePreflightPacket | None) -> tuple[bool, str | None]:
    if packet is None:
        return False, "preflight packet unavailable"
    try:
        _validate_refs(packet)
    except ValueError as exc:
        return False, str(exc)
    return True, None


def _source_coverage_details(
    packet: IntakePreflightPacket | None,
) -> tuple[bool, dict[str, Any]]:
    if packet is None:
        return False, {"error": "preflight packet unavailable"}
    read_states = {item.read_state for item in packet.source_inventory}
    availability_states = {item.availability_state for item in packet.source_inventory}
    duplicate_links = [
        item.source_id
        for item in packet.source_inventory
        if item.availability_state == "duplicate" and item.duplicate_of_source_id
    ]
    sources_with_attachment_refs = [
        item.source_id for item in packet.source_inventory if item.attachment_refs
    ]
    summary = packet.source_coverage_summary
    passed = (
        summary.get("coverage_complete") is False
        and summary.get("missing_sources", 0) >= 1
        and summary.get("duplicate_sources", 0) >= 1
        and summary.get("attachment_reference_count", 0) >= 1
        and REQUIRED_SOURCE_COVERAGE_STATES.issubset(read_states)
        and REQUIRED_SOURCE_AVAILABILITY_STATES.issubset(availability_states)
        and bool(duplicate_links)
        and bool(sources_with_attachment_refs)
    )
    return passed, {
        "coverage_summary": summary,
        "read_states": sorted(read_states),
        "availability_states": sorted(availability_states),
        "duplicate_source_ids": duplicate_links,
        "sources_with_attachment_refs": sources_with_attachment_refs,
    }


def _candidate_surface_details(
    packet: IntakePreflightPacket | None,
) -> tuple[bool, dict[str, Any]]:
    if packet is None:
        return False, {"error": "preflight packet unavailable"}
    counts = {
        "party_candidates": len(packet.party_candidates),
        "party_role_candidates": sum(
            len(party.role_candidates) for party in packet.party_candidates
        ),
        "inbound_event_candidates": len(packet.inbound_event_candidates),
        "matter_family_candidates": len(packet.matter_family_candidates),
        "representation_posture_candidates": len(packet.representation_posture_candidates),
        "deadline_candidates": len(packet.deadline_candidates),
        "missing_information_candidates": len(packet.missing_information_candidates),
        "critic_findings": len(packet.critic_findings),
    }
    top_labels = {
        "inbound_event": (
            packet.inbound_event_candidates[0].label if packet.inbound_event_candidates else None
        ),
        "matter_family": (
            packet.matter_family_candidates[0].label if packet.matter_family_candidates else None
        ),
        "representation_posture": (
            packet.representation_posture_candidates[0].label
            if packet.representation_posture_candidates
            else None
        ),
    }
    source_statuses = {
        candidate.source_evidence_status
        for candidate in [
            *packet.inbound_event_candidates,
            *packet.matter_family_candidates,
            *packet.representation_posture_candidates,
        ]
    }
    passed = (
        all(counts[field] > 0 for field in REQUIRED_PACKET_CANDIDATE_FIELDS)
        and counts["party_role_candidates"] > 0
        and top_labels["inbound_event"] is not None
        and top_labels["matter_family"] is not None
        and top_labels["representation_posture"] is not None
        and "unknown_option" in source_statuses
        and "ROLE_CANDIDATES_AMBIGUOUS" in {finding.code for finding in packet.critic_findings}
    )
    return passed, {
        "candidate_counts": counts,
        "top_labels": top_labels,
        "source_evidence_statuses": sorted(source_statuses),
        "critic_codes": sorted({finding.code for finding in packet.critic_findings}),
    }


def _evidence_graph_details(graph: EvidenceGraph | None) -> tuple[bool, dict[str, Any]]:
    if graph is None:
        return False, {"error": "evidence graph unavailable"}
    node_types = {node.node_type for node in graph.nodes}
    relationships = {edge.relationship for edge in graph.edges}
    missing_node_types = sorted(REQUIRED_BUDGET_GRAPH_NODE_TYPES - node_types)
    missing_relationships = sorted(REQUIRED_BUDGET_GRAPH_RELATIONSHIPS - relationships)
    source_bound_edges = [
        edge.relationship
        for edge in graph.edges
        if edge.relationship.startswith("supports_") and edge.evidence_refs
    ]
    passed = not missing_node_types and not missing_relationships and bool(source_bound_edges)
    return passed, {
        "node_type_count": len(node_types),
        "edge_relationship_count": len(relationships),
        "missing_node_types": missing_node_types,
        "missing_relationships": missing_relationships,
        "source_bound_support_edge_count": len(source_bound_edges),
    }


def _review_package_details(review_text: str) -> tuple[bool, dict[str, Any]]:
    missing = sorted(
        phrase for phrase in REQUIRED_REVIEW_PACKAGE_PHRASES if phrase not in review_text
    )
    return not missing, {"missing_phrases": missing}


def _ingestion_refs_are_valid(result: IngestionResult | None) -> tuple[bool, str | None]:
    if result is None:
        return False, "ingestion result unavailable"
    try:
        validate_ingestion_result(result)
    except ValueError as exc:
        return False, str(exc)
    return True, None


def _deterministic_budget_math_is_valid(
    budget: BudgetProposal | None,
) -> tuple[bool, dict[str, Any]]:
    if budget is None or budget.calculation_report is None:
        return False, {"error": "budget or calculation report unavailable"}
    report = budget.calculation_report
    details: dict[str, Any] = {
        "mode": report.mode,
        "deterministic": report.deterministic,
        "line_count": report.line_count,
    }
    if not report.deterministic:
        return False, details
    if report.line_count != len(budget.lines):
        details["error"] = "line count mismatch"
        return False, details
    if budget.pricing_status == "hours_only":
        unpriced = all(
            line.hourly_rate is None and line.estimated_fees is None for line in budget.lines
        )
        details["all_lines_unpriced"] = unpriced
        return unpriced and budget.total_proposed_budget is None, details
    if budget.pricing_status == "priced":
        subtotal = sum(line.estimated_fees or 0 for line in budget.lines)
        expenses = sum(line.estimated_expenses for line in budget.lines)
        contingency = subtotal * budget.contingency_percent / 100
        total = subtotal + expenses + contingency
        matches = (
            abs((budget.subtotal_fees or 0) - subtotal) <= CURRENCY_TOLERANCE
            and abs(budget.subtotal_expenses - expenses) <= CURRENCY_TOLERANCE
            and abs((budget.contingency_amount or 0) - contingency) <= CURRENCY_TOLERANCE
            and abs((budget.total_proposed_budget or 0) - total) <= CURRENCY_TOLERANCE
        )
        details.update(
            {
                "computed_subtotal_fees": subtotal,
                "computed_expenses": expenses,
                "computed_contingency": contingency,
                "computed_total": total,
            }
        )
        return matches, details
    return budget.pricing_status == "insufficient_information", details


def build_starter_release_audit_report(
    *,
    repo_root: str | Path,
    demo_dir: str | Path,
) -> StarterReleaseAuditReport:
    repo_root = Path(repo_root)
    demo_dir = Path(demo_dir)
    preflight_dir = _find_preflight_dir(demo_dir)
    budget_dir = demo_dir / "budget"
    paths = _artifact_paths(demo_dir, preflight_dir, budget_dir)

    packet = (
        _model_or_none(IntakePreflightPacket, paths["preflight_packet"])
        if "preflight_packet" in paths
        else None
    )
    contract_state = _model_or_none(ContractStateReport, paths["contract_state_report"])
    model_adapter = _model_or_none(ModelAdapterReport, paths["model_adapter_report"])
    ingestion_result = _model_or_none(IngestionResult, paths["ingestion_result"])
    ingestion_volume = _model_or_none(IngestionVolumeProfile, paths["ingestion_volume_profile"])
    rust_readiness = _model_or_none(
        RustIngestionReadinessReport, paths["rust_ingestion_readiness_report"]
    )
    deadline_guard = _model_or_none(
        DeadlineDocketingGuardReport, paths["deadline_docketing_guard_report"]
    )
    preflight_gold = _model_or_none(FixtureGoldReport, paths["preflight_fixture_gold_report"])
    confirmation = _model_or_none(HumanConfirmation, paths["human_confirmation"])
    human_review_outcome = _model_or_none(HumanReviewOutcomeRecord, paths["human_review_outcome"])
    budget_precondition = _model_or_none(
        BudgetPreconditionReport, paths["budget_precondition_report"]
    )
    conflict_seed = _model_or_none(ConflictSeedPacket, paths["conflict_search_seed"])
    budget = _model_or_none(BudgetProposal, paths["legal_budget_proposal"])
    budget_submission_guard = _model_or_none(
        BudgetSubmissionGuardReport, paths["budget_submission_guard_report"]
    )
    readiness = _model_or_none(MatterOpeningReadiness, paths["matter_opening_readiness"])
    budget_exception_readiness = _model_or_none(
        ExceptionLakeReadinessReport, paths["budget_exception_lake_readiness_report"]
    )
    preflight_exception_readiness = _model_or_none(
        ExceptionLakeReadinessReport, paths["preflight_exception_lake_readiness_report"]
    )
    budget_exception_handoff = _model_or_none(
        ExceptionLakeHandoffManifest, paths["budget_exception_lake_handoff_manifest"]
    )
    preflight_exception_handoff = _model_or_none(
        ExceptionLakeHandoffManifest, paths["preflight_exception_lake_handoff_manifest"]
    )
    safety = _model_or_none(SafetyGateReport, paths["safety_gate_report"])
    manifest = _model_or_none(ReviewPackageManifest, paths["review_package_manifest"])
    completeness = _model_or_none(
        ReviewPackageCompletenessReport, paths["review_package_completeness_report"]
    )
    preflight_ledger_integrity = _model_or_none(
        RunLedgerIntegrityReport, paths["preflight_run_ledger_integrity_report"]
    )
    budget_ledger_integrity = _model_or_none(
        RunLedgerIntegrityReport, paths["budget_run_ledger_integrity_report"]
    )
    budget_graph = _model_or_none(EvidenceGraph, paths["budget_evidence_graph"])
    budget_gold = _model_or_none(FixtureGoldReport, paths["budget_fixture_gold_report"])
    raw_input = _json_or_none(paths["raw_input"]) if "raw_input" in paths else None
    review_text = _text_or_empty(paths["review_package"])

    preflight_exceptions = load_jsonl(paths["preflight_exception_candidates"])
    budget_exceptions = load_jsonl(paths["budget_exception_candidates"])
    preflight_ledger = load_jsonl(paths["preflight_run_ledger"])
    budget_ledger = load_jsonl(paths["budget_run_ledger"])

    missing_root_files = [rel for rel in REQUIRED_ROOT_FILES if not (repo_root / rel).is_file()]
    duplicate_root = repo_root / "LawFirm-os-intake"
    required_artifact_keys = [
        key for key in [*REQUIRED_PREFLIGHT_ARTIFACTS, *REQUIRED_BUDGET_ARTIFACTS] if key in paths
    ]
    missing_artifacts = [
        key
        for key in required_artifact_keys
        if not paths[key].exists() or (paths[key].is_file() and paths[key].stat().st_size == 0)
    ]
    registry_ok, registry_failures = _all_candidate_registry_files_are_noncanonical(repo_root)
    packet_refs_ok, packet_ref_error = _candidate_refs_are_valid(packet)
    ingestion_refs_ok, ingestion_ref_error = _ingestion_refs_are_valid(ingestion_result)
    budget_math_ok, budget_math_details = _deterministic_budget_math_is_valid(budget)
    source_coverage_ok, source_coverage_details = _source_coverage_details(packet)
    candidate_surface_ok, candidate_surface_details = _candidate_surface_details(packet)
    budget_graph_ok, budget_graph_details = _evidence_graph_details(budget_graph)
    review_text_ok, review_text_details = _review_package_details(review_text)

    manifest_refs = list(manifest.artifact_refs.values()) if manifest else []
    all_exception_candidates = preflight_exceptions + budget_exceptions
    preflight_ledger_steps = _step_names(preflight_ledger)
    budget_ledger_steps = _step_names(budget_ledger)
    missing_preflight_steps = sorted(REQUIRED_PREFLIGHT_LEDGER_STEPS - preflight_ledger_steps)
    missing_budget_steps = sorted(REQUIRED_BUDGET_LEDGER_STEPS - budget_ledger_steps)
    exception_candidates_dry_run = all(
        item.get("status") == "dry_run_candidate"
        and item.get("raw_payload_included") is False
        and item.get("canonical_promotion_required") is True
        for item in all_exception_candidates
    )
    harbor_roles = [
        party.confirmed_role
        for party in (confirmation.confirmed_parties if confirmation else [])
        if party.name == "Harbor Point Insurance"
    ]

    checks = [
        _check(
            "front_door_files_present",
            not missing_root_files and not duplicate_root.exists(),
            "Root front-door and governance files exist without a nested duplicate repo root.",
            requirement_refs=["DoD-1", "DoD-2"],
            artifact_refs=[str(repo_root / rel) for rel in REQUIRED_ROOT_FILES],
            details={
                "missing_root_files": missing_root_files,
                "nested_duplicate_root_exists": duplicate_root.exists(),
            },
        ),
        _check(
            "required_demo_artifacts_present",
            not missing_artifacts and preflight_dir is not None and budget_dir.exists(),
            "North-star demo emitted every required preflight and budget artifact.",
            requirement_refs=["DoD-6"],
            artifact_refs=_artifact_refs(paths, required_artifact_keys),
            details={"missing_artifact_keys": missing_artifacts},
        ),
        _check(
            "synthetic_scope_only",
            bool(
                packet
                and packet.data_origin == "synthetic"
                and isinstance(raw_input, dict)
                and raw_input.get("data_origin") == "synthetic"
                and raw_input.get("contains_real_client_data") is False
                and raw_input.get("contains_real_matter_data") is False
                and raw_input.get("contains_privileged_data") is False
            ),
            "Runtime input and packet remain synthetic-only with no real or privileged data flags.",
            requirement_refs=["DoD-16", "DoD-17", "Safety-real-data-zero"],
            artifact_refs=_artifact_refs(paths, ["raw_input", "preflight_packet"]),
        ),
        _check(
            "contract_and_adapter_gates_passed",
            bool(
                contract_state
                and contract_state.status == "passed"
                and contract_state.lock_status == "reviewed_seed_lock"
                and model_adapter
                and model_adapter.status == "passed"
                and model_adapter.provider_call_performed is False
                and model_adapter.external_writes_allowed is False
                and model_adapter.raw_payload_externalized is False
            ),
            "Contract state and model adapter boundaries passed without provider calls or external writes.",
            requirement_refs=["DoD-16", "DoD-18"],
            artifact_refs=_artifact_refs(paths, ["contract_state_report", "model_adapter_report"]),
        ),
        _check(
            "candidate_registries_remain_noncanonical",
            registry_ok,
            "Local candidate registries remain explicitly noncanonical.",
            requirement_refs=["DoD-18"],
            artifact_refs=[
                str(path) for path in sorted((repo_root / "contracts/candidate").glob("*.json"))
            ],
            details={"canonical_registry_failures": registry_failures},
        ),
        _check(
            "evidence_refs_validate_against_segments",
            packet_refs_ok and ingestion_refs_ok,
            "Candidate and ingestion evidence refs preserve source IDs, segment IDs, offsets, and hashes.",
            requirement_refs=["DoD-7"],
            artifact_refs=_artifact_refs(
                paths, ["preflight_packet", "segments", "ingestion_result"]
            ),
            details={
                "packet_ref_error": packet_ref_error,
                "ingestion_ref_error": ingestion_ref_error,
            },
        ),
        _check(
            "north_star_source_coverage_exercised",
            source_coverage_ok,
            "North-star source inventory exercises missing, duplicate, attachment, and incomplete coverage states.",
            requirement_refs=["DoD-6", "Repeatable-quality"],
            artifact_refs=_artifact_refs(
                paths,
                ["source_inventory", "preflight_packet", "ingestion_result"],
            ),
            details=source_coverage_details,
        ),
        _check(
            "north_star_candidate_surface_complete",
            candidate_surface_ok,
            "North-star packet contains reviewable parties, roles, matter, posture, deadlines, gaps, and critic findings.",
            requirement_refs=["DoD-6", "DoD-7", "DoD-10", "Exception-aware"],
            artifact_refs=_artifact_refs(paths, ["preflight_packet", "intake_review_form"]),
            details=candidate_surface_details,
        ),
        _check(
            "evidence_graph_covers_intake_to_budget_deliverables",
            budget_graph_ok,
            "Budget evidence graph contains the named intake, conflict, budget, blocker, and guardrail deliverables with support edges.",
            requirement_refs=["DoD-6", "DoD-7"],
            artifact_refs=_artifact_refs(paths, ["budget_evidence_graph"]),
            details=budget_graph_details,
        ),
        _check(
            "human_review_package_tells_complete_north_star_story",
            review_text_ok,
            "Human-readable review package includes source inventory, candidates, conflict seed, budget, exceptions, ledgers, blockers, and boundary text.",
            requirement_refs=["DoD-2", "DoD-6", "DoD-14", "DoD-15"],
            artifact_refs=_artifact_refs(paths, ["review_package"]),
            details=review_text_details,
        ),
        _check(
            "rust_boundary_is_prepared_but_not_authorized",
            bool(
                ingestion_result
                and ingestion_result.parity_contract == "rust_ready_ingestion_v0_1"
                and ingestion_result.rust_replacement_allowed is False
                and ingestion_volume
                and ingestion_volume.rust_replacement_allowed is False
                and ingestion_volume.required_performance_profile_dimensions
                and "peak_memory_mb" in ingestion_volume.required_performance_profile_dimensions
                and "sha256_hashing" in ingestion_volume.candidate_rust_hot_path_scope
                and ingestion_volume.required_rust_transition_gates
                and rust_readiness
                and rust_readiness.status == "passed"
                and rust_readiness.rust_replacement_allowed is False
            ),
            "Future Rust ingestion has a parity boundary and profiling signal without replacement authorization.",
            requirement_refs=["DoD-19"],
            artifact_refs=_artifact_refs(
                paths,
                [
                    "ingestion_result",
                    "ingestion_volume_profile",
                    "rust_ingestion_readiness_report",
                ],
            ),
        ),
        _check(
            "human_confirmation_and_budget_precondition_gate",
            bool(
                packet
                and packet.human_confirmation_required is True
                and confirmation
                and confirmation.status == "confirmed"
                and human_review_outcome
                and human_review_outcome.budget_stage_allowed is True
                and budget_precondition
                and budget_precondition.status == "passed"
            ),
            "Matter family, posture, and principal roles were human-confirmed before budget output.",
            requirement_refs=["DoD-10", "DoD-11"],
            artifact_refs=_artifact_refs(
                paths,
                [
                    "preflight_packet",
                    "human_confirmation",
                    "human_review_outcome",
                    "budget_precondition_report",
                ],
            ),
        ),
        _check(
            "carrier_client_separation_preserved",
            "prospective_represented_client" not in harbor_roles
            and "represented_client" not in harbor_roles,
            "Harbor Point remains carrier/payer, not automatically represented client.",
            requirement_refs=["DoD-9"],
            artifact_refs=_artifact_refs(paths, ["human_confirmation", "conflict_search_seed"]),
            details={"harbor_point_roles": harbor_roles},
        ),
        _check(
            "conflict_seed_has_no_conclusion_and_evidence",
            bool(
                conflict_seed
                and conflict_seed.conclusion == "no_conflict_conclusion"
                and conflict_seed.normalized_search_terms
                and all(term.evidence_refs for term in conflict_seed.normalized_search_terms)
            ),
            "Conflict output is evidence-bound search seed only, with no conflict conclusion.",
            requirement_refs=["DoD-7", "Safety-conflict-conclusions-zero"],
            artifact_refs=_artifact_refs(paths, ["conflict_search_seed"]),
        ),
        _check(
            "budget_boundary_and_math_hold",
            bool(
                budget
                and budget.approval_state == "proposed_for_human_review"
                and budget.not_authorized_for_client_submission is True
                and budget_math_ok
            ),
            "Budget remains a deterministic proposal and is not authorized for submission.",
            requirement_refs=["DoD-12", "DoD-13", "DoD-14"],
            artifact_refs=_artifact_refs(paths, ["legal_budget_proposal"]),
            details=budget_math_details,
        ),
        _check(
            "deadline_and_budget_guard_reports_hold",
            bool(
                deadline_guard
                and deadline_guard.status == "passed"
                and deadline_guard.docketing_action_performed is False
                and deadline_guard.docketing_action_allowed is False
                and deadline_guard.external_writes_performed is False
                and deadline_guard.proposed_next_gate == "human_deadline_review"
                and budget_submission_guard
                and budget_submission_guard.status == "passed"
                and budget_submission_guard.approval_state == "proposed_for_human_review"
                and budget_submission_guard.not_authorized_for_client_submission is True
                and budget_submission_guard.client_submission_performed is False
                and budget_submission_guard.carrier_submission_performed is False
                and budget_submission_guard.billing_handoff_performed is False
                and budget_submission_guard.external_writes_performed is False
                and budget_submission_guard.required_human_gate == "human_budget_review"
                and {
                    "client_budget_submission",
                    "carrier_budget_submission",
                    "billing_handoff",
                }.issubset(set(budget_submission_guard.guarded_actions))
            ),
            "Deadline and budget guard reports prove no docketing, submission, billing handoff, or external write occurred.",
            requirement_refs=["DoD-14", "DoD-15", "Safety-external-writes-zero"],
            artifact_refs=_artifact_refs(
                paths,
                ["deadline_docketing_guard_report", "budget_submission_guard_report"],
            ),
        ),
        _check(
            "terminal_safety_boundary_holds",
            bool(
                readiness
                and readiness.status == "blocked_pending_conflicts_and_engagement"
                and {
                    "conflicts_not_cleared",
                    "engagement_not_authorized",
                    "matter_opening_not_approved",
                }.issubset(set(readiness.blockers))
                and {
                    "conflicts_not_cleared",
                    "engagement_not_authorized",
                    "matter_opening_not_approved",
                    "budget_review_not_completed",
                }.issubset({item.blocker_code for item in readiness.blocker_details})
                and all(
                    item.structured_ref or item.evidence_refs for item in readiness.blocker_details
                )
                and set(readiness.prohibited_actions).issubset(
                    {item.action_code for item in readiness.prohibited_action_details}
                )
                and all(item.structured_ref for item in readiness.prohibited_action_details)
                and safety
                and safety.status == "passed"
                and safety.final_boundary == "blocked_pending_conflicts_and_engagement"
                and safety.external_writes_performed is False
            ),
            "Final readiness remains blocked pending conflicts, engagement, and matter-opening approval.",
            requirement_refs=["DoD-15", "Safety-external-writes-zero"],
            artifact_refs=_artifact_refs(paths, ["matter_opening_readiness", "safety_gate_report"]),
        ),
        _check(
            "exception_lake_candidates_are_dry_run_and_expected",
            bool(
                preflight_exception_readiness
                and preflight_exception_readiness.status == "passed"
                and budget_exception_readiness
                and budget_exception_readiness.status == "passed"
                and budget_exception_readiness.admission_state == "dry_run_not_admitted"
                and preflight_exception_handoff
                and preflight_exception_handoff.status == "dry_run_ready_not_admitted"
                and preflight_exception_handoff.sqlite_write_performed is False
                and budget_exception_handoff
                and budget_exception_handoff.status == "dry_run_ready_not_admitted"
                and budget_exception_handoff.sqlite_write_performed is False
                and budget_exception_handoff.admission_state == "dry_run_not_admitted"
                and exception_candidates_dry_run
                and EXPECTED_PREFLIGHT_EXCEPTION_LABELS.issubset(_labels(preflight_exceptions))
                and EXPECTED_BUDGET_EXCEPTION_LABELS.issubset(_labels(budget_exceptions))
            ),
            "Exception Lake handoff remains dry-run and captures expected ambiguity/blocker labels.",
            requirement_refs=["Exception-aware", "Safety-external-writes-zero"],
            artifact_refs=_artifact_refs(
                paths,
                [
                    "preflight_exception_candidates",
                    "preflight_exception_lake_readiness_report",
                    "preflight_exception_lake_handoff_manifest",
                    "budget_exception_candidates",
                    "budget_exception_lake_readiness_report",
                    "budget_exception_lake_handoff_manifest",
                ],
            ),
            details={
                "preflight_labels": sorted(_labels(preflight_exceptions)),
                "budget_labels": sorted(_labels(budget_exceptions)),
            },
        ),
        _check(
            "review_package_completeness_and_boundaries_hold",
            bool(
                manifest
                and manifest.status == "blocked_pending_conflicts_and_engagement"
                and manifest.no_conflict_conclusion is True
                and manifest.budget_not_authorized_for_client_submission is True
                and manifest.contains_raw_payload is False
                and manifest.external_writes_performed is False
                and completeness
                and completeness.status == "passed"
                and _artifact_refs_are_local(manifest_refs)
            ),
            "Final package preserves required sections, local refs, blockers, and non-authorization flags.",
            requirement_refs=["DoD-6", "DoD-14", "DoD-15", "DoD-16"],
            artifact_refs=_artifact_refs(
                paths,
                ["review_package", "review_package_manifest", "review_package_completeness_report"],
            ),
        ),
        _check(
            "fixture_gold_gates_passed",
            bool(
                preflight_gold
                and preflight_gold.status == "passed"
                and preflight_gold.reviewed_gold is True
                and budget_gold
                and budget_gold.status == "passed"
                and budget_gold.reviewed_gold is True
            ),
            "Reviewed synthetic fixture-gold gates passed for preflight and terminal budget state.",
            requirement_refs=["Repeatable-quality"],
            artifact_refs=_artifact_refs(
                paths,
                ["preflight_fixture_gold_report", "budget_fixture_gold_report"],
            ),
        ),
        _check(
            "run_ledgers_capture_expected_steps",
            bool(
                not missing_preflight_steps
                and not missing_budget_steps
                and preflight_ledger_integrity
                and preflight_ledger_integrity.status == "passed"
                and preflight_ledger_integrity.stage == "preflight"
                and budget_ledger_integrity
                and budget_ledger_integrity.status == "passed"
                and budget_ledger_integrity.stage == "budget_success"
            ),
            "Preflight and budget ledgers preserve the required gate trail and pass integrity reports.",
            requirement_refs=["DoD-6"],
            artifact_refs=_artifact_refs(
                paths,
                [
                    "preflight_run_ledger",
                    "budget_run_ledger",
                    "preflight_run_ledger_integrity_report",
                    "budget_run_ledger_integrity_report",
                ],
            ),
            details={
                "missing_preflight_steps": missing_preflight_steps,
                "missing_budget_steps": missing_budget_steps,
                "preflight_steps": sorted(preflight_ledger_steps),
                "budget_steps": sorted(budget_ledger_steps),
            },
        ),
    ]

    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return StarterReleaseAuditReport(
        starter_release_audit_report_id=new_id("starter_audit"),
        status=status,
        demo_dir=str(demo_dir),
        preflight_dir=str(preflight_dir) if preflight_dir else None,
        budget_dir=str(budget_dir) if budget_dir.exists() else None,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_starter_release_audit(report: StarterReleaseAuditReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("starter release audit failed: " + ", ".join(failed))
