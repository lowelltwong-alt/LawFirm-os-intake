import React from "react";
import { createRoot } from "react-dom/client";

import demoBudgetLearningLoop from "./fixtures/demo-budget-learning-loop-report.json";
import demoLaborEmploymentBlockedDriverReview from "./fixtures/demo-labor-employment-blocked-driver-impact-review-report.json";
import demoLaborEmploymentBudgetLearningFixtures from "./fixtures/demo-labor-employment-budget-learning-fixtures-report.json";
import demoLaborEmploymentBudgetOutputExpectations from "./fixtures/demo-labor-employment-budget-output-expectations-report.json";
import demoLaborEmploymentBudgetQAGate from "./fixtures/demo-labor-employment-budget-qa-gate-report.json";
import demoLaborEmploymentExecutableCoverage from "./fixtures/demo-labor-employment-executable-coverage-report.json";
import demoLaborEmploymentQAMatrix from "./fixtures/demo-labor-employment-qa-matrix-report.json";
import demoManifest from "./fixtures/demo-run-manifest.json";
import demoMatterLinkingPreflight from "./fixtures/demo-matter-linking-preflight-report.json";
import demoMatterLinkingQAGate from "./fixtures/demo-matter-linking-qa-gate-report.json";
import demoMatterLinkingReviewOutcome from "./fixtures/demo-matter-linking-review-outcome-report.json";
import demoPocQATriage from "./fixtures/demo-poc-qa-triage-report.json";
import demoSyntheticQABlockerReport from "./fixtures/demo-synthetic-qa-blocker-report.json";
import demoSyntheticQAReviewOutcome from "./fixtures/demo-synthetic-qa-review-outcome-report.json";
import demoSyntheticConfidenceSummary from "./fixtures/demo-synthetic-confidence-summary-report.json";
import demoSyntheticQAReviewRun from "./fixtures/demo-synthetic-qa-review-run-report.json";
import demoReviewDataBundle from "./fixtures/demo-ui-review-data-bundle.json";
import demoValidationSuiteEvidence from "./fixtures/demo-validation-suite-evidence-report.json";
import {
  assertMatterLinkingPreflightReport,
  assertMatterLinkingQAGateReport,
  assertMatterLinkingReviewOutcomeReport,
  assertBudgetLearningLoopReport,
  assertLaborEmploymentBudgetOutputExpectationReport,
  assertLaborEmploymentBudgetLearningFixtureReport,
  assertLaborEmploymentBudgetQAGateReport,
  assertLaborEmploymentBlockedDriverImpactReviewReport,
  assertLaborEmploymentExecutableCoverageReport,
  assertLaborEmploymentQAMatrixReport,
  assertPOCQATriageReport,
  assertReadOnlyManifest,
  assertSyntheticQABlockerReport,
  assertSyntheticQAReviewOutcomeReport,
  assertSyntheticConfidenceSummaryReport,
  assertSyntheticQAReviewRunReport,
  assertUIReviewDataBundle,
  assertValidationSuiteEvidenceReport,
  failingQualityGates,
} from "./data-contract";
import type {
  ArtifactStatus,
  BudgetLearningLoopReport,
  GateState,
  LaborEmploymentAllowedBudgetOutput,
  LaborEmploymentBudgetLearningFixtureReport,
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
  QualityGate,
  QualityGateStatus,
  ReviewArtifact,
  ReviewManifest,
  SyntheticQABlockerActionState,
  SyntheticQABlockerReport,
  SyntheticQABlockerRowState,
  SyntheticQAReviewOutcomeReport,
  SyntheticQAReviewOutcomeStatus,
  SyntheticConfidenceSummaryReport,
  SyntheticConfidenceSummaryItemState,
  SyntheticQAReviewRunReport,
  UIReviewDataBundle,
  ValidationSuiteEvidenceReport,
  ValidationSuiteStepStatus,
} from "./types";
import "./styles.css";

