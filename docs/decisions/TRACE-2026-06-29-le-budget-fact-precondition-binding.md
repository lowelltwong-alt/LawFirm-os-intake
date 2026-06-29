# TRACE-2026-06-29 - L&E Budget Fact Precondition Binding

## Context

The L&E budget fact audit already identified source-bound budget drivers,
human-review questions, and critical fact gaps. The budget path still needed to
consume that report as a precondition artifact instead of leaving it as a
standalone review report.

## Decision

Add optional `build-budget --labor-employment-budget-fact-report`.

When supplied:

- critical L&E budget fact gaps fail `budget_precondition_report.json` with
  `blocked_state=labor_employment_budget_facts_blocked`;
- the blocked path emits only the existing blocked precondition artifacts and a
  dry-run Exception Lake candidate;
- successful non-critical reports add supported proposal unknowns with
  `source_kind=labor_employment_budget_fact_report`;
- the review package and manifest show the report ref, readiness state,
  treatment, critical-gap count, and required human questions.

## Red-Team Notes

- This is an explicit artifact input, not automatic public-data ingestion.
- Non-critical L&E gaps do not rewrite hours, rates, expenses, totals, or
  carrier-compliant projections.
- Intake still writes no Lake/SQLite records, performs no connector work, and
  authorizes no budget submission, matter opening, conflict conclusion, or
  learning update.
- The source remains candidate-only until owner review in the appropriate
  platform repos.

## Validation

- `python scripts/run_full_pytest.py tests/test_labor_employment_budget_gate.py tests/test_validation_runtime_policy.py -q`
  - 13 passed.
- `python scripts/run_validation_suite.py`
  - repository validation passed.
  - exported 228 schemas.
  - ruff check passed.
  - ruff format check passed.
  - full pytest passed: 382 passed in 328.01s.
  - smoke demo completed with final boundary `blocked_pending_conflicts_and_engagement`.
  - final repository validation passed.
