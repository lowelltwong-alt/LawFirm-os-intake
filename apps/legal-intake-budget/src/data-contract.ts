import type {
  BoundaryFlags,
  LaborEmploymentBudgetOutputExpectationReport,
  LaborEmploymentBlockedDriverImpactReviewReport,
  LaborEmploymentExecutableCoverageReport,
  LaborEmploymentQAMatrixReport,
  MatterLinkingPreflightReport,
  POCQATriageReport,
  QualityGate,
  ReviewArtifact,
  ReviewManifest,
  SyntheticQABlockerReport,
  SyntheticQAReviewOutcomeReport,
  SyntheticConfidenceSummaryReport,
  SyntheticQAReviewRunReport,
  UIReviewDataBundle,
  ValidationSuiteEvidenceReport,
} from "./types";

export const REQUIRED_ARTIFACT_FILES = [
  "intake_preflight_packet.json",
  "human_gate_status_report.json",
  "conflict_search_seed_packet.json",
  "legal_budget_proposal.json",
  "matter_opening_readiness.json",
  "budget_submission_guard_report.json",
  "exception_lake_handoff_manifest.json",
  "run_ledger_integrity_report.json",
  "budget_coherence_report.json",
  "synthetic_qa_bundle_report.json",
  "synthetic_qa_review_run_report.json",
  "synthetic_confidence_summary_report.json",
  "poc_qa_triage_report.json",
  "synthetic_qa_blocker_report.json",
  "matter_linking_preflight_report.json",
  "synthetic_fixture_depth_audit_report.json",
  "budget_calibration_readiness_report.json",
  "budget_calibration_starter_pack_report.json",
  "labor_employment_qa_matrix_report.json",
  "labor_employment_fixture_family_pack_report.json",
  "labor_employment_executable_fixtures_report.json",
  "labor_employment_executable_coverage_report.json",
  "labor_employment_executable_fact_binding_report.json",
  "labor_employment_executable_driver_binding_report.json",
  "labor_employment_executable_driver_impact_report.json",
  "labor_employment_driver_impact_review_report.json",
  "labor_employment_blocked_driver_impact_review_report.json",
  "labor_employment_budget_output_expectations_report.json",
  "labor_employment_budget_fact_gold_report.json",
  "validation_suite_evidence_report.json",
  "budget_human_review_packet.json",
  "carrier_rejection_decision_ledger_report.json",
  "budget_actual_variance_ledger_report.json",
  "public_source_methodology_report.json",
  "public_data_cache_audit_report.json",
] as const;

export const REQUIRED_BOUNDARY_FLAGS: BoundaryFlags = {
  readOnly: true,
  localJsonOnly: true,
  networkCallsAllowed: false,
  mutationCommandsAllowed: false,
  exceptionLakeWritesAllowed: false,
  sqliteWritesAllowed: false,
  publicRuntimeIngestionAllowed: false,
  budgetSubmissionAllowed: false,
  matterOpeningAllowed: false,
};

export const REQUIRED_DETAIL_REPORT_FILES = [
  "ui_review_manifest.json",
  "matter_linking_preflight_report.json",
  "synthetic_confidence_summary_report.json",
  "labor_employment_qa_matrix_report.json",
  "labor_employment_executable_coverage_report.json",
  "labor_employment_blocked_driver_impact_review_report.json",
  "labor_employment_budget_output_expectations_report.json",
] as const;

export function missingRequiredArtifacts(artifacts: ReviewArtifact[]): string[] {
  const available = new Set(artifacts.map((artifact) => artifact.fileName));
  return REQUIRED_ARTIFACT_FILES.filter((fileName) => !available.has(fileName));
}

export function assertReadOnlyManifest(manifest: ReviewManifest): string[] {
  const failures: string[] = [];
  const missing = missingRequiredArtifacts(manifest.artifacts);
  if (missing.length > 0) {
    failures.push(`missing_artifacts:${missing.join(",")}`);
  }
  for (const [key, expected] of Object.entries(REQUIRED_BOUNDARY_FLAGS)) {
    const actual = manifest.boundaryFlags[key as keyof BoundaryFlags];
    if (actual !== expected) {
      failures.push(`boundary_flag_mismatch:${key}`);
    }
  }
  for (const artifact of manifest.artifacts) {
    if (!artifact.candidateOnly) {
      failures.push(`artifact_not_candidate_only:${artifact.artifactId}`);
    }
    if (artifact.externalWritesPerformed) {
      failures.push(`artifact_external_write:${artifact.artifactId}`);
    }
  }
  for (const gate of manifest.qualityGates) {
    if (gate.status === "failed") {
      failures.push(`quality_gate_failed:${gate.gateId}`);
    }
    if (!gate.evidenceFile) {
      failures.push(`quality_gate_missing_evidence:${gate.gateId}`);
    }
  }
  return failures;
}

