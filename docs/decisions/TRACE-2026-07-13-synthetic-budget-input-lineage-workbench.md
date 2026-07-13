# TRACE: Synthetic Budget Input Lineage Workbench

## Decision

Expose the fixed synthetic EPLI proposal as a read-only, source-hashed input ledger
with deterministic JSON, Markdown, and macro-free XLSX outputs. The local UI may
download the same ledger as CSV, but it cannot edit inputs or run pricing logic.

## Why

The POC needs every budget number to be inspectable: staffing role, hours, hourly
rate, fees, expenses, formula, estimate basis, and basis reference. A browser-side
editable calculator would create an ungoverned pricing and provenance authority.
That authority belongs to a future Orchestrator-owned edit-session contract, after
human confirmation and owner adoption.

## Boundaries

- The only budget-math input is the pinned synthetic `legal_budget_proposal.json`.
- Rate card, carrier guideline, benchmark, and actuals sources are shown as
  `excluded_context_only`; they cannot change the ledger total.
- The CLI writes local artifacts only. The UI reads checked JSON and performs no
  connector, SQLite, Exception Lake, submission, matter-opening, or calibration write.
- The generated XLSX contains audited snapshot values and no formulas. To change
  synthetic values, edit the checked-in synthetic proposal and regenerate through the CLI.

## Evidence

- `src/lawfirm_os_intake/synthetic_budget_input_workbench.py`
- `tests/test_synthetic_budget_input_workbench.py`
- `apps/legal-intake-budget/src/fixtures/demo-synthetic-budget-input-workbench-report.json`
- `apps/legal-intake-budget/scripts/ui-browser-smoke.mjs`

## Red Team And Follow-Up

The main failure mode is accidental mixing of valid-but-incompatible context lanes
into proposal math. The workbench fails its contract when a line is not synthetic,
when fees/totals drift, or when estimate-basis references are absent. A future
editable session must be owned by Orchestrator and bind the selected rate card,
guideline version, benchmark snapshot, confirmed facts, reviewer, and change history
into one immutable request before any derived budget can be displayed.
