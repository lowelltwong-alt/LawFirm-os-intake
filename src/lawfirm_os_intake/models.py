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
        "human_carrier_preapproval",
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
    timekeeper_id: str | None = None
    estimated_hours: float = Field(ge=0)
    estimated_hours_min: float | None = Field(default=None, ge=0)
    estimated_hours_max: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    rate_source: Literal[
        "synthetic_profile",
        "authorized_profile",
        "synthetic_named_timekeeper_override",
        "absent",
    ] = "absent"
    rate_is_synthetic: bool = True
    estimated_fees: float | None = Field(default=None, ge=0)
    estimated_expenses: float = Field(default=0, ge=0)
    estimated_expenses_min: float | None = Field(default=None, ge=0)
    estimated_expenses_max: float | None = Field(default=None, ge=0)
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
    probability: float | None = Field(default=None, ge=0, le=1)
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
    selected_scenario_basis: Literal[
        "default_standard",
        "confirmed_resolution_path",
        "fallback_last_scenario",
    ] = "default_standard"
    expected_total: float | None = None
    expected_total_probability_sum: float | None = None
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


class CarrierCompliantProjectionLine(StrictModel):
    phase_id: str
    task_id: str
    external_code_candidate: str | None = None
    expense_code: str | None = None
    staffing_role: str
    compliant_staffing_role: str | None = None
    proposed_hours: float = Field(ge=0)
    proposed_rate: float | None = Field(default=None, ge=0)
    staffing_rule_rate: float | None = Field(default=None, ge=0)
    compliant_rate: float | None = Field(default=None, ge=0)
    proposed_fees: float | None = Field(default=None, ge=0)
    compliant_fees: float | None = Field(default=None, ge=0)
    proposed_expenses: float = Field(ge=0)
    compliant_expenses: float = Field(ge=0)
    proposed_line_total: float | None = None
    compliant_line_total: float | None = None
    capped: bool = False
    disallowed: bool = False
    rate_cap_applied: bool = False
    expense_cap_applied: bool = False
    staffing_rule_applied: bool = False
    over_cap_amount: float = Field(default=0, ge=0)
    rate_cap_delta: float = Field(default=0, ge=0)
    expense_cap_delta: float = Field(default=0, ge=0)
    staffing_rule_delta: float = Field(default=0, ge=0)
    guideline_refs: list[str] = Field(default_factory=list)
    note: str


class NamedTimekeeperRate(StrictModel):
    timekeeper_id: str
    title: str
    state: str | None = None
    approved_rate: float = Field(ge=0)
    carrier_id: str
    rate_card_id: str
    precedence_tier: Literal["named_timekeeper_override"] = "named_timekeeper_override"
    source: Literal["synthetic_carrier_rate_card"] = "synthetic_carrier_rate_card"
    contains_real_firm_data: Literal[False] = False
    candidate_only: Literal[True] = True


class CarrierCompliantLeverageSummary(StrictModel):
    role: str
    proposed_hours: float = Field(ge=0)
    compliant_hours: float = Field(ge=0)
    proposed_fees: float = Field(ge=0)
    compliant_fees: float = Field(ge=0)
    proposed_hours_percent: float = Field(ge=0)
    compliant_hours_percent: float = Field(ge=0)
    proposed_fee_percent: float = Field(ge=0)
    compliant_fee_percent: float = Field(ge=0)


class CarrierCompliantProjectionBasis(StrictModel):
    guideline_id: str
    guideline_ref: str
    carrier_id: str
    guideline_status: Literal["candidate"]
    data_scope: Literal["synthetic_only"] = "synthetic_only"
    rate_caps: dict[str, float] = Field(default_factory=dict)
    expense_caps: dict[str, float] = Field(default_factory=dict)
    staffing_task_role_overrides: dict[str, str] = Field(default_factory=dict)
    contingency_allowed: bool
    budget_cadence: str
    variance_approval_percent: float = Field(ge=0)
    projection_only: Literal[True] = True
    proposal_lines_unchanged: Literal[True] = True
    no_submission_authority: Literal[True] = True


class CarrierCompliantProjection(StrictModel):
    schema_version: str = "0.1"
    projection_id: str
    status: Literal["projected_for_human_review"]
    basis: CarrierCompliantProjectionBasis
    proposed_total: float | None = None
    compliant_total: float | None = None
    proposed_subtotal_fees: float | None = None
    compliant_subtotal_fees: float | None = None
    proposed_subtotal_expenses: float = Field(ge=0)
    compliant_subtotal_expenses: float = Field(ge=0)
    proposed_contingency_amount: float | None = None
    compliant_contingency_amount: float | None = None
    over_cap_amount: float = Field(ge=0)
    rate_cap_delta: float = Field(ge=0)
    expense_cap_delta: float = Field(ge=0)
    staffing_rule_delta: float = Field(ge=0)
    contingency_delta: float = Field(ge=0)
    proposed_blended_rate: float | None = None
    compliant_blended_rate: float | None = None
    blended_rate_delta: float = Field(default=0, ge=0)
    line_count: int = Field(ge=0)
    capped_line_count: int = Field(ge=0)
    disallowed_line_count: int = Field(ge=0)
    staffing_rule_adjusted_line_count: int = Field(ge=0)
    leverage_summary: list[CarrierCompliantLeverageSummary] = Field(default_factory=list)
    lines: list[CarrierCompliantProjectionLine]
    rewrites_budget: Literal[False] = False
    not_authorized_for_client_submission: Literal[True] = True
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True


class CarrierPreapprovalRequirement(StrictModel):
    requirement_id: str
    threshold_id: str
    requirement_type: Literal[
        "experts_over_count",
        "expert_spend_over_amount",
        "depositions_over_count",
        "research_hours_over",
        "vendor_spend_over_amount",
    ]
    status: Literal["preapproval_required", "not_triggered", "unknown"]
    current_value: float | None = Field(default=None, ge=0)
    threshold_value: float = Field(ge=0)
    unit: str
    required_human_gate: Literal["human_carrier_preapproval"] = "human_carrier_preapproval"
    source: Literal["synthetic_carrier_guideline"] = "synthetic_carrier_guideline"
    structured_refs: list[str] = Field(default_factory=list)
    related_phase_ids: list[str] = Field(default_factory=list)
    related_task_ids: list[str] = Field(default_factory=list)
    related_external_codes: list[str] = Field(default_factory=list)
    related_expense_codes: list[str] = Field(default_factory=list)
    reason: str
    rewrites_budget: Literal[False] = False
    preapproval_obtained: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False


class CarrierPreapprovalReport(StrictModel):
    schema_version: str = "0.1"
    report_id: str
    budget_proposal_id: str
    guideline_id: str
    guideline_ref: str
    carrier_id: str
    status: Literal["preapproval_required", "no_preapproval_required", "unknown"]
    requirement_count: int = Field(ge=0)
    required_count: int = Field(ge=0)
    requirements: list[CarrierPreapprovalRequirement]
    required_human_gate: Literal["human_carrier_preapproval"] = "human_carrier_preapproval"
    candidate_only: Literal[True] = True
    preapproval_obtained: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str

    @model_validator(mode="after")
    def preapproval_counts_match(self) -> "CarrierPreapprovalReport":
        required = sum(
            1 for requirement in self.requirements if requirement.status == "preapproval_required"
        )
        if self.requirement_count != len(self.requirements):
            raise ValueError("carrier preapproval requirement count does not match")
        if self.required_count != required:
            raise ValueError("carrier preapproval required count does not match")
        if self.status == "preapproval_required" and required == 0:
            raise ValueError("preapproval-required report must include required items")
        if self.status == "no_preapproval_required" and required:
            raise ValueError("no-preapproval report cannot include required items")
        return self


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
    carrier_compliant_projection: CarrierCompliantProjection | None = None
    carrier_preapproval_report: CarrierPreapprovalReport | None = None
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


class BudgetReviewChange(StrictModel):
    change_id: str
    target_type: Literal[
        "budget_line",
        "proposal_assumption",
        "proposal_exclusion",
        "proposal_unknown",
        "scenario_selection",
    ]
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    expense_code: str | None = None
    staffing_role: str | None = None
    field: Literal[
        "estimated_hours",
        "hourly_rate",
        "estimated_expenses",
        "assumption",
        "exclusion",
        "unknown",
        "scenario_id",
    ]
    new_value: float | str | None = None
    reason: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    requires_human_review: Literal[True] = True

    @model_validator(mode="after")
    def support_required(self) -> "BudgetReviewChange":
        if not self.evidence_refs and not self.structured_refs:
            raise ValueError("budget review change requires evidence_refs or structured_refs")
        if self.target_type == "budget_line" and (not self.phase_id or not self.task_id):
            raise ValueError("budget line review change requires phase_id and task_id")
        return self


class BudgetReviewChangeRecord(StrictModel):
    schema_version: str = "0.1"
    budget_review_change_record_id: str
    budget_proposal_id: str
    source_budget_proposal_ref: str | None = None
    reviewer_id: str
    reviewer_role: str
    reviewed_at: str
    outcome: Literal[
        "confirmed_no_change",
        "corrected",
        "needs_more_information",
        "human_only",
        "declined_referred",
    ]
    decision_reason: str
    supersedes_budget_review_change_record_id: str | None = None
    changes: list[BudgetReviewChange] = Field(default_factory=list)
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    original_budget_mutated: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def corrected_requires_change(self) -> "BudgetReviewChangeRecord":
        if self.outcome == "corrected" and not self.changes:
            raise ValueError("corrected budget review requires at least one change")
        if self.outcome == "confirmed_no_change" and self.changes:
            raise ValueError("confirmed_no_change review cannot carry changes")
        return self


class BudgetPhaseBudgetSnapshot(StrictModel):
    phase_id: str
    budgeted_fees: float | None = None
    budgeted_expenses: float = Field(default=0, ge=0)
    budgeted_total: float | None = None
    external_code_candidates: list[str] = Field(default_factory=list)


class BudgetCodeBudgetSnapshot(StrictModel):
    code: str
    phase_id: str | None = None
    budgeted_fees: float = Field(default=0, ge=0)
    budgeted_expenses: float = Field(default=0, ge=0)
    budgeted_total: float = Field(default=0, ge=0)


class BudgetRevisionDelta(StrictModel):
    delta_id: str
    change_id: str
    target_type: str
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    expense_code: str | None = None
    staffing_role: str | None = None
    field: str
    previous_value: float | str | None = None
    new_value: float | str | None = None
    hours_delta: float = 0
    fee_delta: float = 0
    expense_delta: float = 0
    total_delta: float = 0
    reason: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)


class BudgetRevisionReport(StrictModel):
    schema_version: str = "0.1"
    budget_revision_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_review_change_record_id: str
    source_budget_proposal_ref: str
    status: Literal[
        "revision_recorded",
        "confirmed_no_change",
        "blocked_needs_more_information",
        "human_only",
        "declined_referred",
    ]
    review_outcome: str
    change_count: int = Field(ge=0)
    numeric_change_count: int = Field(ge=0)
    original_phase_totals: list[BudgetPhaseBudgetSnapshot]
    revised_phase_totals: list[BudgetPhaseBudgetSnapshot]
    original_code_totals: list[BudgetCodeBudgetSnapshot] = Field(default_factory=list)
    revised_code_totals: list[BudgetCodeBudgetSnapshot] = Field(default_factory=list)
    original_total: float | None = None
    revised_total: float | None = None
    total_delta: float = 0
    deltas: list[BudgetRevisionDelta]
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    original_budget_mutated: Literal[False] = False
    superseding_budget_written: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False
    not_authorized_for_client_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    candidate_only: Literal[True] = True
    append_only_history_ref: str | None = None
    dry_run_exception_label: Literal["budget_human_change_recorded"] = (
        "budget_human_change_recorded"
    )
    not_authorized_for_lake_write: Literal[True] = True
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True
    generated_at: str


