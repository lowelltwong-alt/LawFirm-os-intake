import React from "react";
import { createRoot } from "react-dom/client";

import demoLaborEmploymentQAMatrix from "./fixtures/demo-labor-employment-qa-matrix-report.json";
import demoManifest from "./fixtures/demo-run-manifest.json";
import {
  assertLaborEmploymentQAMatrixReport,
  assertReadOnlyManifest,
  failingQualityGates,
} from "./data-contract";
import type {
  ArtifactStatus,
  GateState,
  LaborEmploymentBudgetGateEffect,
  LaborEmploymentBudgetReadinessState,
  LaborEmploymentQAMatrixReport,
  QualityGate,
  QualityGateStatus,
  ReviewArtifact,
  ReviewManifest,
} from "./types";
import "./styles.css";

const manifest = demoManifest as ReviewManifest;
const laborEmploymentQAMatrix = demoLaborEmploymentQAMatrix as LaborEmploymentQAMatrixReport;
const manifestContractFailures = assertReadOnlyManifest(manifest);
const matrixContractFailures = assertLaborEmploymentQAMatrixReport(laborEmploymentQAMatrix);
const contractFailures = [...manifestContractFailures, ...matrixContractFailures];

function gateClass(state: GateState | ArtifactStatus | QualityGateStatus) {
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

      <div className="grid-layout">
        <BoundaryGrid manifest={manifest} />
        <NotesPanel title="Blockers" items={manifest.blockerSummary} />
        <NotesPanel title="Red Team" items={manifest.redTeamNotes} />
      </div>

      <QualityGatePanel gates={manifest.qualityGates} />
      <LaborEmploymentMatrixPanel report={laborEmploymentQAMatrix} />
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
