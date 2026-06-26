# TRACE: Budget Change Ledger

Date: 2026-06-26

## Decision

Extend `record-budget-review` so every human budget review outcome writes a
typed append-only budget change ledger in addition to the existing revision
report.

## Why

Budget edits need to become inspectable learning-loop evidence without mutating
the proposed budget or silently entering the Exception Lake. A revision report
summarizes the math, but a ledger gives reviewers one row per human decision or
change with reviewer metadata, before/after totals, evidence refs, local Lake
label candidates, and no-write boundary flags.

## Implementation

- Add `BudgetChangeLedgerEvent` and `BudgetChangeLedgerReport` local candidate
  schemas.
- `record-budget-review` now writes:
  - `budget_change_ledger_report.json`;
  - `budget_change_ledger.jsonl`;
  - `budget_change_ledger_report.md`.
- Corrected budget reviews produce one ledger event per revision delta.
- `confirmed_no_change`, blocked, human-only, and declined/referred review
  outcomes produce outcome-only ledger events.
- Ledger events preserve reviewer ID, reviewer role, reviewed timestamp,
  supersession ID, field-level before/after math, evidence refs, structured refs,
  and local candidate Lake labels.

## Boundary

The ledger is local candidate evidence only. It does not mutate the original
budget, write a superseding budget, authorize client/carrier submission, read or
write billing, admit Lake or SQLite records, promote canon, or apply learning.

Semantic Substrate remains canonical authority. Exception Lake remains the
future owner of append-only runtime admission and storage. Orchestrator remains
the future owner of production human pauses, billing reads, connector captures,
and evidence packet workflows.

## Tests

- Corrected budget review writes one ledger row per human change.
- No-change review writes a no-change outcome ledger row.
- CLI summary exposes ledger report ID, entry count, SQLite write state, and
  silent learning state.
- Existing actuals comparison still uses the human-revised candidate budget
  without mutating source artifacts.