BudgetChangeLedgerEventKind = Literal[
    "human_budget_change_recorded",
    "human_budget_no_change_confirmed",
    "human_budget_review_blocked",
    "human_budget_human_only_hold",
    "human_budget_declined_referred",
]

BudgetChangeLedgerEventStatus = Literal[
    "recorded_candidate",
    "no_change_confirmed",
    "blocked_from_budget_use",
]

BudgetChangeLedgerChangeClass = Literal[
    "hours_change",
    "rate_change",
    "expense_change",
    "assumption_change",
    "exclusion_change",
    "unknown_info_change",
    "scenario_change",
    "other_non_numeric_change",
    "review_outcome_only",
]


class BudgetChangeLedgerEvent(StrictModel):
    schema_version: str = "0.1"
    budget_change_ledger_event_id: str
    ledger_id: str
    sequence_index: int = Field(ge=0)
    budget_revision_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_review_change_record_id: str
    source_budget_proposal_ref: str
    reviewer_id: str
    reviewer_role: str
    reviewed_at: str
    review_outcome: str
    decision_reason: str
    supersedes_budget_review_change_record_id: str | None = None
    change_id: str | None = None
    delta_id: str | None = None
    event_kind: BudgetChangeLedgerEventKind
    status: BudgetChangeLedgerEventStatus
    change_class: BudgetChangeLedgerChangeClass
    target_type: str | None = None
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    expense_code: str | None = None
    staffing_role: str | None = None
    field: str | None = None
    previous_value: float | str | None = None
    new_value: float | str | None = None
    hours_delta: float = 0
    fee_delta: float = 0
    expense_delta: float = 0
    total_delta: float = 0
    budget_total_before_event: float | None = None
    budget_total_after_event: float | None = None
    reason: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    exception_lake_local_event_label: str
    exception_lake_candidate_reason: str
    requires_exception_lake_admission_review: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only: Literal[True] = True
    original_budget_mutated: Literal[False] = False
    superseding_budget_written: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False
    not_authorized_for_client_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def changed_events_require_change_id(self) -> "BudgetChangeLedgerEvent":
        if self.event_kind == "human_budget_change_recorded" and not (
            self.change_id and self.delta_id
        ):
            raise ValueError("human budget change ledger events require change_id and delta_id")
        return self


class BudgetChangeLedgerReport(StrictModel):
    schema_version: str = "0.1"
    budget_change_ledger_report_id: str
    ledger_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_revision_report_id: str
    budget_review_change_record_id: str
    source_budget_proposal_ref: str
    source_budget_revision_report_ref: str
    ledger_ref: str
    status: Literal[
        "ledger_recorded",
        "no_change_confirmed",
        "blocked_budget_review_outcome_recorded",
    ]
    review_outcome: str
    entry_count: int = Field(ge=0)
    numeric_change_entry_count: int = Field(ge=0)
    total_delta: float = 0
    event_kind_counts: dict[str, int] = Field(default_factory=dict)
    events: list[BudgetChangeLedgerEvent]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only: Literal[True] = True
    source_budget_mutated: Literal[False] = False
    source_revision_report_mutated: Literal[False] = False
    superseding_budget_written: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    carrier_submission_authorized: Literal[False] = False
    not_authorized_for_client_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_events(self) -> "BudgetChangeLedgerReport":
        if self.entry_count != len(self.events):
            raise ValueError("budget change ledger entry count must match events")
        if self.numeric_change_entry_count != sum(
            1
            for event in self.events
            if event.fee_delta or event.expense_delta or event.hours_delta
        ):
            raise ValueError("budget change ledger numeric count must match events")
        kind_counts: dict[str, int] = {}
        for event in self.events:
            kind_counts[event.event_kind] = kind_counts.get(event.event_kind, 0) + 1
        if self.event_kind_counts != kind_counts:
            raise ValueError("budget change ledger kind counts must match events")
        if self.status == "ledger_recorded" and not self.events:
            raise ValueError("recorded budget change ledger requires events")
        return self


class BudgetActualAmount(StrictModel):
    fees: float = Field(default=0, ge=0)
    expenses: float = Field(default=0, ge=0)
    hours: float | None = Field(default=None, ge=0)


class BudgetActualsSource(StrictModel):
    schema_version: str = "0.1"
    actuals_source_id: str
    budget_proposal_id: str | None = None
    data_origin: Literal["synthetic"] = "synthetic"
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    actual_resolution_scenario_id: str | None = None
    actuals_by_phase: dict[str, BudgetActualAmount] = Field(default_factory=dict)
    actuals_by_code: dict[str, BudgetActualAmount] = Field(default_factory=dict)
    source_ref: str | None = None
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    non_authoritative: Literal[True] = True


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
    variance_driver_candidates: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class BudgetActualCodeComparison(StrictModel):
    code: str
    phase_id: str | None = None
    budgeted_fees: float = 0
    budgeted_expenses: float = 0
    budgeted_total: float = 0
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
    variance_driver_candidates: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class BudgetActualVarianceDriverCandidate(StrictModel):
    candidate_id: str
    driver_label: Literal[
        "actuals_without_budget",
        "fee_overrun",
        "fee_underrun",
        "expense_overrun",
        "expense_underrun",
        "human_revision_delta",
        "unknown_driver",
    ]
    phase_id: str | None = None
    code: str | None = None
    variance_amount: float | None = None
    reason: str
    target_learning_loop: Literal["budget_driver", "template_mapping", "validation_rule"]
    requires_human_review: Literal[True] = True
    silent_learning_performed: Literal[False] = False


class BudgetActualComparisonReport(StrictModel):
    schema_version: str = "0.1"
    budget_actual_comparison_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: Literal["actuals_not_available", "passed", "variance_review_required"]
    comparison_scope: Literal["phase", "phase_and_code"] = "phase"
    comparison_budget_state: Literal["original_proposal", "human_revised_candidate"] = (
        "original_proposal"
    )
    budget_revision_report_id: str | None = None
    budget_revision_report_ref: str | None = None
    actual_resolution_scenario_id: str | None = None
    phase_comparisons: list[BudgetActualPhaseComparison]
    code_comparisons: list[BudgetActualCodeComparison] = Field(default_factory=list)
    variance_driver_candidates: list[BudgetActualVarianceDriverCandidate] = Field(
        default_factory=list
    )
    learning_disposition_candidates: list[str] = Field(default_factory=list)
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


BudgetActualVarianceLedgerEventKind = Literal[
    "budget_actual_phase_comparison_recorded",
    "budget_actual_code_comparison_recorded",
    "budget_actual_missing_actuals_recorded",
    "budget_actual_without_budget_recorded",
    "budget_actual_human_revision_context_recorded",
]

BudgetActualVarianceLedgerDecisionStatus = Literal[
    "recorded_within_threshold",
    "over_threshold_requires_review",
    "under_threshold_requires_review",
    "actuals_missing_pending_source",
    "actuals_without_budget_requires_review",
    "human_revision_context_requires_review",
]

BudgetActualVarianceLedgerStatus = Literal[
    "variance_ledger_ready_for_review",
    "variance_ledger_passed",
    "variance_ledger_no_actuals",
]


class BudgetActualVarianceLedgerEvent(StrictModel):
    schema_version: str = "0.1"
    budget_actual_variance_ledger_event_id: str
    ledger_id: str
    sequence_index: int = Field(ge=0)
    budget_actual_comparison_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_revision_report_id: str | None = None
    actuals_source_ref: str | None = None
    comparison_budget_state: Literal["original_proposal", "human_revised_candidate"]
    actual_resolution_scenario_id: str | None = None
    comparison_scope: Literal["phase", "code", "revision_context"]
    phase_id: str | None = None
    code: str | None = None
    event_kind: BudgetActualVarianceLedgerEventKind
    decision_status: BudgetActualVarianceLedgerDecisionStatus
    local_event_label: str
    canonical_lake_class_candidate: Literal["workflow_escalation"] = "workflow_escalation"
    comparison_status: Literal[
        "actuals_not_available",
        "within_threshold",
        "over_threshold",
        "under_threshold",
        "revision_context",
    ]
    budgeted_fees: float | None = None
    budgeted_expenses: float | None = None
    budgeted_total: float | None = None
    actual_fees: float | None = None
    actual_expenses: float | None = None
    actual_total: float | None = None
    variance_amount: float | None = None
    variance_percent: float | None = None
    variance_driver_candidates: list[str] = Field(default_factory=list)
    learning_disposition_candidates: list[str] = Field(default_factory=list)
    proposed_next_actions: list[str] = Field(default_factory=list)
    required_human_decisions: list[str] = Field(default_factory=list)
    exception_candidate_ids: list[str] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    requires_exception_lake_admission_review: Literal[True] = True
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def variance_event_scope_is_complete(self) -> "BudgetActualVarianceLedgerEvent":
        if self.comparison_scope == "phase" and not self.phase_id:
            raise ValueError("phase variance ledger events require phase_id")
        if self.comparison_scope == "code" and not self.code:
            raise ValueError("code variance ledger events require code")
        if (
            self.decision_status
            in {
                "over_threshold_requires_review",
                "under_threshold_requires_review",
                "actuals_without_budget_requires_review",
                "actuals_missing_pending_source",
                "human_revision_context_requires_review",
            }
            and not self.required_human_decisions
        ):
            raise ValueError("variance review events require human decision prompts")
        if self.event_kind == "budget_actual_without_budget_recorded":
            if (self.budgeted_total or 0) != 0 or (self.actual_total or 0) <= 0:
                raise ValueError("actuals-without-budget events require zero budget and actuals")
        return self


