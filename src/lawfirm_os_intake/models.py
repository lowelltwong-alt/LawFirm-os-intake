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


class CourtListenerDatasetStrategyCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class CourtListenerDatasetStrategyReport(StrictModel):
    schema_version: str = "0.1"
    courtlistener_dataset_strategy_report_id: str
    status: Literal[
        "ready_for_human_dataset_strategy_review",
        "blocked_courtlistener_dataset_strategy",
    ]
    strategy_config_ref: str
    rust_transition_policy_ref: str
    source_id: str
    base_url: str
    token_env_var: str
    offline_fixture_mode: bool
    allow_live_calls: bool
    endpoint_paths: list[str]
    primary_practice_area: Literal["labor_employment"]
    starter_matter_families: list[str]
    positive_document_types: list[str]
    excluded_positive_document_types: list[str]
    negative_case_stage_labels: list[str]
    source_profile_ids: list[str]
    rust_shadow_scope: list[str]
    rust_forbidden_scope: list[str]
    required_rust_gates: list[str]
    checks: list[CourtListenerDatasetStrategyCheck]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    public_records_ingested: Literal[False] = False
    public_payload_committed: Literal[False] = False
    live_calls_performed: Literal[False] = False
    pacer_purchase_allowed: bool
    recap_fetch_purchase_allowed: bool
    uploads_allowed: bool
    court_writes_allowed: bool
    sealed_or_restricted_requests_allowed: bool
    real_client_data_allowed: bool
    privileged_data_allowed: bool
    connector_implemented: Literal[False] = False
    rust_runtime_added: Literal[False] = False
    rust_replacement_allowed: Literal[False] = False
    budget_accuracy_claimed: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def dataset_strategy_status_matches_checks(self) -> "CourtListenerDatasetStrategyReport":
        if not self.checks:
            raise ValueError("courtlistener dataset strategy report requires checks")
        failed = [check.check_id for check in self.checks if check.status == "failed"]
        if self.status == "ready_for_human_dataset_strategy_review" and failed:
            raise ValueError("ready courtlistener dataset strategy cannot include failed checks")
        if self.status == "ready_for_human_dataset_strategy_review":
            unsafe = [
                self.allow_live_calls,
                self.pacer_purchase_allowed,
                self.recap_fetch_purchase_allowed,
                self.uploads_allowed,
                self.court_writes_allowed,
                self.sealed_or_restricted_requests_allowed,
                self.real_client_data_allowed,
                self.privileged_data_allowed,
            ]
            if self.offline_fixture_mode is not True or any(unsafe):
                raise ValueError("ready courtlistener dataset strategy has unsafe source mode")
        if self.status == "blocked_courtlistener_dataset_strategy" and not failed:
            raise ValueError("blocked courtlistener dataset strategy requires failed checks")
        if not self.endpoint_paths:
            raise ValueError("courtlistener dataset strategy requires endpoint paths")
        if "courtlistener_removal_state_pleadings_proxy" not in self.source_profile_ids:
            raise ValueError("courtlistener removal proxy profile is required")
        return self


class CourtListenerSnapshotSegment(StrictModel):
    segment_id: str
    source_document_id: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    sha256: str
    text: str

    @model_validator(mode="after")
    def segment_offsets_match_text(self) -> "CourtListenerSnapshotSegment":
        if self.end_offset <= self.start_offset:
            raise ValueError("courtlistener snapshot segment end offset must exceed start offset")
        if self.end_offset - self.start_offset != len(self.text):
            raise ValueError("courtlistener snapshot segment offsets must match text length")
        return self


class CourtListenerSnapshotDocument(StrictModel):
    source_document_id: str
    document_type: str
    case_stage: str
    source_role: str
    filed_day: int = Field(ge=0)
    source_access_mode: Literal["offline_fixture"]
    sha256: str
    segments: list[CourtListenerSnapshotSegment]

    @model_validator(mode="after")
    def snapshot_document_segments_required(self) -> "CourtListenerSnapshotDocument":
        if not self.segments:
            raise ValueError("courtlistener snapshot document requires at least one segment")
        if any(segment.source_document_id != self.source_document_id for segment in self.segments):
            raise ValueError("courtlistener snapshot segment document id drift")
        return self


class CourtListenerDocketEntry(StrictModel):
    docket_entry_id: str
    entry_number: int = Field(ge=1)
    filed_day: int = Field(ge=0)
    description: str
    source_document_ids: list[str] = Field(default_factory=list)


class CourtListenerDocketSnapshot(StrictModel):
    schema_version: str = "0.1"
    snapshot_id: str
    source_profile_id: Literal["courtlistener_removal_state_pleadings_proxy"]
    synthetic_wrapper_id: str
    source_access_mode: Literal["offline_fixture"]
    public_data_sensitivity_level: Literal["synthetic_no_real_public_identity"]
    real_person_data_present: Literal[False]
    fixture_redaction_status: Literal["synthetic_no_real_identity"]
    originating_jurisdiction_type: Literal["state", "federal", "administrative", "unknown"]
    originating_state: str | None = None
    originating_county: str | None = None
    originating_court_name: str | None = None
    originating_case_number: str | None = None
    federal_court: str
    federal_docket_id: str
    federal_docket_number: str
    removed_to_federal: bool
    first_docket_day_count: int = Field(ge=0)
    docket_entries: list[CourtListenerDocketEntry]
    documents: list[CourtListenerSnapshotDocument]
    public_records_ingested: Literal[False] = False
    live_calls_performed: Literal[False] = False
    pacer_purchase_performed: Literal[False] = False
    recap_fetch_purchase_performed: Literal[False] = False
    uploads_performed: Literal[False] = False
    court_writes_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def snapshot_documents_and_entries_match(self) -> "CourtListenerDocketSnapshot":
        if not self.documents:
            raise ValueError("courtlistener docket snapshot requires documents")
        document_ids = {document.source_document_id for document in self.documents}
        for entry in self.docket_entries:
            missing = set(entry.source_document_ids) - document_ids
            if missing:
                raise ValueError("courtlistener docket entry references unknown document")
        return self


class CourtListenerLabelSourceRef(StrictModel):
    docket_id: str
    source_document_id: str
    source_segment_id: str
    source_span_ref: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    sha256: str
    public_source_profile_id: Literal["courtlistener_removal_state_pleadings_proxy"]

    @model_validator(mode="after")
    def label_source_ref_span_matches_offsets(self) -> "CourtListenerLabelSourceRef":
        expected = f"{self.source_segment_id}:{self.start_offset}-{self.end_offset}"
        if self.source_span_ref != expected:
            raise ValueError("courtlistener label source span ref must match offsets")
        if self.end_offset <= self.start_offset:
            raise ValueError("courtlistener label source ref end offset must exceed start offset")
        return self


DatasetLabeler = Literal["human", "rule", "model_candidate", "imported_metadata"]
DatasetReviewStatus = Literal["candidate", "reviewed", "rejected", "needs_review"]


class IntakeStageDocumentLabel(StrictModel):
    schema_version: str = "0.1"
    label_id: str
    label_type: Literal["document_type", "case_stage", "source_role"]
    value: str
    source_ref: CourtListenerLabelSourceRef
    confidence: float = Field(ge=0, le=1)
    labeler: DatasetLabeler
    review_status: DatasetReviewStatus
    notes: str = ""
    uncertainty: str = "low"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class ConflictSeedLabel(StrictModel):
    schema_version: str = "0.1"
    label_id: str
    name: str
    normalized_name: str
    observed_role: str
    inferred_role: str | None = None
    source_ref: CourtListenerLabelSourceRef
    confidence: float = Field(ge=0, le=1)
    labeler: DatasetLabeler
    review_status: DatasetReviewStatus
    uncertainty: str = "medium"
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


BudgetDriverValue = str | int | float | bool | None


class BudgetDriverLabel(StrictModel):
    schema_version: str = "0.1"
    label_id: str
    driver_id: str
    value: BudgetDriverValue
    value_status: Literal["observed", "missing", "unknown", "synthetic_context_wrapper"]
    source_ref: CourtListenerLabelSourceRef
    confidence: float = Field(ge=0, le=1)
    labeler: DatasetLabeler
    review_status: DatasetReviewStatus
    uncertainty: str = "medium"
    budget_amount_inferred: Literal[False] = False
    rate_inferred: Literal[False] = False
    guideline_inferred: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class PersonTimelineEventLabel(StrictModel):
    schema_version: str = "0.1"
    label_id: str
    person_id: str
    person_name: str
    event_type: str
    event_datetime_text: str
    normalized_datetime_candidate: str | None = None
    timezone_candidate: str | None = None
    location_text: str | None = None
    normalized_location_candidate: str | None = None
    source_ref: CourtListenerLabelSourceRef
    asserted_by: str
    document_type: str
    contradiction_links: list[str] = Field(default_factory=list)
    plausibility_status: Literal["plausible", "implausible", "unknown", "needs_review"]
    labeler: DatasetLabeler
    review_status: DatasetReviewStatus
    uncertainty: str = "medium"
    contradiction_candidate_only: Literal[True] = True
    legal_or_factual_impossibility_claimed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class SyntheticIntakeWrapper(StrictModel):
    schema_version: str = "0.1"
    synthetic_wrapper_id: str
    wrapper_type: Literal[
        "defense_carrier_assignment_wrapper",
        "employer_defense_assignment_wrapper",
        "plaintiff_side_consultation_wrapper",
        "generic_referral_wrapper",
        "public_docket_review_wrapper",
    ]
    observed_public_source_refs: list[str]
    synthetic_role_assumptions: list[str]
    context_prior_refs: list[str] = Field(default_factory=list)
    human_confirmed_fact_refs: list[str] = Field(default_factory=list)
    observed_facts_manufactured: Literal[False] = False
    distinguishes_synthetic_context_from_observed_evidence: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class CourtListenerDatasetManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    dataset_strategy_ref: str
    source_profile_id: Literal["courtlistener_removal_state_pleadings_proxy"]
    primary_practice_area: Literal["labor_employment"]
    fixture_snapshot_refs: list[str]
    synthetic_intake_wrapper: SyntheticIntakeWrapper
    intake_stage_document_labels: list[IntakeStageDocumentLabel]
    conflict_seed_labels: list[ConflictSeedLabel]
    budget_driver_labels: list[BudgetDriverLabel]
    person_timeline_event_labels: list[PersonTimelineEventLabel]
    public_records_ingested: Literal[False] = False
    live_calls_performed: Literal[False] = False
    pacer_purchase_performed: Literal[False] = False
    recap_fetch_purchase_performed: Literal[False] = False
    uploads_performed: Literal[False] = False
    court_writes_performed: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    budget_accuracy_claimed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def dataset_manifest_has_required_labels(self) -> "CourtListenerDatasetManifest":
        if not self.fixture_snapshot_refs:
            raise ValueError("courtlistener dataset manifest requires snapshot refs")
        if not self.intake_stage_document_labels:
            raise ValueError("courtlistener dataset manifest requires document labels")
        if not self.conflict_seed_labels:
            raise ValueError("courtlistener dataset manifest requires conflict seed labels")
        if not self.budget_driver_labels:
            raise ValueError("courtlistener dataset manifest requires budget driver labels")
        if not self.person_timeline_event_labels:
            raise ValueError("courtlistener dataset manifest requires timeline event labels")
        return self


class CourtListenerFixtureAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class CourtListenerFixtureAuditReport(StrictModel):
    schema_version: str = "0.1"
    courtlistener_fixture_audit_report_id: str
    status: Literal["courtlistener_fixture_ready_for_review", "blocked_courtlistener_fixture"]
    manifest_ref: str
    manifest_id: str
    snapshot_refs: list[str]
    snapshot_count: int = Field(ge=0)
    document_label_count: int = Field(ge=0)
    conflict_seed_label_count: int = Field(ge=0)
    budget_driver_label_count: int = Field(ge=0)
    timeline_event_label_count: int = Field(ge=0)
    checks: list[CourtListenerFixtureAuditCheck]
    public_records_ingested: Literal[False] = False
    live_calls_performed: Literal[False] = False
    pacer_purchase_performed: Literal[False] = False
    recap_fetch_purchase_performed: Literal[False] = False
    uploads_performed: Literal[False] = False
    court_writes_performed: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    budget_accuracy_claimed: Literal[False] = False
    fixture_mutation_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    generated_at: str

    @model_validator(mode="after")
    def fixture_audit_status_matches_checks(self) -> "CourtListenerFixtureAuditReport":
        failed = [check.check_id for check in self.checks if check.status == "failed"]
        if self.status == "courtlistener_fixture_ready_for_review" and failed:
            raise ValueError("ready courtlistener fixture audit cannot include failed checks")
        if self.status == "blocked_courtlistener_fixture" and not failed:
            raise ValueError("blocked courtlistener fixture audit requires failed checks")
        if self.snapshot_count != len(self.snapshot_refs):
            raise ValueError("courtlistener fixture snapshot count mismatch")
        return self


LaborEmploymentBudgetFactCategory = Literal[
    "entity_relationship",
    "claims_and_posture",
    "damages_and_exposure",
    "discovery_and_evidence",
    "timeline_and_stage",
    "guideline_and_rate_context",
]


LaborEmploymentBudgetFactState = Literal[
    "source_bound_observed_candidate",
    "source_bound_needs_review",
    "synthetic_context_requires_confirmation",
    "unknown_missing",
]


class LaborEmploymentBudgetFactSource(StrictModel):
    label_family: Literal[
        "budget_driver_label",
        "conflict_seed_label",
        "intake_stage_document_label",
        "person_timeline_event_label",
    ]
    label_id: str
    value: BudgetDriverValue
    observed_role: str | None = None
    inferred_role: str | None = None
    value_status: str | None = None
    review_status: DatasetReviewStatus
    uncertainty: str
    source_ref: CourtListenerLabelSourceRef


class LaborEmploymentBudgetFactFinding(StrictModel):
    fact_id: str
    fact_category: LaborEmploymentBudgetFactCategory
    required_level: Literal["critical", "important", "context"]
    question: str
    current_state: LaborEmploymentBudgetFactState
    budget_effects: list[str]
    sources: list[LaborEmploymentBudgetFactSource] = Field(default_factory=list)
    reviewer_action: str
    recommended_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    source_bound: bool
    human_confirmation_required: bool
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class LaborEmploymentBudgetFactGap(StrictModel):
    gap_id: str
    fact_id: str
    severity: Literal["critical", "warning", "info"]
    gap_type: Literal[
        "missing_evidence",
        "human_confirmation_required",
        "uncertain_candidate",
    ]
    budget_risk: str
    recommended_question: str
    blocks_precise_budget: bool
    source_refs: list[CourtListenerLabelSourceRef] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


LaborEmploymentRelationshipBucket = Literal[
    "employee_or_claimant_person",
    "employer_or_defendant_entity",
    "prospective_client_payer_or_carrier_posture",
    "individual_actor_or_defendant",
    "joint_employer_affiliate_or_staffing_structure",
]


class LaborEmploymentRelationshipCoverage(StrictModel):
    fact_id: str
    relationship_bucket: LaborEmploymentRelationshipBucket
    current_state: LaborEmploymentBudgetFactState
    required_level: Literal["critical", "important", "context"]
    question: str
    observed_roles: list[str] = Field(default_factory=list)
    inferred_roles: list[str] = Field(default_factory=list)
    source_label_ids: list[str] = Field(default_factory=list)
    source_refs: list[CourtListenerLabelSourceRef] = Field(default_factory=list)
    budget_effects: list[str] = Field(default_factory=list)
    blocks_precise_budget: bool
    human_confirmation_required: bool
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class LaborEmploymentRelationshipTopologySummary(StrictModel):
    coverage: list[LaborEmploymentRelationshipCoverage]
    source_bound_relationship_count: int = Field(ge=0)
    missing_or_review_relationship_count: int = Field(ge=0)
    critical_relationship_gap_count: int = Field(ge=0)
    person_candidate_count: int = Field(ge=0)
    organization_candidate_count: int = Field(ge=0)
    unresolved_relationship_fact_ids: list[str] = Field(default_factory=list)
    required_human_relationship_questions: list[str] = Field(default_factory=list)
    budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    canonical_role_promotion_authorized: Literal[False] = False
    relationship_classification_authoritative: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def relationship_topology_counts_match(self) -> "LaborEmploymentRelationshipTopologySummary":
        if self.source_bound_relationship_count != sum(
            1 for item in self.coverage if item.source_refs
        ):
            raise ValueError("L&E relationship source-bound count mismatch")
        if self.missing_or_review_relationship_count != sum(
            1 for item in self.coverage if item.current_state != "source_bound_observed_candidate"
        ):
            raise ValueError("L&E relationship missing/review count mismatch")
        if self.critical_relationship_gap_count != sum(
            1
            for item in self.coverage
            if item.required_level == "critical"
            and item.current_state != "source_bound_observed_candidate"
        ):
            raise ValueError("L&E critical relationship gap count mismatch")
        if self.unresolved_relationship_fact_ids != [
            item.fact_id
            for item in self.coverage
            if item.current_state != "source_bound_observed_candidate"
        ]:
            raise ValueError("L&E unresolved relationship fact IDs mismatch")
        return self


class LaborEmploymentBudgetFactAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class LaborEmploymentBudgetFactAuditReport(StrictModel):
    schema_version: str = "0.1"
    labor_employment_budget_fact_audit_report_id: str
    status: Literal[
        "labor_employment_budget_facts_ready_for_review",
        "blocked_labor_employment_budget_fact_audit",
    ]
    manifest_ref: str
    manifest_id: str
    policy_ref: str
    primary_practice_area: Literal["labor_employment"]
    budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    review_gate: Literal["human_labor_employment_budget_fact_review"] = (
        "human_labor_employment_budget_fact_review"
    )
    finding_count: int = Field(ge=0)
    source_bound_finding_count: int = Field(ge=0)
    needs_review_finding_count: int = Field(ge=0)
    unknown_finding_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    critical_gap_count: int = Field(ge=0)
    relationship_topology: LaborEmploymentRelationshipTopologySummary
    findings: list[LaborEmploymentBudgetFactFinding]
    gaps: list[LaborEmploymentBudgetFactGap]
    required_human_questions: list[str]
    checks: list[LaborEmploymentBudgetFactAuditCheck]
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    generated_at: str

    @model_validator(mode="after")
    def le_budget_fact_report_counts_match(self) -> "LaborEmploymentBudgetFactAuditReport":
        failed = [check.check_id for check in self.checks if check.status == "failed"]
        if self.status == "labor_employment_budget_facts_ready_for_review" and failed:
            raise ValueError("ready L&E budget fact audit cannot include failed checks")
        if self.status == "blocked_labor_employment_budget_fact_audit" and not failed:
            raise ValueError("blocked L&E budget fact audit requires failed checks")
        if self.finding_count != len(self.findings):
            raise ValueError("L&E budget fact finding count mismatch")
        if self.gap_count != len(self.gaps):
            raise ValueError("L&E budget fact gap count mismatch")
        if self.source_bound_finding_count != sum(
            1 for finding in self.findings if finding.source_bound
        ):
            raise ValueError("L&E source-bound finding count mismatch")
        if self.needs_review_finding_count != sum(
            1
            for finding in self.findings
            if finding.current_state
            in {"source_bound_needs_review", "synthetic_context_requires_confirmation"}
        ):
            raise ValueError("L&E needs-review finding count mismatch")
        if self.unknown_finding_count != sum(
            1 for finding in self.findings if finding.current_state == "unknown_missing"
        ):
            raise ValueError("L&E unknown finding count mismatch")
        if self.critical_gap_count != sum(1 for gap in self.gaps if gap.severity == "critical"):
            raise ValueError("L&E critical gap count mismatch")
        if (
            self.budget_readiness_state == "blocked_missing_critical_facts"
            and self.critical_gap_count == 0
        ):
            raise ValueError("blocked L&E budget readiness requires critical gaps")
        if (
            self.budget_readiness_state != "blocked_missing_critical_facts"
            and self.critical_gap_count > 0
        ):
            raise ValueError("L&E critical gaps require blocked budget readiness")
        return self


LaborEmploymentQAMatrixBudgetGateEffect = Literal[
    "block_amount_budget_before_proposal",
    "allow_range_or_hours_only_pending_review",
    "candidate_ready_for_budget_review_after_review",
]


class LaborEmploymentQAMatrixCase(StrictModel):
    case_id: str
    label: str
    status: Literal["passed", "failed"]
    manifest_ref: str
    fact_report_ref: str
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    actual_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    actual_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    critical_gap_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    source_bound_finding_count: int = Field(ge=0)
    unknown_finding_count: int = Field(ge=0)
    needs_review_finding_count: int = Field(ge=0)
    relationship_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    critical_relationship_gap_count: int = Field(ge=0)
    required_human_question_count: int = Field(ge=0)
    notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_qa_matrix_case_status_matches_expectations(self) -> "LaborEmploymentQAMatrixCase":
        expected_match = (
            self.expected_budget_readiness_state == self.actual_budget_readiness_state
            and self.expected_budget_gate_effect == self.actual_budget_gate_effect
        )
        if self.status == "passed" and not expected_match:
            raise ValueError("passed L&E QA matrix case must match expected state and gate effect")
        return self


