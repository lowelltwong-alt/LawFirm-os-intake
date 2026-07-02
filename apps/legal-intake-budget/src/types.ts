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