class BudgetActualVarianceLedgerReport(StrictModel):
    schema_version: str = "0.1"
    budget_actual_variance_ledger_report_id: str
    ledger_id: str
    budget_actual_comparison_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_revision_report_id: str | None = None
    budget_revision_report_ref: str | None = None
    actuals_source_ref: str | None = None
    status: BudgetActualVarianceLedgerStatus
    comparison_scope: Literal["phase", "phase_and_code"] = "phase"
    comparison_budget_state: Literal["original_proposal", "human_revised_candidate"]
    actual_resolution_scenario_id: str | None = None
    entry_count: int = Field(ge=0)
    phase_event_count: int = Field(ge=0)
    code_event_count: int = Field(ge=0)
    revision_context_event_count: int = Field(ge=0)
    variance_review_event_count: int = Field(ge=0)
    missing_actuals_event_count: int = Field(ge=0)
    actuals_without_budget_event_count: int = Field(ge=0)
    within_threshold_event_count: int = Field(ge=0)
    event_kind_counts: dict[str, int] = Field(default_factory=dict)
    total_budgeted: float | None = None
    total_actual: float | None = None
    total_variance_amount: float | None = None
    total_variance_percent: float | None = None
    events: list[BudgetActualVarianceLedgerEvent]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_events(self) -> "BudgetActualVarianceLedgerReport":
        if self.entry_count != len(self.events):
            raise ValueError("budget actual variance ledger count must match events")
        if self.phase_event_count != sum(
            1 for event in self.events if event.comparison_scope == "phase"
        ):
            raise ValueError("budget actual variance phase count must match events")
        if self.code_event_count != sum(
            1 for event in self.events if event.comparison_scope == "code"
        ):
            raise ValueError("budget actual variance code count must match events")
        if self.revision_context_event_count != sum(
            1 for event in self.events if event.comparison_scope == "revision_context"
        ):
            raise ValueError("budget actual variance revision-context count must match events")
        review_statuses = {
            "over_threshold_requires_review",
            "under_threshold_requires_review",
            "actuals_without_budget_requires_review",
            "human_revision_context_requires_review",
        }
        if self.variance_review_event_count != sum(
            1 for event in self.events if event.decision_status in review_statuses
        ):
            raise ValueError("budget actual variance review count must match events")
        if self.missing_actuals_event_count != sum(
            1 for event in self.events if event.decision_status == "actuals_missing_pending_source"
        ):
            raise ValueError("budget actual variance missing-actuals count must match events")
        if self.actuals_without_budget_event_count != sum(
            1
            for event in self.events
            if event.decision_status == "actuals_without_budget_requires_review"
        ):
            raise ValueError("budget actuals-without-budget count must match events")
        if self.within_threshold_event_count != sum(
            1 for event in self.events if event.decision_status == "recorded_within_threshold"
        ):
            raise ValueError("budget actual within-threshold count must match events")
        kind_counts: dict[str, int] = {}
        for event in self.events:
            kind_counts[event.event_kind] = kind_counts.get(event.event_kind, 0) + 1
        if self.event_kind_counts != kind_counts:
            raise ValueError("budget actual variance ledger kind counts must match events")
        if self.status != "variance_ledger_no_actuals" and not self.events:
            raise ValueError("budget actual variance ledger requires events")
        return self


BudgetCalibrationArtifactKind = Literal[
    "intake_source_fixture",
    "human_confirmation_fixture",
    "budget_review_fixture",
    "actuals_fixture",
    "carrier_rejection_fixture",
    "reviewed_gold_fixture",
    "learning_gate_fixture",
    "learning_shadow_eval_fixture",
    "learning_support_fixture",
    "unclassified_json_fixture",
]

BudgetCalibrationRole = Literal[
    "input_context_fixture",
    "outcome_evidence_fixture",
    "reviewed_baseline_fixture",
    "learning_gate_fixture",
    "shadow_eval_fixture",
    "unclassified_supporting_fixture",
]

BudgetCalibrationEligibility = Literal[
    "eligible_for_synthetic_calibration_review",
    "supporting_context_only",
    "blocked_real_or_privileged_data",
    "blocked_boundary_violation",
]


class BudgetCalibrationCorpusArtifact(StrictModel):
    artifact_id: str
    artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    calibration_role: BudgetCalibrationRole
    eligibility: BudgetCalibrationEligibility
    sha256: str
    data_origin: str | None = None
    synthetic_only: bool | None = None
    contains_real_client_data: bool | None = None
    contains_real_matter_data: bool | None = None
    contains_privileged_data: bool | None = None
    scope_failures: list[str] = Field(default_factory=list)
    boundary_failures: list[str] = Field(default_factory=list)
    support_refs: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class BudgetCalibrationCorpusCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)


class BudgetCalibrationCorpusReport(StrictModel):
    schema_version: str = "0.1"
    corpus_report_id: str
    status: Literal[
        "synthetic_corpus_ready_for_review",
        "blocked_real_or_privileged_data",
        "failed",
        "empty_corpus",
    ]
    corpus_root_ref: str
    artifact_count: int = Field(ge=0)
    eligible_artifact_count: int = Field(ge=0)
    supporting_artifact_count: int = Field(ge=0)
    blocked_artifact_count: int = Field(ge=0)
    artifact_kind_counts: dict[str, int] = Field(default_factory=dict)
    calibration_role_counts: dict[str, int] = Field(default_factory=dict)
    artifacts: list[BudgetCalibrationCorpusArtifact]
    checks: list[BudgetCalibrationCorpusCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_artifacts(self) -> "BudgetCalibrationCorpusReport":
        if self.artifact_count != len(self.artifacts):
            raise ValueError("budget calibration corpus artifact count must match artifacts")
        if self.eligible_artifact_count != sum(
            1
            for artifact in self.artifacts
            if artifact.eligibility == "eligible_for_synthetic_calibration_review"
        ):
            raise ValueError("eligible artifact count does not match artifacts")
        blocked = sum(
            1
            for artifact in self.artifacts
            if artifact.eligibility
            in {"blocked_real_or_privileged_data", "blocked_boundary_violation"}
        )
        if self.blocked_artifact_count != blocked:
            raise ValueError("blocked artifact count does not match artifacts")
        if self.status == "synthetic_corpus_ready_for_review" and (
            self.blocked_artifact_count or not self.eligible_artifact_count
        ):
            raise ValueError("ready corpus requires eligible artifacts and no blocked artifacts")
        return self


BudgetCorpusReplayCommandExecutionMode = Literal["planned_only_not_executed"]

BudgetCorpusReplayCaseStatus = Literal[
    "planned_for_replay",
    "supporting_context_only",
    "blocked_from_replay",
]

BudgetCorpusReplayPlanStatus = Literal[
    "replay_plan_ready_for_review",
    "blocked_by_corpus_report",
    "no_replay_candidates",
]


class BudgetCorpusReplayCommand(StrictModel):
    command_id: str
    command: str
    purpose: str
    input_artifact_refs: list[str] = Field(default_factory=list)
    expected_output_refs: list[str] = Field(default_factory=list)
    requires_prior_command_ids: list[str] = Field(default_factory=list)
    execution_mode: BudgetCorpusReplayCommandExecutionMode = "planned_only_not_executed"
    candidate_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False


class BudgetCorpusReplayCase(StrictModel):
    replay_case_id: str
    source_artifact_id: str
    source_artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    calibration_role: BudgetCalibrationRole
    eligibility: BudgetCalibrationEligibility
    status: BudgetCorpusReplayCaseStatus
    baseline_input_ref: str | None = None
    baseline_practice_profile_ref: str | None = None
    baseline_confirmation_ref: str | None = None
    command_chain: list[BudgetCorpusReplayCommand] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    support_refs: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    required_next_gates: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def command_status_matches_case_status(self) -> "BudgetCorpusReplayCase":
        if self.status != "planned_for_replay" and self.command_chain:
            raise ValueError("only planned replay cases may include command chains")
        if self.status == "planned_for_replay" and not self.command_chain:
            raise ValueError("planned replay cases require at least one command")
        return self


class BudgetCorpusReplayCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    case_ids: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)


