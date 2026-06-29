# TRACE: Budget Fixture-Binding Handoff

## Decision

Add `build-budget-fixture-binding-handoff`, a local candidate-only command that
turns a `budget_fixture_binding_candidate_report.json` into a human fixture-
update handoff report.

## Why

The calibration corpus chain already produces reviewed replay outcomes and
fixture-binding candidates. The missing step was a narrow handoff artifact that
tells reviewers which approved synthetic replay outputs are ready for a separate
fixture-update PR and which candidates remain blocked. Without this handoff, a
fixture edit could be mistaken for automatic learning or silently bundled into a
larger change.

## Implementation

- Add `BudgetFixtureBindingHandoffItem` and
  `BudgetFixtureBindingHandoffReport` local candidate schemas.
- Add `src/lawfirm_os_intake/budget_fixture_binding_handoff.py`.
- Add CLI command `build-budget-fixture-binding-handoff`.
- Export schemas for the handoff item and report.
- Add focused tests for ready, blocked, CLI, and persisted JSONL behavior.

## Boundary

- Does not update source fixtures or reviewed gold.
- Does not create a PR.
- Does not apply calibration or learning.
- Does not mutate profiles, templates, budgets, or carrier guidelines.
- Does not write Lake or SQLite records.
- Does not submit budgets, open matters, or perform external writes.

## Acceptance Checks

- Ready candidates require approved output refs and target fixture refs.
- Blocked fixture-binding candidates remain blocked in the handoff.
- Each handoff item includes why-notes, recommended owner actions, red-team
  notes, and required next gates.
- Report-level flags preserve `fixture_update_authorized=false`,
  `fixture_update_pr_created=false`, `fixture_files_mutated=false`,
  `fixture_binding_applied=false`, `lake_write_performed=false`,
  `sqlite_write_performed=false`, and `silent_learning_performed=false`.
