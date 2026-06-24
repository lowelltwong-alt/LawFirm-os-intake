from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceItem(StrictModel):
    source_id: str
    source_type: Literal[
        "email",
        "letter",
        "attachment_text",
        "correspondence_dump",
        "party_list",
        "public_docket_stub",
    ]
    filename: str | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceBundle(StrictModel):
    schema_version: str = "0.1"
    bundle_id: str
    data_origin: Literal["synthetic", "public_reference", "production"]
    contains_real_client_data: bool = False
    contains_real_matter_data: bool = False
    contains_privileged_data: bool = False
    sources: list[SourceItem]
    fixture_hints: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sources_required(self) -> "SourceBundle":
        if not self.sources:
            raise ValueError("at least one source is required")
        return self


class Segment(StrictModel):
    segment_id: str
    source_id: str
    parent_segment_id: str | None = None
    segment_type: str
    sequence: int
    start_offset: int
    end_offset: int
    sha256: str
    text: str
    structural_path: str | None = None
    message_index: int | None = None
    attachment_ref: str | None = None
    source_instruction_risk: bool = False


class SourceInventoryItem(StrictModel):
    source_id: str
    source_type: str
    filename: str | None = None
    read_state: Literal["read", "unread", "missing", "unreadable"] = "read"
    availability_state: Literal["available", "missing", "duplicate", "unreadable"] = "available"
    character_count: int
    source_sha256: str
    duplicate_of_source_id: str | None = None
    attachment_refs: list[str] = Field(default_factory=list)
    metadata_keys: list[str] = Field(default_factory=list)


class EvidenceRef(StrictModel):
    source_id: str
    segment_id: str
    start_offset: int
    end_offset: int
    sha256: str


class IngestionResult(StrictModel):
    schema_version: str = "0.1"
    ingestion_result_id: str
    bundle_id: str
    adapter_kind: Literal["python_reference_ingestion_adapter"] = (
        "python_reference_ingestion_adapter"
    )
    parity_contract: Literal["rust_ready_ingestion_v0_1"] = "rust_ready_ingestion_v0_1"
    rust_replacement_allowed: Literal[False] = False
    source_inventory: list[SourceInventoryItem]
    source_coverage_summary: dict[str, Any] = Field(default_factory=dict)
    segments: list[Segment]
    segment_evidence_refs: list[EvidenceRef]
    generated_at: str


class RustIngestionReadinessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RustIngestionReadinessReport(StrictModel):
    schema_version: str = "0.1"
    rust_ingestion_readiness_report_id: str
    run_id: str
    ingestion_result_id: str
    bundle_id: str
    status: Literal["passed", "failed"]
    current_adapter_kind: str
    parity_contract: Literal["rust_ready_ingestion_v0_1"]
    rust_replacement_allowed: Literal[False] = False
    eligible_hot_path_scope: list[str]
    forbidden_rust_scope: list[str]
    required_parity_dimensions: list[str]
    checks: list[RustIngestionReadinessCheck]
    generated_at: str


class RoleCandidate(StrictModel):
    role: str
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class PartyCandidate(StrictModel):
    party_candidate_id: str
    name: str
    normalized_name: str
    aliases: list[str] = Field(default_factory=list)
    role_candidates: list[RoleCandidate]
    evidence_refs: list[EvidenceRef]
    status: Literal["candidate"] = "candidate"


class ScoredCandidate(StrictModel):
    candidate_id: str
    label: str
    confidence: float = Field(ge=0, le=1)
    observed_evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    context_signal_refs: list[str] = Field(default_factory=list)
    calibration_label: Literal["observed", "context_influenced", "unknown_option"] = "observed"
    support_summary: str | None = None
    status: Literal["candidate"] = "candidate"


class DeadlineCandidate(StrictModel):
    deadline_candidate_id: str
    expression: str
    normalized_date: str | None = None
    deadline_type_candidate: str
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[EvidenceRef]
    requires_human_verification: bool = True


