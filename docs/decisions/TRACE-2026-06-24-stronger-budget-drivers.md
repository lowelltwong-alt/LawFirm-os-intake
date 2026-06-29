# TRACE: Stronger Budget Drivers

## Context

The roadmap called for severity, venue, liability, coverage, and guideline/cap handling after the first scenario-set slice. The existing budget builder applied count drivers, but intensity, coverage, and guideline signals were either defaults or unknowns with no visible effect surface.

## Decision

Add local candidate budget-driver effects and guideline flags.

- Severity, liability, and venue can apply bounded synthetic intensity multipliers by phase.
- Cumulative task multipliers are capped by `config/budget-driver-policy.yaml`.
- Coverage posture is surfaced as a boundary or unknown driver and is not blended into defense-fee math.
- Synthetic role-rate, phase-budget, and total-budget caps produce `BudgetGuidelineFlag` records.
- Guideline flags never rewrite hours, rates, expenses, or totals.
- Profile defaults may affect synthetic calculations, but every default-driven effect says it is a default and preserves `default_used_as_observed_fact=false`.

## Authority Boundary

This remains local candidate behavior in `LawFirm-os-intake`. It does not promote driver taxonomy, multiplier policy, guideline policy, UTBMS mapping, budget schema, route IDs, event classes, or workflow authority to canon. It does not ingest real guidelines, use negotiated rates, clear conflicts, authorize engagement, open a matter, docket deadlines, bill, submit a budget, call providers, write externally, or admit records to the Exception Lake.

## Validation

- Added deterministic tests for default-driver visibility, no default-as-observed-fact, unknown coverage posture, human-confirmed severity counterfactuals, and guideline flags that do not rewrite rates.
- Updated UTBMS budget tests for count scaling followed by intensity adjustment.
- Focused verification passed:
  - `python -m ruff format src tests scripts`
  - `python -m ruff check src tests scripts`
  - `python -m pytest tests/test_budget_drivers.py tests/test_budget_driver_scaling.py tests/test_budget_stronger_drivers.py tests/test_utbms_budget.py tests/test_budget_scenarios.py tests/test_budget_gate_and_math.py tests/test_budget_support_items.py tests/test_review_package.py tests/test_north_star_demo.py -q`

## Residual Risk

The multiplier and cap values are synthetic policy examples. A future promotion package must move any canonical driver taxonomy, guideline handling, cap semantics, and runtime approval routing to the owning LawFirm OS repos before production use.
