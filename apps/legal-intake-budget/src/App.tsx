import React from "react";
import { createRoot } from "react-dom/client";

import demoLaborEmploymentBlockedDriverReview from "./fixtures/demo-labor-employment-blocked-driver-impact-review-report.json";
import demoLaborEmploymentBudgetOutputExpectations from "./fixtures/demo-labor-employment-budget-output-expectations-report.json";
import demoLaborEmploymentQAMatrix from "./fixtures/demo-labor-employment-qa-matrix-report.json";
import demoManifest from "./fixtures/demo-run-manifest.json";
import demoMatterLinkingPreflight from "./fixtures/demo-matter-linking-preflight-report.json";
import demoSyntheticQABlockerReport from "./fixtures/demo-synthetic-qa-blocker-report.json";
import demoSyntheticConfidenceSummary from "./fixtures/demo-synthetic-confidence-summary-report.json";
import demoSyntheticQAReviewRun from "./fixtures/demo-synthetic-qa-review-run-report.json";
import demoReviewDataBundle from "./fixtures/demo-ui-review-data-bundle.json";
import {
  assertMatterLinkingPreflightReport,
  assertLaborEmploymentBudgetOutputExpectationReport,
  assertLaborEmploymentBlockedDriverImpactReviewReport,
  assertLaborEmploymentQAMatrixReport,
  assertReadOnlyManifest,
  assertSyntheticQABlockerReport,
  assertSyntheticConfidenceSummaryReport,
  assertSyntheticQAReviewRunReport,
  assertUIReviewDataBundle,
  failingQualityGates,
} from "./data-contract";
import type {
  ArtifactStatus,
  GateState,
  LaborEmploymentAllowedBudgetOutput,
  LaborEmploymentBudgetOutputExpectationCase,
  LaborEmploymentBudgetOutputExpectationReport,
  LaborEmploymentBlockedDriverImpactCaseReview,
  LaborEmploymentBlockedDriverImpactReviewReport,
  LaborEmploymentBudgetGateEffect,
  LaborEmploymentBudgetReadinessState,
  LaborEmploymentQAMatrixReport,
  MatterLinkingPreflightReport,
  QualityGate,
  QualityGateStatus,
  ReviewArtifact,
  ReviewManifest,
  SyntheticQABlockerActionState,
  SyntheticQABlockerReport,
  SyntheticQABlockerRowState,
  SyntheticConfidenceSummaryReport,
  SyntheticConfidenceSummaryItemState,
  SyntheticQAReviewRunReport,
  UIReviewDataBundle,
} from "./types";
import "./styles.css";

const reviewDataBundle = demoReviewDataBundle as UIReviewDataBundle;
const manifest = demoManifest as ReviewManifest;
const syntheticQAReviewRun = demoSyntheticQAReviewRun as SyntheticQAReviewRunReport;
const syntheticQABlockerReport = demoSyntheticQABlockerReport as SyntheticQABlockerReport;
const syntheticConfidenceSummary =
  demoSyntheticConfidenceSummary as SyntheticConfidenceSummaryReport;
const matterLinkingPreflight = demoMatterLinkingPreflight as MatterLinkingPreflightReport;
const laborEmploymentQAMatrix = demoLaborEmploymentQAMatrix as LaborEmploymentQAMatrixReport;
const laborEmploymentBlockedDriverReview =
  demoLaborEmploymentBlockedDriverReview as LaborEmploymentBlockedDriverImpactReviewReport;
const laborEmploymentBudgetOutputExpectations =
  demoLaborEmploymentBudgetOutputExpectations as LaborEmploymentBudgetOutputExpectationReport;
const bundleContractFailures = assertUIReviewDataBundle(reviewDataBundle);
const manifestContractFailures = assertReadOnlyManifest(manifest);
const syntheticQAReviewRunFailures = assertSyntheticQAReviewRunReport(syntheticQAReviewRun);
const syntheticQABlockerFailures = assertSyntheticQABlockerReport(syntheticQABlockerReport);
const syntheticConfidenceSummaryFailures =
  assertSyntheticConfidenceSummaryReport(syntheticConfidenceSummary);
const matterLinkingFailures = assertMatterLinkingPreflightReport(matterLinkingPreflight);
const matrixContractFailures = assertLaborEmploymentQAMatrixReport(laborEmploymentQAMatrix);
const blockedDriverContractFailures =
  assertLaborEmploymentBlockedDriverImpactReviewReport(laborEmploymentBlockedDriverReview);
const budgetOutputExpectationFailures = assertLaborEmploymentBudgetOutputExpectationReport(
  laborEmploymentBudgetOutputExpectations,
);
const contractFailures = [
  ...bundleContractFailures,
  ...manifestContractFailures,
  ...syntheticQAReviewRunFailures,
  ...syntheticQABlockerFailures,
  ...syntheticConfidenceSummaryFailures,
  ...matterLinkingFailures,
  ...matrixContractFailures,
  ...blockedDriverContractFailures,
  ...budgetOutputExpectationFailures,
];

function gateClass(state: GateState | ArtifactStatus | QualityGateStatus | SyntheticQABlockerRowState) {
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

type FixtureDrilldownRow = {
  outputCase: LaborEmploymentBudgetOutputExpectationCase;
  blockerReview?: LaborEmploymentBlockedDriverImpactCaseReview;
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
          <span>Weak Signals</span>
          <strong>{report.weak_signal_count}</strong>
        </div>
        <div>
          <span>Split Evidence</span>
          <strong>{report.strong_negative_signal_count}</strong>
        </div>
      </div>

      <div className="table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Candidate Cluster</th>
              <th>Support</th>
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
      <SyntheticConfidenceSummaryPanel report={syntheticConfidenceSummary} />
      <SyntheticQABlockerDrilldownPanel report={syntheticQABlockerReport} />
      <SyntheticQAReviewRunPanel report={syntheticQAReviewRun} />
      <div className="grid-layout">
        <BoundaryGrid manifest={manifest} />
        <NotesPanel title="Blockers" items={manifest.blockerSummary} />
        <NotesPanel title="Red Team" items={manifest.redTeamNotes} />
      </div>

      <QualityGatePanel gates={manifest.qualityGates} />
      <MatterLinkingPreflightPanel report={matterLinkingPreflight} />
      <LaborEmploymentMatrixPanel report={laborEmploymentQAMatrix} />
      <LaborEmploymentBlockedDriverPanel report={laborEmploymentBlockedDriverReview} />
      <LaborEmploymentBudgetOutputExpectationsPanel
        report={laborEmploymentBudgetOutputExpectations}
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
