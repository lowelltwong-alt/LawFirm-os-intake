# TRACE-2026-06-24 - Budget Driver Scaling (Slice 2)

## Situation

Slice 1 (#2) captured `CaseDriverProfile` drivers with provenance but did not feed them
into budget math. The budget total therefore did not move with the counts that drive
litigation cost (depositions, experts, written-discovery rounds, trial days).

## Decision

Give `build_budget_proposal` an optional `case_drivers: CaseDriverProfile | None = None`
parameter and scale count-driven tasks:

- a task may declare `scaling_driver`, `hours_per_unit`, and `expense_per_unit`;
- when a usable (numeric, non-`unknown`) driver value is present, the line uses
  `hours_per_unit * units` and `base_expense + expense_per_unit * units`, records the
  scaling in `calculation_formula`, and adds an assumption naming the driver and its
  provenance;
- otherwise the line falls back to the template's fixed `estimated_hours` / expenses.

Scaling provenance is recorded in the existing `BudgetLine.calculation_formula` and
`assumptions` fields, so **no model or schema change is required**.

## Non-decision

When `case_drivers` is omitted (or `None`), output is byte-for-byte identical to the
prior behavior; a regression test asserts this. This slice does not wire driver
resolution into the demo pipeline (`run_budget` is unchanged), does not modify the
shipped med-mal template or any reviewed gold fixture, and does not change rates,
contingency, approval state, submission authority, conflicts, engagement, or matter
opening. Only `budget.py` changed; one test file was added.

## Authority impact

Local candidate behavior in `LawFirm-os-intake`. Driver taxonomy and any future budget
schema remain `candidate`; promotion runs through Semantic Substrate. Runtime budget
gating remains Orchestrator's.

## Evidence

- `BudgetLine` already exposes `calculation_formula` and `assumptions`, so scaling
  provenance is recorded without new fields.
- `drivers.py` (#2) supplies driver values with provenance; only numeric, non-`unknown`
  drivers are eligible for scaling.
- `build_budget_proposal` is called positionally with three arguments in `workflow.py`
  and tests; the new fourth parameter is optional and defaulted.

## Alternatives rejected

- Apply scaling to the shipped med-mal template now: deferred; that changes the demo
  budget and its reviewed gold, which warrants its own reviewed slice.
- Add scaling fields to `BudgetLine`: rejected for this slice; `calculation_formula`
  and `assumptions` already carry the needed record, avoiding a schema change.
- Invent a number when a driver is unknown: rejected; unknown drivers fall back to the
  template hours, never a fabricated count.

## Risks and rollback

`budget.py` is a hot file; the change is additive and back-compat-guarded by a test that
compares full line output with and without drivers. Rollback removes the parameter,
helper, and scaling branch and deletes one test file.

## Validation

Isolated worktree, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- `python scripts/validate_repo.py` -> repository validation passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> already formatted.
- `python -m pytest -q` -> passed (existing suite unchanged; 4 scaling tests added).
- `python scripts/export_schemas.py` -> unchanged schema set still exports.
- `bash scripts/smoke_demo.sh` -> passed; demo total unchanged (drivers not wired into
  `run_budget`).

## Human gates

Human confirmation still precedes budget generation. The budget remains
`proposed_for_human_review` and `not_authorized_for_client_submission=true`. Conflicts
clearance, engagement authorization, and matter opening remain separate blockers.