export function failingQualityGates(gates: QualityGate[]): QualityGate[] {
  return gates.filter((gate) => gate.status === "failed" || gate.status === "blocked");
}

export function assertUIReviewDataBundle(bundle: UIReviewDataBundle): string[] {
  const failures: string[] = [];
  if (!bundle.candidate_only || !bundle.synthetic_only || !bundle.non_authoritative) {
    failures.push("ui_review_bundle_authority_boundary_failed");
  }
  if (!bundle.local_json_only) {
    failures.push("ui_review_bundle_not_local_json_only");
  }
  if (
    bundle.budget_amount_output_authorized ||
    bundle.budget_submission_authorized ||
    bundle.conflict_conclusion_emitted ||
    bundle.matter_opening_authorized ||
    bundle.training_pipeline_created ||
    bundle.lake_write_performed ||
    bundle.sqlite_write_performed ||
    bundle.external_writes_performed ||
    bundle.silent_learning_performed
  ) {
    failures.push("ui_review_bundle_side_effect_boundary_failed");
  }
  if (bundle.detail_report_count !== bundle.detail_reports.length) {
    failures.push("ui_review_bundle_detail_count_mismatch");
  }
  const required = bundle.detail_reports.filter((report) => report.required);
  const present = bundle.detail_reports.filter((report) => report.present);
  const missingRequired = required.filter((report) => !report.present);
  const externalWriteReports = bundle.detail_reports.filter(
    (report) => report.external_writes_performed,
  );
  if (bundle.required_detail_report_count !== required.length) {
    failures.push("ui_review_bundle_required_count_mismatch");
  }
  if (bundle.present_detail_report_count !== present.length) {
    failures.push("ui_review_bundle_present_count_mismatch");
  }
  if (bundle.missing_required_detail_report_count !== missingRequired.length) {
    failures.push("ui_review_bundle_missing_required_count_mismatch");
  }
  if (bundle.external_write_report_count !== externalWriteReports.length) {
    failures.push("ui_review_bundle_external_write_count_mismatch");
  }
  for (const requiredFile of REQUIRED_DETAIL_REPORT_FILES) {
    if (!bundle.detail_reports.some((report) => report.file_name === requiredFile)) {
      failures.push(`ui_review_bundle_missing_detail:${requiredFile}`);
    }
  }
  for (const report of bundle.detail_reports) {
    if (report.required && !report.present) {
      failures.push(`ui_review_bundle_required_detail_missing:${report.file_name}`);
    }
    if (!report.candidate_only || !report.synthetic_only || report.external_writes_performed) {
      failures.push(`ui_review_bundle_detail_boundary_failed:${report.file_name}`);
    }
    if (report.present && !report.source_sha256?.startsWith("sha256:")) {
      failures.push(`ui_review_bundle_detail_missing_hash:${report.file_name}`);
    }
  }
  if (bundle.status !== "ready_for_review") {
    failures.push(`ui_review_bundle_not_ready:${bundle.status}`);
  }
  return failures;
}

export function assertSyntheticQAReviewRunReport(
  report: SyntheticQAReviewRunReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.synthetic_only || !report.non_authoritative) {
    failures.push("synthetic_qa_review_run_authority_boundary_failed");
  }
  if (!report.local_json_only) {
    failures.push("synthetic_qa_review_run_not_local_json_only");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.calibration_applied ||
    report.fixture_files_mutated ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("synthetic_qa_review_run_side_effect_boundary_failed");
  }
  if (report.step_count !== report.steps.length) {
    failures.push("synthetic_qa_review_run_step_count_mismatch");
  }
  const failedSteps = report.steps.filter((step) => step.status === "failed");
  if (report.failed_step_count !== failedSteps.length) {
    failures.push("synthetic_qa_review_run_failed_step_count_mismatch");
  }
  if (report.status === "synthetic_qa_review_run_ready" && failedSteps.length > 0) {
    failures.push("synthetic_qa_review_run_ready_with_failed_steps");
  }
  if (report.status === "blocked_by_synthetic_qa_review_run" && failedSteps.length === 0) {
    failures.push("synthetic_qa_review_run_blocked_without_failed_steps");
  }
  for (const step of report.steps) {
    if (!step.artifact_ref || step.notes.length === 0) {
      failures.push(`synthetic_qa_review_run_step_not_actionable:${step.step_id}`);
    }
  }
  return failures;
}

