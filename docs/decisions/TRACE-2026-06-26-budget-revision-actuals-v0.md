# TRACE 2026-06-26 Budget Revision And Actuals v0

## Decision

Implement a local candidate-only loop for human budget review changes and
synthetic budget-vs-actual comparison. The loop records append-only human edits,
calculates phase and UTBMS-code deltas, compares original or human-revised
candidate budgets to synthetic actuals, and emits dry-run Exception Lake
candidates for human review.

## Why

Carrier rejections, appeal outcomes, and actual-cost variance cannot become a
useful learning loop unless human budget corrections and actual-cost outcomes
are recorded as structured evidence. The first safe step is deterministic local
proof, not production connectors or profile mutation.

## Implemented

- `record-budget-review` writes a bound `budget_review_change_record.json`,
  appends to `budget_revision_history.jsonl`, writes
  `budget_revision_report.json` and `.md`, and emits dry-run
  `budget_human_change_recorded` candidates.
- `BudgetRevisionReport` preserves original/revised phase totals,
  original/revised code totals, line-level deltas, review outcome, mutation
  policy, and no-submission/no-Lake-write flags.
- `compare-budget-actuals` reads a synthetic `BudgetActualsSource`, optionally
  compares against a `budget_revision_report.json`, and writes
  `budget_actual_comparison_report.json`, `.md`, and variance candidates.
- Actual comparison now supports phase and code rows, comparison budget state,
  actual resolution scenario, variance-driver candidates, and
  learning-disposition candidates.
- Zero-budget/positive-actual rows are over-threshold because a missing percent
  denominator must not hide spend outside the comparison budget.

## Boundaries

- No original budget mutation.
- No superseding budget write.
- No client or carrier submission authorization.
- No billing connector read or write.
- No SQLite write or Lake admission.
- No profile, template, carrier guideline, or learning-loop mutation.
- No canonical event, route, taxonomy, or schema promotion from intake.

## Owning-Repos Still Needed

- Orchestrator must own future real billing-read contracts, budget submission
  state, carrier response capture, human pauses, and evidence packet assembly.
- Exception Lake runtime must own append-only admission records, SQLite schema,
  record hashes, corrections, and supersession semantics.
- Semantic Substrate must review any canonical schema, event-label, taxonomy, or
  route promotion.
