# TRACE 2026-07-04: L&E Wage/Hour Messy-Thread Executable Fixture

## Decision

Add a synthetic-only executable fixture for `wage_hour_flsa_state:messy_thread` and require the QA ladder to preserve conflicting employee and pay-period counts as alternatives instead of averaging, silently selecting, or double-counting duplicated correspondence.

## Why

Wage/hour budgets are highly sensitive to putative class or collective scope, employee count, pay-period volume, timekeeping/payroll systems, custodians, and expert/vendor needs. A realistic intake may include a current clean summary, quoted history with different numbers, and a duplicated correspondence dump from an adjuster or client contact.

This fixture makes that uncertainty executable. The system may produce a range or hours-only candidate after review, but it must not treat the 18-employee and 42-employee counts as one observed fact or inflate volume because the same text arrived twice.

## Boundary

- Source bundle is synthetic and candidate-only.
- Duplicate correspondence is evidence of intake noise, not extra budget volume.
- The 18-employee/52-pay-period and 42-employee/78-pay-period figures remain source-bound alternatives until confirmed.
- Class or collective scope, ESI sources, and expert/vendor needs require review before amount confidence can tighten.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-wage-hour-messy-thread.source-bundle.json`.
- Linked the executable fixture to `le-wage-hour-messy-thread.v0_1`.
- Added fact bindings for class/collective scope, wage/hour volume, ESI sources, and expert/vendor needs.
- Included the case in the reviewed nonblocking driver-impact replay slice as `range_or_hours_only_pending_review`.
- Extended fixture, coverage, fact-binding, driver-binding, impact, driver-review, blocked-review, budget-output, QA-gate, smoke, and UI contract tests.
- Updated proof expectations to 22 executable fixtures, 23 covered pack cases, 9 remaining missing executable cases, and 11 reviewed nonblocking cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-wage-messy\full-run --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
- `python scripts\run_validation_suite.py --report-out .lawfirm-os-intake\synthetic-qa-review\quality\validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`