export function assertSyntheticConfidenceSummaryReport(
  report: SyntheticConfidenceSummaryReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.synthetic_only || !report.non_authoritative) {
    failures.push("synthetic_confidence_summary_authority_boundary_failed");
  }
  if (!report.local_json_only || !report.human_review_required) {
    failures.push("synthetic_confidence_summary_review_boundary_failed");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("synthetic_confidence_summary_side_effect_boundary_failed");
  }
  if (
    !report.display_banner.candidate_only ||
    !report.display_banner.synthetic_only ||
    !report.display_banner.local_json_only ||
    !report.display_banner.not_production_ready ||
    !report.display_banner.human_review_required ||
    report.display_banner.budget_submission_authorized ||
    report.display_banner.matter_opening_authorized ||
    report.display_banner.lake_write_performed ||
    report.display_banner.sqlite_write_performed ||
    report.display_banner.external_writes_performed
  ) {
    failures.push("synthetic_confidence_summary_display_banner_boundary_failed");
  }
  if (report.qa_step_count !== report.qa_passed_step_count + report.qa_failed_step_count) {
    failures.push("synthetic_confidence_summary_step_count_mismatch");
  }
  if (report.readiness_item_count !== report.readiness_items.length) {
    failures.push("synthetic_confidence_summary_item_count_mismatch");
  }
  if (
    report.quality_gate_count !==
    report.quality_gate_passed_count +
      report.quality_gate_pending_count +
      report.quality_gate_blocked_count +
      report.quality_gate_failed_count
  ) {
    failures.push("synthetic_confidence_summary_gate_count_mismatch");
  }
  if (
    report.status === "synthetic_confidence_summary_ready_for_review" &&
    (report.qa_failed_step_count > 0 ||
      report.qa_missing_required_artifact_count > 0 ||
      report.qa_blocked_artifact_count > 0 ||
      report.qa_failed_artifact_count > 0 ||
      report.ui_missing_required_detail_report_count > 0 ||
      report.ui_external_write_report_count > 0 ||
      report.quality_gate_blocked_count > 0 ||
      report.quality_gate_failed_count > 0 ||
      report.top_blockers.length > 0)
  ) {
    failures.push("synthetic_confidence_summary_ready_with_blockers");
  }
  if (
    report.status !== "synthetic_confidence_summary_ready_for_review" &&
    report.top_blockers.length === 0
  ) {
    failures.push("synthetic_confidence_summary_blocked_without_blockers");
  }
  for (const item of report.readiness_items) {
    if (
      item.evidence_refs.length === 0 ||
      item.notes.length === 0 ||
      !item.no_write_boundary_confirmed
    ) {
      failures.push(`synthetic_confidence_summary_item_not_actionable:${item.item_id}`);
    }
  }
  if (!report.required_next_actions.length) {
    failures.push("synthetic_confidence_summary_missing_next_actions");
  }
  return failures;
}

export function assertPOCQATriageReport(report: POCQATriageReport): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.synthetic_only || !report.non_authoritative) {
    failures.push("poc_qa_triage_authority_boundary_failed");
  }
  if (!report.local_json_only || !report.human_review_required) {
    failures.push("poc_qa_triage_review_boundary_failed");
  }
  if (
    !report.not_authorized_for_lake_write ||
    !report.not_authorized_for_sqlite_write ||
    !report.not_authorized_for_budget_submission ||
    !report.not_authorized_for_matter_opening ||
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("poc_qa_triage_side_effect_boundary_failed");
  }
  const passed = report.items.filter((item) => item.status === "passed");
  const needsReview = report.items.filter((item) => item.status === "needs_review");
  const watch = report.items.filter((item) => item.status === "watch");
  const blocked = report.items.filter((item) => item.status === "blocked");
  const p0Blocked = blocked.filter((item) => item.priority === "p0");
  if (report.item_count !== report.items.length) {
    failures.push("poc_qa_triage_item_count_mismatch");
  }
  if (report.passed_item_count !== passed.length) {
    failures.push("poc_qa_triage_passed_count_mismatch");
  }
  if (report.needs_review_item_count !== needsReview.length) {
    failures.push("poc_qa_triage_needs_review_count_mismatch");
  }
  if (report.watch_item_count !== watch.length) {
    failures.push("poc_qa_triage_watch_count_mismatch");
  }
  if (report.blocked_item_count !== blocked.length) {
    failures.push("poc_qa_triage_blocked_count_mismatch");
  }
  if (report.p0_blocked_item_count !== p0Blocked.length) {
    failures.push("poc_qa_triage_p0_blocked_count_mismatch");
  }
  if (report.status === "poc_qa_ready_for_review" && blocked.length > 0) {
    failures.push("poc_qa_triage_ready_with_blockers");
  }
  if (report.status === "blocked_by_poc_qa_triage" && blocked.length === 0) {
    failures.push("poc_qa_triage_blocked_without_blockers");
  }
  for (const item of report.items) {
    if (
      !item.item_id ||
      !item.summary ||
      !item.recommended_next_action ||
      item.evidence_refs.length === 0
    ) {
      failures.push(`poc_qa_triage_item_not_actionable:${item.item_id}`);
    }
    if (
      (item.status === "needs_review" || item.status === "blocked") &&
      item.candidate_exception_lake_labels.length === 0
    ) {
      failures.push(`poc_qa_triage_item_missing_labels:${item.item_id}`);
    }
  }
  if (!report.required_next_actions.length) {
    failures.push("poc_qa_triage_missing_next_actions");
  }
  return failures;
}

