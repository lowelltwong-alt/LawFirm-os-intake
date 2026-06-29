# TRACE: Carrier Rejection Decision Ledger

Date: 2026-06-26

## Decision

Extend `capture-carrier-rejections` so each synthetic reconciliation run writes
a carrier rejection decision ledger.

## Why

The carrier loop needs 100% response-state capture before learning can be
trusted. Rejections, missing responses, unlinked notices, parse failures,
duplicate notices, pending fix/appeal decisions, appeal results, recovered
amounts, and write-downs must be visible as append-only evidence candidates
before anything can enter Lake admission review or learning gates.

## Implementation

- Add `CarrierRejectionDecisionLedgerEvent` and
  `CarrierRejectionDecisionLedgerReport` local candidate schemas.
- `capture-carrier-rejections` now writes:
  - `carrier_rejection_decision_ledger_report.json`;
  - `carrier_rejection_decision_ledger.jsonl`;
  - `carrier_rejection_decision_ledger_report.md`.
- The ledger creates rows for:
  - captured rejection or missing-response cases;
  - duplicate notice collapse;
  - pending human fix/appeal decisions;
  - captured appeal results;
  - financial outcomes with recovered/write-down math.

## Boundary

The ledger is local candidate evidence only. It does not submit appeals, write
portal/email/billing systems, admit Lake or SQLite records, mutate budgets,
change carrier guidelines, or apply learning. Future production capture,
human pauses, appeal submission, and evidence packets remain Orchestrator-owned.
Lake admission and storage remain Exception Lake-owned.

## Tests

- Synthetic capture writes ledger JSON, JSONL, and Markdown.
- Ledger includes rejection, missing-response, unlinked, parse-failure,
  duplicate-collapse, pending decision, appeal-result, and financial-outcome
  event kinds.
- Appeal-result financial math preserves appealed, recovered, write-down, and
  remaining write-down amounts.
- Missing follow-up metadata marks the ledger blocked.
- CLI output reports ledger count and no-write/no-learning flags.