class LaborEmploymentQAMatrixReport(StrictModel):
    schema_version: str = "0.1"
    labor_employment_qa_matrix_report_id: str
    status: Literal[
        "labor_employment_qa_matrix_ready_for_review",
        "blocked_by_labor_employment_qa_matrix",
    ]
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    cases: list[LaborEmploymentQAMatrixCase]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_qa_matrix_counts_and_status_match(self) -> "LaborEmploymentQAMatrixReport":
        failed = [case for case in self.cases if case.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("L&E QA matrix case count does not match")
        if self.failed_case_count != len(failed):
            raise ValueError("L&E QA matrix failed case count does not match")
        if self.status == "labor_employment_qa_matrix_ready_for_review" and failed:
            raise ValueError("ready L&E QA matrix cannot include failed cases")
        if self.status == "blocked_by_labor_employment_qa_matrix" and not failed:
            raise ValueError("blocked L&E QA matrix requires failed cases")
        required = {
            "human_labor_employment_budget_fact_review",
            "no_amount_budget_when_critical_facts_missing",
            "range_or_hours_only_until_review",
            "no_role_taxonomy_promotion_from_matrix",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("L&E QA matrix missing required next gates")
        return self


LaborEmploymentSyntheticFixtureFamily = Literal[
    "discrimination_harassment",
    "retaliation_wrongful_termination",
    "wage_hour_flsa_state",
    "ada_fmla_accommodation_leave",
    "restrictive_covenant_trade_secret",
    "epli_carrier_assignment",
    "class_collective_paga_representative",
    "administrative_exhaustion_agency_record",
]


LaborEmploymentSyntheticFixtureVariant = Literal[
    "clean",
    "messy_thread",
    "missing_attachment",
    "adversarial",
]


class LaborEmploymentSyntheticFixtureCase(StrictModel):
    case_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    label: str
    data_origin: Literal["synthetic"] = "synthetic"
    source_shape: Literal["spec_only"] = "spec_only"
    public_structure_only: Literal[True] = True
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    fact_need_ids: list[str]
    missing_critical_fact_ids: list[str] = Field(default_factory=list)
    missing_important_fact_ids: list[str] = Field(default_factory=list)
    budget_driver_dimensions: list[str]
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    expected_exception_labels: list[str]
    red_team_notes: list[str]
    holdout_excluded_from_prompt_assembly: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    calibration_approved: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_fixture_case_budget_gate_matches_missing_facts(
        self,
    ) -> "LaborEmploymentSyntheticFixtureCase":
        if self.missing_critical_fact_ids:
            if self.expected_budget_readiness_state != "blocked_missing_critical_facts":
                raise ValueError("missing critical L&E facts require blocked readiness")
            if self.expected_budget_gate_effect != "block_amount_budget_before_proposal":
                raise ValueError("missing critical L&E facts require amount-budget block")
        elif self.missing_important_fact_ids:
            if self.expected_budget_readiness_state != "range_only_pending_human_review":
                raise ValueError("missing important L&E facts require range-only review")
            if self.expected_budget_gate_effect != "allow_range_or_hours_only_pending_review":
                raise ValueError("missing important L&E facts require range-only gate")
        return self


class LaborEmploymentSyntheticFixtureFamilyPack(StrictModel):
    schema_version: str = "0.1"
    pack_id: str
    status: Literal["candidate_fixture_family_pack"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    source_methodology_refs: list[str]
    required_families: list[LaborEmploymentSyntheticFixtureFamily]
    required_variants: list[LaborEmploymentSyntheticFixtureVariant]
    required_fact_need_ids: list[str]
    required_budget_driver_dimensions: list[str]
    cases: list[LaborEmploymentSyntheticFixtureCase]
    human_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    calibration_approved: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_fixture_family_pack_counts_are_consistent(
        self,
    ) -> "LaborEmploymentSyntheticFixtureFamilyPack":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("L&E fixture family pack case IDs must be unique")
        required_families = set(self.required_families)
        required_variants = set(self.required_variants)
        for case in self.cases:
            if case.family not in required_families:
                raise ValueError("L&E fixture case family is not declared as required")
            if case.variant not in required_variants:
                raise ValueError("L&E fixture case variant is not declared as required")
        return self


class LaborEmploymentSyntheticFixtureFamilyCoverage(StrictModel):
    family: LaborEmploymentSyntheticFixtureFamily
    case_count: int = Field(ge=0)
    covered_variants: list[LaborEmploymentSyntheticFixtureVariant]
    missing_variants: list[LaborEmploymentSyntheticFixtureVariant]


class LaborEmploymentSyntheticFixtureFamilyPackCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentSyntheticFixtureFamilyPackReport(StrictModel):
    schema_version: str = "0.1"
    fixture_family_pack_report_id: str
    status: Literal[
        "labor_employment_fixture_family_pack_ready_for_review",
        "blocked_by_labor_employment_fixture_family_pack",
    ]
    pack_id: str
    pack_ref: str
    case_count: int = Field(ge=0)
    required_family_count: int = Field(ge=0)
    required_variant_count: int = Field(ge=0)
    complete_family_variant_count: int = Field(ge=0)
    missing_family_variant_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    range_only_case_count: int = Field(ge=0)
    ready_case_count: int = Field(ge=0)
    missing_fact_need_ids: list[str]
    missing_critical_fact_need_ids: list[str]
    missing_budget_driver_dimensions: list[str]
    family_coverage: list[LaborEmploymentSyntheticFixtureFamilyCoverage]
    checks: list[LaborEmploymentSyntheticFixtureFamilyPackCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    calibration_approved: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_fixture_family_pack_report_status_matches_checks(
        self,
    ) -> "LaborEmploymentSyntheticFixtureFamilyPackReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.required_family_count != len(self.family_coverage):
            raise ValueError("L&E fixture family coverage count does not match")
        has_gap = bool(
            failed
            or self.missing_family_variant_count
            or self.missing_fact_need_ids
            or self.missing_budget_driver_dimensions
        )
        if self.status == "labor_employment_fixture_family_pack_ready_for_review" and has_gap:
            raise ValueError("ready L&E fixture family pack cannot have coverage gaps")
        if self.status == "blocked_by_labor_employment_fixture_family_pack" and not has_gap:
            raise ValueError("blocked L&E fixture family pack requires a gap")
        required = {
            "synthetic_fixture_generation_review",
            "reviewed_gold_before_calibration",
            "no_real_public_payload_or_identity_reconstruction",
            "range_or_block_until_human_fact_review",
            "no_lake_or_sqlite_write_from_fixture_pack",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("L&E fixture family pack report missing required next gates")
        return self


class LaborEmploymentExecutableFixtureSpec(StrictModel):
    executable_fixture_id: str
    source_bundle_ref: str
    linked_pack_case_ids: list[str]
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    data_origin: Literal["synthetic"] = "synthetic"
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    expected_min_sources: int = Field(default=1, ge=1)
    expected_min_segments: int = Field(default=1, ge=1)
    expected_min_missing_sources: int = Field(default=0, ge=0)
    expected_min_duplicate_sources: int = Field(default=0, ge=0)
    expected_source_signal_terms: list[str]
    expected_preflight_exception_labels: list[str] = Field(default_factory=list)
    expected_budget_fact_gap_ids: list[str] = Field(default_factory=list)
    red_team_notes: list[str]
    public_structure_only: Literal[True] = True
    holdout_excluded_from_prompt_assembly: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_fixture_spec_is_reviewable(
        self,
    ) -> "LaborEmploymentExecutableFixtureSpec":
        if not self.linked_pack_case_ids:
            raise ValueError("executable L&E fixture requires at least one pack case link")
        if not self.expected_source_signal_terms:
            raise ValueError("executable L&E fixture requires source signal terms")
        if self.missing_critical_fact_expected:
            if self.expected_budget_readiness_state != "blocked_missing_critical_facts":
                raise ValueError("critical L&E fact gaps require blocked readiness")
            if self.expected_budget_gate_effect != "block_amount_budget_before_proposal":
                raise ValueError("critical L&E fact gaps require amount-budget block")
        return self

    @property
    def missing_critical_fact_expected(self) -> bool:
        return bool(self.expected_budget_fact_gap_ids) and (
            self.expected_budget_treatment == "block_amount_budget"
        )


class LaborEmploymentExecutableFixtureManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    status: Literal["candidate_executable_fixture_manifest"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    pack_ref: str
    practice_profile_ref: str
    source_methodology_refs: list[str]
    fixtures: list[LaborEmploymentExecutableFixtureSpec]
    human_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    calibration_approved: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_fixture_manifest_ids_are_unique(
        self,
    ) -> "LaborEmploymentExecutableFixtureManifest":
        fixture_ids = [fixture.executable_fixture_id for fixture in self.fixtures]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("executable L&E fixture IDs must be unique")
        source_refs = [fixture.source_bundle_ref for fixture in self.fixtures]
        if len(source_refs) != len(set(source_refs)):
            raise ValueError("executable L&E source bundle refs must be unique")
        if not self.fixtures:
            raise ValueError("executable L&E manifest requires at least one fixture")
        return self


class LaborEmploymentExecutableFixtureAuditCase(StrictModel):
    executable_fixture_id: str
    source_bundle_ref: str
    linked_pack_case_ids: list[str]
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    preflight_packet_ref: str | None = None
    data_scope_gate_report_ref: str | None = None
    intake_review_form_ref: str | None = None
    source_count: int = Field(ge=0)
    segment_count: int = Field(ge=0)
    source_hash_count: int = Field(ge=0)
    missing_source_count: int = Field(ge=0)
    duplicate_source_count: int = Field(ge=0)
    party_candidate_count: int = Field(ge=0)
    matter_candidate_count: int = Field(ge=0)
    deadline_candidate_count: int = Field(ge=0)
    prohibited_next_step_count: int = Field(ge=0)
    exception_labels: list[str]
    missing_expected_exception_labels: list[str]
    missing_source_signal_terms: list[str]
    missing_pack_case_ids: list[str]
    pack_family_variant_mismatch_case_ids: list[str]
    failed_expectation_ids: list[str] = Field(default_factory=list)
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    expected_budget_fact_gap_ids: list[str]
    budget_fact_audit_required: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    notes: list[str]

    @model_validator(mode="after")
    def le_executable_fixture_case_status_matches_findings(
        self,
    ) -> "LaborEmploymentExecutableFixtureAuditCase":
        failed = bool(
            self.missing_expected_exception_labels
            or self.missing_source_signal_terms
            or self.missing_pack_case_ids
            or self.pack_family_variant_mismatch_case_ids
            or self.failed_expectation_ids
        )
        if self.preflight_packet_ref is None:
            failed = True
        if self.status == "passed" and failed:
            raise ValueError("passed executable L&E fixture case cannot have unresolved gaps")
        if self.status == "failed" and not failed:
            raise ValueError("failed executable L&E fixture case requires an unresolved gap")
        return self


class LaborEmploymentExecutableFixtureAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentExecutableFixtureAuditReport(StrictModel):
    schema_version: str = "0.1"
    executable_fixture_audit_report_id: str
    status: Literal[
        "labor_employment_executable_fixtures_ready_for_review",
        "blocked_by_labor_employment_executable_fixtures",
    ]
    manifest_id: str
    manifest_ref: str
    pack_ref: str
    practice_profile_ref: str
    fixture_count: int = Field(ge=0)
    preflight_executed_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    missing_pack_link_count: int = Field(ge=0)
    missing_source_signal_count: int = Field(ge=0)
    missing_expected_exception_label_count: int = Field(ge=0)
    cases: list[LaborEmploymentExecutableFixtureAuditCase]
    checks: list[LaborEmploymentExecutableFixtureAuditCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    calibration_approved: Literal[False] = False
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_executable_fixture_report_status_matches_counts(
        self,
    ) -> "LaborEmploymentExecutableFixtureAuditReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.fixture_count != len(self.cases):
            raise ValueError("executable L&E fixture count does not match")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("executable L&E failed case count does not match")
        if self.preflight_executed_count != sum(
            1 for case in self.cases if case.preflight_packet_ref is not None
        ):
            raise ValueError("executable L&E preflight executed count does not match")
        if self.missing_pack_link_count != sum(
            len(case.missing_pack_case_ids) for case in self.cases
        ):
            raise ValueError("executable L&E missing pack link count does not match")
        if self.missing_source_signal_count != sum(
            len(case.missing_source_signal_terms) for case in self.cases
        ):
            raise ValueError("executable L&E missing signal count does not match")
        if self.missing_expected_exception_label_count != sum(
            len(case.missing_expected_exception_labels) for case in self.cases
        ):
            raise ValueError("executable L&E missing exception label count does not match")
        has_gap = bool(failed_cases or failed_checks)
        if self.status == "labor_employment_executable_fixtures_ready_for_review" and has_gap:
            raise ValueError("ready executable L&E report cannot include failed cases/checks")
        if self.status == "blocked_by_labor_employment_executable_fixtures" and not has_gap:
            raise ValueError("blocked executable L&E report requires a failed case/check")
        required = {
            "human_labor_employment_budget_fact_review",
            "preflight_to_budget_fact_fixture_binding",
            "no_amount_budget_from_preflight_only",
            "no_real_public_payload_or_identity_reconstruction",
            "no_lake_or_sqlite_write_from_executable_fixtures",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("executable L&E report missing required next gates")
        return self


class LaborEmploymentExecutableBudgetFactBindingItemSpec(StrictModel):
    fact_id: str
    expected_gap_type: Literal[
        "missing_evidence",
        "human_confirmation_required",
        "uncertain_candidate",
    ]
    source_signal_terms: list[str] = Field(default_factory=list)
    expected_exception_labels: list[str] = Field(default_factory=list)
    expected_source_ids: list[str] = Field(default_factory=list)
    reason: str
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_has_anchor(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingItemSpec":
        if not (
            self.source_signal_terms or self.expected_exception_labels or self.expected_source_ids
        ):
            raise ValueError("executable L&E budget fact binding requires an evidence anchor")
        return self


class LaborEmploymentExecutableBudgetFactBindingCaseSpec(StrictModel):
    binding_case_id: str
    executable_fixture_id: str
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    fact_bindings: list[LaborEmploymentExecutableBudgetFactBindingItemSpec]
    red_team_notes: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_case_is_unique(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingCaseSpec":
        fact_ids = [binding.fact_id for binding in self.fact_bindings]
        if not fact_ids:
            raise ValueError("executable L&E budget fact binding case requires fact bindings")
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("executable L&E budget fact binding IDs must be unique per case")
        return self


class LaborEmploymentExecutableBudgetFactBindingManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    status: Literal["candidate_executable_budget_fact_binding_manifest"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    executable_fixture_manifest_ref: str
    fact_policy_ref: str
    bindings: list[LaborEmploymentExecutableBudgetFactBindingCaseSpec]
    human_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_manifest_is_unique(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingManifest":
        case_ids = [case.binding_case_id for case in self.bindings]
        fixture_ids = [case.executable_fixture_id for case in self.bindings]
        if not self.bindings:
            raise ValueError("executable L&E budget fact binding manifest requires bindings")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("executable L&E budget fact binding case IDs must be unique")
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("executable L&E budget fact binding fixture IDs must be unique")
        return self


class LaborEmploymentExecutableBudgetFactBindingItem(StrictModel):
    fact_id: str
    fact_category: LaborEmploymentBudgetFactCategory
    required_level: Literal["critical", "important", "context"]
    question: str
    expected_gap_type: Literal[
        "missing_evidence",
        "human_confirmation_required",
        "uncertain_candidate",
    ]
    binding_state: Literal[
        "source_bound_gap_candidate",
        "exception_bound_gap_candidate",
        "source_and_exception_bound_gap_candidate",
        "inventory_bound_gap_candidate",
        "unbound_gap_candidate",
    ]
    recommended_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    budget_effects: list[str]
    source_signal_terms: list[str]
    matched_source_signal_terms: list[str]
    missing_source_signal_terms: list[str]
    expected_exception_labels: list[str]
    matched_exception_labels: list[str]
    missing_exception_labels: list[str]
    expected_source_ids: list[str]
    matched_source_ids: list[str]
    missing_source_ids: list[str]
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    source_inventory_refs: list[str] = Field(default_factory=list)
    blocks_precise_budget: bool
    human_confirmation_required: bool
    reason: str
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_item_state_matches_refs(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingItem":
        if self.binding_state == "source_bound_gap_candidate" and not self.evidence_refs:
            raise ValueError("source-bound gap binding requires evidence refs")
        if (
            self.binding_state == "exception_bound_gap_candidate"
            and not self.matched_exception_labels
        ):
            raise ValueError("exception-bound gap binding requires matched exception labels")
        if self.binding_state == "source_and_exception_bound_gap_candidate" and (
            not self.evidence_refs or not self.matched_exception_labels
        ):
            raise ValueError("source+exception gap binding requires both anchor types")
        if self.binding_state == "inventory_bound_gap_candidate" and not self.source_inventory_refs:
            raise ValueError("inventory-bound gap binding requires source inventory refs")
        return self


class LaborEmploymentExecutableBudgetFactBindingCase(StrictModel):
    binding_case_id: str
    executable_fixture_id: str
    status: Literal["passed", "failed"]
    preflight_packet_ref: str | None = None
    executable_fixture_report_case_status: Literal["passed", "failed"] | None = None
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    executable_expected_budget_readiness_state: (
        Literal[
            "blocked_missing_critical_facts",
            "range_only_pending_human_review",
            "candidate_ready_for_budget_review",
        ]
        | None
    ) = None
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect
    executable_expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect | None = None
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    executable_expected_budget_treatment: (
        Literal[
            "block_amount_budget",
            "hours_only_or_broad_range",
            "candidate_range_budget_after_review",
        ]
        | None
    ) = None
    fact_binding_count: int = Field(ge=0)
    critical_fact_binding_count: int = Field(ge=0)
    evidence_bound_fact_count: int = Field(ge=0)
    exception_bound_fact_count: int = Field(ge=0)
    missing_policy_fact_ids: list[str]
    failed_expectation_ids: list[str]
    fact_bindings: list[LaborEmploymentExecutableBudgetFactBindingItem]
    notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_case_counts_match(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingCase":
        failed = bool(self.missing_policy_fact_ids or self.failed_expectation_ids)
        if self.fact_binding_count != len(self.fact_bindings):
            raise ValueError("executable L&E budget fact binding count mismatch")
        if self.critical_fact_binding_count != sum(
            1 for binding in self.fact_bindings if binding.required_level == "critical"
        ):
            raise ValueError("executable L&E critical fact binding count mismatch")
        if self.evidence_bound_fact_count != sum(
            1 for binding in self.fact_bindings if binding.evidence_refs
        ):
            raise ValueError("executable L&E evidence-bound fact count mismatch")
        if self.exception_bound_fact_count != sum(
            1 for binding in self.fact_bindings if binding.matched_exception_labels
        ):
            raise ValueError("executable L&E exception-bound fact count mismatch")
        if self.status == "passed" and failed:
            raise ValueError("passed executable L&E budget fact binding case has failures")
        if self.status == "failed" and not failed:
            raise ValueError("failed executable L&E budget fact binding case requires failures")
        return self


class LaborEmploymentExecutableBudgetFactBindingCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentExecutableBudgetFactBindingReport(StrictModel):
    schema_version: str = "0.1"
    executable_budget_fact_binding_report_id: str
    status: Literal[
        "labor_employment_executable_budget_fact_bindings_ready_for_review",
        "blocked_by_labor_employment_executable_budget_fact_bindings",
    ]
    binding_manifest_id: str
    binding_manifest_ref: str
    executable_fixture_report_ref: str
    fact_policy_ref: str
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    fact_binding_count: int = Field(ge=0)
    critical_fact_binding_count: int = Field(ge=0)
    evidence_bound_fact_count: int = Field(ge=0)
    exception_bound_fact_count: int = Field(ge=0)
    missing_policy_fact_count: int = Field(ge=0)
    missing_source_signal_count: int = Field(ge=0)
    missing_exception_label_count: int = Field(ge=0)
    missing_source_id_count: int = Field(ge=0)
    cases: list[LaborEmploymentExecutableBudgetFactBindingCase]
    checks: list[LaborEmploymentExecutableBudgetFactBindingCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_executable_budget_fact_binding_report_counts_match(
        self,
    ) -> "LaborEmploymentExecutableBudgetFactBindingReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("executable L&E budget fact binding case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("executable L&E budget fact binding failed case count mismatch")
        if self.fact_binding_count != sum(case.fact_binding_count for case in self.cases):
            raise ValueError("executable L&E budget fact binding aggregate count mismatch")
        if self.critical_fact_binding_count != sum(
            case.critical_fact_binding_count for case in self.cases
        ):
            raise ValueError("executable L&E critical fact binding aggregate count mismatch")
        if self.evidence_bound_fact_count != sum(
            case.evidence_bound_fact_count for case in self.cases
        ):
            raise ValueError("executable L&E evidence-bound aggregate count mismatch")
        if self.exception_bound_fact_count != sum(
            case.exception_bound_fact_count for case in self.cases
        ):
            raise ValueError("executable L&E exception-bound aggregate count mismatch")
        if self.missing_policy_fact_count != sum(
            len(case.missing_policy_fact_ids) for case in self.cases
        ):
            raise ValueError("executable L&E missing policy fact count mismatch")
        if self.missing_source_signal_count != sum(
            len(binding.missing_source_signal_terms)
            for case in self.cases
            for binding in case.fact_bindings
        ):
            raise ValueError("executable L&E missing source signal count mismatch")
        if self.missing_exception_label_count != sum(
            len(binding.missing_exception_labels)
            for case in self.cases
            for binding in case.fact_bindings
        ):
            raise ValueError("executable L&E missing exception label count mismatch")
        if self.missing_source_id_count != sum(
            len(binding.missing_source_ids) for case in self.cases for binding in case.fact_bindings
        ):
            raise ValueError("executable L&E missing source id count mismatch")
        has_gap = bool(failed_cases or failed_checks)
        if (
            self.status == "labor_employment_executable_budget_fact_bindings_ready_for_review"
            and has_gap
        ):
            raise ValueError("ready executable L&E budget fact binding report has failures")
        if (
            self.status == "blocked_by_labor_employment_executable_budget_fact_bindings"
            and not has_gap
        ):
            raise ValueError("blocked executable L&E budget fact binding report requires failures")
        required = {
            "human_labor_employment_budget_fact_review",
            "build_labor_employment_budget_fact_audit_before_budget_precondition",
            "no_amount_budget_from_binding_report",
            "no_lake_or_sqlite_write_from_binding_report",
            "no_role_taxonomy_promotion_from_binding_report",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("executable L&E budget fact binding report missing required gates")
        return self


class PublicSourceMethodologySource(StrictModel):
    source_id: str
    url: str
    methodology_role: str
    useful_for: list[str]
    safe_use_classes: list[str]
    prohibited_use_classes: list[str]
    review_requirements: list[str]
    synthetic_conversion_rules: list[str]
    retention_policy: str
    privacy_posture: str
    adapter_status: str
    direct_runtime_ingestion: bool
    status: Literal["ready_for_human_methodology_review", "blocked"]
    blocking_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def public_source_methodology_required(self) -> "PublicSourceMethodologySource":
        required_review = {
            "source_license_review",
            "privacy_review",
            "retention_decision",
            "owner_approval_before_adapter",
            "no_raw_payload_commit",
        }
        if self.status == "ready_for_human_methodology_review" and self.blocking_reasons:
            raise ValueError("ready public source methodology cannot include blockers")
        if self.status == "ready_for_human_methodology_review":
            if not required_review.issubset(set(self.review_requirements)):
                raise ValueError("public source methodology is missing required review gates")
            if not self.synthetic_conversion_rules:
                raise ValueError("public source methodology requires synthetic conversion rules")
            if self.adapter_status != "not_authorized":
                raise ValueError("ready public source methodology requires adapter not authorized")
            if self.direct_runtime_ingestion is not False:
                raise ValueError("ready public source methodology cannot allow direct ingestion")
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked public source methodology requires blockers")
        return self


class PublicSourceMethodologyCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    source_ids: list[str] = Field(default_factory=list)


class PublicSourceMethodologyReport(StrictModel):
    schema_version: str = "0.1"
    public_source_methodology_report_id: str
    status: Literal[
        "ready_for_human_public_source_methodology_review",
        "blocked_public_source_methodology",
    ]
    source_catalog_ref: str
    data_policy_ref: str
    source_count: int = Field(ge=0)
    required_source_ids: list[str]
    missing_required_source_ids: list[str]
    sources: list[PublicSourceMethodologySource]
    checks: list[PublicSourceMethodologyCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    metadata_only: Literal[True] = True
    human_review_required: Literal[True] = True
    direct_runtime_ingestion_allowed: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    real_party_records_committed: Literal[False] = False
    real_matter_records_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def public_methodology_counts_match(self) -> "PublicSourceMethodologyReport":
        if self.source_count != len(self.sources):
            raise ValueError("public source methodology source count must match sources")
        if self.status == "ready_for_human_public_source_methodology_review":
            if self.missing_required_source_ids:
                raise ValueError("ready public source methodology cannot miss required sources")
            if any(check.status != "passed" for check in self.checks):
                raise ValueError("ready public source methodology cannot include failed checks")
            if any(
                source.status != "ready_for_human_methodology_review" for source in self.sources
            ):
                raise ValueError("ready public source methodology cannot include blocked sources")
        if self.status == "blocked_public_source_methodology" and not any(
            check.status in {"blocked", "failed"} for check in self.checks
        ):
            raise ValueError("blocked public source methodology requires blocked or failed checks")
        return self


class PublicDataCacheSourceManifest(StrictModel):
    schema_version: str = "0.1"
    source_id: str
    source_url: str
    source_type: str
    retrieved_at: str
    sha256: str
    byte_count: int = Field(ge=0)
    cache_ref: str
    license_terms_note: str
    allowed_use: str
    prohibited_use: str
    retention_posture: str
    data_origin: Literal["public_reference_cache"] = "public_reference_cache"
    public_payload_committed: Literal[False] = False
    direct_runtime_ingestion_allowed: Literal[False] = False
    runtime_intake_input: Literal[False] = False

    @model_validator(mode="after")
    def cache_source_manifest_is_reviewable(self) -> "PublicDataCacheSourceManifest":
        required_text = {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at,
            "cache_ref": self.cache_ref,
            "license_terms_note": self.license_terms_note,
            "allowed_use": self.allowed_use,
            "prohibited_use": self.prohibited_use,
            "retention_posture": self.retention_posture,
        }
        missing = [field for field, value in required_text.items() if not value.strip()]
        if missing:
            raise ValueError(f"public data cache source manifest missing fields: {missing}")
        digest = self.sha256.removeprefix("sha256:")
        if len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise ValueError("public data cache source manifest sha256 must be a SHA-256 digest")
        if self.cache_ref.startswith(("/", "\\")) or ":" in self.cache_ref:
            raise ValueError("public data cache source manifest cache_ref must be relative")
        return self


class PublicDataCacheAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    source_ids: list[str] = Field(default_factory=list)
    path_refs: list[str] = Field(default_factory=list)


class PublicDataCacheAuditReport(StrictModel):
    schema_version: str = "0.1"
    public_data_cache_audit_report_id: str
    status: Literal[
        "ready_for_human_public_data_cache_review",
        "blocked_public_data_cache",
    ]
    source_catalog_ref: str
    data_policy_ref: str
    cache_root_ref: str
    manifest_ref: str
    manifest_entry_count: int = Field(ge=0)
    valid_manifest_entry_count: int = Field(ge=0)
    cache_sample_count: int = Field(ge=0)
    total_cache_sample_bytes: int = Field(ge=0)
    approved_source_ids: list[str]
    unknown_source_ids: list[str] = Field(default_factory=list)
    failed_hash_source_ids: list[str] = Field(default_factory=list)
    missing_cache_file_source_ids: list[str] = Field(default_factory=list)
    blocked_path_refs: list[str] = Field(default_factory=list)
    sources: list[PublicDataCacheSourceManifest]
    checks: list[PublicDataCacheAuditCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    report_payload_metadata_only: Literal[True] = True
    human_review_required: Literal[True] = True
    public_cache_samples_present: bool
    direct_runtime_ingestion_allowed: Literal[False] = False
    public_records_runtime_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    tracked_public_payload_committed: Literal[False] = False
    real_party_records_committed: Literal[False] = False
    real_matter_records_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def public_data_cache_counts_match(self) -> "PublicDataCacheAuditReport":
        if self.valid_manifest_entry_count != len(self.sources):
            raise ValueError("public data cache valid manifest count must match sources")
        if self.cache_sample_count > self.valid_manifest_entry_count:
            raise ValueError("public data cache sample count cannot exceed valid manifest count")
        if self.public_cache_samples_present != (self.cache_sample_count > 0):
            raise ValueError("public data cache sample presence must match sample count")
        if self.status == "ready_for_human_public_data_cache_review":
            if self.manifest_entry_count == 0:
                raise ValueError("ready public data cache audit requires manifest entries")
            if any(check.status != "passed" for check in self.checks):
                raise ValueError("ready public data cache audit cannot include failed checks")
            if (
                self.unknown_source_ids
                or self.failed_hash_source_ids
                or self.missing_cache_file_source_ids
                or self.blocked_path_refs
            ):
                raise ValueError("ready public data cache audit cannot include blockers")
        if self.status == "blocked_public_data_cache" and not any(
            check.status in {"blocked", "failed"} for check in self.checks
        ):
            raise ValueError("blocked public data cache audit requires blocked or failed checks")
        return self


PublicSyntheticFixtureFamily = Literal[
    "docket_structure",
    "aggregate_case_metadata",
    "messy_email_structure",
    "public_filing_structure",
    "auto_liability_distribution",
    "medical_malpractice_distribution",
    "public_structure_review",
]


class PublicSyntheticFixtureConversionSpec(StrictModel):
    schema_version: str = "0.1"
    conversion_spec_id: str
    source_id: str
    source_methodology_ref: str
    methodology_role: str
    target_fixture_family: PublicSyntheticFixtureFamily
    allowed_structure_inputs: list[str]
    forbidden_inputs: list[str]
    identity_replacement_rules: list[str]
    field_transformation_rules: list[str]
    required_synthetic_gold_checks: list[str]
    required_red_team_checks: list[str]
    review_status: Literal[
        "planned_for_human_conversion_review",
        "blocked_by_methodology",
    ]
    blocking_reasons: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    no_public_payload_ingested: Literal[True] = True
    no_real_party_records: Literal[True] = True
    no_real_matter_records: Literal[True] = True
    no_adapter_authorized: Literal[True] = True
    fixture_file_mutation_allowed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def conversion_spec_has_reviewable_boundaries(self) -> "PublicSyntheticFixtureConversionSpec":
        required_forbidden = {
            "real_party_names",
            "real_case_numbers",
            "raw_public_payloads",
            "downloaded_public_payloads",
            "privileged_or_confidential_material",
        }
        missing_forbidden = required_forbidden - set(self.forbidden_inputs)
        if self.review_status == "planned_for_human_conversion_review":
            if self.blocking_reasons:
                raise ValueError("ready conversion spec cannot include blockers")
            if not self.allowed_structure_inputs:
                raise ValueError("conversion spec requires allowed structure inputs")
            if missing_forbidden:
                raise ValueError("conversion spec is missing required forbidden inputs")
            if not self.identity_replacement_rules:
                raise ValueError("conversion spec requires identity replacement rules")
            if not self.field_transformation_rules:
                raise ValueError("conversion spec requires field transformation rules")
            if not self.required_synthetic_gold_checks:
                raise ValueError("conversion spec requires synthetic gold checks")
            if not self.required_red_team_checks:
                raise ValueError("conversion spec requires red-team checks")
        if self.review_status == "blocked_by_methodology" and not self.blocking_reasons:
            raise ValueError("blocked conversion spec requires blockers")
        return self


class PublicSyntheticFixtureConversionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    source_ids: list[str] = Field(default_factory=list)


class PublicSyntheticFixtureConversionPlan(StrictModel):
    schema_version: str = "0.1"
    conversion_plan_id: str
    status: Literal[
        "ready_for_human_conversion_review",
        "blocked_public_methodology_not_ready",
    ]
    source_methodology_report_id: str
    source_methodology_report_ref: str
    source_catalog_ref: str
    specs_output_ref: str
    spec_count: int = Field(ge=0)
    specs: list[PublicSyntheticFixtureConversionSpec]
    checks: list[PublicSyntheticFixtureConversionCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def conversion_plan_counts_and_status_match(self) -> "PublicSyntheticFixtureConversionPlan":
        if self.spec_count != len(self.specs):
            raise ValueError("conversion plan spec count must match specs")
        if not self.required_next_gates:
            raise ValueError("conversion plan requires next gates")
        if self.status == "ready_for_human_conversion_review":
            if self.spec_count == 0:
                raise ValueError("ready conversion plan requires specs")
            if any(check.status != "passed" for check in self.checks):
                raise ValueError("ready conversion plan cannot include failed checks")
            if any(
                spec.review_status != "planned_for_human_conversion_review" for spec in self.specs
            ):
                raise ValueError("ready conversion plan cannot include blocked specs")
        if self.status == "blocked_public_methodology_not_ready" and not any(
            check.status in {"blocked", "failed"} for check in self.checks
        ):
            raise ValueError("blocked conversion plan requires blocked or failed checks")
        return self


PublicSyntheticFixtureReviewPriority = Literal["critical", "high", "medium", "low"]

PublicSyntheticFixtureReviewAction = Literal[
    "approve_for_separate_fixture_pr_after_required_reviews",
    "hold_for_privacy_or_license_review",
    "revise_conversion_spec_before_fixture_pr",
    "reject_source_for_fixture_use",
    "human_only_hold",
]

PublicSyntheticFixtureReviewOutcome = Literal[
    "approve_conversion_spec_for_separate_fixture_pr",
    "require_spec_revision",
    "reject_source_for_fixture_use",
    "needs_more_information",
    "human_only_hold",
]


class PublicSyntheticFixtureConversionReviewRecommendation(StrictModel):
    recommendation_id: str
    conversion_spec_id: str
    source_id: str
    target_fixture_family: PublicSyntheticFixtureFamily
    recommended_action: PublicSyntheticFixtureReviewAction
    priority: PublicSyntheticFixtureReviewPriority
    why: list[str]
    required_human_decisions: list[str]
    required_evidence_refs: list[str]
    red_team_focus: list[str]
    fixture_generation_authorized: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    external_submission_authorized: Literal[False] = False
    lake_write_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False

    @model_validator(mode="after")
    def recommendation_requires_review_basis(
        self,
    ) -> "PublicSyntheticFixtureConversionReviewRecommendation":
        if not self.why:
            raise ValueError("conversion review recommendation requires why notes")
        if not self.required_human_decisions:
            raise ValueError("conversion review recommendation requires human decisions")
        if not self.required_evidence_refs:
            raise ValueError("conversion review recommendation requires evidence refs")
        if not self.red_team_focus:
            raise ValueError("conversion review recommendation requires red-team focus")
        return self


class PublicSyntheticFixtureConversionReviewRedTeamNote(StrictModel):
    note_id: str
    severity: PublicSyntheticFixtureReviewPriority
    scope: Literal[
        "boundary",
        "identity_reconstruction",
        "privacy_license_retention",
        "payload_contamination",
        "legal_fact_misuse",
        "adapter_scope",
        "aggregate_reidentification",
        "prompt_injection",
    ]
    message: str
    recommended_check: str
    source_ids: list[str] = Field(default_factory=list)


class PublicSyntheticFixtureConversionReviewDecisionTemplate(StrictModel):
    decision_template_id: str
    conversion_spec_id: str
    source_id: str
    recommended_action: PublicSyntheticFixtureReviewAction
    allowed_outcomes: list[PublicSyntheticFixtureReviewOutcome]
    recommended_outcome: PublicSyntheticFixtureReviewOutcome
    required_fields: list[str]
    required_evidence_refs: list[str]
    append_only_review_outcome_required: Literal[True] = True
    reviewer_id_required: Literal[True] = True
    reviewed_at_required: Literal[True] = True
    decision_reason_required: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    external_submission_authorized: Literal[False] = False
    lake_write_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False

    @model_validator(mode="after")
    def decision_template_requires_fields(
        self,
    ) -> "PublicSyntheticFixtureConversionReviewDecisionTemplate":
        if not self.allowed_outcomes:
            raise ValueError("conversion review decision template requires outcomes")
        if self.recommended_outcome not in self.allowed_outcomes:
            raise ValueError("recommended outcome must be allowed")
        if not self.required_fields:
            raise ValueError("conversion review decision template requires fields")
        if not self.required_evidence_refs:
            raise ValueError("conversion review decision template requires evidence refs")
        return self


class PublicSyntheticFixtureConversionReviewPacket(StrictModel):
    schema_version: str = "0.1"
    review_packet_id: str
    conversion_plan_id: str
    conversion_plan_ref: str
    conversion_plan_status: str
    status: Literal[
        "ready_for_human_conversion_review",
        "blocked_by_conversion_plan",
        "no_specs_to_review",
    ]
    spec_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    red_team_note_count: int = Field(ge=0)
    decision_template_count: int = Field(ge=0)
    recommendations: list[PublicSyntheticFixtureConversionReviewRecommendation]
    red_team_notes: list[PublicSyntheticFixtureConversionReviewRedTeamNote]
    decision_templates: list[PublicSyntheticFixtureConversionReviewDecisionTemplate]
    allowed_reviewer_outcomes: list[PublicSyntheticFixtureReviewOutcome]
    required_next_gates: list[str]
    human_readable_review_ref: str | None = None
    decision_template_ref: str | None = None
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    append_only_review_outcome_required: Literal[True] = True
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def conversion_review_packet_counts_match(
        self,
    ) -> "PublicSyntheticFixtureConversionReviewPacket":
        if self.recommendation_count != len(self.recommendations):
            raise ValueError("conversion review recommendation count must match")
        if self.red_team_note_count != len(self.red_team_notes):
            raise ValueError("conversion review red-team note count must match")
        if self.decision_template_count != len(self.decision_templates):
            raise ValueError("conversion review decision template count must match")
        if self.status == "ready_for_human_conversion_review":
            if self.conversion_plan_status != "ready_for_human_conversion_review":
                raise ValueError("ready review packet requires ready conversion plan")
            if self.spec_count == 0:
                raise ValueError("ready review packet requires specs")
            if self.recommendation_count != self.spec_count:
                raise ValueError("ready review packet requires one recommendation per spec")
            if self.decision_template_count != self.spec_count:
                raise ValueError("ready review packet requires one decision template per spec")
            if not self.red_team_notes:
                raise ValueError("ready review packet requires red-team notes")
        if self.status == "blocked_by_conversion_plan" and self.recommendations:
            raise ValueError("blocked review packet cannot include recommendations")
        return self


class PublicSyntheticFixtureConversionReviewOutcomeCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    conversion_spec_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class PublicSyntheticFixtureConversionReviewRecord(StrictModel):
    schema_version: str = "0.1"
    conversion_review_id: str
    review_packet_id: str
    conversion_plan_id: str
    conversion_spec_id: str
    source_id: str
    reviewer_id: str
    reviewed_at: str
    outcome: PublicSyntheticFixtureReviewOutcome
    decision_reason: str
    accepted_required_gates: list[str] = Field(default_factory=list)
    rejected_or_revision_reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    supersedes_review_outcome_id: str | None = None
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_fixture_generation: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def conversion_review_record_is_complete(
        self,
    ) -> "PublicSyntheticFixtureConversionReviewRecord":
        if not self.conversion_review_id.strip():
            raise ValueError("conversion review record requires conversion_review_id")
        if not self.reviewer_id.strip():
            raise ValueError("conversion review record requires reviewer_id")
        if not self.reviewed_at.strip():
            raise ValueError("conversion review record requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("conversion review record requires decision_reason")
        if not self.evidence_refs:
            raise ValueError("conversion review record requires evidence_refs")
        approval_gates = {
            "human_public_synthetic_conversion_review",
            "source_license_review",
            "privacy_review",
            "retention_decision",
            "separate_synthetic_fixture_generation_pr_if_approved",
            "synthetic_fixture_gold_review",
            "red_team_identity_reconstruction_review",
        }
        if self.outcome == "approve_conversion_spec_for_separate_fixture_pr":
            if not approval_gates.issubset(set(self.accepted_required_gates)):
                raise ValueError("approved conversion reviews require all approval gates")
        if self.outcome in {"require_spec_revision", "reject_source_for_fixture_use"}:
            if not self.rejected_or_revision_reasons:
                raise ValueError("revision or rejection conversion reviews require reasons")
        if self.outcome == "needs_more_information" and not self.required_followups:
            raise ValueError("needs_more_information conversion reviews require followups")
        return self


class PublicSyntheticFixtureConversionReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    review_outcome_report_id: str
    status: Literal[
        "conversion_review_recorded_separate_fixture_pr_required",
        "conversion_review_recorded_revision_or_rejection",
        "conversion_review_recorded_more_information_required",
        "conversion_review_recorded_human_only_hold",
        "conversion_review_blocked_by_review_evidence",
    ]
    source_review_packet_ref: str
    review_packet_id: str
    conversion_plan_id: str
    conversion_review_id: str
    conversion_spec_id: str
    source_id: str
    outcome: PublicSyntheticFixtureReviewOutcome
    decision_reason: str
    source_review_packet_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_by_conversion_plan",
        "no_specs_to_review",
    ]
    target_fixture_family: PublicSyntheticFixtureFamily | None = None
    source_recommendation_id: str | None = None
    source_recommended_action: PublicSyntheticFixtureReviewAction | None = None
    source_recommended_outcome: PublicSyntheticFixtureReviewOutcome | None = None
    source_decision_template_id: str | None = None
    accepted_required_gates: list[str] = Field(default_factory=list)
    rejected_or_revision_reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    append_only_history_ref: str
    checks: list[PublicSyntheticFixtureConversionReviewOutcomeCheck]
    required_next_gates: list[str]
    accepted_for_separate_fixture_pr: bool = False
    separate_fixture_generation_pr_required: bool = False
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_fixture_generation: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def conversion_review_outcome_report_status_matches_checks(
        self,
    ) -> "PublicSyntheticFixtureConversionReviewOutcomeReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "conversion_review_blocked_by_review_evidence" and not failed:
            raise ValueError("blocked conversion review outcome report requires failed checks")
        if self.status != "conversion_review_blocked_by_review_evidence" and failed:
            raise ValueError(
                "non-blocked conversion review outcome report cannot have failed checks"
            )
        if self.status == "conversion_review_recorded_separate_fixture_pr_required":
            if not (
                self.outcome == "approve_conversion_spec_for_separate_fixture_pr"
                and self.accepted_for_separate_fixture_pr
                and self.separate_fixture_generation_pr_required
            ):
                raise ValueError("separate fixture PR status requires approved outcome")
        if self.status != "conversion_review_recorded_separate_fixture_pr_required" and (
            self.accepted_for_separate_fixture_pr or self.separate_fixture_generation_pr_required
        ):
            raise ValueError("non-approval conversion review cannot require a fixture PR")
        required = {
            "append_only_conversion_review_outcome",
            "separate_synthetic_fixture_generation_pr_if_approved",
            "synthetic_fixture_gold_review",
            "red_team_identity_reconstruction_review",
            "legal_knowledge_runtime_owner_review_before_adapter",
            "no_public_payload_or_identity_contamination",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("conversion review outcome report is missing required gates")
        return self


class PublicSyntheticFixturePRPackageCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    conversion_spec_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class PublicSyntheticFixturePRPackageItem(StrictModel):
    schema_version: str = "0.1"
    package_item_id: str
    review_outcome_report_id: str
    conversion_review_id: str
    source_id: str
    conversion_spec_id: str
    target_fixture_family: PublicSyntheticFixtureFamily
    proposed_manual_action: Literal[
        "create_non_identifying_synthetic_fixture_in_separate_pr",
        "hold_no_fixture_change",
    ]
    source_methodology_ref: str
    proposed_fixture_scope: str
    allowed_structure_inputs: list[str]
    forbidden_inputs: list[str]
    identity_replacement_rules: list[str]
    field_transformation_rules: list[str]
    required_synthetic_gold_checks: list[str]
    required_red_team_checks: list[str]
    required_manual_steps: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_fixture_generation: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    github_pr_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def public_fixture_pr_item_is_reviewable(
        self,
    ) -> "PublicSyntheticFixturePRPackageItem":
        if not self.source_methodology_ref.strip():
            raise ValueError("public fixture PR package item requires source methodology ref")
        if not self.proposed_fixture_scope.strip():
            raise ValueError("public fixture PR package item requires fixture scope")
        if not self.allowed_structure_inputs:
            raise ValueError("public fixture PR package item requires allowed structure inputs")
        if not self.forbidden_inputs:
            raise ValueError("public fixture PR package item requires forbidden inputs")
        if not self.identity_replacement_rules:
            raise ValueError("public fixture PR package item requires identity replacement rules")
        if not self.field_transformation_rules:
            raise ValueError("public fixture PR package item requires transformation rules")
        if not self.required_synthetic_gold_checks:
            raise ValueError("public fixture PR package item requires synthetic gold checks")
        if not self.required_red_team_checks:
            raise ValueError("public fixture PR package item requires red-team checks")
        if not self.required_manual_steps:
            raise ValueError("public fixture PR package item requires manual steps")
        if not self.red_team_notes:
            raise ValueError("public fixture PR package item requires red-team notes")
        return self


class PublicSyntheticFixturePRPackageReport(StrictModel):
    schema_version: str = "0.1"
    fixture_pr_package_report_id: str
    status: Literal[
        "public_fixture_pr_package_ready_for_manual_pr",
        "no_public_fixture_pr_package_needed",
        "blocked_by_public_fixture_review_outcome",
    ]
    source_review_outcome_report_id: str
    source_review_outcome_report_ref: str
    source_review_outcome_status: Literal[
        "conversion_review_recorded_separate_fixture_pr_required",
        "conversion_review_recorded_revision_or_rejection",
        "conversion_review_recorded_more_information_required",
        "conversion_review_recorded_human_only_hold",
        "conversion_review_blocked_by_review_evidence",
    ]
    source_conversion_plan_id: str
    source_conversion_plan_ref: str
    source_conversion_plan_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_public_methodology_not_ready",
    ]
    conversion_review_id: str
    outcome: PublicSyntheticFixtureReviewOutcome
    source_id: str
    conversion_spec_id: str
    target_fixture_family: PublicSyntheticFixtureFamily | None = None
    item_count: int = Field(ge=0)
    ready_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    package_items: list[PublicSyntheticFixturePRPackageItem]
    package_item_output_ref: str | None = None
    checks: list[PublicSyntheticFixturePRPackageCheck]
    required_next_gates: list[str]
    manual_fixture_generation_pr_required: bool = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_fixture_generation: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    github_pr_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def public_fixture_pr_package_status_matches_items(
        self,
    ) -> "PublicSyntheticFixturePRPackageReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.item_count != len(self.package_items):
            raise ValueError("public fixture PR package item count does not match")
        if self.ready_item_count + self.blocked_item_count != self.item_count:
            raise ValueError("public fixture PR package ready/blocked counts do not add up")
        if self.status == "blocked_by_public_fixture_review_outcome" and not failed:
            raise ValueError("blocked public fixture PR package requires failed checks")
        if self.status != "blocked_by_public_fixture_review_outcome" and failed:
            raise ValueError("non-blocked public fixture PR package cannot have failed checks")
        if self.status == "public_fixture_pr_package_ready_for_manual_pr" and not (
            self.manual_fixture_generation_pr_required
            and self.item_count == 1
            and self.ready_item_count == self.item_count
            and self.target_fixture_family is not None
        ):
            raise ValueError("ready public fixture PR package requires one ready item")
        if self.status == "no_public_fixture_pr_package_needed" and (
            self.manual_fixture_generation_pr_required or self.item_count
        ):
            raise ValueError("no public fixture PR package needed cannot include package items")
        required = {
            "manual_fixture_generation_pr_review",
            "create_fixture_only_in_separate_pr",
            "synthetic_fixture_gold_review",
            "red_team_identity_reconstruction_review",
            "legal_knowledge_runtime_owner_review_before_adapter",
            "no_public_payload_or_identity_contamination",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("public fixture PR package is missing required gates")
        return self


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
    estimate_basis: Literal[
        "template_default",
        "driver_adjusted",
        "human_confirmed",
        "benchmark_cell",
        "unknown",
    ] = "template_default"
    estimate_basis_refs: list[str] = Field(default_factory=list)


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
        "labor_employment_budget_fact_report",
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
    total_hours_min: float | None = Field(default=None, ge=0)
    total_hours_max: float | None = Field(default=None, ge=0)
    subtotal_fees: float | None = None
    subtotal_fees_min: float | None = Field(default=None, ge=0)
    subtotal_fees_max: float | None = Field(default=None, ge=0)
    subtotal_expenses: float = Field(ge=0)
    subtotal_expenses_min: float | None = Field(default=None, ge=0)
    subtotal_expenses_max: float | None = Field(default=None, ge=0)
    contingency_percent: float = Field(ge=0)
    contingency_amount: float | None = None
    contingency_amount_min: float | None = Field(default=None, ge=0)
    contingency_amount_max: float | None = Field(default=None, ge=0)
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
    unknown_probability_mass: float | None = Field(default=None, ge=0, le=1)
    expected_total_min: float | None = None
    expected_total_max: float | None = None
    expected_value_method: Literal[
        "reviewed_probabilities",
        "bounded_unknown_mass",
        "not_computed",
    ] = "not_computed"
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
    rate_unknown_for_reshaped_role: bool = False
    over_cap_amount: float = Field(default=0, ge=0)
    rate_cap_delta: float = Field(default=0, ge=0)
    expense_cap_delta: float = Field(default=0, ge=0)
    disallowed_delta: float = Field(default=0, ge=0)
    staffing_rule_delta: float = Field(default=0, ge=0)
    delta_breakdown: dict[str, float] = Field(default_factory=dict)
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
    projection_pricing_status: Literal["priced", "hours_only_partial"] = "priced"
    total_delta: float = Field(default=0, ge=0)
    over_cap_amount: float = Field(ge=0)
    disallowed_amount: float = Field(default=0, ge=0)
    rate_cap_delta: float = Field(ge=0)
    expense_cap_delta: float = Field(ge=0)
    disallowed_delta: float = Field(default=0, ge=0)
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
    headline_subtotal_fees: float | None = None
    headline_subtotal_expenses: float | None = None
    headline_contingency_amount: float | None = None
    headline_total_proposed_budget: float | None = None
    headline_total_proposed_budget_min: float | None = None
    headline_total_proposed_budget_max: float | None = None
    expected_total_proposed_budget_min: float | None = None
    expected_total_proposed_budget_max: float | None = None
    unknown_probability_mass: float | None = Field(default=None, ge=0, le=1)
    expected_value_method: Literal[
        "reviewed_probabilities",
        "bounded_unknown_mass",
        "not_computed",
    ] = "not_computed"
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
    display_banner: dict[str, Any] = Field(default_factory=dict)
    approval_state: Literal["proposed_for_human_review"] = "proposed_for_human_review"
    not_authorized_for_client_submission: bool = True


class RateBenchmarkCell(StrictModel):
    schema_version: str = "0.1"
    benchmark_cell_id: str
    jurisdiction: str
    role: str
    experience_band: str
    year: int
    percentile: str
    value: float = Field(ge=0)
    benchmark_type: Literal[
        "public_procurement_proxy",
        "synthetic_candidate",
        "carrier_panel_candidate",
    ]
    source_url: str
    retrieved_at: str
    page_sha256: str
    quote_span: str
    license_note: str
    grade: Literal["A", "B", "C", "proxy_only", "ungraded"]
    human_grading_status: Literal["pending", "reviewed", "rejected"]
    candidate_only: Literal[True] = True
    not_authorized_as_carrier_rate: Literal[True] = True


class BenchmarkSnapshotManifest(StrictModel):
    schema_version: str = "0.1"
    benchmark_snapshot_id: str
    created_at: str
    source_owner: Literal["legal_knowledge_runtime", "local_candidate_fixture"]
    cells: list[RateBenchmarkCell]
    pinned_hash: str
    candidate_only: Literal[True] = True
    not_authorized_as_carrier_rate: Literal[True] = True

    @model_validator(mode="after")
    def benchmark_cell_ids_are_unique(self) -> "BenchmarkSnapshotManifest":
        cell_ids = [cell.benchmark_cell_id for cell in self.cells]
        if len(cell_ids) != len(set(cell_ids)):
            raise ValueError("benchmark snapshot cell ids must be unique")
        return self


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


BudgetActualVarianceOwnerTargetRepo = Literal[
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

BudgetActualVarianceOwnerAdoptionFocus = Literal[
    "semantic_actual_variance_label_review",
    "runtime_billing_actuals_workflow",
    "append_only_actual_variance_lake_admission",
]


class BudgetActualVarianceOwnerAdoptionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetActualVarianceOwnerAdoptionPacket(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_packet_id: str
    target_repo: BudgetActualVarianceOwnerTargetRepo
    adoption_focus: BudgetActualVarianceOwnerAdoptionFocus
    status: Literal["ready_for_owner_review", "blocked_by_actual_variance_evidence"]
    source_budget_actual_comparison_report_id: str
    source_budget_actual_comparison_report_ref: str
    source_budget_actual_comparison_status: Literal[
        "actuals_not_available",
        "passed",
        "variance_review_required",
    ]
    source_budget_actual_variance_ledger_report_id: str
    source_budget_actual_variance_ledger_report_ref: str
    source_budget_actual_variance_ledger_status: BudgetActualVarianceLedgerStatus
    run_id: str
    preflight_packet_id: str
    budget_proposal_id: str
    budget_revision_report_id: str | None = None
    actuals_source_ref: str | None = None
    comparison_scope: Literal["phase", "phase_and_code"]
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
    total_budgeted: float | None = None
    total_actual: float | None = None
    total_variance_amount: float | None = None
    total_variance_percent: float | None = None
    candidate_lake_event_labels: list[str] = Field(default_factory=list)
    variance_driver_candidates: list[str] = Field(default_factory=list)
    learning_disposition_candidates: list[str] = Field(default_factory=list)
    source_artifact_refs: list[str] = Field(default_factory=list)
    candidate_contract_refs: list[str] = Field(default_factory=list)
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def actual_variance_owner_packet_is_complete(
        self,
    ) -> "BudgetActualVarianceOwnerAdoptionPacket":
        if not self.required_owner_actions:
            raise ValueError("actual variance owner packet requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("actual variance owner packet requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("actual variance owner packet requires red-team notes")
        required = {
            "human_actual_variance_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "cross_repo_contract_validation_after_owner_changes",
            "no_intake_billing_lake_or_learning_write",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("actual variance owner packet is missing required gates")
        return self


class BudgetActualVarianceOwnerAdoptionReport(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_report_id: str
    status: Literal[
        "budget_actual_variance_owner_adoption_packets_ready",
        "blocked_by_budget_actual_variance_evidence",
    ]
    source_budget_actual_comparison_report_id: str
    source_budget_actual_comparison_report_ref: str
    source_budget_actual_comparison_status: Literal[
        "actuals_not_available",
        "passed",
        "variance_review_required",
    ]
    source_budget_actual_variance_ledger_report_id: str
    source_budget_actual_variance_ledger_report_ref: str
    source_budget_actual_variance_ledger_status: BudgetActualVarianceLedgerStatus
    target_repo_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    ready_packet_count: int = Field(ge=0)
    blocked_packet_count: int = Field(ge=0)
    target_repos: list[BudgetActualVarianceOwnerTargetRepo]
    packets: list[BudgetActualVarianceOwnerAdoptionPacket]
    packet_output_refs: list[str] = Field(default_factory=list)
    checks: list[BudgetActualVarianceOwnerAdoptionCheck]
    entry_count: int = Field(ge=0)
    variance_review_event_count: int = Field(ge=0)
    missing_actuals_event_count: int = Field(ge=0)
    actuals_without_budget_event_count: int = Field(ge=0)
    within_threshold_event_count: int = Field(ge=0)
    total_budgeted: float | None = None
    total_actual: float | None = None
    total_variance_amount: float | None = None
    candidate_lake_event_labels: list[str] = Field(default_factory=list)
    variance_driver_candidates: list[str] = Field(default_factory=list)
    learning_disposition_candidates: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def actual_variance_owner_report_counts_match(
        self,
    ) -> "BudgetActualVarianceOwnerAdoptionReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "budget_actual_variance_owner_adoption_packets_ready" and failed:
            raise ValueError("ready actual variance owner report cannot have failed checks")
        if self.status == "blocked_by_budget_actual_variance_evidence" and not failed:
            raise ValueError("blocked actual variance owner report requires failed checks")
        if self.packet_count != len(self.packets):
            raise ValueError("actual variance owner report packet_count mismatch")
        if self.packet_count != len(self.packet_output_refs):
            raise ValueError("actual variance owner report packet refs mismatch")
        if self.target_repo_count != len(self.target_repos):
            raise ValueError("actual variance owner report target_repo_count mismatch")
        if self.ready_packet_count != sum(
            1 for packet in self.packets if packet.status == "ready_for_owner_review"
        ):
            raise ValueError("actual variance owner ready count mismatch")
        if self.blocked_packet_count != sum(
            1 for packet in self.packets if packet.status == "blocked_by_actual_variance_evidence"
        ):
            raise ValueError("actual variance owner blocked count mismatch")
        required = {
            "human_actual_variance_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "cross_repo_contract_validation_after_owner_changes",
            "no_intake_billing_lake_or_learning_write",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("actual variance owner report is missing required gates")
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


BudgetFixtureBindingHandoffDisposition = Literal[
    "ready_for_human_fixture_update_review",
    "blocked_pending_approved_outcome",
    "blocked_missing_approved_outputs",
]

BudgetFixtureBindingHandoffReportStatus = Literal[
    "fixture_binding_handoff_ready_for_human_review",
    "fixture_binding_handoff_blocked",
    "no_fixture_binding_handoff_candidates",
]


class BudgetFixtureBindingHandoffItem(StrictModel):
    schema_version: str = "0.1"
    handoff_item_id: str
    fixture_binding_candidate_id: str
    fixture_binding_candidate_report_id: str
    review_packet_id: str
    review_outcome_report_id: str
    replay_execution_report_id: str
    replay_case_id: str
    source_artifact_ref: str
    artifact_kind: BudgetCalibrationArtifactKind
    approved_output_refs: list[str] = Field(default_factory=list)
    proposed_target_fixture_refs: list[str] = Field(default_factory=list)
    proposed_binding_action: BudgetFixtureBindingAction
    source_candidate_status: BudgetFixtureBindingCandidateStatus
    disposition: BudgetFixtureBindingHandoffDisposition
    target_owner: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    recommended_owner_actions: list[str]
    why: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    fixture_update_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    fixture_update_authorized: Literal[False] = False
    fixture_update_pr_created: Literal[False] = False
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
    def disposition_matches_candidate_status(self) -> "BudgetFixtureBindingHandoffItem":
        if (
            self.source_candidate_status == "candidate_ready_for_fixture_update_review"
            and self.disposition != "ready_for_human_fixture_update_review"
        ):
            raise ValueError("ready fixture-binding candidates must create ready handoff items")
        if (
            self.source_candidate_status == "blocked_pending_approved_outcome"
            and self.disposition != "blocked_pending_approved_outcome"
        ):
            raise ValueError("pending-outcome fixture-binding candidates must stay blocked")
        if (
            self.source_candidate_status == "blocked_missing_approved_outputs"
            and self.disposition != "blocked_missing_approved_outputs"
        ):
            raise ValueError("missing-output fixture-binding candidates must stay blocked")
        if self.disposition == "ready_for_human_fixture_update_review" and not (
            self.approved_output_refs and self.proposed_target_fixture_refs
        ):
            raise ValueError("ready fixture-binding handoffs require outputs and target refs")
        if not self.recommended_owner_actions:
            raise ValueError("fixture-binding handoff item requires owner actions")
        if not self.red_team_notes:
            raise ValueError("fixture-binding handoff item requires red-team notes")
        return self


class BudgetFixtureBindingHandoffReport(StrictModel):
    schema_version: str = "0.1"
    fixture_binding_handoff_report_id: str
    source_fixture_binding_candidate_report_id: str
    source_fixture_binding_candidate_report_ref: str
    source_fixture_binding_candidate_report_status: BudgetFixtureBindingCandidateReportStatus
    status: BudgetFixtureBindingHandoffReportStatus
    item_count: int = Field(ge=0)
    ready_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    target_owner: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    handoff_items: list[BudgetFixtureBindingHandoffItem]
    handoff_item_output_ref: str | None = None
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    fixture_update_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    fixture_update_authorized: Literal[False] = False
    fixture_update_pr_created: Literal[False] = False
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
    def handoff_counts_match(self) -> "BudgetFixtureBindingHandoffReport":
        if self.item_count != len(self.handoff_items):
            raise ValueError("fixture-binding handoff item count does not match")
        ready_count = sum(
            1
            for item in self.handoff_items
            if item.disposition == "ready_for_human_fixture_update_review"
        )
        if self.ready_item_count != ready_count:
            raise ValueError("fixture-binding handoff ready count does not match")
        if self.blocked_item_count != self.item_count - self.ready_item_count:
            raise ValueError("fixture-binding handoff blocked count does not match")
        if self.status == "fixture_binding_handoff_ready_for_human_review" and (
            not self.ready_item_count or self.blocked_item_count
        ):
            raise ValueError("ready fixture-binding handoff cannot include blocked items")
        if self.status == "fixture_binding_handoff_blocked" and not self.blocked_item_count:
            raise ValueError("blocked fixture-binding handoff requires blocked items")
        if self.status == "no_fixture_binding_handoff_candidates" and self.handoff_items:
            raise ValueError("no-candidate fixture-binding handoff cannot include items")
        return self


class BudgetCalibrationReadinessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetCalibrationReadinessReport(StrictModel):
    schema_version: str = "0.1"
    budget_calibration_readiness_report_id: str
    status: Literal[
        "ready_for_manual_fixture_update_review",
        "blocked_by_calibration_chain",
    ]
    corpus_report_id: str
    replay_plan_id: str
    replay_execution_report_id: str
    review_packet_id: str
    review_outcome_report_id: str
    fixture_binding_candidate_report_id: str
    fixture_binding_handoff_report_id: str
    replay_case_id: str
    source_corpus_report_ref: str
    source_replay_plan_ref: str
    source_replay_execution_report_ref: str
    source_review_packet_ref: str
    source_review_outcome_report_ref: str
    source_fixture_binding_candidate_report_ref: str
    source_fixture_binding_handoff_report_ref: str
    ready_fixture_binding_handoff_count: int = Field(ge=0)
    blocked_fixture_binding_handoff_count: int = Field(ge=0)
    approved_output_refs: list[str] = Field(default_factory=list)
    proposed_target_fixture_refs: list[str] = Field(default_factory=list)
    checks: list[BudgetCalibrationReadinessCheck]
    required_next_gates: list[str]
    manual_fixture_update_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    fixture_update_authorized: Literal[False] = False
    fixture_update_pr_created: Literal[False] = False
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
    def readiness_status_matches_checks(self) -> "BudgetCalibrationReadinessReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "ready_for_manual_fixture_update_review" and (
            failed
            or not self.ready_fixture_binding_handoff_count
            or self.blocked_fixture_binding_handoff_count
        ):
            raise ValueError("ready calibration readiness report cannot include blockers")
        if self.status == "blocked_by_calibration_chain" and not failed:
            raise ValueError("blocked calibration readiness report requires failed checks")
        required = {
            "human_fixture_update_review",
            "separate_fixture_update_pr_if_accepted",
            "append_only_fixture_update_record",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget calibration readiness report is missing required gates")
        return self


class BudgetCalibrationStarterPackStep(StrictModel):
    step_id: str
    status: Literal["passed", "failed"]
    artifact_ref: str
    notes: list[str] = Field(default_factory=list)


class BudgetCalibrationStarterPackReport(StrictModel):
    schema_version: str = "0.1"
    starter_pack_report_id: str
    status: Literal[
        "starter_pack_ready_for_manual_fixture_update_review",
        "blocked_by_starter_pack",
    ]
    selected_replay_case_id: str
    selected_artifact_kind: BudgetCalibrationArtifactKind
    corpus_report_ref: str
    replay_plan_ref: str
    replay_execution_report_ref: str
    replay_review_packet_ref: str
    synthetic_review_outcome_input_ref: str
    replay_review_outcome_report_ref: str
    fixture_binding_candidate_report_ref: str
    fixture_binding_handoff_report_ref: str
    budget_calibration_readiness_report_ref: str
    budget_calibration_readiness_status: Literal[
        "ready_for_manual_fixture_update_review",
        "blocked_by_calibration_chain",
    ]
    step_count: int = Field(ge=0)
    failed_step_count: int = Field(ge=0)
    steps: list[BudgetCalibrationStarterPackStep]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    qa_fixture_review_only: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    fixture_update_authorized: Literal[False] = False
    fixture_update_pr_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_binding_applied: Literal[False] = False
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
    def starter_pack_counts_and_status_match(self) -> "BudgetCalibrationStarterPackReport":
        failed = [step for step in self.steps if step.status == "failed"]
        if self.step_count != len(self.steps):
            raise ValueError("starter pack step count does not match")
        if self.failed_step_count != len(failed):
            raise ValueError("starter pack failed step count does not match")
        if self.status == "starter_pack_ready_for_manual_fixture_update_review" and (
            failed
            or self.budget_calibration_readiness_status != "ready_for_manual_fixture_update_review"
        ):
            raise ValueError("ready starter pack requires passed steps and readiness")
        if self.status == "blocked_by_starter_pack" and not (
            failed or self.budget_calibration_readiness_status == "blocked_by_calibration_chain"
        ):
            raise ValueError("blocked starter pack requires failed steps or blocked readiness")
        required = {
            "inspect_synthetic_qa_review_outcome",
            "manual_fixture_update_review",
            "no_learning_without_reviewed_gate_and_shadow_eval",
            "no_fixture_mutation_from_starter_pack",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("starter pack is missing required next gates")
        return self


BudgetFixtureUpdateReviewDecision = Literal[
    "accept_for_separate_fixture_update_pr",
    "accept_with_corrections_for_separate_fixture_update_pr",
    "reject_fixture_update",
    "needs_more_information",
]


class BudgetFixtureUpdateReviewCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetFixtureUpdateReviewRecord(StrictModel):
    schema_version: str = "0.1"
    fixture_update_review_id: str
    budget_calibration_readiness_report_id: str
    fixture_binding_handoff_report_id: str
    replay_case_id: str
    reviewer_id: str
    reviewed_at: str
    decision: BudgetFixtureUpdateReviewDecision
    decision_reason: str
    accepted_output_refs: list[str] = Field(default_factory=list)
    rejected_output_refs: list[str] = Field(default_factory=list)
    target_fixture_refs: list[str] = Field(default_factory=list)
    reviewer_corrections: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    reviewed_red_team_notes: list[str] = Field(default_factory=list)
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    source_readiness_report_mutated: Literal[False] = False
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    fixture_update_pr_created: Literal[False] = False
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
    def fixture_update_review_decision_is_complete(
        self,
    ) -> "BudgetFixtureUpdateReviewRecord":
        if not self.reviewer_id.strip():
            raise ValueError("fixture update review requires reviewer_id")
        if not self.reviewed_at.strip():
            raise ValueError("fixture update review requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("fixture update review requires decision_reason")
        accept_decisions = {
            "accept_for_separate_fixture_update_pr",
            "accept_with_corrections_for_separate_fixture_update_pr",
        }
        if self.decision in accept_decisions and not (
            self.accepted_output_refs and self.target_fixture_refs
        ):
            raise ValueError("accepted fixture update reviews require output and target refs")
        if (
            self.decision == "accept_with_corrections_for_separate_fixture_update_pr"
            and not self.reviewer_corrections
        ):
            raise ValueError("accept_with_corrections requires reviewer_corrections")
        return self


class BudgetFixtureUpdateReviewReport(StrictModel):
    schema_version: str = "0.1"
    fixture_update_review_report_id: str
    status: Literal[
        "fixture_update_review_recorded_separate_pr_required",
        "fixture_update_review_recorded_no_fixture_pr",
        "blocked_by_fixture_update_review_evidence",
    ]
    source_budget_calibration_readiness_report_id: str
    source_budget_calibration_readiness_report_ref: str
    source_budget_calibration_readiness_status: Literal[
        "ready_for_manual_fixture_update_review",
        "blocked_by_calibration_chain",
    ]
    fixture_binding_handoff_report_id: str
    replay_case_id: str
    fixture_update_review_id: str
    decision: BudgetFixtureUpdateReviewDecision
    decision_reason: str
    accepted_output_refs: list[str] = Field(default_factory=list)
    rejected_output_refs: list[str] = Field(default_factory=list)
    target_fixture_refs: list[str] = Field(default_factory=list)
    reviewer_corrections: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    reviewed_red_team_notes: list[str] = Field(default_factory=list)
    append_only_history_ref: str
    checks: list[BudgetFixtureUpdateReviewCheck]
    required_next_gates: list[str]
    accepted_for_fixture_update_pr: bool = False
    separate_fixture_update_pr_required: bool = False
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    source_readiness_report_mutated: Literal[False] = False
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    fixture_update_pr_created: Literal[False] = False
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
    def fixture_update_review_status_matches_checks(
        self,
    ) -> "BudgetFixtureUpdateReviewReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "blocked_by_fixture_update_review_evidence" and not failed:
            raise ValueError("blocked fixture update review report requires failed checks")
        if self.status != "blocked_by_fixture_update_review_evidence" and failed:
            raise ValueError("non-blocked fixture update review report cannot have failed checks")
        if self.status == "fixture_update_review_recorded_separate_pr_required":
            if not (
                self.accepted_for_fixture_update_pr
                and self.separate_fixture_update_pr_required
                and self.accepted_output_refs
                and self.target_fixture_refs
            ):
                raise ValueError("separate fixture PR review requires accepted refs")
        if self.status == "fixture_update_review_recorded_no_fixture_pr" and (
            self.accepted_for_fixture_update_pr or self.separate_fixture_update_pr_required
        ):
            raise ValueError("no-fixture-PR review cannot require a fixture update PR")
        required = {
            "append_only_fixture_update_review_record",
            "separate_fixture_update_pr_if_accepted",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("fixture update review report is missing required gates")
        return self


class BudgetFixtureUpdatePRPackageCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetFixtureUpdatePRPackageItem(StrictModel):
    schema_version: str = "0.1"
    package_item_id: str
    fixture_update_review_id: str
    decision: BudgetFixtureUpdateReviewDecision
    accepted_output_refs: list[str]
    target_fixture_ref: str
    proposed_manual_action: Literal[
        "update_synthetic_fixture_in_separate_pr",
        "create_synthetic_fixture_in_separate_pr",
        "hold_no_fixture_change",
    ]
    manual_patch_summary: str
    reviewer_corrections: list[str] = Field(default_factory=list)
    required_manual_steps: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    github_pr_created: Literal[False] = False
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
    def fixture_update_pr_item_is_reviewable(self) -> "BudgetFixtureUpdatePRPackageItem":
        if not self.accepted_output_refs:
            raise ValueError("fixture update PR package item requires accepted output refs")
        if not self.target_fixture_ref.strip():
            raise ValueError("fixture update PR package item requires target fixture ref")
        if not self.manual_patch_summary.strip():
            raise ValueError("fixture update PR package item requires manual patch summary")
        if not self.required_manual_steps:
            raise ValueError("fixture update PR package item requires manual steps")
        if not self.red_team_notes:
            raise ValueError("fixture update PR package item requires red-team notes")
        return self


class BudgetFixtureUpdatePRPackageReport(StrictModel):
    schema_version: str = "0.1"
    fixture_update_pr_package_report_id: str
    status: Literal[
        "fixture_update_pr_package_ready_for_manual_pr",
        "no_fixture_update_pr_package_needed",
        "blocked_by_fixture_update_review",
    ]
    source_budget_fixture_update_review_report_id: str
    source_budget_fixture_update_review_report_ref: str
    source_budget_fixture_update_review_status: Literal[
        "fixture_update_review_recorded_separate_pr_required",
        "fixture_update_review_recorded_no_fixture_pr",
        "blocked_by_fixture_update_review_evidence",
    ]
    fixture_update_review_id: str
    decision: BudgetFixtureUpdateReviewDecision
    item_count: int = Field(ge=0)
    ready_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    accepted_output_refs: list[str] = Field(default_factory=list)
    target_fixture_refs: list[str] = Field(default_factory=list)
    package_items: list[BudgetFixtureUpdatePRPackageItem]
    package_item_output_ref: str | None = None
    checks: list[BudgetFixtureUpdatePRPackageCheck]
    required_next_gates: list[str]
    manual_fixture_update_pr_required: bool = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    github_pr_created: Literal[False] = False
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
    def fixture_update_pr_package_status_matches_items(
        self,
    ) -> "BudgetFixtureUpdatePRPackageReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.item_count != len(self.package_items):
            raise ValueError("fixture update PR package item count does not match")
        if self.ready_item_count + self.blocked_item_count != self.item_count:
            raise ValueError("fixture update PR package ready/blocked counts do not add up")
        if self.status == "blocked_by_fixture_update_review" and not failed:
            raise ValueError("blocked fixture update PR package requires failed checks")
        if self.status != "blocked_by_fixture_update_review" and failed:
            raise ValueError("non-blocked fixture update PR package cannot have failed checks")
        if self.status == "fixture_update_pr_package_ready_for_manual_pr" and not (
            self.manual_fixture_update_pr_required
            and self.item_count > 0
            and self.ready_item_count == self.item_count
            and self.accepted_output_refs
            and self.target_fixture_refs
        ):
            raise ValueError("ready fixture update PR package requires ready items and refs")
        if self.status == "no_fixture_update_pr_package_needed" and (
            self.manual_fixture_update_pr_required or self.item_count
        ):
            raise ValueError("no fixture update PR package needed cannot include package items")
        required = {
            "manual_fixture_update_pr_review",
            "apply_fixture_update_only_in_separate_pr",
            "run_regression_after_fixture_update_pr",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("fixture update PR package is missing required gates")
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
    labor_employment_budget_fact_report_ref: str | None = None
    labor_employment_budget_readiness_state: (
        Literal[
            "blocked_missing_critical_facts",
            "range_only_pending_human_review",
            "candidate_ready_for_budget_review",
        ]
        | None
    ) = None
    labor_employment_budget_treatment: Literal[
        "not_applicable",
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
        "candidate_ready_for_budget_review",
    ] = "not_applicable"
    labor_employment_critical_gap_count: int = Field(default=0, ge=0)
    labor_employment_required_human_questions: list[str] = Field(default_factory=list)
    prohibited_outputs: list[str]
    external_writes_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def budget_precondition_status_matches_checks(self) -> "BudgetPreconditionReport":
        failed = [check.check_id for check in self.checks if check.status == "failed"]
        if self.status == "passed" and failed:
            raise ValueError("passed budget precondition report cannot include failed checks")
        if self.status == "failed" and not failed:
            raise ValueError("failed budget precondition report requires failed checks")
        if (
            self.labor_employment_budget_treatment != "not_applicable"
            and not self.labor_employment_budget_fact_report_ref
        ):
            raise ValueError("L&E budget treatment requires a fact report ref")
        if self.labor_employment_critical_gap_count > 0:
            if self.status != "failed":
                raise ValueError("L&E critical fact gaps must fail the budget precondition gate")
            if self.blocked_state != "labor_employment_budget_facts_blocked":
                raise ValueError("L&E critical fact gaps require the L&E blocked state")
            if self.labor_employment_budget_treatment != "block_amount_budget":
                raise ValueError("L&E critical fact gaps require block_amount_budget treatment")
        if self.blocked_state == "labor_employment_budget_facts_blocked":
            if not self.labor_employment_budget_fact_report_ref:
                raise ValueError("L&E blocked state requires a fact report ref")
            if self.labor_employment_critical_gap_count == 0:
                raise ValueError("L&E blocked state requires at least one critical gap")
        return self


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


class LearningShadowEvalFixtureReviewItem(StrictModel):
    proposed_change_id: str
    candidate_id: str
    evaluation_outcome: Literal["passed", "failed", "blocked"]
    passed_eval_suites: list[str] = Field(default_factory=list)
    failed_eval_suites: list[str] = Field(default_factory=list)
    passed_regression_guardrails: list[str] = Field(default_factory=list)
    failed_regression_guardrails: list[str] = Field(default_factory=list)
    baseline_behavior_ref: str | None = None
    proposed_behavior_ref: str | None = None
    expected_behavior_summary: str | None = None
    observed_behavior_summary: str | None = None
    support_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def review_item_evidence_required(self) -> "LearningShadowEvalFixtureReviewItem":
        if not self.support_refs:
            raise ValueError("shadow eval fixture review item requires support_refs")
        if self.evaluation_outcome == "passed":
            if not self.passed_eval_suites:
                raise ValueError("passed shadow eval review item requires passed eval suites")
            if not self.passed_regression_guardrails:
                raise ValueError("passed shadow eval review item requires passed guardrails")
            if self.failed_eval_suites or self.failed_regression_guardrails:
                raise ValueError("passed shadow eval review item cannot include failed checks")
        return self


class LearningShadowEvalFixtureReviewRecord(StrictModel):
    schema_version: str = "0.1"
    shadow_eval_fixture_review_id: str
    proposed_change_set_id: str
    reviewer_id: str
    reviewer_role: str | None = None
    reviewed_at: str
    decision: Literal[
        "record_fixture_results",
        "record_partial_fixture_results",
        "reject_fixture_results",
    ]
    decision_reason: str
    items: list[LearningShadowEvalFixtureReviewItem] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    reviewed_red_team_notes: list[str] = Field(default_factory=list)
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
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

    @model_validator(mode="after")
    def review_record_evidence_required(self) -> "LearningShadowEvalFixtureReviewRecord":
        if not self.decision_reason:
            raise ValueError("shadow eval fixture review record requires a decision reason")
        if not self.evidence_refs:
            raise ValueError("shadow eval fixture review record requires evidence_refs")
        if not self.required_followups:
            raise ValueError("shadow eval fixture review record requires followups")
        if not self.reviewed_red_team_notes:
            raise ValueError("shadow eval fixture review record requires red-team notes")
        if self.decision in {"record_fixture_results", "record_partial_fixture_results"}:
            if not self.items:
                raise ValueError("shadow eval fixture review record requires review items")
        if self.decision == "record_fixture_results" and any(
            item.evaluation_outcome != "passed" for item in self.items
        ):
            raise ValueError("record_fixture_results requires all review items to pass")
        return self


class LearningShadowEvalFixtureEvidenceCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    proposed_change_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LearningShadowEvalFixtureEvidenceReport(StrictModel):
    schema_version: str = "0.1"
    fixture_evidence_report_id: str
    status: Literal[
        "fixture_results_recorded",
        "fixture_results_partially_recorded",
        "blocked_by_fixture_review",
    ]
    source_proposed_change_set_id: str
    source_proposed_change_set_ref: str
    source_review_record_id: str
    source_review_record_ref: str
    reviewer_id: str
    reviewed_at: str
    change_count: int = Field(ge=0)
    reviewed_item_count: int = Field(ge=0)
    passed_item_count: int = Field(ge=0)
    failed_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    missing_item_count: int = Field(ge=0)
    fixture_result_refs: list[str]
    fixture_results: list[LearningShadowEvalFixtureResult]
    checks: list[LearningShadowEvalFixtureEvidenceCheck]
    required_next_gates: list[str]
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    proposed_changes_applied_by_fixture_recorder: Literal[False] = False
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
    def evidence_counts_match(self) -> "LearningShadowEvalFixtureEvidenceReport":
        if self.reviewed_item_count != (
            self.passed_item_count + self.failed_item_count + self.blocked_item_count
        ):
            raise ValueError("shadow eval fixture evidence item counts do not match")
        if self.change_count != self.reviewed_item_count + self.missing_item_count:
            raise ValueError("shadow eval fixture evidence change count does not match")
        if self.passed_item_count != len(self.fixture_results):
            raise ValueError("shadow eval fixture evidence result count must match passed items")
        if len(self.fixture_result_refs) != len(self.fixture_results):
            raise ValueError("shadow eval fixture evidence refs must match results")
        if self.status == "fixture_results_recorded":
            if self.missing_item_count or self.failed_item_count or self.blocked_item_count:
                raise ValueError("recorded fixture evidence cannot have missing or blocked items")
            if len(self.fixture_result_refs) != self.change_count:
                raise ValueError("recorded fixture evidence requires one fixture per change")
        if self.status == "blocked_by_fixture_review" and not any(
            check.status in {"blocked", "failed"} for check in self.checks
        ):
            raise ValueError("blocked fixture evidence requires blocking or failed checks")
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
    target_owner_repos: list[str]
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
        "blocked_missing_or_failed_lake_bundle",
        "blocked_missing_or_failed_calibration_readiness",
        "blocked_missing_or_failed_fixture_update_review",
        "blocked_missing_or_failed_fixture_update_pr_package",
    ]
    review_readiness: Literal[
        "ready_for_human_pr_review_not_auto_marked",
        "not_ready_missing_local_artifacts",
        "not_ready_learning_artifact_chain_blocked",
        "not_ready_lake_bundle_blocked",
        "not_ready_calibration_readiness_blocked",
        "not_ready_fixture_update_review_blocked",
        "not_ready_fixture_update_pr_package_blocked",
    ]
    source_owner_handoff_report_ref: str
    source_budget_event_lake_bundle_report_ref: str
    source_budget_calibration_readiness_report_ref: str
    source_budget_fixture_update_review_report_ref: str
    source_budget_fixture_update_pr_package_report_ref: str
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


class PRReviewChecklistItem(StrictModel):
    item_id: str
    section: Literal[
        "readiness_audit",
        "lake_bundle",
        "learning_chain",
        "calibration_chain",
        "fixture_update_review",
        "fixture_update_pr_package",
        "authority_boundary",
        "validation",
        "external_owner_review",
        "human_decision",
    ]
    title: str
    recommendation: Literal[
        "inspect",
        "confirm",
        "block_until_resolved",
        "external_owner_review",
    ]
    why: str
    artifact_refs: list[str] = Field(default_factory=list)
    required_before_ready: bool = True
    red_team_note: str
    required_human_decision: str | None = None
    status: Literal["open_for_human_review", "blocked_by_readiness_audit"] = "open_for_human_review"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def blocked_items_must_block(self) -> "PRReviewChecklistItem":
        if self.status == "blocked_by_readiness_audit" and (
            self.recommendation != "block_until_resolved"
        ):
            raise ValueError("blocked checklist item must recommend block_until_resolved")
        if self.recommendation == "block_until_resolved" and (
            self.status != "blocked_by_readiness_audit"
        ):
            raise ValueError("blocking checklist item must be blocked_by_readiness_audit")
        if not self.why:
            raise ValueError("checklist item requires why")
        if not self.red_team_note:
            raise ValueError("checklist item requires red-team note")
        return self


class PRReviewChecklistReport(StrictModel):
    schema_version: str = "0.1"
    checklist_report_id: str
    source_readiness_audit_report_ref: str
    source_readiness_audit_report_id: str
    source_readiness_status: Literal[
        "ready_for_pr_review_external_adoption_required",
        "incomplete_missing_local_artifacts",
        "blocked_missing_or_failed_learning_artifacts",
        "blocked_missing_or_failed_lake_bundle",
        "blocked_missing_or_failed_calibration_readiness",
        "blocked_missing_or_failed_fixture_update_review",
        "blocked_missing_or_failed_fixture_update_pr_package",
    ]
    source_review_readiness: Literal[
        "ready_for_human_pr_review_not_auto_marked",
        "not_ready_missing_local_artifacts",
        "not_ready_learning_artifact_chain_blocked",
        "not_ready_lake_bundle_blocked",
        "not_ready_calibration_readiness_blocked",
        "not_ready_fixture_update_review_blocked",
        "not_ready_fixture_update_pr_package_blocked",
    ]
    status: Literal["ready_for_human_pr_review", "blocked_by_readiness_audit"]
    recommendation: Literal[
        "eligible_for_human_to_mark_ready_after_review",
        "keep_draft_until_human_review_complete",
    ]
    item_count: int = Field(ge=0)
    blocking_item_count: int = Field(ge=0)
    items: list[PRReviewChecklistItem]
    required_human_decisions: list[str]
    validation_commands: list[str]
    external_adoption_target_repos: list[LearningTargetOwner]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_completion_scope: Literal["synthetic_candidate_only"] = "synthetic_candidate_only"
    pr_marked_ready: Literal[False] = False
    github_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
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
    def checklist_counts_and_boundaries_match(self) -> "PRReviewChecklistReport":
        if self.item_count != len(self.items):
            raise ValueError("PR review checklist item count does not match")
        counted_blocking = sum(
            1 for item in self.items if item.recommendation == "block_until_resolved"
        )
        if self.blocking_item_count != counted_blocking:
            raise ValueError("PR review checklist blocking count does not match")
        if not self.required_human_decisions:
            raise ValueError("PR review checklist requires human decisions")
        if not self.validation_commands:
            raise ValueError("PR review checklist requires validation commands")
        if self.status == "ready_for_human_pr_review":
            if self.source_readiness_status != "ready_for_pr_review_external_adoption_required":
                raise ValueError("ready PR review checklist requires ready readiness audit")
            if self.source_review_readiness != "ready_for_human_pr_review_not_auto_marked":
                raise ValueError("ready PR review checklist requires ready review_readiness")
            if self.blocking_item_count:
                raise ValueError("ready PR review checklist cannot include blocking items")
            if self.recommendation != "eligible_for_human_to_mark_ready_after_review":
                raise ValueError("ready PR review checklist has invalid recommendation")
        if self.status == "blocked_by_readiness_audit":
            if not self.blocking_item_count:
                raise ValueError("blocked PR review checklist requires a blocking item")
            if self.recommendation != "keep_draft_until_human_review_complete":
                raise ValueError("blocked PR review checklist must keep draft")
        return self


PRReadinessDecision = Literal[
    "mark_ready_for_review",
    "keep_draft",
    "needs_more_work",
    "split_followup_work",
]


class PRReadinessDecisionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class PRReadinessDecisionRecord(StrictModel):
    schema_version: str = "0.1"
    pr_readiness_decision_id: str
    checklist_report_id: str
    closeout_report_id: str
    observed_pr_number: int | None = None
    observed_pr_url: str | None = None
    observed_pr_state: Literal["draft", "ready_for_review", "merged", "not_supplied"] = (
        "not_supplied"
    )
    reviewer_id: str
    reviewed_at: str
    decision: PRReadinessDecision
    decision_reason: str
    accepted_checklist_item_ids: list[str] = Field(default_factory=list)
    validation_evidence_refs: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    red_team_notes: list[str] = Field(default_factory=list)
    supersedes_pr_readiness_decision_id: str | None = None
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    manual_github_action_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    pr_marked_ready: Literal[False] = False
    github_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def pr_readiness_decision_is_complete(self) -> "PRReadinessDecisionRecord":
        if not self.pr_readiness_decision_id.strip():
            raise ValueError("PR readiness decision requires pr_readiness_decision_id")
        if not self.reviewer_id.strip():
            raise ValueError("PR readiness decision requires reviewer_id")
        if not self.reviewed_at.strip():
            raise ValueError("PR readiness decision requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("PR readiness decision requires decision_reason")
        if self.decision == "mark_ready_for_review":
            if not self.accepted_checklist_item_ids:
                raise ValueError("mark_ready_for_review requires accepted checklist item IDs")
            if not self.validation_evidence_refs:
                raise ValueError("mark_ready_for_review requires validation evidence refs")
        if self.decision in {"keep_draft", "needs_more_work", "split_followup_work"}:
            if not self.required_followups:
                raise ValueError("draft/work decisions require required_followups")
        if not self.red_team_notes:
            raise ValueError("PR readiness decision requires red-team notes")
        return self


class PRReadinessDecisionReport(StrictModel):
    schema_version: str = "0.1"
    pr_readiness_decision_report_id: str
    status: Literal[
        "pr_readiness_decision_recorded_manual_ready_action_required",
        "pr_readiness_decision_recorded_keep_draft",
        "pr_readiness_decision_recorded_more_work_required",
        "pr_readiness_decision_recorded_split_followup_work",
        "blocked_by_pr_readiness_decision_evidence",
    ]
    source_pr_review_checklist_id: str
    source_pr_review_checklist_ref: str
    source_pr_review_checklist_status: Literal[
        "ready_for_human_pr_review",
        "blocked_by_readiness_audit",
    ]
    source_closeout_report_id: str
    source_closeout_report_ref: str
    source_closeout_status: Literal[
        "intake_local_closeout_ready_manual_actions_required",
        "blocked_by_closeout_evidence",
    ]
    pr_readiness_decision_id: str
    observed_pr_number: int | None = None
    observed_pr_url: str | None = None
    observed_pr_state: Literal["draft", "ready_for_review", "merged", "not_supplied"] = (
        "not_supplied"
    )
    reviewer_id: str
    decision: PRReadinessDecision
    decision_reason: str
    accepted_checklist_item_ids: list[str] = Field(default_factory=list)
    validation_evidence_refs: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    red_team_notes: list[str] = Field(default_factory=list)
    append_only_history_ref: str
    checks: list[PRReadinessDecisionCheck]
    required_next_gates: list[str]
    manual_ready_action_required: bool = False
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    manual_github_action_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    pr_marked_ready: Literal[False] = False
    github_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def pr_readiness_decision_report_status_matches_checks(
        self,
    ) -> "PRReadinessDecisionReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "blocked_by_pr_readiness_decision_evidence" and not failed:
            raise ValueError("blocked PR readiness decision report requires failed checks")
        if self.status != "blocked_by_pr_readiness_decision_evidence" and failed:
            raise ValueError("non-blocked PR readiness decision report cannot have failed checks")
        if self.status == "pr_readiness_decision_recorded_manual_ready_action_required":
            if not (self.decision == "mark_ready_for_review" and self.manual_ready_action_required):
                raise ValueError("manual-ready status requires mark_ready_for_review decision")
        if self.status != "pr_readiness_decision_recorded_manual_ready_action_required":
            if self.manual_ready_action_required:
                raise ValueError("non-ready PR decision cannot require manual ready action")
        required = {
            "manual_github_pr_state_change_if_accepted",
            "owner_issue_creation_remains_manual",
            "cross_repo_validation_after_owner_changes",
            "no_automated_github_write",
            "no_sibling_repo_or_lake_write",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("PR readiness decision report is missing required gates")
        return self


RemainingRoadmapOwner = Literal[
    "Human reviewer",
    "LawFirm-os-intake",
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
    "Cross-repo owners",
]

RemainingRoadmapWorkstream = Literal[
    "human_pr_review",
    "manual_owner_issue_creation",
    "owner_triage",
    "semantic_contract_promotion",
    "runtime_orchestration_adoption",
    "exception_lake_admission",
    "fixture_and_eval_expansion",
    "public_source_methodology",
    "skill_registry_review",
    "real_data_pilot_governance",
]

RemainingRoadmapEffort = Literal["easy", "medium", "large"]
RemainingRoadmapRisk = Literal["low", "medium", "high", "critical"]
RemainingRoadmapGate = Literal[
    "local_candidate",
    "manual_human_review",
    "owner_repo_review",
    "cross_repo_validation",
    "governance_approval",
    "production_pilot_approval",
]
RemainingRoadmapItemStatus = Literal[
    "ready_to_start",
    "blocked_until_human_decision",
    "blocked_until_owner_action",
    "deferred_governance_required",
    "completed_by_observed_merged_pr",
]


class RemainingRoadmapCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class RemainingRoadmapItem(StrictModel):
    item_id: str
    title: str
    workstream: RemainingRoadmapWorkstream
    owner: RemainingRoadmapOwner
    effort: RemainingRoadmapEffort
    risk: RemainingRoadmapRisk
    gate: RemainingRoadmapGate
    status: RemainingRoadmapItemStatus
    why_now: str
    source_evidence_refs: list[str]
    required_next_actions: list[str]
    acceptance_evidence_required: list[str]
    red_team_notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    no_external_action_performed: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def remaining_roadmap_item_is_actionable(self) -> "RemainingRoadmapItem":
        if not self.source_evidence_refs:
            raise ValueError("remaining roadmap item requires source evidence refs")
        if not self.required_next_actions:
            raise ValueError("remaining roadmap item requires next actions")
        if not self.acceptance_evidence_required:
            raise ValueError("remaining roadmap item requires acceptance evidence")
        if not self.red_team_notes:
            raise ValueError("remaining roadmap item requires red-team notes")
        if self.risk == "critical" and self.gate in {"local_candidate", "manual_human_review"}:
            raise ValueError("critical remaining roadmap items require owner/governance gates")
        return self


class RemainingRoadmapReport(StrictModel):
    schema_version: str = "0.1"
    remaining_roadmap_report_id: str
    status: Literal[
        "remaining_roadmap_ready_manual_execution_required",
        "blocked_by_source_evidence",
    ]
    source_readiness_audit_report_id: str
    source_readiness_audit_report_ref: str
    source_readiness_status: str
    source_closeout_report_id: str
    source_closeout_report_ref: str
    source_closeout_status: str
    source_pr_readiness_decision_report_id: str | None = None
    source_pr_readiness_decision_report_ref: str | None = None
    source_pr_readiness_decision_status: str | None = None
    source_pr_readiness_decision: PRReadinessDecision | None = None
    item_count: int = Field(ge=0)
    easy_item_count: int = Field(ge=0)
    medium_item_count: int = Field(ge=0)
    large_item_count: int = Field(ge=0)
    critical_item_count: int = Field(ge=0)
    owner_gated_item_count: int = Field(ge=0)
    local_or_human_item_count: int = Field(ge=0)
    next_recommended_item_ids: list[str]
    items: list[RemainingRoadmapItem]
    checks: list[RemainingRoadmapCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_completion_scope: Literal["remaining_phase_plan_manual_execution_required"] = (
        "remaining_phase_plan_manual_execution_required"
    )
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def remaining_roadmap_counts_and_status_match(self) -> "RemainingRoadmapReport":
        if self.item_count != len(self.items):
            raise ValueError("remaining roadmap item count does not match")
        if self.easy_item_count != sum(1 for item in self.items if item.effort == "easy"):
            raise ValueError("remaining roadmap easy count does not match")
        if self.medium_item_count != sum(1 for item in self.items if item.effort == "medium"):
            raise ValueError("remaining roadmap medium count does not match")
        if self.large_item_count != sum(1 for item in self.items if item.effort == "large"):
            raise ValueError("remaining roadmap large count does not match")
        if self.critical_item_count != sum(1 for item in self.items if item.risk == "critical"):
            raise ValueError("remaining roadmap critical count does not match")
        owner_gates = {"owner_repo_review", "cross_repo_validation", "governance_approval"}
        owner_gates.add("production_pilot_approval")
        if self.owner_gated_item_count != sum(1 for item in self.items if item.gate in owner_gates):
            raise ValueError("remaining roadmap owner-gated count does not match")
        if self.local_or_human_item_count != sum(
            1 for item in self.items if item.gate in {"local_candidate", "manual_human_review"}
        ):
            raise ValueError("remaining roadmap local/human count does not match")
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "remaining_roadmap_ready_manual_execution_required" and failed:
            raise ValueError("ready remaining roadmap cannot have failed checks")
        if self.status == "blocked_by_source_evidence" and not failed:
            raise ValueError("blocked remaining roadmap requires failed checks")
        known_item_ids = {item.item_id for item in self.items}
        if not set(self.next_recommended_item_ids).issubset(known_item_ids):
            raise ValueError("remaining roadmap recommendation references unknown items")
        required = {
            "manual_owner_issue_creation_if_desired",
            "owner_repo_triage",
            "owner_repo_implementation_prs_if_accepted",
            "cross_repo_validation_after_owner_changes",
            "no_intake_external_write_or_promotion",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("remaining roadmap report is missing required gates")
        pr_gate_alternatives = {
            "human_pr_state_decision",
            "human_pr_state_decision_completed_by_observed_merge",
        }
        if not pr_gate_alternatives.intersection(set(self.required_next_gates)):
            raise ValueError("remaining roadmap report is missing required PR state gate")
        return self


SyntheticFixtureExpansionFamily = Literal[
    "ambiguous_roles",
    "missing_actuals",
    "carrier_rejection_variants",
    "budget_driver_edges",
]


class SyntheticFixtureExpansionHoldoutSpec(StrictModel):
    holdout_id: str
    family: SyntheticFixtureExpansionFamily
    description: str
    fixture_refs: list[str]
    test_refs: list[str]
    expected_signals: list[str]
    red_team_notes: list[str]
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    calibration_approved: Literal[False] = False
    fixture_files_mutated_by_audit: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def synthetic_fixture_expansion_holdout_has_review_material(
        self,
    ) -> "SyntheticFixtureExpansionHoldoutSpec":
        if not self.fixture_refs:
            raise ValueError("synthetic fixture expansion holdout requires fixture refs")
        if not self.test_refs:
            raise ValueError("synthetic fixture expansion holdout requires test refs")
        if not self.expected_signals:
            raise ValueError("synthetic fixture expansion holdout requires expected signals")
        if not self.red_team_notes:
            raise ValueError("synthetic fixture expansion holdout requires red-team notes")
        return self


class SyntheticFixtureExpansionManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    source_remaining_roadmap_item_id: Literal["fixture-and-eval-expansion"]
    required_families: list[SyntheticFixtureExpansionFamily]
    holdouts: list[SyntheticFixtureExpansionHoldoutSpec]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    calibration_approved: Literal[False] = False
    fixture_files_mutated_by_audit: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def synthetic_fixture_expansion_manifest_covers_required_families(
        self,
    ) -> "SyntheticFixtureExpansionManifest":
        if not self.holdouts:
            raise ValueError("synthetic fixture expansion manifest requires holdouts")
        holdout_ids = [holdout.holdout_id for holdout in self.holdouts]
        if len(holdout_ids) != len(set(holdout_ids)):
            raise ValueError("synthetic fixture expansion holdout IDs must be unique")
        required = set(self.required_families)
        covered = {holdout.family for holdout in self.holdouts}
        if not required:
            raise ValueError("synthetic fixture expansion manifest requires families")
        if not required.issubset(covered):
            raise ValueError("synthetic fixture expansion manifest is missing required families")
        return self


class SyntheticFixtureExpansionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class SyntheticFixtureExpansionReport(StrictModel):
    schema_version: str = "0.1"
    fixture_expansion_report_id: str
    status: Literal[
        "synthetic_fixture_expansion_ready_for_review",
        "blocked_by_fixture_expansion_evidence",
    ]
    source_remaining_roadmap_report_id: str
    source_remaining_roadmap_report_ref: str
    source_remaining_roadmap_status: str
    source_remaining_roadmap_item_id: Literal["fixture-and-eval-expansion"]
    source_remaining_roadmap_item_status: str
    manifest_id: str
    manifest_ref: str
    required_family_count: int = Field(ge=0)
    holdout_count: int = Field(ge=0)
    family_counts: dict[str, int]
    missing_required_families: list[SyntheticFixtureExpansionFamily]
    holdouts: list[SyntheticFixtureExpansionHoldoutSpec]
    checks: list[SyntheticFixtureExpansionCheck]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    calibration_approved: Literal[False] = False
    fixture_files_mutated_by_audit: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def synthetic_fixture_expansion_counts_and_status_match(
        self,
    ) -> "SyntheticFixtureExpansionReport":
        if self.holdout_count != len(self.holdouts):
            raise ValueError("synthetic fixture expansion holdout count does not match")
        if self.required_family_count != len(set(self.family_counts)) + len(
            set(self.missing_required_families)
        ):
            raise ValueError("synthetic fixture expansion required family count does not match")
        expected_counts: dict[str, int] = {}
        for holdout in self.holdouts:
            expected_counts[holdout.family] = expected_counts.get(holdout.family, 0) + 1
        if self.family_counts != expected_counts:
            raise ValueError("synthetic fixture expansion family counts do not match")
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "synthetic_fixture_expansion_ready_for_review" and failed:
            raise ValueError("ready synthetic fixture expansion cannot have failed checks")
        if self.status == "blocked_by_fixture_expansion_evidence" and not failed:
            raise ValueError("blocked synthetic fixture expansion requires failed checks")
        return self


SyntheticFixtureDepthAuditStatus = Literal[
    "synthetic_fixture_depth_ready_for_review",
    "synthetic_fixture_depth_gaps_identified",
    "blocked_by_depth_audit_boundary_violation",
]


class SyntheticFixtureDepthDimension(StrictModel):
    dimension_id: str
    family: str
    danger_loop: str
    description: str
    status: Literal["covered", "missing"]
    matched_holdout_ids: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    required_term_groups: list[list[str]]
    fixture_evidence_refs: list[str] = Field(default_factory=list)
    test_evidence_refs: list[str] = Field(default_factory=list)
    source_json_pointers: list[str] = Field(default_factory=list)
    fixture_test_binding_statuses: dict[str, str] = Field(default_factory=dict)
    test_refs_verified: list[str] = Field(default_factory=list)
    prose_only_match_count: int = Field(default=0, ge=0)
    why_it_matters: str
    remediation_hint: str

    @model_validator(mode="after")
    def synthetic_fixture_depth_dimension_status_matches_matches(
        self,
    ) -> "SyntheticFixtureDepthDimension":
        if self.status == "covered" and not self.matched_holdout_ids:
            raise ValueError("covered fixture depth dimension requires matched holdouts")
        if self.status == "covered" and not self.fixture_evidence_refs:
            raise ValueError("covered fixture depth dimension requires fixture evidence")
        if self.status == "covered" and not self.test_evidence_refs:
            raise ValueError("covered fixture depth dimension requires test evidence")
        if self.status == "missing" and self.matched_holdout_ids:
            raise ValueError("missing fixture depth dimension cannot have matched holdouts")
        if not self.required_term_groups:
            raise ValueError("fixture depth dimension requires term groups")
        return self


class SyntheticFixtureDepthFamilySummary(StrictModel):
    family: str
    holdout_count: int = Field(ge=0)
    covered_dimension_count: int = Field(ge=0)
    missing_dimension_count: int = Field(ge=0)
    missing_dimension_ids: list[str] = Field(default_factory=list)


class SyntheticFixtureDepthAuditReport(StrictModel):
    schema_version: str = "0.1"
    fixture_depth_audit_report_id: str
    status: SyntheticFixtureDepthAuditStatus
    manifest_id: str
    manifest_ref: str
    holdout_count: int = Field(ge=0)
    dimension_count: int = Field(ge=0)
    covered_dimension_count: int = Field(ge=0)
    missing_dimension_count: int = Field(ge=0)
    boundary_violation_count: int = Field(ge=0)
    missing_dimension_ids: list[str] = Field(default_factory=list)
    boundary_violations: list[str] = Field(default_factory=list)
    family_summaries: list[SyntheticFixtureDepthFamilySummary]
    dimensions: list[SyntheticFixtureDepthDimension]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    calibration_approved: Literal[False] = False
    fixture_files_mutated_by_audit: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def synthetic_fixture_depth_counts_and_status_match(
        self,
    ) -> "SyntheticFixtureDepthAuditReport":
        if self.dimension_count != len(self.dimensions):
            raise ValueError("fixture depth dimension count does not match")
        covered = [dimension for dimension in self.dimensions if dimension.status == "covered"]
        missing = [dimension for dimension in self.dimensions if dimension.status == "missing"]
        if self.covered_dimension_count != len(covered):
            raise ValueError("fixture depth covered dimension count does not match")
        if self.missing_dimension_count != len(missing):
            raise ValueError("fixture depth missing dimension count does not match")
        if self.missing_dimension_ids != [dimension.dimension_id for dimension in missing]:
            raise ValueError("fixture depth missing dimension IDs do not match")
        if self.boundary_violation_count != len(self.boundary_violations):
            raise ValueError("fixture depth boundary violation count does not match")
        if self.status == "synthetic_fixture_depth_ready_for_review" and (
            self.missing_dimension_count or self.boundary_violation_count
        ):
            raise ValueError("ready fixture depth audit cannot have gaps or boundary violations")
        if self.status == "synthetic_fixture_depth_gaps_identified" and (
            not self.missing_dimension_count or self.boundary_violation_count
        ):
            raise ValueError("fixture depth gaps status requires gaps and no boundary violations")
        if (
            self.status == "blocked_by_depth_audit_boundary_violation"
            and not self.boundary_violation_count
        ):
            raise ValueError("blocked fixture depth audit requires boundary violations")
        return self


SyntheticQABundleArtifactStatus = Literal[
    "passed",
    "pending_review",
    "blocked",
    "failed",
    "missing",
]


class SyntheticQABundleArtifact(StrictModel):
    artifact_id: str
    label: str
    file_name: str
    required: bool
    present: bool
    status: SyntheticQABundleArtifactStatus
    gate_state: SyntheticQABundleArtifactStatus
    artifact_ref: str | None = None
    copied_to_ref: str | None = None
    source_sha256: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def synthetic_qa_bundle_artifact_status_matches_presence(
        self,
    ) -> "SyntheticQABundleArtifact":
        if self.present and not self.artifact_ref:
            raise ValueError("present synthetic QA artifact requires artifact_ref")
        if self.present and not self.source_sha256:
            raise ValueError("present synthetic QA artifact requires source_sha256")
        if not self.present and self.status != "missing":
            raise ValueError("missing synthetic QA artifact must have missing status")
        if not self.present and self.gate_state != "missing":
            raise ValueError("missing synthetic QA artifact must have missing gate state")
        if self.copied_to_ref and not self.present:
            raise ValueError("missing synthetic QA artifact cannot have copied_to_ref")
        return self


class SyntheticQABundleReport(StrictModel):
    schema_version: str = "0.1"
    synthetic_qa_bundle_report_id: str
    status: Literal["passed", "pending_review", "blocked", "failed"]
    run_root_ref: str
    out_dir_ref: str
    artifact_count: int = Field(ge=0)
    required_artifact_count: int = Field(ge=0)
    missing_required_artifact_count: int = Field(ge=0)
    blocked_artifact_count: int = Field(ge=0)
    pending_artifact_count: int = Field(ge=0)
    failed_artifact_count: int = Field(ge=0)
    artifacts: list[SyntheticQABundleArtifact]
    ui_manifest_ref: str | None = None
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    fixture_files_mutated: Literal[False] = False
    calibration_applied: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    matter_opening_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def synthetic_qa_bundle_counts_and_status_match(self) -> "SyntheticQABundleReport":
        if self.artifact_count != len(self.artifacts):
            raise ValueError("synthetic QA bundle artifact count does not match")
        required = [artifact for artifact in self.artifacts if artifact.required]
        missing_required = [
            artifact
            for artifact in required
            if not artifact.present or artifact.status == "missing"
        ]
        blocked = [artifact for artifact in self.artifacts if artifact.status == "blocked"]
        pending = [artifact for artifact in self.artifacts if artifact.status == "pending_review"]
        failed = [artifact for artifact in self.artifacts if artifact.status == "failed"]
        if self.required_artifact_count != len(required):
            raise ValueError("synthetic QA bundle required artifact count does not match")
        if self.missing_required_artifact_count != len(missing_required):
            raise ValueError("synthetic QA bundle missing required artifact count does not match")
        if self.blocked_artifact_count != len(blocked):
            raise ValueError("synthetic QA bundle blocked artifact count does not match")
        if self.pending_artifact_count != len(pending):
            raise ValueError("synthetic QA bundle pending artifact count does not match")
        if self.failed_artifact_count != len(failed):
            raise ValueError("synthetic QA bundle failed artifact count does not match")
        if self.status == "passed" and (missing_required or blocked or pending or failed):
            raise ValueError("passed synthetic QA bundle cannot include blockers or pending review")
        if self.status == "failed" and not failed:
            raise ValueError("failed synthetic QA bundle requires failed artifacts")
        if self.status == "blocked" and not (missing_required or blocked):
            raise ValueError("blocked synthetic QA bundle requires missing or blocked artifacts")
        if self.status == "pending_review" and (
            missing_required or blocked or failed or not pending
        ):
            raise ValueError("pending synthetic QA bundle requires only pending review artifacts")
        if not self.required_next_actions:
            raise ValueError("synthetic QA bundle requires next actions")
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


class OrchestratorOwnerReviewSourceRef(StrictModel):
    source_ref_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_refs: list[str]
    coverage: Literal["full", "partial", "missing"]


class OrchestratorOwnerReviewHumanConfirmation(StrictModel):
    status: Literal[
        "confirmed",
        "approved",
        "pending",
        "needs_more_information",
        "unknown",
        "human_only",
        "declined",
        "declined_referred",
        "declined_or_referred",
    ]
    human_review_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class OrchestratorOwnerReviewBudgetPreconditions(StrictModel):
    party_count_known: bool
    complexity_known: bool
    matter_family_confirmed: bool
    representation_posture_confirmed: bool
    principal_roles_confirmed: bool


class OrchestratorOwnerReviewBudgetActualLine(StrictModel):
    line_id: str
    budget_phase: str
    budget_task_code: str
    proposed_budget_amount: str
    carrier_compliant_projection_amount: str
    approved_budget_amount_if_known: str = ""
    actual_billed_amount: str
    write_down_or_disallowed_amount: str
    variance_driver_candidate: str


class OrchestratorOwnerReviewCarrierAppeal(StrictModel):
    requested: bool
    human_authorization_ref: str | None = None


class OrchestratorOwnerReviewCarrierAppealResult(StrictModel):
    result_id: str
    result: str
    received_at: str


class OrchestratorOwnerReviewCarrierRejectionNotice(StrictModel):
    notice_id: str
    channel: str
    source_ref_id: str
    notice_title: str
    reason_summary: str
    carrier_reason_code: str
    matched_budget_line_id: str = ""
    appeal: OrchestratorOwnerReviewCarrierAppeal
    appeal_results: list[OrchestratorOwnerReviewCarrierAppealResult] = Field(default_factory=list)
    financial_outcome: str | None = None


class OrchestratorOwnerReviewRequest(StrictModel):
    schema_version: Literal["intake_owner_review_request.v0_1"] = "intake_owner_review_request.v0_1"
    request_id: str
    generated_at: str
    workflow_label: Literal["orchestrator.local.intake_to_budget_owner_review"] = (
        "orchestrator.local.intake_to_budget_owner_review"
    )
    synthetic: Literal[True] = True
    contains_real_firm_data: Literal[False] = False
    contains_real_client_data: Literal[False] = False
    contains_real_matter_data: Literal[False] = False
    contains_privileged_data: Literal[False] = False
    source_refs: list[OrchestratorOwnerReviewSourceRef]
    human_confirmations: dict[str, OrchestratorOwnerReviewHumanConfirmation]
    budget_preconditions: OrchestratorOwnerReviewBudgetPreconditions
    budget_actual_lines: list[OrchestratorOwnerReviewBudgetActualLine] = Field(default_factory=list)
    carrier_rejection_notices: list[OrchestratorOwnerReviewCarrierRejectionNotice] = Field(
        default_factory=list
    )
    lake_handoff_mode: Literal["disabled", "validate_only"] = "disabled"

    @model_validator(mode="after")
    def required_orchestrator_fields_present(self) -> "OrchestratorOwnerReviewRequest":
        required_pauses = {
            "confirm_matter_family",
            "confirm_representation_posture",
            "confirm_principal_party_roles",
            "approve_budget_proposal_before_external_submission",
            "approve_exception_lake_handoff_before_admission",
        }
        missing = sorted(required_pauses - set(self.human_confirmations))
        if missing:
            raise ValueError(f"orchestrator owner-review request missing pauses: {missing}")
        if not self.source_refs:
            raise ValueError("orchestrator owner-review request requires source_refs")
        source_ids = [source.source_ref_id for source in self.source_refs]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError(
                "orchestrator owner-review request source_ref_id values must be unique"
            )
        known_sources = set(source_ids)
        missing_notice_sources = sorted(
            {
                notice.source_ref_id
                for notice in self.carrier_rejection_notices
                if notice.source_ref_id not in known_sources
            }
        )
        if missing_notice_sources:
            raise ValueError(
                "carrier rejection notice source_ref_id values must be present in source_refs: "
                + ", ".join(missing_notice_sources)
            )
        return self


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


BudgetLakeEvidenceArtifactKind = Literal[
    "budget_change_ledger_report",
    "budget_change_ledger_jsonl",
    "budget_actual_variance_ledger_report",
    "budget_actual_variance_ledger_jsonl",
    "carrier_rejection_decision_ledger_report",
    "carrier_rejection_decision_ledger_jsonl",
]

BudgetLakeCandidateRecordFamily = Literal[
    "budget_human_change_record",
    "budget_actual_variance_record",
    "budget_actual_missing_source_record",
    "carrier_rejection_decision_record",
    "carrier_appeal_result_record",
    "carrier_financial_outcome_record",
]


class BudgetLakeEvidenceArtifact(StrictModel):
    schema_version: str = "0.1"
    artifact_id: str
    artifact_kind: BudgetLakeEvidenceArtifactKind
    artifact_ref: str
    sha256: str
    report_id: str | None = None
    ledger_id: str | None = None
    run_id: str | None = None
    preflight_packet_id: str | None = None
    budget_proposal_id: str | None = None
    event_count: int = Field(ge=0)
    row_event_count: int = Field(ge=0)
    event_kind_counts: dict[str, int] = Field(default_factory=dict)
    local_event_labels: list[str] = Field(default_factory=list)
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)
    admission_state: Literal["candidate_not_admitted"] = "candidate_not_admitted"
    requires_exception_lake_owner_review: Literal[True] = True
    artifact_hash_required: Literal[True] = True
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    raw_payload_included: Literal[False] = False
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def artifact_hash_is_sha256(self) -> "BudgetLakeEvidenceArtifact":
        if not self.sha256.startswith("sha256:"):
            raise ValueError("budget Lake evidence artifact hash must be sha256")
        return self


class BudgetLakeAdmissionBundleCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)


class BudgetLakeAdmissionBundleReport(StrictModel):
    schema_version: str = "0.1"
    bundle_report_id: str
    status: Literal[
        "ready_for_exception_lake_review",
        "blocked_missing_artifacts",
        "blocked_inconsistent_evidence",
    ]
    origin_repo: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    target_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )
    admission_state: Literal["dry_run_not_admitted"] = "dry_run_not_admitted"
    artifact_count: int = Field(ge=0)
    ledger_report_count: int = Field(ge=0)
    jsonl_row_count: int = Field(ge=0)
    total_event_count: int = Field(ge=0)
    budget_proposal_ids: list[str] = Field(default_factory=list)
    preflight_packet_ids: list[str] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)
    local_event_labels: list[str] = Field(default_factory=list)
    artifacts: list[BudgetLakeEvidenceArtifact]
    checks: list[BudgetLakeAdmissionBundleCheck]
    required_next_gates: list[str]
    append_only_required: Literal[True] = True
    correction_supersession_required: Literal[True] = True
    record_hash_required: Literal[True] = True
    orchestrator_evidence_packet_required: Literal[True] = True
    exception_lake_owner_admission_required: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    raw_payload_included: Literal[False] = False
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
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
    def bundle_counts_match_artifacts(self) -> "BudgetLakeAdmissionBundleReport":
        if self.artifact_count != len(self.artifacts):
            raise ValueError("budget Lake bundle artifact count must match artifacts")
        if self.ledger_report_count != sum(
            1 for artifact in self.artifacts if artifact.artifact_kind.endswith("_report")
        ):
            raise ValueError("budget Lake bundle report count must match artifacts")
        if self.jsonl_row_count != sum(artifact.row_event_count for artifact in self.artifacts):
            raise ValueError("budget Lake bundle JSONL row count must match artifacts")
        if self.total_event_count != sum(artifact.event_count for artifact in self.artifacts):
            raise ValueError("budget Lake bundle event count must match artifacts")
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.status == "ready_for_exception_lake_review" and failed_checks:
            raise ValueError("ready budget Lake bundle cannot have failed checks")
        if self.status != "ready_for_exception_lake_review" and not failed_checks:
            raise ValueError("blocked budget Lake bundle requires failed checks")
        return self


class BudgetLifecycleAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)


class BudgetLifecycleFinancialSummary(StrictModel):
    original_budget_total: float | None = None
    human_revision_total_delta: float | None = None
    human_revised_candidate_total: float | None = None
    actual_comparison_budgeted_total: float | None = None
    actual_total: float | None = None
    actual_variance_amount: float | None = None
    carrier_disputed_amount: float = Field(default=0, ge=0)
    carrier_recovered_amount: float = Field(default=0, ge=0)
    carrier_write_down_amount: float = Field(default=0, ge=0)


class BudgetLifecycleAuditReport(StrictModel):
    schema_version: str = "0.1"
    lifecycle_audit_report_id: str
    status: Literal[
        "ready_for_budget_lifecycle_review",
        "blocked_missing_lifecycle_artifacts",
        "blocked_inconsistent_lifecycle_evidence",
    ]
    budget_proposal_id: str | None = None
    preflight_packet_id: str | None = None
    run_ids: list[str] = Field(default_factory=list)
    source_budget_change_ledger_report_ref: str
    source_budget_actual_variance_ledger_report_ref: str
    source_carrier_rejection_decision_ledger_report_ref: str
    source_budget_event_lake_bundle_report_ref: str
    budget_change_ledger_report_id: str | None = None
    budget_actual_variance_ledger_report_id: str | None = None
    carrier_rejection_decision_ledger_report_id: str | None = None
    budget_event_lake_bundle_report_id: str | None = None
    budget_change_event_count: int = Field(ge=0)
    actual_variance_event_count: int = Field(ge=0)
    carrier_rejection_event_count: int = Field(ge=0)
    total_lifecycle_event_count: int = Field(ge=0)
    human_budget_change_event_count: int = Field(ge=0)
    actual_variance_review_event_count: int = Field(ge=0)
    carrier_pending_decision_event_count: int = Field(ge=0)
    carrier_appeal_result_event_count: int = Field(ge=0)
    carrier_financial_outcome_event_count: int = Field(ge=0)
    pending_human_decision_count: int = Field(ge=0)
    required_human_decisions: list[str] = Field(default_factory=list)
    proposed_next_actions: list[str] = Field(default_factory=list)
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)
    local_event_labels: list[str] = Field(default_factory=list)
    financial_summary: BudgetLifecycleFinancialSummary
    checks: list[BudgetLifecycleAuditCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only_evidence_required: Literal[True] = True
    human_review_required: Literal[True] = True
    orchestrator_owner_for_runtime_capture: Literal[True] = True
    exception_lake_owner_for_admission: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def budget_lifecycle_counts_and_status_match(self) -> "BudgetLifecycleAuditReport":
        if self.total_lifecycle_event_count != (
            self.budget_change_event_count
            + self.actual_variance_event_count
            + self.carrier_rejection_event_count
        ):
            raise ValueError("budget lifecycle total event count must match stream counts")
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.status == "ready_for_budget_lifecycle_review" and failed_checks:
            raise ValueError("ready budget lifecycle audit cannot have failed checks")
        if self.status != "ready_for_budget_lifecycle_review" and not failed_checks:
            raise ValueError("blocked budget lifecycle audit requires failed checks")
        required = {
            "human_budget_lifecycle_review",
            "orchestrator_evidence_packet_assembly",
            "exception_lake_runtime_admission_validation",
            "reviewed_learning_gate_before_candidate_changes",
            "no_silent_profile_template_budget_or_guideline_mutation",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget lifecycle audit is missing required gates")
        return self


BudgetHumanReviewAction = Literal[
    "confirm_no_change",
    "correct_budget",
    "request_more_information",
    "appeal",
    "accept_write_down",
    "reopen",
    "block_submission",
    "human_only",
    "route_to_owner_review",
    "no_learning_change",
]

BudgetHumanReviewOutcome = Literal[
    "confirm",
    "correct",
    "unknown",
    "needs_more_information",
    "human_only",
    "declined_referred",
    "no_change",
    "appeal",
    "write_off",
    "reopen",
    "block",
    "route_to_owner_review",
    "no_learning_change",
]

BudgetHumanReviewPriority = Literal["critical", "high", "medium", "low"]

BudgetHumanReviewArea = Literal[
    "budget_revision",
    "actual_variance",
    "carrier_rejection",
    "appeal_result",
    "lake_handoff",
    "learning_loop",
    "authority_boundary",
    "overall",
]


class BudgetHumanReviewPacketCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetHumanReviewRecommendation(StrictModel):
    recommendation_id: str
    review_area: BudgetHumanReviewArea
    recommended_action: BudgetHumanReviewAction
    priority: BudgetHumanReviewPriority
    why: list[str]
    source_artifact_refs: list[str] = Field(default_factory=list)
    required_human_decisions: list[str] = Field(default_factory=list)
    proposed_next_actions: list[str] = Field(default_factory=list)
    financial_impact: float | None = None
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)

    @model_validator(mode="after")
    def recommendation_is_explainable(self) -> "BudgetHumanReviewRecommendation":
        if not self.recommendation_id.strip():
            raise ValueError("budget human review recommendation requires recommendation_id")
        if not self.why:
            raise ValueError("budget human review recommendation requires why notes")
        if not self.source_artifact_refs:
            raise ValueError("budget human review recommendation requires source artifact refs")
        return self


class BudgetHumanReviewRedTeamNote(StrictModel):
    note_id: str
    severity: BudgetHumanReviewPriority
    scope: Literal[
        "proposed_vs_compliant_collapse",
        "duplicate_rejection",
        "scenario_variance_mismatch",
        "source_coverage",
        "authority_boundary",
        "learning_loop_mutation",
        "financial_math",
        "actuals_coverage",
        "lake_handoff",
    ]
    message: str
    recommended_check: str
    artifact_refs: list[str] = Field(default_factory=list)


class BudgetHumanReviewDecisionTemplate(StrictModel):
    template_id: str
    review_area: BudgetHumanReviewArea
    source_recommendation_ids: list[str] = Field(default_factory=list)
    allowed_outcomes: list[BudgetHumanReviewOutcome]
    recommended_outcome: BudgetHumanReviewOutcome
    required_fields: list[str]
    mutation_policy: Literal["append_or_supersede_only"] = "append_or_supersede_only"
    external_submission_authorized: Literal[False] = False
    lake_write_authorized: Literal[False] = False
    silent_learning_allowed: Literal[False] = False

    @model_validator(mode="after")
    def recommended_outcome_allowed(self) -> "BudgetHumanReviewDecisionTemplate":
        if self.recommended_outcome not in self.allowed_outcomes:
            raise ValueError("recommended outcome must be in allowed outcomes")
        if not self.required_fields:
            raise ValueError("budget human review decision template requires fields")
        return self


class BudgetHumanReviewPacket(StrictModel):
    schema_version: str = "0.1"
    budget_human_review_packet_id: str
    status: Literal["ready_for_human_budget_review", "blocked_by_lifecycle_audit"]
    source_budget_lifecycle_audit_report_id: str
    source_budget_lifecycle_audit_report_ref: str
    source_budget_lifecycle_audit_status: Literal[
        "ready_for_budget_lifecycle_review",
        "blocked_missing_lifecycle_artifacts",
        "blocked_inconsistent_lifecycle_evidence",
    ]
    source_budget_revision_report_ref: str | None = None
    source_budget_actual_comparison_report_ref: str | None = None
    source_carrier_rejection_review_packet_ref: str | None = None
    source_carrier_rejection_learning_report_ref: str | None = None
    budget_proposal_id: str | None = None
    preflight_packet_id: str | None = None
    run_ids: list[str] = Field(default_factory=list)
    financial_summary: BudgetLifecycleFinancialSummary
    pending_human_decision_count: int = Field(ge=0)
    required_human_decisions: list[str] = Field(default_factory=list)
    proposed_next_actions: list[str] = Field(default_factory=list)
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)
    local_event_labels: list[str] = Field(default_factory=list)
    required_review_sections: list[BudgetHumanReviewArea]
    recommendations: list[BudgetHumanReviewRecommendation]
    red_team_notes: list[BudgetHumanReviewRedTeamNote]
    decision_templates: list[BudgetHumanReviewDecisionTemplate]
    checks: list[BudgetHumanReviewPacketCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    append_only_decision_required: Literal[True] = True
    human_review_required: Literal[True] = True
    orchestrator_owner_for_runtime_capture: Literal[True] = True
    exception_lake_owner_for_admission: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_read_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def budget_human_review_packet_status_matches_checks(
        self,
    ) -> "BudgetHumanReviewPacket":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "ready_for_human_budget_review" and failed:
            raise ValueError("ready budget human review packet cannot have failed checks")
        if self.status == "blocked_by_lifecycle_audit" and not failed:
            raise ValueError("blocked budget human review packet requires failed checks")
        if self.status == "ready_for_human_budget_review":
            if not self.recommendations:
                raise ValueError("ready budget human review packet requires recommendations")
            if not self.red_team_notes:
                raise ValueError("ready budget human review packet requires red-team notes")
            if not self.decision_templates:
                raise ValueError("ready budget human review packet requires decision templates")
        required = {
            "append_only_human_budget_decision",
            "orchestrator_human_pause_before_external_action",
            "exception_lake_owner_review_before_admission",
            "reviewed_learning_gate_before_mutation",
            "no_budget_or_appeal_submission_from_intake",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget human review packet is missing required gates")
        return self


BudgetHumanReviewOutcomeStatus = Literal[
    "budget_human_review_outcome_recorded",
    "blocked_by_review_packet_evidence",
    "blocked_by_outcome_evidence",
]

BudgetHumanReviewTargetOwnerRepo = Literal[
    "LawFirm-os-intake",
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-legal-knowledge-runtime",
    "LawFirm-os-skills-registry",
]


class BudgetHumanReviewOutcomeDecision(StrictModel):
    decision_id: str
    template_id: str
    review_area: BudgetHumanReviewArea
    outcome: BudgetHumanReviewOutcome
    decision_reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    source_recommendation_ids: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    followup_owner: str | None = None
    followup_due_at: str | None = None
    financial_amount: float | None = None
    target_owner_repo: BudgetHumanReviewTargetOwnerRepo | None = None
    proposed_correction_refs: list[str] = Field(default_factory=list)
    candidate_record_families: list[BudgetLakeCandidateRecordFamily] = Field(default_factory=list)

    @model_validator(mode="after")
    def budget_human_review_decision_is_complete(
        self,
    ) -> "BudgetHumanReviewOutcomeDecision":
        if not self.decision_id.strip():
            raise ValueError("budget human review outcome decision requires decision_id")
        if not self.template_id.strip():
            raise ValueError("budget human review outcome decision requires template_id")
        if not self.decision_reason.strip():
            raise ValueError("budget human review outcome decision requires decision_reason")
        if not self.evidence_refs:
            raise ValueError("budget human review outcome decision requires evidence_refs")
        if self.outcome == "correct" and not self.proposed_correction_refs:
            raise ValueError("correct budget human review decisions require correction refs")
        if self.outcome in {"appeal", "reopen", "needs_more_information"}:
            if not (self.followup_owner and self.followup_owner.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_owner")
            if not (self.followup_due_at and self.followup_due_at.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_due_at")
            if not self.required_followups:
                raise ValueError(f"{self.outcome} decisions require required_followups")
        if self.outcome == "route_to_owner_review" and self.target_owner_repo is None:
            raise ValueError("route_to_owner_review decisions require target_owner_repo")
        if self.outcome == "write_off":
            if self.financial_amount is None:
                raise ValueError("write_off decisions require financial_amount")
            if self.financial_amount < 0:
                raise ValueError("write_off financial_amount cannot be negative")
        return self


class BudgetHumanReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    budget_human_review_outcome_record_id: str
    budget_human_review_packet_id: str
    source_budget_human_review_packet_ref: str | None = None
    reviewer_id: str
    reviewer_role: str | None = None
    reviewed_at: str
    overall_outcome: BudgetHumanReviewOutcome
    decision_reason: str
    decisions: list[BudgetHumanReviewOutcomeDecision]
    supersedes_budget_human_review_outcome_record_id: str | None = None
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def budget_human_review_outcome_record_is_complete(
        self,
    ) -> "BudgetHumanReviewOutcomeRecord":
        if not self.budget_human_review_outcome_record_id.strip():
            raise ValueError("budget human review outcome record requires id")
        if not self.budget_human_review_packet_id.strip():
            raise ValueError("budget human review outcome record requires packet id")
        if not self.reviewer_id.strip():
            raise ValueError("budget human review outcome record requires reviewer_id")
        if not self.reviewed_at.strip():
            raise ValueError("budget human review outcome record requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("budget human review outcome record requires decision_reason")
        if not self.decisions:
            raise ValueError("budget human review outcome record requires decisions")
        decision_ids = [decision.decision_id for decision in self.decisions]
        if len(set(decision_ids)) != len(decision_ids):
            raise ValueError("budget human review outcome decision IDs must be unique")
        template_ids = [decision.template_id for decision in self.decisions]
        if len(set(template_ids)) != len(template_ids):
            raise ValueError("budget human review outcome template IDs must be unique")
        return self


class BudgetHumanReviewOutcomeCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    template_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetHumanReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    budget_human_review_outcome_report_id: str
    status: BudgetHumanReviewOutcomeStatus
    source_budget_human_review_packet_ref: str
    budget_human_review_packet_id: str
    source_budget_human_review_packet_status: Literal[
        "ready_for_human_budget_review",
        "blocked_by_lifecycle_audit",
    ]
    budget_human_review_outcome_record_id: str
    overall_outcome: BudgetHumanReviewOutcome
    decision_reason: str
    reviewer_id: str
    reviewed_at: str
    decision_count: int = Field(ge=0)
    appeal_decision_count: int = Field(ge=0)
    write_off_decision_count: int = Field(ge=0)
    correction_decision_count: int = Field(ge=0)
    route_to_owner_decision_count: int = Field(ge=0)
    no_learning_change_decision_count: int = Field(ge=0)
    unresolved_followup_count: int = Field(ge=0)
    recorded_outcomes: list[BudgetHumanReviewOutcome] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    candidate_lake_event_labels: list[str] = Field(default_factory=list)
    append_only_history_ref: str
    checks: list[BudgetHumanReviewOutcomeCheck]
    required_next_gates: list[str]
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_carrier_submission: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def budget_human_review_outcome_report_status_matches_checks(
        self,
    ) -> "BudgetHumanReviewOutcomeReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "budget_human_review_outcome_recorded" and failed:
            raise ValueError("recorded budget human review outcome cannot have failed checks")
        if self.status != "budget_human_review_outcome_recorded" and not failed:
            raise ValueError("blocked budget human review outcome report requires failed checks")
        if self.decision_count != len(self.recorded_outcomes):
            raise ValueError("budget human review outcome decision count must match outcomes")
        if self.unresolved_followup_count != len(self.required_followups):
            raise ValueError("budget human review followup count must match followups")
        required = {
            "append_only_human_budget_decision",
            "orchestrator_human_pause_before_external_action",
            "exception_lake_owner_review_before_admission",
            "reviewed_learning_gate_before_mutation",
            "no_budget_or_appeal_submission_from_intake",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget human review outcome report is missing required gates")
        return self


BudgetHumanReviewOutcomeOwnerAdoptionFocus = Literal[
    "semantic_outcome_label_review",
    "runtime_action_followup_workflow",
    "append_only_outcome_lake_admission",
]


class BudgetHumanReviewOutcomeOwnerAdoptionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BudgetHumanReviewOutcomeOwnerAdoptionPacket(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_packet_id: str
    target_repo: BudgetHumanReviewTargetOwnerRepo
    adoption_focus: BudgetHumanReviewOutcomeOwnerAdoptionFocus
    status: Literal["ready_for_owner_review", "blocked_by_outcome_evidence"]
    source_budget_human_review_outcome_report_id: str
    source_budget_human_review_outcome_report_ref: str
    source_budget_human_review_outcome_record_id: str
    source_budget_human_review_outcome_record_ref: str
    source_budget_human_review_packet_id: str
    source_budget_human_review_outcome_status: BudgetHumanReviewOutcomeStatus
    overall_outcome: BudgetHumanReviewOutcome
    decision_count: int = Field(ge=0)
    appeal_decision_count: int = Field(ge=0)
    write_off_decision_count: int = Field(ge=0)
    correction_decision_count: int = Field(ge=0)
    route_to_owner_decision_count: int = Field(ge=0)
    no_learning_change_decision_count: int = Field(ge=0)
    unresolved_followup_count: int = Field(ge=0)
    candidate_lake_event_labels: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    source_artifact_refs: list[str] = Field(default_factory=list)
    candidate_contract_refs: list[str] = Field(default_factory=list)
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def outcome_owner_packet_is_complete(
        self,
    ) -> "BudgetHumanReviewOutcomeOwnerAdoptionPacket":
        if not self.required_owner_actions:
            raise ValueError("budget outcome owner packet requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("budget outcome owner packet requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("budget outcome owner packet requires red-team notes")
        required = {
            "human_budget_outcome_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "cross_repo_contract_validation_after_owner_changes",
            "no_intake_external_action_or_lake_admission",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget outcome owner packet is missing required gates")
        return self


class BudgetHumanReviewOutcomeOwnerAdoptionReport(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_report_id: str
    status: Literal[
        "budget_outcome_owner_adoption_packets_ready",
        "blocked_by_budget_outcome_evidence",
    ]
    source_budget_human_review_outcome_report_id: str
    source_budget_human_review_outcome_report_ref: str
    source_budget_human_review_outcome_record_id: str
    source_budget_human_review_outcome_record_ref: str
    source_budget_human_review_packet_id: str
    source_budget_human_review_outcome_status: BudgetHumanReviewOutcomeStatus
    target_repo_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    ready_packet_count: int = Field(ge=0)
    blocked_packet_count: int = Field(ge=0)
    target_repos: list[BudgetHumanReviewTargetOwnerRepo]
    packets: list[BudgetHumanReviewOutcomeOwnerAdoptionPacket]
    packet_output_refs: list[str] = Field(default_factory=list)
    checks: list[BudgetHumanReviewOutcomeOwnerAdoptionCheck]
    candidate_lake_event_labels: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    billing_connector_write_performed: Literal[False] = False
    carrier_portal_write_performed: Literal[False] = False
    email_send_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def outcome_owner_report_counts_match(
        self,
    ) -> "BudgetHumanReviewOutcomeOwnerAdoptionReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "budget_outcome_owner_adoption_packets_ready" and failed:
            raise ValueError("ready budget outcome owner report cannot have failed checks")
        if self.status == "blocked_by_budget_outcome_evidence" and not failed:
            raise ValueError("blocked budget outcome owner report requires failed checks")
        if self.packet_count != len(self.packets):
            raise ValueError("budget outcome owner report packet_count mismatch")
        if self.packet_count != len(self.packet_output_refs):
            raise ValueError("budget outcome owner report packet refs mismatch")
        if self.target_repo_count != len(self.target_repos):
            raise ValueError("budget outcome owner report target_repo_count mismatch")
        if self.ready_packet_count != sum(
            1 for packet in self.packets if packet.status == "ready_for_owner_review"
        ):
            raise ValueError("budget outcome owner ready count mismatch")
        if self.blocked_packet_count != sum(
            1 for packet in self.packets if packet.status == "blocked_by_outcome_evidence"
        ):
            raise ValueError("budget outcome owner blocked count mismatch")
        required = {
            "human_budget_outcome_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "cross_repo_contract_validation_after_owner_changes",
            "no_intake_external_action_or_lake_admission",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("budget outcome owner report is missing required gates")
        return self


BudgetLifecycleOwnerTargetRepo = Literal[
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

BudgetLifecycleOwnerAdoptionFocus = Literal[
    "semantic_contract_and_event_labels",
    "runtime_capture_and_human_workflow",
    "append_only_lake_admission",
]


class BudgetLifecycleOwnerAdoptionPacket(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_packet_id: str
    target_repo: BudgetLifecycleOwnerTargetRepo
    adoption_focus: BudgetLifecycleOwnerAdoptionFocus
    status: Literal["ready_for_owner_review", "blocked_by_lifecycle_audit"]
    source_budget_lifecycle_audit_report_id: str
    source_budget_lifecycle_audit_report_ref: str
    source_budget_lifecycle_audit_status: str
    source_budget_proposal_id: str | None = None
    source_preflight_packet_id: str | None = None
    source_artifact_refs: list[str] = Field(default_factory=list)
    candidate_contract_refs: list[str] = Field(default_factory=list)
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    connector_implemented: Literal[False] = False
    external_writes_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def budget_lifecycle_owner_packet_is_reviewable(
        self,
    ) -> "BudgetLifecycleOwnerAdoptionPacket":
        if not self.required_owner_actions:
            raise ValueError("budget lifecycle owner packet requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("budget lifecycle owner packet requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("budget lifecycle owner packet requires red-team notes")
        if not self.required_next_gates:
            raise ValueError("budget lifecycle owner packet requires next gates")
        if not self.source_artifact_refs:
            raise ValueError("budget lifecycle owner packet requires source artifact refs")
        return self


class BudgetLifecycleOwnerAdoptionReport(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_report_id: str
    status: Literal["owner_adoption_packets_ready", "blocked_by_lifecycle_audit"]
    source_budget_lifecycle_audit_report_id: str
    source_budget_lifecycle_audit_report_ref: str
    source_budget_lifecycle_audit_status: str
    target_repo_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    ready_packet_count: int = Field(ge=0)
    blocked_packet_count: int = Field(ge=0)
    target_repos: list[BudgetLifecycleOwnerTargetRepo]
    packets: list[BudgetLifecycleOwnerAdoptionPacket]
    packet_output_refs: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    connector_implemented: Literal[False] = False
    external_writes_performed: Literal[False] = False
    budget_submission_performed: Literal[False] = False
    appeal_submission_performed: Literal[False] = False
    budget_mutation_performed: Literal[False] = False
    profile_mutation_performed: Literal[False] = False
    template_mutation_performed: Literal[False] = False
    carrier_guideline_mutation_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def budget_lifecycle_owner_report_counts_match(
        self,
    ) -> "BudgetLifecycleOwnerAdoptionReport":
        if self.packet_count != len(self.packets):
            raise ValueError("budget lifecycle owner packet count does not match")
        if self.target_repo_count != len(self.target_repos):
            raise ValueError("budget lifecycle owner target repo count does not match")
        if self.packet_count != len(self.packet_output_refs):
            raise ValueError("budget lifecycle owner packet output ref count does not match")
        ready_count = sum(1 for packet in self.packets if packet.status == "ready_for_owner_review")
        blocked_count = self.packet_count - ready_count
        if self.ready_packet_count != ready_count or self.blocked_packet_count != blocked_count:
            raise ValueError("budget lifecycle owner ready/blocked counts do not match")
        if self.status == "owner_adoption_packets_ready" and self.blocked_packet_count:
            raise ValueError("ready budget lifecycle owner report cannot include blocked packets")
        if self.status == "blocked_by_lifecycle_audit" and not self.blocked_packet_count:
            raise ValueError("blocked budget lifecycle owner report requires blocked packets")
        if not self.required_next_gates:
            raise ValueError("budget lifecycle owner report requires next gates")
        return self


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


CrossRepoAdoptionTargetRepo = Literal[
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
]


class CrossRepoOwnerAdoptionPacket(StrictModel):
    schema_version: str = "0.1"
    adoption_packet_id: str
    target_repo: CrossRepoAdoptionTargetRepo
    authority_plane: Literal[
        "control",
        "execution",
        "evidence",
        "skills_registry",
        "legal_knowledge_runtime",
        "mixed",
    ]
    status: Literal["ready_for_owner_review", "blocked_by_pr_readiness"]
    source_promotion_package_id: str
    source_promotion_package_ref: str
    source_readiness_audit_report_id: str
    source_readiness_audit_report_ref: str
    source_readiness_status: str
    source_pr_review_checklist_id: str
    source_pr_review_checklist_ref: str
    source_pr_review_checklist_status: str
    proposal_count: int = Field(ge=0)
    proposals: list[CrossRepoPromotionProposal]
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def owner_packet_counts_and_boundaries_match(self) -> "CrossRepoOwnerAdoptionPacket":
        if self.proposal_count != len(self.proposals):
            raise ValueError("owner adoption proposal count does not match")
        if not self.required_owner_actions:
            raise ValueError("owner adoption packet requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("owner adoption packet requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("owner adoption packet requires red-team notes")
        if not self.required_next_gates:
            raise ValueError("owner adoption packet requires next gates")
        if any(proposal.target_repo != self.target_repo for proposal in self.proposals):
            raise ValueError("owner adoption packet contains proposal for another repo")
        return self


class CrossRepoOwnerAdoptionReport(StrictModel):
    schema_version: str = "0.1"
    owner_adoption_report_id: str
    status: Literal["owner_adoption_packets_ready", "blocked_by_pr_readiness"]
    source_promotion_package_id: str
    source_promotion_package_ref: str
    source_readiness_audit_report_id: str
    source_readiness_audit_report_ref: str
    source_readiness_status: str
    source_pr_review_checklist_id: str
    source_pr_review_checklist_ref: str
    source_pr_review_checklist_status: str
    source_pr_review_checklist_recommendation: str
    target_repo_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    ready_packet_count: int = Field(ge=0)
    blocked_packet_count: int = Field(ge=0)
    proposal_count: int = Field(ge=0)
    target_repos: list[CrossRepoAdoptionTargetRepo]
    packets: list[CrossRepoOwnerAdoptionPacket]
    packet_output_refs: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def adoption_report_counts_match(self) -> "CrossRepoOwnerAdoptionReport":
        if self.packet_count != len(self.packets):
            raise ValueError("owner adoption packet count does not match")
        if self.target_repo_count != len(self.target_repos):
            raise ValueError("owner adoption target repo count does not match")
        if self.packet_count != len(self.packet_output_refs):
            raise ValueError("owner adoption packet output ref count does not match")
        if self.proposal_count != sum(packet.proposal_count for packet in self.packets):
            raise ValueError("owner adoption proposal count does not match packets")
        ready_count = sum(1 for packet in self.packets if packet.status == "ready_for_owner_review")
        blocked_count = self.packet_count - ready_count
        if self.ready_packet_count != ready_count or self.blocked_packet_count != blocked_count:
            raise ValueError("owner adoption ready/blocked counts do not match")
        if self.status == "owner_adoption_packets_ready" and self.blocked_packet_count:
            raise ValueError("ready owner adoption report cannot include blocked packets")
        if self.status == "blocked_by_pr_readiness" and not self.blocked_packet_count:
            raise ValueError("blocked owner adoption report requires blocked packets")
        if not self.required_next_gates:
            raise ValueError("owner adoption report requires next gates")
        return self


class CrossRepoOwnerIssueDraft(StrictModel):
    schema_version: str = "0.1"
    issue_draft_id: str
    target_repo: CrossRepoAdoptionTargetRepo
    source_owner_adoption_packet_id: str
    source_owner_adoption_packet_ref: str
    source_owner_adoption_packet_status: str
    status: Literal["ready_for_manual_issue_creation", "blocked_by_owner_adoption_packet"]
    suggested_title: str
    suggested_labels: list[str]
    issue_body_markdown: str
    proposal_count: int = Field(ge=0)
    proposal_ids: list[str]
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    manual_creation_required: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def issue_draft_counts_and_boundaries_match(self) -> "CrossRepoOwnerIssueDraft":
        if self.proposal_count != len(self.proposal_ids):
            raise ValueError("owner issue draft proposal count does not match")
        if not self.suggested_title:
            raise ValueError("owner issue draft requires a suggested title")
        if not self.suggested_labels:
            raise ValueError("owner issue draft requires suggested labels")
        if not self.issue_body_markdown:
            raise ValueError("owner issue draft requires issue body")
        if not self.required_owner_actions:
            raise ValueError("owner issue draft requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("owner issue draft requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("owner issue draft requires red-team notes")
        if not self.required_next_gates:
            raise ValueError("owner issue draft requires next gates")
        if (
            self.status == "ready_for_manual_issue_creation"
            and self.source_owner_adoption_packet_status != "ready_for_owner_review"
        ):
            raise ValueError("ready issue draft requires a ready owner adoption packet")
        if (
            self.status == "blocked_by_owner_adoption_packet"
            and self.source_owner_adoption_packet_status == "ready_for_owner_review"
        ):
            raise ValueError("blocked issue draft cannot come from a ready packet")
        return self


class CrossRepoOwnerIssueDraftReport(StrictModel):
    schema_version: str = "0.1"
    issue_draft_report_id: str
    status: Literal["issue_drafts_ready_for_manual_creation", "blocked_by_owner_adoption"]
    source_owner_adoption_report_id: str
    source_owner_adoption_report_ref: str
    source_owner_adoption_status: str
    draft_count: int = Field(ge=0)
    ready_draft_count: int = Field(ge=0)
    blocked_draft_count: int = Field(ge=0)
    target_repos: list[CrossRepoAdoptionTargetRepo]
    drafts: list[CrossRepoOwnerIssueDraft]
    draft_output_refs: list[str] = Field(default_factory=list)
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    manual_creation_required: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def issue_draft_report_counts_match(self) -> "CrossRepoOwnerIssueDraftReport":
        if self.draft_count != len(self.drafts):
            raise ValueError("owner issue draft count does not match")
        if self.draft_count != len(self.draft_output_refs):
            raise ValueError("owner issue draft output ref count does not match")
        ready_count = sum(
            1 for draft in self.drafts if draft.status == "ready_for_manual_issue_creation"
        )
        blocked_count = self.draft_count - ready_count
        if self.ready_draft_count != ready_count or self.blocked_draft_count != blocked_count:
            raise ValueError("owner issue draft ready/blocked counts do not match")
        if self.status == "issue_drafts_ready_for_manual_creation" and self.blocked_draft_count:
            raise ValueError("ready issue draft report cannot include blocked drafts")
        if self.status == "blocked_by_owner_adoption" and not self.blocked_draft_count:
            raise ValueError("blocked issue draft report requires blocked drafts")
        if not self.required_next_gates:
            raise ValueError("owner issue draft report requires next gates")
        return self


class CrossRepoOwnerIssueDraftQualityCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class CrossRepoOwnerIssueDraftQualityItem(StrictModel):
    target_repo: CrossRepoAdoptionTargetRepo
    issue_draft_id: str
    source_issue_draft_status: Literal[
        "ready_for_manual_issue_creation",
        "blocked_by_owner_adoption_packet",
    ]
    status: Literal[
        "ready_for_manual_owner_issue_review",
        "blocked_by_source_issue_draft",
        "failed_quality_gate",
    ]
    issue_draft_output_ref: str
    markdown_output_exists: bool
    markdown_matches_embedded_body: bool
    missing_required_sections: list[str] = Field(default_factory=list)
    missing_source_evidence_labels: list[str] = Field(default_factory=list)
    missing_boundary_phrases: list[str] = Field(default_factory=list)
    suggested_label_count: int = Field(ge=0)
    required_owner_action_count: int = Field(ge=0)
    acceptance_check_count: int = Field(ge=0)
    red_team_note_count: int = Field(ge=0)
    required_next_gate_count: int = Field(ge=0)
    proposal_count: int = Field(ge=0)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    manual_creation_required: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def owner_issue_draft_quality_item_status_matches_findings(
        self,
    ) -> "CrossRepoOwnerIssueDraftQualityItem":
        quality_blockers = (
            self.missing_required_sections
            or self.missing_source_evidence_labels
            or self.missing_boundary_phrases
            or not self.markdown_output_exists
            or not self.markdown_matches_embedded_body
            or not self.suggested_label_count
            or not self.required_owner_action_count
            or not self.acceptance_check_count
            or not self.red_team_note_count
            or not self.required_next_gate_count
        )
        if self.status == "ready_for_manual_owner_issue_review":
            if self.source_issue_draft_status != "ready_for_manual_issue_creation":
                raise ValueError("ready quality item requires ready source issue draft")
            if quality_blockers:
                raise ValueError("ready quality item cannot contain quality blockers")
        if self.status == "blocked_by_source_issue_draft":
            if self.source_issue_draft_status == "ready_for_manual_issue_creation":
                raise ValueError("source-blocked quality item requires blocked source draft")
        if self.status == "failed_quality_gate":
            if self.source_issue_draft_status != "ready_for_manual_issue_creation":
                raise ValueError("quality failure requires otherwise ready source draft")
            if not quality_blockers:
                raise ValueError("quality failure requires at least one quality blocker")
        return self


class CrossRepoOwnerIssueDraftQualityReport(StrictModel):
    schema_version: str = "0.1"
    quality_report_id: str
    status: Literal[
        "owner_issue_draft_quality_ready_for_manual_review",
        "blocked_by_owner_issue_draft_quality",
    ]
    source_issue_draft_report_id: str
    source_issue_draft_report_ref: str
    source_issue_draft_status: Literal[
        "issue_drafts_ready_for_manual_creation",
        "blocked_by_owner_adoption",
    ]
    draft_count: int = Field(ge=0)
    ready_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    failed_item_count: int = Field(ge=0)
    target_repos: list[CrossRepoAdoptionTargetRepo]
    quality_items: list[CrossRepoOwnerIssueDraftQualityItem]
    checks: list[CrossRepoOwnerIssueDraftQualityCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    manual_creation_required: Literal[True] = True
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def owner_issue_draft_quality_report_counts_match(
        self,
    ) -> "CrossRepoOwnerIssueDraftQualityReport":
        if self.draft_count != len(self.quality_items):
            raise ValueError("owner issue draft quality item count does not match")
        item_target_repos = [item.target_repo for item in self.quality_items]
        if set(self.target_repos) != set(item_target_repos) or len(self.target_repos) != len(
            item_target_repos
        ):
            raise ValueError("owner issue draft quality target repos do not match items")
        ready_count = sum(
            1 for item in self.quality_items if item.status == "ready_for_manual_owner_issue_review"
        )
        blocked_count = sum(
            1 for item in self.quality_items if item.status == "blocked_by_source_issue_draft"
        )
        failed_count = sum(1 for item in self.quality_items if item.status == "failed_quality_gate")
        if self.ready_item_count != ready_count:
            raise ValueError("owner issue draft quality ready count does not match")
        if self.blocked_item_count != blocked_count:
            raise ValueError("owner issue draft quality blocked count does not match")
        if self.failed_item_count != failed_count:
            raise ValueError("owner issue draft quality failed count does not match")
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if (
            self.status == "owner_issue_draft_quality_ready_for_manual_review"
            and self.source_issue_draft_status != "issue_drafts_ready_for_manual_creation"
        ):
            raise ValueError("ready owner issue draft quality report requires ready source report")
        if self.status == "owner_issue_draft_quality_ready_for_manual_review" and (
            failed_checks or blocked_count or failed_count
        ):
            raise ValueError("ready owner issue draft quality report cannot include blockers")
        if self.status == "blocked_by_owner_issue_draft_quality" and not (
            failed_checks or blocked_count or failed_count
        ):
            raise ValueError("blocked owner issue draft quality report requires blockers")
        required = {
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "cross_repo_contract_validation_after_owner_changes",
            "no_intake_github_or_sibling_repo_write",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("owner issue draft quality report is missing required gates")
        return self


class IntakeLocalCloseoutCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)


class IntakeLocalCloseoutReport(StrictModel):
    schema_version: str = "0.1"
    closeout_report_id: str
    status: Literal[
        "intake_local_closeout_ready_manual_actions_required",
        "blocked_by_closeout_evidence",
    ]
    observed_pr_number: int | None = None
    observed_pr_url: str | None = None
    observed_pr_state: Literal["draft", "ready_for_review", "merged", "not_supplied"] = (
        "not_supplied"
    )
    source_readiness_audit_report_id: str
    source_readiness_audit_report_ref: str
    source_readiness_status: str
    source_review_readiness: str
    source_pr_review_checklist_id: str
    source_pr_review_checklist_ref: str
    source_pr_review_checklist_status: str
    source_pr_review_checklist_recommendation: str
    source_owner_adoption_report_id: str
    source_owner_adoption_report_ref: str
    source_owner_adoption_status: str
    source_owner_issue_draft_report_id: str
    source_owner_issue_draft_report_ref: str
    source_owner_issue_draft_status: str
    check_count: int = Field(ge=0)
    passed_check_count: int = Field(ge=0)
    blocking_check_count: int = Field(ge=0)
    checks: list[IntakeLocalCloseoutCheck]
    manual_actions_remaining: list[str]
    generated_artifact_refs: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_completion_scope: Literal[
        "intake_candidate_complete_manual_external_actions_required"
    ] = "intake_candidate_complete_manual_external_actions_required"
    manual_pr_state_change_required: Literal[True] = True
    manual_owner_issue_creation_required: Literal[True] = True
    pr_state_change_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    proposed_changes_applied: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def closeout_counts_and_boundaries_match(self) -> "IntakeLocalCloseoutReport":
        if self.check_count != len(self.checks):
            raise ValueError("closeout check count does not match")
        passed_count = sum(1 for check in self.checks if check.status == "passed")
        blocked_count = self.check_count - passed_count
        if self.passed_check_count != passed_count:
            raise ValueError("closeout passed check count does not match")
        if self.blocking_check_count != blocked_count:
            raise ValueError("closeout blocking check count does not match")
        if not self.manual_actions_remaining:
            raise ValueError("closeout report requires manual actions")
        if not self.generated_artifact_refs:
            raise ValueError("closeout report requires generated artifact refs")
        if (
            self.status == "intake_local_closeout_ready_manual_actions_required"
            and self.blocking_check_count
        ):
            raise ValueError("ready closeout cannot include blocked checks")
        if self.status == "blocked_by_closeout_evidence" and not self.blocking_check_count:
            raise ValueError("blocked closeout requires blocked checks")
        return self


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
