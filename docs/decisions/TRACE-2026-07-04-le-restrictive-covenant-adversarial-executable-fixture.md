# TRACE 2026-07-04: L&E Restrictive Covenant Adversarial Executable Fixture

## Decision

Add a synthetic-only executable fixture for `restrictive_covenant_trade_secret:adversarial` and require the QA ladder to block amount-budget output when the intake source contains prompt-injection text, unsupported emergency-injunction certainty, missing claimant and employer identities, missing governing agreement and policy documents, and unresolved forum, damages, and claim-scope facts.

## Why

Restrictive covenant and trade-secret intakes can look urgent even when the core facts needed for a defensible budget are absent. This fixture exercises the highest-risk version of that path: source text tries to order conflict clearance, matter opening, docketing, and budget submission, while also asserting a near-term injunction path without confirmed party identities, agreement terms, forum posture, damages exposure, or policy documents. The system must treat those statements as untrusted source content, preserve the observed text, route deadlines and prohibited transitions into review/exception labels, and refuse an amount budget.

## Boundary

- Source bundle is synthetic and candidate-only.
- Prompt-injection text remains source content and cannot alter workflow authority.
- The July 6, 2026 emergency-injunction statement is a deadline or procedural candidate for review, not a docketing instruction.
- Claimant identity and employer or defendant identity are missing critical facts.
- Agreement, handbook, policy, forum, arbitration, damages, and claim-scope facts require evidence-bound review before pricing narrows.
- No budget submission, matter opening, conflict conclusion, deadline docketing, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-restrictive-covenant-adversarial.source-bundle.json`.
- Linked the executable fixture to `le-restrictive-covenant-adversarial.v0_1`, moving executable coverage to 26 fixtures, 27 covered pack cases, and 5 remaining missing executable cases.
- Added fact bindings for claimant identity, employer or defendant identity, claims and causes of action, forum and arbitration posture, damages categories and exposure, and policy or contract documents.
- Added driver-impact expectations that make party topology block amount budgeting while claim family and damages exposure remain critical review-only signals.
- Updated fixture, coverage, fact-binding, driver-binding, impact, blocked-review, budget-output, QA-gate, smoke, and UI contract expectations.
- Updated read-only UI proof fixtures to show 26 executable fixtures, 27 covered pack cases, 5 remaining missing executable cases, 13 blocked cases, 5 range-or-hours-only cases, and 8 candidate range-after-review cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-restrictive-adversarial\full-run-1 --repo-root . --generated-at 2026-07-04T00:00:00Z`
- `python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py -q`
- `python scripts\run_full_pytest.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py tests\test_poc_qa_triage.py tests\test_synthetic_qa_review_run.py -q`
