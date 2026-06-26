# TRACE: Budget Event Lake Review Bundle

## Decision

Add a run-specific candidate bundle for budget-event Exception Lake owner review.

## Why

The repo now has three append-only local ledgers:

- human budget changes;
- actual-cost variance;
- carrier rejection decisions, appeals, recoveries, and write-downs.

Those ledgers are useful only if they can be handed to the Exception Lake runtime
with proof that the artifacts are complete, hash-addressed, internally
consistent, and still no-write. A design-time admission proposal is not enough;
reviewers need a concrete bundle tied to the generated ledger files.

## Scope

- Add `BudgetLakeEvidenceArtifact`, `BudgetLakeAdmissionBundleCheck`, and
  `BudgetLakeAdmissionBundleReport` local candidate schemas.
- Add `build-budget-event-lake-bundle`.
- Write `budget_event_lake_admission_bundle_report.json` and
  `budget_event_lake_admission_bundle.md`.
- Hash each provided ledger report and JSONL artifact.
- Verify JSONL row counts and event IDs match report events.
- Require provided ledgers to agree on `budget_proposal_id` and
  `preflight_packet_id`.
- Map events to candidate Lake record families for owner review.
- Block if a ledger claims Lake, SQLite, billing, submission, mutation, or silent
  learning side effects.

## Boundaries

This slice does not admit Lake records, write SQLite, assign canonical event
classes, create record hashes, create Lake migrations, submit appeals or budgets,
read billing, write billing, mutate profiles/templates/budgets/guidelines, write
sibling repos, or apply learning. Exception Lake remains the owner of admission,
append-only storage, record hashes, correction/supersession, and any future
SQLite schema.

## Red Team Notes

- A bundle that only lists paths is weak; it must hash artifacts and verify row
  counts.
- A bundle that accepts mismatched budget IDs could mix evidence from unrelated
  matters.
- A bundle that ignores within-threshold or missing-actuals rows would be unable
  to prove complete comparison coverage.
- A bundle that passes through side-effect flags without checking them could
  accidentally normalize an intake-owned Lake write.
- Passing status must mean owner-review readiness only, not admission.

## Verification

- Focused tests generate all three synthetic ledgers and prove the bundle is
  ready only when artifacts are present, row/event IDs match, budget/preflight
  IDs agree, and no-write flags hold.
- Negative tests cover missing JSONL artifacts and mismatched budget IDs.
- Full validation should run repo validation, schema export, lint, format check,
  full pytest, and the smoke demo.
