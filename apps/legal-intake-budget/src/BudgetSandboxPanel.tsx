import React from "react";

import type {
  SyntheticBudgetInputWorkbenchReport,
} from "./types";

type DraftLine = {
  lineNumber: number;
  estimatedHours: number;
  hourlyRate: number;
  estimatedExpenses: number;
};

type PreviewLine = DraftLine & {
  estimatedFees: number;
  lineTotal: number;
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value: number) {
  return money.format(value);
}

function csvCell(value: string | number) {
  const normalized = String(value);
  return /[",\n]/.test(normalized) ? `"${normalized.replaceAll('"', '""')}"` : normalized;
}

function downloadFile(filename: string, body: string, type: string) {
  const objectUrl = URL.createObjectURL(new Blob([body], { type }));
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

function initialDraft(report: SyntheticBudgetInputWorkbenchReport): DraftLine[] {
  return report.lines.map((line) => ({
    lineNumber: line.line_number,
    estimatedHours: line.estimated_hours,
    hourlyRate: line.hourly_rate ?? 0,
    estimatedExpenses: line.estimated_expenses,
  }));
}

function roundMoney(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function parseNonNegative(value: string, fallback: number, roundToCents = false) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return fallback;
  return roundToCents ? roundMoney(parsed) : parsed;
}

function previewLines(draft: DraftLine[]): PreviewLine[] {
  return draft.map((line) => ({
    ...line,
    estimatedFees: roundMoney(line.estimatedHours * line.hourlyRate),
    lineTotal: roundMoney(line.estimatedHours * line.hourlyRate + line.estimatedExpenses),
  }));
}

function changedLineCount(draft: DraftLine[], baseline: DraftLine[]) {
  return draft.filter((line, index) => {
    const original = baseline[index];
    return (
      line.estimatedHours !== original.estimatedHours ||
      line.hourlyRate !== original.hourlyRate ||
      line.estimatedExpenses !== original.estimatedExpenses
    );
  }).length;
}

export function BudgetSandboxPanel({
  budgetInput,
}: {
  budgetInput: SyntheticBudgetInputWorkbenchReport;
}) {
  const baseline = React.useMemo(() => initialDraft(budgetInput), [budgetInput]);
  const [draft, setDraft] = React.useState<DraftLine[]>(baseline);
  const [contingencyAmount, setContingencyAmount] = React.useState(
    roundMoney(budgetInput.contingency_amount ?? 0),
  );

  const preview = previewLines(draft);
  const draftFees = roundMoney(preview.reduce((total, line) => total + line.estimatedFees, 0));
  const draftExpenses = roundMoney(preview.reduce((total, line) => total + line.estimatedExpenses, 0));
  const draftTotal = roundMoney(draftFees + draftExpenses + contingencyAmount);
  const pinnedTotal = budgetInput.total_proposed_budget ?? 0;
  const delta = roundMoney(draftTotal - pinnedTotal);
  const changedCount =
    changedLineCount(draft, baseline) +
    (contingencyAmount === roundMoney(budgetInput.contingency_amount ?? 0) ? 0 : 1);

  const updateLine = (lineNumber: number, field: keyof Omit<DraftLine, "lineNumber">, value: string) => {
    setDraft((current) =>
      current.map((line) =>
        line.lineNumber === lineNumber
          ? {
              ...line,
              [field]: parseNonNegative(
                value,
                line[field],
                field === "hourlyRate" || field === "estimatedExpenses",
              ),
            }
          : line,
      ),
    );
  };

  const resetDraft = () => {
    setDraft(initialDraft(budgetInput));
    setContingencyAmount(roundMoney(budgetInput.contingency_amount ?? 0));
  };

  const downloadCsv = () => {
    const rows = [
      ["Phase", "Task", "Role", "Hours", "Hourly Rate", "Fees", "Expenses", "Line Total"],
      ...preview.map((line, index) => {
        const source = budgetInput.lines[index];
        return [
          source.phase_id,
          source.task_id,
          source.staffing_role,
          line.estimatedHours,
          line.hourlyRate,
          line.estimatedFees,
          line.estimatedExpenses,
          line.lineTotal,
        ];
      }),
      ["", "", "Fixed contingency", "", "", "", "", contingencyAmount],
      ["", "", "Draft total", "", "", draftFees, draftExpenses, draftTotal],
    ];
    downloadFile(
      "synthetic-budget-sandbox.csv",
      rows.map((row) => row.map(csvCell).join(",")).join("\n"),
      "text/csv;charset=utf-8",
    );
  };

  const downloadChangePackage = () => {
    downloadFile(
      "synthetic-budget-sandbox-change-package.json",
      JSON.stringify(
        {
          schema_version: "0.1",
          artifact_type: "synthetic_budget_sandbox_change_package",
          data_origin: "synthetic",
          candidate_only: true,
          local_browser_draft: true,
          source_budget_proposal_sha256: budgetInput.budget_proposal_sha256,
          pinned_total: pinnedTotal,
          fixed_contingency_amount: contingencyAmount,
          draft_total: draftTotal,
          delta,
          lines: preview,
          blocked_actions: [
            "configuration_write",
            "real_rate_import",
            "budget_submission",
            "exception_lake_write",
            "sqlite_write",
            "silent_learning",
          ],
        },
        null,
        2,
      ),
      "application/json;charset=utf-8",
    );
  };

  return (
    <section className="panel budget-sandbox-panel" aria-labelledby="budget-sandbox-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Local synthetic what-if draft</p>
          <h2 id="budget-sandbox-title">Budget Sandbox</h2>
          <code>browser-memory-only / {budgetInput.budget_proposal_id}</code>
        </div>
        <span className="state state-pending">draft only</span>
      </div>

      <div className="budget-input-banner">
        <strong>Every displayed number is a synthetic candidate input for this selected budget.</strong>
        <span>
          Edits recompute locally and disappear on refresh. They do not alter source files, rate
          authority, a matter record, or any external system.
        </span>
      </div>

      <div className="budget-input-metrics" aria-label="Budget sandbox totals">
        <article><span>Pinned Candidate</span><strong>{formatMoney(pinnedTotal)}</strong></article>
        <article><span>Draft Fees</span><strong>{formatMoney(draftFees)}</strong></article>
        <article><span>Draft Expenses</span><strong>{formatMoney(draftExpenses)}</strong></article>
        <article>
          <span>Draft Total</span><strong>{formatMoney(draftTotal)}</strong>
          <p className={delta === 0 ? "sandbox-neutral" : delta > 0 ? "sandbox-increase" : "sandbox-decrease"}>
            Includes {formatMoney(contingencyAmount)} contingency / Delta {delta >= 0 ? "+" : ""}{formatMoney(delta)}
          </p>
        </article>
      </div>

      <div className="sandbox-controls" aria-label="Budget sandbox controls">
        <label>
          Fixed contingency
          <input aria-label="Contingency amount" type="number" min="0" step="0.01" value={contingencyAmount} onChange={(event) => setContingencyAmount(parseNonNegative(event.target.value, contingencyAmount, true))} />
        </label>
        <button type="button" onClick={resetDraft} disabled={changedCount === 0}>Reset Draft</button>
        <span>{changedCount} changed input{changedCount === 1 ? "" : "s"}</span>
      </div>

      <div className="table-wrap budget-input-table-wrap">
        <table className="budget-sandbox-table">
          <thead><tr><th>Phase / Task</th><th>Role</th><th>Hours</th><th>Rate</th><th>Expenses</th><th>Draft Total</th></tr></thead>
          <tbody>{preview.map((line, index) => {
            const source = budgetInput.lines[index];
            return <tr key={line.lineNumber}>
              <td data-label="Phase / Task"><strong>{source.phase_id} / {source.task_id}</strong><br /><span>{source.task_name}</span></td>
              <td data-label="Role">{source.staffing_role.replaceAll("_", " ")}<br /><code>{source.rate_source}</code></td>
              <td data-label="Hours"><input aria-label={`Hours for line ${line.lineNumber}`} type="number" min="0" step="0.25" value={line.estimatedHours} onChange={(event) => updateLine(line.lineNumber, "estimatedHours", event.target.value)} /></td>
              <td data-label="Rate"><input aria-label={`Hourly rate for line ${line.lineNumber}`} type="number" min="0" step="0.01" value={line.hourlyRate} onChange={(event) => updateLine(line.lineNumber, "hourlyRate", event.target.value)} /></td>
              <td data-label="Expenses"><input aria-label={`Expenses for line ${line.lineNumber}`} type="number" min="0" step="0.01" value={line.estimatedExpenses} onChange={(event) => updateLine(line.lineNumber, "estimatedExpenses", event.target.value)} /></td>
              <td data-label="Draft Total"><strong>{formatMoney(line.lineTotal)}</strong><br /><span>{formatMoney(line.estimatedFees)} fees</span></td>
            </tr>;
          })}</tbody>
        </table>
      </div>

      <div className="sandbox-phase-chart" aria-label="Draft cost by phase">
        {Array.from(new Set(budgetInput.lines.map((line) => line.phase_id))).map((phaseId) => {
          const phaseTotal = preview.reduce(
            (total, line, index) => total + (budgetInput.lines[index].phase_id === phaseId ? line.lineTotal : 0),
            0,
          );
          const width = draftTotal === 0 ? 0 : (phaseTotal / draftTotal) * 100;
          return <div className="sandbox-phase-row" key={phaseId}>
            <span>{phaseId}</span><div><i style={{ width: `${width}%` }} /></div><strong>{formatMoney(phaseTotal)}</strong>
          </div>;
        })}
      </div>

      <div className="sandbox-export-row">
        <button type="button" onClick={downloadCsv}>Download Excel-Ready CSV</button>
        <button type="button" onClick={downloadChangePackage}>Download Candidate Change Package</button>
        <span>CSV opens in Excel; the JSON package is an untrusted candidate draft for a later reviewed CLI regeneration. Rate-card rows remain excluded context unless a future contract binds them.</span>
      </div>

      <div className="budget-input-footer">
        <span>No configuration write, real-rate import, budget submission, Lake write, SQLite write, or silent learning occurs here.</span>
      </div>
    </section>
  );
}