export function assertValidationSuiteEvidenceReport(
  report: ValidationSuiteEvidenceReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.synthetic_only || !report.non_authoritative) {
    failures.push("validation_suite_evidence_authority_boundary_failed");
  }
  if (!report.local_json_only || !report.human_review_required) {
    failures.push("validation_suite_evidence_review_boundary_failed");
  }
  if (
    !report.not_authorized_for_lake_write ||
    !report.not_authorized_for_sqlite_write ||
    !report.not_authorized_for_budget_submission ||
    !report.not_authorized_for_matter_opening ||
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("validation_suite_evidence_side_effect_boundary_failed");
  }
  const passed = report.steps.filter((step) => step.status === "passed");
  const failed = report.steps.filter((step) => step.status === "failed");
  const timedOut = report.steps.filter((step) => step.status === "timed_out");
  if (report.step_count !== report.steps.length) {
    failures.push("validation_suite_evidence_step_count_mismatch");
  }
  if (report.passed_step_count !== passed.length) {
    failures.push("validation_suite_evidence_passed_count_mismatch");
  }
  if (report.failed_step_count !== failed.length) {
    failures.push("validation_suite_evidence_failed_count_mismatch");
  }
  if (report.timed_out_step_count !== timedOut.length) {
    failures.push("validation_suite_evidence_timed_out_count_mismatch");
  }
  const passedStepIds = new Set(passed.map((step) => step.step_id));
  for (const requiredStep of [
    "validate_repo",
    "export_schemas",
    "ruff_check",
    "ruff_format_check",
    "full_pytest",
    "smoke_demo",
    "validate_repo_final",
  ]) {
    if (!passedStepIds.has(requiredStep)) {
      failures.push(`validation_suite_evidence_missing_passed_step:${requiredStep}`);
    }
  }
  if (report.status === "validation_suite_passed" && (failed.length > 0 || timedOut.length > 0)) {
    failures.push("validation_suite_evidence_passed_with_failed_steps");
  }
  if (report.status === "blocked_by_validation_suite" && failed.length + timedOut.length === 0) {
    failures.push("validation_suite_evidence_blocked_without_failed_steps");
  }
  for (const step of report.steps) {
    if (
      !step.step_id ||
      !step.command_key ||
      step.command.length === 0 ||
      !step.command_display ||
      step.timeout_seconds < 1 ||
      step.duration_seconds < 0 ||
      step.evidence_refs.length === 0
    ) {
      failures.push(`validation_suite_evidence_step_not_actionable:${step.step_id}`);
    }
    if (step.status === "passed" && step.return_code !== 0) {
      failures.push(`validation_suite_evidence_passed_return_code:${step.step_id}`);
    }
  }
  if (!report.required_next_actions.length) {
    failures.push("validation_suite_evidence_missing_next_actions");
  }
  return failures;
}

