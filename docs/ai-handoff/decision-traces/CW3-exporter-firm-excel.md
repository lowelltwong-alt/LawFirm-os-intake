# Decision Trace — CW3 Exporter Seam + Firm-Excel Renderer

Wave: CW3 of the converged Opus marathon. Branch:
`claude/cw3-exporter-firm-excel`, off the merged `main` (CW0–CW2 merged as PRs
#108/#109/#110). Candidate-only, synthetic-only, exact integer minor units.

## Situation

The layered pipeline treats Excel as exporter #1, not the tool. The firm's
sanitized budget template is dollar-per-UTBMS-task only and carries two formula
defects (missing phase-subtotal formulas G33/G47/G61/G77/G85; a P85 grand-expense
formula that double-counts P129). The engine needs a pluggable exporter seam and a
firm-Excel renderer that matches the template shape but corrects those defects and
keeps the role/rate/hours decomposition internal.

## Decision

1. **Exporter plugin boundary** (`budget_exporters.py`): a `BudgetExporter`
   protocol (`format_id`, `export(model, path) -> BudgetExportResult`,
   `documented_deviations()`) with a registry (`register`/`get`/`list`). The
   structured `FirmExcelBudgetExport` model is the source of truth.
2. **Firm-Excel renderer** (`FirmExcelExporter`, `firm_excel_v0`): matches the
   sanitized template shape — UTBMS phase/task rows; Original / Billed / Remaining
   / New columns (G/J/M/P) — writing per-task dollars as numbers and **corrected**
   formulas: every phase Original/New subtotal is an explicit `SUM` over its task
   rows (fixes the template's missing G33–G85), each task summed exactly once
   (fixes the P85 double-count of P129), Remaining = G−J, grand total = sum of the
   now-complete phase subtotals. Both deviations are written into the workbook and
   returned by `documented_deviations()`.
3. **Model → export mapping** (`firm_excel_export_from_projection_report`): groups
   a synthetic budget's lines into dollars-per-UTBMS-task; the role/rate/hours
   decomposition stays internal — only dollars per task are exported.
4. **Round-trip** (`read_firm_excel_task_totals`): re-reads the numeric task cells
   and recomputes phase subtotals + totals in minor units, reconciling to the
   model exactly (independent of any spreadsheet formula evaluation).
5. **UI**: a Case Sizing / Proportionality / Settlement Posture panel rendering the
   CW2 `CaseSizingReport` (sized work plan, budget/exposure ratio and band, ranked
   postures + recommended envelope) with the candidate banner; the posture table
   scrolls inside its own `table-wrap` (mobile-contained).

## Non-decision

- No client submission, no real template data ingested — the exporter matches the
  documented shape and writes synthetic candidate content.
- Role/rate/hours stay internal (not exported); the budget model is unchanged.
- LEDES/PDF exporters are future plugins behind the same seam.

## Authority impact

Local candidate work; new candidate schemas and an additive exporter module. No
canonical/promoted contract change; no cross-repo write.

## Evidence

- `tests/test_budget_exporters.py` — 6 tests (failing-test-first): totals
  fail-closed recompute; registry; **round-trip reconciles to the model exactly**;
  documented deviations (G33, P129); no active/external workbook content;
  dollars-per-task-only from the projection.
- Three exported schemas; `config`-free (no new policy needed).

## Alternatives rejected

- **Reproduce the template's `+`-chained subtotals.** Rejected: that is exactly
  where the defects live; `SUM(range)` is correct and sums each task once.
- **Rely on formula evaluation for the round-trip.** Rejected: openpyxl does not
  evaluate formulas; reconciling on the numeric task cells is exact and
  toolchain-independent.

## Risks and rollback

- Risk: the exporter shape drifts from the firm template. Contained by the
  round-trip test, `export_schemas` idempotency, and the export-shape review gate.
  Rollback is a single-branch revert; the module is additive.

## Validation

ruff check/format clean; `export_schemas.py` idempotent (three new schemas);
`validate_repo.py` passed; `run_full_pytest.py -q` full suite passed; `npm run
build` OK; `npm run smoke:browser` passed (posture table mobile-contained).

## Human gates

CW3 human gate: **export-shape review vs the firm template**. Opened by the agent;
it does not merge its own PR and does not push `main`.

## DAD

Per-wave preflight/lesson/postflight run through the canonical `asset-dir` lesson
pipeline (not the mailbox).
