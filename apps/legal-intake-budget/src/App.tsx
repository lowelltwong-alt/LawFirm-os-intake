import React from "react";
import { createRoot } from "react-dom/client";

import demoCrosswalkAudit from "./fixtures/demo-crosswalk-audit-report.json";
import demoOCGRuleIRAdoption from "./fixtures/demo-ocg-rule-ir-adoption-report.json";
import demoBudgetLearningLoop from "./fixtures/demo-budget-learning-loop-report.json";
import demoCrossRepoContractProof from "./fixtures/demo-cross-repo-contract-proof-report.json";
import demoPilotReviewStory from "./fixtures/demo-pilot-review-story-report.json";
import demoLaborEmploymentBlockedDriverReview from "./fixtures/demo-labor-employment-blocked-driver-impact-review-report.json";
import demoLaborEmploymentBudgetLearningFixtures from "./fixtures/demo-labor-employment-budget-learning-fixtures-report.json";
import demoLaborEmploymentBudgetOutcomeReplayBuilderBinding from "./fixtures/demo-labor-employment-budget-outcome-replay-builder-binding-report.json";
import demoLaborEmploymentBudgetOutcomeReplayConfidenceStatus from "./fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json";
import demoLaborEmploymentBudgetOutcomeReplayExecution from "./fixtures/demo-labor-employment-budget-outcome-replay-execution-report.json";
import demoLaborEmploymentBudgetOutcomeReplayReadiness from "./fixtures/demo-labor-employment-budget-outcome-replay-readiness-report.json";
import demoLaborEmploymentBudgetOutputExpectations from "./fixtures/demo-labor-employment-budget-output-expectations-report.json";
import demoLaborEmploymentBudgetQAGate from "./fixtures/demo-labor-employment-budget-qa-gate-report.json";
import demoLaborEmploymentExecutableCoverage from "./fixtures/demo-labor-employment-executable-coverage-report.json";
import demoLaborEmploymentQAMatrix from "./fixtures/demo-labor-employment-qa-matrix-report.json";
import demoManifest from "./fixtures/demo-run-manifest.json";
import demoMatterLinkingPreflight from "./fixtures/demo-matter-linking-preflight-report.json";
import demoMatterLinkingQAGate from "./fixtures/demo-matter-linking-qa-gate-report.json";
import demoMatterLinkingReviewOutcome from "./fixtures/demo-matter-linking-review-outcome-report.json";
import demoPocQATriage from "./fixtures/demo-poc-qa-triage-report.json";
import demoPublicDataCacheAudit from "./fixtures/demo-public-data-cache-audit-report.json";
import demoRustFixtureBoundary from "./fixtures/demo-rust-fixture-boundary-report.json";
import demoRustFixtureManifest from "./fixtures/demo-rust-fixture-manifest-report.json";
import demoRustPublicDataCacheCustody from "./fixtures/demo-rust-public-data-cache-custody-report.json";
import demoSyntheticQABlockerReport from "./fixtures/demo-synthetic-qa-blocker-report.json";
import demoSyntheticQAReviewOutcome from "./fixtures/demo-synthetic-qa-review-outcome-report.json";
import demoSyntheticConfidenceSummary from "./fixtures/demo-synthetic-confidence-summary-report.json";
import demoSyntheticQAReviewRun from "./fixtures/demo-synthetic-qa-review-run-report.json";
import demoReviewDataBundle from "./fixtures/demo-ui-review-data-bundle.json";
import demoUIDemoQARecipe from "./fixtures/demo-ui-demo-qa-recipe-report.json";
import demoValidationSuiteEvidence from "./fixtures/demo-validation-suite-evidence-report.json";
import {
  assertMatterLinkingPreflightReport,
  assertMatterLinkingQAGateReport,
  assertMatterLinkingReviewOutcomeReport,
  assertBudgetLearningLoopReport,
  assertCrossRepoContractProofReport,
  assertPilotReviewStoryReport,
  assertLaborEmploymentBudgetOutputExpectationReport,
  assertLaborEmploymentBudgetLearningFixtureReport,
  assertLaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
  assertLaborEmploymentBudgetOutcomeReplayConfidenceStatusReport,
  assertLaborEmploymentBudgetOutcomeReplayExecutionReport,
  assertLaborEmploymentBudgetOutcomeReplayReadinessReport,
  assertLaborEmploymentBudgetQAGateReport,
  assertLaborEmploymentBlockedDriverImpactReviewReport,
  assertLaborEmploymentExecutableCoverageReport,
  assertLaborEmploymentQAMatrixReport,
  assertPOCQATriageReport,
  assertPublicDataCacheAuditReport,
  assertReadOnlyManifest,
  assertCrosswalkAuditReport,
  assertOCGRuleIRAdoptionReport,
  assertRustFixtureBoundaryReport,
  assertRustFixtureManifestReport,
  assertRustPublicDataCacheCustodyReport,
  assertSyntheticQABlockerReport,
  assertSyntheticQAReviewOutcomeReport,
  assertSyntheticConfidenceSummaryReport,
  assertSyntheticQAReviewRunReport,
  assertUIDemoQARecipeReport,
  assertUIReviewDataBundle,
  assertValidationSuiteEvidenceReport,
  failingQualityGates,
} from "./data-contract";
import type {
  ArtifactStatus,
  BudgetLearningLoopReport,
  CrossRepoContractProofReport,
  PilotReviewStoryReport,
  GateState,
  LaborEmploymentAllowedBudgetOutput,
  LaborEmploymentBudgetLearningFixtureReport,
  LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
  LaborEmploymentBudgetOutcomeReplayConfidenceStageStatus,
  LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport,
  LaborEmploymentBudgetOutcomeReplayExecutionReport,
  LaborEmploymentBudgetOutcomeReplayReadinessReport,
  LaborEmploymentBudgetOutputExpectationCase,
  LaborEmploymentBudgetOutputExpectationReport,
  LaborEmploymentBudgetQAGateReport,
  LaborEmploymentBlockedDriverImpactCaseReview,
  LaborEmploymentBlockedDriverImpactReviewReport,
  LaborEmploymentExecutableCoverageReport,
  LaborEmploymentExecutableCoverageState,
  LaborEmploymentBudgetGateEffect,
  LaborEmploymentBudgetReadinessState,
  LaborEmploymentQAMatrixReport,
  MatterLinkingPreflightReport,
  MatterLinkingQAGateReport,
  MatterLinkingReviewOutcomeReport,
  MatterLinkingReviewOutcomeStatus,
  POCQATriageItemStatus,
  POCQATriageReport,
  CrosswalkAuditReport,
  OCGRuleIRAdoptionReport,
  PublicDataCacheAuditReport,
  QualityGate,
  QualityGateStatus,
  ReviewArtifact,
  ReviewManifest,
  RustFixtureBoundaryReport,
  RustFixtureManifestReport,
  RustPublicDataCacheCustodyReport,
  SyntheticQABlockerActionState,
  SyntheticQABlockerReport,
  SyntheticQABlockerRowState,
  SyntheticQAReviewOutcomeReport,
  SyntheticQAReviewOutcomeStatus,
  SyntheticConfidenceSummaryReport,
  SyntheticConfidenceSummaryItemState,
  SyntheticQAReviewRunReport,
  UIDemoQARecipeReport,
  UIReviewDataBundle,
  ValidationSuiteEvidenceReport,
  ValidationSuiteStepStatus,
} from "./types";
import "./styles.css";

const reviewDataBundle = demoReviewDataBundle as UIReviewDataBundle;
const manifest = demoManifest as ReviewManifest;
const syntheticQAReviewRun = demoSyntheticQAReviewRun as SyntheticQAReviewRunReport;
const uiDemoQARecipe = demoUIDemoQARecipe as UIDemoQARecipeReport;
const syntheticQABlockerReport = demoSyntheticQABlockerReport as SyntheticQABlockerReport;
const syntheticQAReviewOutcome =
  demoSyntheticQAReviewOutcome as SyntheticQAReviewOutcomeReport;
const syntheticConfidenceSummary =
  demoSyntheticConfidenceSummary as SyntheticConfidenceSummaryReport;
const pocQATriage = demoPocQATriage as POCQATriageReport;
const publicDataCacheAudit = demoPublicDataCacheAudit as PublicDataCacheAuditReport;
const validationSuiteEvidence =
  demoValidationSuiteEvidence as ValidationSuiteEvidenceReport;
const matterLinkingPreflight = demoMatterLinkingPreflight as MatterLinkingPreflightReport;
const matterLinkingQAGate = demoMatterLinkingQAGate as MatterLinkingQAGateReport;
const matterLinkingReviewOutcome =
  demoMatterLinkingReviewOutcome as MatterLinkingReviewOutcomeReport;
const rustFixtureBoundary = demoRustFixtureBoundary as RustFixtureBoundaryReport;
const rustFixtureManifest = demoRustFixtureManifest as RustFixtureManifestReport;
const rustPublicDataCacheCustody =
  demoRustPublicDataCacheCustody as RustPublicDataCacheCustodyReport;
const laborEmploymentQAMatrix = demoLaborEmploymentQAMatrix as LaborEmploymentQAMatrixReport;
const laborEmploymentExecutableCoverage =
  demoLaborEmploymentExecutableCoverage as LaborEmploymentExecutableCoverageReport;
const laborEmploymentBlockedDriverReview =
  demoLaborEmploymentBlockedDriverReview as LaborEmploymentBlockedDriverImpactReviewReport;
const laborEmploymentBudgetOutputExpectations =
  demoLaborEmploymentBudgetOutputExpectations as LaborEmploymentBudgetOutputExpectationReport;
const laborEmploymentBudgetQAGate =
  demoLaborEmploymentBudgetQAGate as LaborEmploymentBudgetQAGateReport;
const laborEmploymentBudgetLearningFixtures =
  demoLaborEmploymentBudgetLearningFixtures as LaborEmploymentBudgetLearningFixtureReport;
const laborEmploymentBudgetOutcomeReplayReadiness =
  demoLaborEmploymentBudgetOutcomeReplayReadiness as LaborEmploymentBudgetOutcomeReplayReadinessReport;
const laborEmploymentBudgetOutcomeReplayExecution =
  demoLaborEmploymentBudgetOutcomeReplayExecution as LaborEmploymentBudgetOutcomeReplayExecutionReport;
const laborEmploymentBudgetOutcomeReplayBuilderBinding =
  demoLaborEmploymentBudgetOutcomeReplayBuilderBinding as LaborEmploymentBudgetOutcomeReplayBuilderBindingReport;
const laborEmploymentBudgetOutcomeReplayConfidenceStatus =
  demoLaborEmploymentBudgetOutcomeReplayConfidenceStatus as unknown as LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport;
const budgetLearningLoop = demoBudgetLearningLoop as BudgetLearningLoopReport;
const crossRepoContractProof = demoCrossRepoContractProof as CrossRepoContractProofReport;
const pilotReviewStory = demoPilotReviewStory as PilotReviewStoryReport;
const bundleContractFailures = assertUIReviewDataBundle(reviewDataBundle);
const manifestContractFailures = assertReadOnlyManifest(manifest);
const syntheticQAReviewRunFailures = assertSyntheticQAReviewRunReport(syntheticQAReviewRun);
const syntheticQABlockerFailures = assertSyntheticQABlockerReport(syntheticQABlockerReport);
const syntheticQAReviewOutcomeFailures =
  assertSyntheticQAReviewOutcomeReport(syntheticQAReviewOutcome);
const syntheticConfidenceSummaryFailures =
  assertSyntheticConfidenceSummaryReport(syntheticConfidenceSummary);
const pocQATriageFailures = assertPOCQATriageReport(pocQATriage);
const validationSuiteEvidenceFailures =
  assertValidationSuiteEvidenceReport(validationSuiteEvidence);
const uiDemoQARecipeFailures = assertUIDemoQARecipeReport(uiDemoQARecipe);
const matterLinkingFailures = assertMatterLinkingPreflightReport(matterLinkingPreflight);
const matterLinkingQAGateFailures = assertMatterLinkingQAGateReport(matterLinkingQAGate);
const matterLinkingReviewOutcomeFailures =
  assertMatterLinkingReviewOutcomeReport(matterLinkingReviewOutcome);
const crosswalkAudit = demoCrosswalkAudit as CrosswalkAuditReport;
const ocgRuleIRAdoption = demoOCGRuleIRAdoption as OCGRuleIRAdoptionReport;
const crosswalkAuditFailures = assertCrosswalkAuditReport(crosswalkAudit);
const ocgRuleIRAdoptionFailures = assertOCGRuleIRAdoptionReport(ocgRuleIRAdoption);
const rustFixtureBoundaryFailures = assertRustFixtureBoundaryReport(rustFixtureBoundary);
const rustFixtureManifestFailures = assertRustFixtureManifestReport(rustFixtureManifest);
const publicDataCacheAuditFailures =
  assertPublicDataCacheAuditReport(publicDataCacheAudit);
const rustPublicDataCacheCustodyFailures =
  assertRustPublicDataCacheCustodyReport(rustPublicDataCacheCustody);
const matrixContractFailures = assertLaborEmploymentQAMatrixReport(laborEmploymentQAMatrix);
const executableCoverageFailures =
  assertLaborEmploymentExecutableCoverageReport(laborEmploymentExecutableCoverage);
const blockedDriverContractFailures =
  assertLaborEmploymentBlockedDriverImpactReviewReport(laborEmploymentBlockedDriverReview);
const budgetOutputExpectationFailures = assertLaborEmploymentBudgetOutputExpectationReport(
  laborEmploymentBudgetOutputExpectations,
);
const budgetQAGateFailures = assertLaborEmploymentBudgetQAGateReport(laborEmploymentBudgetQAGate);
const budgetLearningFixtureFailures = assertLaborEmploymentBudgetLearningFixtureReport(
  laborEmploymentBudgetLearningFixtures,
);
const budgetOutcomeReplayFailures = assertLaborEmploymentBudgetOutcomeReplayReadinessReport(
  laborEmploymentBudgetOutcomeReplayReadiness,
);
const budgetOutcomeReplayExecutionFailures =
  assertLaborEmploymentBudgetOutcomeReplayExecutionReport(
    laborEmploymentBudgetOutcomeReplayExecution,
  );
const budgetOutcomeReplayBuilderBindingFailures =
  assertLaborEmploymentBudgetOutcomeReplayBuilderBindingReport(
    laborEmploymentBudgetOutcomeReplayBuilderBinding,
  );
const budgetOutcomeReplayConfidenceStatusFailures =
  assertLaborEmploymentBudgetOutcomeReplayConfidenceStatusReport(
    laborEmploymentBudgetOutcomeReplayConfidenceStatus,
  );