class CriticFinding(StrictModel):
    code: str
    severity: Literal["info", "warning", "blocker"]
    message: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class MissingInformationCandidate(StrictModel):
    field_name: str
    reason: str
    evidence_refs: list[EvidenceRef]
    status: Literal["candidate"] = "candidate"


class EscalationDecision(StrictModel):
    required: bool
    triggers: list[str] = Field(default_factory=list)
    recommended_target: Literal[
        "ordinary_human_intake_review",
        "frontier_adjudicator_then_human",
        "human_only",
    ]
    self_reported_confidence_used_as_sole_trigger: bool = False


class EffectiveContext(StrictModel):
    context_id: str
    profile_id: str
    profile_version: str
    profile_sha256: str
    applied_layers: list[str]
    active_practices: list[str]
    default_side: str
    typical_inbound_sources: dict[str, float]
    matter_family_priors: dict[str, float]
    required_intake_fields: list[str]
    budget_template_ids: list[str]
    context_precedence: list[str]


class ContractStateDependency(StrictModel):
    repo: str
    remote: str | None = None
    branch: str | None = None
    ref_type: str | None = None
    sha: str | None = None
    authority_plane: str | None = None
    local_folder: str | None = None
    topology_sha: str | None = None
    topology_authority_plane: str | None = None
    topology_matches_lock: bool = False
    status: Literal["verified", "invalid"]


class ContractStateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)


class ContractStateReport(StrictModel):
    schema_version: str = "0.1"
    contract_state_report_id: str
    run_id: str
    status: Literal["passed", "failed"]
    lock_status: str | None = None
    reviewed_lock_required: bool = True
    lockfile_ref: str
    topology_lock_ref: str
    dependencies: list[ContractStateDependency]
    checks: list[ContractStateCheck]
    errors: list[str] = Field(default_factory=list)
    generated_at: str


class IntakePreflightPacket(StrictModel):
    schema_version: str = "0.1"
    packet_id: str
    run_id: str
    bundle_id: str
    status: Literal["human_intake_review_required", "blocked"]
    data_origin: str
    source_inventory: list[SourceInventoryItem]
    source_coverage_summary: dict[str, Any] = Field(default_factory=dict)
    segments: list[Segment]
    ingestion_result_ref: str | None = None
    rust_ingestion_readiness_report_ref: str | None = None
    effective_context: EffectiveContext
    inbound_event_candidates: list[ScoredCandidate]
    matter_family_candidates: list[ScoredCandidate]
    representation_posture_candidates: list[ScoredCandidate]
    party_candidates: list[PartyCandidate]
    deadline_candidates: list[DeadlineCandidate]
    missing_information: list[str]
    missing_information_candidates: list[MissingInformationCandidate] = Field(default_factory=list)
    critic_findings: list[CriticFinding]
    escalation: EscalationDecision
    human_confirmation_required: bool = True
    prohibited_next_steps: list[str]
    evidence_graph_ref: str
    run_ledger_ref: str
    contract_state_report_ref: str
    exception_candidates_ref: str | None = None
    exception_lake_readiness_report_ref: str | None = None
    intake_review_form_ref: str | None = None


class ConfirmedParty(StrictModel):
    name: str
    confirmed_role: str
    aliases: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class HumanConfirmation(StrictModel):
    schema_version: str = "0.1"
    confirmation_id: str
    preflight_packet_id: str
    status: Literal[
        "confirmed",
        "needs_more_information",
        "unknown",
        "human_only",
        "declined",
        "declined_or_referred",
    ]
    supersedes_confirmation_id: str | None = None
    confirmed_inbound_event: str | None = None
    confirmed_matter_family: str | None = None
    confirmed_representation_posture: str | None = None
    confirmed_parties: list[ConfirmedParty] = Field(default_factory=list)
    confirmed_jurisdiction: str | None = None
    confirmed_deadlines: list[str] = Field(default_factory=list)
    reviewer_id: str
    reviewed_at: str
    notes: str | None = None
    decision_evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class HumanReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    review_outcome_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_preflight_packet_id: str
    confirmation_id: str
    status: Literal[
        "confirmed",
        "needs_more_information",
        "unknown",
        "human_only",
        "declined",
        "declined_or_referred",
    ]
    reviewer_id: str
    reviewed_at: str
    supersedes_confirmation_id: str | None = None
    mutation_policy: Literal["append_or_supersede_only"] = "append_or_supersede_only"
    matches_preflight_packet: bool
    budget_stage_allowed: bool
    required_next_gate: Literal[
        "budget_precondition_gate",
        "collect_missing_information",
        "human_classification_correction",
        "human_only_handling",
        "declined_or_referred_handoff",
    ]
    decision_evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confirmed_party_evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confirmed_party_count: int
    notes: str | None = None


