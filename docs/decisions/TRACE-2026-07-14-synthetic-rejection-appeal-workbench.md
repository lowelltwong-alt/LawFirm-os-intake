# TRACE: Synthetic Rejection And Appeal Workbench

## Decision

Add a deterministic, read-only workbench that replays the existing synthetic
carrier-rejection capture, review, decision-ledger, and learning-candidate flow.
It presents disputed, recovered, and write-down amounts alongside the human
decisions still required for each captured case.

## Why

The budget workbenches already make proposal inputs, guideline projections, and
actuals variance inspectable. Carrier feedback is another material budget signal,
but a review screen must not turn an intake-local candidate into an appeal
submission, a Lake admission, or a silent learning update.

## Guardrails

- Replay only the pinned `epli-carrier-clean` synthetic proposal and response bundle.
- Hash both inputs, preserve source-bound case counts, and reconcile all financial
  totals to the existing decision ledger.
- Normalize run timestamps and temporary review-file locations for reproducible
  fixture generation.
- Write local JSON, Markdown, and a macro-free XLSX only; prefix formula-like
  spreadsheet text so it is displayed as text.
- The UI reads checked JSON and cannot submit an appeal, mutate a budget, write
  the Exception Lake or SQLite, open a matter, or apply learning.

## Evidence

- `src/lawfirm_os_intake/synthetic_rejection_appeal_workbench.py`
- `tests/test_synthetic_rejection_appeal_workbench.py`
- `tests/test_ui_foundation_contract.py`
- `apps/legal-intake-budget/scripts/ui-browser-smoke.mjs`

## Non-Applicability

This is not a production carrier-portal or email ingestion path. Any future
appeal submission requires Orchestrator ownership, human authorization, and an
admitted Exception Lake event; learning remains a reviewed candidate process.
