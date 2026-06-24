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


class RustTransitionPolicy(StrictModel):
    schema_version: str = "0.1"
    policy_id: str
    status: Literal["local_candidate"]
    authority: str
    profile_thresholds: dict[str, int]
    required_rust_transition_gates: list[str]
    candidate_rust_hot_path_scope: list[str]
    eligible_hot_path_scope: list[str]
    forbidden_rust_scope: list[str]
    required_parity_dimensions: list[str]
    required_performance_profile_dimensions: list[str]
    rust_replacement_allowed: Literal[False] = False
    no_rust_runtime_added: Literal[True] = True
    external_writes_performed: Literal[False] = False


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
    rust_transition_policy_ref: str
    rust_replacement_allowed: Literal[False] = False
    eligible_hot_path_scope: list[str]
    forbidden_rust_scope: list[str]
    required_parity_dimensions: list[str]
    checks: list[RustIngestionReadinessCheck]
    generated_at: str


class IngestionVolumeProfile(StrictModel):
    schema_version: str = "0.1"
    ingestion_volume_profile_id: str
    run_id: str
    ingestion_result_id: str
    bundle_id: str
    source_count: int = Field(ge=0)
    total_source_characters: int = Field(ge=0)
    max_source_characters: int = Field(ge=0)
    segment_count: int = Field(ge=0)
    total_segment_characters: int = Field(ge=0)
    max_segment_characters: int = Field(ge=0)
    source_type_counts: dict[str, int]
    source_state_counts: dict[str, int]
    segment_type_counts: dict[str, int]
    rust_transition_policy_ref: str
    profile_thresholds: dict[str, int]
    scale_signals: list[str] = Field(default_factory=list)
    compute_pressure_signals: list[str] = Field(default_factory=list)
    required_performance_profile_dimensions: list[str] = Field(default_factory=list)
    candidate_rust_hot_path_scope: list[str] = Field(default_factory=list)
    observed_scale_band: Literal["starter_fixture", "profile_candidate"]
    performance_profile_required_before_rust: bool
    rust_replacement_allowed: Literal[False] = False
    rust_adapter_proposal_state: Literal[
        "not_warranted",
        "profiling_required_before_adapter_proposal",
    ]
    required_rust_transition_gates: list[str]
    decision: Literal["keep_python_reference", "profile_before_rust_adapter"]
    rationale: list[str]
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
    source_evidence_status: Literal["observed_support", "source_anchor_only", "unknown_option"] = (
        "observed_support"
    )
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


class DeadlineDocketingGuardItem(StrictModel):
    deadline_candidate_id: str
    expression: str
    normalized_date: str | None = None
    deadline_type_candidate: str
    source_evidence_status: Literal["source_bound_candidate"] = "source_bound_candidate"
    requires_human_verification: Literal[True] = True
    evidence_refs: list[EvidenceRef]
    proposed_next_gate: Literal["human_deadline_review"] = "human_deadline_review"
    structured_refs: list[str] = Field(default_factory=list)


class DeadlineDocketingGuardCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)


class DeadlineDocketingGuardReport(StrictModel):
    schema_version: str = "0.1"
    deadline_docketing_guard_report_id: str
    run_id: str
    preflight_packet_id: str
    status: Literal["passed", "failed"]
    candidate_count: int = Field(ge=0)
    review_required_count: int = Field(ge=0)
    docketing_action_performed: Literal[False] = False
    docketing_action_allowed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    proposed_next_gate: Literal["human_deadline_review"] = "human_deadline_review"
    candidate_items: list[DeadlineDocketingGuardItem]
    checks: list[DeadlineDocketingGuardCheck]
    generated_at: str


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


class EvidenceCompletenessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceCompletenessReport(StrictModel):
    schema_version: str = "0.1"
    evidence_completeness_report_id: str
    run_id: str
    preflight_packet_id: str
    status: Literal["passed", "failed"]
    strict_evidence_required: bool
    checked_surfaces: list[str]
    surface_counts: dict[str, int]
    evidence_ref_count: int = Field(ge=0)
    source_evidence_status_counts: dict[str, int] = Field(default_factory=dict)
    human_confirmation_required: bool
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    checks: list[EvidenceCompletenessCheck]
    generated_at: str


class ContextBoundaryCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)
    context_signal_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ContextBoundaryReport(StrictModel):
    schema_version: str = "0.1"
    context_boundary_report_id: str
    run_id: str
    preflight_packet_id: str
    status: Literal["passed", "failed"]
    effective_context_id: str
    profile_id: str
    profile_version: str
    profile_sha256: str
    observed_source_evidence_precedence: Literal[True] = True
    practice_context_is_observed_evidence: Literal[False] = False
    human_confirmation_required: bool
    checked_candidate_count: int = Field(ge=0)
    context_signal_candidate_count: int = Field(ge=0)
    context_only_candidate_count: int = Field(ge=0)
    observed_with_context_candidate_count: int = Field(ge=0)
    unknown_option_count: int = Field(ge=0)
    checks: list[ContextBoundaryCheck]
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


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


class DataScopeGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    policy_refs: list[str] = Field(default_factory=list)


class DataScopeGateReport(StrictModel):
    schema_version: str = "0.1"
    data_scope_gate_report_id: str
    run_id: str
    bundle_id: str
    status: Literal["passed", "blocked"]
    blocked_state: str | None = None
    runtime_mode: Literal["synthetic_only"] = "synthetic_only"
    data_origin: str
    allowed_data_origins: list[Literal["synthetic"]] = Field(default_factory=lambda: ["synthetic"])
    contains_real_client_data: bool
    contains_real_matter_data: bool
    contains_privileged_data: bool
    source_count: int = Field(ge=0)
    raw_payload_written: Literal[False] = False
    public_data_direct_ingestion_allowed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    policy_refs: list[str]
    checks: list[DataScopeGateCheck]
    generated_at: str


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


class ModelAdapterGuardCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ModelAdapterReport(StrictModel):
    schema_version: str = "0.1"
    model_adapter_report_id: str
    run_id: str
    adapter_name: Literal["deterministic", "structured-model"]
    adapter_mode: Literal["deterministic", "dry_run"]
    status: Literal["passed", "failed"]
    provider_call_performed: Literal[False] = False
    model_calls_allowed: bool
    external_tools_allowed: bool
    network_access_allowed: Literal[False] = False
    external_writes_allowed: Literal[False] = False
    raw_payload_externalized: Literal[False] = False
    approved_for_real_data: Literal[False] = False
    typed_json_only: Literal[True] = True
    prompt_registry_ref: str
    prompt_hashes: dict[str, str]
    structured_output_schema_refs: list[str]
    model_budget: dict[str, int]
    allowed_tool_refs: list[str] = Field(default_factory=list)
    tool_denylist: list[str]
    required_human_gates: list[str]
    independent_critic_required: Literal[True] = True
    human_confirmation_required: Literal[True] = True
    deterministic_baseline_required: Literal[True] = True
    deterministic_workers_authoritative: Literal[True] = True
    baseline_comparison_state: Literal[
        "deterministic_workers_are_current_baseline",
        "dry_run_no_provider_output",
        "compared_to_deterministic_baseline",
        "failed_missing_synthetic_gold",
        "failed_synthetic_gold",
    ]
    comparison_status: Literal["not_run", "passed", "failed"] = "not_run"
    comparison_basis: list[str] = Field(default_factory=list)
    deterministic_baseline_hash: str | None = None
    structured_candidate_hash: str | None = None
    typed_json_validation_status: Literal["not_run", "passed", "failed"] = "not_run"
    synthetic_gold_required: bool = False
    synthetic_gold_compared: bool = False
    fixture_gold_report_ref: str | None = None
    fixture_gold_status: Literal["not_requested", "passed", "failed"] = "not_requested"
    comparison_summary: dict[str, Any] = Field(default_factory=dict)
    checks: list[ModelAdapterGuardCheck]
    generated_at: str


class FixtureGoldSourceExpectation(StrictModel):
    source_id: str
    read_state: str | None = None
    availability_state: str | None = None
    duplicate_of_source_id: str | None = None


