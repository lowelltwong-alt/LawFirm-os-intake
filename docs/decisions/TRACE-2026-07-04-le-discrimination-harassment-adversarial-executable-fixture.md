# TRACE 2026-07-04: Discrimination/Harassment Adversarial Executable Fixture

## Decision

Add `le-discrimination-harassment-adversarial.executable.v0_1` as a synthetic-only
labor/employment fixture that exercises prompt-injection, missing party identity,
missing prospective-client posture, leaked-rate text, and prohibited-transition
attempts in a discrimination/harassment context.

## Rationale

The L&E executable coverage ladder still had no adversarial discrimination and
harassment case. This fixture closes that family/variant gap while preserving
the key budget rule: source-present claim, damages, and ESI terms may create
review-only driver signals, but missing claimant, employer, and client/payer
posture facts must block amount-budget output.

## Expected Deterministic Behavior

- Preflight emits prompt-injection and prohibited-transition candidate labels.
- The source remains synthetic-only and untrusted.
- Claim, damages, and ESI terms remain source-bound review candidates.
- Claimant, employer, and prospective-client/payer posture remain missing
  critical budget facts.
- Budget output stays `blocked_amount_budget`.
- Blocked review identifies three blocker facts and three amount-budget block
  impacts.
- UI fixtures display the blocked state from local JSON only.

## Prohibited Outcomes

- No conflict conclusion.
- No matter opening.
- No deadline docketing.
- No budget submission or carrier/client export.
- No accepted leaked rates, benchmark cells, or approved rate schedule.
- No Lake, SQLite, connector, external write, or silent-learning side effect.

## Validation

Focused L&E and UI contract tests passed after adding the fixture:

```text
python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py -q
54 passed
```
