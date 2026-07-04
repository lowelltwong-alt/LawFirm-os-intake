# TRACE 2026-07-04: L&E Restrictive Covenant Messy-Thread Executable Fixture

## Decision

Add a synthetic-only executable fixture for `restrictive_covenant_trade_secret:messy_thread` and require the QA ladder to keep the budget output at `range_or_hours_only_pending_review` when the intake source contains duplicate quoted history, affiliate or joint-employer ambiguity, forum-selection uncertainty, ESI/device scope, and forensic-vendor preapproval pressure.

## Why

Restrictive covenant and trade-secret intakes often arrive as forwarded threads where the same facts appear multiple times, entity roles are blurry, and urgent injunction language can tempt premature budget narrowing. This fixture exercises that path without using real client data: the system must preserve source evidence, detect duplicates and deadline-review risk, keep Northstar Field Systems as an unresolved affiliate or joint-employer candidate, and treat forensic-vendor references as preapproval review rather than expense authority.

## Boundary

- Source bundle is synthetic and candidate-only.
- Duplicate quoted thread text must not inflate device, custodian, vendor, or emergency-injunction scope.
- Northstar Field Systems remains an affiliate or joint-employer candidate, not a confirmed represented client.
- Forum-selection and emergency-injunction references are procedural candidates only; they do not authorize filing, docketing, or scenario selection.
- Forensic vendor mentions are not vendor approval, expert approval, expense approval, or carrier preapproval.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-restrictive-covenant-messy-thread.source-bundle.json`.
- Linked the executable fixture to `le-restrictive-covenant-messy-thread.v0_1`, moving executable coverage to 25 fixtures, 26 covered pack cases, and 6 remaining missing executable cases.
- Added fact bindings for affiliate/joint-employer structure, forum/arbitration posture, ESI sources, expert/vendor needs, and policy/contract documents.
- Added the messy-thread restrictive-covenant case to the reviewed nonblocking driver-impact replay spec, moving that slice to 13 cases.
- Updated fixture, coverage, fact-binding, driver-binding, impact, blocked-review, budget-output, QA-gate, smoke, and UI contract expectations.
- Updated read-only UI proof fixtures to show 25 executable fixtures, 26 covered pack cases, 6 remaining missing executable cases, 13 reviewed nonblocking cases, 5 range-or-hours-only cases, and 8 candidate range-after-review cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-restrictive-messy\full-run-1 --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py -q`
- `python scripts\run_full_pytest.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
