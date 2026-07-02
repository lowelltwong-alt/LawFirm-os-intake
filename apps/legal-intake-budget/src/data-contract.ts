import type {
  BoundaryFlags,
  LaborEmploymentQAMatrixReport,
  QualityGate,
  ReviewArtifact,
  ReviewManifest,
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
  "synthetic_fixture_depth_audit_report.json",
  "budget_calibration_readiness_report.json",
  "budget_calibration_starter_pack_report.json",
  "labor_employment_qa_matrix_report.json",
  "labor_employment_fixture_family_pack_report.json",
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