class FixtureGoldSpec(StrictModel):
    schema_version: str = "0.1"
    gold_id: str
    fixture_id: str
    applies_to: Literal["preflight", "demo", "preflight_and_budget"]
    reviewed: bool
    reviewer_id: str
    reviewed_at: str
    data_scope: Literal["synthetic_only"] = "synthetic_only"
    expected_bundle_id: str | None = None
    expected_preflight_status: str | None = None
    expected_source_coverage: dict[str, Any] = Field(default_factory=dict)
    expected_source_states: list[FixtureGoldSourceExpectation] = Field(default_factory=list)
    expected_top_three_matter_families: list[str] = Field(default_factory=list)
    expected_top_inbound_event: str | None = None
    expected_top_representation_posture: str | None = None
    expected_party_role_candidates: dict[str, list[str]] = Field(default_factory=dict)
    prohibited_party_role_candidates: dict[str, list[str]] = Field(default_factory=dict)
    expected_deadline_expressions: list[str] = Field(default_factory=list)
    expected_missing_information: list[str] = Field(default_factory=list)
    expected_critic_finding_codes: list[str] = Field(default_factory=list)
    expected_preflight_exception_labels: list[str] = Field(default_factory=list)
    expected_prohibited_next_steps: list[str] = Field(default_factory=list)
    require_source_bound_evidence: bool = True
    expected_confirmation_status: str | None = None
    expected_conflict_conclusion: str | None = None
    expected_conflict_term_groups: list[str] = Field(default_factory=list)
    expected_budget_pricing_status: str | None = None
    expected_budget_approval_state: str | None = None
    expected_budget_not_authorized_for_client_submission: bool | None = None
    expected_budget_exception_labels: list[str] = Field(default_factory=list)
    expected_budget_precondition_status: str | None = None
    expected_safety_status: str | None = None
    expected_final_boundary: str | None = None
    expected_readiness_blockers: list[str] = Field(default_factory=list)
    expected_no_external_writes: bool | None = True


class FixtureGoldCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "skipped"]
    message: str
    expected: Any = None
    actual: Any = None


class FixtureGoldReport(StrictModel):
    schema_version: str = "0.1"
    fixture_gold_report_id: str
    run_id: str
    preflight_packet_id: str
    stage: Literal["preflight", "demo"]
    gold_id: str
    gold_ref: str
    status: Literal["passed", "failed"]
    reviewed_gold: bool
    data_scope: Literal["synthetic_only"] = "synthetic_only"
    non_authoritative: Literal[True] = True
    evaluated_artifact_refs: dict[str, str] = Field(default_factory=dict)
    checks: list[FixtureGoldCheck]
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
    ingestion_volume_profile_ref: str | None = None
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
    data_scope_gate_report_ref: str | None = None
    model_adapter_report_ref: str | None = None
    fixture_gold_report_ref: str | None = None
    exception_candidates_ref: str | None = None
    exception_lake_readiness_report_ref: str | None = None
    exception_lake_handoff_manifest_ref: str | None = None
    run_ledger_integrity_report_ref: str | None = None
    deadline_docketing_guard_report_ref: str | None = None
    evidence_completeness_report_ref: str | None = None
    context_boundary_report_ref: str | None = None
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


class HumanGateStatus(StrictModel):
    gate_id: Literal[
        "human_intake_confirmation",
        "human_conflicts_clearance",
        "human_engagement_authorization",
        "human_budget_review",
        "human_matter_opening_authorization",
    ]
    label: str
    required: Literal[True] = True
    status: Literal["completed", "pending"]
    authority_owner: str
    completed_by_human: bool
    artifact_refs: list[str] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    notes: str | None = None


