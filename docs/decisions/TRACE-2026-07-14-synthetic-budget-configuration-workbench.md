# TRACE: Synthetic Budget Configuration Workbench

## Decision

Add a deterministic, source-hashed inventory of every editable numeric synthetic
budget input across the practice profile, carrier rate card, carrier guideline,
and L&E nonlinear-template source. It produces local JSON, Markdown, a
macro-free Excel worksheet, and a read-only UI table/CSV export.

## Why

The POC needs an obvious answer to where each rate, task-hour, expense,
contingency, and carrier threshold lives. A spreadsheet is useful for review and
copying values, but making it an automatic import path would create a second,
untracked pricing authority.

## Guardrails

- Every source path and source hash is shown with each editable numeric entry.
- Every entry labels its math effect: proposal fallback rate, template hours or
  expenses, contingency, guideline projection cap, preapproval threshold, or
  named-timekeeper override.
- The builder fails closed and omits its XLSX when a source is missing, a value
  is invalid, paths collide, or any nested `contains_real_*` flag is true.
- The L&E nonlinear template remains a visible structural source; its tiers are
  not fabricated into numeric pricing values.
- The XLSX and browser CSV are reference/edit worksheets only. Runtime code
  never imports them; changes require a reviewed edit to the declared synthetic
  YAML/JSON source followed by regeneration.

## Evidence

- `src/lawfirm_os_intake/synthetic_budget_configuration_workbench.py`
- `tests/test_synthetic_budget_configuration_workbench.py`
- `tests/test_ui_foundation_contract.py`
- `apps/legal-intake-budget/scripts/ui-browser-smoke.mjs`

## Non-Applicability

This does not authorize real-rate ingestion, a carrier panel schedule, a budget
submission, browser-side pricing, or a production edit session. Future real
values require a pinned, reviewed private snapshot owned by Legal Knowledge
Runtime and consumed through the applicable Orchestrator contract.
