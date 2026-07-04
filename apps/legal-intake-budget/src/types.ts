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
  | "matter_linking_preflight"
  | "matter_linking_review_outcome"
  | "matter_linking_qa_gate"
  | "labor_employment_qa_matrix"
  | "labor_employment_executable_coverage"
  | "labor_employment_blocked_driver_impact_review"
  | "labor_employment_budget_output_expectations"
  | "labor_employment_budget_qa_gate";

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
