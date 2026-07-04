# TRACE 2026-07-04: L&E Retaliation Missing-Attachment Executable Fixture

## Decision

Add a synthetic-only executable fixture for `retaliation_wrongful_termination:missing_attachment` and require the budget QA ladder to block amount-budget output when carrier assignment, guideline/rate, and key policy documents are missing.

## Why

The L&E budget proof needs cases where the intake packet contains enough narrative to identify a likely claim family, but not enough authority or pricing context to produce an amount budget. Retaliation and wrongful-termination intakes often include timeline signals while omitting documents that materially control budget scope: discipline files, termination letters, employee handbooks, carrier assignments, billing guidelines, and approved rate schedules.

This fixture makes that failure mode executable instead of merely described in the roadmap.

## Boundary

- Source bundle is synthetic and candidate-only.
- The mailbox name `insurance-notice@synthetic-mailbox.example` is sender context only; it is not evidence of insurer, payer, instructing source, represented client, guideline authority, or approved rates.
- Missing attachments are classified as source gaps and candidate exception labels, not facts to infer away.
- Timeline references are source-present review candidates, not docketing or deadline instructions.
- Budget output remains `blocked_amount_budget` until critical facts are collected or confirmed unavailable.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-retaliation-wrongful-termination-missing-attachment.source-bundle.json`.
- Linked the executable fixture to `le-retaliation-wrongful-termination-missing-attachment.v0_1`.
- Added fact bindings for unresolved carrier/client/payer posture, missing carrier guideline and approved rates, missing policy/handbook/discipline documents, and a source-present timeline that still requires confirmation.
- Extended driver binding, driver impact, blocked-review, budget-output, QA-gate, smoke, and UI contract tests for the new blocked case.
- Refreshed read-only UI proof fixtures so the dashboard shows 20 executable fixtures, 21 covered pack cases, 11 remaining missing executable cases, and 10 blocked amount-budget cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-retaliation-missing\full-run --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python -m lawfirm_os_intake build-poc-qa-triage-report --ui-manifest apps\legal-intake-budget\src\fixtures\demo-run-manifest.json --synthetic-confidence-summary apps\legal-intake-budget\src\fixtures\demo-synthetic-confidence-summary-report.json --synthetic-qa-review-run-report apps\legal-intake-budget\src\fixtures\demo-synthetic-qa-review-run-report.json --synthetic-qa-blocker-report apps\legal-intake-budget\src\fixtures\demo-synthetic-qa-blocker-report.json --ui-review-data-bundle apps\legal-intake-budget\src\fixtures\demo-ui-review-data-bundle.json --matter-linking-preflight apps\legal-intake-budget\src\fixtures\demo-matter-linking-preflight-report.json --labor-employment-qa-matrix apps\legal-intake-budget\src\fixtures\demo-labor-employment-qa-matrix-report.json --blocked-driver-impact-review apps\legal-intake-budget\src\fixtures\demo-labor-employment-blocked-driver-impact-review-report.json --budget-output-expectations apps\legal-intake-budget\src\fixtures\demo-labor-employment-budget-output-expectations-report.json --budget-qa-gate apps\legal-intake-budget\src\fixtures\demo-labor-employment-budget-qa-gate-report.json --validation-suite-evidence apps\legal-intake-budget\src\fixtures\demo-validation-suite-evidence-report.json --out-dir .lawfirm-os-intake\tmp\le-retaliation-missing\poc-triage --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
- `python scripts\run_validation_suite.py --report-out .lawfirm-os-intake\synthetic-qa-review\quality\validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`