export function assertSyntheticQABlockerReport(report: SyntheticQABlockerReport): string[] {
  const failures: string[] = [];
  if (
    !report.candidate_only ||
    !report.synthetic_only ||
    !report.non_authoritative ||
    !report.local_json_only ||
    !report.human_review_required
  ) {
    failures.push("synthetic_qa_blocker_report_authority_boundary_failed");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("synthetic_qa_blocker_report_side_effect_boundary_failed");
  }
  if (report.row_count !== report.rows.length) {
    failures.push("synthetic_qa_blocker_report_row_count_mismatch");
  }
  const failedRows = report.rows.filter((row) => row.state === "failed");
  const blockedRows = report.rows.filter((row) => row.state === "blocked");
  const pendingRows = report.rows.filter((row) => row.state === "pending_review");
  const blockedActions = report.rows.filter((row) => row.action_state === "blocked");
  const needsReviewActions = report.rows.filter((row) => row.action_state === "needs_review");
  const fixedActions = report.rows.filter((row) => row.action_state === "fixed");
  const readyActions = report.rows.filter((row) => row.action_state === "ready");
  if (report.failed_row_count !== failedRows.length) {
    failures.push("synthetic_qa_blocker_report_failed_count_mismatch");
  }
  if (report.blocked_row_count !== blockedRows.length) {
    failures.push("synthetic_qa_blocker_report_blocked_count_mismatch");
  }
  if (report.pending_review_row_count !== pendingRows.length) {
    failures.push("synthetic_qa_blocker_report_pending_count_mismatch");
  }
  if (report.blocked_action_count !== blockedActions.length) {
    failures.push("synthetic_qa_blocker_report_blocked_action_count_mismatch");
  }
  if (report.needs_review_action_count !== needsReviewActions.length) {
    failures.push("synthetic_qa_blocker_report_needs_review_action_count_mismatch");
  }
  if (report.fixed_action_count !== fixedActions.length) {
    failures.push("synthetic_qa_blocker_report_fixed_action_count_mismatch");
  }
  if (report.ready_action_count !== readyActions.length) {
    failures.push("synthetic_qa_blocker_report_ready_action_count_mismatch");
  }
  const expectedQueueState =
    blockedActions.length > 0 ? "blocked" : needsReviewActions.length > 0 ? "needs_review" : "ready";
  if (report.review_queue_state !== expectedQueueState) {
    failures.push("synthetic_qa_blocker_report_queue_state_mismatch");
  }
  if (
    report.status === "synthetic_qa_blocker_report_ready_for_review" &&
    (failedRows.length > 0 || blockedRows.length > 0)
  ) {
    failures.push("synthetic_qa_blocker_report_ready_with_failed_blockers");
  }
  if (
    report.status !== "synthetic_qa_blocker_report_ready_for_review" &&
    failedRows.length + blockedRows.length === 0
  ) {
    failures.push("synthetic_qa_blocker_report_blocked_without_failed_blockers");
  }
  for (const row of report.rows) {
    if (
      !row.row_id ||
      !row.label ||
      !row.owner ||
      row.evidence_refs.length === 0 ||
      !row.recommended_next_action ||
      row.candidate_exception_lake_labels.length === 0
    ) {
      failures.push(`synthetic_qa_blocker_report_row_not_actionable:${row.row_id}`);
    }
    if ((row.state === "failed" || row.state === "blocked") && row.action_state !== "blocked") {
      failures.push(`synthetic_qa_blocker_report_row_action_mismatch:${row.row_id}`);
    }
    if (row.state === "pending_review" && row.action_state !== "needs_review") {
      failures.push(`synthetic_qa_blocker_report_row_action_mismatch:${row.row_id}`);
    }
  }
  if (!report.required_next_actions.length) {
    failures.push("synthetic_qa_blocker_report_missing_next_actions");
  }
  return failures;
}

export function assertSyntheticQAReviewOutcomeReport(
  report: SyntheticQAReviewOutcomeReport,
): string[] {
  const failures: string[] = [];
  if (
    !report.append_only ||
    !report.candidate_only ||
    !report.synthetic_only ||
    !report.non_authoritative ||
    !report.local_json_only ||
    !report.human_review_required
  ) {
    failures.push("synthetic_qa_review_outcome_authority_boundary_failed");
  }
  if (
    !report.not_authorized_for_lake_write ||
    !report.not_authorized_for_sqlite_write ||
    !report.not_authorized_for_budget_submission ||
    !report.not_authorized_for_matter_opening ||
    !report.not_authorized_for_calibration ||
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("synthetic_qa_review_outcome_side_effect_boundary_failed");
  }
  if (
    report.decision_count !==
    report.accepted_decision_count +
      report.needs_fix_decision_count +
      report.deferred_decision_count +
      report.not_applicable_decision_count
  ) {
    failures.push("synthetic_qa_review_outcome_decision_count_mismatch");
  }
  if (report.reviewed_row_count !== report.reviewed_row_ids.length) {
    failures.push("synthetic_qa_review_outcome_reviewed_row_count_mismatch");
  }
  if (report.unreviewed_row_count !== report.unreviewed_row_ids.length) {
    failures.push("synthetic_qa_review_outcome_unreviewed_row_count_mismatch");
  }
  if (report.unknown_row_count !== report.unknown_row_ids.length) {
    failures.push("synthetic_qa_review_outcome_unknown_row_count_mismatch");
  }
  if (report.reviewed_row_count + report.unreviewed_row_count !== report.source_row_count) {
    failures.push("synthetic_qa_review_outcome_source_coverage_mismatch");
  }
  if (report.unresolved_followup_count !== report.required_followups.length) {
    failures.push("synthetic_qa_review_outcome_followup_count_mismatch");
  }
  if (
    report.status === "synthetic_qa_review_outcome_recorded" &&
    (report.unreviewed_row_count > 0 || report.unresolved_followup_count > 0)
  ) {
    failures.push("synthetic_qa_review_outcome_recorded_with_open_work");
  }
  if (
    report.status === "synthetic_qa_review_outcome_recorded_pending_followup" &&
    report.unreviewed_row_count + report.unresolved_followup_count === 0
  ) {
    failures.push("synthetic_qa_review_outcome_pending_without_open_work");
  }
  if (
    report.status === "blocked_by_synthetic_qa_review_outcome" &&
    report.unknown_row_count === 0 &&
    report.source_synthetic_qa_blocker_report_status !== "failed_synthetic_qa_blocker_boundary"
  ) {
    failures.push("synthetic_qa_review_outcome_blocked_without_unknown_rows");
  }
  if (!report.required_next_actions.length || !report.candidate_lake_event_labels.length) {
    failures.push("synthetic_qa_review_outcome_not_actionable");
  }
  return failures;
}

