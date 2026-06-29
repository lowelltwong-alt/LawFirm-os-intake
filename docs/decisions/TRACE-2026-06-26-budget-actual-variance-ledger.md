# TRACE: Budget Actual Variance Ledger

## Decision

Extend `compare-budget-actuals` so each synthetic actual-cost comparison writes a
budget actual variance ledger.

## Why

The budget loop needs more than a point-in-time comparison report. Human budget
changes, carrier rejections, appeal outcomes, and actual costs must become
append-only candidate evidence before any Exception Lake admission or learning
proposal. A ledger row for every phase and code comparison proves coverage and
keeps within-threshold rows visible instead of storing only exceptions.

## Scope

- Add `BudgetActualVarianceLedgerEvent` and
  `BudgetActualVarianceLedgerReport` local candidate schemas.
- Add `budget_actual_variance_ledger_report.json`,
  `budget_actual_variance_ledger.jsonl`, and
  `budget_actual_variance_ledger_report.md`.
- Record phase comparison rows, code comparison rows, missing-actuals rows,
  zero-budget/positive-actual rows, and human-revised comparison context.
- Surface ledger ID, event counts, SQLite-write status, and silent-learning
  status in CLI output.
- Export schemas and test the revised-budget, missing-actuals, and CLI paths.

## Boundaries

This slice does not read billing, write billing, admit Exception Lake records,
write SQLite, submit budgets, mutate budget proposals, mutate profiles, mutate
templates, mutate carrier guidelines, or apply learning. Future production
actuals must arrive through an Orchestrator-owned governed billing-read
contract, and Lake admission must be performed by the Exception Lake runtime.

## Red Team Notes

- Recording only over-threshold rows would make later admission unable to prove
  complete comparison coverage.
- Treating a human-revised budget as the same as the original proposal would hide
  whether variance came from the matter, the original estimate, or the review
  correction.
- Zero-budget/positive-actual rows must fail into review instead of disappearing
  behind an undefined percentage.
- Missing actuals are not a pass; they are a source-follow-up state.
- A variance candidate is not permission to mutate a profile, template, budget,
  or carrier guideline.

## Verification

- Focused tests cover ledger emission for revised-budget actuals, missing actuals,
  and CLI output.
- Full validation should run `python scripts/validate_repo.py`,
  `python scripts/export_schemas.py`, `python -m ruff check src tests scripts`,
  `python -m ruff format --check src tests scripts`, `python -m pytest -q`, and
  `bash scripts/smoke_demo.sh`.