const reviewDataBundle = demoReviewDataBundle as UIReviewDataBundle;
const manifest = demoManifest as ReviewManifest;
const syntheticQAReviewRun = demoSyntheticQAReviewRun as SyntheticQAReviewRunReport;
const syntheticQABlockerReport = demoSyntheticQABlockerReport as SyntheticQABlockerReport;
const syntheticQAReviewOutcome =
  demoSyntheticQAReviewOutcome as SyntheticQAReviewOutcomeReport;
const syntheticConfidenceSummary =
  demoSyntheticConfidenceSummary as SyntheticConfidenceSummaryReport;
const pocQATriage = demoPocQATriage as POCQATriageReport;
const validationSuiteEvidence =
  demoValidationSuiteEvidence as ValidationSuiteEvidenceReport;
const matterLinkingPreflight = demoMatterLinkingPreflight as MatterLinkingPreflightReport;
const matterLinkingQAGate = demoMatterLinkingQAGate as MatterLinkingQAGateReport;
const matterLinkingReviewOutcome =
  demoMatterLinkingReviewOutcome as MatterLinkingReviewOutcomeReport;
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
const budgetLearningLoop = demoBudgetLearningLoop as BudgetLearningLoopReport;
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
const matterLinkingFailures = assertMatterLinkingPreflightReport(matterLinkingPreflight);
const matterLinkingQAGateFailures = assertMatterLinkingQAGateReport(matterLinkingQAGate);
const matterLinkingReviewOutcomeFailures =
  assertMatterLinkingReviewOutcomeReport(matterLinkingReviewOutcome);
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
const budgetLearningLoopFailures = assertBudgetLearningLoopReport(budgetLearningLoop);
const contractFailures = [
  ...bundleContractFailures,
  ...manifestContractFailures,
  ...syntheticQAReviewRunFailures,
  ...syntheticQABlockerFailures,
  ...syntheticQAReviewOutcomeFailures,
  ...syntheticConfidenceSummaryFailures,
  ...pocQATriageFailures,
  ...validationSuiteEvidenceFailures,
  ...matterLinkingFailures,
  ...matterLinkingQAGateFailures,
  ...matterLinkingReviewOutcomeFailures,
  ...matrixContractFailures,
  ...executableCoverageFailures,
  ...blockedDriverContractFailures,
  ...budgetOutputExpectationFailures,
  ...budgetQAGateFailures,
  ...budgetLearningFixtureFailures,
  ...budgetLearningLoopFailures,
];

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
    validationReport.timed_out_step_count === 0;
  const pocReady = pocReport.status === "poc_qa_ready_for_review";
  const reviewQueueReady =
    blockerReport.failed_row_count === 0 && blockerReport.blocked_row_count === 0;

  return [
    {
      id: "validation-evidence",
      label: "Validation Evidence",
      state: validationReady && pocReady ? "passed" : "blocked",
      metric: `${validationReport.passed_step_count}/${validationReport.step_count}`,
      detail: "Full pytest, smoke demo, schema export, lint, and repo validation evidence is attached.",
      nextAction: validationReady
        ? "Use this as the baseline before adding the next fixture family."
        : "Refresh validation evidence before expanding synthetic QA.",
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
    validationSuiteEvidenceFailures.length === 0
      ? "state state-passed"
      : "state state-blocked";

  return (
    <section className="panel validation-panel" aria-labelledby="validation-suite-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">QA proof</p>
          <h2 id="validation-suite-title">Validation Suite Evidence</h2>
          <code>{report.validation_suite_evidence_report_id}</code>
        </div>
        <span className={statusClass}>
          {report.status === "validation_suite_passed" ? "passed" : "blocked"}
        </span>
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
        Evidence is local JSON only. Lake writes:{" "}
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
      <BudgetLearningLoopPanel report={budgetLearningLoop} />
      <SyntheticConfidenceSummaryPanel report={syntheticConfidenceSummary} />
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
