# TRACE 2026-07-04: L&E Restrictive Covenant Clean Executable Fixture

## Decision

Add a synthetic-only executable fixture for `restrictive_covenant_trade_secret:clean` and require the QA ladder to allow only candidate range budgeting after review when source evidence includes agreement terms, emergency injunction timing, damages categories, and ESI/device scope while forensic vendor and expert needs remain unapproved.

## Why

Restrictive covenant and trade-secret matters can distort early budgets quickly: emergency injunction posture compresses staffing timelines, agreement language drives pleading and motion assumptions, and device or ESI scope can create forensic/vendor expense pressure before facts are confirmed.

This fixture makes that high-leverage nonblocking path executable. The system should recognize that clean source coverage improves budget-driver visibility, but it must still keep every budget output candidate-only, source-bound, and pending human driver review.

## Boundary

- Source bundle is synthetic and candidate-only.
- Emergency injunction dates are timeline candidates, not docketing or filing instructions.
- Employment-agreement excerpts are source evidence, not enforceability conclusions.
- Device inventory, laptop logs, email export logs, CRM logs, and cloud-drive scope remain ESI candidates.
- Forensic vendor mentions are not vendor approval, expert approval, or expense approval.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-restrictive-covenant-clean.source-bundle.json`.
- Linked the executable fixture to `le-restrictive-covenant-clean.v0_1`, moving restrictive-covenant executable coverage from one to two variants.
- Added fact bindings for forum/injunction posture, employment timeline, damages exposure, policy/contract documents, ESI sources, and expert/vendor needs.
- Added the clean restrictive-covenant case to the reviewed nonblocking driver-impact replay spec.
- Updated fixture, coverage, fact-binding, driver-binding, impact, blocked-review, budget-output, QA-gate, smoke, and UI contract tests.
- Updated read-only UI proof fixtures to show 24 executable fixtures, 25 covered pack cases, 7 remaining missing executable cases, 12 reviewed nonblocking cases, and 8 candidate range-after-review cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-restrictive-clean\full-run-3 --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py -q`
- `python scripts\run_full_pytest.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
