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
  | "labor_employment_qa_matrix"
  | "labor_employment_blocked_driver_impact_review";

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

export type LaborEmploymentBlockedDriverImpactCheck = {
  check_id: string;
  status: "passed" | "failed";
  message: string;
  evidence_refs: string[];
  blocking_refs: string[];
};

export type LaborEmploymentBlockedDriverImpactFactReview = {
  fact_id: string;
  required_level: "critical";
  binding_state:
    | "source_bound_gap_candidate"
    | "exception_bound_gap_candidate"
    | "source_and_exception_bound_gap_candidate"
    | "inventory_bound_gap_candidate"
    | "unbound_gap_candidate";
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
