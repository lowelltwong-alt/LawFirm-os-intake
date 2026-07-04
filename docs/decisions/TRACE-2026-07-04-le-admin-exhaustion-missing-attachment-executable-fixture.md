# TRACE 2026-07-04: L&E Admin Exhaustion Missing-Attachment Executable Fixture

## Decision

Add a synthetic-only executable fixture for `administrative_exhaustion_agency_record:missing_attachment` and require the QA ladder to block amount-budget output when the filing/receipt/deadline chronology is missing.

## Why

Labor and employment intake packets can identify a plausible discrimination or retaliation matter while omitting the agency charge, right-to-sue letter, and date basis needed to reason about posture, deadlines, early motion work, and budget stage. This is especially risky because a cover email may mention a right-to-sue deadline, but the system must not docket, open a matter, or price phases from attachment names or sender summary alone.

This fixture makes that failure mode executable and visible in the read-only UI proof artifacts.

## Boundary

- Source bundle is synthetic and candidate-only.
- Right-to-sue and complaint-deadline references are deadline candidates only; no docketing is authorized.
- Missing agency and forum files are source-bound review gaps.
- Missing filing date, right-to-sue receipt date, and complaint-deadline basis are the critical amount-budget blocker under the current candidate fact policy.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-admin-exhaustion-missing-attachment.source-bundle.json`.
- Linked the executable fixture to `le-admin-exhaustion-missing-attachment.v0_1`.
- Added fact bindings for missing agency/right-to-sue evidence, missing filing/receipt/deadline timeline evidence, and missing forum/removal/arbitration notes.
- Extended fixture, coverage, fact-binding, driver-binding, impact, blocked-review, budget-output, QA-gate, smoke, and UI contract tests.
- Refreshed read-only UI proof fixtures so the dashboard shows 21 executable fixtures, 22 covered pack cases, 10 remaining missing executable cases, and 11 blocked amount-budget cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-admin-missing\full-run --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python -m lawfirm_os_intake build-poc-qa-triage-report --ui-manifest apps\legal-intake-budget\src\fixtures\demo-run-manifest.json --synthetic-confidence-summary apps\legal-intake-budget\src\fixtures\demo-synthetic-confidence-summary-report.json --synthetic-qa-review-run-report apps\legal-intake-budget\src\fixtures\demo-synthetic-qa-review-run-report.json --synthetic-qa-blocker-report apps\legal-intake-budget\src\fixtures\demo-synthetic-qa-blocker-report.json --ui-review-data-bundle apps\legal-intake-budget\src\fixtures\demo-ui-review-data-bundle.json --matter-linking-preflight apps\legal-intake-budget\src\fixtures\demo-matter-linking-preflight-report.json --labor-employment-qa-matrix apps\legal-intake-budget\src\fixtures\demo-labor-employment-qa-matrix-report.json --blocked-driver-impact-review apps\legal-intake-budget\src\fixtures\demo-labor-employment-blocked-driver-impact-review-report.json --budget-output-expectations apps\legal-intake-budget\src\fixtures\demo-labor-employment-budget-output-expectations-report.json --budget-qa-gate apps\legal-intake-budget\src\fixtures\demo-labor-employment-budget-qa-gate-report.json --validation-suite-evidence apps\legal-intake-budget\src\fixtures\demo-validation-suite-evidence-report.json --out-dir .lawfirm-os-intake\tmp\le-admin-missing\poc-triage --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
- `python scripts\run_validation_suite.py --report-out .lawfirm-os-intake\synthetic-qa-review\quality\validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`
