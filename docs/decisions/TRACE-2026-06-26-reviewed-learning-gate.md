# TRACE 2026-06-26 Reviewed Learning Gate

## Decision

Add a local candidate-only reviewed learning gate that aggregates carrier
rejection learning proposals, human budget revision deltas, and budget actual
variance drivers into one report. The gate does not learn by itself; it proves
which candidate learning loops need human-reviewed outcome evidence,
append-only evidence records, synthetic fixture updates, shadow evals, and
owning-repo review before promotion.

## Why

Carrier rejections, appeal results, human budget changes, and actual-cost
variance are all useful learning signals, but combining them without a gate would
make silent profile/template/guideline mutation too easy. A deterministic
aggregate report lets humans see the pressure and next gates while preserving
LawFirm OS authority boundaries.

## Implemented

- `review-learning-gate` command.
- `ReviewedLearningGateReport`, `ReviewedLearningGateCandidate`, and
  `ReviewedLearningGateCheck` candidate schemas.
- Inputs:
  - `carrier_rejection_learning_report.json`;
  - `budget_revision_report.json`;
  - `budget_actual_comparison_report.json`.
- Outputs:
  - `reviewed_learning_gate_report.json`;
  - `reviewed_learning_gate_report.md`;
  - `reviewed_learning_gate_candidates.jsonl`.

## Boundaries

- No profile mutation.
- No template mutation.
- No connector mutation.
- No budget mutation.
- No carrier guideline mutation.
- No Lake or SQLite write.
- No external write.
- No canonical schema, route, event, or taxonomy promotion.
- No silent learning.

## Remaining Owners

- Orchestrator owns future production evidence packets, connector outputs,
  human pauses, appeal submissions, and billing-read contracts.
- Exception Lake owns admitted append-only records, SQLite schema, record hashes,
  and supersession/correction semantics.
- Semantic Substrate owns canonical schemas, event labels, route IDs, and
  promoted taxonomy.
