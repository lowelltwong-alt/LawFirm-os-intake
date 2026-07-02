import React from "react";
import { createRoot } from "react-dom/client";

import demoManifest from "./fixtures/demo-run-manifest.json";
import { assertReadOnlyManifest, failingQualityGates } from "./data-contract";
import type {
  ArtifactStatus,
  GateState,
  QualityGate,
  QualityGateStatus,
  ReviewArtifact,
  ReviewManifest,
} from "./types";
import "./styles.css";

const manifest = demoManifest as ReviewManifest;
const contractFailures = assertReadOnlyManifest(manifest);

function gateClass(state: GateState | ArtifactStatus | QualityGateStatus) {
  return `state state-${state.replace("_", "-")}`;
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