class ConflictSeedPacket(StrictModel):
    schema_version: str = "0.1"
    conflict_seed_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["seed_ready_for_conflicts_team"]
    prospective_represented_clients: list[str]
    instructing_sources: list[str]
    payers: list[str]
    adverse_parties: list[str]
    insureds: list[str] = Field(default_factory=list)
    opposing_counsel: list[str]
    other_search_terms: list[str]
    unresolved_roles: list[str]
    normalized_search_terms: list["ConflictSearchTerm"] = Field(default_factory=list)
    conclusion: Literal["no_conflict_conclusion"] = "no_conflict_conclusion"


class ConflictSearchTerm(StrictModel):
    term: str
    normalized_term: str
    group: Literal[
        "prospective_represented_client",
        "instructing_source",
        "payer",
        "insured",
        "adverse_party",
        "opposing_counsel",
        "alias",
        "unresolved_role",
    ]
    source_role: str | None = None
    evidence_refs: list[EvidenceRef]


class BudgetLine(StrictModel):
    phase_id: str
    phase_name: str
    task_id: str
    task_name: str
    staffing_role: str
    estimated_hours: float = Field(ge=0)
    estimated_hours_min: float | None = Field(default=None, ge=0)
    estimated_hours_max: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    rate_source: Literal["synthetic_profile", "authorized_profile", "absent"] = "absent"
    rate_is_synthetic: bool = True
    estimated_fees: float | None = Field(default=None, ge=0)
    estimated_expenses: float = Field(default=0, ge=0)
    calculation_formula: str | None = None
    external_code_candidate: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class BudgetSupportItem(StrictModel):
    item_type: Literal["assumption", "exclusion", "unknown"]
    text: str
    source_kind: Literal[
        "observed_evidence",
        "human_confirmation",
        "synthetic_practice_profile",
        "workflow_policy",
        "missing_template",
    ]
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_ref: str | None = None
    requires_human_review: bool = True

    @model_validator(mode="after")
    def evidence_or_structured_ref_required(self) -> "BudgetSupportItem":
        if not self.evidence_refs and not self.structured_ref:
            raise ValueError("budget support item requires evidence_refs or structured_ref")
        return self


class BudgetProposal(StrictModel):
    schema_version: str = "0.1"
    budget_proposal_id: str
    preflight_packet_id: str
    confirmation_id: str
    practice_profile_id: str
    matter_family: str
    representation_posture: str
    pricing_status: Literal["priced", "hours_only", "insufficient_information"]
    currency: str = "USD"
    lines: list[BudgetLine]
    subtotal_fees: float | None = None
    subtotal_expenses: float = 0
    contingency_percent: float = 0
    contingency_amount: float | None = None
    total_proposed_budget: float | None = None
    scenario_name: str = "baseline"
    calculation_report: "BudgetCalculationReport | None" = None
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    budget_support_items: list[BudgetSupportItem] = Field(default_factory=list)
    approval_state: Literal["proposed_for_human_review"] = "proposed_for_human_review"
    not_authorized_for_client_submission: bool = True


class BudgetCalculationReport(StrictModel):
    calculation_report_id: str
    mode: Literal["priced", "hours_only", "insufficient_information"]
    line_count: int
    total_hours: float
    priced_line_count: int
    unpriced_line_count: int
    subtotal_fees: float | None = None
    subtotal_expenses: float
    contingency_percent: float
    contingency_amount: float | None = None
    total_proposed_budget: float | None = None
    rate_sources: list[str] = Field(default_factory=list)
    deterministic: bool = True


