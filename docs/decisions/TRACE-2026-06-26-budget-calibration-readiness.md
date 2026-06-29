# TRACE: Budget Calibration Readiness Audit

## Decision

Add `audit-budget-calibration-readiness`, a local candidate-only command that
verifies the synthetic budget calibration chain before any manual fixture-update
review.

## Why

The calibration lane now has corpus audit, replay planning, replay execution,
human replay review, append-only outcome recording, fixture-binding candidates,
and fixture-binding handoff packaging. The missing proof was a single report
that checks those artifacts line up by ID and preserve no-mutation boundaries
before a reviewer considers a separate fixture-update PR.

## Implementation

- Add `BudgetCalibrationReadinessCheck` and
  `BudgetCalibrationReadinessReport` local candidate schemas.
- Add `src/lawfirm_os_intake/budget_calibration_readiness.py`.
- Add CLI command `audit-budget-calibration-readiness`.
- Export schemas for the readiness check and report.
- Add focused tests for ready, blocked, CLI, and persisted report behavior.

## Boundary

- Does not update fixtures or reviewed gold.
- Does not create a PR.
- Does not apply calibration or learning.
- Does not mutate profiles, templates, budgets, or carrier guidelines.
- Does not write Lake or SQLite records.
- Does not submit budgets, open matters, or perform external writes.

## Acceptance Checks

- Corpus report is synthetic-ready with eligible artifacts and no blocked
  artifacts.
- Replay plan, execution report, review packet, review outcome, fixture-binding
  candidate report, and fixture-binding handoff report line up by ID.
- Review outcome approves fixture binding and carries approved output refs.
- Handoff is ready for human fixture-update review and has no blocked items.
- Required next gates include human fixture update review, separate fixture
  update PR if accepted, append-only fixture update record, reviewed learning
  gate, shadow eval, owning-repo review, and no silent mutation.
- Report-level flags preserve `fixture_update_authorized=false`,
  `fixture_update_pr_created=false`, `fixture_files_mutated=false`,
  `fixture_binding_applied=false`, `calibration_applied=false`,
  `lake_write_performed=false`, `sqlite_write_performed=false`, and
  `silent_learning_performed=false`.
