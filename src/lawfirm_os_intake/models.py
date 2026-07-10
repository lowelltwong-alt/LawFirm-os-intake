from __future__ import annotations

import json
from hashlib import sha256
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


MatterLinkKeyType = Literal[
    "claim_number",
    "policy_number",
    "docket_ref",
    "adjuster_ref",
    "party_pair",
    "employer_employee_pair",
    "counsel_ref",
    "email_thread",
    "attachment_identity",
    "incident_date_party",
    "subsidiary_alias",
]


class MatterLinkKey(StrictModel):
    key_id: str
    key_type: MatterLinkKeyType
    raw_value: str
    normalized_value: str
    tier: Literal["strong", "medium", "weak"]
    evidence_refs: list[EvidenceRef]
    extraction_rule_id: str
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def matter_link_key_is_source_bound(self) -> "MatterLinkKey":
        if not self.key_id.strip():
            raise ValueError("matter-link key requires key_id")
        if not self.raw_value.strip():
            raise ValueError("matter-link key requires raw_value")
        if not self.normalized_value.strip():
            raise ValueError("matter-link key requires normalized_value")
        if not self.extraction_rule_id.strip():
            raise ValueError("matter-link key requires extraction_rule_id")
        if not self.evidence_refs:
            raise ValueError("matter-link key requires source-bound evidence refs")
        for ref in self.evidence_refs:
            if ref.start_offset < 0 or ref.end_offset <= ref.start_offset:
                raise ValueError("matter-link key evidence ref has invalid offsets")
            if not ref.sha256.startswith("sha256:"):
                raise ValueError("matter-link key evidence ref requires sha256 hash")
        return self


class MatterLinkKeySet(StrictModel):
    document_id: str
    bundle_id: str
    sender_identity: str
    keys: list[MatterLinkKey] = Field(default_factory=list)
    extraction_gaps: list[str] = Field(default_factory=list)
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def matter_link_key_set_is_candidate_only(self) -> "MatterLinkKeySet":
        if not self.document_id.strip():
            raise ValueError("matter-link key set requires document_id")
        if not self.bundle_id.strip():
            raise ValueError("matter-link key set requires bundle_id")
        if len({key.key_id for key in self.keys}) != len(self.keys):
            raise ValueError("matter-link key IDs must be unique within a document")
        return self


class EntityNormalizationResult(StrictModel):
    raw_value: str
    normalized_value: str
    base_value: str
    suffix_stripped: str | None = None
    rewrites_applied: list[str] = Field(default_factory=list)
    residual_terms_stripped: list[str] = Field(default_factory=list)
    normalization_rule_ids: list[str]
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def entity_normalization_result_is_complete(self) -> "EntityNormalizationResult":
        if not self.raw_value.strip():
            raise ValueError("entity normalization requires raw_value")
        if not self.normalized_value.strip():
            raise ValueError("entity normalization requires normalized_value")
        if not self.base_value.strip():
            raise ValueError("entity normalization requires base_value")
        if not self.normalization_rule_ids:
            raise ValueError("entity normalization requires rule ids")
        return self


class EntityComparisonResult(StrictModel):
    left: EntityNormalizationResult
    right: EntityNormalizationResult
    comparison_rung: Literal[
        "E1_exact",
        "E2_normalized_exact",
        "E3_declared_alias",
        "E4_declared_structure",
        "E5_suffix_residual",
        "E6_no_match",
    ]
    outcome: Literal["match", "related", "hold", "no_match"]
    disposition: Literal[
        "raw_exact",
        "normalized_exact",
        "declared_alias",
        "related_distinct",
        "unreviewed_structure_edge",
        "suffix_conflict",
        "possible_affiliate",
        "no_match",
    ]
    decision_rule_ids: list[str]
    review_required: bool
    alias_proposal_required: bool
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def entity_comparison_result_matches_rung(self) -> "EntityComparisonResult":
        if not self.decision_rule_ids:
            raise ValueError("entity comparison requires decision rule ids")
        if self.outcome == "match" and self.review_required:
            raise ValueError("entity matches must not require review in this local result")
        if self.outcome != "hold" and self.alias_proposal_required:
            raise ValueError("only held entity comparisons may propose alias-table review")
        if self.comparison_rung == "E6_no_match" and self.outcome != "no_match":
            raise ValueError("E6 comparisons must be no_match")
        if self.comparison_rung == "E3_declared_alias" and (
            self.outcome != "match" or self.disposition != "declared_alias"
        ):
            raise ValueError("E3 comparisons must be declared alias matches")
        if self.comparison_rung == "E4_declared_structure":
            if self.disposition not in {"related_distinct", "unreviewed_structure_edge"}:
                raise ValueError("E4 comparisons require a structural-edge disposition")
            if self.disposition == "related_distinct" and self.outcome != "related":
                raise ValueError(
                    "reviewed E4 comparisons must preserve related-but-distinct entities"
                )
            if self.disposition == "unreviewed_structure_edge" and self.outcome != "hold":
                raise ValueError("unreviewed E4 comparisons must hold for review")
        if self.outcome == "hold" and not self.review_required:
            raise ValueError("held entity comparisons require human review")
        return self


class MatterLinkKeyExtractionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    document_ids: list[str] = Field(default_factory=list)
    key_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkKeyExtractionReport(StrictModel):
    schema_version: str = "0.1"
    matter_link_key_extraction_report_id: str
    status: Literal[
        "matter_link_keys_extracted_for_review",
        "blocked_matter_link_key_extraction",
    ]
    bundle_id: str
    policy_ref: str
    policy_sha256: str
    document_count: int = Field(ge=0)
    key_count: int = Field(ge=0)
    key_sets: list[MatterLinkKeySet]
    checks: list[MatterLinkKeyExtractionCheck]
    required_next_gates: list[str]
    candidate_exception_lake_labels: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    no_clustering_performed: Literal[True] = True
    matter_identity_asserted: Literal[False] = False
    matter_link_finalized: Literal[False] = False
    sender_identity_used_as_link_key: Literal[False] = False
    fuzzy_matching_performed: Literal[False] = False
    acronym_inference_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def matter_link_key_extraction_report_is_consistent(
        self,
    ) -> "MatterLinkKeyExtractionReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.document_count != len(self.key_sets):
            raise ValueError("matter-link key report document count mismatch")
        if self.key_count != sum(len(key_set.keys) for key_set in self.key_sets):
            raise ValueError("matter-link key report key count mismatch")
        key_ids = [key.key_id for key_set in self.key_sets for key in key_set.keys]
        if len(set(key_ids)) != len(key_ids):
            raise ValueError("matter-link key report key IDs must be unique")
        if self.status == "matter_link_keys_extracted_for_review" and failed:
            raise ValueError("ready matter-link key report cannot include failed checks")
        if self.status == "blocked_matter_link_key_extraction" and not failed:
            raise ValueError("blocked matter-link key report requires failed checks")
        required_gates = {
            "human_matter_linking_review",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_matter_link_keys",
        }
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-link key report is missing required next gates")
        if not self.candidate_exception_lake_labels:
            raise ValueError("matter-link key report requires candidate Lake labels")
        return self


MatterLinkDecisionOutcome = Literal["merge", "split", "hold", "block"]
MatterLinkAmbiguityClass = Literal[
    "corroborated_multi_key",
    "single_strong_key",
    "medium_key_only",
    "weak_key_only",
    "conflicted",
]
MatterLinkClusterDisposition = Literal[
    "proposed_link",
    "hold_for_more_documents",
    "human_review_required",
    "blocked_conflict",
]


class MatterLinkDecisionRecord(StrictModel):
    schema_version: str = "0.1"
    decision_id: str
    left_document_id: str
    right_document_id: str
    rule_id: str
    outcome: MatterLinkDecisionOutcome
    ambiguity_signal: str
    supporting_key_ids: list[str] = Field(default_factory=list)
    conflicting_key_ids: list[str] = Field(default_factory=list)
    note: str
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def matter_link_decision_record_is_complete(self) -> "MatterLinkDecisionRecord":
        if not self.decision_id.strip():
            raise ValueError("matter-link decision requires decision_id")
        if not self.left_document_id.strip() or not self.right_document_id.strip():
            raise ValueError("matter-link decision requires document ids")
        if self.left_document_id == self.right_document_id:
            raise ValueError("matter-link decision requires two distinct documents")
        if not self.rule_id.strip():
            raise ValueError("matter-link decision requires rule_id")
        if not self.ambiguity_signal.strip():
            raise ValueError("matter-link decision requires ambiguity_signal")
        if not self.note.strip():
            raise ValueError("matter-link decision requires note")
        if self.outcome in {"merge", "hold"} and self.conflicting_key_ids:
            raise ValueError("non-conflict matter-link decisions cannot include conflict keys")
        if self.outcome in {"split", "block"} and not self.conflicting_key_ids:
            raise ValueError("split/block matter-link decisions require conflict keys")
        if self.outcome == "merge" and not self.supporting_key_ids:
            raise ValueError("merge matter-link decisions require supporting keys")
        return self


class MatterClusterProposal(StrictModel):
    schema_version: str = "0.1"
    cluster_id: str
    document_ids: list[str]
    ambiguity_class: MatterLinkAmbiguityClass
    supporting_keys: list[MatterLinkKey] = Field(default_factory=list)
    conflicting_keys: list[MatterLinkKey] = Field(default_factory=list)
    disposition: MatterLinkClusterDisposition
    decision_rule_ids: list[str]
    decision_ids: list[str]
    blocking_decision_ids: list[str] = Field(default_factory=list)
    requires_human_confirmation: Literal[True] = True
    matter_identity_asserted: Literal[False] = False
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def matter_cluster_proposal_is_review_only(self) -> "MatterClusterProposal":
        if not self.cluster_id.strip():
            raise ValueError("matter cluster proposal requires cluster_id")
        if not self.document_ids:
            raise ValueError("matter cluster proposal requires documents")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("matter cluster proposal document ids must be unique")
        if not self.decision_rule_ids:
            raise ValueError("matter cluster proposal requires decision rules")
        if len(set(self.decision_ids)) != len(self.decision_ids):
            raise ValueError("matter cluster proposal decision ids must be unique")
        if self.ambiguity_class == "conflicted":
            if self.disposition != "blocked_conflict":
                raise ValueError("conflicted matter clusters must be blocked_conflict")
            if not self.conflicting_keys and not self.blocking_decision_ids:
                raise ValueError("conflicted matter clusters require conflict evidence")
        if self.disposition == "proposed_link" and self.ambiguity_class not in {
            "corroborated_multi_key",
            "single_strong_key",
        }:
            raise ValueError("only strong-supported matter clusters may be proposed links")
        return self


class MatterLinkingClusterCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    document_ids: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkingClusterReport(StrictModel):
    schema_version: str = "0.1"
    matter_linking_cluster_report_id: str
    status: Literal[
        "matter_linking_clusters_proposed_for_review",
        "blocked_matter_linking_cluster_validation",
    ]
    source_matter_link_key_extraction_report_id: str
    bundle_id: str
    document_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    cluster_count: int = Field(ge=0)
    conflicted_cluster_count: int = Field(ge=0)
    hold_cluster_count: int = Field(ge=0)
    proposed_link_cluster_count: int = Field(ge=0)
    decisions: list[MatterLinkDecisionRecord]
    clusters: list[MatterClusterProposal]
    checks: list[MatterLinkingClusterCheck]
    required_next_gates: list[str]
    candidate_exception_lake_labels: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    matter_identity_asserted: Literal[False] = False
    matter_link_finalized: Literal[False] = False
    budget_generation_performed: Literal[False] = False
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    connector_called: Literal[False] = False
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    order_invariant_algorithm: Literal[True] = True
    generated_at: str

    @model_validator(mode="after")
    def matter_linking_cluster_report_counts_match(self) -> "MatterLinkingClusterReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.decision_count != len(self.decisions):
            raise ValueError("matter-linking decision count mismatch")
        if self.cluster_count != len(self.clusters):
            raise ValueError("matter-linking cluster count mismatch")
        if self.conflicted_cluster_count != sum(
            1 for cluster in self.clusters if cluster.ambiguity_class == "conflicted"
        ):
            raise ValueError("matter-linking conflicted cluster count mismatch")
        if self.hold_cluster_count != sum(
            1 for cluster in self.clusters if cluster.disposition == "hold_for_more_documents"
        ):
            raise ValueError("matter-linking hold cluster count mismatch")
        if self.proposed_link_cluster_count != sum(
            1 for cluster in self.clusters if cluster.disposition == "proposed_link"
        ):
            raise ValueError("matter-linking proposed-link cluster count mismatch")
        if len({decision.decision_id for decision in self.decisions}) != len(self.decisions):
            raise ValueError("matter-linking decision ids must be unique")
        if len({cluster.cluster_id for cluster in self.clusters}) != len(self.clusters):
            raise ValueError("matter-linking cluster ids must be unique")
        if self.status == "matter_linking_clusters_proposed_for_review" and failed:
            raise ValueError("ready matter-linking cluster report cannot include failed checks")
        if self.status == "blocked_matter_linking_cluster_validation" and not failed:
            raise ValueError("blocked matter-linking cluster report requires failed checks")
        required_gates = {
            "human_matter_linking_review",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_matter_linking_clusters",
        }
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-linking cluster report is missing required next gates")
        if not self.candidate_exception_lake_labels:
            raise ValueError("matter-linking cluster report requires candidate labels")
        return self


MatterLinkingClusterReviewOutcome = Literal[
    "confirm_budget_scope_cluster",
    "confirm_split",
    "unknown",
    "request_more_info",
    "declined_or_referred",
]


