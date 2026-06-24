# TRACE: Budget Scenario Set

## Context

The roadmap called for the budget proposal to stop looking like one falsely precise number and instead expose early, standard, and through-trial branches. The existing renderer, safety gates, review forms, and budget-form mapping code all consumed `BudgetProposal`, so the change needed to preserve the legacy proposal surface while adding the comparison artifact.

## Decision

Embed a local candidate `BudgetScenarioSet` in `BudgetProposal`.

- `early_resolution` truncates through `L200`.
- `standard` truncates through `L300`.
- `through_trial` truncates through `L400`.
- The proposal compatibility fields (`lines`, subtotal fields, calculation report, and total) map to `standard`.
- Priced scenarios assert monotonic total order; hours-only scenarios assert monotonic hours.
- Scenario branches carry included phases, included UTBMS code candidates, totals, and min/max ranges.

## Authority Boundary

This remains local candidate behavior in `LawFirm-os-intake`. It does not promote scenario vocabulary, UTBMS mappings, budget schema, driver taxonomy, route IDs, event classes, or workflow authority to canon. It does not clear conflicts, authorize engagement, open a matter, docket deadlines, bill, submit a budget, call providers, use real data, write externally, or admit records to the Exception Lake.

## Validation

- Added deterministic tests for scenario IDs, UTBMS cutoffs, monotonic totals, standard back-compat, trial-only codes, and hours-only monotonicity.
- Updated review package tests from `baseline` to `standard`.
- Updated UTBMS tests so `L450` appears in the through-trial branch, not the default standard proposal.
- Focused verification passed:
  - `python -m ruff format src tests scripts`
  - `python -m ruff check src tests scripts`
  - `python -m pytest tests/test_budget_scenarios.py tests/test_budget_gate_and_math.py tests/test_budget_driver_scaling.py tests/test_utbms_budget.py tests/test_budget_form.py tests/test_review_package.py tests/test_north_star_demo.py -q`

## Residual Risk

Scenario cutoffs are still local candidate policy. Future work should add stronger budget drivers, guideline/cap handling, a second matter family, and cross-repo promotion proposals before treating the scenario vocabulary as a platform contract.
