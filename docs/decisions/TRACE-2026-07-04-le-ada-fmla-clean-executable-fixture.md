# TRACE: ADA/FMLA Clean Executable Fixture

Date: 2026-07-04

## Decision

Add a clean ADA/FMLA accommodation and leave executable fixture to the Labor &
Employment synthetic QA ladder.

The fixture is candidate-only and synthetic-only. It increases executable L&E
coverage from 14 fixtures / 15 linked pack cases to 15 fixtures / 16 linked pack
cases while preserving partial corpus coverage as an explicit UI and QA state.

## Rationale

The fixture-family pack already contained `le-ada-fmla-clean.v0_1`, but the
executable manifest only covered ADA/FMLA through a combined missing/messy
thread fixture. That left the budget QA path without a clean ADA/FMLA source
packet that could test source-present but still human-confirmed leave timeline,
policy, deposition, damages, and expert/vendor assumptions.

The new fixture proves that clean source coverage does not authorize an amount
budget. It supports only `candidate_range_budget_after_review`, with medical,
vocational, manager-role, deposition, and vendor assumptions staying review-only.

## Boundary

- No real client, matter, public-record, privileged, or private rate data.
- No connector, portal, billing, court, Lake, SQLite, matter-opening, conflict
  conclusion, budget submission, or training write.
- No canonical taxonomy or schema promotion from this repo.
- Practice-context facts remain separate from source-observed evidence.

## Evidence

- Source bundle:
  `examples/synthetic/labor-employment/executable-fixtures/le-ada-fmla-clean.source-bundle.json`
- Executable manifest:
  `examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json`
- Fact-binding manifest:
  `examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json`
- Reviewed nonblocking replay spec:
  `examples/synthetic/gold/labor-employment-driver-impact-review.json`
- Read-only UI fixture refresh:
  `apps/legal-intake-budget/src/fixtures/`

## Acceptance

- Focused L&E chain:
  `python scripts/run_full_pytest.py tests/test_labor_employment_executable_fixtures.py tests/test_labor_employment_executable_coverage.py tests/test_labor_employment_executable_fact_binding.py tests/test_labor_employment_executable_driver_binding.py tests/test_labor_employment_executable_driver_impact.py tests/test_labor_employment_driver_impact_review.py tests/test_labor_employment_budget_output_expectations.py tests/test_labor_employment_blocked_driver_impact_review.py tests/test_labor_employment_budget_qa_gate.py -q`
- Synthetic QA/UI contract:
  `python scripts/run_full_pytest.py tests/test_synthetic_qa_bundle.py tests/test_synthetic_confidence_summary.py tests/test_synthetic_qa_blocker_report.py tests/test_synthetic_qa_review_run.py tests/test_ui_review_data_bundle.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`

Both focused suites passed after fixture, review-spec, UI fixture, and smoke
expectation updates.

## Follow-Up

Continue filling the remaining executable L&E pack gaps in small slices:
ADA/FMLA adversarial, retaliation clean/missing/adversarial, restrictive
covenant clean/messy/adversarial, administrative exhaustion messy/missing/
adversarial, and EPLI adversarial. Keep each slice source-bound, candidate-only,
and paired with reviewed budget-output expectations before it reaches the UI.
