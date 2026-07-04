# TRACE 2026-07-04: L&E Wage/Hour Adversarial Executable Fixture

## Decision

Add a synthetic-only executable fixture for `wage_hour_flsa_state:adversarial` and require the QA ladder to block amount-budget output when source text injects workflow commands, leaked rates, invented employee counts, and invented pay-period assumptions while claimant, employer, and authorized rate/guideline evidence are missing.

## Why

Wage/hour budgets are especially vulnerable to false precision because employee count, pay periods, payroll exports, timekeeping exports, and rate assumptions directly drive discovery, expert, vendor, and phase-budget math. A source can contain plausible-looking numbers while also saying those numbers are invented or unauthorized.

This fixture makes that failure mode executable. The system must preserve the source-bound text, flag prompt injection and prohibited transition attempts, treat invented volume as an unresolved driver, and block amount budgets until party identities and authorized guideline/rate evidence are resolved.

## Boundary

- Source bundle is synthetic and candidate-only.
- Leaked rates are not authorized rates, approved carrier rates, benchmark cells, rate schedules, or guideline sources.
- Invented employee counts and pay-period assumptions are not payroll or timekeeping evidence.
- Missing claimant identity, employer identity, and carrier guideline/rate source facts block amount-budget output.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-wage-hour-adversarial.source-bundle.json`.
- Linked the executable fixture to `le-wage-hour-adversarial.v0_1`, completing wage/hour executable coverage across clean, messy-thread, missing-attachment, and adversarial variants.
- Added fact bindings for missing claimant identity, missing employer identity, source-present claim family, adversarial invented wage/hour volume, and missing authorized guideline/rate evidence.
- Updated fixture, coverage, fact-binding, driver-binding, impact, blocked-review, budget-output, QA-gate, smoke, and UI contract tests.
- Updated read-only UI proof fixtures to show 23 executable fixtures, 24 covered pack cases, 8 remaining missing executable cases, and 12 blocked amount-budget cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-wage-adversarial\full-run --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py -q`
- `python scripts\run_full_pytest.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
- `python scripts\run_validation_suite.py --report-out .lawfirm-os-intake\synthetic-qa-review\quality\validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`