export function assertMatterLinkingPreflightReport(
  report: MatterLinkingPreflightReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.synthetic_only || !report.non_authoritative) {
    failures.push("matter_linking_authority_boundary_failed");
  }
  if (!report.local_json_only || !report.human_review_required) {
    failures.push("matter_linking_review_boundary_failed");
  }
  if (
    report.upfront_connector_implemented ||
    report.vendor_api_called ||
    report.external_write_performed ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.matter_opening_authorized ||
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.screen_created ||
    report.silent_learning_performed
  ) {
    failures.push("matter_linking_side_effect_boundary_failed");
  }
  if (report.cluster_count !== report.clusters.length) {
    failures.push("matter_linking_cluster_count_mismatch");
  }
  if (!report.required_next_gates.includes("human_matter_linking_review")) {
    failures.push("matter_linking_missing_human_gate");
  }
  if (
    report.sender_followup_required &&
    !report.required_next_gates.includes("sender_reference_followup")
  ) {
    failures.push("matter_linking_missing_sender_followup_gate");
  }
  for (const cluster of report.clusters) {
    if (!cluster.requires_human_confirmation || cluster.matter_link_finalized) {
      failures.push(`matter_linking_cluster_finalized:${cluster.cluster_id}`);
    }
    if (cluster.source_hashes.length === 0 || cluster.supporting_signal_types.length === 0) {
      failures.push(`matter_linking_cluster_missing_evidence:${cluster.cluster_id}`);
    }
  }
  return failures;
}

export function assertLaborEmploymentQAMatrixReport(
  report: LaborEmploymentQAMatrixReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only) {
    failures.push("le_matrix_not_candidate_only");
  }
  if (!report.non_authoritative || !report.synthetic_only) {
    failures.push("le_matrix_authority_boundary_failed");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("le_matrix_side_effect_boundary_failed");
  }
  if (report.case_count !== report.cases.length) {
    failures.push("le_matrix_case_count_mismatch");
  }
  const failedCases = report.cases.filter((testCase) => testCase.status === "failed");
  if (report.failed_case_count !== failedCases.length) {
    failures.push("le_matrix_failed_case_count_mismatch");
  }
  for (const testCase of report.cases) {
    if (!testCase.candidate_only || !testCase.non_authoritative) {
      failures.push(`le_matrix_case_authority_boundary_failed:${testCase.case_id}`);
    }
    if (
      testCase.status === "passed" &&
      (testCase.expected_budget_readiness_state !== testCase.actual_budget_readiness_state ||
        testCase.expected_budget_gate_effect !== testCase.actual_budget_gate_effect)
    ) {
      failures.push(`le_matrix_case_expectation_mismatch:${testCase.case_id}`);
    }
  }
  return failures;
}

export function assertLaborEmploymentExecutableCoverageReport(
  report: LaborEmploymentExecutableCoverageReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.non_authoritative || !report.synthetic_only) {
    failures.push("le_executable_coverage_authority_boundary_failed");
  }
  if (!report.human_review_required) {
    failures.push("le_executable_coverage_missing_human_review_gate");
  }
  if (
    report.fixture_generation_authorized ||
    report.calibration_approved ||
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("le_executable_coverage_side_effect_boundary_failed");
  }
  const coveredCases = report.case_coverage.filter(
    (testCase) => testCase.coverage_state === "covered_executable",
  );
  const missingCases = report.case_coverage.filter(
    (testCase) => testCase.coverage_state === "missing_executable",
  );
  if (report.pack_case_count !== report.case_coverage.length) {
    failures.push("le_executable_coverage_pack_case_count_mismatch");
  }
  if (report.covered_pack_case_count !== coveredCases.length) {
    failures.push("le_executable_coverage_covered_case_count_mismatch");
  }
  if (report.missing_executable_pack_case_count !== missingCases.length) {
    failures.push("le_executable_coverage_missing_case_count_mismatch");
  }
  if (report.covered_family_variant_count !== coveredCases.length) {
    failures.push("le_executable_coverage_covered_variant_count_mismatch");
  }
  if (report.missing_family_variant_count !== missingCases.length) {
    failures.push("le_executable_coverage_missing_variant_count_mismatch");
  }
  if (
    report.coverage_state === "complete_executable_coverage" &&
    report.missing_executable_pack_case_count > 0
  ) {
    failures.push("le_executable_coverage_complete_with_missing_cases");
  }
  if (
    report.coverage_state === "partial_executable_coverage" &&
    report.missing_executable_pack_case_count === 0
  ) {
    failures.push("le_executable_coverage_partial_without_missing_cases");
  }
  if (
    report.status === "labor_employment_executable_coverage_ready_for_review" &&
    report.checks.some((check) => check.status === "failed")
  ) {
    failures.push("le_executable_coverage_ready_with_failed_check");
  }
  if (
    !report.required_next_gates.length ||
    (report.coverage_state === "partial_executable_coverage" &&
      !report.missing_family_variant_refs.length)
  ) {
    failures.push("le_executable_coverage_not_actionable");
  }
  for (const testCase of report.case_coverage) {
    if (!testCase.candidate_only || !testCase.non_authoritative) {
      failures.push(`le_executable_coverage_case_boundary_failed:${testCase.pack_case_id}`);
    }
    if (
      testCase.coverage_state === "covered_executable" &&
      testCase.executable_fixture_ids.length === 0
    ) {
      failures.push(`le_executable_coverage_case_missing_fixture:${testCase.pack_case_id}`);
    }
    if (
      testCase.coverage_state === "missing_executable" &&
      testCase.executable_fixture_ids.length > 0
    ) {
      failures.push(`le_executable_coverage_missing_case_has_fixture:${testCase.pack_case_id}`);
    }
  }
  for (const family of report.family_coverage) {
    if (family.pack_case_count !== family.covered_case_count + family.missing_case_count) {
      failures.push(`le_executable_coverage_family_count_mismatch:${family.family}`);
    }
  }
  return failures;
}

