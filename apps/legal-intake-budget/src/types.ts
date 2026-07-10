export type GateState = "passed" | "blocked" | "pending" | "failed";

export type ArtifactStatus = "present" | "missing" | "blocked" | "pending_review";

export type QualityGateStatus = "passed" | "failed" | "blocked" | "pending_review";

export type QualityGate = {
  gateId: string;
  label: string;
  status: QualityGateStatus;
  evidenceFile: string;
  owner: string;
  notes: string[];
};

export type UIReviewDataBundleStatus =
  | "ready_for_review"
  | "blocked_missing_required_reports"
  | "failed_side_effect_boundary";

export type UIReviewDataBundleReportKind =
  | "ui_review_manifest"
  | "synthetic_qa_review_run"
  | "synthetic_confidence_summary"
  | "synthetic_qa_blocker_report"
  | "synthetic_qa_review_outcome"
  | "ui_demo_qa_recipe"
  | "rust_fixture_boundary"
  | "rust_fixture_manifest"
  | "public_data_cache_audit"
  | "rust_public_data_cache_custody"
  | "public_derived_synthetic_qa_gate"
  | "matter_linking_preflight"
  | "matter_linking_review_outcome"
  | "matter_linking_qa_gate"
  | "labor_employment_qa_matrix"
  | "labor_employment_executable_coverage"
  | "labor_employment_blocked_driver_impact_review"
  | "labor_employment_budget_output_expectations"
  | "labor_employment_budget_qa_gate"
  | "labor_employment_budget_learning_fixtures"
  | "labor_employment_budget_outcome_replay_readiness"
  | "labor_employment_budget_outcome_replay_execution"
  | "labor_employment_budget_outcome_replay_builder_binding"
  | "labor_employment_budget_outcome_replay_confidence_status"
  | "budget_learning_loop"
  | "crosswalk_audit"
  | "ocg_rule_ir_adoption";

export type MatterLinkingPreflightCluster = {
  cluster_id: string;
  link_state: string;
  match_strength: string;
  proposed_short_label?: string;
  source_ids: string[];
  source_hashes: string[];
  supporting_signal_count: number;
  strong_supporting_signal_count: number;
  negative_signal_count: number;
  strong_negative_signal_count: number;
  supporting_signal_types: string[];
  negative_signal_types: string[];
  source_bound_strong_support_present: boolean;
  weak_only_candidate: boolean;
  negative_split_evidence_required: boolean;
  requires_human_confirmation: boolean;
  matter_link_finalized: boolean;
};