class MatterOpeningReadiness(StrictModel):
    readiness_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["blocked_pending_conflicts_and_engagement"]
    satisfied: list[str]
    blockers: list[str]
    prohibited_actions: list[str]


class BudgetPreconditionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)


class BudgetPreconditionReport(StrictModel):
    schema_version: str = "0.1"
    budget_precondition_report_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["passed", "failed"]
    checks: list[BudgetPreconditionCheck]
    blocked_state: str | None = None
    input_refs: list[str]
    human_review_outcome_ref: str | None = None
    prohibited_outputs: list[str]
    external_writes_performed: Literal[False] = False
    generated_at: str


class EvidenceGraphNode(StrictModel):
    node_id: str
    node_type: str
    status: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(StrictModel):
    edge_id: str
    source_node_id: str
    relationship: str
    target_node_id: str
    status: str = "candidate"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class EvidenceGraph(StrictModel):
    schema_version: str = "0.1"
    graph_id: str
    nodes: list[EvidenceGraphNode]
    edges: list[EvidenceGraphEdge]


class RunEvent(StrictModel):
    run_id: str
    step_index: int
    step_name: str
    status: Literal["started", "completed", "blocked", "failed"]
    timestamp: str
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class ExceptionLakeCandidate(StrictModel):
    schema_version: str = "0.1"
    candidate_id: str
    run_id: str
    preflight_packet_id: str
    local_event_label: str
    canonical_lake_class: Literal[
        "retrieval_miss",
        "workflow_escalation",
        "authority_conflict_override",
    ]
    status: Literal["dry_run_candidate"] = "dry_run_candidate"
    reason: str
    source_inventory_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    blocked_state: str | None = None
    raw_payload_included: bool = False
    canonical_promotion_required: bool = True
    target_runtime_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )


class ExceptionLakeReadinessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)


class ExceptionLakeReadinessReport(StrictModel):
    schema_version: str = "0.1"
    exception_lake_readiness_report_id: str
    run_id: str
    preflight_packet_id: str
    status: Literal["passed", "failed"]
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    target_runtime_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    candidate_count: int
    candidate_file_refs: list[str]
    checks: list[ExceptionLakeReadinessCheck]
    generated_at: str


class ReviewPackageManifest(StrictModel):
    schema_version: str = "0.1"
    review_package_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_id: str
    conflict_seed_id: str
    budget_proposal_id: str
    readiness_id: str
    status: Literal["blocked_pending_conflicts_and_engagement"]
    human_readable_review_ref: str
    artifact_refs: dict[str, str]
    required_human_gates: list[str]
    final_blockers: list[str]
    prohibited_actions: list[str]
    safety_gate_report_ref: str
    contract_state_report_ref: str | None = None
    budget_precondition_report_ref: str | None = None
    evidence_graph_ref: str
    run_ledger_refs: list[str]
    exception_candidate_refs: list[str]
    exception_lake_readiness_report_ref: str | None = None
    review_package_completeness_report_ref: str | None = None
    no_conflict_conclusion: Literal[True] = True
    budget_not_authorized_for_client_submission: Literal[True] = True
    contains_raw_payload: Literal[False] = False
    external_writes_performed: Literal[False] = False


class ReviewPackageCompletenessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ReviewPackageCompletenessReport(StrictModel):
    schema_version: str = "0.1"
    review_package_completeness_report_id: str
    run_id: str
    preflight_packet_id: str
    review_package_id: str
    status: Literal["passed", "failed"]
    human_readable_review_ref: str
    review_package_manifest_ref: str
    required_sections: list[str]
    required_artifact_keys: list[str]
    checks: list[ReviewPackageCompletenessCheck]
    generated_at: str


class SafetyGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)


class SafetyGateReport(StrictModel):
    schema_version: str = "0.1"
    safety_gate_report_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["passed", "failed"]
    checks: list[SafetyGateCheck]
    prohibited_actions_verified: list[str]
    final_boundary: Literal["blocked_pending_conflicts_and_engagement"]
    external_writes_performed: Literal[False] = False
    generated_at: str
