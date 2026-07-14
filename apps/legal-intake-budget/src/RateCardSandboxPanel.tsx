import React from "react";

import type { SyntheticRateCardWorkbenchReport } from "./types";

type DraftCell = {
  cellId: string;
  carrierId: string;
  carrierName: string;
  state: string;
  title: string;
  hourlyRate: number;
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

function roundMoney(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function initialDraft(report: SyntheticRateCardWorkbenchReport): DraftCell[] {
  return report.rows.map((row) => ({
    cellId: `${row.carrier_id}|${row.state}|${row.title}`,
    carrierId: row.carrier_id,
    carrierName: row.carrier_name,
    state: row.state,
    title: row.title,
    hourlyRate: row.hourly_rate,
  }));
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

function parsePositiveRate(value: string, fallback: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return roundMoney(parsed);
}

export function RateCardSandboxPanel({
  rateCard,
}: {
  rateCard: SyntheticRateCardWorkbenchReport;
}) {
  const baseline = React.useMemo(() => initialDraft(rateCard), [rateCard]);
  const [draft, setDraft] = React.useState<DraftCell[]>(baseline);
  const [rateErrors, setRateErrors] = React.useState<Record<string, string>>({});
  const [carrierFilter, setCarrierFilter] = React.useState("all");
  const [stateFilter, setStateFilter] = React.useState("all");
  const pinnedTotal = roundMoney(baseline.reduce((total, cell) => total + cell.hourlyRate, 0));
  const draftTotal = roundMoney(draft.reduce((total, cell) => total + cell.hourlyRate, 0));
  const delta = roundMoney(draftTotal - pinnedTotal);
  const changedCellCount = draft.filter(
    (cell, index) => cell.hourlyRate !== baseline[index].hourlyRate,
  ).length;
  const carriers = [...new Map(draft.map((cell) => [cell.carrierId, cell.carrierName])).entries()];
  const states = [...new Set(draft.map((cell) => cell.state))].sort();
  const visibleCells = draft.filter(
    (cell) =>
      (carrierFilter === "all" || cell.carrierId === carrierFilter) &&
      (stateFilter === "all" || cell.state === stateFilter),
  );
  const maxRate = Math.max(...visibleCells.map((cell) => cell.hourlyRate), 1);

  const updateCell = (cellId: string, value: string) => {
    const parsed = Number(value);
    const rounded = Math.round((parsed + Number.EPSILON) * 100) / 100;
    if (!Number.isFinite(parsed) || !Number.isFinite(rounded) || rounded < 0.01) {
      setRateErrors((current) => ({
        ...current,
        [cellId]: "Enter a finite hourly rate of at least $0.01.",
      }));
      return;
    }
    setRateErrors((current) => {
      const { [cellId]: _ignored, ...remaining } = current;
      return remaining;
    });
    setDraft((current) =>
      current.map((cell) =>
        cell.cellId === cellId
          ? { ...cell, hourlyRate: parsePositiveRate(value, cell.hourlyRate) }
          : cell,
      ),
    );
  };

  const resetDraft = () => {
    setDraft(initialDraft(rateCard));
    setRateErrors({});
  };

  const downloadCsv = () => {
    const rows = [
      ["Carrier ID", "Carrier", "State", "Title", "Pinned Rate", "Candidate Rate", "Delta"],
      ...draft.map((cell, index) => [
        cell.carrierId,
        cell.carrierName,
        cell.state,
        cell.title,
        baseline[index].hourlyRate,
        cell.hourlyRate,
        roundMoney(cell.hourlyRate - baseline[index].hourlyRate),
      ]),
      ["", "", "", "Pinned rate total", pinnedTotal, "", ""],
      ["", "", "", "Candidate rate total", "", draftTotal, delta],
    ];
    downloadFile(
      "synthetic-rate-card-sandbox.csv",
      rows.map((row) => row.map(csvCell).join(",")).join("\n"),
      "text/csv;charset=utf-8",
    );
  };

  const downloadChangePackage = () => {
    downloadFile(
      "synthetic-rate-card-sandbox-change-package.json",
      JSON.stringify(
        {
          schema_version: "0.1",
          artifact_type: "synthetic_rate_card_sandbox_change_package",
          data_origin: "synthetic",
          candidate_only: true,
          local_browser_draft: true,
          source_rate_card_sha256: rateCard.rate_card_sha256,
          pinnedRateTotal: pinnedTotal,
          draftRateTotal: draftTotal,
          delta,
          changedCellCount,
          cells: draft.map((cell) => ({
            cellId: cell.cellId,
            carrierId: cell.carrierId,
            state: cell.state,
            title: cell.title,
            hourlyRate: cell.hourlyRate,
          })),
          blocked_actions: [
            "configuration_write",
            "real_rate_import",
            "rate_card_apply_to_budget",
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
    <section className="panel rate-card-sandbox-panel" aria-labelledby="rate-card-sandbox-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Local synthetic what-if draft</p>
          <h2 id="rate-card-sandbox-title">Rate Card Sandbox</h2>
          <code>browser-memory-only / {rateCard.rate_card_id}</code>
        </div>
        <span className="state state-pending">draft only</span>
      </div>

      <div className="budget-input-banner">
        <strong>Every rate is a synthetic candidate cell, not a real carrier or firm rate.</strong>
        <span>
          Edits update only this browser draft. They do not alter the source catalog, import real
          rates, apply a rate to a budget, or write to any external system.
        </span>
      </div>

      <div className="budget-input-metrics" aria-label="Rate card sandbox totals">
        <article><span>Pinned Rate Total</span><strong>{formatMoney(pinnedTotal)}</strong></article>
        <article><span>Candidate Rate Total</span><strong>{formatMoney(draftTotal)}</strong></article>
        <article><span>Changed Cells</span><strong>{changedCellCount}</strong></article>
        <article>
          <span>Candidate Delta</span><strong>{delta >= 0 ? "+" : ""}{formatMoney(delta)}</strong>
          <p className={delta === 0 ? "sandbox-neutral" : delta > 0 ? "sandbox-increase" : "sandbox-decrease"}>
            Catalog-only comparison
          </p>
        </article>
      </div>

      <div className="sandbox-controls" aria-label="Rate card sandbox controls">
        <label>
          Carrier
          <select value={carrierFilter} onChange={(event) => setCarrierFilter(event.target.value)}>
            <option value="all">All carriers</option>
            {carriers.map(([carrierId, carrierName]) => <option key={carrierId} value={carrierId}>{carrierName}</option>)}
          </select>
        </label>
        <label>
          State
          <select value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}>
            <option value="all">All states</option>
            {states.map((state) => <option key={state} value={state}>{state}</option>)}
          </select>
        </label>
        <button type="button" onClick={resetDraft} disabled={changedCellCount === 0 && Object.keys(rateErrors).length === 0}>Reset Draft</button>
        <span>{changedCellCount} changed cell{changedCellCount === 1 ? "" : "s"}</span>
      </div>

      <div className="table-wrap rate-card-table-wrap">
        <table className="rate-card-sandbox-table">
          <thead><tr><th>Carrier / State</th><th>Role</th><th>Pinned Rate</th><th>Candidate Rate</th><th>Delta</th></tr></thead>
          <tbody>{visibleCells.map((cell) => {
            const baselineCell = baseline.find((candidate) => candidate.cellId === cell.cellId)!;
            const cellDelta = roundMoney(cell.hourlyRate - baselineCell.hourlyRate);
            return <tr key={cell.cellId}>
              <td data-label="Carrier / State"><strong>{cell.carrierName}</strong><br /><code>{cell.carrierId} / {cell.state}</code></td>
              <td data-label="Role">{cell.title.replaceAll("_", " ")}</td>
              <td data-label="Pinned Rate">{formatMoney(baselineCell.hourlyRate)}</td>
              <td data-label="Candidate Rate"><input aria-label={`Hourly rate for ${cell.carrierId} ${cell.state} ${cell.title}`} type="number" min="0.01" step="0.01" value={cell.hourlyRate} onChange={(event) => updateCell(cell.cellId, event.target.value)} />{rateErrors[cell.cellId] && <span className="sandbox-input-error" role="alert">{rateErrors[cell.cellId]}</span>}</td>
              <td data-label="Delta" className={cellDelta === 0 ? "sandbox-neutral" : cellDelta > 0 ? "sandbox-increase" : "sandbox-decrease"}>{cellDelta >= 0 ? "+" : ""}{formatMoney(cellDelta)}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>

      <div className="sandbox-phase-chart" aria-label="Candidate hourly rate comparison">
        {visibleCells.map((cell) => <div className="sandbox-phase-row" key={cell.cellId}>
          <span>{cell.state} / {cell.title.replaceAll("_", " ")}</span>
          <div><i style={{ width: `${(cell.hourlyRate / maxRate) * 100}%` }} /></div>
          <strong>{formatMoney(cell.hourlyRate)}</strong>
        </div>)}
      </div>

      <div className="sandbox-export-row">
        <button type="button" onClick={downloadCsv} disabled={Object.keys(rateErrors).length > 0}>Download Excel-Ready CSV</button>
        <button type="button" onClick={downloadChangePackage} disabled={Object.keys(rateErrors).length > 0}>Download Candidate Change Package</button>
        <span>CSV opens in Excel. The JSON package is an untrusted candidate draft for the local XLSX validation CLI; it cannot change the catalog or price a budget.</span>
      </div>

      <div className="budget-input-footer">
        <span>No configuration write, real-rate import, rate-card application, budget submission, Lake write, SQLite write, or silent learning occurs here.</span>
      </div>
    </section>
  );
}