const budgetLearningLoopFailures = assertBudgetLearningLoopReport(budgetLearningLoop);
const crossRepoContractProofFailures = assertCrossRepoContractProofReport(crossRepoContractProof);
const pilotReviewStoryFailures = assertPilotReviewStoryReport(pilotReviewStory);
const contractFailures = [
  ...bundleContractFailures,
  ...manifestContractFailures,
  ...syntheticQAReviewRunFailures,
  ...syntheticQABlockerFailures,
  ...syntheticQAReviewOutcomeFailures,
  ...syntheticConfidenceSummaryFailures,
  ...pocQATriageFailures,
  ...validationSuiteEvidenceFailures,
  ...uiDemoQARecipeFailures,
  ...matterLinkingFailures,
  ...matterLinkingQAGateFailures,
  ...matterLinkingReviewOutcomeFailures,
  ...rustFixtureBoundaryFailures,
  ...rustFixtureManifestFailures,
  ...publicDataCacheAuditFailures,
  ...rustPublicDataCacheCustodyFailures,
  ...matrixContractFailures,
  ...executableCoverageFailures,
  ...blockedDriverContractFailures,
  ...budgetOutputExpectationFailures,
  ...budgetQAGateFailures,
  ...budgetLearningFixtureFailures,
  ...budgetOutcomeReplayFailures,
  ...budgetOutcomeReplayExecutionFailures,
  ...budgetOutcomeReplayBuilderBindingFailures,
  ...budgetOutcomeReplayConfidenceStatusFailures,
  ...budgetLearningLoopFailures,
  ...crossRepoContractProofFailures,
  ...pilotReviewStoryFailures,
];

const PUBLIC_DATA_CUSTODY_COMMANDS = [
  "audit-public-data-cache",
  "build-rust-public-data-cache-custody-report",
  "audit-public-source-methodology",
  "plan-public-synthetic-fixture-conversion",
  "review-public-synthetic-fixture-conversion",
  "record-public-synthetic-fixture-conversion-review",
  "build-public-synthetic-fixture-pr-package",
];

const PUBLIC_DATA_BLOCKED_ACTIONS = [
  "public runtime ingestion",
  "public payload commit",
  "fixture generation without conversion review",
  "public-source adapters",
  "Lake or SQLite writes",
  "budget submission",
  "matter opening",
];

function artifactById(manifestData: ReviewManifest, artifactId: string): ReviewArtifact | undefined {
  return manifestData.artifacts.find((artifact) => artifact.artifactId === artifactId);
}

function gateClass(
  state:
    | GateState
    | ArtifactStatus
    | QualityGateStatus
    | SyntheticQABlockerRowState
    | POCQATriageItemStatus
    | SyntheticQAReviewOutcomeStatus
    | MatterLinkingReviewOutcomeStatus
    | ValidationSuiteStepStatus,
) {
  return `state state-${state.replace("_", "-")}`;
}

function replayConfidenceStageClass(state: LaborEmploymentBudgetOutcomeReplayConfidenceStageStatus) {
  if (state === "ready") {
    return "state state-passed";
  }
  if (state === "pending_inputs") {
    return "state state-pending";
  }
  return "state state-blocked";
}

function budgetGateClass(effect: LaborEmploymentBudgetGateEffect) {
  if (effect === "block_amount_budget_before_proposal") {
    return "state state-blocked";
  }
  if (effect === "allow_range_or_hours_only_pending_review") {
    return "state state-pending";
  }
  return "state state-passed";
}

function readinessClass(state: LaborEmploymentBudgetReadinessState) {
  if (state === "blocked_missing_critical_facts") {
    return "state state-blocked";
  }
  if (state === "range_only_pending_human_review") {
    return "state state-pending";
  }
  return "state state-passed";
}

function qaActionClass(actionState: SyntheticQABlockerActionState) {
  if (actionState === "blocked") {
    return "state state-blocked";
  }
  if (actionState === "needs_review") {
    return "state state-pending";
  }
  return "state state-passed";
}

function qaReviewOutcomeClass(status: SyntheticQAReviewOutcomeStatus) {
  if (status === "blocked_by_synthetic_qa_review_outcome") {
    return "state state-blocked";
  }
  if (status === "synthetic_qa_review_outcome_recorded_pending_followup") {
    return "state state-pending";
  }
  return "state state-passed";
}

function summaryItemClass(state: SyntheticConfidenceSummaryItemState) {
  if (state === "ready_for_review") {
    return "state state-passed";
  }
  if (state === "pending_review") {
    return "state state-pending";
  }
  return "state state-blocked";
}

function allowedBudgetOutputClass(output: LaborEmploymentAllowedBudgetOutput) {
  return output === "blocked_amount_budget" ? "state state-blocked" : "state state-pending";
}

function executableCoverageClass(state: LaborEmploymentExecutableCoverageState) {
  return state === "complete_executable_coverage" ? "state state-passed" : "state state-pending";
}

