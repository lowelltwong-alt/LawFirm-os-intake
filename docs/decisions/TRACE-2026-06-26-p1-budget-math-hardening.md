# TRACE 2026-06-26 P1 Budget Math Hardening

## Decision

Implement the P1 budget-math fixes as a local candidate slice: propagate
uncertainty from unknown/profile-default count drivers, select the headline
scenario from confirmed or observed resolution path, compute a labeled expected
total when scenario probabilities are complete, make intensity materially affect
expense-bearing lines under policy, preserve per-task driver effects, filter
actuals comparison by actual resolution scenario, and replace the budget totals
tuple with a named dataclass.

## Why

The budget loop is becoming evidence for human edits, carrier responses, appeals,
actuals comparison, and reviewed learning. The math surface has to separate likely
values from uncertainty, preserve scenario risk, and expose why a number changed.
Otherwise later Lake and learning artifacts would inherit false precision.

## Implemented

- `BudgetLine` now carries `estimated_expenses_min` and
  `estimated_expenses_max`.
- `BudgetScenario` now carries optional `probability`.
- `BudgetScenarioSet` now carries `selected_scenario_basis`, `expected_total`,
  and `expected_total_probability_sum`.
- `CaseDriverProfile` now carries candidate `scenario_policy` and
  `count_driver_range_policy` from `config/budget-driver-policy.yaml`.
- `budget.py` widens hour and expense ranges for unknown/profile-default
  count drivers, keeps human-confirmed count ranges tight, and computes scenario
  expected total only when probabilities sum to 1.
- Confirmed or observed `resolution_path` selects the headline scenario; absent
  resolution path preserves the default `standard` compatibility surface.
- The synthetic intensity policy has a finite cap and can apply to
  expense-bearing lines.
- `_driver_effect_key` includes `task_ids` so two tasks sharing one driver are
  not collapsed.
- Budget actual comparison can filter by `actual_resolution_scenario_id` and
  still flags zero-budget/positive-actual rows as over-threshold.

## Boundaries

- Synthetic-only driver policy and profile data.
- No real rates, real carrier guidelines, billing reads, billing writes, carrier
  submission, SQLite writes, Lake admission, or external writes.
- No conflict clearance, engagement decision, matter opening, or docketing.
- No profile, template, carrier guideline, or learning mutation.
- No canonical scenario, event, route, or budget taxonomy promotion from intake.

## Tests

- Unknown count drivers produce wider ranges than confirmed count drivers.
- Scenario probabilities sum to 1 and produce an expected total.
- Confirmed `through_trial` selects the through-trial scenario and keeps the
  standard scenario as the compatibility reference.
- Trial-day effects survive separately for L440 and L450.
- Expense-bearing intensity changes proposed expense values while carrier caps
  remain projection-only.
- Actuals comparison filters early-resolution actuals against the early scenario
  and flags actual discovery spend as over-threshold when no discovery budget is
  in scope.

## Risks And Follow-Up

Actuals comparison can filter selected proposal lines by a scenario. If a future
runtime needs full non-selected scenario line reconstruction for production
actuals, Orchestrator should carry or request a governed full scenario-line
artifact rather than inferring it from summary totals.

The next PR-sized slice should build the human budget correction and carrier
response learning evidence chain forward from these math surfaces, not silently
mutate profiles from one variance.
