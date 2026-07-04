# TRACE 2026-07-04: Complete L&E Fixture Gap Coverage

## Decision

Close the remaining labor/employment executable fixture gaps with synthetic-only
source bundles for:

- `le-retaliation-wrongful-termination-adversarial.executable.v0_1`
- `le-admin-exhaustion-messy-thread.executable.v0_1`
- `le-admin-exhaustion-adversarial.executable.v0_1`

Refresh the local read-only UI fixtures so the app displays complete executable
coverage from generated JSON artifacts.

## Rationale

The confidence ladder needed all declared L&E family variants represented before
budget QA could be treated as a useful POC gate. The missing gaps were important
budget-risk surfaces: retaliation/wrongful-termination prompt injection,
administrative-exhaustion messy thread duplication, and administrative-exhaustion
adversarial deadline/posture ambiguity.

This slice keeps the repo candidate-only. It improves deterministic QA coverage
without authorizing matter opening, conflict conclusions, deadline docketing,
budget submission, Lake writes, SQLite writes, connector writes, or calibration.

## Expected Deterministic Behavior

- Executable fixture coverage reports `complete_executable_coverage`.
- The 31 executable fixtures cover all 32 declared L&E pack cases.
- No L&E family or family variant remains missing.
- Retaliation/wrongful-termination adversarial intake blocks amount-budget output
  when employee, employer, posture, and timeline facts are missing.
- Administrative-exhaustion messy-thread intake remains nonblocking but review
  gated, detects duplicate source material, and keeps deadline candidates
  review-only.
- Administrative-exhaustion adversarial intake blocks amount-budget output when
  claimant, employer, posture, and timeline facts are missing.
- Prompt-injection and prohibited-transition text remains untrusted source text
  and produces only candidate exception labels.
- UI fixtures render the updated local JSON state without external writes.

## Prohibited Outcomes

- No conflict conclusion.
- No matter opening.
- No deadline docketing.
- No budget submission or carrier/client export.
- No accepted leaked rates, benchmark cells, or approved rate schedule.
- No Lake, SQLite, connector, external write, or silent-learning side effect.
- No real case data or public payload ingestion.

## Validation

Generated QA run:

```text
python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\complete-le-fixture-gaps\full-run-3 --repo-root . --generated-at 2026-07-04T00:00:00Z
```

Observed generated state:

```text
status: synthetic_qa_review_run_ready
failed_step_count: 0
executable_fixture_count: 31
pack_case_count: 32
covered_pack_case_count: 32
missing_executable_pack_case_count: 0
coverage_state: complete_executable_coverage
blocked_amount_budget_case_count: 16
reviewed_nonblocking_case_count: 15
candidate_range_after_review_case_count: 10
```

Focused L&E and UI contract tests passed:

```text
python scripts\run_full_pytest.py tests\test_labor_employment_executable_fixtures.py tests\test_labor_employment_executable_coverage.py tests\test_labor_employment_executable_fact_binding.py tests\test_labor_employment_executable_driver_binding.py tests\test_labor_employment_executable_driver_impact.py tests\test_labor_employment_driver_impact_review.py tests\test_labor_employment_blocked_driver_impact_review.py tests\test_labor_employment_budget_output_expectations.py tests\test_labor_employment_budget_qa_gate.py tests\test_ui_foundation_contract.py -q
58 passed
```