function formatMoney(amount: number | null) {
  if (amount === null) {
    return "unknown";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

function pilotStoryStageClass(status: PilotReviewStoryReport["stages"][number]["status"]) {
  if (status === "passed") {
    return "state state-passed";
  }
  if (status === "ready_for_human_review") {
    return "state state-pending";
  }
  if (status === "not_available") {
    return "state state-pending";
  }
  return "state state-blocked";
}

type FixtureDrilldownRow = {
  outputCase: LaborEmploymentBudgetOutputExpectationCase;
  blockerReview?: LaborEmploymentBlockedDriverImpactCaseReview;
};

type QAWorkbenchCard = {
  id: string;
  label: string;
  state: GateState;
  metric: string;
  detail: string;
  nextAction: string;
  evidenceRefs: string[];
};

function buildFixtureDrilldownRows(
  outputReport: LaborEmploymentBudgetOutputExpectationReport,
  blockedReviewReport: LaborEmploymentBlockedDriverImpactReviewReport,
): FixtureDrilldownRow[] {
  const blockerReviewByFixture = new Map(
    blockedReviewReport.case_reviews.map((review) => [review.executable_fixture_id, review]),
  );

  return outputReport.cases.map((outputCase) => ({
    outputCase,
    blockerReview: blockerReviewByFixture.get(outputCase.executable_fixture_id),
  }));
}

function buildQAWorkbenchCards({
  coverageReport,
  budgetQAGateReport,
  blockerReport,
  pocReport,
  validationReport,
}: {
  coverageReport: LaborEmploymentExecutableCoverageReport;
  budgetQAGateReport: LaborEmploymentBudgetQAGateReport;
  blockerReport: SyntheticQABlockerReport;
  pocReport: POCQATriageReport;
  validationReport: ValidationSuiteEvidenceReport;
}): QAWorkbenchCard[] {
  const coverageReady =
    coverageReport.coverage_state === "complete_executable_coverage" &&
    coverageReport.missing_executable_pack_case_count === 0;
  const validationReady =
    validationReport.status === "validation_suite_passed" &&
    validationReport.failed_step_count === 0 &&
    validationReport.timed_out_step_count === 0 &&
    !validationReport.working_tree_dirty;
  const pocReady = pocReport.status === "poc_qa_ready_for_review";
  const reviewQueueReady =
    blockerReport.failed_row_count === 0 && blockerReport.blocked_row_count === 0;

  return [
    {
      id: "validation-evidence",
      label: "Validation Evidence",
      state: validationReady && pocReady ? "passed" : "blocked",
      metric: `${validationReport.passed_step_count}/${validationReport.step_count}`,
      detail: validationReport.working_tree_dirty
        ? "Validation commands passed, but the report was captured from a dirty worktree."
        : "Full pytest, smoke demo, schema export, lint, and repo validation evidence is attached.",
      nextAction: validationReady
        ? "Use this as the baseline before adding the next fixture family."
        : "Regenerate validation evidence from a clean worktree before expanding synthetic QA.",
      evidenceRefs: ["demo-validation-suite-evidence-report.json", "scripts/run_validation_suite.py"],
    },
    {
      id: "executable-coverage",
      label: "Executable Coverage",
      state: coverageReady ? "passed" : "pending",
      metric: `${coverageReport.covered_pack_case_count}/${coverageReport.pack_case_count}`,
      detail: "Declared L&E fixture-family variants are represented by executable local fixtures.",
      nextAction: "Keep new scenarios tied to manifests, fact bindings, gold, and regression tests.",
      evidenceRefs: [
        "demo-labor-employment-executable-coverage-report.json",
        "labor-employment-executable-fixtures-manifest.json",
      ],
    },
    {
      id: "budget-output-partition",
      label: "Budget Output Partition",
      state: "pending",
      metric: `${budgetQAGateReport.blocked_amount_budget_case_count} blocked`,
      detail: `${budgetQAGateReport.reviewed_nonblocking_case_count} cases are reviewed nonblocking; amount budgets remain guarded when facts are missing.`,
      nextAction: "Use blocked and range-only cases to test budget-driver widening, missing facts, and follow-up prompts.",
      evidenceRefs: [
        "demo-labor-employment-budget-output-expectations-report.json",
        "demo-labor-employment-budget-qa-gate-report.json",
      ],
    },
    {
      id: "review-queue",
      label: "Review Queue",
      state: reviewQueueReady ? "pending" : "blocked",
      metric: `${blockerReport.needs_review_action_count} review`,
      detail: "Synthetic QA rows are review-only and remain outside calibration, Lake writes, and learning.",
      nextAction: "Resolve or supersede review rows before treating them as closed QA decisions.",
      evidenceRefs: ["demo-synthetic-qa-blocker-report.json", "demo-poc-qa-triage-report.json"],
    },
  ];
}

function BoundaryGrid({ manifest }: { manifest: ReviewManifest }) {
  const rows = Object.entries(manifest.boundaryFlags);
  return (
    <section className="panel boundary-panel" aria-labelledby="boundary-title">
      <div className="panel-heading">
        <h2 id="boundary-title">Authority Boundary</h2>
        <span className={contractFailures.length === 0 ? "state state-passed" : "state state-failed"}>
          {contractFailures.length === 0 ? "contract held" : "contract failed"}
        </span>
      </div>
      <div className="boundary-grid">
        {rows.map(([key, value]) => (
          <div className="boundary-item" key={key}>
            <span>{key}</span>
            <strong>{String(value)}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function BundlePanel({ bundle }: { bundle: UIReviewDataBundle }) {
  return (
    <section className="panel bundle-panel" aria-labelledby="bundle-title">
      <div className="panel-heading">
        <div>
          <h2 id="bundle-title">UI Review Data Bundle</h2>
          <code>{bundle.ui_review_data_bundle_id}</code>
        </div>
        <span
          className={
            bundleContractFailures.length === 0 ? "state state-passed" : "state state-failed"
          }
        >
          {bundle.status}
        </span>
      </div>
      <div className="bundle-source">
        <span>Run Root</span>
        <code>{bundle.run_root_ref}</code>
      </div>
      <div className="bundle-report-grid">
        {bundle.detail_reports.map((report) => (
          <article className="bundle-report" key={report.detail_report_id}>
            <div>
              <strong>{report.label}</strong>
              <code>{report.file_name}</code>
            </div>
            <span className={report.present ? "state state-present" : "state state-blocked"}>
              {report.present ? "present" : "missing"}
            </span>
            <p>{report.renderer}</p>
            <code>{report.source_sha256 ?? "missing hash"}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

function QAWorkbenchPanel({
  cards,
  budgetOutputReport,
  pocReport,
}: {
  cards: QAWorkbenchCard[];
  budgetOutputReport: LaborEmploymentBudgetOutputExpectationReport;
  pocReport: POCQATriageReport;
}) {
  const blockedCards = cards.filter((card) => card.state === "blocked");
  const priorityItems = pocReport.items
    .filter((item) => item.status === "blocked" || item.status === "needs_review")
    .slice(0, 6);
  const stressCases = [...budgetOutputReport.cases]
    .sort(
      (left, right) =>
        right.block_amount_budget_impact_count - left.block_amount_budget_impact_count ||
        right.critical_review_only_impact_count - left.critical_review_only_impact_count ||
        right.range_widening_impact_count - left.range_widening_impact_count,
    )
    .slice(0, 6);

  return (
    <section className="panel qa-workbench-panel" aria-labelledby="qa-workbench-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Synthetic QA workbench</p>
          <h2 id="qa-workbench-title">Testing Readiness And Next Targets</h2>
        </div>
        <span className={blockedCards.length === 0 ? "state state-passed" : "state state-blocked"}>
          {blockedCards.length === 0 ? "ready for next slice" : `${blockedCards.length} blocked`}
        </span>
      </div>

      <div className="qa-workbench-grid" aria-label="Synthetic QA workbench lanes">
        {cards.map((card) => (
          <article className="qa-workbench-card" key={card.id}>
            <div>
              <strong>{card.label}</strong>
              <span className={gateClass(card.state)}>{card.state}</span>
            </div>
            <b>{card.metric}</b>
            <p>{card.detail}</p>
            <p>{card.nextAction}</p>
            <TokenList items={card.evidenceRefs} limit={2} />
          </article>
        ))}
      </div>

      <div className="qa-workbench-columns">
        <section aria-labelledby="qa-workbench-queue-title">
          <h3 id="qa-workbench-queue-title">Review Queue</h3>
          <div className="qa-workbench-list">
            {priorityItems.map((item) => (
              <article key={item.item_id}>
                <strong>{item.item_id.replaceAll("_", " ")}</strong>
                <span className={gateClass(item.status)}>{item.status}</span>
                <p>{item.recommended_next_action}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="qa-workbench-target-title">
          <h3 id="qa-workbench-target-title">Budget Stress Targets</h3>
          <div className="qa-workbench-list">
            {stressCases.map((testCase) => (
              <article key={testCase.executable_fixture_id}>
                <strong>{testCase.family}</strong>
                <span className={allowedBudgetOutputClass(testCase.final_allowed_budget_output)}>
                  {testCase.final_allowed_budget_output}
                </span>
                <p>
                  {testCase.variant}: {testCase.block_amount_budget_impact_count} amount blocks,{" "}
                  {testCase.range_widening_impact_count} range impacts,{" "}
                  {testCase.scenario_fork_impact_count} scenario forks
                </p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function BudgetLearningLoopPanel({ report }: { report: BudgetLearningLoopReport }) {
  const actuals = report.actuals;
  const carrier = report.carrier_rejections;
  const gate = report.reviewed_learning_gate;

  return (
    <section className="panel budget-learning-panel" aria-labelledby="budget-learning-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Budget learning loop</p>
          <h2 id="budget-learning-title">Actuals, Rejections, Appeals, And Candidate Learning</h2>
        </div>
        <span className="state state-pending">review required</span>
      </div>

      <div className="budget-learning-summary" aria-label="Budget learning loop metrics">
        <article>
          <span>Budgeted</span>
          <strong>{formatMoney(actuals.total_budgeted)}</strong>
          <p>{report.comparison_budget_state.replaceAll("_", " ")}</p>
        </article>
        <article>
          <span>Actual</span>
          <strong>{formatMoney(actuals.total_actual)}</strong>
          <p>
            {actuals.total_variance_percent}% variance, {actuals.variance_review_event_count}{" "}
            review events
          </p>
        </article>
        <article>
          <span>Disputed</span>
          <strong>{formatMoney(carrier.total_disputed_amount)}</strong>
          <p>
            {carrier.missing_response_count} missing, {carrier.unlinked_notice_count} unlinked,{" "}
            {carrier.parser_failure_count} parser failure
          </p>
        </article>
        <article>
          <span>Recovered</span>
          <strong>{formatMoney(carrier.total_recovered_amount)}</strong>
          <p>{formatMoney(carrier.total_write_down_amount)} write-down recorded</p>
        </article>
      </div>

      <div className="budget-learning-grid" aria-label="Lifecycle learning lanes">
        {report.lifecycle_lanes.map((lane) => (
          <article key={lane.lane_id}>
            <div>
              <strong>{lane.label}</strong>
              <span className={gateClass(lane.state)}>{lane.state}</span>
            </div>
            <b>{lane.metric}</b>
            <p>{lane.why}</p>
            <p>{lane.next_action}</p>
            <TokenList items={lane.candidate_exception_lake_labels} limit={3} />
          </article>
        ))}
      </div>

      <div className="budget-learning-columns">
        <section aria-labelledby="budget-learning-gates-title">
          <h3 id="budget-learning-gates-title">Learning Gate</h3>
          <p>
            {gate.candidate_count} candidates across {gate.target_learning_loops.length} loops;{" "}
            reviewed outcomes and shadow eval are required before candidate changes.
          </p>
          <TokenList items={gate.target_learning_loops} limit={7} />
        </section>
        <section aria-labelledby="budget-learning-red-team-title">
          <h3 id="budget-learning-red-team-title">Red Team</h3>
          <ul>
            {report.red_team_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}

function CrossRepoContractProofPanel({
  report,
}: {
  report: CrossRepoContractProofReport;
}) {
  const proofFailed = crossRepoContractProofFailures.length > 0;
  const steps = [
    {
      label: "Intake request",
      state: "passed" as GateState,
      detail: report.request_id,
      hash: report.request_sha256,
    },
    {
      label: "Orchestrator owner packet",
      state: "blocked" as GateState,
      detail: report.owner_packet_status.replaceAll("_", " "),
      hash: report.owner_packet_sha256,
    },
    {
      label: "Lake review packet",
      state: "blocked" as GateState,
      detail: report.lake_review_packet_status.replaceAll("_", " "),
      hash: report.lake_review_packet_sha256,
    },
    {
      label: "Exception Lake validation",
      state: "passed" as GateState,
      detail: report.lake_validation_status.replaceAll("_", " "),
      hash: report.lake_validation_report_sha256,
    },
  ];
  const boundaries = [
    ["Real data accepted", report.real_data_accepted],
    ["Connector called", report.connector_called],
    ["Lake write", report.lake_write_performed],
    ["SQLite write", report.sqlite_write_performed],
    ["External write", report.external_writes_performed],
    ["Budget submission", report.budget_submission_authorized],
    ["Matter opening", report.matter_opening_authorized],
    ["Conflict clearance", report.conflict_clearance_authorized],
  ] as const;

  return (
    <section className="panel contract-proof-panel" aria-labelledby="contract-proof-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Pinned cross-repo proof</p>
          <h2 id="contract-proof-title">Intake Handoff Contract</h2>
          <code>{report.contract_proof_id}</code>
        </div>
        <span className={proofFailed ? "state state-failed" : "state state-passed"}>
          {proofFailed ? "proof failed" : "proof passed"}
        </span>
      </div>

      <div className="contract-proof-owners" aria-label="Pinned owner commits">
        <article>
          <span>Orchestrator</span>
          <code>{report.orchestrator_commit.slice(0, 12)}</code>
        </article>
        <article>
          <span>Exception Lake</span>
          <code>{report.exception_lake_commit.slice(0, 12)}</code>
        </article>
        <article>
          <span>Owner worktrees</span>
          <strong>{report.owner_worktrees_clean ? "clean" : "not clean"}</strong>
        </article>
      </div>

      <div className="contract-proof-flow" aria-label="Cross-repo handoff sequence">
        {steps.map((step) => (
          <article key={step.label}>
            <div>
              <strong>{step.label}</strong>
              <span className={gateClass(step.state)}>{step.state}</span>
            </div>
            <p>{step.detail}</p>
            <code>{step.hash.slice(0, 16)}...</code>
          </article>
        ))}
      </div>

      <div className="contract-proof-boundaries" aria-label="Disabled authorities">
        {boundaries.map(([label, enabled]) => (
          <div key={label}>
            <span>{label}</span>
            <strong className={enabled ? "state state-failed" : "state state-passed"}>
              {enabled ? "enabled" : "blocked"}
            </strong>
          </div>
        ))}
      </div>

      <p className="boundary">
        This proves a pinned synthetic handoff only. It does not accept work, approve a budget,
        open a matter, admit Lake evidence, or convert candidate artifacts into authority.
      </p>
    </section>
  );
}

function PilotReviewStoryPanel({ report }: { report: PilotReviewStoryReport }) {
  const hasFailures = pilotReviewStoryFailures.length > 0;

  return (
    <section className="panel pilot-story-panel" aria-labelledby="pilot-story-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Flagship synthetic L&E pilot</p>
          <h2 id="pilot-story-title">Brightline EPLI Review Dossier</h2>
          <p>{report.selected_candidate_matter_label}</p>
        </div>
        <span className={hasFailures ? "state state-failed" : "state state-pending"}>
          {hasFailures ? "contract failed" : "review required"}
        </span>
      </div>

      <div className="pilot-story-metrics" aria-label="Pilot review metrics">
        <article>
          <span>Sources</span>
          <strong>{report.source_count}</strong>
          <p>hashed synthetic records</p>
        </article>
        <article>
          <span>Candidate Budget</span>
          <strong>{formatMoney(report.budget_proposal_total)}</strong>
          <p>withheld pending link and role review</p>
        </article>
        <article>
          <span>Rejections</span>
          <strong>{formatMoney(report.carrier_rejected_amount)}</strong>
          <p>{report.carrier_rejection_notice_count} synthetic notices</p>
        </article>
        <article>
          <span>Appeal Result</span>
          <strong>{formatMoney(report.carrier_recovered_amount)}</strong>
          <p>{formatMoney(report.carrier_write_down_amount)} write-down observed</p>
        </article>
        <article>
          <span>Actual Variance</span>
          <strong>{formatMoney(report.actuals_variance_amount)}</strong>
          <p>{formatMoney(report.actuals_total)} synthetic actuals; review pending</p>
        </article>
      </div>

      <div className="pilot-story-flow" aria-label="Pilot review sequence">
        {report.stages.map((stage) => (
          <article key={stage.stage_id}>
            <div>
              <strong>{stage.label}</strong>
              <span className={pilotStoryStageClass(stage.status)}>
                {stage.status.replaceAll("_", " ")}
              </span>
            </div>
            <p>{stage.summary}</p>
            {stage.required_next_gate ? <code>{stage.required_next_gate}</code> : null}
          </article>
        ))}
      </div>

      <div className="pilot-story-columns">
        <section aria-labelledby="pilot-story-gates-title">
          <h3 id="pilot-story-gates-title">Gates Before Any Action</h3>
          <TokenList items={report.required_next_gates} limit={6} />
        </section>
        <section aria-labelledby="pilot-story-exceptions-title">
          <h3 id="pilot-story-exceptions-title">Candidate Exception Labels</h3>
          <TokenList items={report.candidate_exception_lake_labels} limit={8} />
        </section>
      </div>

      <div className="pilot-story-red-team">
        <strong>Red Team</strong>
        <ul>
          {report.red_team_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ArtifactRow({ artifact }: { artifact: ReviewArtifact }) {
  return (
    <tr>
      <td>
        <div className="artifact-title">{artifact.label}</div>
        <code>{artifact.fileName}</code>
      </td>
      <td>
        <span className={gateClass(artifact.status)}>{artifact.status}</span>
      </td>
      <td>
        <span className={gateClass(artifact.gateState)}>{artifact.gateState}</span>
      </td>
      <td>{artifact.owner}</td>
      <td>{artifact.notes.join(" ")}</td>
    </tr>
  );
}

function ArtifactTable({ artifacts }: { artifacts: ReviewArtifact[] }) {
  return (
    <section className="panel artifact-panel" aria-labelledby="artifact-title">
      <div className="panel-heading">
        <h2 id="artifact-title">Run Artifacts</h2>
        <span className="count">{artifacts.length}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Status</th>
              <th>Gate</th>
              <th>Owner</th>
              <th>Review Note</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => (
              <ArtifactRow artifact={artifact} key={artifact.artifactId} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function NotesPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="panel note-panel">
      <h2>{title}</h2>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function QualityGatePanel({ gates }: { gates: QualityGate[] }) {
  const blocked = failingQualityGates(gates).length;
  return (
    <section className="panel quality-panel" aria-labelledby="quality-title">
      <div className="panel-heading">
        <h2 id="quality-title">QA Gates</h2>
        <span className={blocked === 0 ? "state state-passed" : "state state-blocked"}>
          {blocked === 0 ? "ready" : `${blocked} blocked`}
        </span>
      </div>
      <div className="quality-list">
        {gates.map((gate) => (
          <article className="quality-item" key={gate.gateId}>
            <div>
              <strong>{gate.label}</strong>
              <code>{gate.evidenceFile}</code>
            </div>
            <span className={gateClass(gate.status)}>{gate.status}</span>
            <p>{gate.notes.join(" ")}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function SyntheticQABlockerDrilldownPanel({ report }: { report: SyntheticQABlockerReport }) {
  const failedCount = report.failed_row_count;
  const blockedCount = report.blocked_row_count;
  const pendingCount = report.pending_review_row_count;
  const queueStateClass =
    report.review_queue_state === "blocked"
      ? "state state-blocked"
      : report.review_queue_state === "needs_review"
        ? "state state-pending"
        : "state state-passed";
  const queueStateLabel =
    report.review_queue_state === "blocked"
      ? `${report.blocked_action_count} repair required`
      : report.review_queue_state === "needs_review"
        ? `${report.needs_review_action_count} need review`
        : "review queue ready";

  return (
    <section className="panel qa-blocker-panel" aria-labelledby="qa-blocker-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Synthetic QA queue</p>
          <h2 id="qa-blocker-title">Synthetic QA Blocker Drilldown</h2>
          <code>{report.synthetic_qa_blocker_report_id}</code>
        </div>
        <span className={queueStateClass}>{queueStateLabel}</span>
      </div>

      <div className="matrix-summary" aria-label="Synthetic QA blocker drilldown summary">
        <div>
          <span>Failed</span>
          <strong>{failedCount}</strong>
        </div>
        <div>
          <span>Blocked</span>
          <strong>{blockedCount}</strong>
        </div>
        <div>
          <span>Pending Review</span>
          <strong>{pendingCount}</strong>
        </div>
        <div>
          <span>Repair Required</span>
          <strong>{report.blocked_action_count}</strong>
        </div>
        <div>
          <span>Needs Review</span>
          <strong>{report.needs_review_action_count}</strong>
        </div>
        <div>
          <span>Fixed / Ready</span>
          <strong>{report.fixed_action_count + report.ready_action_count}</strong>
        </div>
        <div>
          <span>Next Actions</span>
          <strong>{report.required_next_actions.length}</strong>
        </div>
      </div>

      {report.rows.length === 0 ? (
        <div className="empty-state">
          <strong>No failed or blocked synthetic QA rows in the current local JSON bundle.</strong>
          <span>
            This remains candidate-only: the next action is review, not calibration, submission, or
            Lake write.
          </span>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="qa-blocker-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>State</th>
                <th>Action</th>
                <th>Owner</th>
                <th>Evidence</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <tr key={row.row_id}>
                  <td>
                    <div className="artifact-title">{row.label}</div>
                    <code>{row.source}</code>
                  </td>
                  <td>
                    <span className={gateClass(row.state)}>{row.state}</span>
                  </td>
                  <td>
                    <span className={qaActionClass(row.action_state)}>{row.action_state}</span>
                    <p>{row.recommended_next_action}</p>
                    <TokenList items={row.candidate_exception_lake_labels} limit={3} />
                  </td>
                  <td>{row.owner}</td>
                  <td>
                    <TokenList items={row.evidence_refs} limit={3} />
                  </td>
                  <td>{row.notes.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="next-gates">
        <h3>Review-Only Next Actions</h3>
        <div>
          {report.required_next_actions.map((action) => (
            <code key={action}>{action}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function SyntheticQAReviewOutcomePanel({
  report,
}: {
  report: SyntheticQAReviewOutcomeReport;
}) {
  const statusClass =
    syntheticQAReviewOutcomeFailures.length === 0
      ? qaReviewOutcomeClass(report.status)
      : "state state-failed";

  return (
    <section className="panel qa-review-outcome-panel" aria-labelledby="qa-review-outcome-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Append-only QA review</p>
          <h2 id="qa-review-outcome-title">Synthetic QA Review Outcome</h2>
          <code>{report.synthetic_qa_review_outcome_report_id}</code>
        </div>
        <span className={statusClass}>
          {report.status === "synthetic_qa_review_outcome_recorded"
            ? "recorded"
            : report.status === "synthetic_qa_review_outcome_recorded_pending_followup"
              ? "pending followup"
              : "blocked"}
        </span>
      </div>

      <div className="outcome-source">
        <span>Source Queue</span>
        <code>{report.source_synthetic_qa_blocker_report_id}</code>
        <span>Reviewer</span>
        <code>{report.reviewer_id}</code>
      </div>

      <div className="matrix-summary" aria-label="Synthetic QA review outcome summary">
        <div>
          <span>Reviewed Rows</span>
          <strong>
            {report.reviewed_row_count}/{report.source_row_count}
          </strong>
        </div>
        <div>
          <span>Unreviewed</span>
          <strong>{report.unreviewed_row_count}</strong>
        </div>
        <div>
          <span>Needs Fix</span>
          <strong>{report.needs_fix_decision_count}</strong>
        </div>
        <div>
          <span>Deferred</span>
          <strong>{report.deferred_decision_count}</strong>
        </div>
        <div>
          <span>Accepted</span>
          <strong>{report.accepted_decision_count}</strong>
        </div>
        <div>
          <span>Followups</span>
          <strong>{report.unresolved_followup_count}</strong>
        </div>
      </div>

      <div className="outcome-grid">
        <article>
          <strong>Reviewed Rows</strong>
          <TokenList items={report.reviewed_row_ids} limit={6} />
        </article>
        <article>
          <strong>Open Rows</strong>
          <TokenList items={report.unreviewed_row_ids} limit={6} />
        </article>
        <article>
          <strong>Required Followups</strong>
          <TokenList items={report.required_followups} limit={4} />
        </article>
        <article>
          <strong>Candidate Lake Labels</strong>
          <TokenList items={report.candidate_lake_event_labels} limit={5} />
        </article>
      </div>

      <div className="next-gates">
        <h3>Outcome Next Actions</h3>
        <div>
          {report.required_next_actions.map((action) => (
            <code key={action}>{action}</code>
          ))}
        </div>
      </div>

      <p className="boundary">
        Append-only local QA evidence. Calibration:{" "}
        {report.not_authorized_for_calibration ? "blocked" : "not blocked"}. Lake writes:{" "}
        {report.lake_write_performed ? "not blocked" : "blocked"}. Silent learning:{" "}
        {report.silent_learning_performed ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function SyntheticQAReviewRunPanel({ report }: { report: SyntheticQAReviewRunReport }) {
  const passedSteps = report.steps.filter((step) => step.status === "passed").length;
  const statusClass =
    report.status === "synthetic_qa_review_run_ready" && syntheticQAReviewRunFailures.length === 0
      ? "state state-passed"
      : "state state-failed";

  return (
    <section className="panel recipe-panel" aria-labelledby="recipe-title">
      <div className="panel-heading">
        <div>
          <h2 id="recipe-title">Synthetic QA Review Run</h2>
          <code>{report.synthetic_qa_review_run_report_id}</code>
        </div>
        <span className={statusClass}>
          {report.status === "synthetic_qa_review_run_ready" ? "ready" : "blocked"}
        </span>
      </div>

      <div className="recipe-summary" aria-label="Synthetic QA review run summary">
        <div>
          <span>Steps</span>
          <strong>{report.step_count}</strong>
        </div>
        <div>
          <span>Passed</span>
          <strong>{passedSteps}</strong>
        </div>
        <div>
          <span>Failed</span>
          <strong>{report.failed_step_count}</strong>
        </div>
        <div>
          <span>Local Only</span>
          <strong>{report.local_json_only ? "yes" : "no"}</strong>
        </div>
      </div>

      <div className="recipe-step-grid">
        {report.steps.map((step) => (
          <article className="recipe-step" key={step.step_id}>
            <div>
              <strong>{step.label}</strong>
              <code>{step.artifact_ref}</code>
            </div>
            <span className={gateClass(step.status)}>{step.status}</span>
            <p>
              {step.observed_status} - {step.notes.join(" ")}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function UIDemoQARecipePanel({ report }: { report: UIDemoQARecipeReport }) {
  const passedSteps = report.steps.filter((step) => step.status === "passed").length;
  const verified =
    report.status === "ui_demo_qa_recipe_verified" && uiDemoQARecipeFailures.length === 0;
  const statusClass = verified ? "state state-passed" : "state state-blocked";

  return (
    <section className="panel recipe-panel" aria-labelledby="ui-demo-qa-recipe-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">End-to-end QA proof</p>
          <h2 id="ui-demo-qa-recipe-title">UI Demo QA Recipe</h2>
          <code>{report.ui_demo_qa_recipe_report_id}</code>
        </div>
        <span className={statusClass}>{verified ? "verified" : "blocked"}</span>
      </div>

      <div className="recipe-summary" aria-label="UI demo QA recipe summary">
        <div>
          <span>Steps</span>
          <strong>
            {passedSteps}/{report.step_count}
          </strong>
        </div>
        <div>
          <span>Validation</span>
          <strong>
            {report.validation_exact_step_order_confirmed &&
            report.validation_worktree_clean_confirmed
              ? "clean"
              : "blocked"}
          </strong>
        </div>
        <div>
          <span>Rust Roots</span>
          <strong>
            {report.rust_boundary_root_matches_temp_fixtures &&
            report.rust_manifest_root_matches_temp_fixtures
              ? "matched"
              : "blocked"}
          </strong>
        </div>
        <div>
          <span>Fixture Write</span>
          <strong>{report.local_fixture_updates_performed ? "checked" : "blocked"}</strong>
        </div>
        <div>
          <span>Rollback</span>
          <strong>{report.rollback_performed ? "yes" : "no"}</strong>
        </div>
      </div>

      <div className="boundary-grid">
        <div className="boundary-item">
          <span>Validation Evidence</span>
          <code>{report.validation_suite_evidence_ref}</code>
        </div>
        <div className="boundary-item">
          <span>Final Bundle</span>
          <code>{report.final_ui_review_data_bundle_ref ?? "not supplied"}</code>
        </div>
        <div className="boundary-item">
          <span>Final Promotion</span>
          <code>{report.final_promotion_report_ref ?? "not supplied"}</code>
        </div>
        <div className="boundary-item">
          <span>Budget Submission</span>
          <strong>{String(report.budget_submission_authorized)}</strong>
        </div>
      </div>

      <div className="recipe-step-grid">
        {report.steps.map((step) => (
          <article className="recipe-step" key={step.step_id}>
            <div>
              <strong>{step.label}</strong>
              <code>{step.artifact_ref ?? "not supplied"}</code>
            </div>
            <span className={gateClass(step.status)}>{step.status}</span>
            <p>
              {step.observed_status} - {step.notes.join(" ")}
            </p>
          </article>
        ))}
      </div>

      <p className="boundary">
        Recipe evidence is candidate-only local JSON. Lake writes:{" "}
        {report.lake_write_performed ? "not blocked" : "blocked"}. Matter opening:{" "}
        {report.matter_opening_authorized ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function CrosswalkAuditEvidencePanel({ report }: { report: CrosswalkAuditReport }) {
  const statusClass =
    report.status === "passed" && crosswalkAuditFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel crosswalk-evidence-panel" aria-labelledby="crosswalk-evidence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Candidate standard crosswalk</p>
          <h2 id="crosswalk-evidence-title">Standard Crosswalk Evidence</h2>
          <code>{report.report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="warning-strip">
        <strong>Candidate-only / not canon.</strong>
        <span>
          UTBMS-like strings in local labels (e.g. task-L310-family-*) are mnemonic candidate
          families — not exact SALI, LEDES, or UTBMS codes (
          <code>exact_standard_code_verified=false</code>). This evidence is read-only and must not
          drive budget math.
        </span>
      </div>

      <div className="recipe-summary" aria-label="Crosswalk audit summary">
        <div>
          <span>Acceptance Gate</span>
          <strong>{report.acceptance_gate_status}</strong>
        </div>
        <div>
          <span>Exact Standard Code Verified</span>
          <strong>{String(report.exact_standard_code_verified)}</strong>
        </div>
        <div>
          <span>UTBMS-like Family Labels</span>
          <strong>{report.utbms_like_candidate_family_label_count}</strong>
        </div>
        <div>
          <span>Crosswalks</span>
          <strong>{report.crosswalk_count}</strong>
        </div>
        <div>
          <span>Mapped / Unmapped</span>
          <strong>
            {report.mapped_entry_count} / {report.unmapped_entry_count}
          </strong>
        </div>
        <div>
          <span>Violations</span>
          <strong>
            {report.canonical_claim_count +
              report.guessed_mapping_count +
              report.high_confidence_dual_review_violation_count +
              report.unverified_pinned_target_count +
              report.workflow_dependency_violation_count}
          </strong>
        </div>
      </div>

      <TokenList items={report.prohibited_actions} />
    </section>
  );
}

function OCGRuleIRAdoptionEvidencePanel({ report }: { report: OCGRuleIRAdoptionReport }) {
  const statusClass =
    report.status === "accepted_as_read_only_candidate" && ocgRuleIRAdoptionFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel ocg-evidence-panel" aria-labelledby="ocg-evidence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Substrate-owned OCG rule IR</p>
          <h2 id="ocg-evidence-title">OCG Rule IR Adoption Evidence</h2>
          <code>{report.report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="warning-strip">
        <strong>Read-only candidate evidence.</strong>
        <span>
          Source owner {report.source_owner}. Proposed vs compliant totals are display-only and do
          not authorize budget rewrite, carrier submission, or canon promotion.
        </span>
      </div>

      <div className="recipe-summary" aria-label="OCG adoption summary">
        <div>
          <span>Source Owner</span>
          <strong>{report.source_owner}</strong>
        </div>
        <div>
          <span>Rules / Impact Lines</span>
          <strong>
            {report.rule_count} / {report.impact_line_count}
          </strong>
        </div>
        <div>
          <span>Proposed Total</span>
          <strong>{report.proposed_total_before ?? "n/a"}</strong>
        </div>
        <div>
          <span>Compliant Total</span>
          <strong>{report.carrier_compliant_total ?? "n/a"}</strong>
        </div>
      </div>

      <TokenList items={report.prohibited_actions} />
    </section>
  );
}

function RustFixtureBoundaryPanel({ report }: { report: RustFixtureBoundaryReport }) {
  const statusClass =
    report.status === "passed" && rustFixtureBoundaryFailures.length === 0
      ? "state state-passed"
      : "state state-failed";

  return (
    <section className="panel rust-boundary-panel" aria-labelledby="rust-boundary-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rust QA leaf tool</p>
          <h2 id="rust-boundary-title">Fixture Boundary Checker</h2>
          <code>{report.checker}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="recipe-summary" aria-label="Rust fixture boundary summary">
        <div>
          <span>JSON Files</span>
          <strong>{report.checked_json_file_count}</strong>
        </div>
        <div>
          <span>Objects</span>
          <strong>{report.checked_object_count}</strong>
        </div>
        <div>
          <span>Failures</span>
          <strong>{report.failure_count}</strong>
        </div>
        <div>
          <span>Local Only</span>
          <strong>{report.local_json_only ? "yes" : "no"}</strong>
        </div>
      </div>

      <div className="boundary-grid">
        <div className="boundary-item">
          <span>Root</span>
          <code>{report.root}</code>
        </div>
        <div className="boundary-item">
          <span>UI Bundle</span>
          <code>{report.ui_bundle_ref ?? "not supplied"}</code>
        </div>
        <div className="boundary-item">
          <span>Lake Writes</span>
          <strong>{String(report.lake_write_performed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Budget Submission</span>
          <strong>{String(report.budget_submission_authorized)}</strong>
        </div>
      </div>

      {report.failures.length > 0 && (
        <div className="qa-workbench-list">
          {report.failures.map((failure) => (
            <article key={`${failure.path}-${failure.json_path}-${failure.check}`}>
              <strong>{failure.check}</strong>
              <code>{failure.json_path}</code>
              <p>{failure.message}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function RustFixtureManifestPanel({ report }: { report: RustFixtureManifestReport }) {
  const statusClass =
    report.status === "passed" && rustFixtureManifestFailures.length === 0
      ? "state state-passed"
      : "state state-failed";
  const sampledFiles = report.files.slice(0, 6);

  return (
    <section className="panel rust-boundary-panel" aria-labelledby="rust-manifest-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rust QA leaf tool</p>
          <h2 id="rust-manifest-title">Fixture Manifest Scanner</h2>
          <code>{report.scanner}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="recipe-summary" aria-label="Rust fixture manifest summary">
        <div>
          <span>JSON Files</span>
          <strong>{report.checked_json_file_count}</strong>
        </div>
        <div>
          <span>Parsed</span>
          <strong>{report.parsed_json_file_count}</strong>
        </div>
        <div>
          <span>Parse Errors</span>
          <strong>{report.parse_error_count}</strong>
        </div>
        <div>
          <span>Skipped</span>
          <strong>{report.skipped_file_count}</strong>
        </div>
        <div>
          <span>Bytes</span>
          <strong>{report.total_byte_count.toLocaleString()}</strong>
        </div>
      </div>

      <div className="boundary-grid">
        <div className="boundary-item">
          <span>Root</span>
          <code>{report.root}</code>
        </div>
        <div className="boundary-item">
          <span>Manifest Hash</span>
          <code>{report.manifest_sha256}</code>
        </div>
        <div className="boundary-item">
          <span>Lake Writes</span>
          <strong>{String(report.lake_write_performed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Matter Opening</span>
          <strong>{String(report.matter_opening_authorized)}</strong>
        </div>
      </div>

      <div className="qa-workbench-list">
        {sampledFiles.map((file) => (
          <article key={file.path}>
            <strong>{file.path}</strong>
            <code>{file.sha256}</code>
            <p>
              {file.top_level_type}
              {file.status ? ` - ${file.status}` : ""}
              {file.report_kind ? ` - ${file.report_kind}` : ""}
            </p>
          </article>
        ))}
      </div>

      {report.failures.length > 0 && (
        <div className="qa-workbench-list">
          {report.failures.map((failure) => (
            <article key={`${failure.path}-${failure.check}`}>
              <strong>{failure.check}</strong>
              <code>{failure.path}</code>
              <p>{failure.message}</p>
            </article>
          ))}
        </div>
      )}

      {report.skipped_files.length > 0 && (
        <div className="qa-workbench-list">
          {report.skipped_files.map((file) => (
            <article key={`${file.path}-${file.reason}`}>
              <strong>{file.reason}</strong>
              <code>{file.path}</code>
              <p>Skipped to keep the manifest hash acyclic and reproducible.</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function PublicDataCacheAuditPanel({
  report,
  manifest: manifestData,
  triageReport,
}: {
  report: PublicDataCacheAuditReport;
  manifest: ReviewManifest;
  triageReport: POCQATriageReport;
}) {
  const methodologyArtifact = artifactById(manifestData, "public-methodology");
  const cacheArtifact = artifactById(manifestData, "public-cache");
  const triageItem = triageReport.items.find(
    (item) =>
      item.category === "public_data_boundary" ||
      item.candidate_exception_lake_labels.includes("public_data_cache_review_pending"),
  );
  const failedChecks = report.checks.filter((check) => check.status !== "passed");
  const statusClass =
    report.status === "ready_for_human_public_data_cache_review" &&
    publicDataCacheAuditFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel public-data-panel" aria-labelledby="public-data-cache-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Public-data boundary</p>
          <h2 id="public-data-cache-title">Public Data Cache Audit</h2>
          <code>{report.public_data_cache_audit_report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="warning-strip">
        <strong>Public records are not runtime intake.</strong>
        <span>
          This lane is methodology evidence only. A passing cache audit still requires human
          review before public structures can inform synthetic fixtures.
        </span>
      </div>

      <div className="public-data-grid" aria-label="Public data cache audit summary">
        <article>
          <span>Cache Artifact</span>
          <strong>{cacheArtifact?.status ?? "missing"}</strong>
          <code>{cacheArtifact?.fileName ?? "public_data_cache_audit_report.json"}</code>
        </article>
        <article>
          <span>Methodology Artifact</span>
          <strong>{methodologyArtifact?.status ?? "missing"}</strong>
          <code>{methodologyArtifact?.fileName ?? "public_source_methodology_report.json"}</code>
        </article>
        <article>
          <span>Rust Custody</span>
          <strong>{report.rust_custody_status}</strong>
          <code>{report.rust_custody_report_ref ?? "rust custody report not linked"}</code>
        </article>
        <article>
          <span>Cache Samples</span>
          <strong>{report.cache_sample_count}</strong>
          <code>{report.total_cache_sample_bytes.toLocaleString()} bytes checked</code>
        </article>
      </div>

      <div className="boundary-grid">
        <div className="boundary-item">
          <span>Runtime Ingestion</span>
          <strong>{String(report.direct_runtime_ingestion_allowed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Public Payload Committed</span>
          <strong>{String(report.tracked_public_payload_committed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Lake Writes</span>
          <strong>{String(report.lake_write_performed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Fixture Mutation</span>
          <strong>{String(report.fixture_files_mutated)}</strong>
        </div>
      </div>

      {triageItem ? (
        <div className="public-data-callout">
          <strong>{triageItem.summary}</strong>
          <p>{triageItem.recommended_next_action}</p>
          <TokenList items={triageItem.candidate_exception_lake_labels} />
        </div>
      ) : null}

      <div className="qa-workbench-columns">
        <section aria-labelledby="public-data-failed-checks-title">
          <h3 id="public-data-failed-checks-title">Failed Or Pending Checks</h3>
          <div className="qa-workbench-list">
            {failedChecks.length > 0 ? (
              failedChecks.map((check) => (
                <article key={check.check_id}>
                  <strong>{check.check_id}</strong>
                  <span className={gateClass(check.status)}>{check.status}</span>
                  <p>{check.message}</p>
                  <TokenList items={[...check.source_ids, ...check.path_refs]} limit={4} />
                </article>
              ))
            ) : (
              <article>
                <strong>No failed checks</strong>
                <p>Human public-data cache review is still required before conversion.</p>
              </article>
            )}
          </div>
        </section>

        <section aria-labelledby="public-data-commands-title">
          <h3 id="public-data-commands-title">Commands And Blocked Actions</h3>
          <div className="qa-workbench-list">
            <article>
              <strong>Custody commands</strong>
              <TokenList items={PUBLIC_DATA_CUSTODY_COMMANDS} limit={4} />
            </article>
            <article>
              <strong>Still blocked</strong>
              <TokenList items={PUBLIC_DATA_BLOCKED_ACTIONS} limit={7} />
            </article>
          </div>
        </section>
      </div>

      <div className="next-gates">
        <h3>Required Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function RustPublicDataCacheCustodyPanel({
  report,
}: {
  report: RustPublicDataCacheCustodyReport;
}) {
  const statusClass =
    report.status === "passed" && rustPublicDataCacheCustodyFailures.length === 0
      ? "state state-passed"
      : "state state-failed";
  const sampleRows = report.samples.slice(0, 5);

  return (
    <section
      className="panel public-data-panel rust-public-custody-panel"
      aria-labelledby="rust-public-data-custody-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rust QA leaf tool</p>
          <h2 id="rust-public-data-custody-title">Public Data Cache Custody Checker</h2>
          <code>{report.checker}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="recipe-summary" aria-label="Rust public data custody summary">
        <div>
          <span>Sources</span>
          <strong>{report.checked_source_count}</strong>
        </div>
        <div>
          <span>Samples</span>
          <strong>{report.checked_sample_count}</strong>
        </div>
        <div>
          <span>Hash Drift</span>
          <strong>{report.hash_mismatch_count}</strong>
        </div>
        <div>
          <span>Failures</span>
          <strong>{report.failure_count}</strong>
        </div>
      </div>

      <div className="boundary-grid">
        <div className="boundary-item">
          <span>Metadata Only</span>
          <strong>{String(report.metadata_only_report)}</strong>
        </div>
        <div className="boundary-item">
          <span>Runtime Ingestion</span>
          <strong>{String(report.direct_runtime_ingestion_allowed)}</strong>
        </div>
        <div className="boundary-item">
          <span>Public Payload Committed</span>
          <strong>{String(report.tracked_public_payload_committed)}</strong>
        </div>
        <div className="boundary-item">
          <span>External Writes</span>
          <strong>{String(report.external_writes_performed)}</strong>
        </div>
      </div>

      <div className="qa-workbench-columns">
        <section aria-labelledby="rust-public-data-failures-title">
          <h3 id="rust-public-data-failures-title">Custody Failures</h3>
          <div className="qa-workbench-list">
            {report.failures.map((failure) => (
              <article key={`${failure.source_id}-${failure.check}`}>
                <strong>{failure.check}</strong>
                <code>{failure.source_id}</code>
                <p>{failure.message}</p>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="rust-public-data-samples-title">
          <h3 id="rust-public-data-samples-title">Sample Metadata</h3>
          <div className="qa-workbench-list">
            {sampleRows.length > 0 ? (
              sampleRows.map((sample) => (
                <article key={sample.source_id}>
                  <strong>{sample.source_id}</strong>
                  <span className={sample.status === "passed" ? "state state-passed" : "state state-blocked"}>
                    {sample.status}
                  </span>
                  <p>
                    {sample.expected_byte_count ?? 0} expected bytes;{" "}
                    {sample.actual_byte_count ?? 0} observed bytes.
                  </p>
                </article>
              ))
            ) : (
              <article>
                <strong>No sample metadata</strong>
                <p>No public cache sample is present in the checked demo fixture.</p>
              </article>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}

function SyntheticConfidenceSummaryPanel({
  report,
}: {
  report: SyntheticConfidenceSummaryReport;
}) {
  const statusClass =
    report.status === "synthetic_confidence_summary_ready_for_review" &&
    syntheticConfidenceSummaryFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel confidence-panel" aria-labelledby="confidence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Synthetic QA posture</p>
          <h2 id="confidence-title">Confidence Summary</h2>
          <code>{report.synthetic_confidence_summary_report_id}</code>
        </div>
        <span className={statusClass}>
          {report.status === "synthetic_confidence_summary_ready_for_review"
            ? "review ready"
            : "blocked"}
        </span>
      </div>

      <div className="confidence-banner">
        <strong>{report.display_banner.summary}</strong>
        <div>
          <span>Testing state</span>
          <code>{report.testing_readiness_state}</code>
        </div>
      </div>

      <div className="matrix-summary" aria-label="Synthetic confidence summary counts">
        <div>
          <span>QA Steps</span>
          <strong>
            {report.qa_passed_step_count}/{report.qa_step_count}
          </strong>
        </div>
        <div>
          <span>Pending Gates</span>
          <strong>{report.quality_gate_pending_count}</strong>
        </div>
        <div>
          <span>UI Reports</span>
          <strong>
            {report.ui_present_detail_report_count}/{report.ui_detail_report_count}
          </strong>
        </div>
        <div>
          <span>Top Blockers</span>
          <strong>{report.top_blockers.length}</strong>
        </div>
      </div>

      <div className="confidence-item-grid">
        {report.readiness_items.map((item) => (
          <article className="confidence-item" key={item.item_id}>
            <div>
              <strong>{item.label}</strong>
              <code>{item.owner}</code>
            </div>
            <span className={summaryItemClass(item.state)}>{item.state}</span>
            <p>{item.notes.join(" ")}</p>
            <TokenList items={item.evidence_refs} limit={2} />
          </article>
        ))}
      </div>

      <div className="next-gates">
        <h3>Required Next Actions</h3>
        <div>
          {report.required_next_actions.map((action) => (
            <code key={action}>{action}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function POCQATriagePanel({ report }: { report: POCQATriageReport }) {
  const blockerItems = report.items.filter((item) => item.status === "blocked");
  const reviewItems = report.items.filter((item) => item.status === "needs_review");
  const watchItems = report.items.filter((item) => item.status === "watch");
  const statusClass =
    report.status === "poc_qa_ready_for_review" && pocQATriageFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel poc-triage-panel" aria-labelledby="poc-triage-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">QA action queue</p>
          <h2 id="poc-triage-title">POC QA Triage</h2>
          <code>{report.poc_qa_triage_report_id}</code>
        </div>
        <span className={statusClass}>
          {report.status === "poc_qa_ready_for_review" ? "ready for review" : "blocked"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="POC QA triage summary">
        <div>
          <span>Passed</span>
          <strong>{report.passed_item_count}</strong>
        </div>
        <div>
          <span>Needs Review</span>
          <strong>{report.needs_review_item_count}</strong>
        </div>
        <div>
          <span>Watch</span>
          <strong>{report.watch_item_count}</strong>
        </div>
        <div>
          <span>P0 Blockers</span>
          <strong>{report.p0_blocked_item_count}</strong>
        </div>
      </div>

      <div className="triage-stack" aria-label="POC QA triage items">
        {[...blockerItems, ...reviewItems, ...watchItems].map((item) => (
          <article className={`triage-item triage-${item.status}`} key={item.item_id}>
            <div>
              <strong>{item.item_id.replaceAll("_", " ")}</strong>
              <code>
                {item.priority} / {item.category}
              </code>
            </div>
            <span className={gateClass(item.status)}>{item.status}</span>
            <p>{item.summary}</p>
            <p>{item.recommended_next_action}</p>
            <TokenList items={item.candidate_exception_lake_labels} limit={4} />
          </article>
        ))}
      </div>

      <div className="next-gates">
        <h3>Required Next Actions</h3>
        <div>
          {report.required_next_actions.map((action) => (
            <code key={action}>{action}</code>
          ))}
        </div>
      </div>

      <p className="boundary">
        POC triage is candidate-only. Lake writes:{" "}
        {report.lake_write_performed ? "not blocked" : "blocked"}. Budget submission:{" "}
        {report.budget_submission_authorized ? "not blocked" : "blocked"}. Matter opening:{" "}
        {report.matter_opening_authorized ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function ValidationSuiteEvidencePanel({
  report,
}: {
  report: ValidationSuiteEvidenceReport;
}) {
  const statusClass =
    report.status === "validation_suite_passed" &&
    !report.working_tree_dirty &&
    validationSuiteEvidenceFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";
  const displayStatus =
    report.status === "validation_suite_passed" && report.working_tree_dirty
      ? "dirty"
      : report.status === "validation_suite_passed"
        ? "passed"
        : "blocked";

  return (
    <section className="panel validation-panel" aria-labelledby="validation-suite-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">QA proof</p>
          <h2 id="validation-suite-title">Validation Suite Evidence</h2>
          <code>{report.validation_suite_evidence_report_id}</code>
        </div>
        <span className={statusClass}>{displayStatus}</span>
      </div>

      <div className="matrix-summary" aria-label="Validation suite summary">
        <div>
          <span>Passed</span>
          <strong>
            {report.passed_step_count}/{report.step_count}
          </strong>
        </div>
        <div>
          <span>Failed</span>
          <strong>{report.failed_step_count}</strong>
        </div>
        <div>
          <span>Timed Out</span>
          <strong>{report.timed_out_step_count}</strong>
        </div>
        <div>
          <span>Worktree</span>
          <strong>{report.working_tree_dirty ? "dirty" : "clean"}</strong>
        </div>
        <div>
          <span>Policy</span>
          <strong>{report.policy_version}</strong>
        </div>
      </div>

      <div className="validation-step-grid">
        {report.steps.map((step) => (
          <article className="validation-step" key={step.step_id}>
            <div>
              <strong>{step.step_id.replaceAll("_", " ")}</strong>
              <code>{step.command_key}</code>
            </div>
            <span className={gateClass(step.status)}>{step.status}</span>
            <p>
              Timeout {step.timeout_seconds}s / duration {step.duration_seconds}s / return{" "}
              {step.return_code}
            </p>
            <TokenList items={step.evidence_refs} limit={3} />
          </article>
        ))}
      </div>

      <p className="boundary">
        Evidence is local JSON only. Clean worktree required for promotion:{" "}
        {report.working_tree_dirty ? "not satisfied" : "satisfied"}. Lake writes:{" "}
        {report.lake_write_performed ? "not blocked" : "blocked"}. Budget submission:{" "}
        {report.budget_submission_authorized ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function MatterLinkingPreflightPanel({ report }: { report: MatterLinkingPreflightReport }) {
  const statusClass =
    report.status === "blocked_matter_linking_preflight" || matterLinkingFailures.length > 0
      ? "state state-blocked"
      : "state state-pending";

  return (
    <section className="panel matrix-panel" aria-labelledby="matter-linking-title">
      <div className="panel-heading">
        <div>
          <h2 id="matter-linking-title">Matter-Linking Preflight</h2>
          <code>{report.matter_linking_preflight_report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="matrix-summary" aria-label="Matter-linking preflight summary">
        <div>
          <span>Clusters</span>
          <strong>{report.cluster_count}</strong>
        </div>
        <div>
          <span>High Evidence</span>
          <strong>{report.high_evidence_candidate_count}</strong>
        </div>
        <div>
          <span>Weak Only</span>
          <strong>{report.weak_only_candidate_count}</strong>
        </div>
        <div>
          <span>Weak Signals</span>
          <strong>{report.weak_signal_count}</strong>
        </div>
        <div>
          <span>Split Evidence</span>
          <strong>{report.strong_negative_signal_count}</strong>
        </div>
        <div>
          <span>Split Required</span>
          <strong>{report.negative_split_evidence_required ? "Yes" : "No"}</strong>
        </div>
      </div>

      <div className="table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Candidate Cluster</th>
              <th>Support</th>
              <th>Strong Source Support</th>
              <th>Negative Evidence</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            {report.clusters.map((cluster) => (
              <tr key={cluster.cluster_id}>
                <td>
                  <div className="artifact-title">{cluster.proposed_short_label}</div>
                  <code>{cluster.cluster_id}</code>
                </td>
                <td>
                  <TokenList items={cluster.supporting_signal_types} limit={4} />
                </td>
                <td>
                  <span
                    className={
                      cluster.source_bound_strong_support_present
                        ? "state state-passed"
                        : "state state-blocked"
                    }
                  >
                    {cluster.weak_only_candidate ? "weak only" : "source-bound"}
                  </span>
                </td>
                <td>
                  <TokenList items={cluster.negative_signal_types} limit={4} />
                </td>
                <td>
                  <TokenList items={cluster.source_ids} limit={4} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="lake-label-strip" aria-label="Rejected weak merge signals">
        <span>Weak merge signals</span>
        <TokenList items={report.weak_merge_signal_types} />
      </div>

      <div className="next-gates">
        <h3>Required Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function MatterLinkingQAGatePanel({ report }: { report: MatterLinkingQAGateReport }) {
  const statusClass =
    report.status === "blocked_by_matter_linking_qa_gate" ||
    matterLinkingQAGateFailures.length > 0
      ? "state state-blocked"
      : "state state-pending";

  return (
    <section className="panel matrix-panel" aria-labelledby="matter-linking-qa-gate-title">
      <div className="panel-heading">
        <div>
          <h2 id="matter-linking-qa-gate-title">Matter-Linking QA Gate</h2>
          <code>{report.matter_linking_qa_gate_report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="matrix-summary" aria-label="Matter-linking QA gate summary">
        <div>
          <span>Cases</span>
          <strong>{report.case_count}</strong>
        </div>
        <div>
          <span>Passed</span>
          <strong>{report.passed_case_count}</strong>
        </div>
        <div>
          <span>Failed</span>
          <strong>{report.failed_case_count}</strong>
        </div>
        <div>
          <span>Coverage</span>
          <strong>
            {report.observed_coverage_tag_count}/{report.required_coverage_tag_count}
          </strong>
        </div>
        <div>
          <span>Lake Write</span>
          <strong>{report.lake_write_performed ? "Yes" : "No"}</strong>
        </div>
        <div>
          <span>Matter Opening</span>
          <strong>{report.matter_opening_authorized ? "Yes" : "No"}</strong>
        </div>
      </div>

      {report.missing_coverage_tags.length > 0 ? (
        <div className="warning-strip">
          <span>Missing coverage</span>
          <TokenList items={report.missing_coverage_tags} />
        </div>
      ) : (
        <p className="empty-state">Required matter-linking coverage tags are present.</p>
      )}

      <div className="table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Fixture Case</th>
              <th>Status</th>
              <th>Expected</th>
              <th>Observed</th>
              <th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {report.cases.map((testCase) => (
              <tr key={testCase.case_id}>
                <td>
                  <div className="artifact-title">{testCase.case_id.replaceAll("_", " ")}</div>
                  <code>{testCase.fixture_ref}</code>
                </td>
                <td>
                  <span className={gateClass(testCase.status)}>{testCase.status}</span>
                </td>
                <td>
                  <code>{testCase.expected_status}</code>
                  <p>{testCase.expected_overall_link_state}</p>
                </td>
                <td>
                  <code>{testCase.observed_status}</code>
                  <p>{testCase.observed_overall_link_state}</p>
                </td>
                <td>
                  <TokenList items={testCase.required_coverage_tags} limit={4} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="lake-label-strip" aria-label="Matter-linking QA candidate Lake labels">
        <span>Candidate Lake labels</span>
        <TokenList items={report.candidate_exception_lake_labels} limit={8} />
      </div>

      <p className="boundary">
        Aggregate matching QA is local JSON only. Budget amount:{" "}
        {report.budget_amount_output_authorized ? "not blocked" : "blocked"}. Matter opening:{" "}
        {report.matter_opening_authorized ? "not blocked" : "blocked"}. Learning:{" "}
        {report.silent_learning_performed ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function MatterLinkingReviewOutcomePanel({
  report,
}: {
  report: MatterLinkingReviewOutcomeReport;
}) {
  const statusClass =
    report.status === "blocked_by_matter_linking_review_outcome" ||
    matterLinkingReviewOutcomeFailures.length > 0
      ? "state state-blocked"
      : report.status === "matter_linking_review_outcome_recorded_pending_followup"
        ? "state state-pending"
        : "state state-passed";

  return (
    <section className="panel matrix-panel" aria-labelledby="matter-linking-outcome-title">
      <div className="panel-heading">
        <div>
          <h2 id="matter-linking-outcome-title">Matter-Linking Review Outcome</h2>
          <code>{report.matter_linking_review_outcome_report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="matrix-summary" aria-label="Matter-linking review outcome summary">
        <div>
          <span>Outcome</span>
          <strong>{report.overall_outcome.replaceAll("_", " ")}</strong>
        </div>
        <div>
          <span>Reviewed Clusters</span>
          <strong>{report.reviewed_cluster_count}</strong>
        </div>
        <div>
          <span>Unreviewed</span>
          <strong>{report.unreviewed_cluster_count}</strong>
        </div>
        <div>
          <span>Followups</span>
          <strong>{report.required_followups.length}</strong>
        </div>
        <div>
          <span>Lake Write</span>
          <strong>{report.lake_write_performed ? "Yes" : "No"}</strong>
        </div>
        <div>
          <span>Matter Opening</span>
          <strong>{report.matter_opening_authorized ? "Yes" : "No"}</strong>
        </div>
      </div>

      <div className="triage-stack">
        <article>
          <span>Decision Reason</span>
          <p>{report.decision_reason}</p>
        </article>
        <article>
          <span>Reviewed Cluster IDs</span>
          <TokenList items={report.reviewed_cluster_ids} />
        </article>
        <article>
          <span>Required Followups</span>
          {report.required_followups.length > 0 ? (
            <ul>
              {report.required_followups.map((followup) => (
                <li key={followup}>{followup}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No followups recorded.</p>
          )}
        </article>
      </div>

      <div className="lake-label-strip" aria-label="Matter-linking candidate Lake labels">
        <span>Candidate Lake labels</span>
        <TokenList items={report.candidate_lake_event_labels} limit={8} />
      </div>

      <p className="boundary">
        Append-only local review evidence. Budget amount:{" "}
        {report.budget_amount_output_authorized ? "not blocked" : "blocked"}. Conflict
        conclusion: {report.conflict_conclusion_emitted ? "not blocked" : "blocked"}. Learning:{" "}
        {report.silent_learning_performed ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function LaborEmploymentMatrixPanel({ report }: { report: LaborEmploymentQAMatrixReport }) {
  const criticalGaps = report.cases.reduce(
    (total, testCase) => total + testCase.critical_gap_count,
    0,
  );
  const reviewQuestions = report.cases.reduce(
    (total, testCase) => total + testCase.required_human_question_count,
    0,
  );
  const sourceBoundFindings = report.cases.reduce(
    (total, testCase) => total + testCase.source_bound_finding_count,
    0,
  );

  return (
    <section className="panel matrix-panel" aria-labelledby="matrix-title">
      <div className="panel-heading">
        <div>
          <h2 id="matrix-title">L&amp;E Budget Fact QA</h2>
          <code>{report.labor_employment_qa_matrix_report_id}</code>
        </div>
        <span className={report.failed_case_count === 0 ? "state state-passed" : "state state-failed"}>
          {report.failed_case_count === 0 ? "matrix held" : "matrix failed"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E matrix summary">
        <div>
          <span>Cases</span>
          <strong>{report.case_count}</strong>
        </div>
        <div>
          <span>Critical Gaps</span>
          <strong>{criticalGaps}</strong>
        </div>
        <div>
          <span>Source-Bound Facts</span>
          <strong>{sourceBoundFindings}</strong>
        </div>
        <div>
          <span>Review Questions</span>
          <strong>{reviewQuestions}</strong>
        </div>
      </div>

      <div className="table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Case</th>
              <th>Budget Readiness</th>
              <th>Gate Effect</th>
              <th>Gaps</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {report.cases.map((testCase) => (
              <tr key={testCase.case_id}>
                <td>
                  <div className="artifact-title">{testCase.label}</div>
                  <code>{testCase.manifest_ref}</code>
                </td>
                <td>
                  <span className={readinessClass(testCase.actual_budget_readiness_state)}>
                    {testCase.actual_budget_readiness_state}
                  </span>
                </td>
                <td>
                  <span className={budgetGateClass(testCase.actual_budget_gate_effect)}>
                    {testCase.actual_budget_gate_effect}
                  </span>
                </td>
                <td>
                  <strong>{testCase.critical_gap_count}</strong> critical / {testCase.gap_count} total
                </td>
                <td>
                  {testCase.source_bound_finding_count} source-bound,{" "}
                  {testCase.required_human_question_count} questions
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="next-gates">
        <h3>Required Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function LaborEmploymentExecutableCoveragePanel({
  report,
}: {
  report: LaborEmploymentExecutableCoverageReport;
}) {
  const coveragePercent =
    report.pack_case_count === 0
      ? 0
      : Math.round((report.covered_pack_case_count / report.pack_case_count) * 100);
  const missingPreview = report.case_coverage
    .filter((testCase) => testCase.coverage_state === "missing_executable")
    .slice(0, 8);

  return (
    <section
      className="panel executable-coverage-panel"
      aria-labelledby="executable-coverage-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Synthetic fixture readiness</p>
          <h2 id="executable-coverage-title">L&amp;E Executable Coverage</h2>
          <code>{report.executable_coverage_report_id}</code>
        </div>
        <span
          className={
            executableCoverageFailures.length === 0
              ? executableCoverageClass(report.coverage_state)
              : "state state-failed"
          }
        >
          {report.coverage_state}
        </span>
      </div>

      <div className="coverage-meter" aria-label="L&E executable coverage meter">
        <div>
          <strong>{coveragePercent}%</strong>
          <span>
            {report.covered_pack_case_count}/{report.pack_case_count} pack cases executable
          </span>
        </div>
        <div className="coverage-bar" aria-hidden="true">
          <span style={{ width: `${coveragePercent}%` }} />
        </div>
      </div>

      <div className="matrix-summary" aria-label="L&E executable coverage summary">
        <div>
          <span>Executable Fixtures</span>
          <strong>{report.executable_fixture_count}</strong>
        </div>
        <div>
          <span>Covered Cases</span>
          <strong>{report.covered_pack_case_count}</strong>
        </div>
        <div>
          <span>Missing Cases</span>
          <strong>{report.missing_executable_pack_case_count}</strong>
        </div>
        <div>
          <span>Families Touched</span>
          <strong>
            {report.covered_family_count}/{report.family_coverage.length}
          </strong>
        </div>
      </div>

      <div className="coverage-family-grid" aria-label="L&E executable family coverage">
        {report.family_coverage.map((family) => (
          <article className="coverage-family-item" key={family.family}>
            <strong>{family.family}</strong>
            <span>
              {family.covered_case_count}/{family.pack_case_count} executable
            </span>
            <TokenList items={family.missing_variants} limit={4} />
          </article>
        ))}
      </div>

      <div className="table-wrap">
        <table className="executable-coverage-table">
          <thead>
            <tr>
              <th>Missing Pack Case</th>
              <th>Expected Budget Treatment</th>
              <th>Critical Gaps</th>
              <th>Important Gaps</th>
            </tr>
          </thead>
          <tbody>
            {missingPreview.map((testCase) => (
              <tr key={testCase.pack_case_id}>
                <td>
                  <div className="artifact-title">{testCase.family}</div>
                  <code>{testCase.pack_case_id}</code>
                  <div className="impact-counts">
                    <span>{testCase.variant}</span>
                    <span>{testCase.expected_budget_readiness_state}</span>
                  </div>
                </td>
                <td>
                  <span className={readinessClass(testCase.expected_budget_readiness_state)}>
                    {testCase.expected_budget_treatment}
                  </span>
                </td>
                <td>
                  <TokenList items={testCase.missing_critical_fact_ids} limit={4} />
                </td>
                <td>
                  <TokenList items={testCase.missing_important_fact_ids} limit={4} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="next-gates">
        <h3>Coverage Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function TokenList({ items, limit }: { items: string[]; limit?: number }) {
  const visibleItems = typeof limit === "number" ? items.slice(0, limit) : items;
  const hiddenCount = Math.max(items.length - visibleItems.length, 0);
  return (
    <div className="token-list">
      {visibleItems.map((item) => (
        <code key={item}>{item}</code>
      ))}
      {hiddenCount > 0 ? <span className="more-count">+{hiddenCount}</span> : null}
    </div>
  );
}

function BlockedDriverFacts({
  testCase,
}: {
  testCase: LaborEmploymentBlockedDriverImpactCaseReview;
}) {
  return (
    <div className="fact-stack">
      {testCase.blocker_facts.map((fact) => (
        <div className="fact-row" key={`${testCase.executable_fixture_id}-${fact.fact_id}`}>
          <strong>{fact.fact_id}</strong>
          <code>{fact.fact_resolution_state}</code>
          <span>{fact.reason}</span>
          <TokenList items={fact.budget_effects} limit={4} />
        </div>
      ))}
    </div>
  );
}

function LaborEmploymentBlockedDriverPanel({
  report,
}: {
  report: LaborEmploymentBlockedDriverImpactReviewReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;

  return (
    <section className="panel blocked-review-panel" aria-labelledby="blocked-driver-title">
      <div className="panel-heading">
        <div>
          <h2 id="blocked-driver-title">L&amp;E Blocked Driver Review</h2>
          <code>{report.blocked_driver_impact_review_report_id}</code>
        </div>
        <span
          className={
            blockedDriverContractFailures.length === 0
              ? "state state-passed"
              : "state state-failed"
          }
        >
          {blockedDriverContractFailures.length === 0 ? "review packet held" : "review packet failed"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E blocked driver review summary">
        <div>
          <span>Blocked Cases</span>
          <strong>{report.blocked_case_count}</strong>
        </div>
        <div>
          <span>Blocker Facts</span>
          <strong>{report.blocker_fact_count}</strong>
        </div>
        <div>
          <span>Amount Blocks</span>
          <strong>{report.block_amount_budget_impact_count}</strong>
        </div>
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
      </div>

      <div className="lake-label-strip" aria-label="Candidate exception lake labels">
        <span>Candidate Lake labels</span>
        <TokenList items={report.candidate_exception_lake_labels} />
      </div>

      <div className="table-wrap">
        <table className="blocked-review-table">
          <thead>
            <tr>
              <th>Blocked Case</th>
              <th>Critical Drivers</th>
              <th>Blocker Facts</th>
              <th>Follow-Up</th>
            </tr>
          </thead>
          <tbody>
            {report.case_reviews.map((testCase) => (
              <tr key={testCase.executable_fixture_id}>
                <td>
                  <div className="artifact-title">{testCase.family}</div>
                  <code>{testCase.executable_fixture_id}</code>
                  <div className="impact-counts">
                    <span>{testCase.block_amount_budget_impact_count} amount blocks</span>
                    <span>{testCase.range_widening_impact_count} range impacts</span>
                    <span>{testCase.scenario_fork_impact_count} scenario forks</span>
                    <span>{testCase.rate_guideline_review_impact_count} rate reviews</span>
                  </div>
                </td>
                <td>
                  <TokenList items={testCase.critical_driver_dimensions} />
                </td>
                <td>
                  <BlockedDriverFacts testCase={testCase} />
                </td>
                <td>
                  <TokenList items={testCase.unblock_actions} limit={4} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="next-gates">
        <h3>Required Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function LaborEmploymentBudgetOutputExpectationsPanel({
  report,
}: {
  report: LaborEmploymentBudgetOutputExpectationReport;
}) {
  return (
    <section className="panel blocked-review-panel" aria-labelledby="le-output-title">
      <div className="panel-heading">
        <div>
          <h2 id="le-output-title">L&amp;E Budget Output Expectations</h2>
          <code>{report.budget_output_expectation_report_id}</code>
        </div>
        <span
          className={
            budgetOutputExpectationFailures.length === 0
              ? "state state-passed"
              : "state state-failed"
          }
        >
          {budgetOutputExpectationFailures.length === 0 ? "expectations held" : "expectations failed"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget output expectation summary">
        <div>
          <span>Cases</span>
          <strong>{report.case_count}</strong>
        </div>
        <div>
          <span>Amount Blocked</span>
          <strong>{report.blocked_amount_budget_case_count}</strong>
        </div>
        <div>
          <span>Reviewed Ranges</span>
          <strong>{report.candidate_range_after_review_case_count}</strong>
        </div>
        <div>
          <span>Replay Slice</span>
          <strong>{report.reviewed_nonblocking_case_count}</strong>
        </div>
      </div>

      <div className="lake-label-strip" aria-label="Budget output candidate exception lake labels">
        <span>Candidate Lake labels</span>
        <TokenList items={report.candidate_exception_lake_labels} />
      </div>

      <div className="table-wrap">
        <table className="blocked-review-table">
          <thead>
            <tr>
              <th>Executable Case</th>
              <th>Allowed Output</th>
              <th>Evidence State</th>
              <th>Next Gates</th>
            </tr>
          </thead>
          <tbody>
            {report.cases.map((testCase) => (
              <tr key={testCase.executable_fixture_id}>
                <td>
                  <div className="artifact-title">{testCase.family}</div>
                  <code>{testCase.executable_fixture_id}</code>
                </td>
                <td>
                  <span
                    className={allowedBudgetOutputClass(testCase.final_allowed_budget_output)}
                  >
                    {testCase.final_allowed_budget_output}
                  </span>
                </td>
                <td>
                  <div className="impact-counts">
                    <span>{testCase.expectation_state}</span>
                    <span>{testCase.block_amount_budget_impact_count} amount blocks</span>
                    <span>
                      {testCase.critical_review_only_impact_count} critical review-only
                    </span>
                    <span>{testCase.range_widening_impact_count} range impacts</span>
                    <span>{testCase.scenario_fork_impact_count} scenario forks</span>
                  </div>
                </td>
                <td>
                  <TokenList items={testCase.required_next_gates} limit={4} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="next-gates">
        <h3>Required Next Gates</h3>
        <div>
          {report.required_next_gates.map((gate) => (
            <code key={gate}>{gate}</code>
          ))}
        </div>
      </div>
    </section>
  );
}

function LaborEmploymentBudgetQAGatePanel({
  report,
}: {
  report: LaborEmploymentBudgetQAGateReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;

  return (
    <section className="panel budget-qa-gate-panel" aria-labelledby="le-budget-qa-gate-title">
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-qa-gate-title">L&amp;E Budget QA Gate</h2>
          <code>{report.budget_qa_gate_report_id}</code>
        </div>
        <span
          className={budgetQAGateFailures.length === 0 ? "state state-passed" : "state state-failed"}
        >
          {budgetQAGateFailures.length === 0 ? "budget QA held" : "budget QA failed"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget QA gate summary">
        <div>
          <span>Blocked</span>
          <strong>{report.blocked_amount_budget_case_count}</strong>
        </div>
        <div>
          <span>Range Only</span>
          <strong>{report.range_or_hours_only_case_count}</strong>
        </div>
        <div>
          <span>Candidate Range</span>
          <strong>{report.candidate_range_after_review_case_count}</strong>
        </div>
        <div>
          <span>Families Covered</span>
          <strong>
            {report.covered_required_family_count}/{report.required_family_count}
          </strong>
        </div>
      </div>

      <div className="warning-strip">
        <strong>Budget output remains review-only.</strong>
        <span>
          This gate proves distribution and blockers, not budget correctness, approval, submission,
          matter opening, or Lake admission.
        </span>
      </div>

      <div className="budget-bucket-grid" aria-label="Budget output state buckets">
        {report.output_state_buckets.map((bucket) => (
          <div className="budget-bucket" key={bucket.output_state}>
            <span className={allowedBudgetOutputClass(bucket.output_state)}>
              {bucket.output_state}
            </span>
            <strong>{bucket.case_count}</strong>
            <TokenList items={bucket.executable_fixture_ids} limit={3} />
          </div>
        ))}
      </div>

      <div className="matrix-summary" aria-label="L&E budget QA gate checks">
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
        <div>
          <span>Reviewed Nonblocking</span>
          <strong>{report.reviewed_nonblocking_case_count}</strong>
        </div>
        <div>
          <span>Missing Blocked Reviews</span>
          <strong>{report.missing_blocked_review_case_ids.length}</strong>
        </div>
        <div>
          <span>Missing Replay Reviews</span>
          <strong>{report.missing_nonblocking_review_case_ids.length}</strong>
        </div>
      </div>

      <div className="lake-label-strip" aria-label="L&E budget QA candidate exception lake labels">
        <span>Candidate Lake labels</span>
        <TokenList items={report.candidate_exception_lake_labels} />
      </div>
    </section>
  );
}

function LaborEmploymentBudgetLearningFixturesPanel({
  report,
}: {
  report: LaborEmploymentBudgetLearningFixtureReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;

  return (
    <section
      className="panel budget-learning-fixtures-panel"
      aria-labelledby="le-budget-learning-fixtures-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-learning-fixtures-title">
            L&amp;E Budget Learning Fixtures
          </h2>
          <code>{report.budget_learning_fixture_report_id}</code>
        </div>
        <span
          className={
            budgetLearningFixtureFailures.length === 0 ? "state state-passed" : "state state-failed"
          }
        >
          {budgetLearningFixtureFailures.length === 0 ? "fixture map held" : "fixture map failed"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget learning fixture summary">
        <div>
          <span>Fixtures</span>
          <strong>{report.fixture_count}</strong>
        </div>
        <div>
          <span>Families Covered</span>
          <strong>
            {report.covered_required_family_count}/{report.required_family_count}
          </strong>
        </div>
        <div>
          <span>Learning Loops</span>
          <strong>{report.covered_learning_loop_types.length}</strong>
        </div>
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
      </div>

      <div className="warning-strip">
        <strong>Fixture map only.</strong>
        <span>
          This proves coverage intent for L&amp;E actuals, carrier rejections, appeals,
          reviewed-learning, and blocked-budget guards; it does not create submitted budgets or
          learning changes.
        </span>
      </div>

      <div className="budget-bucket-grid" aria-label="L&E budget learning loop coverage">
        <div className="budget-bucket">
          <span>Actuals variance</span>
          <strong>{report.actuals_variance_fixture_count}</strong>
          <TokenList items={report.covered_budget_output_states} limit={3} />
        </div>
        <div className="budget-bucket">
          <span>Carrier rejections</span>
          <strong>{report.carrier_rejection_fixture_count}</strong>
          <TokenList items={report.candidate_exception_lake_labels} limit={3} />
        </div>
        <div className="budget-bucket">
          <span>Appeal outcomes</span>
          <strong>{report.appeal_outcome_fixture_count}</strong>
          <TokenList items={report.red_team_notes} limit={2} />
        </div>
        <div className="budget-bucket">
          <span>Blocked guard</span>
          <strong>{report.blocked_budget_guard_fixture_count}</strong>
          <TokenList items={report.missing_learning_loop_types} limit={2} />
        </div>
      </div>

      <div className="fixture-table" aria-label="L&E budget learning fixture cases">
        {report.cases.slice(0, 6).map((testCase) => (
          <div className="fixture-row" key={testCase.learning_fixture_id}>
            <div>
              <strong>{testCase.family}</strong>
              <span>{testCase.variant}</span>
            </div>
            <span className={allowedBudgetOutputClass(testCase.expected_budget_output_state)}>
              {testCase.expected_budget_output_state}
            </span>
            <TokenList items={testCase.learning_loop_types} limit={3} />
          </div>
        ))}
      </div>
    </section>
  );
}

function LaborEmploymentBudgetOutcomeReplayReadinessPanel({
  report,
}: {
  report: LaborEmploymentBudgetOutcomeReplayReadinessReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;
  const failedCases = report.cases.filter((testCase) => testCase.status === "failed");

  return (
    <section
      className="panel budget-outcome-replay-panel"
      aria-labelledby="le-budget-outcome-replay-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-outcome-replay-title">
            L&amp;E Budget Outcome Replay Readiness
          </h2>
          <code>{report.outcome_replay_readiness_report_id}</code>
        </div>
        <span
          className={
            budgetOutcomeReplayFailures.length === 0 ? "state state-passed" : "state state-failed"
          }
        >
          {budgetOutcomeReplayFailures.length === 0 ? "seeds ready" : "seeds blocked"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget outcome replay readiness summary">
        <div>
          <span>Seed Specs</span>
          <strong>{report.seed_spec_count}</strong>
        </div>
        <div>
          <span>Seeded Loops</span>
          <strong>
            {report.seeded_loop_requirement_count}/{report.loop_requirement_count}
          </strong>
        </div>
        <div>
          <span>Unresolved Refs</span>
          <strong>{report.unresolved_source_ref_count}</strong>
        </div>
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
      </div>

      <div className="warning-strip">
        <strong>Readiness only.</strong>
        <span>
          Seeds must still be executed, reviewed, and shadow-evaluated before any
          calibration, guideline, template, or model change.
        </span>
      </div>

      <div className="budget-bucket-grid" aria-label="L&E outcome replay coverage">
        <div className="budget-bucket">
          <span>Loop Types</span>
          <strong>{report.covered_learning_loop_types.length}</strong>
          <TokenList items={report.covered_learning_loop_types} limit={5} />
        </div>
        <div className="budget-bucket">
          <span>Replay Artifacts</span>
          <strong>{report.expected_replay_artifact_count}</strong>
          <TokenList
            items={Array.from(
              new Set(report.cases.flatMap((testCase) => testCase.expected_replay_artifacts)),
            )}
            limit={4}
          />
        </div>
        <div className="budget-bucket">
          <span>Failed Cases</span>
          <strong>{failedCases.length}</strong>
          <TokenList items={failedCases.map((testCase) => testCase.learning_fixture_id)} limit={3} />
        </div>
        <div className="budget-bucket">
          <span>Lake Labels</span>
          <strong>{report.candidate_exception_lake_labels.length}</strong>
          <TokenList items={report.candidate_exception_lake_labels} limit={4} />
        </div>
      </div>

      <div className="fixture-table" aria-label="L&E outcome replay readiness cases">
        {report.cases.slice(0, 6).map((testCase) => (
          <div className="fixture-row" key={testCase.learning_fixture_id}>
            <div>
              <strong>{testCase.family}</strong>
              <span>{testCase.outcome_seed_id}</span>
            </div>
            <span className={testCase.status === "passed" ? "state state-passed" : "state state-failed"}>
              {testCase.status}
            </span>
            <TokenList items={testCase.seeded_learning_loop_types} limit={3} />
          </div>
        ))}
      </div>
    </section>
  );
}

function LaborEmploymentBudgetOutcomeReplayExecutionPanel({
  report,
}: {
  report: LaborEmploymentBudgetOutcomeReplayExecutionReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;
  const failedCases = report.cases.filter((testCase) => testCase.status === "failed");
  const sampleSlots = report.cases.flatMap((testCase) => testCase.artifact_slots).slice(0, 8);

  return (
    <section
      className="panel budget-outcome-replay-panel"
      aria-labelledby="le-budget-outcome-replay-execution-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-outcome-replay-execution-title">
            L&amp;E Budget Outcome Replay Execution
          </h2>
          <code>{report.outcome_replay_execution_report_id}</code>
        </div>
        <span
          className={
            budgetOutcomeReplayExecutionFailures.length === 0
              ? "state state-passed"
              : "state state-failed"
          }
        >
          {budgetOutcomeReplayExecutionFailures.length === 0 ? "slots ready" : "slots blocked"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget outcome replay execution summary">
        <div>
          <span>Cases</span>
          <strong>
            {report.materialized_case_count}/{report.fixture_count}
          </strong>
        </div>
        <div>
          <span>Artifact Slots</span>
          <strong>
            {report.materialized_artifact_slot_count}/{report.expected_artifact_slot_count}
          </strong>
        </div>
        <div>
          <span>Runtime Artifacts</span>
          <strong>{report.runtime_artifact_count}</strong>
        </div>
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
      </div>

      <div className="warning-strip">
        <strong>Slots only.</strong>
        <span>
          These candidate files reserve deterministic replay outputs; they are not billing,
          carrier response, Lake, SQLite, calibration, or learning artifacts.
        </span>
      </div>

      <div className="budget-bucket-grid" aria-label="L&E outcome replay execution coverage">
        <div className="budget-bucket">
          <span>Loop Types</span>
          <strong>{report.covered_learning_loop_types.length}</strong>
          <TokenList items={report.covered_learning_loop_types} limit={5} />
        </div>
        <div className="budget-bucket">
          <span>Failed Cases</span>
          <strong>{failedCases.length}</strong>
          <TokenList items={failedCases.map((testCase) => testCase.learning_fixture_id)} limit={3} />
        </div>
        <div className="budget-bucket">
          <span>Lake Labels</span>
          <strong>{report.candidate_exception_lake_labels.length}</strong>
          <TokenList items={report.candidate_exception_lake_labels} limit={4} />
        </div>
        <div className="budget-bucket">
          <span>Next Gates</span>
          <strong>{report.required_next_gates.length}</strong>
          <TokenList items={report.required_next_gates} limit={3} />
        </div>
      </div>

      <div className="fixture-table" aria-label="L&E outcome replay execution slots">
        {sampleSlots.map((slot) => (
          <div className="fixture-row" key={`${slot.loop_type}-${slot.expected_artifact_name}`}>
            <div>
              <strong>{slot.expected_artifact_name}</strong>
              <span>{slot.loop_type}</span>
            </div>
            <span
              className={
                slot.artifact_slot_status === "materialized_candidate_slot"
                  ? "state state-passed"
                  : "state state-failed"
              }
            >
              {slot.artifact_slot_status}
            </span>
            <TokenList items={slot.evidence_refs} limit={2} />
          </div>
        ))}
      </div>
    </section>
  );
}

function LaborEmploymentBudgetOutcomeReplayBuilderBindingPanel({
  report,
}: {
  report: LaborEmploymentBudgetOutcomeReplayBuilderBindingReport;
}) {
  const passedChecks = report.checks.filter((check) => check.status === "passed").length;
  const sampleBindings = report.cases.flatMap((testCase) => testCase.bindings).slice(0, 8);
  const replayGapIds = Array.from(
    new Set(
      report.cases.flatMap((testCase) =>
        testCase.bindings.flatMap((binding) => binding.replay_input_gap_ids),
      ),
    ),
  );
  const prerequisiteGaps = Array.from(
    new Set(
      report.cases.flatMap((testCase) =>
        testCase.bindings.flatMap((binding) => binding.missing_case_prerequisite_artifacts),
      ),
    ),
  );

  return (
    <section
      className="panel budget-outcome-replay-panel"
      aria-labelledby="le-budget-outcome-replay-binding-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-outcome-replay-binding-title">
            L&amp;E Budget Replay Builder Binding
          </h2>
          <code>{report.builder_binding_report_id}</code>
        </div>
        <span
          className={
            budgetOutcomeReplayBuilderBindingFailures.length === 0
              ? "state state-passed"
              : "state state-failed"
          }
        >
          {budgetOutcomeReplayBuilderBindingFailures.length === 0 ? "builders bound" : "binding gaps"}
        </span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget replay builder binding summary">
        <div>
          <span>Bound Slots</span>
          <strong>
            {report.bound_slot_count}/{report.slot_count}
          </strong>
        </div>
        <div>
          <span>Input Gaps</span>
          <strong>{report.replay_input_gap_count}</strong>
        </div>
        <div>
          <span>Prerequisite Gaps</span>
          <strong>{report.missing_case_prerequisite_count}</strong>
        </div>
        <div>
          <span>Checks Passed</span>
          <strong>
            {passedChecks}/{report.checks.length}
          </strong>
        </div>
      </div>

      <div className="warning-strip">
        <strong>Binding only.</strong>
        <span>
          These rows map slots to deterministic builders. They do not execute builders, create
          runtime artifacts, submit budgets, write Lake records, or learn from outcomes.
        </span>
      </div>

      <div className="budget-bucket-grid" aria-label="L&E replay binding gaps">
        <div className="budget-bucket">
          <span>Builder Contracts</span>
          <strong>{report.builder_contracts.length}</strong>
          <TokenList
            items={report.builder_contracts.map(
              (contract) => `${contract.loop_type}:${contract.artifact_name}`,
            )}
            limit={4}
          />
        </div>
        <div className="budget-bucket">
          <span>Replay Inputs</span>
          <strong>{replayGapIds.length}</strong>
          <TokenList items={replayGapIds} limit={4} />
        </div>
        <div className="budget-bucket">
          <span>Complement Reports</span>
          <strong>{prerequisiteGaps.length}</strong>
          <TokenList items={prerequisiteGaps} limit={4} />
        </div>
        <div className="budget-bucket">
          <span>Next Gates</span>
          <strong>{report.required_next_gates.length}</strong>
          <TokenList items={report.required_next_gates} limit={3} />
        </div>
      </div>

      <div className="fixture-table" aria-label="L&E replay builder bindings">
        {sampleBindings.map((binding) => (
          <div className="fixture-row" key={binding.binding_id}>
            <div>
              <strong>{binding.expected_artifact_name}</strong>
              <span>
                {binding.builder_module}.{binding.builder_function}
              </span>
            </div>
            <span
              className={
                binding.binding_status === "bound_to_existing_builder"
                  ? "state state-passed"
                  : "state state-failed"
              }
            >
              {binding.binding_status}
            </span>
            <TokenList
              items={[
                ...binding.replay_input_gap_ids,
                ...binding.missing_case_prerequisite_artifacts,
              ]}
              limit={3}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

function LaborEmploymentBudgetOutcomeReplayConfidenceStatusPanel({
  report,
}: {
  report: LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport;
}) {
  const statusClass =
    budgetOutcomeReplayConfidenceStatusFailures.length === 0 &&
    report.status === "labor_employment_budget_outcome_replay_confidence_ready_for_review"
      ? "state state-passed"
      : report.status === "blocked_by_labor_employment_budget_outcome_replay_confidence"
        ? "state state-blocked"
        : "state state-pending";

  return (
    <section
      className="panel budget-outcome-replay-panel"
      aria-labelledby="le-budget-outcome-replay-confidence-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="le-budget-outcome-replay-confidence-title">
            L&amp;E Budget Replay Confidence Status
          </h2>
          <code>{report.replay_confidence_status_report_id}</code>
        </div>
        <span className={statusClass}>{report.status}</span>
      </div>

      <div className="warning-strip">
        <strong>Candidate-only status.</strong>
        <span>{report.display_banner.summary}</span>
      </div>

      <div className="matrix-summary" aria-label="L&E budget replay confidence summary">
        <div>
          <span>Stages Ready</span>
          <strong>
            {report.ready_stage_count}/{report.stage_count}
          </strong>
        </div>
        <div>
          <span>Pending Stages</span>
          <strong>{report.pending_stage_count}</strong>
        </div>
        <div>
          <span>Blocked Stages</span>
          <strong>{report.blocked_stage_count}</strong>
        </div>
        <div>
          <span>Input Gaps</span>
          <strong>
            {report.builder_replay_input_gap_count + report.input_pack_missing_input_count}
          </strong>
        </div>
      </div>

      <div className="budget-bucket-grid" aria-label="L&E replay confidence controls">
        <div className="budget-bucket">
          <span>Blocked Actions</span>
          <strong>{report.display_banner.blocked_actions.length}</strong>
          <TokenList items={report.display_banner.blocked_actions} limit={6} />
        </div>
        <div className="budget-bucket">
          <span>Next Gates</span>
          <strong>{report.required_next_gates.length}</strong>
          <TokenList items={report.required_next_gates} limit={4} />
        </div>
        <div className="budget-bucket">
          <span>Candidate Lake Labels</span>
          <strong>{report.candidate_exception_lake_labels.length}</strong>
          <TokenList items={report.candidate_exception_lake_labels} limit={4} />
        </div>
        <div className="budget-bucket">
          <span>Rust Candidates</span>
          <strong>{report.rust_transition_candidates.length}</strong>
          <TokenList items={report.rust_transition_candidates} limit={3} />
        </div>
      </div>

      <div className="fixture-table" aria-label="L&E replay confidence stages">
        {report.stages.map((stage) => (
          <div className="fixture-row" key={stage.stage_id}>
            <div>
              <strong>{stage.label}</strong>
              <span>{stage.source_report_status}</span>
            </div>
            <span className={replayConfidenceStageClass(stage.status)}>
              {stage.status}
            </span>
            <TokenList items={stage.blockers.length ? stage.blockers : stage.evidence_refs} limit={3} />
          </div>
        ))}
      </div>

      <p className="boundary">
        Local JSON only. Budget submission:{" "}
        {report.budget_submission_authorized ? "not blocked" : "blocked"}. Matter opening:{" "}
        {report.matter_opening_authorized ? "not blocked" : "blocked"}. Lake writes:{" "}
        {report.lake_write_performed || report.sqlite_write_performed ? "not blocked" : "blocked"}.
      </p>
    </section>
  );
}

function LaborEmploymentFixtureDrilldownPanel({
  outputReport,
  blockedReviewReport,
}: {
  outputReport: LaborEmploymentBudgetOutputExpectationReport;
  blockedReviewReport: LaborEmploymentBlockedDriverImpactReviewReport;
}) {
  const rows = buildFixtureDrilldownRows(outputReport, blockedReviewReport);
  const reviewMatchedCount = rows.filter((row) => row.blockerReview).length;
  const candidateRangeCount = rows.filter(
    (row) =>
      row.outputCase.final_allowed_budget_output ===
      "candidate_range_after_review_pending_human_review",
  ).length;
  const familyRows = Array.from(
    rows
      .reduce(
        (families, row) => {
          const existing = families.get(row.outputCase.family) ?? {
            family: row.outputCase.family,
            total: 0,
            blocked: 0,
            reviewed: 0,
            candidateRange: 0,
          };
          existing.total += 1;
          if (row.outputCase.final_allowed_budget_output === "blocked_amount_budget") {
            existing.blocked += 1;
          }
          if (row.outputCase.final_allowed_budget_output === "candidate_range_after_review_pending_human_review") {
            existing.candidateRange += 1;
          }
          if (row.blockerReview) {
            existing.reviewed += 1;
          }
          families.set(row.outputCase.family, existing);
          return families;
        },
        new Map<
          string,
          { family: string; total: number; blocked: number; reviewed: number; candidateRange: number }
        >(),
      )
      .values(),
  ).sort((left, right) => left.family.localeCompare(right.family));

  return (
    <section className="panel fixture-drilldown-panel" aria-labelledby="fixture-drilldown-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Read-only synthetic QA</p>
          <h2 id="fixture-drilldown-title">L&amp;E Fixture Drilldown</h2>
          <code>{outputReport.budget_output_expectation_report_id}</code>
        </div>
        <span className="state state-pending">candidate review only</span>
      </div>

      <div className="matrix-summary" aria-label="L&E fixture drilldown summary">
        <div>
          <span>Families</span>
          <strong>{familyRows.length}</strong>
        </div>
        <div>
          <span>Executable Cases</span>
          <strong>{rows.length}</strong>
        </div>
        <div>
          <span>Blocker Reviews</span>
          <strong>
            {reviewMatchedCount}/{blockedReviewReport.blocked_case_count}
          </strong>
        </div>
        <div>
          <span>Candidate Ranges</span>
          <strong>{candidateRangeCount}</strong>
        </div>
      </div>

      <div className="fixture-family-grid" aria-label="Fixture family coverage">
        {familyRows.map((family) => (
          <div className="fixture-family-item" key={family.family}>
            <strong>{family.family}</strong>
            <span>
              {family.blocked} blocked / {family.candidateRange} range / {family.reviewed} reviews
            </span>
          </div>
        ))}
      </div>

      <div className="table-wrap">
        <table className="fixture-drilldown-table">
          <thead>
            <tr>
              <th>Fixture</th>
              <th>Allowed Output</th>
              <th>Review Evidence</th>
              <th>Driver Counts</th>
              <th>Follow-Up</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const { outputCase, blockerReview } = row;
              const reviewState = blockerReview
                ? "blocked review present"
                : outputCase.selected_for_reviewed_nonblocking_slice
                  ? "reviewed nonblocking slice"
                  : "no blocker review";
              const followUpItems = blockerReview
                ? blockerReview.unblock_actions
                : outputCase.required_next_gates;

              return (
                <tr key={outputCase.executable_fixture_id}>
                  <td>
                    <div className="artifact-title">{outputCase.family}</div>
                    <code>{outputCase.executable_fixture_id}</code>
                    <div className="impact-counts">
                      <span>{outputCase.variant}</span>
                      <span>{outputCase.expectation_state}</span>
                    </div>
                  </td>
                  <td>
                    <span className={allowedBudgetOutputClass(outputCase.final_allowed_budget_output)}>
                      {outputCase.final_allowed_budget_output}
                    </span>
                  </td>
                  <td>
                    <div className="fixture-evidence-stack">
                      <span className={blockerReview ? "state state-passed" : "state state-pending"}>
                        {reviewState}
                      </span>
                      <span>
                        {blockerReview
                          ? `${blockerReview.blocker_fact_count} blocker facts`
                          : `${outputCase.evidence_refs.length} output refs`}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="impact-counts">
                      <span>{outputCase.block_amount_budget_impact_count} amount blocks</span>
                      <span>
                        {outputCase.critical_review_only_impact_count} critical review-only
                      </span>
                      <span>{outputCase.range_widening_impact_count} range impacts</span>
                      <span>{outputCase.scenario_fork_impact_count} scenario forks</span>
                      <span>{outputCase.rate_guideline_review_impact_count} rate reviews</span>
                    </div>
                  </td>
                  <td>
                    <TokenList items={followUpItems} limit={4} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function App() {
  const blockedCount = manifest.artifacts.filter(
    (artifact) => artifact.status === "blocked" || artifact.gateState === "blocked",
  ).length;
  const pendingCount = manifest.artifacts.filter(
    (artifact) => artifact.status === "pending_review" || artifact.gateState === "pending",
  ).length;
  const qualityBlockedCount = failingQualityGates(manifest.qualityGates).length;
  const qaWorkbenchCards = buildQAWorkbenchCards({
    coverageReport: laborEmploymentExecutableCoverage,
    budgetQAGateReport: laborEmploymentBudgetQAGate,
    blockerReport: syntheticQABlockerReport,
    pocReport: pocQATriage,
    validationReport: validationSuiteEvidence,
  });

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local JSON only</p>
          <h1>{manifest.runLabel}</h1>
          <p>
            {manifest.practiceArea} / {manifest.matterFamily}
          </p>
        </div>
        <div className="status-stack" aria-label="Run status">
          <span className={gateClass(manifest.overallStatus)}>{manifest.overallStatus}</span>
          <span>{manifest.generatedAt}</span>
        </div>
      </header>

      <section className="metric-strip" aria-label="Review counts">
        <div>
          <span>Artifacts</span>
          <strong>{manifest.artifacts.length}</strong>
        </div>
        <div>
          <span>Blocked</span>
          <strong>{blockedCount}</strong>
        </div>
        <div>
          <span>Pending Review</span>
          <strong>{pendingCount}</strong>
        </div>
        <div>
          <span>QA Blockers</span>
          <strong>{qualityBlockedCount}</strong>
        </div>
      </section>

      <BundlePanel bundle={reviewDataBundle} />
      <QAWorkbenchPanel
        cards={qaWorkbenchCards}
        budgetOutputReport={laborEmploymentBudgetOutputExpectations}
        pocReport={pocQATriage}
      />
      <PilotReviewStoryPanel report={pilotReviewStory} />
      <BudgetLearningLoopPanel report={budgetLearningLoop} />
      <CrossRepoContractProofPanel report={crossRepoContractProof} />
      <SyntheticConfidenceSummaryPanel report={syntheticConfidenceSummary} />
      <UIDemoQARecipePanel report={uiDemoQARecipe} />
      <CrosswalkAuditEvidencePanel report={crosswalkAudit} />
      <OCGRuleIRAdoptionEvidencePanel report={ocgRuleIRAdoption} />
      <RustFixtureBoundaryPanel report={rustFixtureBoundary} />
      <RustFixtureManifestPanel report={rustFixtureManifest} />
      <PublicDataCacheAuditPanel
        report={publicDataCacheAudit}
        manifest={manifest}
        triageReport={pocQATriage}
      />
      <RustPublicDataCacheCustodyPanel report={rustPublicDataCacheCustody} />
      <POCQATriagePanel report={pocQATriage} />
      <ValidationSuiteEvidencePanel report={validationSuiteEvidence} />
      <SyntheticQABlockerDrilldownPanel report={syntheticQABlockerReport} />
      <SyntheticQAReviewOutcomePanel report={syntheticQAReviewOutcome} />
      <SyntheticQAReviewRunPanel report={syntheticQAReviewRun} />
      <div className="grid-layout">
        <BoundaryGrid manifest={manifest} />
        <NotesPanel title="Blockers" items={manifest.blockerSummary} />
        <NotesPanel title="Red Team" items={manifest.redTeamNotes} />
      </div>

      <QualityGatePanel gates={manifest.qualityGates} />
      <MatterLinkingPreflightPanel report={matterLinkingPreflight} />
      <MatterLinkingQAGatePanel report={matterLinkingQAGate} />
      <MatterLinkingReviewOutcomePanel report={matterLinkingReviewOutcome} />
      <LaborEmploymentMatrixPanel report={laborEmploymentQAMatrix} />
      <LaborEmploymentExecutableCoveragePanel report={laborEmploymentExecutableCoverage} />
      <LaborEmploymentBlockedDriverPanel report={laborEmploymentBlockedDriverReview} />
      <LaborEmploymentBudgetOutputExpectationsPanel
        report={laborEmploymentBudgetOutputExpectations}
      />
      <LaborEmploymentBudgetQAGatePanel report={laborEmploymentBudgetQAGate} />
      <LaborEmploymentBudgetLearningFixturesPanel report={laborEmploymentBudgetLearningFixtures} />
      <LaborEmploymentBudgetOutcomeReplayReadinessPanel
        report={laborEmploymentBudgetOutcomeReplayReadiness}
      />
      <LaborEmploymentBudgetOutcomeReplayExecutionPanel
        report={laborEmploymentBudgetOutcomeReplayExecution}
      />
      <LaborEmploymentBudgetOutcomeReplayBuilderBindingPanel
        report={laborEmploymentBudgetOutcomeReplayBuilderBinding}
      />
      <LaborEmploymentBudgetOutcomeReplayConfidenceStatusPanel
        report={laborEmploymentBudgetOutcomeReplayConfidenceStatus}
      />
      <LaborEmploymentFixtureDrilldownPanel
        outputReport={laborEmploymentBudgetOutputExpectations}
        blockedReviewReport={laborEmploymentBlockedDriverReview}
      />
      <ArtifactTable artifacts={manifest.artifacts} />
    </main>
  );
}

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
