# TRACE 2026-07-09: L&E Class/Collective Replay Input Preflight Gap Matrix

## Status

Accepted as a local candidate-only intake slice in progress.

## Context

Fable's L&E synthetic corpus roadmap and class/collective/PAGA budget-template
kernel identify class/collective/PAGA matters as the highest nonlinear budget
risk. The canonical intake clone already has L&E replay-readiness, replay
execution, builder-binding, confidence-status, review UI, and learning-gate
surfaces. Cursor started a Phase 1 continuation on the replay-input pack by
adding class/collective actuals-variance inputs and making the report show the
next missing replay inputs before builders run.

## Decision

Keep this as a preflight-only improvement:

- register synthetic class/collective actuals-variance replay inputs for
  `le-learning-class-collective-clean.v0_1`;
- add a report-level preflight gap matrix that lists missing or invalid replay
  slots without running builders;
- prioritize next actions so builder inputs appear before complement reports and
  one-of reviewed signals;
- refresh the affected read-only demo fixtures and manifest hashes.

## Boundary

This slice does not run replay builders, create runtime artifacts, submit or
approve budgets, write to the Exception Lake or SQLite, mutate profiles, create
carrier submissions, open matters, clear conflicts, promote learning, or use
real client/matter/carrier/privileged data.

All added replay inputs are synthetic, candidate-only, and local evidence for
human review. The budget proposal remains a proposal, not an approved or
submitted budget. The actuals source remains synthetic fixture data, not billing
system data.

## Tests

Focused validation:

```text
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py -q
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
```

Expected outcome:

- focused replay-input-pack tests pass;
- confidence-status tests pass;
- UI and Rust fixture hash contract tests pass;
- generated input-pack report remains
  `labor_employment_budget_replay_input_pack_partially_ready_for_review`;
- runtime, budget submission, Lake write, SQLite write, external write, and
  silent-learning flags remain false.

Actual validation results recorded 2026-07-09/2026-07-10:

```text
$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py -q
25 passed

$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
2 passed

$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
45 passed

$env:PYTHONPATH='src'; python scripts\validate_repo.py
repository validation passed
```

## Follow-Ups

- Keep Phase 1 focused on replay-input preflight evidence and review visibility.
- Do not implement the actual builders from this slice.
- Use the saved Fable execution task packets before assigning the remaining
  learning-vs-leakage or DAD-style asset work to subagents.