export function assertLaborEmploymentBlockedDriverImpactReviewReport(
  report: LaborEmploymentBlockedDriverImpactReviewReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.non_authoritative || !report.synthetic_only) {
    failures.push("le_blocked_driver_review_authority_boundary_failed");
  }
  if (!report.human_review_required) {
    failures.push("le_blocked_driver_review_missing_human_review_gate");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("le_blocked_driver_review_side_effect_boundary_failed");
  }
  if (report.case_count !== report.blocked_case_count + report.nonblocking_case_count) {
    failures.push("le_blocked_driver_review_case_partition_mismatch");
  }
  if (report.blocked_case_count !== report.case_reviews.length) {
    failures.push("le_blocked_driver_review_case_count_mismatch");
  }
  if (
    report.blocker_fact_count !==
    report.case_reviews.reduce((total, testCase) => total + testCase.blocker_fact_count, 0)
  ) {
    failures.push("le_blocked_driver_review_fact_count_mismatch");
  }
  if (
    report.block_amount_budget_impact_count !==
    report.case_reviews.reduce(
      (total, testCase) => total + testCase.block_amount_budget_impact_count,
      0,
    )
  ) {
    failures.push("le_blocked_driver_review_budget_block_count_mismatch");
  }
  for (const requiredLabel of [
    "labor_employment_critical_budget_fact_block",
    "source_missing",
    "prompt_injection_source_content",
  ]) {
    if (!report.candidate_exception_lake_labels.includes(requiredLabel)) {
      failures.push(`le_blocked_driver_review_missing_label:${requiredLabel}`);
    }
  }
  for (const testCase of report.case_reviews) {
    if (!testCase.candidate_only || !testCase.synthetic_only || !testCase.amount_budget_blocked) {
      failures.push(
        `le_blocked_driver_review_case_boundary_failed:${testCase.executable_fixture_id}`,
      );
    }
    if (
      testCase.allowed_budget_output !== "blocked_amount_budget" ||
      testCase.budget_amount_output_authorized ||
      testCase.budget_submission_authorized ||
      testCase.lake_write_performed ||
      testCase.sqlite_write_performed ||
      testCase.external_writes_performed
    ) {
      failures.push(
        `le_blocked_driver_review_case_side_effect_failed:${testCase.executable_fixture_id}`,
      );
    }
    if (testCase.blocker_fact_count !== testCase.blocker_facts.length) {
      failures.push(
        `le_blocked_driver_review_case_fact_count_mismatch:${testCase.executable_fixture_id}`,
      );
    }
    if (testCase.critical_driver_dimensions.length === 0 || testCase.unblock_actions.length === 0) {
      failures.push(`le_blocked_driver_review_case_not_actionable:${testCase.executable_fixture_id}`);
    }
    for (const fact of testCase.blocker_facts) {
      if (
        fact.required_level !== "critical" ||
        !fact.blocks_precise_budget ||
        !fact.candidate_only ||
        !fact.synthetic_only ||
        fact.unblock_actions.length === 0 ||
        fact.candidate_exception_lake_labels.length === 0
      ) {
        failures.push(`le_blocked_driver_review_fact_boundary_failed:${fact.fact_id}`);
      }
    }
  }
  if (report.checks.some((check) => check.status === "failed")) {
    failures.push("le_blocked_driver_review_failed_check");
  }
  return failures;
}