class MatterLinkingClusterReviewDecision(StrictModel):
    schema_version: str = "0.1"
    decision_id: str
    outcome: MatterLinkingClusterReviewOutcome
    selected_cluster_ids: list[str]
    decision_reason: str
    evidence_refs: list[str]
    required_followups: list[str] = Field(default_factory=list)
    followup_owner: str | None = None
    followup_due_at: str | None = None
    red_team_notes: list[str]
    candidate_exception_lake_labels: list[str]

    @model_validator(mode="after")
    def matter_linking_cluster_review_decision_is_complete(
        self,
    ) -> "MatterLinkingClusterReviewDecision":
        if not self.decision_id.strip():
            raise ValueError("matter-linking cluster review decision requires decision_id")
        if not self.selected_cluster_ids:
            raise ValueError("matter-linking cluster review decision requires selected clusters")
        if len(set(self.selected_cluster_ids)) != len(self.selected_cluster_ids):
            raise ValueError("matter-linking cluster review selected cluster IDs must be unique")
        if not self.decision_reason.strip():
            raise ValueError("matter-linking cluster review decision requires reason")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("matter-linking cluster review decision requires evidence refs")
        if not self.red_team_notes or any(not note.strip() for note in self.red_team_notes):
            raise ValueError("matter-linking cluster review decision requires red-team notes")
        if not self.candidate_exception_lake_labels or any(
            not label.strip() for label in self.candidate_exception_lake_labels
        ):
            raise ValueError("matter-linking cluster review decision requires candidate labels")
        if self.outcome == "confirm_budget_scope_cluster" and len(self.selected_cluster_ids) != 1:
            raise ValueError("budget-scope confirmation requires exactly one cluster")
        if self.outcome == "confirm_split" and len(self.selected_cluster_ids) < 2:
            raise ValueError("split confirmation requires at least two clusters")
        if self.outcome in {"unknown", "request_more_info", "declined_or_referred"}:
            if not (self.followup_owner and self.followup_owner.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_owner")
            if not (self.followup_due_at and self.followup_due_at.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_due_at")
            if not self.required_followups:
                raise ValueError(f"{self.outcome} decisions require required_followups")
        return self


class MatterLinkingClusterReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    matter_linking_cluster_review_outcome_record_id: str
    matter_linking_cluster_report_id: str
    source_matter_linking_cluster_report_ref: str | None = None
    reviewer_id: str
    reviewer_role: str | None = None
    reviewed_at: str
    overall_outcome: MatterLinkingClusterReviewOutcome
    decision_reason: str
    decisions: list[MatterLinkingClusterReviewDecision]
    supersedes_matter_linking_cluster_review_outcome_record_id: str | None = None
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_conflict_conclusion: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def matter_linking_cluster_review_outcome_record_is_complete(
        self,
    ) -> "MatterLinkingClusterReviewOutcomeRecord":
        if not self.matter_linking_cluster_review_outcome_record_id.strip():
            raise ValueError("matter-linking cluster review outcome record requires id")
        if not self.matter_linking_cluster_report_id.strip():
            raise ValueError("matter-linking cluster review outcome record requires report id")
        if not self.reviewer_id.strip():
            raise ValueError("matter-linking cluster review outcome record requires reviewer")
        if not self.reviewed_at.strip():
            raise ValueError("matter-linking cluster review outcome record requires timestamp")
        if not self.decision_reason.strip():
            raise ValueError("matter-linking cluster review outcome record requires reason")
        if not self.decisions:
            raise ValueError("matter-linking cluster review outcome record requires decisions")
        decision_ids = [decision.decision_id for decision in self.decisions]
        if len(set(decision_ids)) != len(decision_ids):
            raise ValueError("matter-linking cluster review decision IDs must be unique")
        if self.overall_outcome not in {decision.outcome for decision in self.decisions}:
            raise ValueError("matter-linking cluster review overall outcome must match a decision")
        return self


class MatterLinkingClusterReviewOutcomeCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    cluster_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkingClusterReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    matter_linking_cluster_review_outcome_report_id: str
    status: Literal[
        "matter_linking_cluster_review_confirmed_for_budget_scope",
        "matter_linking_cluster_review_recorded_pending_followup",
        "blocked_by_matter_linking_cluster_review",
    ]
    source_matter_linking_cluster_report_ref: str
    matter_linking_cluster_report_id: str
    source_matter_linking_cluster_status: str
    matter_linking_cluster_review_outcome_record_id: str
    reviewer_id: str
    reviewed_at: str
    overall_outcome: MatterLinkingClusterReviewOutcome
    decision_reason: str
    source_cluster_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    budget_scope_cluster_count: int = Field(ge=0)
    reviewed_cluster_count: int = Field(ge=0)
    unreviewed_cluster_count: int = Field(ge=0)
    unknown_cluster_count: int = Field(ge=0)
    budget_blocking_cluster_count: int = Field(ge=0)
    budget_scope_cluster_ids: list[str]
    reviewed_cluster_ids: list[str]
    unreviewed_cluster_ids: list[str]
    unknown_cluster_ids: list[str]
    budget_blocking_cluster_ids: list[str]
    required_followups: list[str]
    candidate_lake_event_labels: list[str]
    append_only_history_ref: str
    checks: list[MatterLinkingClusterReviewOutcomeCheck]
    required_next_gates: list[str]
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    matter_identity_asserted: Literal[False] = False
    matter_link_finalized: Literal[False] = False
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def matter_linking_cluster_review_outcome_report_counts_match(
        self,
    ) -> "MatterLinkingClusterReviewOutcomeReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.decision_count < 1:
            raise ValueError("matter-linking cluster review report requires decisions")
        if self.budget_scope_cluster_count != len(self.budget_scope_cluster_ids):
            raise ValueError("matter-linking cluster review budget-scope count mismatch")
        if self.reviewed_cluster_count != len(self.reviewed_cluster_ids):
            raise ValueError("matter-linking cluster review reviewed count mismatch")
        if self.unreviewed_cluster_count != len(self.unreviewed_cluster_ids):
            raise ValueError("matter-linking cluster review unreviewed count mismatch")
        if self.unknown_cluster_count != len(self.unknown_cluster_ids):
            raise ValueError("matter-linking cluster review unknown count mismatch")
        if self.budget_blocking_cluster_count != len(self.budget_blocking_cluster_ids):
            raise ValueError("matter-linking cluster review blocking count mismatch")
        if self.status == "matter_linking_cluster_review_confirmed_for_budget_scope":
            if (
                failed
                or self.budget_scope_cluster_count != 1
                or self.budget_blocking_cluster_count
                or self.unreviewed_cluster_count
                or self.unknown_cluster_count
            ):
                raise ValueError("confirmed budget-scope cluster review cannot have blockers")
        if self.status == "matter_linking_cluster_review_recorded_pending_followup" and failed:
            raise ValueError("pending matter-linking cluster review cannot include failed checks")
        if self.status == "blocked_by_matter_linking_cluster_review" and not failed:
            raise ValueError("blocked matter-linking cluster review requires failed checks")
        required_gates = {
            "append_only_matter_linking_cluster_review_outcome",
            "exception_lake_owner_review_before_admission",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_intake",
            "no_silent_learning_from_matter_linking_cluster_review",
        }
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-linking cluster review is missing required gates")
        if not self.candidate_lake_event_labels:
            raise ValueError("matter-linking cluster review requires candidate labels")
        return self


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


RustToolLadderStage = Literal[
    "s0_candidate",
    "s1_shadow",
    "s2_audit",
    "s3_cosign",
    "s4_authoritative",
]


class RustToolLadderHistoryEvent(StrictModel):
    event_id: str
    stage: RustToolLadderStage
    recorded_at: str
    actor: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    human_signoff_ref: str | None = None


class RustToolLadderTool(StrictModel):
    tool_id: str
    purpose: str
    stage: RustToolLadderStage
    stage_ceiling: RustToolLadderStage
    review_by: str
    scope_items: list[str]
    replacement_target: str = "none"
    gate_evidence: dict[str, list[str]] = Field(default_factory=dict)
    cargo_manifest_ref: str | None = None
    cargo_binary_name: str | None = None
    wrapper_module_ref: str | None = None
    cli_command_ref: str | None = None
    test_refs: list[str] = Field(default_factory=list)
    ci_wiring_refs: list[str] = Field(default_factory=list)
    parity_corpus_ref: str | None = None
    python_oracle_ref: str | None = None
    adjudication_dir_ref: str | None = None
    contract_lock_ref: str | None = None
    weekly_parity_job_ref: str | None = None
    frozen_goldens_reviewed: bool = False
    python_retained_as_oracle: bool = True
    rust_output_consumed_downstream: bool = False
    rust_replacement_allowed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    history: list[RustToolLadderHistoryEvent]

    @model_validator(mode="after")
    def rust_tool_ladder_history_matches_current_stage(self) -> "RustToolLadderTool":
        if not self.history:
            raise ValueError("rust tool ladder entries require append-only history")
        if self.history[-1].stage != self.stage:
            raise ValueError("latest rust tool ladder history event must match current stage")
        if self.rust_output_consumed_downstream and self.stage not in {
            "s3_cosign",
            "s4_authoritative",
        }:
            raise ValueError("Rust output cannot be consumed downstream before co-sign")
        return self


class RustToolLadderConfig(StrictModel):
    schema_version: str = "0.1"
    ladder_id: str
    status: Literal["local_candidate"]
    authority: str
    rust_transition_policy_ref: str
    methodology_version: Literal["rust_tool_ladder.v0_1"] = "rust_tool_ladder.v0_1"
    stage_order: list[RustToolLadderStage]
    tools: list[RustToolLadderTool]
    rust_replacement_allowed: Literal[False] = False
    no_connector_or_external_writes: Literal[True] = True
    no_lake_or_sqlite_writes: Literal[True] = True
    no_budget_or_matter_authority: Literal[True] = True
    no_canonical_authority: Literal[True] = True
    candidate_only: Literal[True] = True

    @model_validator(mode="after")
    def rust_tool_ladder_config_is_coherent(self) -> "RustToolLadderConfig":
        if self.stage_order != [
            "s0_candidate",
            "s1_shadow",
            "s2_audit",
            "s3_cosign",
            "s4_authoritative",
        ]:
            raise ValueError("rust tool ladder stage_order must match the governed ladder")
        tool_ids = [tool.tool_id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("rust tool ladder tool_id values must be unique")
        return self


class RustToolLadderAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    tool_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class RustToolLadderAuditReport(StrictModel):
    schema_version: str = "0.1"
    rust_tool_ladder_audit_report_id: str
    status: Literal["rust_tool_ladder_ready_for_review", "blocked_by_rust_tool_ladder"]
    ladder_ref: str
    ladder_id: str | None = None
    rust_transition_policy_ref: str | None = None
    methodology_version: Literal["rust_tool_ladder.v0_1"] = "rust_tool_ladder.v0_1"
    tool_count: int = Field(ge=0)
    s0_candidate_count: int = Field(ge=0)
    s1_shadow_count: int = Field(ge=0)
    s2_audit_count: int = Field(ge=0)
    s3_cosign_count: int = Field(ge=0)
    s4_authoritative_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    checks: list[RustToolLadderAuditCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    rust_replacement_allowed: Literal[False] = False
    rust_authoritative_runtime_enabled: Literal[False] = False
    connector_or_external_writes_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    canonical_promotion_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    generated_at: str

    @model_validator(mode="after")
    def rust_tool_ladder_report_counts_match(self) -> "RustToolLadderAuditReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.failed_check_count != len(failed):
            raise ValueError("rust tool ladder failed check count mismatch")
        stage_total = (
            self.s0_candidate_count
            + self.s1_shadow_count
            + self.s2_audit_count
            + self.s3_cosign_count
            + self.s4_authoritative_count
        )
        if self.tool_count != stage_total:
            raise ValueError("rust tool ladder stage counts must equal tool count")
        if self.status == "rust_tool_ladder_ready_for_review" and failed:
            raise ValueError("ready rust tool ladder report cannot include failed checks")
        if self.status == "blocked_by_rust_tool_ladder" and not failed:
            raise ValueError("blocked rust tool ladder report requires failed checks")
        return self


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


class LaborEmploymentBudgetFactGoldFindingExpectation(StrictModel):
    fact_id: str
    expected_state: LaborEmploymentBudgetFactState
    expected_source_bound: bool | None = None
    expected_source_label_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True


class LaborEmploymentBudgetFactGoldCaseSpec(StrictModel):
    case_id: str
    label: str
    manifest_ref: str
    expected_manifest_id: str
    expected_status: Literal[
        "labor_employment_budget_facts_ready_for_review",
        "blocked_labor_employment_budget_fact_audit",
    ]
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_finding_count: int = Field(ge=0)
    expected_source_bound_finding_count: int = Field(ge=0)
    expected_needs_review_finding_count: int = Field(ge=0)
    expected_unknown_finding_count: int = Field(ge=0)
    expected_gap_count: int = Field(ge=0)
    expected_critical_gap_count: int = Field(ge=0)
    expected_critical_gap_ids: list[str] = Field(default_factory=list)
    expected_warning_gap_ids: list[str] = Field(default_factory=list)
    expected_relationship_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    expected_relationship_unresolved_fact_ids: list[str] = Field(default_factory=list)
    expected_person_candidate_count: int = Field(ge=0)
    expected_organization_candidate_count: int = Field(ge=0)
    expected_source_bound_relationship_count: int = Field(ge=0)
    expected_critical_relationship_gap_count: int = Field(ge=0)
    expected_findings: list[LaborEmploymentBudgetFactGoldFindingExpectation]
    red_team_notes: list[str] = Field(default_factory=list)
    require_no_side_effects: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    reviewed: Literal[True] = True

    @model_validator(mode="after")
    def le_budget_fact_gold_case_expectations_are_unique(
        self,
    ) -> "LaborEmploymentBudgetFactGoldCaseSpec":
        fact_ids = [finding.fact_id for finding in self.expected_findings]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("L&E budget fact gold finding expectations must be unique")
        return self


class LaborEmploymentBudgetFactGoldSpec(StrictModel):
    schema_version: str = "0.1"
    gold_id: str
    status: Literal["reviewed_labor_employment_budget_fact_gold"]
    reviewed: Literal[True] = True
    data_scope: Literal["synthetic"] = "synthetic"
    practice_area: Literal["labor_employment"] = "labor_employment"
    policy_ref: str = "config/labor-employment-budget-fact-needs.yaml"
    cases: list[LaborEmploymentBudgetFactGoldCaseSpec]
    required_next_gates: list[str] = Field(
        default_factory=lambda: [
            "human_labor_employment_budget_fact_review",
            "budget_fact_gold_before_calibration_or_model_comparison",
            "no_amount_budget_from_gold_report",
        ]
    )
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

    @model_validator(mode="after")
    def le_budget_fact_gold_spec_cases_are_unique(
        self,
    ) -> "LaborEmploymentBudgetFactGoldSpec":
        case_ids = [case.case_id for case in self.cases]
        manifest_refs = [case.manifest_ref for case in self.cases]
        if not self.cases:
            raise ValueError("L&E budget fact gold requires at least one case")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("L&E budget fact gold case IDs must be unique")
        if len(manifest_refs) != len(set(manifest_refs)):
            raise ValueError("L&E budget fact gold manifest refs must be unique")
        return self


class LaborEmploymentBudgetFactGoldCaseResult(StrictModel):
    case_id: str
    label: str
    manifest_ref: str
    manifest_id: str | None = None
    status: Literal["passed", "failed"]
    audit_report_status: str | None = None
    audit_budget_readiness_state: str | None = None
    failed_expectation_ids: list[str]
    report_ref: str | None = None
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_budget_fact_gold_case_result_status_matches_failures(
        self,
    ) -> "LaborEmploymentBudgetFactGoldCaseResult":
        if self.status == "passed" and self.failed_expectation_ids:
            raise ValueError("passed L&E budget fact gold case cannot include failures")
        if self.status == "failed" and not self.failed_expectation_ids:
            raise ValueError("failed L&E budget fact gold case requires failures")
        return self


class LaborEmploymentBudgetFactGoldCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    case_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LaborEmploymentBudgetFactGoldReport(StrictModel):
    schema_version: str = "0.1"
    labor_employment_budget_fact_gold_report_id: str
    status: Literal["passed", "failed"]
    gold_id: str
    gold_ref: str
    reviewed_gold: bool
    data_scope: Literal["synthetic"]
    policy_ref: str
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    check_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    cases: list[LaborEmploymentBudgetFactGoldCaseResult]
    checks: list[LaborEmploymentBudgetFactGoldCheck]
    required_next_gates: list[str]
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
    generated_at: str

    @model_validator(mode="after")
    def le_budget_fact_gold_report_counts_match(
        self,
    ) -> "LaborEmploymentBudgetFactGoldReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("L&E budget fact gold case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("L&E budget fact gold failed case count mismatch")
        if self.check_count != len(self.checks):
            raise ValueError("L&E budget fact gold check count mismatch")
        if self.failed_check_count != len(failed_checks):
            raise ValueError("L&E budget fact gold failed check count mismatch")
        if self.status == "passed" and (failed_cases or failed_checks):
            raise ValueError("passed L&E budget fact gold report cannot include failures")
        if self.status == "failed" and not (failed_cases or failed_checks):
            raise ValueError("failed L&E budget fact gold report requires failures")
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


class LaborEmploymentExecutableCoverageCase(StrictModel):
    pack_case_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    coverage_state: Literal["covered_executable", "missing_executable"]
    executable_fixture_ids: list[str] = Field(default_factory=list)
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    missing_critical_fact_ids: list[str] = Field(default_factory=list)
    missing_important_fact_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_executable_coverage_case_state_matches_links(
        self,
    ) -> "LaborEmploymentExecutableCoverageCase":
        if self.coverage_state == "covered_executable" and not self.executable_fixture_ids:
            raise ValueError("covered executable L&E case requires executable fixture IDs")
        if self.coverage_state == "missing_executable" and self.executable_fixture_ids:
            raise ValueError("missing executable L&E case cannot include executable fixture IDs")
        return self


class LaborEmploymentExecutableCoverageFamily(StrictModel):
    family: LaborEmploymentSyntheticFixtureFamily
    pack_case_count: int = Field(ge=0)
    covered_case_count: int = Field(ge=0)
    missing_case_count: int = Field(ge=0)
    covered_variants: list[LaborEmploymentSyntheticFixtureVariant]
    missing_variants: list[LaborEmploymentSyntheticFixtureVariant]
    executable_fixture_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def le_executable_coverage_family_counts_match(
        self,
    ) -> "LaborEmploymentExecutableCoverageFamily":
        if self.pack_case_count != self.covered_case_count + self.missing_case_count:
            raise ValueError("L&E executable family coverage count mismatch")
        return self


class LaborEmploymentExecutableCoverageCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentExecutableCoverageReport(StrictModel):
    schema_version: str = "0.1"
    executable_coverage_report_id: str
    status: Literal[
        "labor_employment_executable_coverage_ready_for_review",
        "blocked_labor_employment_executable_coverage",
    ]
    coverage_state: Literal["partial_executable_coverage", "complete_executable_coverage"]
    pack_id: str
    pack_ref: str
    executable_manifest_id: str
    executable_manifest_ref: str
    pack_case_count: int = Field(ge=0)
    executable_fixture_count: int = Field(ge=0)
    executable_pack_case_link_count: int = Field(ge=0)
    covered_pack_case_count: int = Field(ge=0)
    missing_executable_pack_case_count: int = Field(ge=0)
    covered_family_count: int = Field(ge=0)
    missing_family_count: int = Field(ge=0)
    covered_family_variant_count: int = Field(ge=0)
    missing_family_variant_count: int = Field(ge=0)
    covered_pack_case_ids: list[str]
    missing_executable_pack_case_ids: list[str]
    missing_family_variant_refs: list[str]
    family_coverage: list[LaborEmploymentExecutableCoverageFamily]
    case_coverage: list[LaborEmploymentExecutableCoverageCase]
    checks: list[LaborEmploymentExecutableCoverageCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
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
    def le_executable_coverage_report_counts_match(
        self,
    ) -> "LaborEmploymentExecutableCoverageReport":
        failed = [check for check in self.checks if check.status == "failed"]
        covered_cases = [
            case for case in self.case_coverage if case.coverage_state == "covered_executable"
        ]
        missing_cases = [
            case for case in self.case_coverage if case.coverage_state == "missing_executable"
        ]
        if self.pack_case_count != len(self.case_coverage):
            raise ValueError("L&E executable coverage pack case count mismatch")
        if self.covered_pack_case_count != len(covered_cases):
            raise ValueError("L&E executable covered case count mismatch")
        if self.missing_executable_pack_case_count != len(missing_cases):
            raise ValueError("L&E executable missing case count mismatch")
        if self.covered_pack_case_ids != [case.pack_case_id for case in covered_cases]:
            raise ValueError("L&E executable covered case IDs mismatch")
        if self.missing_executable_pack_case_ids != [case.pack_case_id for case in missing_cases]:
            raise ValueError("L&E executable missing case IDs mismatch")
        if self.coverage_state == "complete_executable_coverage" and missing_cases:
            raise ValueError("complete L&E executable coverage cannot have missing cases")
        if self.coverage_state == "partial_executable_coverage" and not missing_cases:
            raise ValueError("partial L&E executable coverage requires missing cases")
        if self.status == "labor_employment_executable_coverage_ready_for_review" and failed:
            raise ValueError("ready L&E executable coverage report cannot include failed checks")
        if self.status == "blocked_labor_employment_executable_coverage" and not failed:
            raise ValueError("blocked L&E executable coverage report requires failed checks")
        return self


LaborEmploymentBudgetFactResolutionState = Literal[
    "missing_critical_fact",
    "missing_noncritical_fact",
    "source_present_needs_confirmation",
    "source_present_unresolved_critical_driver",
    "source_present_unresolved_driver",
    "inventory_present_needs_confirmation",
    "unbound_fact_gap",
]


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
    fact_resolution_state: LaborEmploymentBudgetFactResolutionState
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
        if self.fact_resolution_state == "missing_critical_fact":
            if self.required_level != "critical":
                raise ValueError("missing critical fact state requires critical level")
            if not self.blocks_precise_budget:
                raise ValueError("missing critical fact must block precise budget")
        if self.fact_resolution_state == "missing_noncritical_fact":
            if self.required_level == "critical":
                raise ValueError("missing noncritical fact state cannot use critical level")
            if self.blocks_precise_budget:
                raise ValueError("missing noncritical fact cannot block precise budget")
        if self.fact_resolution_state == "source_present_needs_confirmation":
            if not (self.evidence_refs or self.source_inventory_refs):
                raise ValueError("source-present confirmation state requires source anchors")
            if self.blocks_precise_budget:
                raise ValueError("source-present confirmation state is review-only")
        if self.fact_resolution_state == "source_present_unresolved_critical_driver":
            if self.required_level != "critical":
                raise ValueError("unresolved critical driver state requires critical level")
            if not self.evidence_refs:
                raise ValueError("unresolved critical driver state requires evidence refs")
            if not self.blocks_precise_budget:
                raise ValueError("unresolved critical driver must block precise budget")
        if self.fact_resolution_state == "source_present_unresolved_driver":
            if not (self.evidence_refs or self.source_inventory_refs):
                raise ValueError("unresolved driver state requires source anchors")
            if self.blocks_precise_budget:
                raise ValueError("noncritical unresolved driver cannot block precise budget")
        if self.fact_resolution_state == "inventory_present_needs_confirmation":
            if not self.source_inventory_refs:
                raise ValueError("inventory-present state requires source inventory refs")
            if self.blocks_precise_budget:
                raise ValueError("inventory-present state is review-only")
        if self.fact_resolution_state == "unbound_fact_gap" and (
            self.evidence_refs or self.source_inventory_refs or self.matched_exception_labels
        ):
            raise ValueError("unbound fact gap cannot carry anchors")
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
    missing_critical_fact_count: int = Field(ge=0)
    source_present_confirmation_fact_count: int = Field(ge=0)
    source_present_unresolved_critical_driver_count: int = Field(ge=0)
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
        if self.missing_critical_fact_count != sum(
            1
            for binding in self.fact_bindings
            if binding.fact_resolution_state == "missing_critical_fact"
        ):
            raise ValueError("executable L&E missing critical fact count mismatch")
        if self.source_present_confirmation_fact_count != sum(
            1
            for binding in self.fact_bindings
            if binding.fact_resolution_state == "source_present_needs_confirmation"
        ):
            raise ValueError("executable L&E source-present confirmation count mismatch")
        if self.source_present_unresolved_critical_driver_count != sum(
            1
            for binding in self.fact_bindings
            if binding.fact_resolution_state == "source_present_unresolved_critical_driver"
        ):
            raise ValueError(
                "executable L&E source-present unresolved critical driver count mismatch"
            )
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
    missing_critical_fact_count: int = Field(ge=0)
    source_present_confirmation_fact_count: int = Field(ge=0)
    source_present_unresolved_critical_driver_count: int = Field(ge=0)
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
        if self.missing_critical_fact_count != sum(
            case.missing_critical_fact_count for case in self.cases
        ):
            raise ValueError("executable L&E missing critical fact aggregate count mismatch")
        if self.source_present_confirmation_fact_count != sum(
            case.source_present_confirmation_fact_count for case in self.cases
        ):
            raise ValueError("executable L&E source-present confirmation aggregate mismatch")
        if self.source_present_unresolved_critical_driver_count != sum(
            case.source_present_unresolved_critical_driver_count for case in self.cases
        ):
            raise ValueError(
                "executable L&E source-present unresolved critical driver aggregate mismatch"
            )
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


LaborEmploymentBudgetDriverDimension = Literal[
    "party_topology",
    "representation_posture",
    "claim_family",
    "administrative_exhaustion",
    "class_collective_scope",
    "forum_arbitration",
    "employment_timeline",
    "damages_exposure",
    "wage_hour_volume",
    "esi_discovery",
    "deposition_plan",
    "expert_vendor_needs",
    "policy_contract_documents",
    "carrier_guideline_rate_context",
]


class LaborEmploymentExecutableDriverBindingItem(StrictModel):
    driver_dimension: LaborEmploymentBudgetDriverDimension
    binding_state: Literal["source_bound_driver_candidate", "unbound_driver_candidate"]
    fact_ids: list[str]
    evidence_ref_count: int = Field(ge=0)
    exception_label_count: int = Field(ge=0)
    source_inventory_ref_count: int = Field(ge=0)
    critical_driver_block: bool = False
    critical_driver_review_only: bool = False
    missing_critical_fact_count: int = Field(default=0, ge=0)
    source_present_confirmation_fact_count: int = Field(default=0, ge=0)
    source_present_unresolved_critical_driver_count: int = Field(default=0, ge=0)
    matched_fact_ids: list[str]
    missing_fact_ids: list[str]
    notes: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True

    @model_validator(mode="after")
    def le_executable_driver_binding_item_counts_match(
        self,
    ) -> "LaborEmploymentExecutableDriverBindingItem":
        if self.binding_state == "source_bound_driver_candidate" and not self.matched_fact_ids:
            raise ValueError("source-bound driver candidate requires matched facts")
        if self.binding_state == "unbound_driver_candidate" and not self.missing_fact_ids:
            raise ValueError("unbound driver candidate requires missing facts")
        if sorted(set(self.matched_fact_ids + self.missing_fact_ids)) != sorted(set(self.fact_ids)):
            raise ValueError("driver binding fact coverage mismatch")
        if self.critical_driver_review_only and self.critical_driver_block:
            raise ValueError("driver binding cannot be both review-only and amount-blocking")
        if self.critical_driver_review_only and not self.source_present_confirmation_fact_count:
            raise ValueError("review-only critical driver requires source-present facts")
        return self


class LaborEmploymentExecutableDriverBindingCase(StrictModel):
    executable_fixture_id: str
    linked_pack_case_ids: list[str]
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    driver_binding_count: int = Field(ge=0)
    source_bound_driver_count: int = Field(ge=0)
    unbound_driver_count: int = Field(ge=0)
    critical_driver_block_count: int = Field(ge=0)
    critical_driver_review_only_count: int = Field(ge=0)
    budget_driver_dimensions: list[LaborEmploymentBudgetDriverDimension]
    driver_bindings: list[LaborEmploymentExecutableDriverBindingItem]
    failed_expectation_ids: list[str] = Field(default_factory=list)
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
    def le_executable_driver_binding_case_counts_match(
        self,
    ) -> "LaborEmploymentExecutableDriverBindingCase":
        unbound = [
            item
            for item in self.driver_bindings
            if item.binding_state == "unbound_driver_candidate"
        ]
        if self.driver_binding_count != len(self.driver_bindings):
            raise ValueError("executable L&E driver binding count mismatch")
        if self.source_bound_driver_count != sum(
            1
            for item in self.driver_bindings
            if item.binding_state == "source_bound_driver_candidate"
        ):
            raise ValueError("executable L&E source-bound driver count mismatch")
        if self.unbound_driver_count != len(unbound):
            raise ValueError("executable L&E unbound driver count mismatch")
        if self.critical_driver_block_count != sum(
            1 for item in self.driver_bindings if item.critical_driver_block
        ):
            raise ValueError("executable L&E critical driver block count mismatch")
        if self.critical_driver_review_only_count != sum(
            1 for item in self.driver_bindings if item.critical_driver_review_only
        ):
            raise ValueError("executable L&E critical driver review-only count mismatch")
        if self.status == "passed" and (self.failed_expectation_ids or unbound):
            raise ValueError("passed executable L&E driver binding case has failures")
        if self.status == "failed" and not (self.failed_expectation_ids or unbound):
            raise ValueError("failed executable L&E driver binding case requires failures")
        return self


class LaborEmploymentExecutableDriverBindingCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentExecutableDriverBindingReport(StrictModel):
    schema_version: str = "0.1"
    executable_driver_binding_report_id: str
    status: Literal[
        "labor_employment_executable_driver_bindings_ready_for_review",
        "blocked_by_labor_employment_executable_driver_bindings",
    ]
    executable_fixture_report_ref: str
    executable_fact_binding_report_ref: str
    pack_ref: str
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    driver_binding_count: int = Field(ge=0)
    source_bound_driver_count: int = Field(ge=0)
    unbound_driver_count: int = Field(ge=0)
    critical_driver_block_count: int = Field(ge=0)
    critical_driver_review_only_count: int = Field(ge=0)
    required_driver_dimensions: list[LaborEmploymentBudgetDriverDimension]
    covered_driver_dimensions: list[LaborEmploymentBudgetDriverDimension]
    missing_driver_dimensions: list[LaborEmploymentBudgetDriverDimension]
    cases: list[LaborEmploymentExecutableDriverBindingCase]
    checks: list[LaborEmploymentExecutableDriverBindingCheck]
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
    def le_executable_driver_binding_report_counts_match(
        self,
    ) -> "LaborEmploymentExecutableDriverBindingReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("executable L&E driver binding case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("executable L&E driver binding failed case count mismatch")
        if self.driver_binding_count != sum(case.driver_binding_count for case in self.cases):
            raise ValueError("executable L&E driver binding aggregate count mismatch")
        if self.source_bound_driver_count != sum(
            case.source_bound_driver_count for case in self.cases
        ):
            raise ValueError("executable L&E source-bound driver aggregate count mismatch")
        if self.unbound_driver_count != sum(case.unbound_driver_count for case in self.cases):
            raise ValueError("executable L&E unbound driver aggregate count mismatch")
        if self.critical_driver_block_count != sum(
            case.critical_driver_block_count for case in self.cases
        ):
            raise ValueError("executable L&E critical driver block aggregate count mismatch")
        if self.critical_driver_review_only_count != sum(
            case.critical_driver_review_only_count for case in self.cases
        ):
            raise ValueError("executable L&E critical driver review-only aggregate mismatch")
        if sorted(set(self.covered_driver_dimensions + self.missing_driver_dimensions)) != sorted(
            set(self.required_driver_dimensions)
        ):
            raise ValueError("executable L&E driver dimension coverage mismatch")
        if self.status == "labor_employment_executable_driver_bindings_ready_for_review" and (
            failed_cases or failed_checks or self.missing_driver_dimensions
        ):
            raise ValueError("ready executable L&E driver binding cannot include gaps")
        if self.status == "blocked_by_labor_employment_executable_driver_bindings" and not (
            failed_cases or failed_checks or self.missing_driver_dimensions
        ):
            raise ValueError("blocked executable L&E driver binding requires gaps")
        return self


LaborEmploymentExecutableDriverImpactAction = Literal[
    "block_amount_budget",
    "widen_budget_range",
    "add_scenario_fork",
    "require_rate_guideline_review",
    "hold_for_human_driver_review",
]

LaborEmploymentExecutableDriverPricingEffect = Literal[
    "amount_budget_blocked",
    "range_width_required",
    "scenario_set_required",
    "hours_or_rate_review_required",
    "human_review_required",
]

LaborEmploymentExecutableDriverAllowedBudgetOutput = Literal[
    "blocked_amount_budget",
    "range_or_hours_only_pending_review",
    "candidate_range_after_review_pending_human_review",
]


class LaborEmploymentExecutableDriverImpactItem(StrictModel):
    driver_dimension: LaborEmploymentBudgetDriverDimension
    impact_state: Literal[
        "source_bound_impact_candidate",
        "blocked_missing_impact_policy",
        "blocked_unbound_driver_candidate",
    ]
    source_binding_state: Literal["source_bound_driver_candidate", "unbound_driver_candidate"]
    source_bound: bool
    critical_driver_block: bool
    critical_driver_review_only: bool = False
    impact_actions: list[LaborEmploymentExecutableDriverImpactAction]
    pricing_effect: LaborEmploymentExecutableDriverPricingEffect
    range_widening_factor: float = Field(ge=1.0)
    scenario_fork_required: bool
    rate_guideline_review_required: bool
    human_review_required: Literal[True] = True
    matched_fact_ids: list[str]
    evidence_ref_count: int = Field(ge=0)
    exception_label_count: int = Field(ge=0)
    source_inventory_ref_count: int = Field(ge=0)
    policy_reason: str
    notes: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_executable_driver_impact_item_is_coherent(
        self,
    ) -> "LaborEmploymentExecutableDriverImpactItem":
        if self.impact_state == "source_bound_impact_candidate":
            if (
                self.source_binding_state != "source_bound_driver_candidate"
                or not self.source_bound
            ):
                raise ValueError("source-bound impact candidate requires source-bound driver")
            if not self.matched_fact_ids:
                raise ValueError("source-bound impact candidate requires matched facts")
        if self.impact_state != "source_bound_impact_candidate" and self.source_bound:
            raise ValueError("blocked impact candidates cannot be marked source-bound")
        if self.critical_driver_block:
            if "block_amount_budget" not in self.impact_actions:
                raise ValueError("critical driver block requires amount-budget block action")
            if self.pricing_effect != "amount_budget_blocked":
                raise ValueError("critical driver block requires amount-budget blocked effect")
        if self.critical_driver_review_only and self.critical_driver_block:
            raise ValueError("impact cannot be both review-only and amount-blocking")
        if (
            self.critical_driver_review_only
            and "hold_for_human_driver_review" not in self.impact_actions
        ):
            raise ValueError("review-only critical impact requires human review hold")
        if self.range_widening_factor > 1.0 and "widen_budget_range" not in self.impact_actions:
            raise ValueError("range widening factor requires widen_budget_range action")
        if self.scenario_fork_required and "add_scenario_fork" not in self.impact_actions:
            raise ValueError("scenario fork flag requires add_scenario_fork action")
        if (
            self.rate_guideline_review_required
            and "require_rate_guideline_review" not in self.impact_actions
        ):
            raise ValueError("rate review flag requires require_rate_guideline_review action")
        return self


class LaborEmploymentExecutableDriverImpactCase(StrictModel):
    executable_fixture_id: str
    linked_pack_case_ids: list[str]
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    allowed_budget_output: LaborEmploymentExecutableDriverAllowedBudgetOutput
    impact_item_count: int = Field(ge=0)
    source_bound_impact_count: int = Field(ge=0)
    block_amount_budget_impact_count: int = Field(ge=0)
    critical_review_only_impact_count: int = Field(ge=0)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    human_review_impact_count: int = Field(ge=0)
    max_range_widening_factor: float = Field(ge=1.0)
    impact_items: list[LaborEmploymentExecutableDriverImpactItem]
    failed_expectation_ids: list[str] = Field(default_factory=list)
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
    def le_executable_driver_impact_case_counts_match(
        self,
    ) -> "LaborEmploymentExecutableDriverImpactCase":
        if self.impact_item_count != len(self.impact_items):
            raise ValueError("executable L&E driver impact count mismatch")
        if self.source_bound_impact_count != sum(
            1 for item in self.impact_items if item.impact_state == "source_bound_impact_candidate"
        ):
            raise ValueError("executable L&E source-bound impact count mismatch")
        if self.block_amount_budget_impact_count != sum(
            1 for item in self.impact_items if "block_amount_budget" in item.impact_actions
        ):
            raise ValueError("executable L&E amount-budget block impact count mismatch")
        if self.critical_review_only_impact_count != sum(
            1 for item in self.impact_items if item.critical_driver_review_only
        ):
            raise ValueError("executable L&E critical review-only impact count mismatch")
        if self.range_widening_impact_count != sum(
            1 for item in self.impact_items if "widen_budget_range" in item.impact_actions
        ):
            raise ValueError("executable L&E range-widening impact count mismatch")
        if self.scenario_fork_impact_count != sum(
            1 for item in self.impact_items if item.scenario_fork_required
        ):
            raise ValueError("executable L&E scenario-fork impact count mismatch")
        if self.rate_guideline_review_impact_count != sum(
            1 for item in self.impact_items if item.rate_guideline_review_required
        ):
            raise ValueError("executable L&E rate-guideline impact count mismatch")
        if self.human_review_impact_count != sum(
            1 for item in self.impact_items if item.human_review_required
        ):
            raise ValueError("executable L&E human-review impact count mismatch")
        expected_max = max(
            [item.range_widening_factor for item in self.impact_items],
            default=1.0,
        )
        if self.max_range_widening_factor != expected_max:
            raise ValueError("executable L&E max range-widening factor mismatch")
        if self.status == "passed" and self.failed_expectation_ids:
            raise ValueError("passed executable L&E driver impact case has failures")
        if self.status == "failed" and not self.failed_expectation_ids:
            raise ValueError("failed executable L&E driver impact case requires failures")
        if (
            self.expected_budget_treatment == "block_amount_budget"
            and self.allowed_budget_output != "blocked_amount_budget"
        ):
            raise ValueError("blocked treatment must keep amount budget blocked")
        if (
            self.allowed_budget_output == "blocked_amount_budget"
            and self.block_amount_budget_impact_count == 0
        ):
            raise ValueError("blocked output requires at least one block impact")
        return self


class LaborEmploymentExecutableDriverImpactCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentExecutableDriverImpactReport(StrictModel):
    schema_version: str = "0.1"
    executable_driver_impact_report_id: str
    status: Literal[
        "labor_employment_executable_driver_impacts_ready_for_review",
        "blocked_by_labor_employment_executable_driver_impacts",
    ]
    executable_driver_binding_report_ref: str
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    impact_item_count: int = Field(ge=0)
    source_bound_impact_count: int = Field(ge=0)
    block_amount_budget_impact_count: int = Field(ge=0)
    critical_review_only_impact_count: int = Field(ge=0)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    human_review_impact_count: int = Field(ge=0)
    max_range_widening_factor: float = Field(ge=1.0)
    impact_policy_dimensions: list[LaborEmploymentBudgetDriverDimension]
    missing_impact_policy_dimensions: list[LaborEmploymentBudgetDriverDimension]
    cases: list[LaborEmploymentExecutableDriverImpactCase]
    checks: list[LaborEmploymentExecutableDriverImpactCheck]
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
    def le_executable_driver_impact_report_counts_match(
        self,
    ) -> "LaborEmploymentExecutableDriverImpactReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("executable L&E driver impact case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("executable L&E driver impact failed case count mismatch")
        if self.impact_item_count != sum(case.impact_item_count for case in self.cases):
            raise ValueError("executable L&E driver impact aggregate count mismatch")
        if self.source_bound_impact_count != sum(
            case.source_bound_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E source-bound impact aggregate count mismatch")
        if self.block_amount_budget_impact_count != sum(
            case.block_amount_budget_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E block impact aggregate count mismatch")
        if self.critical_review_only_impact_count != sum(
            case.critical_review_only_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E critical review-only impact aggregate mismatch")
        if self.range_widening_impact_count != sum(
            case.range_widening_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E range impact aggregate count mismatch")
        if self.scenario_fork_impact_count != sum(
            case.scenario_fork_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E scenario impact aggregate count mismatch")
        if self.rate_guideline_review_impact_count != sum(
            case.rate_guideline_review_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E rate-guideline impact aggregate count mismatch")
        if self.human_review_impact_count != sum(
            case.human_review_impact_count for case in self.cases
        ):
            raise ValueError("executable L&E human-review impact aggregate count mismatch")
        expected_max = max(
            [case.max_range_widening_factor for case in self.cases],
            default=1.0,
        )
        if self.max_range_widening_factor != expected_max:
            raise ValueError("executable L&E max range impact aggregate mismatch")
        if self.status == "labor_employment_executable_driver_impacts_ready_for_review" and (
            failed_cases or failed_checks or self.missing_impact_policy_dimensions
        ):
            raise ValueError("ready executable L&E driver impact cannot include blockers")
        if self.status == "blocked_by_labor_employment_executable_driver_impacts" and not (
            failed_cases or failed_checks or self.missing_impact_policy_dimensions
        ):
            raise ValueError("blocked executable L&E driver impact report requires blockers")
        return self


LaborEmploymentNonlinearTemplateId = Literal[
    "le-class-collective-defense",
    "le-paga-shaped-defense",
]

LaborEmploymentNonlinearTemplatePeriodDriver = Literal[
    "class_period_months",
    "paga_period_months",
]

LaborEmploymentNonlinearTemplateTierId = Literal["t0", "t1", "t2", "t3", "t4"]


class LaborEmploymentNonlinearTemplateTierBlock(StrictModel):
    tier_id: LaborEmploymentNonlinearTemplateTierId
    tier_label: str
    action: Literal["use_declared_work_block", "block_pending_staffing_plan"]
    blocker_id: str | None = None
    interpolation_allowed: bool = False
    human_review_required: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False


class LaborEmploymentNonlinearTemplateTask(StrictModel):
    task_id: str
    label: str
    tags: list[str] = Field(default_factory=list)
    driver_dimensions: list[LaborEmploymentBudgetDriverDimension] = Field(default_factory=list)
    period_drivers: list[LaborEmploymentNonlinearTemplatePeriodDriver] = Field(default_factory=list)
    data_scope_task: bool = False
    opt_in_sensitive: bool = False
    exposure_modeling_allowed: bool = False
    money_amount_allowed: bool = False
    requires_human_review: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False


class LaborEmploymentNonlinearTemplatePhase(StrictModel):
    phase_id: str
    label: str
    phase_order: int = Field(ge=1)
    tier_blocks: list[LaborEmploymentNonlinearTemplateTierBlock] = Field(default_factory=list)
    tasks: list[LaborEmploymentNonlinearTemplateTask]
    scenario_sensitive: bool = False
    settlement_administration_phase: bool = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_nonlinear_phase_has_unique_rows(self) -> "LaborEmploymentNonlinearTemplatePhase":
        if len({task.task_id for task in self.tasks}) != len(self.tasks):
            raise ValueError("L&E nonlinear template phase task ids must be unique")
        if len({block.tier_id for block in self.tier_blocks}) != len(self.tier_blocks):
            raise ValueError("L&E nonlinear template phase tier rows must be unique")
        return self


class LaborEmploymentNonlinearTemplateScenarioGate(StrictModel):
    gate_id: str
    driver_id: Literal[
        "certification_posture",
        "manageability_posture",
        "template_selection",
    ]
    allowed_scenarios: list[str]
    default_scenario: str | None = None
    all_scenarios_emitted: bool
    human_selection_required: Literal[True] = True
    blocks_auto_selection: bool = True
    blocker_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_nonlinear_scenario_gate_is_coherent(
        self,
    ) -> "LaborEmploymentNonlinearTemplateScenarioGate":
        if not self.allowed_scenarios:
            raise ValueError("L&E nonlinear scenario gate requires scenarios")
        if self.default_scenario and self.default_scenario not in self.allowed_scenarios:
            raise ValueError("L&E nonlinear scenario default must be an allowed scenario")
        return self


class LaborEmploymentNonlinearTemplateSpecItem(StrictModel):
    template_id: LaborEmploymentNonlinearTemplateId
    label: str
    posture: str
    math_model: Literal["tiered_contract_v0"]
    required_phase_ids: list[str]
    tiered_phase_ids: list[str]
    phases: list[LaborEmploymentNonlinearTemplatePhase]
    scenario_gates: list[LaborEmploymentNonlinearTemplateScenarioGate]
    hybrid_template_selection_requires_human: bool = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_nonlinear_template_rows_are_unique(
        self,
    ) -> "LaborEmploymentNonlinearTemplateSpecItem":
        if len({phase.phase_id for phase in self.phases}) != len(self.phases):
            raise ValueError("L&E nonlinear template phases must be unique")
        if len({gate.gate_id for gate in self.scenario_gates}) != len(self.scenario_gates):
            raise ValueError("L&E nonlinear template scenario gates must be unique")
        return self


class LaborEmploymentNonlinearTemplateSpec(StrictModel):
    schema_version: str = "0.1"
    template_spec_id: str
    data_origin: Literal["synthetic"]
    template_family: Literal["labor_employment_nonlinear_budget_template_contract"]
    methodology_ref: str
    required_template_ids: list[LaborEmploymentNonlinearTemplateId]
    required_blocker_ids: list[str]
    templates: list[LaborEmploymentNonlinearTemplateSpecItem]
    no_budget_amounts_declared: Literal[True] = True
    no_real_rates_declared: Literal[True] = True
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_external_writes_allowed: Literal[True] = True
    no_lake_or_sqlite_writes_allowed: Literal[True] = True
    no_budget_submission_allowed: Literal[True] = True
    no_matter_opening_allowed: Literal[True] = True
    calibration_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_nonlinear_template_spec_rows_are_unique(
        self,
    ) -> "LaborEmploymentNonlinearTemplateSpec":
        if len({template.template_id for template in self.templates}) != len(self.templates):
            raise ValueError("L&E nonlinear template ids must be unique")
        return self


class LaborEmploymentNonlinearTemplateAuditCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    template_id: LaborEmploymentNonlinearTemplateId | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentNonlinearTemplateAuditReport(StrictModel):
    schema_version: str = "0.1"
    nonlinear_template_audit_report_id: str
    status: Literal[
        "labor_employment_nonlinear_templates_ready_for_review",
        "blocked_by_labor_employment_nonlinear_template_contract",
    ]
    template_spec_ref: str
    template_spec_id: str
    template_spec_hash: str
    template_count: int = Field(ge=0)
    phase_count: int = Field(ge=0)
    task_count: int = Field(ge=0)
    tier_block_count: int = Field(ge=0)
    period_driver_task_count: int = Field(ge=0)
    t4_staffing_block_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    candidate_exception_lake_labels: list[str]
    checks: list[LaborEmploymentNonlinearTemplateAuditCheck]
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
    def le_nonlinear_template_audit_counts_match(
        self,
    ) -> "LaborEmploymentNonlinearTemplateAuditReport":
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.failed_check_count != len(failed_checks):
            raise ValueError("L&E nonlinear template failed check count mismatch")
        if self.status == "labor_employment_nonlinear_templates_ready_for_review" and failed_checks:
            raise ValueError("ready L&E nonlinear template report cannot include failed checks")
        if (
            self.status == "blocked_by_labor_employment_nonlinear_template_contract"
            and not failed_checks
        ):
            raise ValueError("blocked L&E nonlinear template report requires failed checks")
        required = {
            "human_labor_employment_template_selection_review",
            "no_amount_budget_from_nonlinear_template_contract",
            "budget_generator_must_consume_reviewed_template_contract_before_pricing",
            "no_lake_or_sqlite_write_from_nonlinear_template_audit",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("L&E nonlinear template report missing required next gates")
        return self


class LaborEmploymentDriverImpactReviewCaseSpec(StrictModel):
    executable_fixture_id: str
    review_outcome: Literal["approved_for_nonblocking_budget_gate_replay"]
    expected_allowed_budget_output: LaborEmploymentExecutableDriverAllowedBudgetOutput
    expected_block_amount_budget_impact_count: int = Field(ge=0)
    minimum_range_widening_impact_count: int = Field(ge=0)
    minimum_scenario_fork_impact_count: int = Field(ge=0)
    minimum_rate_guideline_review_impact_count: int = Field(ge=0)
    review_notes: list[str]
    evidence_refs: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True

    @model_validator(mode="after")
    def le_driver_impact_review_case_spec_is_reviewed(
        self,
    ) -> "LaborEmploymentDriverImpactReviewCaseSpec":
        if not self.review_notes:
            raise ValueError("driver impact review case requires review notes")
        if not self.evidence_refs:
            raise ValueError("driver impact review case requires evidence refs")
        if self.expected_block_amount_budget_impact_count != 0:
            raise ValueError("reviewed nonblocking budget-gate replay slice cannot expect blocks")
        return self


class LaborEmploymentDriverImpactReviewSpec(StrictModel):
    schema_version: str = "0.1"
    review_spec_id: str
    data_origin: Literal["synthetic"]
    review_scope: Literal["nonblocking_driver_impact_budget_gate_replay"]
    description: str
    source_driver_impact_report_expected_status: Literal[
        "labor_employment_executable_driver_impacts_ready_for_review"
    ]
    required_selected_case_count: int = Field(ge=1)
    cases: list[LaborEmploymentDriverImpactReviewCaseSpec]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_external_writes_allowed: Literal[True] = True
    no_lake_or_sqlite_writes_allowed: Literal[True] = True
    no_budget_submission_allowed: Literal[True] = True
    no_matter_opening_allowed: Literal[True] = True
    calibration_authorized: Literal[False] = False

    @model_validator(mode="after")
    def le_driver_impact_review_spec_counts_match(
        self,
    ) -> "LaborEmploymentDriverImpactReviewSpec":
        if self.required_selected_case_count != len(self.cases):
            raise ValueError("driver impact review required selected case count mismatch")
        if len({case.executable_fixture_id for case in self.cases}) != len(self.cases):
            raise ValueError("driver impact review cases must be unique")
        return self


class LaborEmploymentDriverImpactReviewCaseResult(StrictModel):
    executable_fixture_id: str
    status: Literal["passed", "failed"]
    review_outcome: Literal["approved_for_nonblocking_budget_gate_replay"]
    selected_for_reviewed_slice: bool
    allowed_budget_output: LaborEmploymentExecutableDriverAllowedBudgetOutput | None = None
    block_amount_budget_impact_count: int = Field(ge=0)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    failure_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_driver_impact_review_case_result_is_coherent(
        self,
    ) -> "LaborEmploymentDriverImpactReviewCaseResult":
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed driver impact review case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed driver impact review case requires failures")
        if self.selected_for_reviewed_slice and self.status != "passed":
            raise ValueError("only passed review cases can be selected")
        if self.selected_for_reviewed_slice and self.block_amount_budget_impact_count != 0:
            raise ValueError("reviewed nonblocking slice cannot select block impacts")
        return self


class LaborEmploymentDriverImpactReviewReport(StrictModel):
    schema_version: str = "0.1"
    driver_impact_review_report_id: str
    status: Literal[
        "labor_employment_driver_impact_review_ready_for_budget_gate_replay",
        "blocked_by_labor_employment_driver_impact_review",
    ]
    review_spec_ref: str
    source_driver_impact_report_ref: str
    source_driver_impact_report_id: str
    reviewed_slice_report_ref: str | None = None
    case_count: int = Field(ge=0)
    selected_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    block_amount_budget_impact_count: int = Field(ge=0)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    max_range_widening_factor: float = Field(ge=1.0)
    case_results: list[LaborEmploymentDriverImpactReviewCaseResult]
    checks: list[LaborEmploymentExecutableDriverImpactCheck]
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
    def le_driver_impact_review_report_counts_match(
        self,
    ) -> "LaborEmploymentDriverImpactReviewReport":
        failed_cases = [case for case in self.case_results if case.status == "failed"]
        selected_cases = [case for case in self.case_results if case.selected_for_reviewed_slice]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.case_results):
            raise ValueError("driver impact review case count mismatch")
        if self.selected_case_count != len(selected_cases):
            raise ValueError("driver impact review selected case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("driver impact review failed case count mismatch")
        if self.block_amount_budget_impact_count != sum(
            case.block_amount_budget_impact_count for case in selected_cases
        ):
            raise ValueError("driver impact review block impact count mismatch")
        if self.range_widening_impact_count != sum(
            case.range_widening_impact_count for case in selected_cases
        ):
            raise ValueError("driver impact review range impact count mismatch")
        if self.scenario_fork_impact_count != sum(
            case.scenario_fork_impact_count for case in selected_cases
        ):
            raise ValueError("driver impact review scenario impact count mismatch")
        if self.rate_guideline_review_impact_count != sum(
            case.rate_guideline_review_impact_count for case in selected_cases
        ):
            raise ValueError("driver impact review rate review impact count mismatch")
        if self.status == "labor_employment_driver_impact_review_ready_for_budget_gate_replay" and (
            failed_cases or failed_checks or self.reviewed_slice_report_ref is None
        ):
            raise ValueError("ready driver impact review requires passed cases and slice ref")
        if self.status == "blocked_by_labor_employment_driver_impact_review" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked driver impact review requires failures")
        if self.status == "blocked_by_labor_employment_driver_impact_review":
            if self.reviewed_slice_report_ref is not None:
                raise ValueError("blocked driver impact review cannot emit reviewed slice ref")
        return self


class LaborEmploymentBlockedDriverImpactFactReview(StrictModel):
    fact_id: str
    required_level: str
    binding_state: Literal[
        "source_bound_gap_candidate",
        "exception_bound_gap_candidate",
        "source_and_exception_bound_gap_candidate",
        "inventory_bound_gap_candidate",
        "unbound_gap_candidate",
    ]
    fact_resolution_state: LaborEmploymentBudgetFactResolutionState
    blocks_precise_budget: bool
    reason: str
    budget_effects: list[str]
    evidence_ref_count: int = Field(ge=0)
    source_inventory_ref_count: int = Field(ge=0)
    matched_source_signal_terms: list[str] = Field(default_factory=list)
    missing_source_signal_terms: list[str] = Field(default_factory=list)
    matched_exception_labels: list[str] = Field(default_factory=list)
    missing_exception_labels: list[str] = Field(default_factory=list)
    matched_source_ids: list[str] = Field(default_factory=list)
    missing_source_ids: list[str] = Field(default_factory=list)
    unblock_actions: list[str]
    candidate_exception_lake_labels: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True

    @model_validator(mode="after")
    def le_blocked_driver_impact_fact_review_is_actionable(
        self,
    ) -> "LaborEmploymentBlockedDriverImpactFactReview":
        if not self.blocks_precise_budget:
            raise ValueError("blocked driver impact fact review requires precise-budget blocker")
        if self.required_level != "critical":
            raise ValueError("blocked driver impact fact review requires critical fact")
        if not self.unblock_actions:
            raise ValueError("blocked driver impact fact review requires unblock actions")
        if not self.candidate_exception_lake_labels:
            raise ValueError("blocked driver impact fact review requires candidate lake labels")
        return self


class LaborEmploymentBlockedDriverImpactCaseReview(StrictModel):
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    allowed_budget_output: Literal["blocked_amount_budget"]
    block_reason: str
    block_amount_budget_impact_count: int = Field(ge=1)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    critical_driver_dimensions: list[LaborEmploymentBudgetDriverDimension]
    blocker_fact_count: int = Field(ge=1)
    blocker_facts: list[LaborEmploymentBlockedDriverImpactFactReview]
    candidate_exception_lake_labels: list[str]
    unblock_actions: list[str]
    next_review_gates: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    amount_budget_blocked: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_blocked_driver_impact_case_review_counts_match(
        self,
    ) -> "LaborEmploymentBlockedDriverImpactCaseReview":
        if self.blocker_fact_count != len(self.blocker_facts):
            raise ValueError("blocked driver impact blocker fact count mismatch")
        if not self.critical_driver_dimensions:
            raise ValueError("blocked driver impact case requires critical driver dimensions")
        if not self.candidate_exception_lake_labels:
            raise ValueError("blocked driver impact case requires candidate lake labels")
        if not self.unblock_actions:
            raise ValueError("blocked driver impact case requires unblock actions")
        return self


class LaborEmploymentBlockedDriverImpactReviewReport(StrictModel):
    schema_version: str = "0.1"
    blocked_driver_impact_review_report_id: str
    status: Literal[
        "labor_employment_blocked_driver_impacts_ready_for_review",
        "blocked_by_labor_employment_blocked_driver_impact_review",
    ]
    source_fact_binding_report_ref: str
    source_driver_binding_report_ref: str
    source_driver_impact_report_ref: str
    source_driver_impact_report_id: str
    case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    nonblocking_case_count: int = Field(ge=0)
    blocker_fact_count: int = Field(ge=0)
    block_amount_budget_impact_count: int = Field(ge=0)
    candidate_exception_lake_labels: list[str]
    case_reviews: list[LaborEmploymentBlockedDriverImpactCaseReview]
    checks: list[LaborEmploymentExecutableDriverImpactCheck]
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
    def le_blocked_driver_impact_review_report_counts_match(
        self,
    ) -> "LaborEmploymentBlockedDriverImpactReviewReport":
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != self.blocked_case_count + self.nonblocking_case_count:
            raise ValueError("blocked driver impact reviewed case partition mismatch")
        if self.blocked_case_count != len(self.case_reviews):
            raise ValueError("blocked driver impact case review count mismatch")
        if self.blocker_fact_count != sum(case.blocker_fact_count for case in self.case_reviews):
            raise ValueError("blocked driver impact blocker fact aggregate mismatch")
        if self.block_amount_budget_impact_count != sum(
            case.block_amount_budget_impact_count for case in self.case_reviews
        ):
            raise ValueError("blocked driver impact aggregate block count mismatch")
        labels = sorted(
            {label for case in self.case_reviews for label in case.candidate_exception_lake_labels}
        )
        if self.candidate_exception_lake_labels != labels:
            raise ValueError("blocked driver impact candidate lake labels mismatch")
        if (
            self.status == "labor_employment_blocked_driver_impacts_ready_for_review"
            and failed_checks
        ):
            raise ValueError("ready blocked driver impact review cannot include failed checks")
        if (
            self.status == "blocked_by_labor_employment_blocked_driver_impact_review"
            and not failed_checks
        ):
            raise ValueError("blocked driver impact review requires failed checks")
        return self


LaborEmploymentBudgetOutputExpectationState = Literal[
    "blocked_amount_budget_pending_driver_review",
    "range_or_hours_only_pending_human_review",
    "candidate_range_after_review_pending_human_review",
]


class LaborEmploymentBudgetOutputExpectationCase(StrictModel):
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_readiness_state: Literal[
        "blocked_missing_critical_facts",
        "range_only_pending_human_review",
        "candidate_ready_for_budget_review",
    ]
    expected_budget_treatment: Literal[
        "block_amount_budget",
        "hours_only_or_broad_range",
        "candidate_range_budget_after_review",
    ]
    source_allowed_budget_output: LaborEmploymentExecutableDriverAllowedBudgetOutput
    final_allowed_budget_output: LaborEmploymentExecutableDriverAllowedBudgetOutput
    expectation_state: LaborEmploymentBudgetOutputExpectationState
    selected_for_reviewed_nonblocking_slice: bool
    blocked_case_review_present: bool
    amount_budget_blocked: bool
    block_amount_budget_impact_count: int = Field(ge=0)
    critical_review_only_impact_count: int = Field(default=0, ge=0)
    range_widening_impact_count: int = Field(ge=0)
    scenario_fork_impact_count: int = Field(ge=0)
    rate_guideline_review_impact_count: int = Field(ge=0)
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
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
    def le_budget_output_expectation_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutputExpectationCase":
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed budget-output expectation case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed budget-output expectation case requires failures")
        if self.final_allowed_budget_output != self.source_allowed_budget_output:
            raise ValueError("budget-output expectation cannot change source output class")
        if not self.candidate_exception_lake_labels:
            raise ValueError("budget-output expectation case requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("budget-output expectation case requires next gates")
        if not self.evidence_refs:
            raise ValueError("budget-output expectation case requires evidence refs")
        if self.final_allowed_budget_output == "blocked_amount_budget":
            if self.expectation_state != "blocked_amount_budget_pending_driver_review":
                raise ValueError("blocked output requires blocked expectation state")
            if self.status == "passed" and (
                not self.amount_budget_blocked or not self.blocked_case_review_present
            ):
                raise ValueError("blocked output requires blocked-review evidence")
            if self.status == "passed" and self.selected_for_reviewed_nonblocking_slice:
                raise ValueError("blocked output cannot be selected for nonblocking replay")
            if self.status == "passed" and self.block_amount_budget_impact_count == 0:
                raise ValueError("blocked output requires amount-budget block impacts")
        else:
            if self.status == "passed" and (
                self.amount_budget_blocked or self.blocked_case_review_present
            ):
                raise ValueError("nonblocking output cannot carry blocked-review state")
            if self.status == "passed" and not self.selected_for_reviewed_nonblocking_slice:
                raise ValueError("nonblocking output requires reviewed slice selection")
            if self.status == "passed" and self.block_amount_budget_impact_count != 0:
                raise ValueError("nonblocking output cannot carry amount-budget block impacts")
            if (
                self.final_allowed_budget_output == "range_or_hours_only_pending_review"
                and self.expectation_state != "range_or_hours_only_pending_human_review"
            ):
                raise ValueError("range/hours-only output requires range expectation state")
            if (
                self.final_allowed_budget_output
                == "candidate_range_after_review_pending_human_review"
                and self.expectation_state != "candidate_range_after_review_pending_human_review"
            ):
                raise ValueError("candidate range output requires candidate range state")
        return self


class LaborEmploymentBudgetOutputExpectationReport(StrictModel):
    schema_version: str = "0.1"
    budget_output_expectation_report_id: str
    status: Literal[
        "labor_employment_budget_output_expectations_ready_for_review",
        "blocked_by_labor_employment_budget_output_expectations",
    ]
    source_driver_impact_report_ref: str
    source_driver_impact_report_id: str
    source_driver_impact_review_report_ref: str
    source_driver_impact_review_report_id: str
    source_blocked_driver_impact_review_report_ref: str
    source_blocked_driver_impact_review_report_id: str
    case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    blocked_amount_budget_case_count: int = Field(ge=0)
    range_or_hours_only_case_count: int = Field(ge=0)
    candidate_range_after_review_case_count: int = Field(ge=0)
    reviewed_nonblocking_case_count: int = Field(ge=0)
    blocked_review_case_count: int = Field(ge=0)
    candidate_exception_lake_labels: list[str]
    cases: list[LaborEmploymentBudgetOutputExpectationCase]
    checks: list[LaborEmploymentExecutableDriverImpactCheck]
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
    def le_budget_output_expectation_report_counts_match(
        self,
    ) -> "LaborEmploymentBudgetOutputExpectationReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("budget-output expectation case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("budget-output expectation failed case count mismatch")
        if self.blocked_amount_budget_case_count != sum(
            1 for case in self.cases if case.final_allowed_budget_output == "blocked_amount_budget"
        ):
            raise ValueError("budget-output expectation blocked case count mismatch")
        if self.range_or_hours_only_case_count != sum(
            1
            for case in self.cases
            if case.final_allowed_budget_output == "range_or_hours_only_pending_review"
        ):
            raise ValueError("budget-output expectation range/hours-only count mismatch")
        if self.candidate_range_after_review_case_count != sum(
            1
            for case in self.cases
            if case.final_allowed_budget_output
            == "candidate_range_after_review_pending_human_review"
        ):
            raise ValueError("budget-output expectation candidate range count mismatch")
        if self.reviewed_nonblocking_case_count != sum(
            1 for case in self.cases if case.selected_for_reviewed_nonblocking_slice
        ):
            raise ValueError("budget-output expectation reviewed nonblocking count mismatch")
        if self.blocked_review_case_count != sum(
            1 for case in self.cases if case.blocked_case_review_present
        ):
            raise ValueError("budget-output expectation blocked review count mismatch")
        labels = sorted(
            {label for case in self.cases for label in case.candidate_exception_lake_labels}
        )
        if self.candidate_exception_lake_labels != labels:
            raise ValueError("budget-output expectation candidate labels mismatch")
        if not self.required_next_gates:
            raise ValueError("budget-output expectation report requires next gates")
        if self.status == "labor_employment_budget_output_expectations_ready_for_review" and (
            failed_cases or failed_checks
        ):
            raise ValueError("ready budget-output expectation report cannot include failures")
        if self.status == "blocked_by_labor_employment_budget_output_expectations" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked budget-output expectation report requires failures")
        return self


class LaborEmploymentBudgetQAGateBucket(StrictModel):
    output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    case_count: int = Field(ge=0)
    executable_fixture_ids: list[str]

    @model_validator(mode="after")
    def le_budget_qa_bucket_count_matches_ids(self) -> "LaborEmploymentBudgetQAGateBucket":
        if self.case_count != len(self.executable_fixture_ids):
            raise ValueError("L&E budget QA bucket count mismatch")
        return self


class LaborEmploymentBudgetQAGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetQAGateReport(StrictModel):
    schema_version: str = "0.1"
    budget_qa_gate_report_id: str
    status: Literal[
        "labor_employment_budget_qa_gate_ready_for_review",
        "blocked_by_labor_employment_budget_qa_gate",
    ]
    source_budget_output_expectations_report_ref: str
    source_budget_output_expectations_report_id: str
    source_budget_output_expectations_report_status: str
    source_blocked_driver_impact_review_report_ref: str
    source_blocked_driver_impact_review_report_id: str
    source_blocked_driver_impact_review_report_status: str
    source_executable_coverage_report_ref: str
    source_executable_coverage_report_id: str
    source_executable_coverage_report_status: str
    source_executable_coverage_state: str
    case_count: int = Field(ge=0)
    executable_fixture_count: int = Field(ge=0)
    covered_pack_case_count: int = Field(ge=0)
    missing_executable_pack_case_count: int = Field(ge=0)
    blocked_amount_budget_case_count: int = Field(ge=0)
    range_or_hours_only_case_count: int = Field(ge=0)
    candidate_range_after_review_case_count: int = Field(ge=0)
    reviewed_nonblocking_case_count: int = Field(ge=0)
    blocked_review_case_count: int = Field(ge=0)
    required_family_count: int = Field(ge=0)
    covered_required_family_count: int = Field(ge=0)
    blocked_case_ids: list[str]
    range_or_hours_only_case_ids: list[str]
    candidate_range_after_review_case_ids: list[str]
    reviewed_nonblocking_case_ids: list[str]
    missing_blocked_review_case_ids: list[str] = Field(default_factory=list)
    missing_nonblocking_review_case_ids: list[str] = Field(default_factory=list)
    required_families_present: list[LaborEmploymentSyntheticFixtureFamily]
    required_families_missing: list[LaborEmploymentSyntheticFixtureFamily] = Field(
        default_factory=list
    )
    output_state_buckets: list[LaborEmploymentBudgetQAGateBucket]
    checks: list[LaborEmploymentBudgetQAGateCheck]
    candidate_exception_lake_labels: list[str]
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
    def le_budget_qa_gate_report_is_coherent(self) -> "LaborEmploymentBudgetQAGateReport":
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != (
            self.blocked_amount_budget_case_count
            + self.range_or_hours_only_case_count
            + self.candidate_range_after_review_case_count
        ):
            raise ValueError("L&E budget QA gate output partition mismatch")
        if self.blocked_amount_budget_case_count != len(self.blocked_case_ids):
            raise ValueError("L&E budget QA gate blocked case count mismatch")
        if self.range_or_hours_only_case_count != len(self.range_or_hours_only_case_ids):
            raise ValueError("L&E budget QA gate range/hours-only case count mismatch")
        if self.candidate_range_after_review_case_count != len(
            self.candidate_range_after_review_case_ids
        ):
            raise ValueError("L&E budget QA gate candidate range case count mismatch")
        if self.reviewed_nonblocking_case_count != len(self.reviewed_nonblocking_case_ids):
            raise ValueError("L&E budget QA gate reviewed nonblocking case count mismatch")
        if self.covered_required_family_count != len(self.required_families_present):
            raise ValueError("L&E budget QA gate required family present count mismatch")
        if self.required_family_count != (
            len(self.required_families_present) + len(self.required_families_missing)
        ):
            raise ValueError("L&E budget QA gate required family partition mismatch")
        if sum(bucket.case_count for bucket in self.output_state_buckets) != self.case_count:
            raise ValueError("L&E budget QA gate bucket aggregate mismatch")
        if not self.candidate_exception_lake_labels:
            raise ValueError("L&E budget QA gate requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("L&E budget QA gate requires next gates")
        if self.status == "labor_employment_budget_qa_gate_ready_for_review" and failed_checks:
            raise ValueError("ready L&E budget QA gate cannot include failed checks")
        if self.status == "blocked_by_labor_employment_budget_qa_gate" and not failed_checks:
            raise ValueError("blocked L&E budget QA gate requires failed checks")
        return self


LaborEmploymentBudgetLearningLoopType = Literal[
    "actuals_variance",
    "carrier_rejection_capture",
    "appeal_outcome",
    "reviewed_learning_gate",
    "blocked_budget_guard",
]


class LaborEmploymentBudgetLearningFixtureSpec(StrictModel):
    learning_fixture_id: str
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    source_fixture_refs: list[str]
    expected_candidate_exception_lake_labels: list[str]
    expected_learning_targets: list[str]
    notes: str
    data_origin: Literal["synthetic"] = "synthetic"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_learning_fixture_spec_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetLearningFixtureSpec":
        loop_types = set(self.learning_loop_types)
        if len(loop_types) != len(self.learning_loop_types):
            raise ValueError("L&E budget learning fixture loop types must be unique")
        if not self.source_fixture_refs:
            raise ValueError("L&E budget learning fixture requires source refs")
        if not self.expected_candidate_exception_lake_labels:
            raise ValueError("L&E budget learning fixture requires candidate labels")
        if not self.expected_learning_targets:
            raise ValueError("L&E budget learning fixture requires learning targets")
        if self.expected_budget_output_state == "blocked_amount_budget":
            if loop_types != {"blocked_budget_guard"}:
                raise ValueError(
                    "blocked L&E budget learning fixture can only exercise blocked budget guard"
                )
        else:
            if "blocked_budget_guard" in loop_types:
                raise ValueError("nonblocking L&E budget learning fixture cannot use blocked guard")
            if "reviewed_learning_gate" not in loop_types:
                raise ValueError(
                    "nonblocking L&E budget learning fixture requires reviewed learning gate"
                )
            if "appeal_outcome" in loop_types and "carrier_rejection_capture" not in loop_types:
                raise ValueError(
                    "appeal outcome fixture requires carrier rejection capture coverage"
                )
        return self


class LaborEmploymentBudgetLearningFixtureManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    status: Literal["candidate_labor_employment_budget_learning_fixture_manifest"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    source_budget_qa_gate_ref: str
    required_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    required_budget_output_states: list[LaborEmploymentExecutableDriverAllowedBudgetOutput]
    fixtures: list[LaborEmploymentBudgetLearningFixtureSpec]
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
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_learning_manifest_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetLearningFixtureManifest":
        fixture_ids = [fixture.learning_fixture_id for fixture in self.fixtures]
        executable_ids = [fixture.executable_fixture_id for fixture in self.fixtures]
        if not self.fixtures:
            raise ValueError("L&E budget learning manifest requires fixtures")
        if len(set(fixture_ids)) != len(fixture_ids):
            raise ValueError("L&E budget learning fixture IDs must be unique")
        if len(set(executable_ids)) != len(executable_ids):
            raise ValueError("L&E budget learning executable fixture IDs must be unique")
        if not self.required_learning_loop_types:
            raise ValueError("L&E budget learning manifest requires loop types")
        if not self.required_budget_output_states:
            raise ValueError("L&E budget learning manifest requires output states")
        return self


class LaborEmploymentBudgetLearningFixtureCase(StrictModel):
    learning_fixture_id: str
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    observed_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput | None = None
    learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    expected_candidate_exception_lake_labels: list[str]
    expected_learning_targets: list[str]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_learning_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetLearningFixtureCase":
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed L&E budget learning case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed L&E budget learning case requires failures")
        if not self.learning_loop_types:
            raise ValueError("L&E budget learning case requires loop types")
        if not self.expected_candidate_exception_lake_labels:
            raise ValueError("L&E budget learning case requires candidate labels")
        if not self.expected_learning_targets:
            raise ValueError("L&E budget learning case requires learning targets")
        if not self.evidence_refs:
            raise ValueError("L&E budget learning case requires evidence refs")
        if (
            self.status == "passed"
            and self.observed_budget_output_state != self.expected_budget_output_state
        ):
            raise ValueError("passed L&E budget learning case output state mismatch")
        return self


class LaborEmploymentBudgetLearningFixtureCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetLearningFixtureReport(StrictModel):
    schema_version: str = "0.1"
    budget_learning_fixture_report_id: str
    status: Literal[
        "labor_employment_budget_learning_fixtures_ready_for_review",
        "blocked_by_labor_employment_budget_learning_fixtures",
    ]
    source_manifest_ref: str
    source_manifest_id: str
    source_budget_qa_gate_report_ref: str
    source_budget_qa_gate_report_id: str
    source_budget_qa_gate_report_status: str
    fixture_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    required_family_count: int = Field(ge=0)
    covered_required_family_count: int = Field(ge=0)
    missing_required_families: list[LaborEmploymentSyntheticFixtureFamily]
    covered_budget_output_states: list[LaborEmploymentExecutableDriverAllowedBudgetOutput]
    missing_budget_output_states: list[LaborEmploymentExecutableDriverAllowedBudgetOutput]
    covered_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    blocked_budget_guard_fixture_count: int = Field(ge=0)
    actuals_variance_fixture_count: int = Field(ge=0)
    carrier_rejection_fixture_count: int = Field(ge=0)
    appeal_outcome_fixture_count: int = Field(ge=0)
    reviewed_learning_gate_fixture_count: int = Field(ge=0)
    cases: list[LaborEmploymentBudgetLearningFixtureCase]
    checks: list[LaborEmploymentBudgetLearningFixtureCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_learning_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetLearningFixtureReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.fixture_count != len(self.cases):
            raise ValueError("L&E budget learning fixture count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("L&E budget learning failed case count mismatch")
        if self.covered_required_family_count != (
            self.required_family_count - len(self.missing_required_families)
        ):
            raise ValueError("L&E budget learning family coverage count mismatch")
        loop_counts = {
            "blocked_budget_guard": self.blocked_budget_guard_fixture_count,
            "actuals_variance": self.actuals_variance_fixture_count,
            "carrier_rejection_capture": self.carrier_rejection_fixture_count,
            "appeal_outcome": self.appeal_outcome_fixture_count,
            "reviewed_learning_gate": self.reviewed_learning_gate_fixture_count,
        }
        for loop_type, count in loop_counts.items():
            actual = sum(1 for case in self.cases if loop_type in case.learning_loop_types)
            if count != actual:
                raise ValueError(f"L&E budget learning {loop_type} count mismatch")
        if not self.candidate_exception_lake_labels:
            raise ValueError("L&E budget learning report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("L&E budget learning report requires next gates")
        if not self.red_team_notes:
            raise ValueError("L&E budget learning report requires red team notes")
        if self.status == "labor_employment_budget_learning_fixtures_ready_for_review" and (
            failed_cases or failed_checks
        ):
            raise ValueError("ready L&E budget learning report cannot include failures")
        if self.status == "blocked_by_labor_employment_budget_learning_fixtures" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked L&E budget learning report requires failures")
        return self


class LaborEmploymentBudgetOutcomeReplaySeedSpec(StrictModel):
    outcome_seed_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    seeded_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    replay_seed_refs_by_loop: dict[LaborEmploymentBudgetLearningLoopType, list[str]]
    expected_replay_artifacts_by_loop: dict[LaborEmploymentBudgetLearningLoopType, list[str]]
    candidate_exception_lake_labels_by_loop: dict[LaborEmploymentBudgetLearningLoopType, list[str]]
    replay_assertions: list[str]
    notes: str
    data_origin: Literal["synthetic"] = "synthetic"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_outcome_seed_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplaySeedSpec":
        loops = set(self.seeded_learning_loop_types)
        if len(loops) != len(self.seeded_learning_loop_types):
            raise ValueError("L&E budget outcome seed loop types must be unique")
        if not loops:
            raise ValueError("L&E budget outcome seed requires loop types")
        for loop_type in loops:
            if not self.replay_seed_refs_by_loop.get(loop_type):
                raise ValueError(f"L&E budget outcome seed missing refs for {loop_type}")
            if not self.expected_replay_artifacts_by_loop.get(loop_type):
                raise ValueError(f"L&E budget outcome seed missing artifacts for {loop_type}")
            if not self.candidate_exception_lake_labels_by_loop.get(loop_type):
                raise ValueError(f"L&E budget outcome seed missing labels for {loop_type}")
        for loop_type in self.replay_seed_refs_by_loop:
            if loop_type not in loops:
                raise ValueError(f"L&E budget outcome seed has unclaimed refs for {loop_type}")
        for loop_type in self.expected_replay_artifacts_by_loop:
            if loop_type not in loops:
                raise ValueError(f"L&E budget outcome seed has unclaimed artifacts for {loop_type}")
        for loop_type in self.candidate_exception_lake_labels_by_loop:
            if loop_type not in loops:
                raise ValueError(f"L&E budget outcome seed has unclaimed labels for {loop_type}")
        if not self.replay_assertions:
            raise ValueError("L&E budget outcome seed requires replay assertions")
        if self.expected_budget_output_state == "blocked_amount_budget":
            if loops != {"blocked_budget_guard"}:
                raise ValueError("blocked L&E outcome seed can only exercise blocked guard")
        elif "blocked_budget_guard" in loops:
            raise ValueError("nonblocking L&E outcome seed cannot exercise blocked guard")
        return self


class LaborEmploymentBudgetOutcomeReplaySeedManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    status: Literal["candidate_labor_employment_budget_outcome_replay_seed_manifest"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    source_budget_learning_fixture_manifest_ref: str
    seeds: list[LaborEmploymentBudgetOutcomeReplaySeedSpec]
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
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_outcome_seed_manifest_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplaySeedManifest":
        seed_ids = [seed.outcome_seed_id for seed in self.seeds]
        fixture_ids = [seed.learning_fixture_id for seed in self.seeds]
        if not self.seeds:
            raise ValueError("L&E budget outcome seed manifest requires seeds")
        if len(set(seed_ids)) != len(seed_ids):
            raise ValueError("L&E budget outcome seed IDs must be unique")
        if len(set(fixture_ids)) != len(fixture_ids):
            raise ValueError("L&E budget outcome seeds must be one per learning fixture")
        return self


class LaborEmploymentBudgetOutcomeReplayReadinessCase(StrictModel):
    learning_fixture_id: str
    executable_fixture_id: str
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    observed_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput | None = None
    outcome_seed_id: str | None = None
    required_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    seeded_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    extra_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_replay_seed_ref_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_expected_artifact_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_candidate_label_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    unresolved_source_refs: list[str]
    expected_replay_artifacts: list[str]
    candidate_exception_lake_labels: list[str]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_outcome_replay_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayReadinessCase":
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed L&E budget outcome replay case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed L&E budget outcome replay case requires failures")
        if not self.required_learning_loop_types:
            raise ValueError("L&E budget outcome replay case requires loop types")
        if self.status == "passed" and (
            self.missing_learning_loop_types
            or self.extra_learning_loop_types
            or self.missing_replay_seed_ref_loop_types
            or self.missing_expected_artifact_loop_types
            or self.missing_candidate_label_loop_types
            or self.unresolved_source_refs
        ):
            raise ValueError("passed L&E budget outcome replay case cannot carry gaps")
        if not self.evidence_refs:
            raise ValueError("L&E budget outcome replay case requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayReadinessCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetOutcomeReplayReadinessReport(StrictModel):
    schema_version: str = "0.1"
    outcome_replay_readiness_report_id: str
    status: Literal[
        "labor_employment_budget_outcome_replay_ready_for_review",
        "blocked_by_labor_employment_budget_outcome_replay",
    ]
    source_seed_manifest_ref: str
    source_seed_manifest_id: str
    source_learning_fixture_report_ref: str
    source_learning_fixture_report_id: str
    source_learning_fixture_report_status: str
    fixture_count: int = Field(ge=0)
    seed_spec_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    loop_requirement_count: int = Field(ge=0)
    seeded_loop_requirement_count: int = Field(ge=0)
    missing_loop_requirement_count: int = Field(ge=0)
    unresolved_source_ref_count: int = Field(ge=0)
    expected_replay_artifact_count: int = Field(ge=0)
    covered_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    cases: list[LaborEmploymentBudgetOutcomeReplayReadinessCase]
    checks: list[LaborEmploymentBudgetOutcomeReplayReadinessCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_outcome_replay_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayReadinessReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.fixture_count != len(self.cases):
            raise ValueError("L&E budget outcome replay fixture count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("L&E budget outcome replay failed case count mismatch")
        if self.seeded_loop_requirement_count + self.missing_loop_requirement_count != (
            self.loop_requirement_count
        ):
            raise ValueError("L&E budget outcome replay loop requirement count mismatch")
        unresolved = sum(len(case.unresolved_source_refs) for case in self.cases)
        if self.unresolved_source_ref_count != unresolved:
            raise ValueError("L&E budget outcome replay unresolved source count mismatch")
        artifact_count = len(
            {artifact for case in self.cases for artifact in case.expected_replay_artifacts}
        )
        if self.expected_replay_artifact_count != artifact_count:
            raise ValueError("L&E budget outcome replay artifact count mismatch")
        if not self.candidate_exception_lake_labels:
            raise ValueError("L&E budget outcome replay report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("L&E budget outcome replay report requires next gates")
        if not self.red_team_notes:
            raise ValueError("L&E budget outcome replay report requires red team notes")
        if self.status == "labor_employment_budget_outcome_replay_ready_for_review" and (
            failed_cases or failed_checks
        ):
            raise ValueError("ready L&E budget outcome replay report cannot include failures")
        if self.status == "blocked_by_labor_employment_budget_outcome_replay" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked L&E budget outcome replay report requires failures")
        return self


class LaborEmploymentBudgetOutcomeReplayExecutionArtifact(StrictModel):
    loop_type: LaborEmploymentBudgetLearningLoopType
    expected_artifact_name: str
    artifact_slot_ref: str
    artifact_slot_status: Literal["materialized_candidate_slot", "blocked_not_materialized"]
    evidence_refs: list[str]
    runtime_artifact_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_outcome_replay_artifact_slot_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayExecutionArtifact":
        if not self.expected_artifact_name:
            raise ValueError("L&E outcome replay execution artifact requires expected name")
        if self.artifact_slot_status == "materialized_candidate_slot" and not (
            self.artifact_slot_ref
        ):
            raise ValueError("materialized L&E outcome replay artifact slot requires ref")
        if not self.evidence_refs:
            raise ValueError("L&E outcome replay execution artifact requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayExecutionCase(StrictModel):
    execution_case_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    outcome_seed_id: str | None = None
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    replay_case_dir: str
    required_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    materialized_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    blocked_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    expected_artifact_slot_count: int = Field(ge=0)
    materialized_artifact_slot_count: int = Field(ge=0)
    artifact_slots: list[LaborEmploymentBudgetOutcomeReplayExecutionArtifact]
    candidate_exception_lake_labels: list[str]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    runtime_artifacts_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_outcome_replay_execution_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayExecutionCase":
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed L&E outcome replay execution case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed L&E outcome replay execution case requires failures")
        if self.expected_artifact_slot_count != len(self.artifact_slots):
            raise ValueError("L&E outcome replay execution artifact slot count mismatch")
        materialized = [
            slot
            for slot in self.artifact_slots
            if slot.artifact_slot_status == "materialized_candidate_slot"
        ]
        if self.materialized_artifact_slot_count != len(materialized):
            raise ValueError("L&E outcome replay execution materialized slot count mismatch")
        if self.status == "passed" and self.materialized_artifact_slot_count != (
            self.expected_artifact_slot_count
        ):
            raise ValueError("passed L&E outcome replay execution case requires all slots")
        if not self.required_learning_loop_types:
            raise ValueError("L&E outcome replay execution case requires loop types")
        if not self.evidence_refs:
            raise ValueError("L&E outcome replay execution case requires evidence refs")
        if self.expected_budget_output_state == "blocked_amount_budget":
            if set(self.required_learning_loop_types) != {"blocked_budget_guard"}:
                raise ValueError("blocked execution case can only materialize guard loop")
        elif "blocked_budget_guard" in set(self.required_learning_loop_types):
            raise ValueError("nonblocked execution case cannot materialize guard loop")
        return self


class LaborEmploymentBudgetOutcomeReplayExecutionCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetOutcomeReplayExecutionReport(StrictModel):
    schema_version: str = "0.1"
    outcome_replay_execution_report_id: str
    status: Literal[
        "labor_employment_budget_outcome_replay_execution_ready_for_review",
        "blocked_by_labor_employment_budget_outcome_replay_execution",
    ]
    source_seed_manifest_ref: str
    source_seed_manifest_id: str
    source_readiness_report_ref: str
    source_readiness_report_id: str
    source_readiness_report_status: str
    fixture_count: int = Field(ge=0)
    materialized_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    expected_artifact_slot_count: int = Field(ge=0)
    materialized_artifact_slot_count: int = Field(ge=0)
    runtime_artifact_count: int = Field(ge=0)
    covered_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    missing_learning_loop_types: list[LaborEmploymentBudgetLearningLoopType]
    cases: list[LaborEmploymentBudgetOutcomeReplayExecutionCase]
    checks: list[LaborEmploymentBudgetOutcomeReplayExecutionCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    runtime_artifacts_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_outcome_replay_execution_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayExecutionReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        materialized_cases = [case for case in self.cases if case.status == "passed"]
        if self.fixture_count != len(self.cases):
            raise ValueError("L&E outcome replay execution fixture count mismatch")
        if self.materialized_case_count != len(materialized_cases):
            raise ValueError("L&E outcome replay execution materialized case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("L&E outcome replay execution failed case count mismatch")
        expected_slots = sum(case.expected_artifact_slot_count for case in self.cases)
        if self.expected_artifact_slot_count != expected_slots:
            raise ValueError("L&E outcome replay execution expected slot count mismatch")
        materialized_slots = sum(case.materialized_artifact_slot_count for case in self.cases)
        if self.materialized_artifact_slot_count != materialized_slots:
            raise ValueError("L&E outcome replay execution materialized slot count mismatch")
        if self.runtime_artifact_count != 0 or self.runtime_artifacts_created is not False:
            raise ValueError("L&E outcome replay execution cannot create runtime artifacts")
        if not self.candidate_exception_lake_labels:
            raise ValueError("L&E outcome replay execution report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("L&E outcome replay execution report requires next gates")
        if not self.red_team_notes:
            raise ValueError("L&E outcome replay execution report requires red team notes")
        if self.status == "labor_employment_budget_outcome_replay_execution_ready_for_review" and (
            failed_cases or failed_checks
        ):
            raise ValueError("ready L&E outcome replay execution report cannot include failures")
        if self.status == "blocked_by_labor_employment_budget_outcome_replay_execution" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked L&E outcome replay execution report requires failures")
        return self


class LaborEmploymentBudgetOutcomeReplayBuilderContract(StrictModel):
    artifact_name: str
    loop_type: LaborEmploymentBudgetLearningLoopType
    builder_module: str
    builder_function: str
    emitted_output_filenames: list[str]
    required_input_artifacts: list[str]
    intermediate_artifacts: list[str] = Field(default_factory=list)
    side_effect_boundary: Literal["local_candidate_files_only"] = "local_candidate_files_only"
    authority_owner: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    execution_owner: Literal["LawFirm-os-orchestrator"] = "LawFirm-os-orchestrator"
    creates_runtime_artifact: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_builder_contract_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayBuilderContract":
        if self.artifact_name not in self.emitted_output_filenames:
            raise ValueError("builder contract must emit the artifact it binds")
        if not self.builder_module or not self.builder_function:
            raise ValueError("builder contract requires module and function")
        if not self.required_input_artifacts:
            raise ValueError("builder contract requires explicit input artifacts")
        return self


class LaborEmploymentBudgetOutcomeReplayBuilderBinding(StrictModel):
    binding_id: str
    execution_case_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    outcome_seed_id: str | None = None
    loop_type: LaborEmploymentBudgetLearningLoopType
    expected_artifact_name: str
    artifact_slot_ref: str
    artifact_slot_status: Literal["materialized_candidate_slot", "blocked_not_materialized"]
    binding_status: Literal[
        "bound_to_existing_builder",
        "blocked_unknown_artifact",
        "blocked_slot_not_materialized",
    ]
    builder_module: str | None = None
    builder_function: str | None = None
    emitted_output_filenames: list[str] = Field(default_factory=list)
    required_input_artifacts: list[str] = Field(default_factory=list)
    intermediate_artifacts: list[str] = Field(default_factory=list)
    missing_case_prerequisite_artifacts: list[str] = Field(default_factory=list)
    replay_input_gap_ids: list[str] = Field(default_factory=list)
    side_effect_boundary: str | None = None
    binding_notes: list[str]
    evidence_refs: list[str]
    runtime_artifact_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_builder_binding_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayBuilderBinding":
        if self.binding_status == "bound_to_existing_builder":
            if not self.builder_module or not self.builder_function:
                raise ValueError("bound replay slot requires builder module/function")
            if self.expected_artifact_name not in self.emitted_output_filenames:
                raise ValueError("bound replay slot builder does not emit expected artifact")
        if self.binding_status != "bound_to_existing_builder" and (
            self.builder_module or self.builder_function
        ):
            raise ValueError("blocked replay slot cannot claim a builder binding")
        if not self.binding_notes:
            raise ValueError("replay builder binding requires notes")
        if not self.evidence_refs:
            raise ValueError("replay builder binding requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayBuilderBindingCase(StrictModel):
    binding_case_id: str
    execution_case_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    outcome_seed_id: str | None = None
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["passed", "failed"]
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    slot_count: int = Field(ge=0)
    bound_slot_count: int = Field(ge=0)
    unknown_artifact_count: int = Field(ge=0)
    blocked_slot_count: int = Field(ge=0)
    replay_input_gap_count: int = Field(ge=0)
    missing_case_prerequisite_count: int = Field(ge=0)
    bindings: list[LaborEmploymentBudgetOutcomeReplayBuilderBinding]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_builder_binding_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayBuilderBindingCase":
        if self.slot_count != len(self.bindings):
            raise ValueError("builder binding case slot count mismatch")
        bound = [
            binding
            for binding in self.bindings
            if binding.binding_status == "bound_to_existing_builder"
        ]
        unknown = [
            binding
            for binding in self.bindings
            if binding.binding_status == "blocked_unknown_artifact"
        ]
        blocked = [
            binding
            for binding in self.bindings
            if binding.binding_status == "blocked_slot_not_materialized"
        ]
        gaps = sum(len(binding.replay_input_gap_ids) for binding in self.bindings)
        missing = sum(len(binding.missing_case_prerequisite_artifacts) for binding in self.bindings)
        if self.bound_slot_count != len(bound):
            raise ValueError("builder binding case bound slot count mismatch")
        if self.unknown_artifact_count != len(unknown):
            raise ValueError("builder binding case unknown artifact count mismatch")
        if self.blocked_slot_count != len(blocked):
            raise ValueError("builder binding case blocked slot count mismatch")
        if self.replay_input_gap_count != gaps:
            raise ValueError("builder binding case input gap count mismatch")
        if self.missing_case_prerequisite_count != missing:
            raise ValueError("builder binding case prerequisite gap count mismatch")
        if self.status == "passed" and self.failure_ids:
            raise ValueError("passed builder binding case cannot carry failures")
        if self.status == "failed" and not self.failure_ids:
            raise ValueError("failed builder binding case requires failures")
        if not self.evidence_refs:
            raise ValueError("builder binding case requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetOutcomeReplayBuilderBindingReport(StrictModel):
    schema_version: str = "0.1"
    builder_binding_report_id: str
    status: Literal[
        "labor_employment_budget_replay_builder_binding_ready_for_review",
        "blocked_by_labor_employment_budget_replay_builder_binding",
    ]
    source_execution_report_ref: str
    source_execution_report_id: str
    source_execution_report_status: str
    fixture_count: int = Field(ge=0)
    case_count: int = Field(ge=0)
    passed_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    slot_count: int = Field(ge=0)
    bound_slot_count: int = Field(ge=0)
    unknown_artifact_count: int = Field(ge=0)
    blocked_slot_count: int = Field(ge=0)
    replay_input_gap_count: int = Field(ge=0)
    missing_case_prerequisite_count: int = Field(ge=0)
    builder_contracts: list[LaborEmploymentBudgetOutcomeReplayBuilderContract]
    cases: list[LaborEmploymentBudgetOutcomeReplayBuilderBindingCase]
    checks: list[LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    runtime_artifacts_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_replay_builder_binding_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayBuilderBindingReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.fixture_count != self.case_count or self.case_count != len(self.cases):
            raise ValueError("builder binding report case count mismatch")
        if self.passed_case_count != len([case for case in self.cases if case.status == "passed"]):
            raise ValueError("builder binding report passed case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("builder binding report failed case count mismatch")
        if self.slot_count != sum(case.slot_count for case in self.cases):
            raise ValueError("builder binding report slot count mismatch")
        if self.bound_slot_count != sum(case.bound_slot_count for case in self.cases):
            raise ValueError("builder binding report bound slot count mismatch")
        if self.unknown_artifact_count != sum(case.unknown_artifact_count for case in self.cases):
            raise ValueError("builder binding report unknown artifact count mismatch")
        if self.blocked_slot_count != sum(case.blocked_slot_count for case in self.cases):
            raise ValueError("builder binding report blocked slot count mismatch")
        if self.replay_input_gap_count != sum(case.replay_input_gap_count for case in self.cases):
            raise ValueError("builder binding report input gap count mismatch")
        if self.missing_case_prerequisite_count != sum(
            case.missing_case_prerequisite_count for case in self.cases
        ):
            raise ValueError("builder binding report prerequisite count mismatch")
        if not self.builder_contracts:
            raise ValueError("builder binding report requires builder contracts")
        if self.runtime_artifacts_created is not False:
            raise ValueError("builder binding report cannot create runtime artifacts")
        if not self.candidate_exception_lake_labels:
            raise ValueError("builder binding report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("builder binding report requires next gates")
        if not self.red_team_notes:
            raise ValueError("builder binding report requires red team notes")
        if self.status == "labor_employment_budget_replay_builder_binding_ready_for_review" and (
            failed_cases or failed_checks
        ):
            raise ValueError("ready builder binding report cannot include failures")
        if self.status == "blocked_by_labor_employment_budget_replay_builder_binding" and not (
            failed_cases or failed_checks
        ):
            raise ValueError("blocked builder binding report requires failures")
        return self


class LaborEmploymentBudgetOutcomeReplayInputPackEntry(StrictModel):
    entry_id: str
    learning_fixture_id: str
    loop_type: LaborEmploymentBudgetLearningLoopType
    required_input_artifact: str
    input_ref: str
    expected_artifact_name: str | None = None
    input_role: Literal["builder_input", "complement_report", "one_of_signal"]
    notes: str
    data_origin: Literal["synthetic"] = "synthetic"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_input_pack_entry_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayInputPackEntry":
        if not self.required_input_artifact.endswith((".json", ".jsonl")) and not (
            self.required_input_artifact.startswith("one_or_more_of:")
        ):
            raise ValueError("input-pack entry artifact must be a JSON artifact name")
        if self.input_ref.startswith(("http://", "https://", "app://")):
            raise ValueError("input-pack entry refs must be local file refs")
        if not self.notes:
            raise ValueError("input-pack entry requires notes")
        return self


class LaborEmploymentBudgetOutcomeReplayInputPackManifest(StrictModel):
    schema_version: str = "0.1"
    manifest_id: str
    status: Literal["candidate_labor_employment_budget_outcome_replay_input_pack_manifest"]
    practice_area: Literal["labor_employment"] = "labor_employment"
    source_builder_binding_report_ref: str
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_input_pack_manifest_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayInputPackManifest":
        if not self.entries:
            raise ValueError("L&E replay input-pack manifest requires entries")
        keys = [
            (
                entry.learning_fixture_id,
                entry.loop_type,
                entry.expected_artifact_name or "*",
                entry.required_input_artifact,
            )
            for entry in self.entries
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("L&E replay input-pack entries must be unique by slot/input")
        return self


class LaborEmploymentBudgetOutcomeReplayInputPackItem(StrictModel):
    input_check_id: str
    binding_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    outcome_seed_id: str | None = None
    loop_type: LaborEmploymentBudgetLearningLoopType
    expected_artifact_name: str
    required_input_artifact: str
    input_role: Literal["builder_input", "complement_report", "one_of_signal"]
    input_status: Literal["ready", "missing", "invalid"]
    input_ref: str | None = None
    selected_alternative_artifacts: list[str] = Field(default_factory=list)
    validation_model: str | None = None
    validation_message: str
    candidate_exception_lake_labels: list[str]
    evidence_refs: list[str]
    runtime_artifact_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_input_pack_item_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayInputPackItem":
        if self.input_status == "ready" and not self.input_ref:
            raise ValueError("ready input-pack item requires input ref")
        if self.input_status != "ready" and self.selected_alternative_artifacts:
            raise ValueError("non-ready input-pack item cannot select alternatives")
        if self.input_role == "one_of_signal" and self.input_status == "ready":
            if not self.selected_alternative_artifacts:
                raise ValueError("ready one-of input-pack item requires selected alternatives")
        if not self.validation_message:
            raise ValueError("input-pack item requires validation message")
        if not self.candidate_exception_lake_labels:
            raise ValueError("input-pack item requires candidate labels")
        if not self.evidence_refs:
            raise ValueError("input-pack item requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayInputPackCase(StrictModel):
    input_pack_case_id: str
    binding_case_id: str
    execution_case_id: str
    learning_fixture_id: str
    executable_fixture_id: str
    outcome_seed_id: str | None = None
    family: LaborEmploymentSyntheticFixtureFamily
    variant: LaborEmploymentSyntheticFixtureVariant
    status: Literal["ready", "partially_ready", "blocked"]
    expected_budget_output_state: LaborEmploymentExecutableDriverAllowedBudgetOutput
    required_input_count: int = Field(ge=0)
    ready_input_count: int = Field(ge=0)
    missing_input_count: int = Field(ge=0)
    invalid_input_count: int = Field(ge=0)
    one_of_signal_missing_count: int = Field(ge=0)
    items: list[LaborEmploymentBudgetOutcomeReplayInputPackItem]
    evidence_refs: list[str]
    failure_ids: list[str] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_input_pack_case_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayInputPackCase":
        if self.required_input_count != len(self.items):
            raise ValueError("input-pack case required input count mismatch")
        if self.ready_input_count != len(
            [item for item in self.items if item.input_status == "ready"]
        ):
            raise ValueError("input-pack case ready input count mismatch")
        if self.missing_input_count != len(
            [item for item in self.items if item.input_status == "missing"]
        ):
            raise ValueError("input-pack case missing input count mismatch")
        if self.invalid_input_count != len(
            [item for item in self.items if item.input_status == "invalid"]
        ):
            raise ValueError("input-pack case invalid input count mismatch")
        if self.one_of_signal_missing_count != len(
            [
                item
                for item in self.items
                if item.input_role == "one_of_signal" and item.input_status == "missing"
            ]
        ):
            raise ValueError("input-pack case one-of missing count mismatch")
        if self.status == "ready" and (
            self.missing_input_count or self.invalid_input_count or self.failure_ids
        ):
            raise ValueError("ready input-pack case cannot have failures")
        if self.status == "blocked" and not (self.invalid_input_count or self.failure_ids):
            raise ValueError("blocked input-pack case requires invalid inputs or failures")
        if self.status == "partially_ready" and not self.missing_input_count:
            raise ValueError("partially ready input-pack case requires missing inputs")
        if not self.evidence_refs:
            raise ValueError("input-pack case requires evidence refs")
        return self


class LaborEmploymentBudgetOutcomeReplayInputPackCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class LaborEmploymentBudgetOutcomeReplayInputPackReport(StrictModel):
    schema_version: str = "0.1"
    input_pack_report_id: str
    status: Literal[
        "labor_employment_budget_replay_input_pack_ready_for_review",
        "labor_employment_budget_replay_input_pack_partially_ready_for_review",
        "blocked_by_labor_employment_budget_replay_input_pack",
    ]
    source_builder_binding_report_ref: str
    source_builder_binding_report_id: str
    source_builder_binding_report_status: str
    source_input_pack_manifest_ref: str | None = None
    source_input_pack_manifest_id: str | None = None
    case_count: int = Field(ge=0)
    ready_case_count: int = Field(ge=0)
    partial_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    required_input_count: int = Field(ge=0)
    ready_input_count: int = Field(ge=0)
    missing_input_count: int = Field(ge=0)
    invalid_input_count: int = Field(ge=0)
    one_of_signal_missing_count: int = Field(ge=0)
    cases: list[LaborEmploymentBudgetOutcomeReplayInputPackCase]
    checks: list[LaborEmploymentBudgetOutcomeReplayInputPackCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    rust_transition_candidates: list[str]
    runtime_artifacts_created: Literal[False] = False
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_replay_input_pack_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayInputPackReport":
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.case_count != len(self.cases):
            raise ValueError("input-pack report case count mismatch")
        if self.ready_case_count != len([case for case in self.cases if case.status == "ready"]):
            raise ValueError("input-pack report ready case count mismatch")
        if self.partial_case_count != len(
            [case for case in self.cases if case.status == "partially_ready"]
        ):
            raise ValueError("input-pack report partial case count mismatch")
        if self.blocked_case_count != len(
            [case for case in self.cases if case.status == "blocked"]
        ):
            raise ValueError("input-pack report blocked case count mismatch")
        if self.required_input_count != sum(case.required_input_count for case in self.cases):
            raise ValueError("input-pack report required input count mismatch")
        if self.ready_input_count != sum(case.ready_input_count for case in self.cases):
            raise ValueError("input-pack report ready input count mismatch")
        if self.missing_input_count != sum(case.missing_input_count for case in self.cases):
            raise ValueError("input-pack report missing input count mismatch")
        if self.invalid_input_count != sum(case.invalid_input_count for case in self.cases):
            raise ValueError("input-pack report invalid input count mismatch")
        if self.one_of_signal_missing_count != sum(
            case.one_of_signal_missing_count for case in self.cases
        ):
            raise ValueError("input-pack report one-of missing count mismatch")
        if not self.candidate_exception_lake_labels:
            raise ValueError("input-pack report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("input-pack report requires next gates")
        if not self.red_team_notes:
            raise ValueError("input-pack report requires red team notes")
        if not self.rust_transition_candidates:
            raise ValueError("input-pack report requires Rust transition candidates")
        if self.status == "labor_employment_budget_replay_input_pack_ready_for_review" and (
            self.missing_input_count or self.invalid_input_count or failed_checks
        ):
            raise ValueError("ready input-pack report cannot include missing/invalid inputs")
        if (
            self.status == "labor_employment_budget_replay_input_pack_partially_ready_for_review"
            and not self.missing_input_count
        ):
            raise ValueError("partial input-pack report requires missing inputs")
        if self.status == "blocked_by_labor_employment_budget_replay_input_pack" and not (
            self.invalid_input_count or failed_checks
        ):
            raise ValueError("blocked input-pack report requires invalid inputs or checks")
        return self


class LaborEmploymentBudgetOutcomeReplayConfidenceStage(StrictModel):
    stage_id: Literal["readiness", "execution", "builder_binding", "input_pack"]
    label: str
    source_report_ref: str
    source_report_id: str
    source_report_status: str
    status: Literal["ready", "pending_inputs", "blocked"]
    counts: dict[str, int] = Field(default_factory=dict)
    blocker_count: int = Field(ge=0)
    blockers: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def le_budget_replay_confidence_stage_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayConfidenceStage":
        if not self.label:
            raise ValueError("replay confidence stage requires a label")
        if self.blocker_count != len(self.blockers):
            raise ValueError("replay confidence stage blocker count mismatch")
        if self.status == "ready" and self.blockers:
            raise ValueError("ready replay confidence stage cannot include blockers")
        if self.status in {"pending_inputs", "blocked"} and not self.blockers:
            raise ValueError("non-ready replay confidence stage requires blockers")
        if not self.evidence_refs:
            raise ValueError("replay confidence stage requires evidence refs")
        if any(value < 0 for value in self.counts.values()):
            raise ValueError("replay confidence stage counts must be non-negative")
        return self


class LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport(StrictModel):
    schema_version: str = "0.1"
    replay_confidence_status_report_id: str
    status: Literal[
        "labor_employment_budget_outcome_replay_confidence_ready_for_review",
        "labor_employment_budget_outcome_replay_confidence_pending_inputs",
        "blocked_by_labor_employment_budget_outcome_replay_confidence",
    ]
    source_readiness_report_ref: str
    source_readiness_report_id: str
    source_readiness_report_status: str
    source_execution_report_ref: str
    source_execution_report_id: str
    source_execution_report_status: str
    source_builder_binding_report_ref: str
    source_builder_binding_report_id: str
    source_builder_binding_report_status: str
    source_input_pack_report_ref: str
    source_input_pack_report_id: str
    source_input_pack_report_status: str
    fixture_count: int = Field(ge=0)
    stage_count: int = Field(ge=0)
    ready_stage_count: int = Field(ge=0)
    pending_stage_count: int = Field(ge=0)
    blocked_stage_count: int = Field(ge=0)
    readiness_failed_case_count: int = Field(ge=0)
    execution_failed_case_count: int = Field(ge=0)
    builder_replay_input_gap_count: int = Field(ge=0)
    builder_missing_case_prerequisite_count: int = Field(ge=0)
    input_pack_missing_input_count: int = Field(ge=0)
    input_pack_invalid_input_count: int = Field(ge=0)
    stages: list[LaborEmploymentBudgetOutcomeReplayConfidenceStage]
    top_blockers: list[str] = Field(default_factory=list)
    display_banner: dict[str, Any]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    red_team_notes: list[str]
    rust_transition_candidates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    synthetic_only: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_calibration: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def le_budget_replay_confidence_report_is_coherent(
        self,
    ) -> "LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport":
        if self.stage_count != len(self.stages):
            raise ValueError("replay confidence report stage count mismatch")
        if self.ready_stage_count != len(
            [stage for stage in self.stages if stage.status == "ready"]
        ):
            raise ValueError("replay confidence report ready stage count mismatch")
        if self.pending_stage_count != len(
            [stage for stage in self.stages if stage.status == "pending_inputs"]
        ):
            raise ValueError("replay confidence report pending stage count mismatch")
        if self.blocked_stage_count != len(
            [stage for stage in self.stages if stage.status == "blocked"]
        ):
            raise ValueError("replay confidence report blocked stage count mismatch")
        expected_blockers = [blocker for stage in self.stages for blocker in stage.blockers]
        if self.top_blockers != expected_blockers[: len(self.top_blockers)]:
            raise ValueError("replay confidence report top blockers must come from stages")
        if self.status == "labor_employment_budget_outcome_replay_confidence_ready_for_review":
            if self.pending_stage_count or self.blocked_stage_count:
                raise ValueError("ready replay confidence report cannot include non-ready stages")
        if self.status == "labor_employment_budget_outcome_replay_confidence_pending_inputs":
            if self.blocked_stage_count or not self.pending_stage_count:
                raise ValueError("pending replay confidence report requires pending stages only")
        if self.status == "blocked_by_labor_employment_budget_outcome_replay_confidence":
            if not self.blocked_stage_count:
                raise ValueError("blocked replay confidence report requires blocked stages")
        if not self.display_banner:
            raise ValueError("replay confidence report requires display banner")
        for key in ("status", "candidate_only", "blocked_actions"):
            if key not in self.display_banner:
                raise ValueError(f"replay confidence display banner missing {key}")
        if not self.candidate_exception_lake_labels:
            raise ValueError("replay confidence report requires candidate labels")
        if not self.required_next_gates:
            raise ValueError("replay confidence report requires next gates")
        if not self.red_team_notes:
            raise ValueError("replay confidence report requires red team notes")
        if not self.rust_transition_candidates:
            raise ValueError("replay confidence report requires Rust transition candidates")
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


class RustPublicDataCacheCustodyFailure(StrictModel):
    source_id: str
    path: str
    check: str
    expected: str | None = None
    actual: str | None = None
    message: str


class RustPublicDataCacheCustodySample(StrictModel):
    source_id: str
    cache_ref: str | None = None
    resolved_path_ref: str | None = None
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    expected_byte_count: int | None = Field(default=None, ge=0)
    actual_byte_count: int | None = Field(default=None, ge=0)
    status: Literal["passed", "failed", "blocked", "missing", "invalid"]


class RustPublicDataCacheCustodyReport(StrictModel):
    schema_version: str = "0.1"
    checker: Literal["public-data-cache-custody-checker"]
    status: Literal["passed", "failed"]
    repo_root: str
    cache_root: str
    manifest_ref: str
    manifest_sha256: str
    manifest_byte_count: int = Field(ge=0)
    manifest_entry_count: int = Field(ge=0)
    checked_source_count: int = Field(ge=0)
    checked_sample_count: int = Field(ge=0)
    total_checked_sample_bytes: int = Field(ge=0)
    root_violation_count: int = Field(ge=0)
    manifest_error_count: int = Field(ge=0)
    invalid_manifest_entry_count: int = Field(ge=0)
    blocked_path_count: int = Field(ge=0)
    missing_file_count: int = Field(ge=0)
    hash_mismatch_count: int = Field(ge=0)
    byte_count_mismatch_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    failures: list[RustPublicDataCacheCustodyFailure] = Field(default_factory=list)
    samples: list[RustPublicDataCacheCustodySample] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    planning_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    metadata_only_report: Literal[True] = True
    local_file_custody_only: Literal[True] = True
    public_cache_samples_may_be_present: bool
    direct_runtime_ingestion_allowed: Literal[False] = False
    public_records_runtime_ingested: Literal[False] = False
    public_payload_committed: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    tracked_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_public_data_cache_custody_counts_match(
        self,
    ) -> "RustPublicDataCacheCustodyReport":
        if self.failure_count != len(self.failures):
            raise ValueError("Rust public data cache custody failure count mismatch")
        category_total = (
            self.root_violation_count
            + self.manifest_error_count
            + self.invalid_manifest_entry_count
            + self.blocked_path_count
            + self.missing_file_count
            + self.hash_mismatch_count
            + self.byte_count_mismatch_count
        )
        if self.failure_count != category_total:
            raise ValueError("Rust public data cache custody category count mismatch")
        if self.checked_sample_count > self.checked_source_count:
            raise ValueError("Rust public data cache checked sample count exceeds sources")
        if self.public_cache_samples_may_be_present != (self.checked_sample_count > 0):
            raise ValueError("Rust public data cache sample presence mismatch")
        if self.status == "passed":
            if self.failure_count or self.failures:
                raise ValueError("passed Rust public data cache custody report cannot fail")
            if any(sample.status != "passed" for sample in self.samples):
                raise ValueError(
                    "passed Rust public data cache custody report cannot include blocked samples"
                )
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust public data cache custody report requires failures")
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
    rust_custody_report_ref: str | None = None
    rust_custody_status: Literal["passed", "failed", "not_run"] = "not_run"
    rust_custody_failure_count: int = Field(default=0, ge=0)
    rust_custody_checked_source_count: int = Field(default=0, ge=0)
    rust_custody_checked_sample_count: int = Field(default=0, ge=0)
    rust_custody_total_checked_sample_bytes: int = Field(default=0, ge=0)
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
                or self.rust_custody_status != "passed"
                or self.rust_custody_failure_count
            ):
                raise ValueError("ready public data cache audit cannot include blockers")
        if self.status == "blocked_public_data_cache" and not any(
            check.status in {"blocked", "failed"} for check in self.checks
        ):
            raise ValueError("blocked public data cache audit requires blocked or failed checks")
        return self


class MatterLinkingPreflightCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkingPreflightCluster(StrictModel):
    cluster_id: str
    link_state: str
    match_strength: str
    proposed_short_label: str | None = None
    source_ids: list[str]
    source_hashes: list[str]
    supporting_signal_count: int = Field(ge=0)
    strong_supporting_signal_count: int = Field(ge=0)
    negative_signal_count: int = Field(ge=0)
    strong_negative_signal_count: int = Field(ge=0)
    supporting_signal_types: list[str]
    negative_signal_types: list[str]
    source_bound_strong_support_present: bool
    weak_only_candidate: bool
    negative_split_evidence_required: bool
    requires_human_confirmation: Literal[True] = True
    matter_link_finalized: Literal[False] = False

    @model_validator(mode="after")
    def matter_linking_cluster_counts_match(self) -> "MatterLinkingPreflightCluster":
        if self.supporting_signal_count < self.strong_supporting_signal_count:
            raise ValueError("strong supporting signal count cannot exceed supporting signals")
        if self.negative_signal_count < self.strong_negative_signal_count:
            raise ValueError("strong negative signal count cannot exceed negative signals")
        if self.weak_only_candidate and self.source_bound_strong_support_present:
            raise ValueError("weak-only matter-linking candidate cannot have strong support")
        if not self.negative_split_evidence_required and self.strong_negative_signal_count:
            raise ValueError("single-candidate matter link cannot carry split evidence count")
        return self


class MatterLinkingPreflightReport(StrictModel):
    schema_version: str = "0.1"
    matter_linking_preflight_report_id: str
    status: Literal[
        "matter_linking_preflight_requires_review",
        "matter_linking_preflight_resolved_candidate_requires_review",
        "blocked_matter_linking_preflight",
    ]
    source_artifact_ref: str
    source_artifact_id: str
    source_artifact_type: str
    source_artifact_status: str
    source_artifact_hash: str
    data_origin: str
    source_system_name: str
    real_upfront_export: bool
    api_contract_verified: bool
    official_matter_number_status: str
    overall_link_state: str
    requires_human_confirmation: bool
    requires_sender_followup: bool
    cluster_count: int = Field(ge=0)
    high_evidence_candidate_count: int = Field(ge=0)
    weak_only_candidate_count: int = Field(ge=0)
    negative_split_evidence_required: bool
    weak_signal_count: int = Field(ge=0)
    strong_negative_signal_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    source_hashes_by_id: dict[str, str]
    weak_merge_signal_types: list[str]
    candidate_exception_lake_labels: list[str]
    clusters: list[MatterLinkingPreflightCluster]
    checks: list[MatterLinkingPreflightCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    sender_followup_required: bool
    upfront_connector_implemented: bool = False
    vendor_api_called: bool = False
    external_write_performed: bool = False
    lake_write_performed: bool = False
    sqlite_write_performed: bool = False
    matter_opening_authorized: bool = False
    budget_amount_output_authorized: bool = False
    budget_submission_authorized: bool = False
    conflict_conclusion_emitted: bool = False
    screen_created: bool = False
    silent_learning_performed: bool = False
    generated_at: str

    @model_validator(mode="after")
    def matter_linking_preflight_counts_and_status_match(
        self,
    ) -> "MatterLinkingPreflightReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.cluster_count != len(self.clusters):
            raise ValueError("matter-linking cluster count does not match clusters")
        if self.high_evidence_candidate_count != sum(
            1 for cluster in self.clusters if "high_evidence" in cluster.match_strength
        ):
            raise ValueError("matter-linking high-evidence count does not match clusters")
        if self.weak_only_candidate_count != sum(
            1 for cluster in self.clusters if cluster.weak_only_candidate
        ):
            raise ValueError("matter-linking weak-only candidate count mismatch")
        if self.strong_negative_signal_count != sum(
            cluster.strong_negative_signal_count for cluster in self.clusters
        ):
            raise ValueError("matter-linking strong negative signal count mismatch")
        if any(
            cluster.negative_split_evidence_required != self.negative_split_evidence_required
            for cluster in self.clusters
        ):
            raise ValueError("matter-linking split-evidence requirement mismatch")
        if not self.negative_split_evidence_required and self.strong_negative_signal_count:
            raise ValueError("single-candidate matter link cannot require split evidence")
        if self.source_count != len(self.source_hashes_by_id):
            raise ValueError("matter-linking source count must match source hashes")
        if (
            self.status
            in {
                "matter_linking_preflight_requires_review",
                "matter_linking_preflight_resolved_candidate_requires_review",
            }
            and failed
        ):
            raise ValueError("ready matter-linking preflight cannot include failed checks")
        if self.status == "blocked_matter_linking_preflight" and not failed:
            raise ValueError("blocked matter-linking preflight requires failed checks")
        required_gates = {
            "human_matter_linking_review",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
        }
        if self.sender_followup_required:
            required_gates.add("sender_reference_followup")
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-linking preflight is missing required next gates")
        return self


MatterLinkingReviewOutcome = Literal[
    "confirm_split",
    "confirm_merge",
    "confirm_single_candidate",
    "unknown",
    "request_more_info",
    "declined_or_referred",
]


class MatterLinkingReviewDecision(StrictModel):
    schema_version: str = "0.1"
    decision_id: str
    outcome: MatterLinkingReviewOutcome
    selected_cluster_ids: list[str]
    decision_reason: str
    evidence_refs: list[str]
    required_followups: list[str] = Field(default_factory=list)
    followup_owner: str | None = None
    followup_due_at: str | None = None
    red_team_notes: list[str]
    candidate_exception_lake_labels: list[str]

    @model_validator(mode="after")
    def matter_linking_review_decision_is_complete(
        self,
    ) -> "MatterLinkingReviewDecision":
        if not self.decision_id.strip():
            raise ValueError("matter-linking review decision requires decision_id")
        if not self.selected_cluster_ids:
            raise ValueError("matter-linking review decision requires selected clusters")
        if len(set(self.selected_cluster_ids)) != len(self.selected_cluster_ids):
            raise ValueError("matter-linking review decision cluster IDs must be unique")
        if not self.decision_reason.strip():
            raise ValueError("matter-linking review decision requires decision_reason")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("matter-linking review decision requires evidence refs")
        if not self.red_team_notes or any(not note.strip() for note in self.red_team_notes):
            raise ValueError("matter-linking review decision requires red-team notes")
        if not self.candidate_exception_lake_labels or any(
            not label.strip() for label in self.candidate_exception_lake_labels
        ):
            raise ValueError("matter-linking review decision requires candidate labels")
        if (
            self.outcome in {"confirm_split", "confirm_merge"}
            and len(self.selected_cluster_ids) < 2
        ):
            raise ValueError(f"{self.outcome} decisions require at least two clusters")
        if self.outcome == "confirm_single_candidate" and len(self.selected_cluster_ids) != 1:
            raise ValueError("confirm_single_candidate decisions require exactly one cluster")
        if self.outcome in {"unknown", "request_more_info", "declined_or_referred"}:
            if not (self.followup_owner and self.followup_owner.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_owner")
            if not (self.followup_due_at and self.followup_due_at.strip()):
                raise ValueError(f"{self.outcome} decisions require followup_due_at")
            if not self.required_followups:
                raise ValueError(f"{self.outcome} decisions require required_followups")
        return self


class MatterLinkingReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    matter_linking_review_outcome_record_id: str
    matter_linking_preflight_report_id: str
    source_matter_linking_preflight_report_ref: str | None = None
    reviewer_id: str
    reviewer_role: str | None = None
    reviewed_at: str
    overall_outcome: MatterLinkingReviewOutcome
    decision_reason: str
    decisions: list[MatterLinkingReviewDecision]
    supersedes_matter_linking_review_outcome_record_id: str | None = None
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_conflict_conclusion: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    screen_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def matter_linking_review_outcome_record_is_complete(
        self,
    ) -> "MatterLinkingReviewOutcomeRecord":
        if not self.matter_linking_review_outcome_record_id.strip():
            raise ValueError("matter-linking review outcome record requires id")
        if not self.matter_linking_preflight_report_id.strip():
            raise ValueError("matter-linking review outcome record requires source report id")
        if not self.reviewer_id.strip():
            raise ValueError("matter-linking review outcome record requires reviewer_id")
        if not self.reviewed_at.strip():
            raise ValueError("matter-linking review outcome record requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("matter-linking review outcome record requires decision_reason")
        if not self.decisions:
            raise ValueError("matter-linking review outcome record requires decisions")
        decision_ids = [decision.decision_id for decision in self.decisions]
        if len(set(decision_ids)) != len(decision_ids):
            raise ValueError("matter-linking review outcome decision IDs must be unique")
        if self.overall_outcome not in {decision.outcome for decision in self.decisions}:
            raise ValueError("matter-linking review overall outcome must match a decision")
        return self


class MatterLinkingReviewOutcomeCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    cluster_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkingReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    matter_linking_review_outcome_report_id: str
    status: Literal[
        "matter_linking_review_outcome_recorded",
        "matter_linking_review_outcome_recorded_pending_followup",
        "blocked_by_matter_linking_review_outcome",
    ]
    source_matter_linking_preflight_report_ref: str
    matter_linking_preflight_report_id: str
    source_matter_linking_preflight_status: str
    matter_linking_review_outcome_record_id: str
    reviewer_id: str
    reviewed_at: str
    overall_outcome: MatterLinkingReviewOutcome
    decision_reason: str
    source_cluster_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    split_decision_count: int = Field(ge=0)
    merge_decision_count: int = Field(ge=0)
    single_candidate_decision_count: int = Field(ge=0)
    unknown_decision_count: int = Field(ge=0)
    request_more_info_decision_count: int = Field(ge=0)
    declined_or_referred_decision_count: int = Field(ge=0)
    reviewed_cluster_count: int = Field(ge=0)
    unreviewed_cluster_count: int = Field(ge=0)
    unknown_cluster_count: int = Field(ge=0)
    reviewed_cluster_ids: list[str]
    unreviewed_cluster_ids: list[str]
    unknown_cluster_ids: list[str]
    required_followups: list[str]
    candidate_lake_event_labels: list[str]
    append_only_history_ref: str
    checks: list[MatterLinkingReviewOutcomeCheck]
    required_next_gates: list[str]
    append_only: Literal[True] = True
    mutation_policy: Literal["append_only_supersession"] = "append_only_supersession"
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    not_authorized_for_budget_submission: Literal[True] = True
    not_authorized_for_matter_opening: Literal[True] = True
    not_authorized_for_conflict_conclusion: Literal[True] = True
    no_connector_implemented: Literal[True] = True
    no_lake_admission_performed: Literal[True] = True
    no_sibling_repo_writes: Literal[True] = True
    no_canonical_mutation: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    screen_created: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def matter_linking_review_outcome_report_counts_match(
        self,
    ) -> "MatterLinkingReviewOutcomeReport":
        if self.decision_count != (
            self.split_decision_count
            + self.merge_decision_count
            + self.single_candidate_decision_count
            + self.unknown_decision_count
            + self.request_more_info_decision_count
            + self.declined_or_referred_decision_count
        ):
            raise ValueError("matter-linking review decision outcome counts mismatch")
        if self.reviewed_cluster_count != len(self.reviewed_cluster_ids):
            raise ValueError("matter-linking review reviewed cluster count mismatch")
        if self.unreviewed_cluster_count != len(self.unreviewed_cluster_ids):
            raise ValueError("matter-linking review unreviewed cluster count mismatch")
        if self.unknown_cluster_count != len(self.unknown_cluster_ids):
            raise ValueError("matter-linking review unknown cluster count mismatch")
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "matter_linking_review_outcome_recorded" and (
            failed or self.unreviewed_cluster_count or self.unknown_cluster_count
        ):
            raise ValueError("recorded matter-linking review outcome cannot have blockers")
        if self.status == "matter_linking_review_outcome_recorded_pending_followup" and failed:
            raise ValueError("pending matter-linking review outcome cannot include failed checks")
        if self.status == "blocked_by_matter_linking_review_outcome" and not failed:
            raise ValueError("blocked matter-linking review outcome requires failed checks")
        if not self.candidate_lake_event_labels:
            raise ValueError("matter-linking review outcome report requires candidate labels")
        required_gates = {
            "append_only_matter_linking_review_outcome",
            "exception_lake_owner_review_before_admission",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_intake",
            "no_silent_learning_from_matter_linking_review",
        }
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-linking review outcome is missing required next gates")
        return self


class MatterLinkingQAGateCase(StrictModel):
    schema_version: str = "0.1"
    case_id: str
    fixture_ref: str
    generated_report_ref: str
    expected_status: str
    observed_status: str
    expected_overall_link_state: str
    observed_overall_link_state: str
    expected_cluster_count: int = Field(ge=0)
    observed_cluster_count: int = Field(ge=0)
    expected_high_evidence_candidate_count: int = Field(ge=0)
    observed_high_evidence_candidate_count: int = Field(ge=0)
    expected_weak_only_candidate_count: int = Field(ge=0)
    observed_weak_only_candidate_count: int = Field(ge=0)
    expected_negative_split_evidence_required: bool
    observed_negative_split_evidence_required: bool
    expected_sender_followup_required: bool
    observed_sender_followup_required: bool
    expected_failed_check_ids: list[str] = Field(default_factory=list)
    observed_failed_check_ids: list[str] = Field(default_factory=list)
    required_coverage_tags: list[str]
    candidate_exception_lake_labels: list[str]
    status: Literal["passed", "failed"]
    notes: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def matter_linking_qa_gate_case_is_complete(self) -> "MatterLinkingQAGateCase":
        if not self.case_id.strip():
            raise ValueError("matter-linking QA case requires case_id")
        if not self.fixture_ref.strip() or not self.generated_report_ref.strip():
            raise ValueError("matter-linking QA case requires fixture and report refs")
        if not self.required_coverage_tags:
            raise ValueError("matter-linking QA case requires coverage tags")
        if not self.candidate_exception_lake_labels:
            raise ValueError("matter-linking QA case requires candidate labels")
        if not self.notes:
            raise ValueError("matter-linking QA case requires notes")
        return self


class MatterLinkingQAGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    case_ids: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class MatterLinkingQAGateReport(StrictModel):
    schema_version: str = "0.1"
    matter_linking_qa_gate_report_id: str
    status: Literal[
        "matter_linking_qa_gate_ready_for_review",
        "blocked_by_matter_linking_qa_gate",
    ]
    repo_root_ref: str
    out_dir_ref: str
    case_count: int = Field(ge=0)
    passed_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    required_coverage_tag_count: int = Field(ge=0)
    observed_coverage_tag_count: int = Field(ge=0)
    missing_coverage_tags: list[str]
    cases: list[MatterLinkingQAGateCase]
    checks: list[MatterLinkingQAGateCheck]
    candidate_exception_lake_labels: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
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
    def matter_linking_qa_gate_report_counts_match(self) -> "MatterLinkingQAGateReport":
        failed_cases = [case for case in self.cases if case.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        observed_tags = {tag for case in self.cases for tag in case.required_coverage_tags}
        if self.case_count != len(self.cases):
            raise ValueError("matter-linking QA gate case count mismatch")
        if self.failed_case_count != len(failed_cases):
            raise ValueError("matter-linking QA gate failed case count mismatch")
        if self.passed_case_count != self.case_count - self.failed_case_count:
            raise ValueError("matter-linking QA gate passed case count mismatch")
        if self.observed_coverage_tag_count != len(observed_tags):
            raise ValueError("matter-linking QA gate coverage tag count mismatch")
        if self.required_coverage_tag_count < self.observed_coverage_tag_count:
            raise ValueError("observed coverage tags cannot exceed required coverage tags")
        if self.status == "matter_linking_qa_gate_ready_for_review" and (
            failed_cases or failed_checks or self.missing_coverage_tags
        ):
            raise ValueError("ready matter-linking QA gate cannot have failed evidence")
        if self.status == "blocked_by_matter_linking_qa_gate" and not (
            failed_cases or failed_checks or self.missing_coverage_tags
        ):
            raise ValueError("blocked matter-linking QA gate requires failed evidence")
        required_gates = {
            "human_matter_linking_review",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_matter_linking_qa_gate",
            "exception_lake_owner_review_before_admission",
        }
        if not required_gates.issubset(set(self.required_next_gates)):
            raise ValueError("matter-linking QA gate is missing required next gates")
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


class PublicDerivedSyntheticQAGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    conversion_spec_ids: list[str] = Field(default_factory=list)
    candidate_exception_lake_labels: list[str] = Field(default_factory=list)


class PublicDerivedSyntheticQAGateReport(StrictModel):
    schema_version: str = "0.1"
    public_derived_synthetic_qa_gate_report_id: str
    status: Literal[
        "public_derived_synthetic_qa_ready_for_review",
        "blocked_by_public_derived_synthetic_qa_gate",
    ]
    source_methodology_report_ref: str
    source_methodology_report_id: str
    source_methodology_report_status: str
    conversion_plan_ref: str
    conversion_plan_id: str
    conversion_plan_status: str
    conversion_review_packet_ref: str
    conversion_review_packet_id: str
    conversion_review_packet_status: str
    public_data_cache_audit_report_ref: str | None = None
    public_data_cache_audit_report_id: str | None = None
    public_data_cache_audit_status: str | None = None
    cache_audit_present: bool = False
    cache_audit_required: bool = False
    cache_custody_status: Literal["passed", "failed", "not_run", "not_required"] = "not_required"
    methodology_source_count: int = Field(ge=0)
    conversion_spec_count: int = Field(ge=0)
    review_recommendation_count: int = Field(ge=0)
    review_red_team_note_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    blocked_check_count: int = Field(ge=0)
    warning_check_count: int = Field(ge=0)
    source_ids: list[str]
    conversion_spec_ids: list[str]
    target_fixture_families: list[str]
    checks: list[PublicDerivedSyntheticQAGateCheck]
    required_next_gates: list[str]
    candidate_exception_lake_labels: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    metadata_only: Literal[True] = True
    human_review_required: Literal[True] = True
    fixture_generation_authorized: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    github_pr_created: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    tracked_public_payload_committed: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def public_derived_synthetic_qa_gate_counts_match(
        self,
    ) -> "PublicDerivedSyntheticQAGateReport":
        if self.methodology_source_count != len(self.source_ids):
            raise ValueError("public-derived QA gate source count must match source IDs")
        if self.conversion_spec_count != len(self.conversion_spec_ids):
            raise ValueError("public-derived QA gate spec count must match spec IDs")
        failed = [check for check in self.checks if check.status == "failed"]
        blocked = [check for check in self.checks if check.status == "blocked"]
        warnings = [check for check in self.checks if check.status == "warning"]
        if self.failed_check_count != len(failed):
            raise ValueError("public-derived QA gate failed check count mismatch")
        if self.blocked_check_count != len(blocked):
            raise ValueError("public-derived QA gate blocked check count mismatch")
        if self.warning_check_count != len(warnings):
            raise ValueError("public-derived QA gate warning count mismatch")
        if self.cache_audit_required and not self.cache_audit_present:
            raise ValueError("public-derived QA gate cannot require an absent cache audit")
        if not self.cache_audit_required and self.cache_custody_status != "not_required":
            raise ValueError("unrequired cache audit must use not_required custody status")
        if not self.required_next_gates:
            raise ValueError("public-derived QA gate requires next gates")
        if not self.candidate_exception_lake_labels:
            raise ValueError("public-derived QA gate requires candidate exception labels")
        if self.status == "public_derived_synthetic_qa_ready_for_review":
            if self.failed_check_count or self.blocked_check_count:
                raise ValueError("ready public-derived QA gate cannot include blockers")
            if self.methodology_source_count == 0 or self.conversion_spec_count == 0:
                raise ValueError("ready public-derived QA gate requires sources and specs")
        if (
            self.status == "blocked_by_public_derived_synthetic_qa_gate"
            and not self.failed_check_count
            and not self.blocked_check_count
        ):
            raise ValueError("blocked public-derived QA gate requires failed or blocked checks")
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


PublicMethodologyOwnerTargetRepo = Literal[
    "LawFirm-os-intake",
    "LawFirm-os-legal-knowledge-runtime",
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

PublicMethodologyOwnerHandoffFocus = Literal[
    "local_intake_candidate_stewardship",
    "legal_knowledge_public_adapter_boundary",
    "public_data_governance_policy",
    "runtime_public_source_gate",
    "append_only_public_methodology_audit",
]


class PublicMethodologyOwnerHandoffCheck(StrictModel):
    check_id: str
    status: Literal["passed", "blocked", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class PublicMethodologyOwnerHandoffPacket(StrictModel):
    schema_version: str = "0.1"
    handoff_packet_id: str
    target_repo: PublicMethodologyOwnerTargetRepo
    handoff_focus: PublicMethodologyOwnerHandoffFocus
    status: Literal["ready_for_owner_review", "blocked_by_public_methodology_chain"]
    source_public_methodology_report_id: str
    source_public_methodology_report_ref: str
    source_public_methodology_status: Literal[
        "ready_for_human_public_source_methodology_review",
        "blocked_public_source_methodology",
    ]
    source_conversion_plan_id: str
    source_conversion_plan_ref: str
    source_conversion_plan_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_public_methodology_not_ready",
    ]
    source_conversion_review_packet_id: str
    source_conversion_review_packet_ref: str
    source_conversion_review_packet_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_by_conversion_plan",
        "no_specs_to_review",
    ]
    source_count: int = Field(ge=0)
    spec_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    red_team_note_count: int = Field(ge=0)
    source_ids: list[str]
    source_artifact_refs: list[str] = Field(default_factory=list)
    candidate_contract_refs: list[str] = Field(default_factory=list)
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    metadata_only: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    direct_runtime_ingestion_allowed: Literal[False] = False
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    real_party_records_committed: Literal[False] = False
    real_matter_records_committed: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_generation_authorized: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def public_methodology_owner_packet_is_reviewable(
        self,
    ) -> "PublicMethodologyOwnerHandoffPacket":
        if self.status == "ready_for_owner_review" and not self.source_ids:
            raise ValueError("public methodology owner packet requires source ids")
        if not self.source_artifact_refs:
            raise ValueError("public methodology owner packet requires source artifact refs")
        if not self.candidate_contract_refs:
            raise ValueError("public methodology owner packet requires candidate contract refs")
        if not self.required_owner_actions:
            raise ValueError("public methodology owner packet requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("public methodology owner packet requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("public methodology owner packet requires red-team notes")
        required = {
            "human_public_methodology_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "source_license_privacy_retention_review",
            "legal_knowledge_runtime_owner_review_before_adapter",
            "no_intake_public_ingestion_or_adapter_authorization",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("public methodology owner packet is missing required gates")
        return self


class PublicMethodologyOwnerHandoffReport(StrictModel):
    schema_version: str = "0.1"
    owner_handoff_report_id: str
    status: Literal[
        "public_methodology_owner_handoff_packets_ready",
        "blocked_by_public_methodology_chain",
    ]
    source_public_methodology_report_id: str
    source_public_methodology_report_ref: str
    source_public_methodology_status: Literal[
        "ready_for_human_public_source_methodology_review",
        "blocked_public_source_methodology",
    ]
    source_conversion_plan_id: str
    source_conversion_plan_ref: str
    source_conversion_plan_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_public_methodology_not_ready",
    ]
    source_conversion_review_packet_id: str
    source_conversion_review_packet_ref: str
    source_conversion_review_packet_status: Literal[
        "ready_for_human_conversion_review",
        "blocked_by_conversion_plan",
        "no_specs_to_review",
    ]
    target_repo_count: int = Field(ge=0)
    packet_count: int = Field(ge=0)
    ready_packet_count: int = Field(ge=0)
    blocked_packet_count: int = Field(ge=0)
    target_repos: list[PublicMethodologyOwnerTargetRepo]
    packets: list[PublicMethodologyOwnerHandoffPacket]
    packet_output_refs: list[str] = Field(default_factory=list)
    checks: list[PublicMethodologyOwnerHandoffCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    planning_only: Literal[True] = True
    metadata_only: Literal[True] = True
    human_review_required: Literal[True] = True
    owning_repo_review_required: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    direct_runtime_ingestion_allowed: Literal[False] = False
    direct_promotion_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    github_issue_created: Literal[False] = False
    github_pr_created: Literal[False] = False
    github_write_performed: Literal[False] = False
    public_records_ingested: Literal[False] = False
    raw_public_payload_committed: Literal[False] = False
    real_party_records_committed: Literal[False] = False
    real_matter_records_committed: Literal[False] = False
    synthetic_fixtures_created: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    fixture_generation_authorized: Literal[False] = False
    fixture_pr_created: Literal[False] = False
    connector_implemented: Literal[False] = False
    legal_knowledge_adapter_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def public_methodology_owner_report_counts_match(
        self,
    ) -> "PublicMethodologyOwnerHandoffReport":
        blocked_checks = [check for check in self.checks if check.status != "passed"]
        if self.packet_count != len(self.packets):
            raise ValueError("public methodology owner packet count does not match")
        if self.packet_count != len(self.packet_output_refs):
            raise ValueError("public methodology owner packet output ref count does not match")
        if self.target_repo_count != len(self.target_repos):
            raise ValueError("public methodology owner target repo count does not match")
        packet_targets = [packet.target_repo for packet in self.packets]
        if set(packet_targets) != set(self.target_repos) or len(packet_targets) != len(
            self.target_repos
        ):
            raise ValueError("public methodology owner target repos do not match packets")
        ready_count = sum(1 for packet in self.packets if packet.status == "ready_for_owner_review")
        blocked_count = sum(
            1 for packet in self.packets if packet.status == "blocked_by_public_methodology_chain"
        )
        if self.ready_packet_count != ready_count:
            raise ValueError("public methodology owner ready count does not match")
        if self.blocked_packet_count != blocked_count:
            raise ValueError("public methodology owner blocked count does not match")
        if self.status == "public_methodology_owner_handoff_packets_ready" and (
            blocked_checks or blocked_count
        ):
            raise ValueError("ready public methodology owner handoff cannot include blockers")
        if self.status == "blocked_by_public_methodology_chain" and not (
            blocked_checks or blocked_count
        ):
            raise ValueError("blocked public methodology owner handoff requires blockers")
        required = {
            "human_public_methodology_owner_review",
            "manual_owner_issue_creation_if_desired",
            "owning_repo_triage",
            "owner_repo_implementation_pr_if_accepted",
            "source_license_privacy_retention_review",
            "legal_knowledge_runtime_owner_review_before_adapter",
            "no_intake_public_ingestion_or_adapter_authorization",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("public methodology owner report is missing required gates")
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
    independent_critic_finding_codes: list[str] = Field(default_factory=list)
    independent_critic_evidence_ref_count: int = Field(default=0, ge=0)
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
        "carrier_rate_card",
        "labor_employment_budget_fact_report",
        "labor_employment_driver_impact_report",
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
    status: Literal["ready_for_human_review", "flagged_for_human_review"] = "ready_for_human_review"
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
    probability_integrity_status: Literal[
        "not_configured",
        "reviewed_probabilities",
        "bounded_unknown_mass",
        "probability_sum_mismatch",
        "partial_probability_weights",
        "hours_only_not_computed",
    ] = "not_configured"
    policy_issue_codes: list[str] = Field(default_factory=list)
    policy_issue_notes: list[str] = Field(default_factory=list)
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
        if self.monotonic_total_order is False:
            raise ValueError("budget scenario totals must be monotonic by phase order")
        if self.status == "ready_for_human_review" and self.policy_issue_codes:
            raise ValueError("ready budget scenario set cannot contain policy issue codes")
        if self.status == "flagged_for_human_review" and not self.policy_issue_codes:
            raise ValueError("flagged budget scenario set requires policy issue codes")
        if len(self.policy_issue_codes) != len(set(self.policy_issue_codes)):
            raise ValueError("budget scenario policy issue codes must be unique")
        if len(self.policy_issue_notes) < len(self.policy_issue_codes):
            raise ValueError("budget scenario policy issue notes must cover issue codes")
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


class IntensityNormalizationMultiplierRow(StrictModel):
    matter_family: str
    driver_id: str
    tier: str
    phase_id: str
    baseline_tier: str | None = None
    raw_multiplier: float = Field(ge=0)
    baseline_raw_multiplier: float = Field(ge=0)
    effective_multiplier: float = Field(ge=0)


class IntensityNormalizationDemoTotal(StrictModel):
    demo_case_id: str
    matter_family: str
    input_ref: str
    confirmation_ref: str
    pricing_status_before: str
    pricing_status_after: str
    total_proposed_budget_before: float | None = None
    total_proposed_budget_after: float | None = None
    subtotal_fees_before: float | None = None
    subtotal_fees_after: float | None = None
    subtotal_expenses_before: float = Field(ge=0)
    subtotal_expenses_after: float = Field(ge=0)
    contingency_amount_before: float | None = None
    contingency_amount_after: float | None = None
    delta_amount: float | None = None
    delta_percent: float | None = None
    before_case_driver_profile_id: str
    after_case_driver_profile_id: str


class IntensityNormalizationFamilySignoff(StrictModel):
    matter_family: str
    template_id: str
    baseline_source: Literal["template_declaration", "family_defaults"]
    baseline_by_driver: dict[str, str]
    per_phase_default_product_before: dict[str, float]
    per_phase_default_product_after: dict[str, float]
    effective_multiplier_table: list[IntensityNormalizationMultiplierRow]
    demo_totals: list[IntensityNormalizationDemoTotal] = Field(default_factory=list)

    @model_validator(mode="after")
    def baseline_and_table_required(self) -> "IntensityNormalizationFamilySignoff":
        if not self.baseline_by_driver:
            raise ValueError("intensity signoff family requires baseline_by_driver")
        if not self.effective_multiplier_table:
            raise ValueError("intensity signoff family requires effective multiplier rows")
        return self


class IntensityNormalizationSignoffReport(StrictModel):
    schema_version: str = "0.1"
    signoff_id: str
    generated_at: str
    status: Literal[
        "preview_requires_human_approval",
        "approved_for_baseline_relative",
        "rejected",
    ]
    policy_id: str
    policy_version_before: str
    policy_version_after: str
    policy_sha256_before: str
    policy_sha256_after: str
    normalization_mode_before: Literal["raw"] = "raw"
    normalization_mode_after: Literal["baseline_relative"] = "baseline_relative"
    per_family: list[IntensityNormalizationFamilySignoff]
    requires_human_approval: Literal[True] = True
    approved_by: str | None = None
    approved_at: str | None = None
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_real_firm_data: Literal[True] = True
    no_budget_submission_authority: Literal[True] = True
    no_matter_opening_authority: Literal[True] = True
    no_conflict_clearance_authority: Literal[True] = True
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    decision_required: str

    @model_validator(mode="after")
    def approved_status_requires_human_fields(self) -> "IntensityNormalizationSignoffReport":
        if self.status == "approved_for_baseline_relative":
            if not self.approved_by or not self.approved_at:
                raise ValueError("approved intensity signoff requires approved_by and approved_at")
        if not self.per_family:
            raise ValueError("intensity signoff requires at least one matter family")
        return self


class IntensityNormalizationSignoffGateCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    blocking_refs: list[str] = Field(default_factory=list)


class IntensityNormalizationSignoffGateReport(StrictModel):
    schema_version: str = "0.1"
    status: Literal["passed", "failed"]
    policy_id: str
    policy_version: str
    normalization_mode: Literal["raw", "baseline_relative"]
    signoff_required: bool
    signoff_ref: str | None = None
    signoff_status: str | None = None
    checks: list[IntensityNormalizationSignoffGateCheck]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    no_policy_flip_without_approved_signoff: Literal[True] = True
    no_budget_submission_authority: Literal[True] = True
    lake_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False

    @model_validator(mode="after")
    def status_matches_checks(self) -> "IntensityNormalizationSignoffGateReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "passed" and failed:
            raise ValueError("passed signoff gate cannot contain failed checks")
        if self.status == "failed" and not failed:
            raise ValueError("failed signoff gate requires at least one failed check")
        return self


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
    line_delta_signed: float = 0
    rate_cap_delta_signed: float = 0
    expense_cap_delta_signed: float = 0
    disallowed_delta_signed: float = 0
    staffing_rule_delta_signed: float = 0
    compliant_increase_amount: float = Field(default=0, ge=0)
    requires_human_review: bool = False
    review_issue_codes: list[str] = Field(default_factory=list)
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
    total_delta_signed: float = 0
    rate_cap_delta_signed: float = 0
    expense_cap_delta_signed: float = 0
    disallowed_delta_signed: float = 0
    staffing_rule_delta_signed: float = 0
    contingency_delta_signed: float = 0
    compliant_increase_amount: float = Field(default=0, ge=0)
    proposed_blended_rate: float | None = None
    compliant_blended_rate: float | None = None
    blended_rate_delta: float = Field(default=0, ge=0)
    blended_rate_delta_signed: float = 0
    line_count: int = Field(ge=0)
    capped_line_count: int = Field(ge=0)
    disallowed_line_count: int = Field(ge=0)
    staffing_rule_adjusted_line_count: int = Field(ge=0)
    review_required_line_count: int = Field(default=0, ge=0)
    review_issue_codes: list[str] = Field(default_factory=list)
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
    observation_period_end: str | None = None
    page_sha256: str
    quote_span: str
    license_note: str
    proxy_bias_note: str = ""
    grade: Literal["A", "B", "C", "proxy_only", "ungraded"]
    human_grading_status: Literal["pending", "reviewed", "rejected"]
    candidate_only: Literal[True] = True
    not_authorized_as_carrier_rate: Literal[True] = True


class BenchmarkSnapshotManifest(StrictModel):
    schema_version: str = "0.1"
    benchmark_snapshot_id: str
    created_at: str
    source_owner: Literal["legal_knowledge_runtime", "local_candidate_fixture"]
    method_version: str = "benchmark_snapshot_manifest.v0_1"
    rubric_version: str = "benchmark_effective_grade.v0_1"
    contains_real_negotiated_rates: Literal[False] = False
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


BenchmarkEffectiveGrade = Literal["A", "B", "C", "proxy_only", "ungraded", "rejected"]


class BenchmarkReplayCellCheck(StrictModel):
    benchmark_cell_id: str
    status: Literal["passed", "failed", "ignored"]
    original_grade: Literal["A", "B", "C", "proxy_only", "ungraded"]
    effective_grade: BenchmarkEffectiveGrade
    human_grading_status: Literal["pending", "reviewed", "rejected"]
    effective_grade_method: Literal["benchmark_effective_grade.v0_1"] = (
        "benchmark_effective_grade.v0_1"
    )
    staleness_months: int = Field(ge=0)
    band_flag_authorized: bool
    issue_codes: list[str] = Field(default_factory=list)
    message: str
    candidate_only: Literal[True] = True
    not_authorized_as_carrier_rate: Literal[True] = True

    @model_validator(mode="after")
    def benchmark_cell_check_is_coherent(self) -> "BenchmarkReplayCellCheck":
        if self.status == "passed" and self.issue_codes:
            raise ValueError("passed benchmark cell check cannot include issue codes")
        if self.status in {"failed", "ignored"} and not self.issue_codes:
            raise ValueError("failed/ignored benchmark cell check requires issue codes")
        if self.band_flag_authorized and self.effective_grade not in {"A", "B"}:
            raise ValueError("benchmark band flags require effective grade A or B")
        if self.band_flag_authorized and self.human_grading_status != "reviewed":
            raise ValueError("benchmark band flags require reviewed human grading")
        return self


class BenchmarkReplayBudgetLineCheck(StrictModel):
    line_ref: str
    status: Literal["passed", "failed"]
    pricing_status: Literal["priced", "hours_only", "insufficient_information", "unknown"]
    rate_source: str | None = None
    rate_trace_status: Literal[
        "authorized_rate_source",
        "hours_only_no_rate",
        "benchmark_context_ref_valid",
        "benchmark_context_missing",
        "benchmark_launder_attempt",
        "unknown_or_invalid_rate_source",
    ]
    benchmark_refs: list[str] = Field(default_factory=list)
    missing_benchmark_refs: list[str] = Field(default_factory=list)
    issue_codes: list[str] = Field(default_factory=list)
    message: str
    candidate_only: Literal[True] = True
    budget_submission_authorized: Literal[False] = False
    not_authorized_as_carrier_rate: Literal[True] = True

    @model_validator(mode="after")
    def benchmark_line_check_is_coherent(self) -> "BenchmarkReplayBudgetLineCheck":
        if self.status == "passed" and (self.issue_codes or self.missing_benchmark_refs):
            raise ValueError("passed benchmark line check cannot include issues")
        if self.status == "failed" and not (self.issue_codes or self.missing_benchmark_refs):
            raise ValueError("failed benchmark line check requires issue detail")
        if (
            self.rate_trace_status == "benchmark_context_missing"
            and not self.missing_benchmark_refs
        ):
            raise ValueError("missing benchmark context requires missing refs")
        return self


class BenchmarkReplayCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class BenchmarkReplayReport(StrictModel):
    schema_version: str = "0.1"
    benchmark_replay_report_id: str
    status: Literal["benchmark_replay_ready_for_review", "blocked_by_benchmark_replay"]
    budget_proposal_ref: str
    budget_proposal_id: str | None = None
    benchmark_snapshot_ref: str
    benchmark_snapshot_id: str | None = None
    benchmark_snapshot_hash: str | None = None
    expected_benchmark_snapshot_hash: str | None = None
    as_of_date: str
    grade_methodology_version: Literal["benchmark_effective_grade.v0_1"] = (
        "benchmark_effective_grade.v0_1"
    )
    snapshot_cell_count: int = Field(ge=0)
    cell_check_count: int = Field(ge=0)
    failed_cell_check_count: int = Field(ge=0)
    ignored_cell_check_count: int = Field(ge=0)
    budget_line_check_count: int = Field(ge=0)
    failed_budget_line_check_count: int = Field(ge=0)
    missing_benchmark_ref_count: int = Field(ge=0)
    rate_laundering_attempt_count: int = Field(ge=0)
    benchmark_cells_used_as_rate_authority: Literal[False] = False
    cells: list[BenchmarkReplayCellCheck]
    budget_lines: list[BenchmarkReplayBudgetLineCheck]
    checks: list[BenchmarkReplayCheck]
    candidate_exception_lake_labels: list[str]
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
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def benchmark_replay_report_counts_match(self) -> "BenchmarkReplayReport":
        failed_cells = [cell for cell in self.cells if cell.status == "failed"]
        ignored_cells = [cell for cell in self.cells if cell.status == "ignored"]
        failed_lines = [line for line in self.budget_lines if line.status == "failed"]
        failed_checks = [check for check in self.checks if check.status == "failed"]
        if self.cell_check_count != len(self.cells):
            raise ValueError("benchmark replay cell check count mismatch")
        if self.failed_cell_check_count != len(failed_cells):
            raise ValueError("benchmark replay failed cell count mismatch")
        if self.ignored_cell_check_count != len(ignored_cells):
            raise ValueError("benchmark replay ignored cell count mismatch")
        if self.budget_line_check_count != len(self.budget_lines):
            raise ValueError("benchmark replay budget line count mismatch")
        if self.failed_budget_line_check_count != len(failed_lines):
            raise ValueError("benchmark replay failed line count mismatch")
        if self.missing_benchmark_ref_count != sum(
            len(line.missing_benchmark_refs) for line in self.budget_lines
        ):
            raise ValueError("benchmark replay missing ref count mismatch")
        if self.rate_laundering_attempt_count != sum(
            1 for line in self.budget_lines if line.rate_trace_status == "benchmark_launder_attempt"
        ):
            raise ValueError("benchmark replay laundering count mismatch")
        blocked = bool(failed_cells or failed_lines or failed_checks)
        if self.status == "benchmark_replay_ready_for_review" and blocked:
            raise ValueError("ready benchmark replay report cannot include failed checks")
        if self.status == "blocked_by_benchmark_replay" and not blocked:
            raise ValueError("blocked benchmark replay report requires failed checks")
        required = {
            "human_budget_benchmark_context_review",
            "no_benchmark_cell_as_rate_authority",
            "legal_knowledge_runtime_owns_public_retrieval",
            "no_lake_or_sqlite_write_from_benchmark_replay",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("benchmark replay report missing required next gates")
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
    labor_employment_driver_impact_report_ref: str | None = None
    labor_employment_driver_impact_status: (
        Literal[
            "labor_employment_executable_driver_impacts_ready_for_review",
            "blocked_by_labor_employment_executable_driver_impacts",
        ]
        | None
    ) = None
    labor_employment_driver_allowed_budget_output: (
        LaborEmploymentExecutableDriverAllowedBudgetOutput | None
    ) = None
    labor_employment_driver_block_amount_budget_impact_count: int = Field(default=0, ge=0)
    labor_employment_driver_range_widening_impact_count: int = Field(default=0, ge=0)
    labor_employment_driver_scenario_fork_impact_count: int = Field(default=0, ge=0)
    labor_employment_driver_rate_guideline_review_impact_count: int = Field(default=0, ge=0)
    labor_employment_driver_max_range_widening_factor: float = Field(default=1.0, ge=1.0)
    matter_linking_cluster_report_ref: str | None = None
    matter_linking_cluster_review_outcome_report_ref: str | None = None
    matter_linking_cluster_review_status: (
        Literal[
            "matter_linking_cluster_review_confirmed_for_budget_scope",
            "matter_linking_cluster_review_recorded_pending_followup",
            "blocked_by_matter_linking_cluster_review",
        ]
        | None
    ) = None
    matter_linking_budget_scope_cluster_ids: list[str] = Field(default_factory=list)
    matter_linking_budget_blocking_cluster_count: int = Field(default=0, ge=0)
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
        if self.labor_employment_driver_impact_status and (
            not self.labor_employment_driver_impact_report_ref
        ):
            raise ValueError("L&E driver impact status requires a driver impact report ref")
        if self.labor_employment_driver_block_amount_budget_impact_count > 0:
            if self.status != "failed":
                raise ValueError(
                    "L&E driver amount-budget block impacts must fail the budget precondition gate"
                )
            if self.blocked_state != "labor_employment_driver_impacts_blocked":
                raise ValueError("L&E driver amount-budget blocks require driver blocked state")
            if self.labor_employment_driver_allowed_budget_output != "blocked_amount_budget":
                raise ValueError(
                    "L&E driver amount-budget blocks require blocked amount-budget output"
                )
        if self.blocked_state == "labor_employment_driver_impacts_blocked":
            if not self.labor_employment_driver_impact_report_ref:
                raise ValueError("L&E driver blocked state requires a driver impact report ref")
            if self.labor_employment_driver_block_amount_budget_impact_count == 0:
                raise ValueError("L&E driver blocked state requires at least one block impact")
        if self.matter_linking_cluster_review_status and (
            not self.matter_linking_cluster_report_ref
            or not self.matter_linking_cluster_review_outcome_report_ref
        ):
            raise ValueError("matter-linking review status requires cluster and review refs")
        if self.matter_linking_budget_blocking_cluster_count > 0:
            if self.status != "failed":
                raise ValueError(
                    "matter-linking budget blockers must fail the budget precondition gate"
                )
            if self.blocked_state != "matter_linking_confirmation_blocked":
                raise ValueError("matter-linking blockers require matter-linking blocked state")
        if self.blocked_state == "matter_linking_confirmation_blocked":
            if not self.matter_linking_cluster_report_ref:
                raise ValueError("matter-linking blocked state requires cluster report ref")
            if self.matter_linking_cluster_review_status != (
                "matter_linking_cluster_review_confirmed_for_budget_scope"
            ):
                return self
            if (
                self.matter_linking_budget_blocking_cluster_count == 0
                and len(self.matter_linking_budget_scope_cluster_ids) == 1
            ):
                raise ValueError("confirmed matter-linking budget scope cannot be blocked")
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


DADReviewIssueSeverity = Literal["P0", "P1", "P2", "P3"]
DADReviewIssueClass = Literal[
    "architecture_risk",
    "budget_math_risk",
    "carrier_guideline_risk",
    "authority_boundary_risk",
    "matter_linking_ambiguity",
    "budget_driver_gap",
    "synthetic_data_gap",
    "evidence_gap",
    "data_flow_gap",
    "ui_authority_risk",
    "exception_lake_mapping_gap",
    "learning_loop_gap",
    "test_gap",
    "performance_or_rust_candidate",
    "security_privacy_risk",
    "governance_drift_risk",
    "unknown",
]
DADReviewIssueFixStatus = Literal[
    "observed",
    "planned",
    "in_progress",
    "fixed_pending_validation",
    "fixed_validated",
    "deferred",
    "rejected_duplicate",
]


class DADReviewIssueRecord(StrictModel):
    schema_version: str = "0.1"
    issue_id: str
    issue_version: str = "0.1.0"
    observed_at: str
    source_repo_id: Literal["LawFirm-os-intake"] = "LawFirm-os-intake"
    source_repo_path: str | None = None
    originating_agent: Literal["fable_5", "codex", "claude", "human", "other"]
    review_context: str
    finding_title: str
    severity: DADReviewIssueSeverity
    issue_classes: list[DADReviewIssueClass]
    finding_summary: str
    observable_context: list[str]
    observable_decision_logic: list[str]
    solution_path: list[str]
    fix_status: DADReviewIssueFixStatus
    fix_refs: list[str] = Field(default_factory=list)
    test_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    candidate_exception_labels: list[str]
    applies_when: list[str]
    does_not_apply_when: list[str]
    danger_if_misapplied: str
    suggested_actions: list[str]
    reviewer_notes: list[str] = Field(default_factory=list)
    red_team_notes: list[str] = Field(default_factory=list)
    raw_private_payload_included: Literal[False] = False
    hidden_chain_of_thought_included: Literal[False] = False
    candidate_only: Literal[True] = True
    dad_outbox_required: Literal[True] = True
    dad_review_required_before_promotion: Literal[True] = True
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def review_issue_is_classified_and_bounded(self) -> "DADReviewIssueRecord":
        if not self.issue_classes:
            raise ValueError("DAD review issue requires at least one issue class")
        if "unknown" in self.issue_classes and len(self.issue_classes) > 1:
            raise ValueError("DAD review issue class unknown must stand alone")
        if not self.finding_title.strip():
            raise ValueError("DAD review issue requires a finding title")
        if not self.finding_summary.strip():
            raise ValueError("DAD review issue requires a finding summary")
        required_lists = {
            "observable_context": self.observable_context,
            "observable_decision_logic": self.observable_decision_logic,
            "solution_path": self.solution_path,
            "candidate_exception_labels": self.candidate_exception_labels,
            "applies_when": self.applies_when,
            "does_not_apply_when": self.does_not_apply_when,
            "suggested_actions": self.suggested_actions,
        }
        for field_name, values in required_lists.items():
            if not values or any(not value.strip() for value in values):
                raise ValueError(f"DAD review issue requires non-empty {field_name}")
        if self.fix_status == "fixed_validated" and not self.test_refs:
            raise ValueError("validated DAD review issue requires test refs")
        if not self.danger_if_misapplied.strip():
            raise ValueError("DAD review issue requires danger_if_misapplied")
        return self


class DADReviewIssueOutboxMail(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    mail_id: str
    thread_id: str
    message_type: Literal["governance_notice"] = "governance_notice"
    source_repo: str
    target_repo: Literal["central_only", "dad"] = "central_only"
    created_at: str
    dedupe_key: str
    sensitivity: Literal["internal"] = "internal"
    review_status: Literal["generated_candidate"] = "generated_candidate"
    payload: dict[str, Any]
    evidence: list[str]
    suggested_actions: list[str]
    source_provenance: dict[str, Any]
    public_release: dict[str, Any]


class DADReviewIssueOutboxCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DADReviewIssueOutboxReport(StrictModel):
    schema_version: str = "0.1"
    dad_review_issue_outbox_report_id: str
    status: Literal["dad_review_issue_recorded_to_outbox", "dad_review_issue_duplicate_suppressed"]
    source_issue_id: str
    source_issue_version: str
    severity: DADReviewIssueSeverity
    issue_classes: list[DADReviewIssueClass]
    candidate_exception_labels: list[str]
    dad_mail_id: str
    dad_thread_id: str
    dedupe_key: str
    outbox_ref: str
    outbox_append_performed: bool
    outbox_duplicate_suppressed: bool
    payload_sha256: str
    mail_payload: DADReviewIssueOutboxMail
    checks: list[DADReviewIssueOutboxCheck]
    candidate_only: Literal[True] = True
    dad_pickup_required: Literal[True] = True
    dad_review_required_before_promotion: Literal[True] = True
    raw_private_payload_included: Literal[False] = False
    hidden_chain_of_thought_included: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def outbox_report_flags_are_consistent(self) -> "DADReviewIssueOutboxReport":
        if self.outbox_append_performed == self.outbox_duplicate_suppressed:
            raise ValueError(
                "DAD issue outbox report requires exactly one append/duplicate outcome"
            )
        if (
            self.status == "dad_review_issue_recorded_to_outbox"
            and not self.outbox_append_performed
        ):
            raise ValueError("recorded DAD issue outbox report requires append")
        if (
            self.status == "dad_review_issue_duplicate_suppressed"
            and not self.outbox_duplicate_suppressed
        ):
            raise ValueError("duplicate DAD issue outbox report requires duplicate suppression")
        if not self.checks:
            raise ValueError("DAD issue outbox report requires checks")
        if any(check.status == "failed" for check in self.checks):
            raise ValueError("DAD issue outbox report cannot persist with failed checks")
        return self


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
    identity_key: str | None = None
    severity: Literal["S0", "S1", "S2", "S3"] | None = None
    occurrence_hint: str | None = None
    holdout_origin: bool = False
    raw_payload_included: bool = False
    canonical_promotion_required: bool = True
    target_runtime_repo: Literal["LawFirm-os-exceptions-lake-runtime"] = (
        "LawFirm-os-exceptions-lake-runtime"
    )

    @model_validator(mode="after")
    def exception_learning_metadata(self) -> "ExceptionLakeCandidate":
        if self.identity_key is None:
            subject_ids = sorted(
                {
                    *self.structured_refs,
                    *self.source_inventory_refs,
                    *[
                        f"evidence:{ref.source_id}:{ref.segment_id}:{ref.sha256}"
                        for ref in self.evidence_refs
                    ],
                    *([f"blocked_state:{self.blocked_state}"] if self.blocked_state else []),
                }
            )
            primary_structured_ref = (
                self.structured_refs[0]
                if self.structured_refs
                else (
                    self.source_inventory_refs[0]
                    if self.source_inventory_refs
                    else self.local_event_label
                )
            )
            payload = json.dumps(
                {
                    "issue_family_or_label": self.local_event_label,
                    "canonical_lake_class": self.canonical_lake_class,
                    "primary_structured_ref": primary_structured_ref,
                    "normalized_subject_ids": subject_ids or [self.local_event_label],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            self.identity_key = "sha256:" + sha256(payload.encode("utf-8")).hexdigest()
        if self.severity is None:
            self.severity = _exception_candidate_severity(
                self.local_event_label,
                self.canonical_lake_class,
                self.structured_refs,
                self.blocked_state,
            )
        if self.occurrence_hint is None:
            self.occurrence_hint = "count_recurrence_by_identity_key"
        return self


def _exception_candidate_severity(
    local_event_label: str,
    canonical_lake_class: str,
    structured_refs: list[str],
    blocked_state: str | None,
) -> Literal["S0", "S1", "S2", "S3"]:
    if canonical_lake_class == "authority_conflict_override":
        return "S0"
    if local_event_label == "prompt_injection_source_content" or local_event_label.startswith(
        "prohibited_transition_attempted_"
    ):
        return "S0"
    if local_event_label == "budget_invariant_violation" and any(
        invariant in ref for invariant in ("I1", "I4", "I6", "I14") for ref in structured_refs
    ):
        return "S0"
    if local_event_label in {
        "scenario_policy_invalid",
        "rate_resolution_ambiguous",
        "matter_link_conflict",
        "source_matter_link_conflicting_identifiers",
        "labor_employment_critical_budget_fact_block",
    }:
        return "S1"
    if blocked_state in {
        "budget_insufficient_information",
        "budget_hours_only",
        "budget_driver_unknown",
        "budget_unknowns_require_human_review",
        "carrier_preapproval_required",
    }:
        return "S2"
    if local_event_label in {
        "budget_guideline_or_cap_requires_review",
        "carrier_preapproval_required",
        "budget_actual_cost_variance_requires_review",
        "source_matter_link_ambiguous",
        "matter_link_ambiguity_requires_review",
    }:
        return "S2"
    return "S3"


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

    @model_validator(mode="after")
    def carrier_rejection_learning_counts_match(self) -> "CarrierRejectionLearningReport":
        if self.proposal_count != len(self.proposals):
            raise ValueError("carrier rejection learning proposal_count mismatch")
        proposal_owners = sorted({proposal.target_owner for proposal in self.proposals})
        if self.target_owners != proposal_owners:
            raise ValueError("carrier rejection learning target_owners mismatch")
        return self


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

    @model_validator(mode="after")
    def reviewed_learning_gate_counts_match(self) -> "ReviewedLearningGateReport":
        if self.candidate_count != len(self.candidates):
            raise ValueError("reviewed learning gate candidate_count mismatch")
        typed_total = (
            self.carrier_learning_candidate_count
            + self.budget_revision_candidate_count
            + self.budget_actual_variance_candidate_count
        )
        if self.candidate_count != typed_total:
            raise ValueError("reviewed learning gate typed candidate count mismatch")
        return self


BudgetLearningLoopStatus = Literal[
    "budget_learning_loop_ready_for_review",
    "blocked_by_budget_learning_loop",
]

BudgetLearningLoopLaneState = Literal["passed", "pending", "blocked", "failed"]


class BudgetLearningLoopActualsSummary(StrictModel):
    status: Literal["actuals_not_available", "passed", "variance_review_required"]
    comparison_scope: Literal["phase", "phase_and_code"]
    total_budgeted: float | None = None
    total_actual: float | None = None
    total_variance_amount: float | None = None
    total_variance_percent: float | None = None
    phase_event_count: int = Field(ge=0)
    code_event_count: int = Field(ge=0)
    revision_context_event_count: int = Field(ge=0)
    variance_review_event_count: int = Field(ge=0)
    actuals_without_budget_event_count: int = Field(ge=0)
    missing_actuals_event_count: int = Field(ge=0)
    ledger_entry_count: int = Field(ge=0)
    learning_disposition_candidates: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def actuals_count_partition_matches(self) -> "BudgetLearningLoopActualsSummary":
        if (
            self.ledger_entry_count
            != self.phase_event_count + self.code_event_count + self.revision_context_event_count
        ):
            raise ValueError("budget learning loop actuals ledger count mismatch")
        return self


class BudgetLearningLoopCarrierRejectionSummary(StrictModel):
    reconciliation_status: str
    decision_ledger_status: str
    expected_response_count: int = Field(ge=0)
    reconciled_response_count: int = Field(ge=0)
    missing_response_count: int = Field(ge=0)
    unlinked_notice_count: int = Field(ge=0)
    duplicate_notice_count: int = Field(ge=0)
    parser_failure_count: int = Field(ge=0)
    appeal_result_count: int = Field(ge=0)
    remediation_case_count: int = Field(ge=0)
    decision_ledger_entry_count: int = Field(ge=0)
    pending_decision_event_count: int = Field(ge=0)
    total_disputed_amount: float = Field(ge=0)
    total_recovered_amount: float = Field(ge=0)
    total_write_down_amount: float = Field(ge=0)
    candidate_event_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def carrier_response_partition_matches(self) -> "BudgetLearningLoopCarrierRejectionSummary":
        if (
            self.expected_response_count
            != self.reconciled_response_count + self.missing_response_count
        ):
            raise ValueError("budget learning loop carrier response partition mismatch")
        return self


class BudgetLearningLoopReviewedGateSummary(StrictModel):
    status: str
    candidate_count: int = Field(ge=0)
    carrier_learning_candidate_count: int = Field(ge=0)
    budget_revision_candidate_count: int = Field(ge=0)
    budget_actual_variance_candidate_count: int = Field(ge=0)
    target_learning_loops: list[str] = Field(default_factory=list)
    target_owners: list[str] = Field(default_factory=list)
    reviewed_outcome_required: Literal[True] = True
    shadow_eval_required: Literal[True] = True

    @model_validator(mode="after")
    def learning_candidate_partition_matches(self) -> "BudgetLearningLoopReviewedGateSummary":
        if (
            self.candidate_count
            != self.carrier_learning_candidate_count
            + self.budget_revision_candidate_count
            + self.budget_actual_variance_candidate_count
        ):
            raise ValueError("budget learning loop learning candidate count mismatch")
        return self


class BudgetLearningLoopLane(StrictModel):
    lane_id: str
    label: str
    state: BudgetLearningLoopLaneState
    metric: str
    why: str
    next_action: str
    evidence_refs: list[str]
    candidate_exception_lake_labels: list[str]

    @model_validator(mode="after")
    def lane_is_actionable(self) -> "BudgetLearningLoopLane":
        if not self.evidence_refs:
            raise ValueError("budget learning loop lane requires evidence refs")
        if not self.candidate_exception_lake_labels:
            raise ValueError("budget learning loop lane requires candidate labels")
        if not self.metric.strip() or not self.why.strip() or not self.next_action.strip():
            raise ValueError("budget learning loop lane requires metric, why, and next action")
        return self


class BudgetLearningLoopReport(StrictModel):
    schema_version: str = "0.1"
    budget_learning_loop_report_id: str
    status: BudgetLearningLoopStatus
    run_id: str
    preflight_packet_id: str
    source_budget_actual_comparison_report_ref: str
    source_budget_actual_variance_ledger_report_ref: str
    source_carrier_rejection_reconciliation_report_ref: str
    source_carrier_rejection_decision_ledger_report_ref: str
    source_carrier_rejection_review_packet_ref: str
    source_carrier_rejection_learning_report_ref: str
    source_reviewed_learning_gate_report_ref: str
    budget_proposal_id: str
    comparison_budget_state: Literal["original_proposal", "human_revised_candidate"]
    actuals: BudgetLearningLoopActualsSummary
    carrier_rejections: BudgetLearningLoopCarrierRejectionSummary
    reviewed_learning_gate: BudgetLearningLoopReviewedGateSummary
    lifecycle_lanes: list[BudgetLearningLoopLane]
    red_team_notes: list[str]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    appeal_submission_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def learning_loop_report_is_actionable(self) -> "BudgetLearningLoopReport":
        if len(self.lifecycle_lanes) < 4:
            raise ValueError("budget learning loop requires lifecycle lanes")
        if not self.red_team_notes:
            raise ValueError("budget learning loop requires red team notes")
        if not self.required_next_actions:
            raise ValueError("budget learning loop requires next actions")
        if self.status == "budget_learning_loop_ready_for_review" and (
            self.reviewed_learning_gate.status == "failed"
        ):
            raise ValueError("budget learning loop cannot be ready with failed learning gate")
        return self


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


PRMergeOrderObservedState = Literal["open", "closed", "merged", "not_supplied"]
PRMergeOrderMergeableState = Literal[
    "MERGEABLE",
    "CONFLICTING",
    "UNKNOWN",
    "CLEAN",
    "DIRTY",
    "UNSTABLE",
    "BLOCKED",
    "BEHIND",
    "DRAFT",
    "HAS_HOOKS",
    "not_supplied",
]
PRMergeOrderChecksConclusion = Literal[
    "success",
    "failure",
    "pending",
    "cancelled",
    "skipped",
    "neutral",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
    "not_supplied",
]
PRMergeOrderRole = Literal[
    "fixture_gap_closer",
    "fixture_role_expander",
    "audit_verifier",
    "unknown",
]


class PRMergeOrderCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "warning"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class PRMergeOrderSnapshotItem(StrictModel):
    pr_number: int = Field(gt=0)
    title: str
    pr_url: str | None = None
    head_ref_name: str
    base_ref_name: str
    observed_state: PRMergeOrderObservedState = "open"
    is_draft: bool = True
    mergeable_state: PRMergeOrderMergeableState = "not_supplied"
    checks_conclusion: PRMergeOrderChecksConclusion = "not_supplied"
    status_check_count: int = Field(ge=0)
    successful_status_check_count: int = Field(ge=0)
    changed_files: list[str]
    depth_gap_ids_addressed: list[str] = Field(default_factory=list)
    validation_evidence_refs: list[str] = Field(default_factory=list)
    recommended_sequence_role: PRMergeOrderRole = "unknown"
    notes: list[str] = Field(default_factory=list)
    ready_for_review_marked: Literal[False] = False
    merge_performed: Literal[False] = False
    github_write_performed: Literal[False] = False
    sibling_repo_write_performed: Literal[False] = False
    promotion_authorized: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def pr_merge_order_snapshot_item_has_evidence(
        self,
    ) -> "PRMergeOrderSnapshotItem":
        if not self.title.strip():
            raise ValueError("PR merge-order snapshot item requires title")
        if not self.head_ref_name.strip():
            raise ValueError("PR merge-order snapshot item requires head_ref_name")
        if not self.base_ref_name.strip():
            raise ValueError("PR merge-order snapshot item requires base_ref_name")
        if not self.changed_files:
            raise ValueError("PR merge-order snapshot item requires changed files")
        if any(not path.strip() for path in self.changed_files):
            raise ValueError("PR merge-order changed files must be non-empty strings")
        if self.successful_status_check_count > self.status_check_count:
            raise ValueError("successful status check count cannot exceed status check count")
        return self


class PRMergeOrderSnapshot(StrictModel):
    schema_version: str = "0.1"
    snapshot_id: str
    repository_full_name: str
    base_ref_name: str
    observed_at: str
    source_kind: Literal["manual_github_snapshot", "synthetic_fixture"]
    source_refs: list[str]
    prs: list[PRMergeOrderSnapshotItem]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    manual_github_action_required: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    ready_for_review_marked: Literal[False] = False
    merge_performed: Literal[False] = False
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
    def pr_merge_order_snapshot_is_complete(self) -> "PRMergeOrderSnapshot":
        if not self.snapshot_id.strip():
            raise ValueError("PR merge-order snapshot requires snapshot_id")
        if not self.repository_full_name.strip():
            raise ValueError("PR merge-order snapshot requires repository_full_name")
        if not self.base_ref_name.strip():
            raise ValueError("PR merge-order snapshot requires base_ref_name")
        if not self.observed_at.strip():
            raise ValueError("PR merge-order snapshot requires observed_at")
        if not self.source_refs:
            raise ValueError("PR merge-order snapshot requires source refs")
        if not self.prs:
            raise ValueError("PR merge-order snapshot requires PR items")
        numbers = [pr.pr_number for pr in self.prs]
        if len(numbers) != len(set(numbers)):
            raise ValueError("PR merge-order snapshot contains duplicate PR numbers")
        return self


class PRMergeOrderSharedSurface(StrictModel):
    surface_ref: str
    pr_numbers: list[int]
    risk: Literal["medium", "high"]
    reason: str

    @model_validator(mode="after")
    def pr_merge_order_shared_surface_is_shared(self) -> "PRMergeOrderSharedSurface":
        if not self.surface_ref.strip():
            raise ValueError("PR merge-order shared surface requires surface_ref")
        if len(set(self.pr_numbers)) < 2:
            raise ValueError("PR merge-order shared surface requires at least two PRs")
        if not self.reason.strip():
            raise ValueError("PR merge-order shared surface requires reason")
        return self


class PRMergeOrderRecommendation(StrictModel):
    order_index: int = Field(gt=0)
    pr_number: int = Field(gt=0)
    title: str
    head_ref_name: str
    recommended_sequence_role: PRMergeOrderRole
    recommended_after_pr_numbers: list[int] = Field(default_factory=list)
    shared_surface_refs: list[str] = Field(default_factory=list)
    reason: str
    required_manual_actions: list[str]
    validation_required: list[str]
    red_team_notes: list[str]
    merge_gate: Literal["manual_human_review_required"] = "manual_human_review_required"
    ready_state_gate: Literal["manual_human_review_required"] = "manual_human_review_required"
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    ready_for_review_marked: Literal[False] = False
    merge_performed: Literal[False] = False
    github_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def pr_merge_order_recommendation_is_actionable(
        self,
    ) -> "PRMergeOrderRecommendation":
        if not self.title.strip():
            raise ValueError("PR merge-order recommendation requires title")
        if not self.head_ref_name.strip():
            raise ValueError("PR merge-order recommendation requires head_ref_name")
        if not self.reason.strip():
            raise ValueError("PR merge-order recommendation requires reason")
        if not self.required_manual_actions:
            raise ValueError("PR merge-order recommendation requires manual actions")
        if not self.validation_required:
            raise ValueError("PR merge-order recommendation requires validation gates")
        if not self.red_team_notes:
            raise ValueError("PR merge-order recommendation requires red-team notes")
        return self


class PRMergeOrderReadinessPacket(StrictModel):
    schema_version: str = "0.1"
    packet_id: str
    status: Literal[
        "pr_merge_order_ready_manual_queue_required",
        "blocked_by_pr_merge_order_evidence",
    ]
    source_snapshot_id: str
    source_snapshot_ref: str
    repository_full_name: str
    base_ref_name: str
    strategy: Literal["gap_first_then_depth_audit"]
    pr_count: int = Field(ge=0)
    ready_queue_count: int = Field(ge=0)
    blocked_pr_count: int = Field(ge=0)
    recommended_merge_order_pr_numbers: list[int]
    blocked_pr_numbers: list[int]
    shared_surface_count: int = Field(ge=0)
    high_risk_shared_surface_count: int = Field(ge=0)
    recommendations: list[PRMergeOrderRecommendation]
    shared_surfaces: list[PRMergeOrderSharedSurface]
    checks: list[PRMergeOrderCheck]
    required_next_gates: list[str]
    observed_at: str
    generated_at: str
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    human_review_required: Literal[True] = True
    manual_github_action_required: Literal[True] = True
    not_authorized_for_pr_merge: Literal[True] = True
    not_authorized_for_ready_state_change: Literal[True] = True
    not_authorized_for_external_write: Literal[True] = True
    not_authorized_for_lake_write: Literal[True] = True
    not_authorized_for_sqlite_write: Literal[True] = True
    ready_for_review_marked: Literal[False] = False
    merge_performed: Literal[False] = False
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
    def pr_merge_order_packet_counts_and_gates_match(
        self,
    ) -> "PRMergeOrderReadinessPacket":
        if self.pr_count != self.ready_queue_count + self.blocked_pr_count:
            raise ValueError("PR merge-order ready and blocked counts do not sum to PR count")
        if self.ready_queue_count != len(self.recommendations):
            raise ValueError("PR merge-order ready queue count does not match recommendations")
        if self.blocked_pr_count != len(set(self.blocked_pr_numbers)):
            raise ValueError("PR merge-order blocked count does not match blocked PRs")
        if self.shared_surface_count != len(self.shared_surfaces):
            raise ValueError("PR merge-order shared surface count does not match")
        if self.high_risk_shared_surface_count != sum(
            1 for surface in self.shared_surfaces if surface.risk == "high"
        ):
            raise ValueError("PR merge-order high-risk shared surface count does not match")
        ordered = [
            item.pr_number
            for item in sorted(
                self.recommendations, key=lambda recommendation: recommendation.order_index
            )
        ]
        if self.recommended_merge_order_pr_numbers != ordered:
            raise ValueError("PR merge-order recommendation numbers do not match order")
        failed = [check for check in self.checks if check.status == "failed"]
        if self.status == "pr_merge_order_ready_manual_queue_required" and failed:
            raise ValueError("ready PR merge-order packet cannot have failed checks")
        if self.status == "blocked_by_pr_merge_order_evidence" and not failed:
            raise ValueError("blocked PR merge-order packet requires failed checks")
        required = {
            "manual_pr_review_before_any_merge",
            "manual_github_merge_or_ready_state_change_if_accepted",
            "rebase_and_rerun_ci_after_each_shared_surface_merge",
            "run_full_long_ceiling_validation_after_each_merge",
            "no_automated_github_write",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("PR merge-order packet is missing required gates")
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
    ui_data_bundle_ref: str | None = None
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


class SyntheticQAReviewRunStep(StrictModel):
    step_id: str
    label: str
    status: Literal["passed", "failed"]
    observed_status: str
    artifact_ref: str
    notes: list[str] = Field(default_factory=list)


class SyntheticQAReviewRunReport(StrictModel):
    schema_version: str = "0.1"
    synthetic_qa_review_run_report_id: str
    status: Literal["synthetic_qa_review_run_ready", "blocked_by_synthetic_qa_review_run"]
    run_root_ref: str
    quality_dir_ref: str
    step_count: int = Field(ge=0)
    failed_step_count: int = Field(ge=0)
    steps: list[SyntheticQAReviewRunStep]
    synthetic_qa_bundle_ref: str
    ui_manifest_ref: str
    ui_data_bundle_ref: str
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    budget_amount_output_authorized: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    conflict_conclusion_emitted: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    training_pipeline_created: Literal[False] = False
    calibration_applied: Literal[False] = False
    fixture_files_mutated: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    external_writes_performed: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def synthetic_qa_review_run_counts_and_status_match(
        self,
    ) -> "SyntheticQAReviewRunReport":
        failed_steps = [step for step in self.steps if step.status == "failed"]
        if self.step_count != len(self.steps):
            raise ValueError("synthetic QA review run step count mismatch")
        if self.failed_step_count != len(failed_steps):
            raise ValueError("synthetic QA review run failed step count mismatch")
        if self.status == "synthetic_qa_review_run_ready" and failed_steps:
            raise ValueError("ready synthetic QA review run cannot include failed steps")
        if self.status == "blocked_by_synthetic_qa_review_run" and not failed_steps:
            raise ValueError("blocked synthetic QA review run requires failed steps")
        if not self.required_next_actions:
            raise ValueError("synthetic QA review run requires next actions")
        return self


class RustFixtureBoundaryFailure(StrictModel):
    path: str
    json_path: str
    check: str
    message: str


class RustFixtureBoundaryReport(StrictModel):
    schema_version: str = "0.1"
    checker: Literal["fixture-boundary-checker"]
    status: Literal["passed", "failed"]
    root: str
    ui_bundle_ref: str | None = None
    checked_json_file_count: int = Field(ge=0)
    checked_object_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    failures: list[RustFixtureBoundaryFailure] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_fixture_boundary_counts_and_status_match(self) -> "RustFixtureBoundaryReport":
        if self.failure_count != len(self.failures):
            raise ValueError("Rust fixture boundary failure count mismatch")
        if self.status == "passed" and self.failures:
            raise ValueError("passed Rust fixture boundary report cannot include failures")
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust fixture boundary report requires failures")
        return self


class RustFixtureManifestIdField(StrictModel):
    field: str
    value: str


class RustFixtureManifestFile(StrictModel):
    path: str
    sha256: str
    byte_count: int = Field(ge=0)
    top_level_type: str
    schema_version: str | None = None
    status: str | None = None
    report_kind: str | None = None
    data_origin: str | None = None
    candidate_only: bool | None = None
    synthetic_only: bool | None = None
    external_writes_performed: bool | None = None
    id_fields: list[RustFixtureManifestIdField] = Field(default_factory=list)


class RustFixtureManifestFailure(StrictModel):
    path: str
    check: str
    message: str


class RustFixtureManifestSkippedFile(StrictModel):
    path: str
    reason: str


class RustFixtureManifestReport(StrictModel):
    schema_version: str = "0.1"
    scanner: Literal["fixture-manifest-scanner"]
    status: Literal["passed", "failed"]
    root: str
    manifest_sha256: str
    checked_json_file_count: int = Field(ge=0)
    parsed_json_file_count: int = Field(ge=0)
    parse_error_count: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    skipped_files: list[RustFixtureManifestSkippedFile] = Field(default_factory=list)
    total_byte_count: int = Field(ge=0)
    files: list[RustFixtureManifestFile] = Field(default_factory=list)
    failure_count: int = Field(ge=0)
    failures: list[RustFixtureManifestFailure] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_fixture_manifest_counts_and_status_match(self) -> "RustFixtureManifestReport":
        if not _is_sha256_ref(self.manifest_sha256):
            raise ValueError("Rust fixture manifest hash must be sha256:<64 hex>")
        bad_file_hashes = [file.path for file in self.files if not _is_sha256_ref(file.sha256)]
        if bad_file_hashes:
            raise ValueError("Rust fixture manifest file hashes must be sha256:<64 hex>")
        if self.parsed_json_file_count != len(self.files):
            raise ValueError("Rust fixture manifest parsed file count mismatch")
        if self.failure_count != len(self.failures):
            raise ValueError("Rust fixture manifest failure count mismatch")
        if self.parse_error_count != len(self.failures):
            raise ValueError("Rust fixture manifest parse error count mismatch")
        if self.skipped_file_count != len(self.skipped_files):
            raise ValueError("Rust fixture manifest skipped file count mismatch")
        if self.checked_json_file_count != self.parsed_json_file_count + self.parse_error_count:
            raise ValueError("Rust fixture manifest checked file count mismatch")
        if self.status == "passed" and self.failures:
            raise ValueError("passed Rust fixture manifest report cannot include failures")
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust fixture manifest report requires failures")
        return self


class RustSyntheticIdentityGuardFailure(StrictModel):
    path: str
    json_path: str
    check: str
    value: str
    message: str


class RustSyntheticIdentityGuardReport(StrictModel):
    schema_version: str = "0.1"
    checker: Literal["synthetic-fixture-identity-guard"]
    status: Literal["passed", "failed"]
    root: str
    checked_json_file_count: int = Field(ge=0)
    checked_string_count: int = Field(ge=0)
    checked_email_count: int = Field(ge=0)
    allowed_email_count: int = Field(ge=0)
    blocked_email_count: int = Field(ge=0)
    checked_url_count: int = Field(ge=0)
    allowed_url_count: int = Field(ge=0)
    blocked_url_count: int = Field(ge=0)
    synthetic_flag_violation_count: int = Field(ge=0)
    forbidden_provenance_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    failures: list[RustSyntheticIdentityGuardFailure] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_synthetic_identity_guard_counts_match(
        self,
    ) -> "RustSyntheticIdentityGuardReport":
        if self.checked_email_count != self.allowed_email_count + self.blocked_email_count:
            raise ValueError("Rust synthetic identity guard email count mismatch")
        if self.checked_url_count != self.allowed_url_count + self.blocked_url_count:
            raise ValueError("Rust synthetic identity guard URL count mismatch")
        if self.failure_count != len(self.failures):
            raise ValueError("Rust synthetic identity guard failure count mismatch")
        if self.failure_count != (
            self.blocked_email_count
            + self.blocked_url_count
            + self.synthetic_flag_violation_count
            + self.forbidden_provenance_count
        ):
            raise ValueError("Rust synthetic identity guard failure category count mismatch")
        if self.status == "passed" and self.failures:
            raise ValueError("passed Rust synthetic identity guard report cannot include failures")
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust synthetic identity guard report requires failures")
        return self


class RustFixtureSnapshotCoherenceFailure(StrictModel):
    path: str
    check: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    message: str


class RustFixtureSnapshotCoherenceSkippedFile(StrictModel):
    path: str
    reason: str


class RustFixtureSnapshotCoherenceReport(StrictModel):
    schema_version: str = "0.1"
    checker: Literal["fixture-snapshot-coherence-checker"]
    status: Literal["passed", "failed"]
    root: str
    expected_manifest_ref: str
    expected_manifest_sha256: str
    current_manifest_sha256: str
    expected_file_count: int = Field(ge=0)
    current_file_count: int = Field(ge=0)
    matched_file_count: int = Field(ge=0)
    changed_file_count: int = Field(ge=0)
    missing_file_count: int = Field(ge=0)
    unexpected_file_count: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    skipped_files: list[RustFixtureSnapshotCoherenceSkippedFile] = Field(default_factory=list)
    failure_count: int = Field(ge=0)
    failures: list[RustFixtureSnapshotCoherenceFailure] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_fixture_snapshot_coherence_counts_and_status_match(
        self,
    ) -> "RustFixtureSnapshotCoherenceReport":
        if not _is_sha256_ref(self.expected_manifest_sha256):
            raise ValueError("Rust fixture expected manifest hash must be sha256:<64 hex>")
        if not _is_sha256_ref(self.current_manifest_sha256):
            raise ValueError("Rust fixture current manifest hash must be sha256:<64 hex>")
        for failure in self.failures:
            if failure.expected_sha256 is not None and not _is_sha256_ref(failure.expected_sha256):
                raise ValueError("Rust fixture expected failure hash must be sha256:<64 hex>")
            if failure.actual_sha256 is not None and not _is_sha256_ref(failure.actual_sha256):
                raise ValueError("Rust fixture actual failure hash must be sha256:<64 hex>")
        if self.failure_count != len(self.failures):
            raise ValueError("Rust fixture snapshot coherence failure count mismatch")
        if self.skipped_file_count != len(self.skipped_files):
            raise ValueError("Rust fixture snapshot coherence skipped file count mismatch")
        if self.expected_file_count != (
            self.matched_file_count + self.changed_file_count + self.missing_file_count
        ):
            raise ValueError("Rust fixture snapshot coherence expected file count mismatch")
        if self.current_file_count != (
            self.matched_file_count + self.changed_file_count + self.unexpected_file_count
        ):
            raise ValueError("Rust fixture snapshot coherence current file count mismatch")
        if self.failure_count != (
            self.changed_file_count + self.missing_file_count + self.unexpected_file_count
        ):
            raise ValueError("Rust fixture snapshot coherence diff count mismatch")
        if self.status == "passed" and self.failures:
            raise ValueError(
                "passed Rust fixture snapshot coherence report cannot include failures"
            )
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust fixture snapshot coherence report requires failures")
        return self


class RustUIBundleSourceHashDetail(StrictModel):
    detail_report_id: str
    report_kind: str
    file_name: str
    artifact_ref: str | None = None
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    resolved_path: str | None = None
    resolution_strategy: str | None = None
    status: Literal[
        "matched",
        "hash_mismatch",
        "source_missing",
        "invalid_source_hash",
        "skipped_not_present",
    ]

    @model_validator(mode="after")
    def rust_ui_bundle_detail_hashes_match_status(self) -> "RustUIBundleSourceHashDetail":
        if self.expected_sha256 is not None and not _is_sha256_ref(self.expected_sha256):
            raise ValueError("Rust UI bundle expected hash must be sha256:<64 hex>")
        if self.actual_sha256 is not None and not _is_sha256_ref(self.actual_sha256):
            raise ValueError("Rust UI bundle actual hash must be sha256:<64 hex>")
        if self.status in {"matched", "hash_mismatch"} and not (
            self.actual_sha256 and self.resolved_path
        ):
            raise ValueError("checked UI bundle detail requires actual hash and resolved path")
        if self.status == "matched" and self.expected_sha256 != self.actual_sha256:
            raise ValueError("matched UI bundle detail requires equal expected and actual hashes")
        if self.status == "hash_mismatch" and self.expected_sha256 == self.actual_sha256:
            raise ValueError("mismatched UI bundle detail requires different hashes")
        return self


class RustUIBundleSourceHashFailure(StrictModel):
    detail_report_id: str | None = None
    file_name: str
    check: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    message: str


class RustUIBundleSourceHashReport(StrictModel):
    schema_version: str = "0.1"
    checker: Literal["ui-bundle-source-hash-checker"]
    status: Literal["passed", "failed"]
    root: str
    bundle_ref: str
    detail_report_count: int = Field(ge=0)
    present_detail_report_count: int = Field(ge=0)
    checked_detail_report_count: int = Field(ge=0)
    matched_detail_report_count: int = Field(ge=0)
    hash_mismatch_count: int = Field(ge=0)
    missing_source_file_count: int = Field(ge=0)
    invalid_source_hash_count: int = Field(ge=0)
    skipped_detail_report_count: int = Field(ge=0)
    checker_error_count: int = Field(ge=0)
    details: list[RustUIBundleSourceHashDetail] = Field(default_factory=list)
    failure_count: int = Field(ge=0)
    failures: list[RustUIBundleSourceHashFailure] = Field(default_factory=list)
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False

    @model_validator(mode="after")
    def rust_ui_bundle_source_hash_counts_and_status_match(
        self,
    ) -> "RustUIBundleSourceHashReport":
        if self.detail_report_count != len(self.details):
            raise ValueError("Rust UI bundle source-hash detail count mismatch")
        if self.skipped_detail_report_count != len(
            [detail for detail in self.details if detail.status == "skipped_not_present"]
        ):
            raise ValueError("Rust UI bundle source-hash skipped count mismatch")
        if self.matched_detail_report_count != len(
            [detail for detail in self.details if detail.status == "matched"]
        ):
            raise ValueError("Rust UI bundle source-hash matched count mismatch")
        if self.hash_mismatch_count != len(
            [detail for detail in self.details if detail.status == "hash_mismatch"]
        ):
            raise ValueError("Rust UI bundle source-hash mismatch count mismatch")
        if self.missing_source_file_count != len(
            [detail for detail in self.details if detail.status == "source_missing"]
        ):
            raise ValueError("Rust UI bundle source-hash missing count mismatch")
        if self.invalid_source_hash_count != len(
            [detail for detail in self.details if detail.status == "invalid_source_hash"]
        ):
            raise ValueError("Rust UI bundle source-hash invalid hash count mismatch")
        if self.checked_detail_report_count != (
            self.matched_detail_report_count + self.hash_mismatch_count
        ):
            raise ValueError("Rust UI bundle source-hash checked count mismatch")
        if self.present_detail_report_count != (
            self.checked_detail_report_count
            + self.missing_source_file_count
            + self.invalid_source_hash_count
        ):
            raise ValueError("Rust UI bundle source-hash present count mismatch")
        if self.detail_report_count != self.present_detail_report_count + (
            self.skipped_detail_report_count
        ):
            raise ValueError("Rust UI bundle source-hash detail/present count mismatch")
        if self.failure_count != len(self.failures):
            raise ValueError("Rust UI bundle source-hash failure count mismatch")
        if self.failure_count != (
            self.hash_mismatch_count
            + self.missing_source_file_count
            + self.invalid_source_hash_count
            + self.checker_error_count
        ):
            raise ValueError("Rust UI bundle source-hash failure category count mismatch")
        for failure in self.failures:
            if failure.expected_sha256 is not None and not _is_sha256_ref(failure.expected_sha256):
                raise ValueError("Rust UI bundle failure expected hash must be sha256:<64 hex>")
            if failure.actual_sha256 is not None and not _is_sha256_ref(failure.actual_sha256):
                raise ValueError("Rust UI bundle failure actual hash must be sha256:<64 hex>")
        if self.status == "passed" and self.failures:
            raise ValueError("passed Rust UI bundle source-hash report cannot include failures")
        if self.status == "failed" and not self.failures:
            raise ValueError("failed Rust UI bundle source-hash report requires failures")
        return self


UIDemoFixtureRefreshStatus = Literal[
    "ui_demo_fixture_refresh_verified",
    "ui_demo_fixture_refresh_failed",
    "ui_demo_fixture_refresh_blocked_write_flag_required",
]

UIDemoFixtureRefreshDetailStatus = Literal[
    "updated",
    "unchanged",
    "missing_source",
    "skipped_not_present",
    "deferred_manifest",
]


class UIDemoFixtureRefreshDetail(StrictModel):
    detail_report_id: str
    report_kind: str
    file_name: str
    old_source_sha256: str | None = None
    new_source_sha256: str | None = None
    resolved_path: str | None = None
    resolution_strategy: str | None = None
    status: UIDemoFixtureRefreshDetailStatus

    @model_validator(mode="after")
    def ui_demo_fixture_refresh_detail_hashes_match_status(
        self,
    ) -> "UIDemoFixtureRefreshDetail":
        if self.new_source_sha256 is not None and not _is_sha256_ref(self.new_source_sha256):
            raise ValueError("UI demo fixture new source hash must be sha256:<64 hex>")
        if self.status in {"updated", "unchanged"} and not (
            self.new_source_sha256 and self.resolved_path and self.resolution_strategy
        ):
            raise ValueError("refreshed UI demo detail needs new hash and resolved source")
        if self.status == "updated" and self.old_source_sha256 == self.new_source_sha256:
            raise ValueError("updated UI demo detail requires changed hash")
        if self.status == "unchanged" and self.old_source_sha256 != self.new_source_sha256:
            raise ValueError("unchanged UI demo detail requires equal hashes")
        return self


class UIDemoFixtureRefreshReport(StrictModel):
    schema_version: str = "0.1"
    status: UIDemoFixtureRefreshStatus
    fixtures_root_ref: str
    ui_bundle_ref: str
    manifest_ref: str
    old_ui_review_data_bundle_id: str | None = None
    new_ui_review_data_bundle_id: str | None = None
    old_ui_bundle_sha256: str | None = None
    new_ui_bundle_sha256: str | None = None
    old_manifest_sha256: str | None = None
    new_manifest_sha256: str | None = None
    detail_report_count: int = Field(ge=0)
    source_hash_update_count: int = Field(ge=0)
    source_hash_unchanged_count: int = Field(ge=0)
    missing_source_count: int = Field(ge=0)
    invalid_existing_hash_count: int = Field(ge=0)
    manifest_status: str
    source_hash_gate_status: str
    snapshot_gate_status: str
    local_fixture_updates_performed: bool = False
    details: list[UIDemoFixtureRefreshDetail] = Field(default_factory=list)
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def ui_demo_fixture_refresh_counts_and_status_match(
        self,
    ) -> "UIDemoFixtureRefreshReport":
        if self.detail_report_count != len(self.details):
            raise ValueError("UI demo fixture refresh detail count mismatch")
        if self.source_hash_update_count != len(
            [detail for detail in self.details if detail.status == "updated"]
        ):
            raise ValueError("UI demo fixture refresh update count mismatch")
        if self.source_hash_unchanged_count != len(
            [detail for detail in self.details if detail.status == "unchanged"]
        ):
            raise ValueError("UI demo fixture refresh unchanged count mismatch")
        if self.missing_source_count != len(
            [detail for detail in self.details if detail.status == "missing_source"]
        ):
            raise ValueError("UI demo fixture refresh missing source count mismatch")
        for hash_value in [
            self.old_ui_bundle_sha256,
            self.new_ui_bundle_sha256,
            self.old_manifest_sha256,
            self.new_manifest_sha256,
        ]:
            if hash_value is not None and not _is_sha256_ref(hash_value):
                raise ValueError("UI demo fixture refresh hashes must be sha256:<64 hex>")
        if self.status == "ui_demo_fixture_refresh_verified":
            if (
                self.missing_source_count
                or self.manifest_status != "passed"
                or self.source_hash_gate_status != "passed"
                or self.snapshot_gate_status != "passed"
                or not self.local_fixture_updates_performed
            ):
                raise ValueError("verified UI demo fixture refresh requires passed gates")
        if self.status == "ui_demo_fixture_refresh_blocked_write_flag_required":
            if self.local_fixture_updates_performed or self.details:
                raise ValueError("blocked UI demo fixture refresh cannot mutate or include details")
        if not self.required_next_actions:
            raise ValueError("UI demo fixture refresh requires next actions")
        return self


UIDemoFixturePromotionStatus = Literal[
    "ui_demo_fixture_promotion_verified",
    "ui_demo_fixture_promotion_failed",
    "ui_demo_fixture_promotion_blocked_write_flag_required",
]

UIDemoFixturePromotionItemStatus = Literal[
    "promoted",
    "unchanged",
    "generated_wrapper",
    "missing_source",
    "ambiguous_source",
    "blocked_side_effect",
]


class UIDemoFixturePromotionItem(StrictModel):
    fixture_name: str
    source_ref: str | None = None
    target_ref: str
    old_target_sha256: str | None = None
    new_target_sha256: str | None = None
    source_sha256: str | None = None
    sanitized_replacement_count: int = Field(ge=0)
    forbidden_run_root_leak_count: int = Field(ge=0)
    blocked_side_effect_count: int = Field(ge=0)
    status: UIDemoFixturePromotionItemStatus
    message: str

    @model_validator(mode="after")
    def ui_demo_fixture_promotion_item_is_coherent(
        self,
    ) -> "UIDemoFixturePromotionItem":
        for hash_value in [self.old_target_sha256, self.new_target_sha256, self.source_sha256]:
            if hash_value is not None and not _is_sha256_ref(hash_value):
                raise ValueError("UI demo fixture promotion hashes must be sha256:<64 hex>")
        if self.status in {"promoted", "unchanged", "generated_wrapper"}:
            if not self.new_target_sha256:
                raise ValueError("successful UI demo fixture promotion item requires new hash")
            if self.forbidden_run_root_leak_count or self.blocked_side_effect_count:
                raise ValueError("successful UI demo fixture promotion item cannot include leaks")
        if self.status == "unchanged" and self.old_target_sha256 != self.new_target_sha256:
            raise ValueError("unchanged UI demo fixture promotion item requires equal hashes")
        if self.status == "promoted" and self.old_target_sha256 == self.new_target_sha256:
            raise ValueError("promoted UI demo fixture promotion item requires changed hash")
        if self.status == "missing_source" and self.source_ref is None:
            raise ValueError("missing source promotion item requires source ref")
        return self


class UIDemoFixturePromotionReport(StrictModel):
    schema_version: str = "0.1"
    status: UIDemoFixturePromotionStatus
    run_root_ref: str
    sanitized_run_root_ref: Literal["<demo-run-root>"] = "<demo-run-root>"
    fixtures_root_ref: str
    promotion_item_count: int = Field(ge=0)
    promoted_item_count: int = Field(ge=0)
    unchanged_item_count: int = Field(ge=0)
    generated_wrapper_count: int = Field(ge=0)
    missing_source_count: int = Field(ge=0)
    ambiguous_source_count: int = Field(ge=0)
    blocked_side_effect_count: int = Field(ge=0)
    sanitized_replacement_count: int = Field(ge=0)
    forbidden_run_root_leak_count: int = Field(ge=0)
    rust_boundary_status: str
    wrapper_refresh_status: str
    manifest_status: str
    source_hash_gate_status: str
    snapshot_gate_status: str
    wrapper_refresh_report_ref: str | None = None
    old_ui_review_data_bundle_id: str | None = None
    new_ui_review_data_bundle_id: str | None = None
    local_fixture_updates_performed: bool = False
    rollback_performed: bool = False
    items: list[UIDemoFixturePromotionItem] = Field(default_factory=list)
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def ui_demo_fixture_promotion_counts_and_status_match(
        self,
    ) -> "UIDemoFixturePromotionReport":
        if self.promotion_item_count != len(self.items):
            raise ValueError("UI demo fixture promotion item count mismatch")
        status_counts = {
            status: len([item for item in self.items if item.status == status])
            for status in [
                "promoted",
                "unchanged",
                "generated_wrapper",
                "missing_source",
                "ambiguous_source",
            ]
        }
        if self.promoted_item_count != status_counts["promoted"]:
            raise ValueError("UI demo fixture promotion promoted count mismatch")
        if self.unchanged_item_count != status_counts["unchanged"]:
            raise ValueError("UI demo fixture promotion unchanged count mismatch")
        if self.generated_wrapper_count != status_counts["generated_wrapper"]:
            raise ValueError("UI demo fixture promotion wrapper count mismatch")
        if self.missing_source_count != status_counts["missing_source"]:
            raise ValueError("UI demo fixture promotion missing-source count mismatch")
        if self.ambiguous_source_count != status_counts["ambiguous_source"]:
            raise ValueError("UI demo fixture promotion ambiguous-source count mismatch")
        if self.blocked_side_effect_count != sum(
            item.blocked_side_effect_count for item in self.items
        ):
            raise ValueError("UI demo fixture promotion side-effect count mismatch")
        if self.sanitized_replacement_count != sum(
            item.sanitized_replacement_count for item in self.items
        ):
            raise ValueError("UI demo fixture promotion sanitized count mismatch")
        if self.forbidden_run_root_leak_count != sum(
            item.forbidden_run_root_leak_count for item in self.items
        ):
            raise ValueError("UI demo fixture promotion leak count mismatch")
        if self.status == "ui_demo_fixture_promotion_verified":
            if (
                self.missing_source_count
                or self.ambiguous_source_count
                or self.blocked_side_effect_count
                or self.forbidden_run_root_leak_count
                or self.rust_boundary_status != "passed"
                or self.wrapper_refresh_status != "ui_demo_fixture_refresh_verified"
                or self.manifest_status != "passed"
                or self.source_hash_gate_status != "passed"
                or self.snapshot_gate_status != "passed"
                or not self.local_fixture_updates_performed
                or self.rollback_performed
            ):
                raise ValueError("verified UI demo fixture promotion requires passed gates")
        if self.status == "ui_demo_fixture_promotion_blocked_write_flag_required":
            if self.local_fixture_updates_performed or self.items:
                raise ValueError("blocked UI demo fixture promotion cannot mutate or include items")
        if not self.required_next_actions:
            raise ValueError("UI demo fixture promotion requires next actions")
        return self


UIDemoQARecipeStatus = Literal[
    "ui_demo_qa_recipe_verified",
    "ui_demo_qa_recipe_failed",
    "ui_demo_qa_recipe_blocked_write_flag_required",
]

UIDemoQARecipeStepStatus = Literal["passed", "failed", "blocked"]


class UIDemoQARecipeStep(StrictModel):
    step_id: str
    label: str
    status: UIDemoQARecipeStepStatus
    observed_status: str
    artifact_ref: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ui_demo_qa_recipe_step_is_coherent(self) -> "UIDemoQARecipeStep":
        if not self.step_id.strip():
            raise ValueError("UI demo QA recipe step requires step_id")
        if not self.label.strip():
            raise ValueError("UI demo QA recipe step requires label")
        if not self.observed_status.strip():
            raise ValueError("UI demo QA recipe step requires observed_status")
        if self.status == "passed" and not self.artifact_ref:
            raise ValueError("passed UI demo QA recipe step requires artifact_ref")
        return self


class UIDemoQARecipeReport(StrictModel):
    schema_version: str = "0.1"
    ui_demo_qa_recipe_report_id: str
    status: UIDemoQARecipeStatus
    out_dir_ref: str
    final_run_root_ref: str
    initial_run_root_ref: str
    fixtures_root_ref: str
    temp_fixtures_root_ref: str
    validation_mode: Literal["provided", "ran"]
    validation_suite_evidence_ref: str
    validation_suite_status: str
    validation_exact_step_order_confirmed: bool
    validation_worktree_clean_confirmed: bool
    initial_synthetic_qa_status: str
    temp_promotion_status: str
    rust_boundary_status: str
    rust_manifest_status: str
    rust_boundary_root_matches_temp_fixtures: bool
    rust_manifest_root_matches_temp_fixtures: bool
    final_synthetic_qa_status: str
    final_ui_bundle_status: str
    final_poc_qa_triage_status: str
    final_promotion_status: str
    final_promotion_report_ref: str | None = None
    final_ui_review_data_bundle_ref: str | None = None
    final_poc_qa_triage_ref: str | None = None
    step_count: int = Field(ge=0)
    failed_step_count: int = Field(ge=0)
    blocked_step_count: int = Field(ge=0)
    temp_fixture_updates_performed: bool = False
    local_fixture_updates_performed: bool = False
    rollback_performed: bool = False
    steps: list[UIDemoQARecipeStep]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def ui_demo_qa_recipe_counts_and_status_match(self) -> "UIDemoQARecipeReport":
        failed = [step for step in self.steps if step.status == "failed"]
        blocked = [step for step in self.steps if step.status == "blocked"]
        if self.step_count != len(self.steps):
            raise ValueError("UI demo QA recipe step count mismatch")
        if self.failed_step_count != len(failed):
            raise ValueError("UI demo QA recipe failed step count mismatch")
        if self.blocked_step_count != len(blocked):
            raise ValueError("UI demo QA recipe blocked step count mismatch")
        if self.status == "ui_demo_qa_recipe_verified":
            if (
                failed
                or blocked
                or self.validation_suite_status != "validation_suite_passed"
                or not self.validation_exact_step_order_confirmed
                or not self.validation_worktree_clean_confirmed
                or self.initial_synthetic_qa_status != "synthetic_qa_review_run_ready"
                or self.temp_promotion_status != "ui_demo_fixture_promotion_verified"
                or self.rust_boundary_status != "passed"
                or self.rust_manifest_status != "passed"
                or not self.rust_boundary_root_matches_temp_fixtures
                or not self.rust_manifest_root_matches_temp_fixtures
                or self.final_synthetic_qa_status != "synthetic_qa_review_run_ready"
                or self.final_ui_bundle_status != "ready_for_review"
                or self.final_poc_qa_triage_status != "poc_qa_ready_for_review"
                or self.final_promotion_status != "ui_demo_fixture_promotion_verified"
                or not self.temp_fixture_updates_performed
                or not self.local_fixture_updates_performed
                or self.rollback_performed
            ):
                raise ValueError("verified UI demo QA recipe requires passed gates")
        if self.status == "ui_demo_qa_recipe_blocked_write_flag_required":
            if (
                self.local_fixture_updates_performed
                or self.final_promotion_status
                != "ui_demo_fixture_promotion_blocked_write_flag_required"
            ):
                raise ValueError("blocked UI demo QA recipe cannot update checked fixtures")
        if self.status == "ui_demo_qa_recipe_failed" and not (failed or blocked):
            raise ValueError("failed UI demo QA recipe requires failed or blocked steps")
        if not self.steps:
            raise ValueError("UI demo QA recipe requires steps")
        if not self.required_next_actions:
            raise ValueError("UI demo QA recipe requires next actions")
        return self


UIDemoQARecipeFixtureRefreshStatus = Literal[
    "ui_demo_qa_recipe_fixture_refresh_verified",
    "ui_demo_qa_recipe_fixture_refresh_failed",
    "ui_demo_qa_recipe_fixture_refresh_blocked_write_flag_required",
]


class UIDemoQARecipeFixtureRefreshReport(StrictModel):
    schema_version: str = "0.1"
    ui_demo_qa_recipe_fixture_refresh_report_id: str
    status: UIDemoQARecipeFixtureRefreshStatus
    source_recipe_report_ref: str
    source_recipe_status: str
    fixtures_root_ref: str
    target_fixture_ref: str
    old_target_sha256: str | None = None
    new_target_sha256: str | None = None
    source_sha256: str | None = None
    sanitized_replacement_count: int = Field(ge=0)
    forbidden_path_leak_count: int = Field(ge=0)
    blocked_side_effect_count: int = Field(ge=0)
    wrapper_refresh_status: str
    wrapper_refresh_report_ref: str | None = None
    manifest_status: str
    source_hash_gate_status: str
    snapshot_gate_status: str
    local_fixture_update_performed: bool
    rollback_performed: bool
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    external_writes_performed: Literal[False] = False
    lake_write_performed: Literal[False] = False
    sqlite_write_performed: Literal[False] = False
    budget_submission_authorized: Literal[False] = False
    matter_opening_authorized: Literal[False] = False
    silent_learning_performed: Literal[False] = False
    generated_at: str

    @model_validator(mode="after")
    def ui_demo_qa_recipe_fixture_refresh_is_coherent(
        self,
    ) -> "UIDemoQARecipeFixtureRefreshReport":
        if self.status == "ui_demo_qa_recipe_fixture_refresh_verified":
            if (
                self.source_recipe_status != "ui_demo_qa_recipe_verified"
                or not self.source_sha256
                or not self.new_target_sha256
                or self.forbidden_path_leak_count
                or self.blocked_side_effect_count
                or self.wrapper_refresh_status != "ui_demo_fixture_refresh_verified"
                or self.manifest_status != "passed"
                or self.source_hash_gate_status != "passed"
                or self.snapshot_gate_status != "passed"
                or not self.local_fixture_update_performed
                or self.rollback_performed
            ):
                raise ValueError("verified recipe fixture refresh requires passed gates")
        if self.status == "ui_demo_qa_recipe_fixture_refresh_blocked_write_flag_required":
            if self.local_fixture_update_performed or self.new_target_sha256:
                raise ValueError("blocked recipe fixture refresh cannot update fixture")
        if self.status == "ui_demo_qa_recipe_fixture_refresh_failed":
            if (
                self.forbidden_path_leak_count == 0
                and self.blocked_side_effect_count == 0
                and self.wrapper_refresh_status == "ui_demo_fixture_refresh_verified"
                and not self.rollback_performed
            ):
                raise ValueError("failed recipe fixture refresh needs a failed gate or rollback")
        if not self.required_next_actions:
            raise ValueError("recipe fixture refresh requires next actions")
        return self


def _is_sha256_ref(value: str) -> bool:
    if len(value) != len("sha256:") + 64 or not value.startswith("sha256:"):
        return False
    return all(character in "0123456789abcdef" for character in value[len("sha256:") :])


SyntheticConfidenceSummaryItemState = Literal[
    "ready_for_review",
    "pending_review",
    "blocked",
    "failed",
]


class SyntheticConfidenceSummaryItem(StrictModel):
    item_id: str
    label: str
    owner: str
    state: SyntheticConfidenceSummaryItemState
    evidence_refs: list[str]
    notes: list[str]
    no_write_boundary_confirmed: Literal[True] = True

    @model_validator(mode="after")
    def synthetic_confidence_summary_item_is_actionable(
        self,
    ) -> "SyntheticConfidenceSummaryItem":
        if not self.evidence_refs:
            raise ValueError("synthetic confidence summary item requires evidence refs")
        if not self.notes:
            raise ValueError("synthetic confidence summary item requires notes")
        return self


class SyntheticConfidenceSummaryReport(StrictModel):
    schema_version: str = "0.1"
    synthetic_confidence_summary_report_id: str
    status: Literal[
        "synthetic_confidence_summary_ready_for_review",
        "blocked_by_synthetic_confidence_summary",
        "failed_synthetic_confidence_summary_boundary",
    ]
    testing_readiness_state: Literal[
        "synthetic_qa_ready_pending_review",
        "blocked_missing_or_failed_evidence",
        "failed_side_effect_boundary",
    ]
    source_synthetic_qa_review_run_ref: str
    source_synthetic_qa_review_run_report_id: str
    source_synthetic_qa_review_run_status: str
    source_synthetic_qa_bundle_ref: str
    source_synthetic_qa_bundle_report_id: str
    source_synthetic_qa_bundle_status: str
    source_ui_manifest_ref: str
    source_ui_manifest_id: str
    source_ui_manifest_overall_status: str
    source_ui_review_data_bundle_ref: str
    source_ui_review_data_bundle_id: str
    source_ui_review_data_bundle_status: str
    qa_step_count: int = Field(ge=0)
    qa_passed_step_count: int = Field(ge=0)
    qa_failed_step_count: int = Field(ge=0)
    qa_artifact_count: int = Field(ge=0)
    qa_missing_required_artifact_count: int = Field(ge=0)
    qa_blocked_artifact_count: int = Field(ge=0)
    qa_pending_artifact_count: int = Field(ge=0)
    qa_failed_artifact_count: int = Field(ge=0)
    ui_detail_report_count: int = Field(ge=0)
    ui_present_detail_report_count: int = Field(ge=0)
    ui_missing_required_detail_report_count: int = Field(ge=0)
    ui_external_write_report_count: int = Field(ge=0)
    quality_gate_count: int = Field(ge=0)
    quality_gate_passed_count: int = Field(ge=0)
    quality_gate_pending_count: int = Field(ge=0)
    quality_gate_blocked_count: int = Field(ge=0)
    quality_gate_failed_count: int = Field(ge=0)
    readiness_item_count: int = Field(ge=0)
    readiness_items: list[SyntheticConfidenceSummaryItem]
    top_blockers: list[str] = Field(default_factory=list)
    display_banner: dict[str, Any]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def synthetic_confidence_summary_counts_and_status_match(
        self,
    ) -> "SyntheticConfidenceSummaryReport":
        if self.qa_step_count != self.qa_passed_step_count + self.qa_failed_step_count:
            raise ValueError("synthetic confidence QA step counts do not match")
        if self.readiness_item_count != len(self.readiness_items):
            raise ValueError("synthetic confidence readiness item count does not match")
        if self.ui_present_detail_report_count > self.ui_detail_report_count:
            raise ValueError("synthetic confidence UI present count cannot exceed detail count")
        if (
            self.quality_gate_count
            != self.quality_gate_passed_count
            + self.quality_gate_pending_count
            + self.quality_gate_blocked_count
            + self.quality_gate_failed_count
        ):
            raise ValueError("synthetic confidence quality gate counts do not match")
        failed_or_blocked_items = [
            item for item in self.readiness_items if item.state in {"failed", "blocked"}
        ]
        side_effect_failure = (
            self.ui_external_write_report_count > 0
            or self.external_writes_performed
            or self.lake_write_performed
            or self.sqlite_write_performed
            or self.silent_learning_performed
        )
        evidence_blocked = (
            self.qa_failed_step_count > 0
            or self.qa_missing_required_artifact_count > 0
            or self.qa_blocked_artifact_count > 0
            or self.qa_failed_artifact_count > 0
            or self.ui_missing_required_detail_report_count > 0
            or self.quality_gate_blocked_count > 0
            or self.quality_gate_failed_count > 0
            or bool(failed_or_blocked_items)
        )
        if side_effect_failure and self.status != "failed_synthetic_confidence_summary_boundary":
            raise ValueError("side-effect confidence summary failure must use failed status")
        if side_effect_failure and self.testing_readiness_state != "failed_side_effect_boundary":
            raise ValueError("side-effect confidence summary failure must use failed state")
        if self.status == "synthetic_confidence_summary_ready_for_review" and (
            side_effect_failure or evidence_blocked
        ):
            raise ValueError("ready confidence summary cannot have blocked evidence")
        if self.status == "blocked_by_synthetic_confidence_summary" and not evidence_blocked:
            raise ValueError("blocked confidence summary requires blocked evidence")
        if self.testing_readiness_state == "synthetic_qa_ready_pending_review" and (
            side_effect_failure or evidence_blocked
        ):
            raise ValueError("ready pending review state cannot have blocked evidence")
        if not self.display_banner:
            raise ValueError("synthetic confidence summary requires display banner")
        for key in [
            "candidate_only",
            "synthetic_only",
            "local_json_only",
            "not_production_ready",
            "human_review_required",
            "budget_submission_authorized",
            "matter_opening_authorized",
            "lake_write_performed",
            "sqlite_write_performed",
        ]:
            if key not in self.display_banner:
                raise ValueError(f"synthetic confidence display banner missing {key}")
        if not self.required_next_actions:
            raise ValueError("synthetic confidence summary requires next actions")
        return self


ValidationSuiteStepStatus = Literal["passed", "failed", "timed_out"]


class ValidationSuiteStepEvidence(StrictModel):
    step_id: str
    command_key: str
    command: list[str]
    command_display: str
    status: ValidationSuiteStepStatus
    return_code: int | None = None
    timeout_seconds: int = Field(ge=1)
    duration_seconds: float = Field(ge=0)
    started_at: str
    completed_at: str
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validation_step_status_is_coherent(self) -> "ValidationSuiteStepEvidence":
        if not self.step_id.strip():
            raise ValueError("validation suite step requires step_id")
        if not self.command_key.strip():
            raise ValueError("validation suite step requires command_key")
        if not self.command:
            raise ValueError("validation suite step requires command")
        if not self.command_display.strip():
            raise ValueError("validation suite step requires command_display")
        if not self.evidence_refs:
            raise ValueError("validation suite step requires evidence refs")
        if self.status == "passed" and self.return_code != 0:
            raise ValueError("passed validation suite step must have return_code 0")
        if self.status == "failed" and (self.return_code is None or self.return_code == 0):
            raise ValueError("failed validation suite step must have nonzero return_code")
        if self.status == "timed_out" and self.return_code != 124:
            raise ValueError("timed-out validation suite step must use return_code 124")
        return self


class ValidationSuiteEvidenceReport(StrictModel):
    schema_version: str = "0.1"
    validation_suite_evidence_report_id: str
    status: Literal["validation_suite_passed", "blocked_by_validation_suite"]
    policy_id: str
    policy_version: str
    policy_ref: str
    repo_root_ref: str
    git_commit: str | None = None
    working_tree_dirty: bool
    step_count: int = Field(ge=0)
    passed_step_count: int = Field(ge=0)
    failed_step_count: int = Field(ge=0)
    timed_out_step_count: int = Field(ge=0)
    steps: list[ValidationSuiteStepEvidence]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
    human_review_required: Literal[True] = True
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
    def validation_suite_counts_and_status_match(self) -> "ValidationSuiteEvidenceReport":
        passed = [step for step in self.steps if step.status == "passed"]
        failed = [step for step in self.steps if step.status == "failed"]
        timed_out = [step for step in self.steps if step.status == "timed_out"]
        if self.step_count != len(self.steps):
            raise ValueError("validation suite step count mismatch")
        if not self.steps:
            raise ValueError("validation suite evidence report requires steps")
        if self.passed_step_count != len(passed):
            raise ValueError("validation suite passed count mismatch")
        if self.failed_step_count != len(failed):
            raise ValueError("validation suite failed count mismatch")
        if self.timed_out_step_count != len(timed_out):
            raise ValueError("validation suite timed-out count mismatch")
        if self.status == "validation_suite_passed" and (failed or timed_out):
            raise ValueError("passed validation suite report cannot include failed steps")
        if self.status == "blocked_by_validation_suite" and not (failed or timed_out):
            raise ValueError("blocked validation suite report requires failed or timed-out steps")
        if self.status == "validation_suite_passed":
            required_step_ids = {
                "validate_repo",
                "export_schemas",
                "ruff_check",
                "ruff_format_check",
                "full_pytest",
                "smoke_demo",
                "validate_repo_final",
            }
            passed_step_ids = {step.step_id for step in passed}
            missing = sorted(required_step_ids - passed_step_ids)
            if missing:
                raise ValueError(f"passed validation suite report missing steps: {missing}")
        if not self.required_next_actions:
            raise ValueError("validation suite evidence report requires next actions")
        return self


POCQATriageCategory = Literal[
    "synthetic_qa",
    "review_queue",
    "matter_linking",
    "labor_employment_budget_facts",
    "budget_output",
    "budget_qa_gate",
    "public_data_boundary",
    "production_boundary",
]

POCQATriagePriority = Literal["p0", "p1", "p2", "watch"]
POCQATriageItemStatus = Literal["passed", "needs_review", "watch", "blocked"]


class POCQATriageItem(StrictModel):
    item_id: str
    category: POCQATriageCategory
    priority: POCQATriagePriority
    status: POCQATriageItemStatus
    summary: str
    recommended_next_action: str
    evidence_refs: list[str] = Field(default_factory=list)
    candidate_exception_lake_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def poc_qa_triage_item_is_actionable(self) -> "POCQATriageItem":
        if not self.summary.strip():
            raise ValueError("POC QA triage item requires a summary")
        if not self.recommended_next_action.strip():
            raise ValueError("POC QA triage item requires a recommended next action")
        if not self.evidence_refs:
            raise ValueError("POC QA triage item requires evidence refs")
        if self.status in {"needs_review", "blocked"} and not self.candidate_exception_lake_labels:
            raise ValueError("actionable POC QA triage items require candidate Lake labels")
        return self


class POCQATriageReport(StrictModel):
    schema_version: str = "0.1"
    poc_qa_triage_report_id: str
    status: Literal["poc_qa_ready_for_review", "blocked_by_poc_qa_triage"]
    source_ui_manifest_id: str
    source_synthetic_confidence_summary_report_id: str
    source_synthetic_qa_review_run_report_id: str
    source_synthetic_qa_blocker_report_id: str
    source_matter_linking_preflight_report_id: str
    source_labor_employment_qa_matrix_report_id: str
    source_blocked_driver_impact_review_report_id: str
    source_budget_output_expectation_report_id: str
    source_budget_qa_gate_report_id: str
    source_validation_suite_evidence_report_id: str | None = None
    item_count: int = Field(ge=0)
    passed_item_count: int = Field(ge=0)
    needs_review_item_count: int = Field(ge=0)
    watch_item_count: int = Field(ge=0)
    blocked_item_count: int = Field(ge=0)
    p0_blocked_item_count: int = Field(ge=0)
    items: list[POCQATriageItem]
    required_next_actions: list[str]
    display_banner: dict[str, Any]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def poc_qa_triage_counts_and_status_match(self) -> "POCQATriageReport":
        passed = [item for item in self.items if item.status == "passed"]
        needs_review = [item for item in self.items if item.status == "needs_review"]
        watch = [item for item in self.items if item.status == "watch"]
        blocked = [item for item in self.items if item.status == "blocked"]
        p0_blocked = [item for item in blocked if item.priority == "p0"]
        if self.item_count != len(self.items):
            raise ValueError("POC QA triage item count mismatch")
        if self.passed_item_count != len(passed):
            raise ValueError("POC QA triage passed count mismatch")
        if self.needs_review_item_count != len(needs_review):
            raise ValueError("POC QA triage needs-review count mismatch")
        if self.watch_item_count != len(watch):
            raise ValueError("POC QA triage watch count mismatch")
        if self.blocked_item_count != len(blocked):
            raise ValueError("POC QA triage blocked count mismatch")
        if self.p0_blocked_item_count != len(p0_blocked):
            raise ValueError("POC QA triage p0 blocked count mismatch")
        if self.status == "poc_qa_ready_for_review" and blocked:
            raise ValueError("ready POC QA triage cannot contain blocked items")
        if self.status == "blocked_by_poc_qa_triage" and not blocked:
            raise ValueError("blocked POC QA triage requires blocked items")
        if not self.required_next_actions:
            raise ValueError("POC QA triage requires next actions")
        return self


SyntheticQABlockerRowSource = Literal[
    "quality_gate",
    "qa_step",
    "readiness_item",
    "top_blocker",
]
SyntheticQABlockerRowState = Literal["failed", "blocked", "pending_review"]
SyntheticQABlockerActionState = Literal["blocked", "needs_review", "fixed", "ready"]


class SyntheticQABlockerRow(StrictModel):
    row_id: str
    source: SyntheticQABlockerRowSource
    label: str
    state: SyntheticQABlockerRowState
    action_state: SyntheticQABlockerActionState
    owner: str
    evidence_refs: list[str]
    recommended_next_action: str
    candidate_exception_lake_labels: list[str]
    notes: list[str]

    @model_validator(mode="after")
    def synthetic_qa_blocker_row_is_actionable(self) -> "SyntheticQABlockerRow":
        if not self.row_id.strip():
            raise ValueError("synthetic QA blocker row requires row_id")
        if not self.label.strip():
            raise ValueError("synthetic QA blocker row requires label")
        if not self.owner.strip():
            raise ValueError("synthetic QA blocker row requires owner")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("synthetic QA blocker row requires evidence refs")
        if not self.recommended_next_action.strip():
            raise ValueError("synthetic QA blocker row requires recommended next action")
        if not self.candidate_exception_lake_labels or any(
            not label.strip() for label in self.candidate_exception_lake_labels
        ):
            raise ValueError("synthetic QA blocker row requires candidate exception labels")
        if not self.notes or any(not note.strip() for note in self.notes):
            raise ValueError("synthetic QA blocker row requires notes")
        if self.state in {"failed", "blocked"} and self.action_state != "blocked":
            raise ValueError("failed or blocked synthetic QA blocker row must block action")
        if self.state == "pending_review" and self.action_state != "needs_review":
            raise ValueError("pending synthetic QA blocker row must require review")
        return self


class SyntheticQABlockerReport(StrictModel):
    schema_version: str = "0.1"
    synthetic_qa_blocker_report_id: str
    status: Literal[
        "synthetic_qa_blocker_report_ready_for_review",
        "blocked_by_synthetic_qa_blocker_report",
        "failed_synthetic_qa_blocker_boundary",
    ]
    source_ui_manifest_ref: str
    source_ui_manifest_id: str
    source_ui_manifest_overall_status: str
    source_synthetic_confidence_summary_ref: str
    source_synthetic_confidence_summary_report_id: str
    source_synthetic_confidence_summary_status: str
    source_synthetic_qa_review_run_ref: str
    source_synthetic_qa_review_run_report_id: str
    source_synthetic_qa_review_run_status: str
    row_count: int = Field(ge=0)
    failed_row_count: int = Field(ge=0)
    blocked_row_count: int = Field(ge=0)
    pending_review_row_count: int = Field(ge=0)
    blocked_action_count: int = Field(ge=0)
    needs_review_action_count: int = Field(ge=0)
    fixed_action_count: int = Field(ge=0)
    ready_action_count: int = Field(ge=0)
    review_queue_state: Literal["blocked", "needs_review", "ready"]
    rows: list[SyntheticQABlockerRow]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def synthetic_qa_blocker_report_counts_and_status_match(
        self,
    ) -> "SyntheticQABlockerReport":
        failed = [row for row in self.rows if row.state == "failed"]
        blocked = [row for row in self.rows if row.state == "blocked"]
        pending = [row for row in self.rows if row.state == "pending_review"]
        blocked_actions = [row for row in self.rows if row.action_state == "blocked"]
        needs_review_actions = [row for row in self.rows if row.action_state == "needs_review"]
        fixed_actions = [row for row in self.rows if row.action_state == "fixed"]
        ready_actions = [row for row in self.rows if row.action_state == "ready"]
        if self.row_count != len(self.rows):
            raise ValueError("synthetic QA blocker row count mismatch")
        if self.failed_row_count != len(failed):
            raise ValueError("synthetic QA blocker failed row count mismatch")
        if self.blocked_row_count != len(blocked):
            raise ValueError("synthetic QA blocker blocked row count mismatch")
        if self.pending_review_row_count != len(pending):
            raise ValueError("synthetic QA blocker pending row count mismatch")
        if self.blocked_action_count != len(blocked_actions):
            raise ValueError("synthetic QA blocker blocked action count mismatch")
        if self.needs_review_action_count != len(needs_review_actions):
            raise ValueError("synthetic QA blocker needs-review action count mismatch")
        if self.fixed_action_count != len(fixed_actions):
            raise ValueError("synthetic QA blocker fixed action count mismatch")
        if self.ready_action_count != len(ready_actions):
            raise ValueError("synthetic QA blocker ready action count mismatch")
        expected_queue_state = (
            "blocked" if blocked_actions else "needs_review" if needs_review_actions else "ready"
        )
        if self.review_queue_state != expected_queue_state:
            raise ValueError("synthetic QA blocker review queue state mismatch")
        if self.status == "synthetic_qa_blocker_report_ready_for_review" and (failed or blocked):
            raise ValueError("ready synthetic QA blocker report cannot contain failed blockers")
        if self.status == "blocked_by_synthetic_qa_blocker_report" and not (failed or blocked):
            raise ValueError("blocked synthetic QA blocker report requires failed or blocked rows")
        if self.status == "failed_synthetic_qa_blocker_boundary" and not (failed or blocked):
            raise ValueError("failed synthetic QA blocker report requires failed or blocked rows")
        if not self.required_next_actions:
            raise ValueError("synthetic QA blocker report requires next actions")
        return self


SyntheticQABlockerReviewDecisionOutcome = Literal[
    "accepted_for_poc_review",
    "needs_fix",
    "defer_to_roadmap",
    "not_applicable",
]


class SyntheticQABlockerReviewDecision(StrictModel):
    schema_version: str = "0.1"
    decision_id: str
    row_id: str
    outcome: SyntheticQABlockerReviewDecisionOutcome
    decision_reason: str
    evidence_refs: list[str]
    required_followups: list[str] = Field(default_factory=list)
    red_team_notes: list[str]
    candidate_exception_lake_labels: list[str]

    @model_validator(mode="after")
    def synthetic_qa_review_decision_is_actionable(
        self,
    ) -> "SyntheticQABlockerReviewDecision":
        if not self.decision_id.strip():
            raise ValueError("synthetic QA review decision requires decision_id")
        if not self.row_id.strip():
            raise ValueError("synthetic QA review decision requires row_id")
        if not self.decision_reason.strip():
            raise ValueError("synthetic QA review decision requires decision reason")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("synthetic QA review decision requires evidence refs")
        if not self.red_team_notes or any(not note.strip() for note in self.red_team_notes):
            raise ValueError("synthetic QA review decision requires red-team notes")
        if not self.candidate_exception_lake_labels or any(
            not label.strip() for label in self.candidate_exception_lake_labels
        ):
            raise ValueError("synthetic QA review decision requires candidate labels")
        if self.outcome in {"needs_fix", "defer_to_roadmap"} and not self.required_followups:
            raise ValueError("fix/defer QA review decisions require followups")
        return self


class SyntheticQABlockerReviewOutcomeRecord(StrictModel):
    schema_version: str = "0.1"
    synthetic_qa_review_outcome_record_id: str
    synthetic_qa_blocker_report_id: str
    reviewer_id: str
    reviewed_at: str
    decision_reason: str
    decisions: list[SyntheticQABlockerReviewDecision]
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def synthetic_qa_review_outcome_record_is_complete(
        self,
    ) -> "SyntheticQABlockerReviewOutcomeRecord":
        if not self.synthetic_qa_review_outcome_record_id.strip():
            raise ValueError("synthetic QA review outcome record requires id")
        if not self.synthetic_qa_blocker_report_id.strip():
            raise ValueError("synthetic QA review outcome record requires source report id")
        if not self.reviewer_id.strip():
            raise ValueError("synthetic QA review outcome record requires reviewer")
        if not self.reviewed_at.strip():
            raise ValueError("synthetic QA review outcome record requires reviewed_at")
        if not self.decision_reason.strip():
            raise ValueError("synthetic QA review outcome record requires decision reason")
        if not self.decisions:
            raise ValueError("synthetic QA review outcome record requires decisions")
        row_ids = [decision.row_id for decision in self.decisions]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("synthetic QA review outcome record has duplicate row decisions")
        return self


class SyntheticQABlockerReviewOutcomeReport(StrictModel):
    schema_version: str = "0.1"
    synthetic_qa_review_outcome_report_id: str
    status: Literal[
        "synthetic_qa_review_outcome_recorded",
        "synthetic_qa_review_outcome_recorded_pending_followup",
        "blocked_by_synthetic_qa_review_outcome",
    ]
    source_synthetic_qa_blocker_report_ref: str
    source_synthetic_qa_blocker_report_id: str
    source_synthetic_qa_blocker_report_status: str
    synthetic_qa_review_outcome_record_id: str
    reviewer_id: str
    reviewed_at: str
    decision_reason: str
    source_row_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    accepted_decision_count: int = Field(ge=0)
    needs_fix_decision_count: int = Field(ge=0)
    deferred_decision_count: int = Field(ge=0)
    not_applicable_decision_count: int = Field(ge=0)
    reviewed_row_count: int = Field(ge=0)
    unreviewed_row_count: int = Field(ge=0)
    unknown_row_count: int = Field(ge=0)
    unresolved_followup_count: int = Field(ge=0)
    reviewed_row_ids: list[str]
    unreviewed_row_ids: list[str]
    unknown_row_ids: list[str]
    required_followups: list[str]
    candidate_lake_event_labels: list[str]
    append_only_history_ref: str
    required_next_actions: list[str]
    append_only: Literal[True] = True
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def synthetic_qa_review_outcome_report_counts_match(
        self,
    ) -> "SyntheticQABlockerReviewOutcomeReport":
        if self.decision_count != (
            self.accepted_decision_count
            + self.needs_fix_decision_count
            + self.deferred_decision_count
            + self.not_applicable_decision_count
        ):
            raise ValueError("synthetic QA review decision outcome counts mismatch")
        if self.reviewed_row_count != len(self.reviewed_row_ids):
            raise ValueError("synthetic QA review reviewed row count mismatch")
        if self.unreviewed_row_count != len(self.unreviewed_row_ids):
            raise ValueError("synthetic QA review unreviewed row count mismatch")
        if self.unknown_row_count != len(self.unknown_row_ids):
            raise ValueError("synthetic QA review unknown row count mismatch")
        if self.reviewed_row_count + self.unreviewed_row_count != self.source_row_count:
            raise ValueError("synthetic QA review source row coverage mismatch")
        if self.unresolved_followup_count != len(self.required_followups):
            raise ValueError("synthetic QA review followup count mismatch")
        if self.unknown_row_count and self.status != "blocked_by_synthetic_qa_review_outcome":
            raise ValueError("synthetic QA review report with unknown rows must block")
        if self.status == "synthetic_qa_review_outcome_recorded" and (
            self.unreviewed_row_count or self.unresolved_followup_count
        ):
            raise ValueError("recorded synthetic QA review outcome cannot have open followups")
        if self.status == "synthetic_qa_review_outcome_recorded_pending_followup" and not (
            self.unreviewed_row_count or self.unresolved_followup_count
        ):
            raise ValueError("pending synthetic QA review outcome requires open followups")
        if not self.candidate_lake_event_labels:
            raise ValueError("synthetic QA review outcome report requires candidate labels")
        if not self.required_next_actions:
            raise ValueError("synthetic QA review outcome report requires next actions")
        return self


UIReviewDataBundleStatus = Literal[
    "ready_for_review",
    "blocked_missing_required_reports",
    "failed_side_effect_boundary",
]

UIReviewDataBundleReportKind = Literal[
    "ui_review_manifest",
    "synthetic_qa_review_run",
    "synthetic_confidence_summary",
    "synthetic_qa_blocker_report",
    "synthetic_qa_review_outcome",
    "ui_demo_qa_recipe",
    "rust_fixture_boundary",
    "rust_fixture_manifest",
    "public_data_cache_audit",
    "rust_public_data_cache_custody",
    "public_derived_synthetic_qa_gate",
    "matter_linking_preflight",
    "matter_linking_review_outcome",
    "matter_linking_qa_gate",
    "labor_employment_qa_matrix",
    "labor_employment_executable_coverage",
    "labor_employment_blocked_driver_impact_review",
    "labor_employment_budget_output_expectations",
    "labor_employment_budget_qa_gate",
    "labor_employment_budget_learning_fixtures",
    "labor_employment_budget_outcome_replay_readiness",
    "labor_employment_budget_outcome_replay_execution",
    "labor_employment_budget_outcome_replay_builder_binding",
    "labor_employment_budget_outcome_replay_confidence_status",
    "budget_learning_loop",
]


class UIReviewDataBundleDetailReport(StrictModel):
    detail_report_id: str
    label: str
    report_kind: UIReviewDataBundleReportKind
    file_name: str
    required: bool
    present: bool
    status: str
    renderer: str
    artifact_ref: str | None = None
    source_sha256: str | None = None
    candidate_only: bool
    synthetic_only: bool
    external_writes_performed: bool
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ui_review_data_bundle_detail_refs_match_presence(
        self,
    ) -> "UIReviewDataBundleDetailReport":
        if self.present and not self.artifact_ref:
            raise ValueError("present UI detail report requires artifact_ref")
        if self.present and not self.source_sha256:
            raise ValueError("present UI detail report requires source_sha256")
        if not self.present and self.source_sha256:
            raise ValueError("missing UI detail report cannot have source_sha256")
        if self.required and not self.notes:
            raise ValueError("required UI detail report needs a note")
        return self


class UIReviewDataBundle(StrictModel):
    schema_version: str = "0.1"
    ui_review_data_bundle_id: str
    status: UIReviewDataBundleStatus
    run_root_ref: str
    detail_report_count: int = Field(ge=0)
    required_detail_report_count: int = Field(ge=0)
    present_detail_report_count: int = Field(ge=0)
    missing_required_detail_report_count: int = Field(ge=0)
    external_write_report_count: int = Field(ge=0)
    detail_reports: list[UIReviewDataBundleDetailReport]
    required_next_actions: list[str]
    candidate_only: Literal[True] = True
    synthetic_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    local_json_only: Literal[True] = True
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
    def ui_review_data_bundle_counts_and_status_match(self) -> "UIReviewDataBundle":
        required = [report for report in self.detail_reports if report.required]
        present = [report for report in self.detail_reports if report.present]
        missing_required = [report for report in required if not report.present]
        external_write_reports = [
            report for report in self.detail_reports if report.external_writes_performed
        ]
        if self.detail_report_count != len(self.detail_reports):
            raise ValueError("UI review data bundle detail count mismatch")
        if self.required_detail_report_count != len(required):
            raise ValueError("UI review data bundle required count mismatch")
        if self.present_detail_report_count != len(present):
            raise ValueError("UI review data bundle present count mismatch")
        if self.missing_required_detail_report_count != len(missing_required):
            raise ValueError("UI review data bundle missing required count mismatch")
        if self.external_write_report_count != len(external_write_reports):
            raise ValueError("UI review data bundle external-write count mismatch")
        if self.status == "ready_for_review" and (missing_required or external_write_reports):
            raise ValueError("ready UI review data bundle cannot have missing or write reports")
        if self.status == "blocked_missing_required_reports" and not missing_required:
            raise ValueError("blocked UI review data bundle requires missing reports")
        if self.status == "failed_side_effect_boundary" and not external_write_reports:
            raise ValueError("failed UI review data bundle requires external-write reports")
        if not self.required_next_actions:
            raise ValueError("UI review data bundle requires next actions")
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
        "budget_invariant_violation",
        "scenario_policy_invalid",
        "rate_resolution_ambiguous",
        "carrier_appeal_outcome",
        "matter_link_ambiguity",
        "matter_link_conflict",
        "human_correction_of_machine_output",
        "qa_gate_defect",
        "fixture_weakness",
        "workflow_discovery",
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
            "budget_invariant_report",
            "matter_linking_preflight_report",
            "human_review_outcome_record",
            "qa_gate_report",
            "fixture_gold_report",
            "workflow_discovery_note",
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


SkillsRegistrySpecialistStatus = Literal[
    "ready_for_skills_registry_review",
    "blocked_by_specialist_metadata_gap",
]


class SkillsRegistrySpecialistCandidate(StrictModel):
    schema_version: str = "0.1"
    specialist_candidate_id: str
    worker_id: str
    version: str
    agent_ref: str
    prompt_ref: str
    prompt_file_ref: str
    prompt_hash: str
    prompt_hash_verified: bool
    prompt_lifecycle: str
    approved_for_real_data: Literal[False] = False
    purpose: str
    model_class: str
    raw_source_access: str
    cross_matter_access: Literal[False] = False
    network_access: Literal[False] = False
    write_scope: str
    allowed_tool_refs: list[str] = Field(default_factory=list)
    tool_denylist: list[str]
    input_schema_ref: str
    output_schema_ref: str
    input_schema_exists: bool
    output_schema_exists: bool
    requirements: list[str]
    prohibited_actions: list[str]
    accepted_context_classes: list[str]
    forbidden_context_classes: list[str]
    evidence_requirements: list[str]
    human_gate_required: Literal[True] = True
    revocation_owner: Literal["LawFirm-os-skills-registry"] = "LawFirm-os-skills-registry"
    status: SkillsRegistrySpecialistStatus
    missing_metadata_fields: list[str] = Field(default_factory=list)
    required_owner_actions: list[str]
    acceptance_checks: list[str]
    red_team_notes: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    metadata_only: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    skill_promoted: Literal[False] = False
    skill_trust_record_created: Literal[False] = False
    dynamic_agent_created: Literal[False] = False
    model_provider_enabled: Literal[False] = False
    real_data_approved: Literal[False] = False
    external_tools_allowed: Literal[False] = False
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
    def skills_candidate_is_reviewable(self) -> "SkillsRegistrySpecialistCandidate":
        if not self.prompt_hash.startswith("sha256:"):
            raise ValueError("skills specialist prompt hash must be sha256")
        if self.status == "ready_for_skills_registry_review":
            if self.missing_metadata_fields:
                raise ValueError("ready skills specialist cannot have metadata gaps")
            if not self.prompt_hash_verified:
                raise ValueError("ready skills specialist requires verified prompt hash")
            if not self.input_schema_exists or not self.output_schema_exists:
                raise ValueError("ready skills specialist requires existing schema refs")
        if self.status == "blocked_by_specialist_metadata_gap" and not (
            self.missing_metadata_fields
        ):
            raise ValueError("blocked skills specialist requires metadata gaps")
        if not self.tool_denylist:
            raise ValueError("skills specialist requires a tool denylist")
        if not self.required_owner_actions:
            raise ValueError("skills specialist requires owner actions")
        if not self.acceptance_checks:
            raise ValueError("skills specialist requires acceptance checks")
        if not self.red_team_notes:
            raise ValueError("skills specialist requires red-team notes")
        return self


class SkillsRegistrySpecialistReviewCheck(StrictModel):
    check_id: str
    status: Literal["passed", "failed"]
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    worker_ids: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)


class SkillsRegistrySpecialistReviewReport(StrictModel):
    schema_version: str = "0.1"
    specialist_review_report_id: str
    status: Literal[
        "skills_registry_specialist_review_ready",
        "blocked_by_specialist_metadata_gaps",
    ]
    target_repo: Literal["LawFirm-os-skills-registry"] = "LawFirm-os-skills-registry"
    manifest_ref: str
    prompt_registry_ref: str
    expected_harness_count: int = Field(ge=0)
    missing_harness_refs: list[str] = Field(default_factory=list)
    expected_worker_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    ready_candidate_count: int = Field(ge=0)
    blocked_candidate_count: int = Field(ge=0)
    missing_worker_ids: list[str] = Field(default_factory=list)
    unexpected_worker_ids: list[str] = Field(default_factory=list)
    prompt_hash_count: int = Field(ge=0)
    candidates: list[SkillsRegistrySpecialistCandidate]
    candidate_packet_refs: list[str] = Field(default_factory=list)
    checks: list[SkillsRegistrySpecialistReviewCheck]
    required_next_gates: list[str]
    candidate_only: Literal[True] = True
    non_authoritative: Literal[True] = True
    metadata_only: Literal[True] = True
    blocked_until_owner_review: Literal[True] = True
    skill_promoted: Literal[False] = False
    skill_trust_record_created: Literal[False] = False
    dynamic_agent_created: Literal[False] = False
    model_provider_enabled: Literal[False] = False
    real_data_approved: Literal[False] = False
    external_tools_allowed: Literal[False] = False
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
    def skills_report_counts_match(self) -> "SkillsRegistrySpecialistReviewReport":
        failed = [check for check in self.checks if check.status == "failed"]
        if self.candidate_count != len(self.candidates):
            raise ValueError("skills specialist candidate count does not match")
        ready_count = sum(
            1
            for candidate in self.candidates
            if candidate.status == "ready_for_skills_registry_review"
        )
        blocked_count = self.candidate_count - ready_count
        if self.ready_candidate_count != ready_count:
            raise ValueError("skills specialist ready count does not match")
        if self.blocked_candidate_count != blocked_count:
            raise ValueError("skills specialist blocked count does not match")
        if self.status == "skills_registry_specialist_review_ready" and (
            failed
            or blocked_count
            or self.missing_worker_ids
            or self.unexpected_worker_ids
            or self.missing_harness_refs
        ):
            raise ValueError("ready skills specialist report cannot include blockers")
        if self.status == "blocked_by_specialist_metadata_gaps" and not (
            failed
            or blocked_count
            or self.missing_worker_ids
            or self.unexpected_worker_ids
            or self.missing_harness_refs
        ):
            raise ValueError("blocked skills specialist report requires blockers")
        if len(self.candidate_packet_refs) != self.candidate_count * 2:
            raise ValueError(
                "skills specialist packet refs must include JSON and Markdown per candidate"
            )
        required = {
            "skills_registry_owner_review",
            "prompt_hash_review",
            "tool_authority_review",
            "eval_suite_review_before_promotion",
            "revocation_path_review",
            "no_skill_promotion_from_intake",
        }
        if not required.issubset(set(self.required_next_gates)):
            raise ValueError("skills specialist report is missing required gates")
        return self


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