class HumanGateStatusReport(StrictModel):
    schema_version: str = "0.1"
    human_gate_status_report_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["pending_human_gates", "all_human_gates_complete"]
    required_gate_ids: list[str]
    completed_gate_count: int = Field(ge=0)
    pending_gate_count: int = Field(ge=0)
    gates: list[HumanGateStatus]
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


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
    expense_code: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class BudgetSupportItem(StrictModel):
    item_type: Literal["assumption", "exclusion", "unknown"]
    text: str
    source_kind: Literal[
        "observed_evidence",
        "human_confirmation",
        "synthetic_practice_profile",
        "budget_driver_policy",
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


class BudgetScenario(StrictModel):
    scenario_id: str
    scenario_name: str
    description: str
    resolution_phase: str
    included_phase_ids: list[str]
    included_external_codes: list[str] = Field(default_factory=list)
    included_line_count: int = Field(ge=0)
    total_hours: float = Field(ge=0)
    subtotal_fees: float | None = None
    subtotal_expenses: float = Field(ge=0)
    contingency_percent: float = Field(ge=0)
    contingency_amount: float | None = None
    total_proposed_budget: float | None = None
    total_budget_min: float | None = None
    total_budget_max: float | None = None
    pricing_status: Literal["priced", "hours_only", "insufficient_information"]
    proposed_for_human_review: Literal[True] = True
    not_authorized_for_client_submission: Literal[True] = True
    non_authoritative: Literal[True] = True


class BudgetScenarioSet(StrictModel):
    schema_version: str = "0.1"
    scenario_set_id: str
    selected_scenario_id: str = "standard"
    standard_scenario_id: str = "standard"
    scenarios: list[BudgetScenario]
    monotonic_total_order: bool
    total_order_basis: Literal["total_proposed_budget", "total_hours"] = "total_proposed_budget"
    requires_human_budget_review: Literal[True] = True
    not_authorized_for_client_submission: Literal[True] = True
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def scenario_ids_are_unique_and_selected(self) -> "BudgetScenarioSet":
        scenario_ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("budget scenario ids must be unique")
        if self.scenarios and self.selected_scenario_id not in scenario_ids:
            raise ValueError("selected budget scenario must exist in scenario set")
        if self.scenarios and self.standard_scenario_id not in scenario_ids:
            raise ValueError("standard budget scenario must exist in scenario set")
        return self


class BudgetDriverEffect(StrictModel):
    driver_id: str
    driver_value: int | float | str | None = None
    provenance: str
    effect_type: Literal[
        "count_scaling",
        "intensity_multiplier",
        "coverage_boundary",
        "unknown_driver",
    ]
    applied: bool
    phase_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    multiplier: float | None = Field(default=None, ge=0)
    capped: bool = False
    source_refs: list[str] = Field(default_factory=list)
    structured_ref: str | None = None
    note: str
    default_used_as_observed_fact: Literal[False] = False
    requires_human_review: bool = True


class BudgetGuidelineFlag(StrictModel):
    constraint_id: str
    constraint_type: Literal[
        "role_rate_cap",
        "phase_budget_cap",
        "total_budget_cap",
        "staffing_rule",
        "unknown_guidelines",
    ]
    status: Literal["flagged_for_human_review", "not_triggered", "unknown"]
    phase_id: str | None = None
    role: str | None = None
    current_value: float | str | None = None
    threshold_value: float | str | None = None
    provenance: Literal["synthetic_policy", "unknown"] = "synthetic_policy"
    structured_ref: str | None = None
    note: str
    rewrites_budget: Literal[False] = False
    requires_human_review: Literal[True] = True


class BudgetDriverProfileSummary(StrictModel):
    case_driver_profile_id: str
    policy_id: str
    policy_version: str
    driver_count: int = Field(ge=0)
    observed_or_confirmed_driver_ids: list[str] = Field(default_factory=list)
    default_driver_ids: list[str] = Field(default_factory=list)
    unknown_driver_ids: list[str] = Field(default_factory=list)
    profile_defaults_are_observed_facts: Literal[False] = False
    context_priors_are_observed_facts: Literal[False] = False
    requires_human_review: Literal[True] = True
    not_authoritative: Literal[True] = True


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
    scenario_name: str = "standard"
    scenario_set: BudgetScenarioSet | None = None
    calculation_report: "BudgetCalculationReport | None" = None
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    driver_profile_summary: BudgetDriverProfileSummary | None = None
    driver_effects: list[BudgetDriverEffect] = Field(default_factory=list)
    guideline_flags: list[BudgetGuidelineFlag] = Field(default_factory=list)
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


class BudgetActualPhaseComparison(StrictModel):
    phase_id: str
    budgeted_fees: float | None = None
    budgeted_expenses: float = 0
    budgeted_total: float | None = None
    actual_fees: float | None = None
    actual_expenses: float | None = None
    actual_total: float | None = None
    variance_amount: float | None = None
    variance_percent: float | None = None
    status: Literal[
        "actuals_not_available",
        "within_threshold",
        "over_threshold",
        "under_threshold",
    ]
    external_code_candidates: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class BudgetActualComparisonReport(StrictModel):
    schema_version: str = "0.1"
    budget_actual_comparison_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: Literal["actuals_not_available", "passed", "variance_review_required"]
    comparison_scope: Literal["phase"] = "phase"
    phase_comparisons: list[BudgetActualPhaseComparison]
    variance_threshold_percent: float = Field(ge=0)
    total_budgeted: float | None = None
    total_actual: float | None = None
    total_variance_amount: float | None = None
    total_variance_percent: float | None = None
    actuals_source_ref: str | None = None
    actuals_are_synthetic: bool = True
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


class BudgetFormCodeMapping(StrictModel):
    code: str
    kind: Literal["phase", "task"]
    row: int = Field(ge=1)
    label: str
    amount_cell: str
    amount: float = 0


class BudgetFormFormulaCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    cell: str | None = None
    actual_formula: str | None = None
    expected_refs: list[str] = Field(default_factory=list)
    actual_refs: list[str] = Field(default_factory=list)


class BudgetFormMappingReport(StrictModel):
    schema_version: str = "0.1"
    budget_form_mapping_report_id: str
    budget_proposal_id: str
    status: Literal["passed", "failed"]
    template_sha256: str
    sheet_name: str
    task_header_cell: str | None = None
    amount_header_cell: str | None = None
    total_cell: str | None = None
    task_column: int | None = None
    amount_column: int | None = None
    code_mappings: list[BudgetFormCodeMapping] = Field(default_factory=list)
    amounts_by_code: dict[str, float] = Field(default_factory=dict)
    l_code_total: float = 0
    e_code_total: float = 0
    missing_template_codes: list[str] = Field(default_factory=list)
    duplicate_template_codes: list[str] = Field(default_factory=list)
    missing_budget_mappings: list[str] = Field(default_factory=list)
    unmapped_budget_amount_codes: list[str] = Field(default_factory=list)
    formula_checks: list[BudgetFormFormulaCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    not_authorized_for_client_submission: bool = True
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


class BudgetFormTemplateAuditReport(StrictModel):
    schema_version: str = "0.1"
    budget_form_template_audit_report_id: str
    status: Literal["passed", "failed"]
    template_sha256: str
    sheet_name: str
    task_header_cell: str | None = None
    amount_header_cell: str | None = None
    total_cell: str | None = None
    task_column: int | None = None
    amount_column: int | None = None
    code_mappings: list[BudgetFormCodeMapping] = Field(default_factory=list)
    missing_template_codes: list[str] = Field(default_factory=list)
    duplicate_template_codes: list[str] = Field(default_factory=list)
    formula_checks: list[BudgetFormFormulaCheck] = Field(default_factory=list)
    checklist_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


class BudgetSubmissionGuardCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)


class BudgetSubmissionGuardReport(StrictModel):
    schema_version: str = "0.1"
    budget_submission_guard_report_id: str
    run_id: str
    preflight_packet_id: str
    confirmation_id: str
    budget_proposal_id: str
    status: Literal["passed", "failed"]
    approval_state: str
    not_authorized_for_client_submission: bool
    client_submission_performed: Literal[False] = False
    carrier_submission_performed: Literal[False] = False
    billing_handoff_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    required_human_gate: Literal["human_budget_review"] = "human_budget_review"
    guarded_actions: list[
        Literal["client_budget_submission", "carrier_budget_submission", "billing_handoff"]
    ]
    controlled_artifact_refs: list[str]
    structured_refs: list[str]
    checks: list[BudgetSubmissionGuardCheck]
    generated_at: str


class MatterOpeningBlocker(StrictModel):
    blocker_code: str
    label: str
    status: Literal["blocking"] = "blocking"
    blocking_scope: Literal[
        "conflicts",
        "engagement",
        "matter_opening",
        "budget_submission",
    ]
    required_human_gate: str
    authority_owner: str
    support_kind: Literal[
        "structured_workflow_policy",
        "prohibited_transition_policy",
        "budget_submission_boundary",
    ]
    structured_ref: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    reason: str
    prohibits: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_or_structured_ref_required(self) -> "MatterOpeningBlocker":
        if not self.structured_ref and not self.evidence_refs:
            raise ValueError("matter-opening blocker requires structured_ref or evidence_refs")
        return self


class ProhibitedActionGuardrail(StrictModel):
    action_code: str
    transition_blocked: str
    required_human_gate: str
    support_kind: Literal["prohibited_transition_policy", "budget_submission_boundary"]
    structured_ref: str
    reason: str
    linked_blocker_codes: list[str] = Field(default_factory=list)


class MatterOpeningReadiness(StrictModel):
    readiness_id: str
    preflight_packet_id: str
    confirmation_id: str
    status: Literal["blocked_pending_conflicts_and_engagement"]
    satisfied: list[str]
    blockers: list[str]
    blocker_details: list[MatterOpeningBlocker] = Field(default_factory=list)
    prohibited_actions: list[str]
    prohibited_action_details: list[ProhibitedActionGuardrail] = Field(default_factory=list)


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


class RunLedgerIntegrityCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    event_step_names: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RunLedgerIntegrityReport(StrictModel):
    schema_version: str = "0.1"
    run_ledger_integrity_report_id: str
    run_id: str
    stage: Literal["preflight", "budget_success", "budget_precondition_blocked"]
    status: Literal["passed", "failed"]
    run_ledger_ref: str
    event_count: int = Field(ge=0)
    required_steps: list[str]
    observed_steps: list[str]
    terminal_step_name: str
    terminal_status: Literal["started", "completed", "blocked", "failed"]
    local_artifact_refs_only: bool
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    checks: list[RunLedgerIntegrityCheck]
    generated_at: str


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


class ExceptionLakeHandoffCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)