class BudgetCorpusReplayPlan(StrictModel):
    schema_version: str = "0.1"
    replay_plan_id: str
    source_corpus_report_id: str
    source_corpus_report_ref: str
    source_corpus_status: str
    status: BudgetCorpusReplayPlanStatus
    case_count: int = Field(ge=0)
    planned_case_count: int = Field(ge=0)
    supporting_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    cases: list[BudgetCorpusReplayCase]
    checks: list[BudgetCorpusReplayCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_cases(self) -> "BudgetCorpusReplayPlan":
        if self.case_count != len(self.cases):
            raise ValueError("budget corpus replay case count must match cases")
        if self.planned_case_count != sum(
            1 for case in self.cases if case.status == "planned_for_replay"
        ):
            raise ValueError("planned replay case count does not match cases")
        if self.supporting_case_count != sum(
            1 for case in self.cases if case.status == "supporting_context_only"
        ):
            raise ValueError("supporting replay case count does not match cases")
        if self.blocked_case_count != sum(
            1 for case in self.cases if case.status == "blocked_from_replay"
        ):
            raise ValueError("blocked replay case count does not match cases")
        if self.status == "replay_plan_ready_for_review" and not self.planned_case_count:
            raise ValueError("ready replay plan requires at least one planned case")
        return self


BudgetCorpusReplayRunMode = Literal["dry_run", "execute"]

BudgetCorpusReplayCommandResultStatus = Literal[
    "planned_only_not_executed",
    "executed_passed",
    "executed_failed",
    "skipped_not_selected",
    "skipped_supporting_context",
    "blocked_from_plan",
    "blocked_missing_input",
    "blocked_prior_command_failed",
    "blocked_unsupported_command",
    "blocked_missing_placeholder",
]

BudgetCorpusReplayCaseResultStatus = Literal[
    "dry_run_ready",
    "executed_passed",
    "executed_failed",
    "skipped_not_selected",
    "skipped_supporting_context",
    "blocked",
]

BudgetCorpusReplayExecutionReportStatus = Literal[
    "dry_run_ready_for_review",
    "execution_passed_for_review",
    "execution_failed",
    "blocked_by_plan",
    "no_executable_cases",
]


class BudgetCorpusReplayOutputCheck(StrictModel):
    output_ref: str
    resolved_output_path: str
    exists: bool
    sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class BudgetCorpusReplayCommandResult(StrictModel):
    command_id: str
    replay_case_id: str
    status: BudgetCorpusReplayCommandResultStatus
    execution_mode: BudgetCorpusReplayRunMode
    planned_command: str
    resolved_command: str
    return_code: int | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    output_checks: list[BudgetCorpusReplayOutputCheck] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False


class BudgetCorpusReplayCaseResult(StrictModel):
    replay_case_id: str
    source_artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    status: BudgetCorpusReplayCaseResultStatus
    command_results: list[BudgetCorpusReplayCommandResult] = Field(default_factory=list)
    output_checks: list[BudgetCorpusReplayOutputCheck] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False


class BudgetCorpusReplayExecutionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    case_ids: list[str] = Field(default_factory=list)
    command_ids: list[str] = Field(default_factory=list)


class BudgetCorpusReplayExecutionReport(StrictModel):
    schema_version: str = "0.1"
    replay_execution_report_id: str
    replay_plan_id: str
    replay_plan_ref: str
    execution_mode: BudgetCorpusReplayRunMode
    status: BudgetCorpusReplayExecutionReportStatus
    replay_run_root: str
    selected_case_ids: list[str] = Field(default_factory=list)
    case_count: int = Field(ge=0)
    executed_case_count: int = Field(ge=0)
    dry_run_case_count: int = Field(ge=0)
    skipped_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    command_count: int = Field(ge=0)
    executed_command_count: int = Field(ge=0)
    failed_command_count: int = Field(ge=0)
    cases: list[BudgetCorpusReplayCaseResult]
    checks: list[BudgetCorpusReplayExecutionCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_case_results(self) -> "BudgetCorpusReplayExecutionReport":
        if self.case_count != len(self.cases):
            raise ValueError("budget corpus replay execution case count must match cases")
        if self.executed_case_count != sum(
            1 for case in self.cases if case.status == "executed_passed"
        ):
            raise ValueError("executed case count does not match cases")
        if self.dry_run_case_count != sum(
            1 for case in self.cases if case.status == "dry_run_ready"
        ):
            raise ValueError("dry-run case count does not match cases")
        if self.failed_case_count != sum(
            1 for case in self.cases if case.status == "executed_failed"
        ):
            raise ValueError("failed case count does not match cases")
        if self.blocked_case_count != sum(1 for case in self.cases if case.status == "blocked"):
            raise ValueError("blocked case count does not match cases")
        skipped = sum(
            1
            for case in self.cases
            if case.status in {"skipped_not_selected", "skipped_supporting_context"}
        )
        if self.skipped_case_count != skipped:
            raise ValueError("skipped case count does not match cases")
        command_results = [command for case in self.cases for command in case.command_results]
        if self.command_count != len(command_results):
            raise ValueError("command count does not match command results")
        if self.executed_command_count != sum(
            1 for command in command_results if command.status == "executed_passed"
        ):
            raise ValueError("executed command count does not match command results")
        if self.failed_command_count != sum(
            1 for command in command_results if command.status == "executed_failed"
        ):
            raise ValueError("failed command count does not match command results")
        return self


BudgetCorpusReplayReviewAction = Literal[
    "review_fixture_binding",
    "execute_before_learning_review",
    "repair_replay_before_learning",
    "provide_shadow_eval_input_or_hold",
    "resolve_blocker_or_exclude",
    "run_selected_case_before_review",
    "acknowledge_supporting_context",
]

BudgetCorpusReplayReviewPriority = Literal["critical", "high", "medium", "low"]

BudgetCorpusReplayReviewPacketStatus = Literal[
    "ready_for_human_replay_review",
    "replay_repair_required",
    "blocked_pending_replay_execution",
    "no_reviewable_cases",
]

BudgetCorpusReplayReviewOutcome = Literal[
    "approve_fixture_binding",
    "reject_fixture_binding",
    "needs_replay_repair",
    "needs_more_information",
    "human_only_hold",
    "exclude_from_learning",
    "provide_shadow_eval_input",
    "acknowledge_supporting_context",
]


class BudgetCorpusReplayReviewRecommendation(StrictModel):
    recommendation_id: str
    replay_case_id: str
    source_artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    replay_case_status: BudgetCorpusReplayCaseResultStatus
    recommended_action: BudgetCorpusReplayReviewAction
    priority: BudgetCorpusReplayReviewPriority
    why: list[str]
    command_result_statuses: dict[str, str] = Field(default_factory=dict)
    output_refs: list[str] = Field(default_factory=list)
    missing_output_refs: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    required_human_decisions: list[str]
    downstream_learning_gate_candidate: bool = False
    downstream_learning_gate_allowed_without_review: Literal[False] = False
    external_submission_authorized: Literal[False] = False
    lake_write_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False


class BudgetCorpusReplayReviewRedTeamNote(StrictModel):
    note_id: str
    severity: BudgetCorpusReplayReviewPriority
    scope: Literal[
        "boundary",
        "execution_scope",
        "output_integrity",
        "learning_loop",
        "supporting_context",
        "shadow_eval",
    ]
    message: str
    recommended_check: str
    replay_case_ids: list[str] = Field(default_factory=list)


class BudgetCorpusReplayReviewDecisionTemplate(StrictModel):
    decision_template_id: str
    replay_case_id: str
    source_artifact_ref: str
    recommended_action: BudgetCorpusReplayReviewAction
    allowed_outcomes: list[BudgetCorpusReplayReviewOutcome]
    recommended_outcome: BudgetCorpusReplayReviewOutcome
    required_fields: list[str]
    required_evidence_refs: list[str] = Field(default_factory=list)
    append_only_review_outcome_required: Literal[True] = True
    reviewer_id_required: Literal[True] = True
    reviewed_at_required: Literal[True] = True
    decision_reason_required: Literal[True] = True
    downstream_learning_gate_allowed_without_review: Literal[False] = False
    external_submission_authorized: Literal[False] = False
    lake_write_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False


class BudgetCorpusReplayReviewPacket(StrictModel):
    schema_version: str = "0.1"
    review_packet_id: str
    replay_execution_report_id: str
    replay_execution_report_ref: str
    replay_execution_status: BudgetCorpusReplayExecutionReportStatus
    replay_execution_mode: BudgetCorpusReplayRunMode
    status: BudgetCorpusReplayReviewPacketStatus
    recommendation_count: int = Field(ge=0)
    decision_template_count: int = Field(ge=0)
    executed_passed_case_count: int = Field(ge=0)
    dry_run_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    supporting_context_case_count: int = Field(ge=0)
    recommendations: list[BudgetCorpusReplayReviewRecommendation]
    red_team_notes: list[BudgetCorpusReplayReviewRedTeamNote]
    decision_templates: list[BudgetCorpusReplayReviewDecisionTemplate]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    append_only_review_outcome_required: Literal[True] = True
    downstream_learning_gate_allowed_without_review: Literal[False] = False
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_review_packet(self) -> "BudgetCorpusReplayReviewPacket":
        if self.recommendation_count != len(self.recommendations):
            raise ValueError("replay review recommendation count must match recommendations")
        if self.decision_template_count != len(self.decision_templates):
            raise ValueError("replay review decision template count must match templates")
        if self.status == "ready_for_human_replay_review" and not self.recommendations:
            raise ValueError("ready replay review packet requires recommendations")
        return self


class BudgetCorpusReplayReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    review_outcome_id: str
    review_packet_id: str
    replay_execution_report_id: str | None = None
    replay_case_id: str
    reviewer_id: str
    reviewer_role: str | None = None
    reviewed_at: str
    outcome: BudgetCorpusReplayReviewOutcome
    decision_reason: str
    approved_output_refs: list[str] = Field(default_factory=list)
    rejected_output_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    supersedes_review_outcome_id: str | None = None
    source_review_packet_ref: str | None = None
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    fixture_binding_approved: bool = False
    downstream_learning_gate_allowed: Literal[False] = False
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def approved_binding_requires_outputs(self) -> "BudgetCorpusReplayReviewOutcomeRecord":
        if self.outcome == "approve_fixture_binding" and not self.approved_output_refs:
            raise ValueError("approve_fixture_binding requires approved_output_refs")
        if self.outcome == "reject_fixture_binding" and not (
            self.rejected_output_refs or self.decision_reason
        ):
            raise ValueError("reject_fixture_binding requires rejected refs or a reason")
        return self


class BudgetCorpusReplayReviewOutcomeCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    replay_case_ids: list[str] = Field(default_factory=list)


class BudgetCorpusReplayReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    review_outcome_report_id: str
    review_packet_id: str
    replay_execution_report_id: str
    source_review_packet_ref: str
    review_outcome_record_id: str
    status: Literal[
        "review_outcome_recorded",
        "review_outcome_recorded_learning_still_blocked",
        "review_outcome_rejected_or_needs_repair",
        "review_outcome_failed_validation",
    ]
    replay_case_id: str
    outcome: BudgetCorpusReplayReviewOutcome
    decision_action: BudgetCorpusReplayReviewAction | None = None
    decision_reason: str
    append_only_history_ref: str
    approved_output_refs: list[str] = Field(default_factory=list)
    rejected_output_refs: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    checks: list[BudgetCorpusReplayReviewOutcomeCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only: Literal[True] = True
    source_packet_mutated: Literal[False] = False
    fixture_binding_approved: bool = False
    downstream_learning_gate_allowed: Literal[False] = False
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


BudgetFixtureBindingAction = Literal[
    "bind_replay_outputs_to_synthetic_fixture",
    "bind_replay_outputs_to_reviewed_gold",
    "hold_for_manual_fixture_design",
    "exclude_from_fixture_binding",
]

BudgetFixtureBindingCandidateStatus = Literal[
    "candidate_ready_for_fixture_update_review",
    "blocked_pending_approved_outcome",
    "blocked_missing_approved_outputs",
]

BudgetFixtureBindingCandidateReportStatus = Literal[
    "fixture_binding_candidates_ready_for_review",
    "blocked_pending_approved_outcome",
    "blocked_missing_approved_outputs",
    "no_fixture_binding_candidates",
]


class BudgetFixtureBindingCandidate(StrictModel):
    fixture_binding_candidate_id: str
    review_outcome_report_id: str
    review_outcome_record_id: str
    review_packet_id: str
    replay_execution_report_id: str
    replay_case_id: str
    source_artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    approved_output_refs: list[str] = Field(default_factory=list)
    proposed_target_fixture_refs: list[str] = Field(default_factory=list)
    proposed_binding_action: BudgetFixtureBindingAction
    status: BudgetFixtureBindingCandidateStatus
    why: list[str]
    required_human_steps: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    review_packet_mutated: Literal[False] = False
    source_fixture_mutated: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_binding_applied: Literal[False] = False
    downstream_learning_gate_allowed: Literal[False] = False
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def ready_candidates_require_outputs(self) -> "BudgetFixtureBindingCandidate":
        if self.status == "candidate_ready_for_fixture_update_review" and not (
            self.approved_output_refs and self.proposed_target_fixture_refs
        ):
            raise ValueError(
                "ready fixture binding candidates require approved outputs and target refs"
            )
        return self


class BudgetFixtureBindingCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)
    replay_case_ids: list[str] = Field(default_factory=list)


class BudgetFixtureBindingCandidateReport(StrictModel):
    schema_version: str = "0.1"
    fixture_binding_candidate_report_id: str
    review_packet_id: str
    review_outcome_report_id: str
    review_outcome_record_id: str
    replay_execution_report_id: str
    replay_case_id: str
    source_review_packet_ref: str
    source_review_outcome_report_ref: str
    status: BudgetFixtureBindingCandidateReportStatus
    candidate_count: int = Field(ge=0)
    ready_candidate_count: int = Field(ge=0)
    blocked_candidate_count: int = Field(ge=0)
    candidates: list[BudgetFixtureBindingCandidate]
    checks: list[BudgetFixtureBindingCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    review_packet_mutated: Literal[False] = False
    outcome_report_mutated: Literal[False] = False
    source_fixture_mutated: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_binding_applied: Literal[False] = False
    downstream_learning_gate_allowed: Literal[False] = False
    calibration_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_candidates(self) -> "BudgetFixtureBindingCandidateReport":
        if self.candidate_count != len(self.candidates):
            raise ValueError("fixture binding candidate count must match candidates")
        ready_count = sum(
            1
            for candidate in self.candidates
            if candidate.status == "candidate_ready_for_fixture_update_review"
        )
        if self.ready_candidate_count != ready_count:
            raise ValueError("ready fixture binding candidate count does not match candidates")
        if self.blocked_candidate_count != self.candidate_count - self.ready_candidate_count:
            raise ValueError("blocked fixture binding candidate count does not match candidates")
        if self.status == "fixture_binding_candidates_ready_for_review" and not ready_count:
            raise ValueError("ready fixture binding candidate report requires ready candidates")
        return self


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


class CarrierExpectedResponse(StrictModel):
    submission_id: str
    submission_type: Literal["budget", "invoice", "appeal", "portal_action"]
    carrier_id: str
    budget_proposal_id: str | None = None
    invoice_id: str | None = None
    amount_submitted: float | None = Field(default=None, ge=0)
    expected_response_due_at: str
    human_owner: str | None = None
    source_ref: str


class CarrierRejectionSourceRef(StrictModel):
    source_channel: Literal[
        "portal_status",
        "portal_export",
        "email_notice",
        "ledes_response",
        "returned_workbook",
        "appeal_correspondence",
        "manual_entry",
    ]
    source_id: str
    source_record_id: str
    retrieved_at: str
    content_sha256: str
    message_id: str | None = None
    portal_status_id: str | None = None
    row_ref: str | None = None
    attachment_id: str | None = None


class CarrierRejectionNotice(StrictModel):
    notice_id: str
    carrier_id: str
    platform: str
    submission_id: str | None = None
    budget_proposal_id: str | None = None
    invoice_id: str | None = None
    line_id: str | None = None
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    expense_code: str | None = None
    timekeeper_id: str | None = None
    status_timestamp: str
    response_type: Literal[
        "accepted",
        "rejected",
        "partially_accepted",
        "transport_failure",
        "comment_only",
        "unknown",
    ]
    parse_status: Literal["parsed", "parse_failed"] = "parsed"
    parser_version: str
    amount_submitted: float | None = Field(default=None, ge=0)
    amount_rejected: float | None = Field(default=None, ge=0)
    amount_allowed: float | None = Field(default=None, ge=0)
    amount_disputed: float | None = Field(default=None, ge=0)
    reason_code: str | None = None
    reason_text_excerpt: str
    human_owner: str | None = None
    followup_due_at: str | None = None
    idempotency_key: str
    source_refs: list[CarrierRejectionSourceRef]


class CarrierAppealResult(StrictModel):
    appeal_result_id: str
    related_notice_id: str
    result: Literal[
        "accepted",
        "denied",
        "partially_accepted",
        "withdrawn",
        "no_response",
        "stale",
    ]
    appealed_amount: float | None = Field(default=None, ge=0)
    recovered_amount: float | None = Field(default=None, ge=0)
    write_down_amount: float | None = Field(default=None, ge=0)
    status_timestamp: str
    source_refs: list[CarrierRejectionSourceRef]
    append_only: Literal[True] = True


class CarrierRejectionCaptureSourceBundle(StrictModel):
    schema_version: str = "0.1"
    bundle_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    data_origin: Literal["synthetic", "production"] = "synthetic"
    contains_real_client_data: bool = False
    contains_real_matter_data: bool = False
    contains_privileged_data: bool = False
    as_of: str
    expected_responses: list[CarrierExpectedResponse]
    notices: list[CarrierRejectionNotice] = Field(default_factory=list)
    appeal_results: list[CarrierAppealResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def synthetic_only(self) -> "CarrierRejectionCaptureSourceBundle":
        if self.data_origin != "synthetic":
            raise ValueError("carrier rejection capture is synthetic-only in this repo")
        if (
            self.contains_real_client_data
            or self.contains_real_matter_data
            or self.contains_privileged_data
        ):
            raise ValueError("real client, matter, or privileged data is prohibited")
        return self


class CarrierRejectionRemediationCase(StrictModel):
    remediation_case_id: str
    case_key: str
    status: Literal[
        "captured_for_human_review",
        "needs_linkage_review",
        "missing_response_followup",
        "parse_failed",
        "appeal_result_captured",
    ]
    local_event_label: str
    canonical_lake_class: Literal[
        "retrieval_miss",
        "workflow_escalation",
        "authority_conflict_override",
    ]
    carrier_id: str | None = None
    submission_id: str | None = None
    budget_proposal_id: str | None = None
    invoice_id: str | None = None
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    duplicate_notice_ids: list[str] = Field(default_factory=list)
    source_refs: list[CarrierRejectionSourceRef] = Field(default_factory=list)
    disputed_amount: float = Field(default=0, ge=0)
    current_financial_exposure: float = Field(default=0, ge=0)
    human_owner: str | None = None
    followup_due_at: str | None = None
    required_human_decisions: list[str] = Field(default_factory=list)
    linked_appeal_result_ids: list[str] = Field(default_factory=list)
    learning_disposition_candidates: list[str] = Field(default_factory=list)
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    silent_learning_performed: Literal[False] = False


class CarrierResponseReconciliationReport(StrictModel):
    schema_version: str = "0.1"
    reconciliation_report_id: str
    source_bundle_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: Literal[
        "dry_run_ready_for_review",
        "blocked_missing_required_followup",
        "no_rejections_or_missing_responses",
    ]
    expected_response_count: int = Field(ge=0)
    reconciled_response_count: int = Field(ge=0)
    missing_response_count: int = Field(ge=0)
    unlinked_notice_count: int = Field(ge=0)
    duplicate_notice_count: int = Field(ge=0)
    parser_failure_count: int = Field(ge=0)
    appeal_result_count: int = Field(ge=0)
    remediation_cases: list[CarrierRejectionRemediationCase]
    exception_lake_candidates: list[ExceptionLakeCandidate]
    gap_report: list[str] = Field(default_factory=list)
    capture_completeness_target_percent: Literal[100] = 100
    candidate_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    external_writes_performed: Literal[False] = False
    generated_at: str


class CarrierRejectionReviewRecommendation(StrictModel):
    recommendation_id: str
    remediation_case_id: str
    local_event_label: str
    recommended_action: Literal[
        "appeal_review_required",
        "confirm_missing_response_followup",
        "link_or_escalate_unlinked_notice",
        "parse_repair_required",
        "record_appeal_result",
        "human_decision_required",
    ]
    priority: Literal["critical", "high", "medium", "low"]
    human_owner: str | None = None
    followup_due_at: str | None = None
    financial_exposure: float = Field(default=0, ge=0)
    source_ref_count: int = Field(ge=0)
    source_channels: list[str] = Field(default_factory=list)
    why: list[str]
    required_human_decisions: list[str] = Field(default_factory=list)
    learning_disposition_candidates: list[str] = Field(default_factory=list)
    exception_candidate_ids: list[str] = Field(default_factory=list)
    not_authorized_for_external_submission: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True


class CarrierRejectionReviewRedTeamNote(StrictModel):
    note_id: str
    severity: Literal["critical", "high", "medium", "low"]
    scope: Literal[
        "capture_completeness",
        "idempotency",
        "linkage",
        "parser_failure",
        "financial_math",
        "human_authority",
        "learning_loop",
        "boundary",
    ]
    remediation_case_ids: list[str] = Field(default_factory=list)
    message: str
    recommended_check: str


class CarrierRejectionReviewDecisionTemplate(StrictModel):
    remediation_case_id: str
    allowed_outcomes: list[
        Literal[
            "confirm_classification",
            "correct_classification",
            "confirm_linkage",
            "correct_linkage",
            "needs_more_information",
            "appeal",
            "no_appeal",
            "accept_write_down",
            "fix_and_resubmit",
            "record_appeal_result",
            "human_only",
            "close_no_action",
            "create_learning_candidate",
            "no_learning_change",
        ]
    ]
    required_fields: list[str]
    mutation_policy: Literal["append_or_supersede_only"] = "append_or_supersede_only"
    external_submission_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False


class CarrierRejectionReviewPacket(StrictModel):
    schema_version: str = "0.1"
    review_packet_id: str
    reconciliation_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: Literal[
        "ready_for_human_review",
        "blocked_missing_required_followup",
        "no_cases_to_review",
    ]
    expected_response_count: int = Field(ge=0)
    reconciled_response_count: int = Field(ge=0)
    missing_response_count: int = Field(ge=0)
    unlinked_notice_count: int = Field(ge=0)
    duplicate_notice_count: int = Field(ge=0)
    parser_failure_count: int = Field(ge=0)
    appeal_result_count: int = Field(ge=0)
    remediation_case_count: int = Field(ge=0)
    total_financial_exposure: float = Field(ge=0)
    dry_run_exception_candidate_count: int = Field(ge=0)
    recommendations: list[CarrierRejectionReviewRecommendation]
    red_team_notes: list[CarrierRejectionReviewRedTeamNote]
    decision_templates: list[CarrierRejectionReviewDecisionTemplate]
    dry_run_exception_candidate_ids: list[str] = Field(default_factory=list)
    gap_report: list[str] = Field(default_factory=list)
    allowed_reviewer_outcomes: list[str]
    required_review_sections: list[str]
    human_readable_review_ref: str | None = None
    mutation_policy: Literal["append_or_supersede_only"] = "append_or_supersede_only"
    target_orchestrator_owner: Literal["LawFirm-os-orchestrator"] = "LawFirm-os-orchestrator"
    target_exception_lake_owner: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    candidate_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


class CarrierRejectionLearningProposal(StrictModel):
    proposal_id: str
    proposal_type: Literal[
        "timekeeper_rate_candidate",
        "guideline_profile_change_candidate",
        "eval_fixture_candidate",
        "validation_rule_candidate",
        "preapproval_gate_candidate",
        "staffing_rule_candidate",
        "narrative_rule_candidate",
        "template_mapping_candidate",
        "budget_driver_candidate",
        "variance_threshold_candidate",
        "guideline_version_review_candidate",
        "parser_rule_candidate",
        "reconciliation_rule_candidate",
        "capture_sla_candidate",
        "appeal_outcome_candidate",
    ]
    target_learning_loop: Literal[
        "guideline_drift",
        "budget_model",
        "template_mapping",
        "narrative_rule",
        "preapproval_gate",
        "appeal_success_or_failure",
        "capture_completeness",
        "parser_rule",
        "eval_fixture",
        "staffing_leverage",
        "timekeeper_rate",
        "validation_rule",
    ]
    target_owner: Literal[
        "LawFirm-os-intake",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
        "LawFirm-os-semantic-substrate",
    ]
    source_review_packet_id: str
    source_recommendation_ids: list[str]
    remediation_case_ids: list[str]
    local_event_labels: list[str]
    source_structured_refs: list[str]
    support_count: int = Field(ge=0)
    before_behavior: str
    proposed_candidate_behavior: str
    required_human_review_state: Literal["reviewed_outcome_required"] = "reviewed_outcome_required"
    required_evaluation: list[str]
    promotion_target_note: str
    status: Literal[
        "candidate_ready_for_human_review",
        "blocked_until_reviewed_outcome",
    ]
    synthetic_fixture_update_required: Literal[True] = True
    shadow_eval_required: Literal[True] = True
    human_review_required: Literal[True] = True
    promotion_review_required: Literal[True] = True
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False


class CarrierRejectionLearningReport(StrictModel):
    schema_version: str = "0.1"
    learning_report_id: str
    review_packet_id: str
    reconciliation_report_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: Literal[
        "candidate_learning_ready_for_review",
        "blocked_pending_human_review_packet",
        "no_learning_candidates",
    ]
    input_review_status: str
    proposal_count: int = Field(ge=0)
    proposals: list[CarrierRejectionLearningProposal]
    required_next_gates: list[str]
    target_owners: list[str]
    reviewed_outcome_required: Literal[True] = True
    append_only_outcome_required: Literal[True] = True
    candidate_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    external_writes_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


CarrierRejectionDecisionLedgerEventKind = Literal[
    "carrier_rejection_notice_captured",
    "carrier_response_missing_after_sla",
    "carrier_rejection_unlinked_notice",
    "carrier_rejection_parse_failed",
    "carrier_duplicate_notice_collapsed",
    "carrier_fix_or_appeal_decision_pending",
    "carrier_appeal_result_received",
    "carrier_financial_outcome_recorded",
]

CarrierRejectionDecisionLedgerStatus = Literal[
    "decision_ledger_ready_for_review",
    "decision_ledger_blocked_missing_followup",
    "decision_ledger_no_events",
]

CarrierRejectionDecisionStatus = Literal[
    "captured_pending_human_review",
    "pending_human_fix_or_appeal_decision",
    "appeal_result_captured_pending_review",
    "financial_outcome_captured_pending_review",
    "blocked_missing_response_followup",
    "blocked_linkage_or_parse_review",
]


class CarrierRejectionDecisionLedgerEvent(StrictModel):
    schema_version: str = "0.1"
    decision_ledger_event_id: str
    decision_ledger_id: str
    sequence_index: int = Field(ge=0)
    reconciliation_report_id: str
    source_bundle_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    remediation_case_id: str | None = None
    appeal_result_id: str | None = None
    notice_ids: list[str] = Field(default_factory=list)
    carrier_id: str | None = None
    submission_id: str | None = None
    invoice_id: str | None = None
    phase_id: str | None = None
    task_id: str | None = None
    external_code_candidate: str | None = None
    event_kind: CarrierRejectionDecisionLedgerEventKind
    decision_status: CarrierRejectionDecisionStatus
    local_event_label: str
    canonical_lake_class_candidate: Literal[
        "retrieval_miss",
        "workflow_escalation",
        "authority_conflict_override",
    ]
    source_channels: list[str] = Field(default_factory=list)
    source_refs: list[CarrierRejectionSourceRef] = Field(default_factory=list)
    response_type: str | None = None
    appeal_result: str | None = None
    disputed_amount: float = Field(default=0, ge=0)
    current_financial_exposure: float = Field(default=0, ge=0)
    appealed_amount: float = Field(default=0, ge=0)
    recovered_amount: float = Field(default=0, ge=0)
    write_down_amount: float = Field(default=0, ge=0)
    remaining_write_down_amount: float = Field(default=0, ge=0)
    proposed_next_actions: list[str] = Field(default_factory=list)
    required_human_decisions: list[str] = Field(default_factory=list)
    exception_candidate_ids: list[str] = Field(default_factory=list)
    structured_refs: list[str] = Field(default_factory=list)
    requires_exception_lake_admission_review: Literal[True] = True
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def appeal_events_require_appeal_id(self) -> "CarrierRejectionDecisionLedgerEvent":
        if (
            self.event_kind
            in {
                "carrier_appeal_result_received",
                "carrier_financial_outcome_recorded",
            }
            and not self.appeal_result_id
        ):
            raise ValueError("carrier appeal ledger events require appeal_result_id")
        return self


class CarrierRejectionDecisionLedgerReport(StrictModel):
    schema_version: str = "0.1"
    decision_ledger_report_id: str
    decision_ledger_id: str
    reconciliation_report_id: str
    source_bundle_id: str
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    status: CarrierRejectionDecisionLedgerStatus
    entry_count: int = Field(ge=0)
    remediation_case_event_count: int = Field(ge=0)
    pending_decision_event_count: int = Field(ge=0)
    appeal_result_event_count: int = Field(ge=0)
    financial_outcome_event_count: int = Field(ge=0)
    total_disputed_amount: float = Field(default=0, ge=0)
    total_recovered_amount: float = Field(default=0, ge=0)
    total_write_down_amount: float = Field(default=0, ge=0)
    event_kind_counts: dict[str, int] = Field(default_factory=dict)
    events: list[CarrierRejectionDecisionLedgerEvent]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def counts_match_events(self) -> "CarrierRejectionDecisionLedgerReport":
        if self.entry_count != len(self.events):
            raise ValueError("carrier rejection decision ledger count must match events")
        kind_counts: dict[str, int] = {}
        for event in self.events:
            kind_counts[event.event_kind] = kind_counts.get(event.event_kind, 0) + 1
        if self.event_kind_counts != kind_counts:
            raise ValueError("carrier rejection decision ledger kind counts must match events")
        if self.appeal_result_event_count != kind_counts.get("carrier_appeal_result_received", 0):
            raise ValueError("carrier rejection appeal result count must match events")
        if self.financial_outcome_event_count != kind_counts.get(
            "carrier_financial_outcome_recorded", 0
        ):
            raise ValueError("carrier rejection financial outcome count must match events")
        if self.pending_decision_event_count != kind_counts.get(
            "carrier_fix_or_appeal_decision_pending", 0
        ):
            raise ValueError("carrier rejection pending decision count must match events")
        if self.status != "decision_ledger_no_events" and not self.events:
            raise ValueError("carrier rejection decision ledger requires events")
        return self


LearningLoopId = Literal[
    "guideline_drift",
    "budget_model",
    "template_mapping",
    "narrative_rule",
    "preapproval_gate",
    "appeal_success_or_failure",
    "capture_completeness",
    "parser_rule",
    "eval_fixture",
    "staffing_leverage",
    "timekeeper_rate",
    "validation_rule",
]

LearningTargetOwner = Literal[
    "LawFirm-os-intake",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-semantic-substrate",
]


class ReviewedLearningGateCandidate(StrictModel):
    candidate_id: str
    source_kind: Literal[
        "carrier_rejection_learning_proposal",
        "budget_revision_delta",
        "budget_actual_variance_driver",
    ]
    source_artifact_ref: str
    source_record_id: str
    source_status: str | None = None
    target_learning_loop: LearningLoopId
    target_owner: LearningTargetOwner
    trigger_summary: str
    before_behavior: str
    proposed_candidate_behavior: str
    support_refs: list[str]
    support_count: int = Field(ge=0)
    required_evidence: list[str]
    required_evaluation: list[str]
    required_next_gates: list[str]
    status: Literal["blocked_until_reviewed_learning_gate"] = "blocked_until_reviewed_learning_gate"
    human_review_required: Literal[True] = True
    synthetic_fixture_update_required: Literal[True] = True
    shadow_eval_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    append_only_evidence_required: Literal[True] = True
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def support_and_gates_required(self) -> "ReviewedLearningGateCandidate":
        if not self.support_refs:
            raise ValueError("reviewed learning candidate requires support_refs")
        required = {
            "human_reviewed_outcome_evidence",
            "append_only_evidence_record",
            "synthetic_fixture_update",
            "shadow_eval",
            "owning_repo_review",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("reviewed learning candidate is missing required gates")
        return self


class ReviewedLearningGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)


class ReviewedLearningGateReport(StrictModel):
    schema_version: str = "0.1"
    reviewed_learning_gate_report_id: str
    run_id: str
    status: Literal[
        "candidate_learning_gate_ready",
        "no_learning_candidates",
        "failed",
    ]
    source_report_refs: list[str]
    carrier_rejection_learning_report_ref: str | None = None
    budget_revision_report_ref: str | None = None
    budget_actual_comparison_report_ref: str | None = None
    candidate_count: int = Field(ge=0)
    carrier_learning_candidate_count: int = Field(ge=0)
    budget_revision_candidate_count: int = Field(ge=0)
    budget_actual_variance_candidate_count: int = Field(ge=0)
    target_learning_loops: list[str]
    target_owners: list[str]
    candidates: list[ReviewedLearningGateCandidate]
    checks: list[ReviewedLearningGateCheck]
    required_next_gates: list[str]
    reviewed_outcome_required: Literal[True] = True
    append_only_evidence_required: Literal[True] = True
    synthetic_fixture_update_required: Literal[True] = True
    shadow_eval_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_external_submission: Literal[True] = True
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


class LearningShadowEvalCase(StrictModel):
    shadow_eval_case_id: str
    candidate_id: str
    source_kind: Literal[
        "carrier_rejection_learning_proposal",
        "budget_revision_delta",
        "budget_actual_variance_driver",
    ]
    target_learning_loop: LearningLoopId
    target_owner: LearningTargetOwner
    source_artifact_ref: str
    source_record_id: str
    support_refs: list[str]
    required_fixture_updates: list[str]
    required_eval_suites: list[str]
    regression_guardrails: list[str]
    proposed_change_ref: str | None = None
    shadow_eval_result_ref: str | None = None
    status: Literal[
        "blocked_missing_proposed_change",
        "blocked_missing_fixture_update",
        "blocked_missing_shadow_eval_result",
    ] = "blocked_missing_proposed_change"
    candidate_only: Literal[True] = True
    proposed_change_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def eval_requirements_present(self) -> "LearningShadowEvalCase":
        if not self.required_fixture_updates:
            raise ValueError("shadow eval case requires fixture update requirements")
        if not self.required_eval_suites:
            raise ValueError("shadow eval case requires eval suites")
        if not self.regression_guardrails:
            raise ValueError("shadow eval case requires regression guardrails")
        if not self.support_refs:
            raise ValueError("shadow eval case requires support refs")
        return self


class LearningShadowEvalPlan(StrictModel):
    schema_version: str = "0.1"
    shadow_eval_plan_id: str
    reviewed_learning_gate_report_id: str
    status: Literal[
        "shadow_eval_required",
        "no_learning_candidates",
        "failed",
    ]
    source_gate_report_ref: str
    case_count: int = Field(ge=0)
    cases: list[LearningShadowEvalCase]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


class LearningPromotionReadinessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    candidate_ids: list[str] = Field(default_factory=list)


class LearningPromotionReadinessReport(StrictModel):
    schema_version: str = "0.1"
    promotion_readiness_report_id: str
    reviewed_learning_gate_report_id: str
    shadow_eval_plan_id: str
    status: Literal[
        "promotion_blocked_shadow_eval_required",
        "no_learning_candidates",
        "failed",
    ]
    source_gate_report_ref: str
    shadow_eval_plan_ref: str
    candidate_count: int = Field(ge=0)
    blocked_candidate_count: int = Field(ge=0)
    ready_candidate_count: int = Field(default=0, ge=0)
    target_learning_loops: list[str]
    target_owners: list[str]
    checks: list[LearningPromotionReadinessCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    promotion_authorized: Literal[False] = False
    owning_repo_review_required: Literal[True] = True
    semantic_substrate_promotion_required_for_canon: Literal[True] = True
    orchestrator_runtime_review_required: Literal[True] = True
    exception_lake_admission_required: Literal[True] = True
    proposed_changes_applied: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str


LearningProposedChangeType = Literal[
    "guideline_profile_candidate",
    "budget_driver_adjustment_candidate",
    "template_mapping_candidate",
    "narrative_rule_candidate",
    "preapproval_gate_candidate",
    "appeal_outcome_pattern_candidate",
    "capture_reconciliation_rule_candidate",
    "parser_rule_candidate",
    "eval_fixture_candidate",
    "staffing_leverage_candidate",
    "timekeeper_rate_candidate",
    "validation_rule_candidate",
]


class LearningProposedChangeRedTeamNote(StrictModel):
    note_id: str
    severity: Literal["low", "medium", "high"]
    risk_area: Literal[
        "evidence",
        "math",
        "authority",
        "generalization",
        "data_scope",
        "carrier_guideline",
        "workflow",
    ]
    objection: str
    required_check: str
    status: Literal["open_for_human_review"] = "open_for_human_review"


class LearningProposedChangeArtifact(StrictModel):
    schema_version: str = "0.1"
    proposed_change_id: str
    reviewed_learning_gate_report_id: str
    shadow_eval_plan_id: str
    shadow_eval_case_id: str
    promotion_readiness_report_id: str | None = None
    candidate_id: str
    source_kind: Literal[
        "carrier_rejection_learning_proposal",
        "budget_revision_delta",
        "budget_actual_variance_driver",
    ]
    target_learning_loop: LearningLoopId
    target_owner: LearningTargetOwner
    change_type: LearningProposedChangeType
    source_artifact_ref: str
    source_record_id: str
    support_refs: list[str]
    affected_candidate_refs: list[str]
    proposal_title: str
    proposed_behavior_summary: str
    recommendation: Literal[
        "draft_for_human_review",
        "needs_more_evidence",
        "hold_for_owning_repo",
    ] = "draft_for_human_review"
    recommendation_rationale: list[str]
    red_team_notes: list[LearningProposedChangeRedTeamNote]
    required_fixture_updates: list[str]
    required_eval_suites: list[str]
    regression_guardrails: list[str]
    required_next_gates: list[str]
    status: Literal["draft_candidate_not_applied"] = "draft_candidate_not_applied"
    human_review_status: Literal["pending_human_review"] = "pending_human_review"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    proposed_change_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def support_review_and_boundaries_required(self) -> "LearningProposedChangeArtifact":
        if not self.support_refs:
            raise ValueError("proposed learning change requires support refs")
        if not self.recommendation_rationale:
            raise ValueError("proposed learning change requires recommendation rationale")
        if not self.red_team_notes:
            raise ValueError("proposed learning change requires red-team notes")
        required = {
            "human_reviewed_outcome_evidence",
            "append_only_evidence_record",
            "proposed_change_artifact",
            "synthetic_fixture_update",
            "shadow_eval_result",
            "regression_check",
            "owning_repo_review",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("proposed learning change is missing required gates")
        if self.candidate_id not in self.affected_candidate_refs:
            raise ValueError("proposed learning change must reference its source candidate")
        return self


class LearningProposedChangeSet(StrictModel):
    schema_version: str = "0.1"
    proposed_change_set_id: str
    reviewed_learning_gate_report_id: str
    shadow_eval_plan_id: str
    promotion_readiness_report_id: str | None = None
    status: Literal[
        "draft_candidates_ready_for_human_review",
        "no_learning_candidates",
        "failed",
    ]
    source_shadow_eval_plan_ref: str
    source_promotion_readiness_report_ref: str | None = None
    change_count: int = Field(ge=0)
    target_learning_loops: list[str]
    target_owners: list[str]
    changes: list[LearningProposedChangeArtifact]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def change_count_matches_status(self) -> "LearningProposedChangeSet":
        if self.change_count != len(self.changes):
            raise ValueError("proposed learning change set count must match changes")
        if self.status == "no_learning_candidates" and self.changes:
            raise ValueError("no-candidate change set cannot include changes")
        if self.status == "draft_candidates_ready_for_human_review" and not self.changes:
            raise ValueError("draft change set requires at least one change")
        return self


class LearningShadowEvalFixtureResult(StrictModel):
    schema_version: str = "0.1"
    fixture_result_id: str
    proposed_change_id: str
    candidate_id: str
    baseline_behavior_ref: str
    proposed_behavior_ref: str
    baseline_output_hash: str
    proposed_output_hash: str
    expected_behavior_summary: str
    observed_behavior_summary: str
    evaluation_outcome: Literal["passed", "failed", "blocked"]
    passed_eval_suites: list[str]
    failed_eval_suites: list[str] = Field(default_factory=list)
    passed_regression_guardrails: list[str]
    failed_regression_guardrails: list[str] = Field(default_factory=list)
    support_refs: list[str]
    synthetic_only: Literal[True] = True
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    proposed_change_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def fixture_support_required(self) -> "LearningShadowEvalFixtureResult":
        if not self.support_refs:
            raise ValueError("shadow eval fixture result requires support refs")
        if self.evaluation_outcome == "passed":
            if not self.passed_eval_suites:
                raise ValueError("passed shadow eval fixture requires passed eval suites")
            if not self.passed_regression_guardrails:
                raise ValueError("passed shadow eval fixture requires passed guardrails")
            if self.failed_eval_suites or self.failed_regression_guardrails:
                raise ValueError("passed shadow eval fixture cannot include failed checks")
        return self


class LearningShadowEvalResult(StrictModel):
    schema_version: str = "0.1"
    shadow_eval_result_id: str
    proposed_change_set_id: str
    proposed_change_id: str
    candidate_id: str
    target_learning_loop: LearningLoopId
    target_owner: LearningTargetOwner
    change_type: LearningProposedChangeType
    status: Literal[
        "passed_for_owning_repo_review",
        "failed_shadow_eval",
        "blocked_missing_fixture_result",
        "blocked_missing_required_eval",
        "blocked_missing_regression_guardrail",
        "blocked_fixture_mismatch",
    ]
    fixture_result_ref: str | None = None
    fixture_result_id: str | None = None
    baseline_behavior_ref: str | None = None
    proposed_behavior_ref: str | None = None
    baseline_output_hash: str | None = None
    proposed_output_hash: str | None = None
    passed_checks: list[str]
    failed_checks: list[str]
    blocked_checks: list[str]
    red_team_note_count: int = Field(ge=0)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    promotion_authorized: Literal[False] = False
    proposed_change_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def result_checks_match_status(self) -> "LearningShadowEvalResult":
        if self.status == "passed_for_owning_repo_review":
            if self.failed_checks or self.blocked_checks:
                raise ValueError(
                    "passed shadow eval result cannot include failed or blocked checks"
                )
            if not self.fixture_result_id:
                raise ValueError("passed shadow eval result requires a fixture result")
        if self.status.startswith("blocked") and not self.blocked_checks:
            raise ValueError("blocked shadow eval result requires blocked checks")
        if self.status == "failed_shadow_eval" and not self.failed_checks:
            raise ValueError("failed shadow eval result requires failed checks")
        return self


class LearningShadowEvalResultReport(StrictModel):
    schema_version: str = "0.1"
    shadow_eval_result_report_id: str
    proposed_change_set_id: str
    status: Literal[
        "shadow_eval_passed_owner_review_required",
        "shadow_eval_blocked",
        "shadow_eval_failed",
        "no_learning_candidates",
    ]
    source_proposed_change_set_ref: str
    fixture_result_refs: list[str]
    change_count: int = Field(ge=0)
    result_count: int = Field(ge=0)
    passed_result_count: int = Field(ge=0)
    failed_result_count: int = Field(ge=0)
    blocked_result_count: int = Field(ge=0)
    target_learning_loops: list[str]
    target_owners: list[str]
    results: list[LearningShadowEvalResult]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    connector_mutation_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def result_counts_match(self) -> "LearningShadowEvalResultReport":
        if self.result_count != len(self.results):
            raise ValueError("shadow eval result report count must match results")
        if self.change_count != self.result_count:
            raise ValueError("shadow eval result report requires one result per change")
        counted_passed = sum(
            1 for result in self.results if result.status == "passed_for_owning_repo_review"
        )
        counted_failed = sum(1 for result in self.results if result.status == "failed_shadow_eval")
        counted_blocked = self.result_count - counted_passed - counted_failed
        if (
            self.passed_result_count != counted_passed
            or self.failed_result_count != counted_failed
            or self.blocked_result_count != counted_blocked
        ):
            raise ValueError("shadow eval result report aggregate counts do not match")
        if self.status == "no_learning_candidates" and self.results:
            raise ValueError("no-candidate shadow eval report cannot include results")
        return self


LearningOwnerHandoffDisposition = Literal[
    "ready_for_owner_review",
    "failed_before_owner_review",
    "blocked_before_owner_review",
]


class LearningOwnerHandoffItem(StrictModel):
    schema_version: str = "0.1"
    handoff_item_id: str
    shadow_eval_result_id: str
    proposed_change_id: str
    candidate_id: str
    target_learning_loop: LearningLoopId
    target_owner: LearningTargetOwner
    change_type: LearningProposedChangeType
    shadow_eval_status: Literal[
        "passed_for_owning_repo_review",
        "failed_shadow_eval",
        "blocked_missing_fixture_result",
        "blocked_missing_required_eval",
        "blocked_missing_regression_guardrail",
        "blocked_fixture_mismatch",
    ]
    disposition: LearningOwnerHandoffDisposition
    passed_checks: list[str]
    failed_checks: list[str]
    blocked_checks: list[str]
    required_owner_actions: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    promotion_authorized: Literal[False] = False
    proposed_change_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def disposition_matches_status(self) -> "LearningOwnerHandoffItem":
        if (
            self.shadow_eval_status == "passed_for_owning_repo_review"
            and self.disposition != "ready_for_owner_review"
        ):
            raise ValueError("passed shadow eval item must be ready for owner review")
        if (
            self.shadow_eval_status == "failed_shadow_eval"
            and self.disposition != "failed_before_owner_review"
        ):
            raise ValueError("failed shadow eval item must stay failed before owner review")
        if self.shadow_eval_status.startswith("blocked") and self.disposition != (
            "blocked_before_owner_review"
        ):
            raise ValueError("blocked shadow eval item must stay blocked before owner review")
        if not self.required_owner_actions:
            raise ValueError("owner handoff item requires owner actions")
        return self


class LearningOwnerHandoffPackage(StrictModel):
    schema_version: str = "0.1"
    owner_handoff_package_id: str
    target_owner: LearningTargetOwner
    source_shadow_eval_result_report_id: str
    status: Literal[
        "ready_for_owner_review",
        "mixed_review_and_blockers",
        "blocked_or_failed_before_review",
    ]
    item_count: int = Field(ge=0)
    passed_candidate_count: int = Field(ge=0)
    failed_candidate_count: int = Field(ge=0)
    blocked_candidate_count: int = Field(ge=0)
    ready_items: list[LearningOwnerHandoffItem]
    failed_items: list[LearningOwnerHandoffItem]
    blocked_items: list[LearningOwnerHandoffItem]
    required_owner_review_scope: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def package_counts_match(self) -> "LearningOwnerHandoffPackage":
        if self.item_count != (
            len(self.ready_items) + len(self.failed_items) + len(self.blocked_items)
        ):
            raise ValueError("owner handoff package item count does not match items")
        if self.passed_candidate_count != len(self.ready_items):
            raise ValueError("owner handoff package passed count does not match")
        if self.failed_candidate_count != len(self.failed_items):
            raise ValueError("owner handoff package failed count does not match")
        if self.blocked_candidate_count != len(self.blocked_items):
            raise ValueError("owner handoff package blocked count does not match")
        if self.status == "ready_for_owner_review" and (
            self.failed_items or self.blocked_items or not self.ready_items
        ):
            raise ValueError("ready owner handoff package must contain only ready items")
        if self.status == "mixed_review_and_blockers" and not (
            self.ready_items and (self.failed_items or self.blocked_items)
        ):
            raise ValueError("mixed owner handoff package requires ready and blocked/failed items")
        if self.status == "blocked_or_failed_before_review" and self.ready_items:
            raise ValueError("blocked/failed owner handoff package cannot contain ready items")
        return self


class LearningOwnerHandoffReport(StrictModel):
    schema_version: str = "0.1"
    owner_handoff_report_id: str
    source_shadow_eval_result_report_id: str
    source_shadow_eval_result_report_ref: str
    status: Literal[
        "owner_handoff_ready_review_required",
        "owner_handoff_mixed_review_and_blockers",
        "owner_handoff_blocked_or_failed",
        "no_learning_candidates",
    ]
    package_count: int = Field(ge=0)
    target_owners: list[str]
    passed_candidate_count: int = Field(ge=0)
    failed_candidate_count: int = Field(ge=0)
    blocked_candidate_count: int = Field(ge=0)
    packages: list[LearningOwnerHandoffPackage]
    package_output_refs: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def report_counts_match(self) -> "LearningOwnerHandoffReport":
        if self.package_count != len(self.packages):
            raise ValueError("owner handoff report package count does not match")
        if self.passed_candidate_count != sum(
            package.passed_candidate_count for package in self.packages
        ):
            raise ValueError("owner handoff report passed count does not match")
        if self.failed_candidate_count != sum(
            package.failed_candidate_count for package in self.packages
        ):
            raise ValueError("owner handoff report failed count does not match")
        if self.blocked_candidate_count != sum(
            package.blocked_candidate_count for package in self.packages
        ):
            raise ValueError("owner handoff report blocked count does not match")
        if self.status == "no_learning_candidates" and self.packages:
            raise ValueError("no-candidate owner handoff report cannot include packages")
        if self.status == "owner_handoff_ready_review_required" and (
            self.failed_candidate_count or self.blocked_candidate_count
        ):
            raise ValueError("ready owner handoff report cannot include failed/blocked counts")
        return self


class IntakeVerticalReadinessSliceStatus(StrictModel):
    slice_id: int = Field(ge=1)
    title: str
    status: Literal["implemented_local_candidate", "missing_required_artifact"]
    requirement_summary: str
    proof_artifact_refs: list[str]
    missing_artifact_refs: list[str] = Field(default_factory=list)
    command_refs: list[str] = Field(default_factory=list)
    missing_command_refs: list[str] = Field(default_factory=list)
    target_owner_repos: list[LearningTargetOwner]
    remaining_external_actions: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class IntakeVerticalReadinessArtifactCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    artifact_ref: str | None = None
    message: str
    missing_refs: list[str] = Field(default_factory=list)


class IntakeVerticalReadinessAuditReport(StrictModel):
    schema_version: str = "0.1"
    audit_report_id: str
    status: Literal[
        "ready_for_pr_review_external_adoption_required",
        "incomplete_missing_local_artifacts",
        "blocked_missing_or_failed_learning_artifacts",
    ]
    review_readiness: Literal[
        "ready_for_human_pr_review_not_auto_marked",
        "not_ready_missing_local_artifacts",
        "not_ready_learning_artifact_chain_blocked",
    ]
    source_owner_handoff_report_ref: str
    total_slice_count: int = Field(ge=0)
    implemented_slice_count: int = Field(ge=0)
    missing_artifact_refs: list[str] = Field(default_factory=list)
    missing_command_refs: list[str] = Field(default_factory=list)
    slices: list[IntakeVerticalReadinessSliceStatus]
    artifact_checks: list[IntakeVerticalReadinessArtifactCheck]
    required_external_adoption_actions: list[str]
    external_adoption_target_repos: list[LearningTargetOwner]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_completion_scope: Literal["synthetic_candidate_only"] = "synthetic_candidate_only"
    pr_marked_ready: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    baseline_mutated: Literal[False] = False
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    sqlite_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def readiness_counts_match(self) -> "IntakeVerticalReadinessAuditReport":
        if self.total_slice_count != len(self.slices):
            raise ValueError("intake vertical readiness slice count does not match")
        if self.implemented_slice_count != sum(
            1 for item in self.slices if item.status == "implemented_local_candidate"
        ):
            raise ValueError("intake vertical readiness implemented count does not match")
        if self.status == "ready_for_pr_review_external_adoption_required":
            if self.missing_artifact_refs or self.missing_command_refs:
                raise ValueError("ready readiness audit cannot include missing refs")
            if any(check.status == "failed" for check in self.artifact_checks):
                raise ValueError("ready readiness audit cannot include failed artifact checks")
        return self


class CarrierRejectionOrchestratorConnectorChannel(StrictModel):
    channel_id: Literal[
        "carrier_portal_notice",
        "email_rejection_notice",
        "ledes_response_file",
        "returned_budget_workbook",
        "appeal_correspondence",
        "manual_human_entry",
    ]
    connector_owner: Literal["LawFirm-os-orchestrator"] = "LawFirm-os-orchestrator"
    side_effect_class: Literal[
        "read_capture_only",
        "human_entered_record",
    ]
    produces_candidate_artifacts: list[
        Literal[
            "CarrierRejectionNotice",
            "CarrierAppealResult",
            "CarrierRejectionSourceRef",
        ]
    ]
    required_identifiers: list[str]
    required_source_metadata: list[str]
    raw_payload_storage_allowed: Literal[False] = False
    intake_connector_implementation_allowed: Literal[False] = False


class CarrierRejectionOrchestratorWorkflowStep(StrictModel):
    step_id: str
    owner_repo: Literal[
        "LawFirm-os-orchestrator",
        "LawFirm-os-intake",
        "LawFirm-os-exceptions-lake-runtime",
    ]
    action: str
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    required_human_gate: str | None = None
    failure_exception_labels: list[str] = Field(default_factory=list)
    external_write_allowed: bool = False
    intake_runtime_authority: Literal[
        "reference_eval_only",
        "dry_run_candidate_only",
        "none",
    ] = "none"


class CarrierRejectionOrchestratorInterfaceDraft(StrictModel):
    schema_version: str = "0.1"
    interface_id: str
    status: Literal["candidate_only"]
    origin_repo: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    target_repo: Literal["LawFirm-os-orchestrator"] = "LawFirm-os-orchestrator"
    purpose: str
    response_state_ledger_required: Literal[True] = True
    deterministic_reconciliation_required: Literal[True] = True
    connector_channels: list[CarrierRejectionOrchestratorConnectorChannel]
    workflow_steps: list[CarrierRejectionOrchestratorWorkflowStep]
    required_human_pause_points: list[str]
    required_intake_reference_commands: list[str]
    expected_intake_outputs: list[str]
    expected_lake_handoff_candidates: list[str]
    prohibited_intake_actions: list[str]
    proposed_contract_refs: list[str]
    promotion_blockers: list[str]
    no_route_ids_assigned: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_external_writes_performed: Literal[True] = True
    no_lake_write_performed: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    human_approval_required_for_external_writes: Literal[True] = True
    generated_at: str


class CarrierRejectionLakeAdmissionRecordSpec(StrictModel):
    record_type: Literal[
        "carrier_rejection_notice_record",
        "carrier_rejection_reconciliation_record",
        "carrier_rejection_review_outcome_record",
        "carrier_appeal_submission_record",
        "carrier_appeal_result_record",
        "carrier_financial_outcome_record",
        "carrier_rejection_learning_candidate_record",
    ]
    proposed_sqlite_table: str
    local_event_labels: list[str]
    canonical_lake_class_candidates: list[
        Literal[
            "retrieval_miss",
            "workflow_escalation",
            "authority_conflict_override",
        ]
    ]
    source_artifact_refs: list[str]
    required_identifiers: list[str]
    idempotency_fields: list[str]
    required_hash_fields: list[str]
    required_human_review_fields: list[str] = Field(default_factory=list)
    correction_policy: Literal["append_only_supersession"] = "append_only_supersession"
    raw_payload_storage_allowed: Literal[False] = False
    admitted_by_intake: Literal[False] = False
    requires_orchestrator_evidence_packet: Literal[True] = True
    requires_lake_record_hash: Literal[True] = True


class CarrierRejectionLakeAdmissionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    record_types: list[str] = Field(default_factory=list)


class CarrierRejectionLakeAdmissionProposal(StrictModel):
    schema_version: str = "0.1"
    proposal_id: str
    status: Literal["candidate_only"]
    origin_repo: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    target_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    admission_state: Literal["proposal_not_admitted"] = "proposal_not_admitted"
    purpose: str
    record_specs: list[CarrierRejectionLakeAdmissionRecordSpec]
    checks: list[CarrierRejectionLakeAdmissionCheck]
    required_upstream_artifacts: list[str]
    proposed_contract_refs: list[str]
    promotion_blockers: list[str]
    prohibited_intake_actions: list[str]
    append_only_required: Literal[True] = True
    correction_supersession_required: Literal[True] = True
    record_hash_required: Literal[True] = True
    sqlite_owner: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    sqlite_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    raw_payload_storage_allowed: Literal[False] = False
    no_canonical_mutation: Literal[True] = True
    generated_at: str


class CarrierRejectionRoadmapSliceStatus(StrictModel):
    slice_id: int = Field(ge=1, le=8)
    title: str
    status: Literal["implemented_local_candidate", "missing_required_artifact"]
    requirement_summary: str
    proof_artifact_refs: list[str]
    missing_artifact_refs: list[str] = Field(default_factory=list)
    command_refs: list[str] = Field(default_factory=list)
    missing_command_refs: list[str] = Field(default_factory=list)
    local_authority_scope: Literal["synthetic_candidate_only"] = "synthetic_candidate_only"
    runtime_owner_repo: Literal[
        "LawFirm-os-intake",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
        "LawFirm-os-semantic-substrate",
    ]
    remaining_external_actions: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True


class CarrierRejectionRoadmapAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    missing_refs: list[str] = Field(default_factory=list)


class CarrierRejectionRoadmapAuditReport(StrictModel):
    schema_version: str = "0.1"
    audit_report_id: str
    status: Literal[
        "local_candidate_complete_external_adoption_required",
        "incomplete_missing_local_artifacts",
    ]
    local_completion_scope: Literal["synthetic_candidate_only"] = "synthetic_candidate_only"
    total_slice_count: int = Field(ge=0)
    implemented_slice_count: int = Field(ge=0)
    missing_artifact_refs: list[str] = Field(default_factory=list)
    missing_command_refs: list[str] = Field(default_factory=list)
    slices: list[CarrierRejectionRoadmapSliceStatus]
    checks: list[CarrierRejectionRoadmapAuditCheck]
    required_external_adoption_actions: list[str]
    external_adoption_target_repos: list[
        Literal[
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
            "LawFirm-os-semantic-substrate",
        ]
    ]
    review_readiness: Literal[
        "ready_for_intake_pr_review",
        "not_ready_missing_local_artifacts",
    ]
    candidate_only: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    sqlite_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    generated_at: str


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
        "carrier_preapproval_required",
        "human_budget_change",
        "budget_actual_cost_variance",
        "carrier_rejection_capture",
        "carrier_rejection_reconciliation",
        "carrier_rejection_appeal_result",
        "carrier_rejection_learning",
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
            "budget_revision_report",
            "budget_actual_comparison_report",
            "carrier_preapproval_report",
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
            "carrier_appeal_result",
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