export type MatterLinkingPreflightReport = {
  schema_version: string;
  matter_linking_preflight_report_id: string;
  status:
    | "matter_linking_preflight_requires_review"
    | "matter_linking_preflight_resolved_candidate_requires_review"
    | "blocked_matter_linking_preflight";
  source_artifact_ref: string;
  source_artifact_id: string;
  source_artifact_type: string;
  source_artifact_status: string;
  source_artifact_hash: string;
  official_matter_number_status: string;
  overall_link_state: string;
  requires_human_confirmation: boolean;
  requires_sender_followup: boolean;
  cluster_count: number;
  high_evidence_candidate_count: number;
  weak_only_candidate_count: number;
  negative_split_evidence_required: boolean;
  weak_signal_count: number;
  strong_negative_signal_count: number;
  source_count: number;
  source_hashes_by_id: Record<string, string>;
  weak_merge_signal_types: string[];
  candidate_exception_lake_labels: string[];
  clusters: MatterLinkingPreflightCluster[];
  required_next_gates: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  sender_followup_required: boolean;
  upfront_connector_implemented: boolean;
  vendor_api_called: boolean;
  external_write_performed: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  matter_opening_authorized: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  screen_created: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type MatterLinkingReviewOutcomeStatus =
  | "matter_linking_review_outcome_recorded"
  | "matter_linking_review_outcome_recorded_pending_followup"
  | "blocked_by_matter_linking_review_outcome";

export type MatterLinkingReviewOutcomeReport = {
  schema_version: string;
  matter_linking_review_outcome_report_id: string;
  status: MatterLinkingReviewOutcomeStatus;
  source_matter_linking_preflight_report_ref: string;
  matter_linking_preflight_report_id: string;
  source_matter_linking_preflight_status: string;
  matter_linking_review_outcome_record_id: string;
  reviewer_id: string;
  reviewed_at: string;
  overall_outcome:
    | "confirm_split"
    | "confirm_merge"
    | "confirm_single_candidate"
    | "unknown"
    | "request_more_info"
    | "declined_or_referred";
  decision_reason: string;
  source_cluster_count: number;
  decision_count: number;
  split_decision_count: number;
  merge_decision_count: number;
  single_candidate_decision_count: number;
  unknown_decision_count: number;
  request_more_info_decision_count: number;
  declined_or_referred_decision_count: number;
  reviewed_cluster_count: number;
  unreviewed_cluster_count: number;
  unknown_cluster_count: number;
  reviewed_cluster_ids: string[];
  unreviewed_cluster_ids: string[];
  unknown_cluster_ids: string[];
  required_followups: string[];
  candidate_lake_event_labels: string[];
  append_only_history_ref: string;
  required_next_gates: string[];
  append_only: boolean;
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_conflict_conclusion: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  screen_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type MatterLinkingQAGateCase = {
  schema_version: string;
  case_id: string;
  fixture_ref: string;
  generated_report_ref: string;
  expected_status: string;
  observed_status: string;
  expected_overall_link_state: string;
  observed_overall_link_state: string;
  expected_cluster_count: number;
  observed_cluster_count: number;
  expected_high_evidence_candidate_count: number;
  observed_high_evidence_candidate_count: number;
  expected_weak_only_candidate_count: number;
  observed_weak_only_candidate_count: number;
  expected_negative_split_evidence_required: boolean;
  observed_negative_split_evidence_required: boolean;
  expected_sender_followup_required: boolean;
  observed_sender_followup_required: boolean;
  expected_failed_check_ids: string[];
  observed_failed_check_ids: string[];
  required_coverage_tags: string[];
  candidate_exception_lake_labels: string[];
  status: "passed" | "failed";
  notes: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type MatterLinkingQAGateCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  case_ids: string[];
  artifact_refs: string[];
  blocking_refs: string[];
};

export type MatterLinkingQAGateReport = {
  schema_version: string;
  matter_linking_qa_gate_report_id: string;
  status: "matter_linking_qa_gate_ready_for_review" | "blocked_by_matter_linking_qa_gate";
  repo_root_ref: string;
  out_dir_ref: string;
  case_count: number;
  passed_case_count: number;
  failed_case_count: number;
  required_coverage_tag_count: number;
  observed_coverage_tag_count: number;
  missing_coverage_tags: string[];
  cases: MatterLinkingQAGateCase[];
  checks: MatterLinkingQAGateCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type UIReviewDataBundleDetailReport = {
  detail_report_id: string;
  label: string;
  report_kind: UIReviewDataBundleReportKind;
  file_name: string;
  required: boolean;
  present: boolean;
  status: string;
  renderer: string;
  artifact_ref?: string;
  source_sha256?: string;
  candidate_only: boolean;
  synthetic_only: boolean;
  external_writes_performed: boolean;
  notes: string[];
};

export type UIReviewDataBundle = {
  schema_version: string;
  ui_review_data_bundle_id: string;
  status: UIReviewDataBundleStatus;
  run_root_ref: string;
  detail_report_count: number;
  required_detail_report_count: number;
  present_detail_report_count: number;
  missing_required_detail_report_count: number;
  external_write_report_count: number;
  detail_reports: UIReviewDataBundleDetailReport[];
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetReadinessState =
  | "blocked_missing_critical_facts"
  | "range_only_pending_human_review"
  | "candidate_ready_for_budget_review";

export type LaborEmploymentBudgetGateEffect =
  | "block_amount_budget_before_proposal"
  | "allow_range_or_hours_only_pending_review"
  | "candidate_ready_for_budget_review_after_review";

export type SyntheticQAReviewRunStep = {
  step_id: string;
  label: string;
  status: "passed" | "failed";
  observed_status: string;
  artifact_ref: string;
  notes: string[];
};

export type SyntheticQAReviewRunReport = {
  schema_version: string;
  synthetic_qa_review_run_report_id: string;
  status: "synthetic_qa_review_run_ready" | "blocked_by_synthetic_qa_review_run";
  run_root_ref: string;
  quality_dir_ref: string;
  step_count: number;
  failed_step_count: number;
  steps: SyntheticQAReviewRunStep[];
  synthetic_qa_bundle_ref: string;
  ui_manifest_ref: string;
  ui_data_bundle_ref: string;
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  calibration_applied: boolean;
  fixture_files_mutated: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type RustFixtureBoundaryFailure = {
  path: string;
  json_path: string;
  check: string;
  message: string;
};

export type RustFixtureBoundaryReport = {
  schema_version: string;
  checker: "fixture-boundary-checker";
  status: "passed" | "failed";
  root: string;
  ui_bundle_ref?: string | null;
  checked_json_file_count: number;
  checked_object_count: number;
  failure_count: number;
  failures: RustFixtureBoundaryFailure[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  external_writes_performed: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  silent_learning_performed: boolean;
};

export type RustFixtureManifestIdField = {
  field: string;
  value: string;
};

export type RustFixtureManifestFile = {
  path: string;
  sha256: string;
  byte_count: number;
  top_level_type: string;
  schema_version?: string | null;
  status?: string | null;
  report_kind?: string | null;
  data_origin?: string | null;
  candidate_only?: boolean | null;
  synthetic_only?: boolean | null;
  external_writes_performed?: boolean | null;
  id_fields: RustFixtureManifestIdField[];
};

export type RustFixtureManifestFailure = {
  path: string;
  check: string;
  message: string;
};

export type RustFixtureManifestSkippedFile = {
  path: string;
  reason: string;
};

export type RustFixtureManifestReport = {
  schema_version: string;
  scanner: "fixture-manifest-scanner";
  status: "passed" | "failed";
  root: string;
  manifest_sha256: string;
  checked_json_file_count: number;
  parsed_json_file_count: number;
  parse_error_count: number;
  skipped_file_count: number;
  skipped_files: RustFixtureManifestSkippedFile[];
  total_byte_count: number;
  files: RustFixtureManifestFile[];
  failure_count: number;
  failures: RustFixtureManifestFailure[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  external_writes_performed: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  silent_learning_performed: boolean;
};

export type PublicDataCacheSourceManifest = {
  schema_version: string;
  source_id: string;
  source_url: string;
  source_type: string;
  retrieved_at: string;
  sha256: string;
  byte_count: number;
  cache_ref: string;
  license_terms_note: string;
  allowed_use: string;
  prohibited_use: string;
  retention_posture: string;
  data_origin: "public_reference_cache";
  public_payload_committed: boolean;
  direct_runtime_ingestion_allowed: boolean;
  runtime_intake_input: boolean;
};

export type PublicDataCacheAuditCheck = {
  check_id: string;
  status: "passed" | "blocked" | "failed";
  message: string;
  source_ids: string[];
  path_refs: string[];
};

export type PublicDataCacheAuditReport = {
  schema_version: string;
  public_data_cache_audit_report_id: string;
  status: "ready_for_human_public_data_cache_review" | "blocked_public_data_cache";
  source_catalog_ref: string;
  data_policy_ref: string;
  cache_root_ref: string;
  manifest_ref: string;
  manifest_entry_count: number;
  valid_manifest_entry_count: number;
  cache_sample_count: number;
  total_cache_sample_bytes: number;
  approved_source_ids: string[];
  unknown_source_ids: string[];
  failed_hash_source_ids: string[];
  missing_cache_file_source_ids: string[];
  blocked_path_refs: string[];
  rust_custody_report_ref?: string | null;
  rust_custody_status: "passed" | "failed" | "not_run";
  rust_custody_failure_count: number;
  rust_custody_checked_source_count: number;
  rust_custody_checked_sample_count: number;
  rust_custody_total_checked_sample_bytes: number;
  sources: PublicDataCacheSourceManifest[];
  checks: PublicDataCacheAuditCheck[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  planning_only: boolean;
  report_payload_metadata_only: boolean;
  human_review_required: boolean;
  public_cache_samples_present: boolean;
  direct_runtime_ingestion_allowed: boolean;
  public_records_runtime_ingested: boolean;
  raw_public_payload_committed: boolean;
  tracked_public_payload_committed: boolean;
  real_party_records_committed: boolean;
  real_matter_records_committed: boolean;
  connector_implemented: boolean;
  legal_knowledge_adapter_authorized: boolean;
  synthetic_fixtures_created: boolean;
  fixture_files_mutated: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  generated_at: string;
};

export type RustPublicDataCacheCustodyFailure = {
  source_id: string;
  path: string;
  check: string;
  expected?: string | null;
  actual?: string | null;
  message: string;
};

export type RustPublicDataCacheCustodySample = {
  source_id: string;
  cache_ref?: string | null;
  resolved_path_ref?: string | null;
  expected_sha256?: string | null;
  actual_sha256?: string | null;
  expected_byte_count?: number | null;
  actual_byte_count?: number | null;
  status: "passed" | "failed" | "blocked" | "missing" | "invalid";
};

export type RustPublicDataCacheCustodyReport = {
  schema_version: string;
  checker: "public-data-cache-custody-checker";
  status: "passed" | "failed";
  repo_root: string;
  cache_root: string;
  manifest_ref: string;
  manifest_sha256: string;
  manifest_byte_count: number;
  manifest_entry_count: number;
  checked_source_count: number;
  checked_sample_count: number;
  total_checked_sample_bytes: number;
  root_violation_count: number;
  manifest_error_count: number;
  invalid_manifest_entry_count: number;
  blocked_path_count: number;
  missing_file_count: number;
  hash_mismatch_count: number;
  byte_count_mismatch_count: number;
  failure_count: number;
  failures: RustPublicDataCacheCustodyFailure[];
  samples: RustPublicDataCacheCustodySample[];
  candidate_only: boolean;
  planning_only: boolean;
  non_authoritative: boolean;
  metadata_only_report: boolean;
  local_file_custody_only: boolean;
  public_cache_samples_may_be_present: boolean;
  direct_runtime_ingestion_allowed: boolean;
  public_records_runtime_ingested: boolean;
  public_payload_committed: boolean;
  raw_public_payload_committed: boolean;
  tracked_public_payload_committed: boolean;
  connector_implemented: boolean;
  legal_knowledge_adapter_authorized: boolean;
  synthetic_fixtures_created: boolean;
  fixture_files_mutated: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  matter_opening_authorized: boolean;
  budget_submission_authorized: boolean;
  silent_learning_performed: boolean;
};

export type SyntheticConfidenceSummaryItemState =
  | "ready_for_review"
  | "pending_review"
  | "blocked"
  | "failed";

export type SyntheticConfidenceSummaryItem = {
  item_id: string;
  label: string;
  owner: string;
  state: SyntheticConfidenceSummaryItemState;
  evidence_refs: string[];
  notes: string[];
  no_write_boundary_confirmed: boolean;
};

export type SyntheticConfidenceDisplayBanner = {
  candidate_only: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  not_production_ready: boolean;
  human_review_required: boolean;
  testing_readiness_state: string;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  summary: string;
};

export type SyntheticConfidenceSummaryReport = {
  schema_version: string;
  synthetic_confidence_summary_report_id: string;
  status:
    | "synthetic_confidence_summary_ready_for_review"
    | "blocked_by_synthetic_confidence_summary"
    | "failed_synthetic_confidence_summary_boundary";
  testing_readiness_state:
    | "synthetic_qa_ready_pending_review"
    | "blocked_missing_or_failed_evidence"
    | "failed_side_effect_boundary";
  source_synthetic_qa_review_run_ref: string;
  source_synthetic_qa_review_run_report_id: string;
  source_synthetic_qa_review_run_status: string;
  source_synthetic_qa_bundle_ref: string;
  source_synthetic_qa_bundle_report_id: string;
  source_synthetic_qa_bundle_status: string;
  source_ui_manifest_ref: string;
  source_ui_manifest_id: string;
  source_ui_manifest_overall_status: string;
  source_ui_review_data_bundle_ref: string;
  source_ui_review_data_bundle_id: string;
  source_ui_review_data_bundle_status: string;
  qa_step_count: number;
  qa_passed_step_count: number;
  qa_failed_step_count: number;
  qa_artifact_count: number;
  qa_missing_required_artifact_count: number;
  qa_blocked_artifact_count: number;
  qa_pending_artifact_count: number;
  qa_failed_artifact_count: number;
  ui_detail_report_count: number;
  ui_present_detail_report_count: number;
  ui_missing_required_detail_report_count: number;
  ui_external_write_report_count: number;
  quality_gate_count: number;
  quality_gate_passed_count: number;
  quality_gate_pending_count: number;
  quality_gate_blocked_count: number;
  quality_gate_failed_count: number;
  readiness_item_count: number;
  readiness_items: SyntheticConfidenceSummaryItem[];
  top_blockers: string[];
  display_banner: SyntheticConfidenceDisplayBanner;
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type ValidationSuiteStepStatus = "passed" | "failed" | "timed_out";

export type ValidationSuiteStepEvidence = {
  step_id: string;
  command_key: string;
  command: string[];
  command_display: string;
  status: ValidationSuiteStepStatus;
  return_code: number | null;
  timeout_seconds: number;
  duration_seconds: number;
  started_at: string;
  completed_at: string;
  evidence_refs: string[];
};

export type ValidationSuiteEvidenceReport = {
  schema_version: string;
  validation_suite_evidence_report_id: string;
  status: "validation_suite_passed" | "blocked_by_validation_suite";
  policy_id: string;
  policy_version: string;
  policy_ref: string;
  repo_root_ref: string;
  git_commit?: string | null;
  working_tree_dirty: boolean;
  step_count: number;
  passed_step_count: number;
  failed_step_count: number;
  timed_out_step_count: number;
  steps: ValidationSuiteStepEvidence[];
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type UIDemoQARecipeStepStatus = "passed" | "failed" | "blocked";

export type UIDemoQARecipeStep = {
  step_id: string;
  label: string;
  status: UIDemoQARecipeStepStatus;
  observed_status: string;
  artifact_ref?: string | null;
  notes: string[];
};

export type UIDemoQARecipeReport = {
  schema_version: string;
  ui_demo_qa_recipe_report_id: string;
  status:
    | "ui_demo_qa_recipe_verified"
    | "ui_demo_qa_recipe_failed"
    | "ui_demo_qa_recipe_blocked_write_flag_required";
  out_dir_ref: string;
  final_run_root_ref: string;
  initial_run_root_ref: string;
  fixtures_root_ref: string;
  temp_fixtures_root_ref: string;
  validation_mode: "provided" | "ran";
  validation_suite_evidence_ref: string;
  validation_suite_status: string;
  validation_exact_step_order_confirmed: boolean;
  validation_worktree_clean_confirmed: boolean;
  initial_synthetic_qa_status: string;
  temp_promotion_status: string;
  rust_boundary_status: string;
  rust_manifest_status: string;
  rust_boundary_root_matches_temp_fixtures: boolean;
  rust_manifest_root_matches_temp_fixtures: boolean;
  final_synthetic_qa_status: string;
  final_ui_bundle_status: string;
  final_poc_qa_triage_status: string;
  final_promotion_status: string;
  final_promotion_report_ref?: string | null;
  final_ui_review_data_bundle_ref?: string | null;
  final_poc_qa_triage_ref?: string | null;
  step_count: number;
  failed_step_count: number;
  blocked_step_count: number;
  temp_fixture_updates_performed: boolean;
  local_fixture_updates_performed: boolean;
  rollback_performed: boolean;
  steps: UIDemoQARecipeStep[];
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  external_writes_performed: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type POCQATriageStatus = "poc_qa_ready_for_review" | "blocked_by_poc_qa_triage";

export type POCQATriageItemStatus = "passed" | "needs_review" | "watch" | "blocked";

export type POCQATriageItem = {
  item_id: string;
  category:
    | "synthetic_qa"
    | "review_queue"
    | "matter_linking"
    | "labor_employment_budget_facts"
    | "budget_output"
    | "budget_qa_gate"
    | "public_data_boundary"
    | "production_boundary";
  priority: "p0" | "p1" | "p2" | "watch";
  status: POCQATriageItemStatus;
  summary: string;
  recommended_next_action: string;
  evidence_refs: string[];
  candidate_exception_lake_labels: string[];
};

export type POCQATriageReport = {
  schema_version: string;
  poc_qa_triage_report_id: string;
  status: POCQATriageStatus;
  source_ui_manifest_id: string;
  source_synthetic_confidence_summary_report_id: string;
  source_synthetic_qa_review_run_report_id: string;
  source_synthetic_qa_blocker_report_id: string;
  source_matter_linking_preflight_report_id: string;
  source_labor_employment_qa_matrix_report_id: string;
  source_blocked_driver_impact_review_report_id: string;
  source_budget_output_expectation_report_id: string;
  source_budget_qa_gate_report_id: string;
  source_validation_suite_evidence_report_id?: string | null;
  item_count: number;
  passed_item_count: number;
  needs_review_item_count: number;
  watch_item_count: number;
  blocked_item_count: number;
  p0_blocked_item_count: number;
  items: POCQATriageItem[];
  required_next_actions: string[];
  display_banner: {
    summary: string;
    status: POCQATriageStatus;
    candidate_only: boolean;
    synthetic_only: boolean;
    not_production_ready: boolean;
    blocked_actions: string[];
  };
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type BudgetLearningLoopLane = {
  lane_id: string;
  label: string;
  state: GateState;
  metric: string;
  why: string;
  next_action: string;
  evidence_refs: string[];
  candidate_exception_lake_labels: string[];
};

export type BudgetLearningLoopActualsSummary = {
  status: "variance_review_required" | "actuals_not_available" | "actuals_within_threshold";
  comparison_scope: string;
  total_budgeted: number | null;
  total_actual: number | null;
  total_variance_amount: number | null;
  total_variance_percent: number | null;
  phase_event_count: number;
  code_event_count: number;
  revision_context_event_count: number;
  variance_review_event_count: number;
  actuals_without_budget_event_count: number;
  missing_actuals_event_count: number;
  ledger_entry_count: number;
  learning_disposition_candidates: string[];
};

export type BudgetLearningLoopCarrierRejectionSummary = {
  reconciliation_status: string;
  decision_ledger_status: string;
  expected_response_count: number;
  reconciled_response_count: number;
  missing_response_count: number;
  unlinked_notice_count: number;
  duplicate_notice_count: number;
  parser_failure_count: number;
  appeal_result_count: number;
  remediation_case_count: number;
  decision_ledger_entry_count: number;
  pending_decision_event_count: number;
  total_disputed_amount: number;
  total_recovered_amount: number;
  total_write_down_amount: number;
  candidate_event_labels: string[];
};

export type BudgetLearningLoopReviewedGateSummary = {
  status: string;
  candidate_count: number;
  carrier_learning_candidate_count: number;
  budget_revision_candidate_count: number;
  budget_actual_variance_candidate_count: number;
  target_learning_loops: string[];
  target_owners: string[];
  reviewed_outcome_required: boolean;
  shadow_eval_required: boolean;
};

export type BudgetLearningLoopReport = {
  schema_version: string;
  budget_learning_loop_report_id: string;
  status:
    | "budget_learning_loop_ready_for_review"
    | "blocked_by_budget_learning_loop"
    | "failed_budget_learning_loop_boundary";
  run_id: string;
  preflight_packet_id: string;
  source_budget_actual_comparison_report_ref: string;
  source_budget_actual_variance_ledger_report_ref: string;
  source_carrier_rejection_reconciliation_report_ref: string;
  source_carrier_rejection_decision_ledger_report_ref: string;
  source_carrier_rejection_review_packet_ref: string;
  source_carrier_rejection_learning_report_ref: string;
  source_reviewed_learning_gate_report_ref: string;
  budget_proposal_id: string;
  comparison_budget_state: string;
  actuals: BudgetLearningLoopActualsSummary;
  carrier_rejections: BudgetLearningLoopCarrierRejectionSummary;
  reviewed_learning_gate: BudgetLearningLoopReviewedGateSummary;
  lifecycle_lanes: BudgetLearningLoopLane[];
  red_team_notes: string[];
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  appeal_submission_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type SyntheticQABlockerRowState = "failed" | "blocked" | "pending_review";

export type SyntheticQABlockerActionState = "blocked" | "needs_review" | "fixed" | "ready";

export type SyntheticQABlockerRowSource =
  | "quality_gate"
  | "qa_step"
  | "readiness_item"
  | "top_blocker";

export type SyntheticQABlockerRow = {
  row_id: string;
  source: SyntheticQABlockerRowSource;
  label: string;
  state: SyntheticQABlockerRowState;
  action_state: SyntheticQABlockerActionState;
  owner: string;
  evidence_refs: string[];
  recommended_next_action: string;
  candidate_exception_lake_labels: string[];
  notes: string[];
};

export type SyntheticQABlockerReport = {
  schema_version: string;
  synthetic_qa_blocker_report_id: string;
  status:
    | "synthetic_qa_blocker_report_ready_for_review"
    | "blocked_by_synthetic_qa_blocker_report"
    | "failed_synthetic_qa_blocker_boundary";
  source_ui_manifest_ref: string;
  source_ui_manifest_id: string;
  source_ui_manifest_overall_status: string;
  source_synthetic_confidence_summary_ref: string;
  source_synthetic_confidence_summary_report_id: string;
  source_synthetic_confidence_summary_status: string;
  source_synthetic_qa_review_run_ref: string;
  source_synthetic_qa_review_run_report_id: string;
  source_synthetic_qa_review_run_status: string;
  row_count: number;
  failed_row_count: number;
  blocked_row_count: number;
  pending_review_row_count: number;
  blocked_action_count: number;
  needs_review_action_count: number;
  fixed_action_count: number;
  ready_action_count: number;
  review_queue_state: "blocked" | "needs_review" | "ready";
  rows: SyntheticQABlockerRow[];
  required_next_actions: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type SyntheticQAReviewOutcomeStatus =
  | "synthetic_qa_review_outcome_recorded"
  | "synthetic_qa_review_outcome_recorded_pending_followup"
  | "blocked_by_synthetic_qa_review_outcome";

export type SyntheticQAReviewOutcomeReport = {
  schema_version: string;
  synthetic_qa_review_outcome_report_id: string;
  status: SyntheticQAReviewOutcomeStatus;
  source_synthetic_qa_blocker_report_ref: string;
  source_synthetic_qa_blocker_report_id: string;
  source_synthetic_qa_blocker_report_status: string;
  synthetic_qa_review_outcome_record_id: string;
  reviewer_id: string;
  reviewed_at: string;
  decision_reason: string;
  source_row_count: number;
  decision_count: number;
  accepted_decision_count: number;
  needs_fix_decision_count: number;
  deferred_decision_count: number;
  not_applicable_decision_count: number;
  reviewed_row_count: number;
  unreviewed_row_count: number;
  unknown_row_count: number;
  unresolved_followup_count: number;
  reviewed_row_ids: string[];
  unreviewed_row_ids: string[];
  unknown_row_ids: string[];
  required_followups: string[];
  candidate_lake_event_labels: string[];
  append_only_history_ref: string;
  required_next_actions: string[];
  append_only: boolean;
  candidate_only: boolean;
  synthetic_only: boolean;
  non_authoritative: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentQAMatrixCase = {
  case_id: string;
  label: string;
  status: "passed" | "failed";
  manifest_ref: string;
  fact_report_ref: string;
  expected_budget_readiness_state: LaborEmploymentBudgetReadinessState;
  actual_budget_readiness_state: LaborEmploymentBudgetReadinessState;
  expected_budget_gate_effect: LaborEmploymentBudgetGateEffect;
  actual_budget_gate_effect: LaborEmploymentBudgetGateEffect;
  critical_gap_count: number;
  gap_count: number;
  source_bound_finding_count: number;
  unknown_finding_count: number;
  needs_review_finding_count: number;
  relationship_budget_treatment:
    | "block_amount_budget"
    | "hours_only_or_broad_range"
    | "candidate_range_budget_after_review";
  critical_relationship_gap_count: number;
  required_human_question_count: number;
  notes: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
};

export type LaborEmploymentQAMatrixReport = {
  schema_version: string;
  labor_employment_qa_matrix_report_id: string;
  status: "labor_employment_qa_matrix_ready_for_review" | "blocked_by_labor_employment_qa_matrix";
  case_count: number;
  failed_case_count: number;
  cases: LaborEmploymentQAMatrixCase[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentExecutableCoverageState =
  | "partial_executable_coverage"
  | "complete_executable_coverage";

export type LaborEmploymentExecutableCoverageStatus =
  | "labor_employment_executable_coverage_ready_for_review"
  | "blocked_labor_employment_executable_coverage";

export type LaborEmploymentExecutableCoverageCase = {
  pack_case_id: string;
  family: string;
  variant: string;
  coverage_state: "covered_executable" | "missing_executable";
  executable_fixture_ids: string[];
  expected_budget_readiness_state: LaborEmploymentBudgetReadinessState;
  expected_budget_treatment:
    | "block_amount_budget"
    | "hours_only_or_broad_range"
    | "candidate_range_budget_after_review";
  missing_critical_fact_ids: string[];
  missing_important_fact_ids: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
};

export type LaborEmploymentExecutableCoverageFamily = {
  family: string;
  pack_case_count: number;
  covered_case_count: number;
  missing_case_count: number;
  covered_variants: string[];
  missing_variants: string[];
  executable_fixture_ids: string[];
};

export type LaborEmploymentExecutableCoverageCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentExecutableCoverageReport = {
  schema_version: string;
  executable_coverage_report_id: string;
  status: LaborEmploymentExecutableCoverageStatus;
  coverage_state: LaborEmploymentExecutableCoverageState;
  pack_id: string;
  pack_ref: string;
  executable_manifest_id: string;
  executable_manifest_ref: string;
  pack_case_count: number;
  executable_fixture_count: number;
  executable_pack_case_link_count: number;
  covered_pack_case_count: number;
  missing_executable_pack_case_count: number;
  covered_family_count: number;
  missing_family_count: number;
  covered_family_variant_count: number;
  missing_family_variant_count: number;
  covered_pack_case_ids: string[];
  missing_executable_pack_case_ids: string[];
  missing_family_variant_refs: string[];
  family_coverage: LaborEmploymentExecutableCoverageFamily[];
  case_coverage: LaborEmploymentExecutableCoverageCase[];
  checks: LaborEmploymentExecutableCoverageCheck[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  fixture_generation_authorized: boolean;
  calibration_approved: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBlockedDriverImpactCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentFactResolutionState =
  | "missing_critical_fact"
  | "missing_noncritical_fact"
  | "source_present_needs_confirmation"
  | "source_present_unresolved_critical_driver"
  | "source_present_unresolved_driver"
  | "inventory_present_needs_confirmation"
  | "unbound_fact_gap";

export type LaborEmploymentBlockedDriverImpactFactReview = {
  fact_id: string;
  required_level: "critical";
  binding_state:
    | "source_bound_gap_candidate"
    | "exception_bound_gap_candidate"
    | "source_and_exception_bound_gap_candidate"
    | "inventory_bound_gap_candidate"
    | "unbound_gap_candidate";
  fact_resolution_state: LaborEmploymentFactResolutionState;
  blocks_precise_budget: boolean;
  reason: string;
  budget_effects: string[];
  evidence_ref_count: number;
  source_inventory_ref_count: number;
  matched_source_signal_terms: string[];
  missing_source_signal_terms: string[];
  matched_exception_labels: string[];
  missing_exception_labels: string[];
  matched_source_ids: string[];
  missing_source_ids: string[];
  unblock_actions: string[];
  candidate_exception_lake_labels: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
};

export type LaborEmploymentBlockedDriverImpactCaseReview = {
  executable_fixture_id: string;
  family: string;
  variant: string;
  allowed_budget_output: "blocked_amount_budget";
  block_reason: string;
  block_amount_budget_impact_count: number;
  range_widening_impact_count: number;
  scenario_fork_impact_count: number;
  rate_guideline_review_impact_count: number;
  critical_driver_dimensions: string[];
  blocker_fact_count: number;
  blocker_facts: LaborEmploymentBlockedDriverImpactFactReview[];
  candidate_exception_lake_labels: string[];
  unblock_actions: string[];
  next_review_gates: string[];
  candidate_only: boolean;
  synthetic_only: boolean;
  amount_budget_blocked: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
};

export type LaborEmploymentBlockedDriverImpactReviewReport = {
  schema_version: string;
  blocked_driver_impact_review_report_id: string;
  status:
    | "labor_employment_blocked_driver_impacts_ready_for_review"
    | "blocked_by_labor_employment_blocked_driver_impact_review";
  source_fact_binding_report_ref: string;
  source_driver_binding_report_ref: string;
  source_driver_impact_report_ref: string;
  source_driver_impact_report_id: string;
  case_count: number;
  blocked_case_count: number;
  nonblocking_case_count: number;
  blocker_fact_count: number;
  block_amount_budget_impact_count: number;
  candidate_exception_lake_labels: string[];
  case_reviews: LaborEmploymentBlockedDriverImpactCaseReview[];
  checks: LaborEmploymentBlockedDriverImpactCheck[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentAllowedBudgetOutput =
  | "blocked_amount_budget"
  | "range_or_hours_only_pending_review"
  | "candidate_range_after_review_pending_human_review";

export type LaborEmploymentSyntheticFixtureFamily =
  | "discrimination_harassment"
  | "retaliation_wrongful_termination"
  | "wage_hour_flsa_state"
  | "ada_fmla_accommodation_leave"
  | "restrictive_covenant_trade_secret"
  | "epli_carrier_assignment"
  | "class_collective_paga_representative"
  | "administrative_exhaustion_agency_record";

export type LaborEmploymentSyntheticFixtureVariant =
  | "clean"
  | "messy_thread"
  | "missing_attachment"
  | "adversarial";

export type LaborEmploymentBudgetOutputExpectationState =
  | "blocked_amount_budget_pending_driver_review"
  | "range_or_hours_only_pending_human_review"
  | "candidate_range_after_review_pending_human_review";

export type LaborEmploymentBudgetOutputExpectationCase = {
  executable_fixture_id: string;
  family: string;
  variant: string;
  status: "passed" | "failed";
  expected_budget_readiness_state: LaborEmploymentBudgetReadinessState;
  expected_budget_treatment:
    | "block_amount_budget"
    | "hours_only_or_broad_range"
    | "candidate_range_budget_after_review";
  source_allowed_budget_output: LaborEmploymentAllowedBudgetOutput;
  final_allowed_budget_output: LaborEmploymentAllowedBudgetOutput;
  expectation_state: LaborEmploymentBudgetOutputExpectationState;
  selected_for_reviewed_nonblocking_slice: boolean;
  blocked_case_review_present: boolean;
  amount_budget_blocked: boolean;
  block_amount_budget_impact_count: number;
  critical_review_only_impact_count: number;
  range_widening_impact_count: number;
  scenario_fork_impact_count: number;
  rate_guideline_review_impact_count: number;
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  evidence_refs: string[];
  failure_ids: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutputExpectationReport = {
  schema_version: string;
  budget_output_expectation_report_id: string;
  status:
    | "labor_employment_budget_output_expectations_ready_for_review"
    | "blocked_by_labor_employment_budget_output_expectations";
  source_driver_impact_report_ref: string;
  source_driver_impact_report_id: string;
  source_driver_impact_review_report_ref: string;
  source_driver_impact_review_report_id: string;
  source_blocked_driver_impact_review_report_ref: string;
  source_blocked_driver_impact_review_report_id: string;
  case_count: number;
  failed_case_count: number;
  blocked_amount_budget_case_count: number;
  range_or_hours_only_case_count: number;
  candidate_range_after_review_case_count: number;
  reviewed_nonblocking_case_count: number;
  blocked_review_case_count: number;
  candidate_exception_lake_labels: string[];
  cases: LaborEmploymentBudgetOutputExpectationCase[];
  checks: LaborEmploymentBlockedDriverImpactCheck[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetQAGateBucket = {
  output_state: LaborEmploymentAllowedBudgetOutput;
  case_count: number;
  executable_fixture_ids: string[];
};

export type LaborEmploymentBudgetQAGateCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBudgetQAGateReport = {
  schema_version: string;
  budget_qa_gate_report_id: string;
  status:
    | "labor_employment_budget_qa_gate_ready_for_review"
    | "blocked_by_labor_employment_budget_qa_gate";
  source_budget_output_expectations_report_ref: string;
  source_budget_output_expectations_report_id: string;
  source_budget_output_expectations_report_status: string;
  source_blocked_driver_impact_review_report_ref: string;
  source_blocked_driver_impact_review_report_id: string;
  source_blocked_driver_impact_review_report_status: string;
  source_executable_coverage_report_ref: string;
  source_executable_coverage_report_id: string;
  source_executable_coverage_report_status: string;
  source_executable_coverage_state: string;
  case_count: number;
  executable_fixture_count: number;
  covered_pack_case_count: number;
  missing_executable_pack_case_count: number;
  blocked_amount_budget_case_count: number;
  range_or_hours_only_case_count: number;
  candidate_range_after_review_case_count: number;
  reviewed_nonblocking_case_count: number;
  blocked_review_case_count: number;
  required_family_count: number;
  covered_required_family_count: number;
  blocked_case_ids: string[];
  range_or_hours_only_case_ids: string[];
  candidate_range_after_review_case_ids: string[];
  reviewed_nonblocking_case_ids: string[];
  missing_blocked_review_case_ids: string[];
  missing_nonblocking_review_case_ids: string[];
  required_families_present: string[];
  required_families_missing: string[];
  output_state_buckets: LaborEmploymentBudgetQAGateBucket[];
  checks: LaborEmploymentBudgetQAGateCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_amount_output_authorized: boolean;
  budget_submission_authorized: boolean;
  conflict_conclusion_emitted: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetLearningLoopType =
  | "actuals_variance"
  | "carrier_rejection_capture"
  | "appeal_outcome"
  | "reviewed_learning_gate"
  | "blocked_budget_guard";

export type LaborEmploymentBudgetLearningFixtureCase = {
  learning_fixture_id: string;
  executable_fixture_id: string;
  family: string;
  variant: string;
  status: "passed" | "failed";
  expected_budget_output_state: LaborEmploymentAllowedBudgetOutput;
  observed_budget_output_state: LaborEmploymentAllowedBudgetOutput | null;
  learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  expected_candidate_exception_lake_labels: string[];
  expected_learning_targets: string[];
  evidence_refs: string[];
  failure_ids: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetLearningFixtureCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBudgetLearningFixtureReport = {
  schema_version: string;
  budget_learning_fixture_report_id: string;
  status:
    | "labor_employment_budget_learning_fixtures_ready_for_review"
    | "blocked_by_labor_employment_budget_learning_fixtures";
  source_manifest_ref: string;
  source_manifest_id: string;
  source_budget_qa_gate_report_ref: string;
  source_budget_qa_gate_report_id: string;
  source_budget_qa_gate_report_status: string;
  fixture_count: number;
  failed_case_count: number;
  required_family_count: number;
  covered_required_family_count: number;
  missing_required_families: string[];
  covered_budget_output_states: LaborEmploymentAllowedBudgetOutput[];
  missing_budget_output_states: LaborEmploymentAllowedBudgetOutput[];
  covered_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  blocked_budget_guard_fixture_count: number;
  actuals_variance_fixture_count: number;
  carrier_rejection_fixture_count: number;
  appeal_outcome_fixture_count: number;
  reviewed_learning_gate_fixture_count: number;
  cases: LaborEmploymentBudgetLearningFixtureCase[];
  checks: LaborEmploymentBudgetLearningFixtureCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  red_team_notes: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetOutcomeReplayReadinessCase = {
  learning_fixture_id: string;
  executable_fixture_id: string;
  family: string;
  variant: string;
  status: "passed" | "failed";
  expected_budget_output_state: LaborEmploymentAllowedBudgetOutput;
  observed_budget_output_state: LaborEmploymentAllowedBudgetOutput | null;
  outcome_seed_id: string | null;
  required_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  seeded_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  extra_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_replay_seed_ref_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_expected_artifact_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_candidate_label_loop_types: LaborEmploymentBudgetLearningLoopType[];
  unresolved_source_refs: string[];
  expected_replay_artifacts: string[];
  candidate_exception_lake_labels: string[];
  evidence_refs: string[];
  failure_ids: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  human_review_required: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayReadinessCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBudgetOutcomeReplayReadinessReport = {
  schema_version: string;
  outcome_replay_readiness_report_id: string;
  status:
    | "labor_employment_budget_outcome_replay_ready_for_review"
    | "blocked_by_labor_employment_budget_outcome_replay";
  source_seed_manifest_ref: string;
  source_seed_manifest_id: string;
  source_learning_fixture_report_ref: string;
  source_learning_fixture_report_id: string;
  source_learning_fixture_report_status: string;
  fixture_count: number;
  seed_spec_count: number;
  failed_case_count: number;
  loop_requirement_count: number;
  seeded_loop_requirement_count: number;
  missing_loop_requirement_count: number;
  unresolved_source_ref_count: number;
  expected_replay_artifact_count: number;
  covered_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  cases: LaborEmploymentBudgetOutcomeReplayReadinessCase[];
  checks: LaborEmploymentBudgetOutcomeReplayReadinessCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  red_team_notes: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetOutcomeReplayExecutionArtifact = {
  loop_type: LaborEmploymentBudgetLearningLoopType;
  expected_artifact_name: string;
  artifact_slot_ref: string;
  artifact_slot_status: "materialized_candidate_slot" | "blocked_not_materialized";
  evidence_refs: string[];
  runtime_artifact_created: boolean;
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayExecutionCase = {
  execution_case_id: string;
  learning_fixture_id: string;
  executable_fixture_id: string;
  outcome_seed_id: string | null;
  family: LaborEmploymentSyntheticFixtureFamily;
  variant: LaborEmploymentSyntheticFixtureVariant;
  status: "passed" | "failed";
  expected_budget_output_state: LaborEmploymentAllowedBudgetOutput;
  replay_case_dir: string;
  required_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  materialized_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  blocked_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  expected_artifact_slot_count: number;
  materialized_artifact_slot_count: number;
  artifact_slots: LaborEmploymentBudgetOutcomeReplayExecutionArtifact[];
  candidate_exception_lake_labels: string[];
  evidence_refs: string[];
  failure_ids: string[];
  runtime_artifacts_created: boolean;
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayExecutionCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBudgetOutcomeReplayExecutionReport = {
  schema_version: string;
  outcome_replay_execution_report_id: string;
  status:
    | "labor_employment_budget_outcome_replay_execution_ready_for_review"
    | "blocked_by_labor_employment_budget_outcome_replay_execution";
  source_seed_manifest_ref: string;
  source_seed_manifest_id: string;
  source_readiness_report_ref: string;
  source_readiness_report_id: string;
  source_readiness_report_status: string;
  fixture_count: number;
  materialized_case_count: number;
  failed_case_count: number;
  expected_artifact_slot_count: number;
  materialized_artifact_slot_count: number;
  runtime_artifact_count: number;
  covered_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  missing_learning_loop_types: LaborEmploymentBudgetLearningLoopType[];
  cases: LaborEmploymentBudgetOutcomeReplayExecutionCase[];
  checks: LaborEmploymentBudgetOutcomeReplayExecutionCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  red_team_notes: string[];
  runtime_artifacts_created: boolean;
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetOutcomeReplayBuilderContract = {
  artifact_name: string;
  loop_type: LaborEmploymentBudgetLearningLoopType;
  builder_module: string;
  builder_function: string;
  emitted_output_filenames: string[];
  required_input_artifacts: string[];
  intermediate_artifacts: string[];
  side_effect_boundary: "local_candidate_files_only";
  authority_owner: "LawFirm-os-intake";
  execution_owner: "LawFirm-os-orchestrator";
  creates_runtime_artifact: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayBuilderBinding = {
  binding_id: string;
  execution_case_id: string;
  learning_fixture_id: string;
  executable_fixture_id: string;
  outcome_seed_id: string | null;
  loop_type: LaborEmploymentBudgetLearningLoopType;
  expected_artifact_name: string;
  artifact_slot_ref: string;
  artifact_slot_status: "materialized_candidate_slot" | "blocked_not_materialized";
  binding_status:
    | "bound_to_existing_builder"
    | "blocked_unknown_artifact"
    | "blocked_slot_not_materialized";
  builder_module: string | null;
  builder_function: string | null;
  emitted_output_filenames: string[];
  required_input_artifacts: string[];
  intermediate_artifacts: string[];
  missing_case_prerequisite_artifacts: string[];
  replay_input_gap_ids: string[];
  side_effect_boundary: string | null;
  binding_notes: string[];
  evidence_refs: string[];
  runtime_artifact_created: boolean;
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayBuilderBindingCase = {
  binding_case_id: string;
  execution_case_id: string;
  learning_fixture_id: string;
  executable_fixture_id: string;
  outcome_seed_id: string | null;
  family: LaborEmploymentSyntheticFixtureFamily;
  variant: LaborEmploymentSyntheticFixtureVariant;
  status: "passed" | "failed";
  expected_budget_output_state: LaborEmploymentAllowedBudgetOutput;
  slot_count: number;
  bound_slot_count: number;
  unknown_artifact_count: number;
  blocked_slot_count: number;
  replay_input_gap_count: number;
  missing_case_prerequisite_count: number;
  bindings: LaborEmploymentBudgetOutcomeReplayBuilderBinding[];
  evidence_refs: string[];
  failure_ids: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBudgetOutcomeReplayBuilderBindingReport = {
  schema_version: string;
  builder_binding_report_id: string;
  status:
    | "labor_employment_budget_replay_builder_binding_ready_for_review"
    | "blocked_by_labor_employment_budget_replay_builder_binding";
  source_execution_report_ref: string;
  source_execution_report_id: string;
  source_execution_report_status: string;
  fixture_count: number;
  case_count: number;
  passed_case_count: number;
  failed_case_count: number;
  slot_count: number;
  bound_slot_count: number;
  unknown_artifact_count: number;
  blocked_slot_count: number;
  replay_input_gap_count: number;
  missing_case_prerequisite_count: number;
  builder_contracts: LaborEmploymentBudgetOutcomeReplayBuilderContract[];
  cases: LaborEmploymentBudgetOutcomeReplayBuilderBindingCase[];
  checks: LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck[];
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  red_team_notes: string[];
  runtime_artifacts_created: boolean;
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type LaborEmploymentBudgetOutcomeReplayConfidenceStageStatus =
  | "ready"
  | "pending_inputs"
  | "blocked";

export type LaborEmploymentBudgetOutcomeReplayConfidenceStage = {
  stage_id: "readiness" | "execution" | "builder_binding" | "input_pack";
  label: string;
  source_report_ref: string;
  source_report_id: string;
  source_report_status: string;
  status: LaborEmploymentBudgetOutcomeReplayConfidenceStageStatus;
  counts: Record<string, number>;
  blocker_count: number;
  blockers: string[];
  evidence_refs: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
};

export type LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport = {
  schema_version: string;
  replay_confidence_status_report_id: string;
  status:
    | "labor_employment_budget_outcome_replay_confidence_ready_for_review"
    | "labor_employment_budget_outcome_replay_confidence_pending_inputs"
    | "blocked_by_labor_employment_budget_outcome_replay_confidence";
  source_readiness_report_ref: string;
  source_readiness_report_id: string;
  source_readiness_report_status: string;
  source_execution_report_ref: string;
  source_execution_report_id: string;
  source_execution_report_status: string;
  source_builder_binding_report_ref: string;
  source_builder_binding_report_id: string;
  source_builder_binding_report_status: string;
  source_input_pack_report_ref: string;
  source_input_pack_report_id: string;
  source_input_pack_report_status: string;
  fixture_count: number;
  stage_count: number;
  ready_stage_count: number;
  pending_stage_count: number;
  blocked_stage_count: number;
  readiness_failed_case_count: number;
  execution_failed_case_count: number;
  builder_replay_input_gap_count: number;
  builder_missing_case_prerequisite_count: number;
  input_pack_missing_input_count: number;
  input_pack_invalid_input_count: number;
  stages: LaborEmploymentBudgetOutcomeReplayConfidenceStage[];
  top_blockers: string[];
  display_banner: {
    status: string;
    candidate_only: boolean;
    blocked_actions: string[];
    summary: string;
  };
  candidate_exception_lake_labels: string[];
  required_next_gates: string[];
  red_team_notes: string[];
  rust_transition_candidates: string[];
  candidate_only: boolean;
  non_authoritative: boolean;
  synthetic_only: boolean;
  local_json_only: boolean;
  human_review_required: boolean;
  not_authorized_for_external_write: boolean;
  not_authorized_for_lake_write: boolean;
  not_authorized_for_sqlite_write: boolean;
  not_authorized_for_budget_submission: boolean;
  not_authorized_for_matter_opening: boolean;
  not_authorized_for_calibration: boolean;
  budget_submission_authorized: boolean;
  matter_opening_authorized: boolean;
  training_pipeline_created: boolean;
  lake_write_performed: boolean;
  sqlite_write_performed: boolean;
  external_writes_performed: boolean;
  silent_learning_performed: boolean;
  generated_at: string;
};

export type ReviewArtifact = {
  artifactId: string;
  label: string;
  fileName: string;
  status: ArtifactStatus;
  owner: string;
  gateState: GateState;
  candidateOnly: boolean;
  externalWritesPerformed: boolean;
  notes: string[];
};

export type BoundaryFlags = {
  readOnly: boolean;
  localJsonOnly: boolean;
  networkCallsAllowed: boolean;
  mutationCommandsAllowed: boolean;
  exceptionLakeWritesAllowed: boolean;
  sqliteWritesAllowed: boolean;
  publicRuntimeIngestionAllowed: boolean;
  budgetSubmissionAllowed: boolean;
  matterOpeningAllowed: boolean;
};

export type ReviewManifest = {
  manifestId: string;
  generatedAt: string;
  runLabel: string;
  practiceArea: string;
  matterFamily: string;
  overallStatus: GateState;
  boundaryFlags: BoundaryFlags;
  artifacts: ReviewArtifact[];
  qualityGates: QualityGate[];
  blockerSummary: string[];
  redTeamNotes: string[];
};

export type CrosswalkAuditReport = {
  report_id: string;
  status: string;
  acceptance_gate_status: string;
  crosswalk_count: number;
  entry_count: number;
  mapped_entry_count: number;
  unmapped_entry_count: number;
  canonical_claim_count: number;
  guessed_mapping_count: number;
  unverified_pinned_target_count: number;
  candidate_target_prefix_violation_count: number;
  workflow_dependency_violation_count: number;
  display_banner: Record<string, unknown>;
  prohibited_actions: string[];
  candidate_only: boolean;
  not_promoted_canon: boolean;
  not_authorized_for_canonical_use: boolean;
  not_authorized_for_budget_logic: boolean;
};

export type OCGRuleIRAdoptionReport = {
  report_id: string;
  status: string;
  acceptance_gate_status: string;
  rule_ir_id: string;
  source_owner: string;
  source_artifact_ref: string;
  budget_proposal_id: string;
  carrier_projection_id: string;
  carrier: string;
  proposed_total_before: number | null;
  carrier_compliant_total: number | null;
  projection_total_delta: number | null;
  rule_count: number;
  impact_line_count: number;
  canonical_rule_id_violation_count: number;
  rewrite_budget_violation_count: number;
  real_guideline_or_rate_violation_count: number;
  budget_projection_mismatch_count: number;
  display_banner: Record<string, unknown>;
  prohibited_actions: string[];
  read_only_consumption: boolean;
  candidate_only: boolean;
  not_promoted_canon: boolean;
  not_authorized_for_canonical_use: boolean;
  not_authorized_for_budget_rewrite: boolean;
  not_authorized_for_external_submission: boolean;
};