class ExceptionLakeHandoffLabelSummary(StrictModel):
    local_event_label: str
    canonical_lake_class: Literal[
        "retrieval_miss",
        "workflow_escalation",
        "authority_conflict_override",
    ]
    count: int = Field(ge=0)
    candidate_ids: list[str]
    support_modes: list[
        Literal["source_inventory_ref", "source_evidence_ref", "structured_ref", "blocked_state"]
    ]
    source_inventory_ref_count: int = Field(ge=0)
    evidence_ref_count: int = Field(ge=0)
    structured_ref_count: int = Field(ge=0)
    blocked_states: list[str] = Field(default_factory=list)


class ExceptionLakeHandoffManifest(StrictModel):
    schema_version: str = "0.1"
    exception_lake_handoff_manifest_id: str
    run_id: str
    preflight_packet_id: str
    stage: Literal["preflight", "budget_combined", "budget_precondition_blocked"]
    status: Literal["dry_run_ready_not_admitted", "failed"]
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    target_runtime_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    storage_owner: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    mapping_review_required: Literal[True] = True
    canonical_promotion_required: Literal[True] = True
    candidate_count: int = Field(ge=0)
    candidate_file_refs: list[str]
    readiness_report_ref: str
    readiness_status: Literal["passed", "failed"]
    label_summaries: list[ExceptionLakeHandoffLabelSummary]
    checks: list[ExceptionLakeHandoffCheck]
    generated_at: str