export function assertLaborEmploymentBudgetOutputExpectationReport(
  report: LaborEmploymentBudgetOutputExpectationReport,
): string[] {
  const failures: string[] = [];
  if (!report.candidate_only || !report.non_authoritative || !report.synthetic_only) {
    failures.push("le_budget_output_expectation_authority_boundary_failed");
  }
  if (!report.human_review_required) {
    failures.push("le_budget_output_expectation_missing_human_review_gate");
  }
  if (
    report.budget_amount_output_authorized ||
    report.budget_submission_authorized ||
    report.conflict_conclusion_emitted ||
    report.matter_opening_authorized ||
    report.training_pipeline_created ||
    report.lake_write_performed ||
    report.sqlite_write_performed ||
    report.external_writes_performed ||
    report.silent_learning_performed
  ) {
    failures.push("le_budget_output_expectation_side_effect_boundary_failed");
  }
  if (report.case_count !== report.cases.length) {
    failures.push("le_budget_output_expectation_case_count_mismatch");
  }
  const failedCases = report.cases.filter((testCase) => testCase.status === "failed");
  if (report.failed_case_count !== failedCases.length) {
    failures.push("le_budget_output_expectation_failed_case_count_mismatch");
  }
  const blockedCases = report.cases.filter(
    (testCase) => testCase.final_allowed_budget_output === "blocked_amount_budget",
  );
  const rangeCases = report.cases.filter(
    (testCase) => testCase.final_allowed_budget_output === "range_or_hours_only_pending_review",
  );
  const candidateRangeCases = report.cases.filter(
    (testCase) =>
      testCase.final_allowed_budget_output === "candidate_range_after_review_pending_human_review",
  );
  const reviewedNonblockingCases = report.cases.filter(
    (testCase) => testCase.selected_for_reviewed_nonblocking_slice,
  );
  const blockedReviewCases = report.cases.filter((testCase) => testCase.blocked_case_review_present);
  if (report.blocked_amount_budget_case_count !== blockedCases.length) {
    failures.push("le_budget_output_expectation_blocked_case_count_mismatch");
  }
  if (report.range_or_hours_only_case_count !== rangeCases.length) {
    failures.push("le_budget_output_expectation_range_case_count_mismatch");
  }
  if (report.candidate_range_after_review_case_count !== candidateRangeCases.length) {
    failures.push("le_budget_output_expectation_candidate_range_count_mismatch");
  }
  if (report.reviewed_nonblocking_case_count !== reviewedNonblockingCases.length) {
    failures.push("le_budget_output_expectation_reviewed_nonblocking_count_mismatch");
  }
  if (report.blocked_review_case_count !== blockedReviewCases.length) {
    failures.push("le_budget_output_expectation_blocked_review_count_mismatch");
  }
  if (!report.required_next_gates.includes("no_budget_submission_from_budget_output_expectations_report")) {
    failures.push("le_budget_output_expectation_missing_no_submission_gate");
  }
  for (const testCase of report.cases) {
    if (
      !testCase.candidate_only ||
      !testCase.non_authoritative ||
      !testCase.synthetic_only ||
      !testCase.human_review_required
    ) {
      failures.push(`le_budget_output_expectation_case_boundary_failed:${testCase.executable_fixture_id}`);
    }
    if (
      testCase.budget_amount_output_authorized ||
      testCase.budget_submission_authorized ||
      testCase.conflict_conclusion_emitted ||
      testCase.matter_opening_authorized ||
      testCase.training_pipeline_created ||
      testCase.lake_write_performed ||
      testCase.sqlite_write_performed ||
      testCase.external_writes_performed ||
      testCase.silent_learning_performed
    ) {
      failures.push(`le_budget_output_expectation_case_side_effect_failed:${testCase.executable_fixture_id}`);
    }
    if (
      testCase.source_allowed_budget_output !== testCase.final_allowed_budget_output ||
      testCase.candidate_exception_lake_labels.length === 0 ||
      testCase.required_next_gates.length === 0 ||
      testCase.evidence_refs.length === 0
    ) {
      failures.push(`le_budget_output_expectation_case_not_actionable:${testCase.executable_fixture_id}`);
    }
    if (
      testCase.final_allowed_budget_output === "blocked_amount_budget" &&
      (!testCase.amount_budget_blocked ||
        !testCase.blocked_case_review_present ||
        testCase.selected_for_reviewed_nonblocking_slice ||
        testCase.block_amount_budget_impact_count === 0)
    ) {
      failures.push(`le_budget_output_expectation_blocked_case_invalid:${testCase.executable_fixture_id}`);
    }
    if (
      testCase.final_allowed_budget_output !== "blocked_amount_budget" &&
      (testCase.amount_budget_blocked ||
        testCase.blocked_case_review_present ||
        !testCase.selected_for_reviewed_nonblocking_slice ||
        testCase.block_amount_budget_impact_count !== 0)
    ) {
      failures.push(`le_budget_output_expectation_nonblocking_case_invalid:${testCase.executable_fixture_id}`);
    }
  }
  if (report.checks.some((check) => check.status === "failed")) {
    failures.push("le_budget_output_expectation_failed_check");
  }
  return failures;
}