class ExceptionLakeMappingRule(StrictModel):
    mapping_id: str
    issue_family: Literal[
        "broken_template_formula",
        "missing_budget_code_mapping",
        "unknown_budget_driver",
        "guideline_or_cap_issue",
        "human_budget_change",
        "budget_actual_cost_variance",
    ]
    local_event_label: str
    canonical_lake_class: Literal[
        "retrieval_miss",
        "workflow_escalation",
        "authority_conflict_override",
    ]
    trigger_summary: str
    support_ref_kinds: list[
        Literal[
            "structured_ref",
            "budget_form_mapping_report",
            "budget_proposal",
            "budget_change_record",
            "budget_actual_comparison_report",
        ]
    ]
    candidate_ids: list[str] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    mapped: bool = True
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    canonical_promotion_required: Literal[True] = True


class ExceptionLakeMappingCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    mapping_ids: list[str] = Field(default_factory=list)


class ExceptionLakeMappingPackage(StrictModel):
    schema_version: str = "0.1"
    exception_lake_mapping_package_id: str
    run_id: str
    preflight_packet_id: str
    stage: Literal["budget"]
    status: Literal["passed", "failed"]
    target_runtime_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    raw_payload_included: Literal[False] = False
    canonical_promotion_required: Literal[True] = True
    mapping_review_required: Literal[True] = True
    rules: list[ExceptionLakeMappingRule]
    checks: list[ExceptionLakeMappingCheck]
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
    human_gate_status_report_ref: str | None = None
    final_blockers: list[str]
    prohibited_actions: list[str]
    safety_gate_report_ref: str
    contract_state_report_ref: str | None = None
    data_scope_gate_report_ref: str | None = None
    budget_precondition_report_ref: str | None = None
    evidence_completeness_report_ref: str | None = None
    context_boundary_report_ref: str | None = None
    evidence_graph_ref: str
    run_ledger_refs: list[str]
    run_ledger_integrity_report_refs: list[str] = Field(default_factory=list)
    exception_candidate_refs: list[str]
    exception_lake_readiness_report_ref: str | None = None
    exception_lake_handoff_manifest_ref: str | None = None
    review_package_completeness_report_ref: str | None = None
    budget_submission_guard_report_ref: str | None = None
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


class StarterReleaseAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    requirement_refs: list[str] = Field(default_factory=list)
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class StarterReleaseAuditReport(StrictModel):
    schema_version: str = "0.1"
    starter_release_audit_report_id: str
    status: Literal["passed", "failed"]
    demo_dir: str
    preflight_dir: str | None = None
    budget_dir: str | None = None
    non_authoritative: Literal[True] = True
    external_writes_performed: Literal[False] = False
    checks: list[StarterReleaseAuditCheck]
    generated_at: str


class BlockedBudgetAttemptAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class BlockedBudgetAttemptAuditReport(StrictModel):
    schema_version: str = "0.1"
    blocked_budget_attempt_audit_report_id: str
    status: Literal["passed", "failed"]
    preflight_packet_ref: str
    confirmation_ref: str
    blocked_budget_dir: str
    expected_blocked_state: Literal["budget_blocked_before_human_confirmation"]
    exception_raised: bool
    blocked_error: str | None = None
    non_authoritative: Literal[True] = True
    external_writes_performed: Literal[False] = False
    checks: list[BlockedBudgetAttemptAuditCheck]
    generated_at: str


class ContextCounterfactualAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ContextCounterfactualAuditReport(StrictModel):
    schema_version: str = "0.1"
    context_counterfactual_audit_report_id: str
    status: Literal["passed", "failed"]
    input_ref: str
    baseline_profile_ref: str
    comparison_profile_ref: str
    baseline_run_dir: str
    comparison_run_dir: str
    non_authoritative: Literal[True] = True
    external_writes_performed: Literal[False] = False
    checks: list[ContextCounterfactualAuditCheck]
    generated_at: str


class CrossRepoPromotionProposal(StrictModel):
    proposal_id: str
    target_repo: Literal[
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
        "LawFirm-os-skills-registry",
        "LawFirm-os-legal-knowledge-runtime",
    ]
    authority_plane: Literal[
        "control",
        "execution",
        "evidence",
        "skills_registry",
        "legal_knowledge_runtime",
    ]
    proposal_type: Literal[
        "schema_contract",
        "event_label_mapping",
        "workflow_interface",
        "lake_evidence_mapping",
        "skill_metadata",
        "context_bundle_interface",
    ]
    summary: str
    candidate_artifact_refs: list[str] = Field(default_factory=list)
    proposed_contract_refs: list[str] = Field(default_factory=list)
    required_governance_actions: list[str] = Field(default_factory=list)
    promotion_blockers: list[str] = Field(default_factory=list)
    non_authoritative: Literal[True] = True
    direct_promotion_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False


class CrossRepoPromotionPackage(StrictModel):
    schema_version: str = "0.1"
    package_id: str
    status: Literal["candidate_only"]
    origin_repo: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    generated_at: str
    reviewed_lock_status: Literal["reviewed_seed_lock"]
    target_repos: list[
        Literal[
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
            "LawFirm-os-skills-registry",
            "LawFirm-os-legal-knowledge-runtime",
        ]
    ]
    proposals: list[CrossRepoPromotionProposal]
    promotion_rule: str
    no_canonical_mutation: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_external_writes_performed: Literal[True] = True
    non_authoritative: Literal[True] = True


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
