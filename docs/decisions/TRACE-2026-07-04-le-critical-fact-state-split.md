# TRACE: L&E Critical Fact State Split

## Context

The L&E executable budget QA chain treated every bound critical fact as an
amount-budget blocker. That made truly missing source evidence look the same as
source-present but unconfirmed role or guideline evidence. The issue showed up
most clearly in EPLI assignment fixtures where carrier, payer, TPA, insured,
represented-client, claimant, and guideline signals are present in source text
but still require human confirmation before pricing.

## Decision

Add a candidate-only fact-resolution state to executable L&E budget fact
bindings and thread it through driver binding, driver impact, blocked-driver
review, budget-output expectations, and the read-only UI fixtures.

The new states separate:

- `missing_critical_fact`, which keeps amount-budget output blocked;
- `source_present_unresolved_critical_driver`, which keeps amount-budget output
  blocked when a source-present uncertainty is itself budget-determinative;
- `source_present_needs_confirmation`, which creates review/range/rate pressure
  without being classified as missing evidence.

The EPLI clean and messy-thread fixtures now bind critical carrier/client/rate
context signals as source-present confirmation facts while remaining nonblocking
candidate budget-review packets. Missing guideline/rate, timeline, ESI, and
other true source gaps still block amount-budget output.

## Boundary

This is local synthetic QA evidence only. It does not:

- confirm party roles or representation posture;
- clear conflicts or authorize engagement;
- compute, approve, submit, or narrow a client/carrier budget;
- write Exception Lake or SQLite records;
- promote L&E fact states, role states, event labels, or budget taxonomy canon;
- learn silently from the refreshed fixture outcomes.

## Verification

- `python scripts/run_full_pytest.py tests/test_labor_employment_executable_fact_binding.py tests/test_labor_employment_executable_driver_binding.py tests/test_labor_employment_executable_driver_impact.py tests/test_labor_employment_blocked_driver_impact_review.py tests/test_labor_employment_budget_output_expectations.py -q`
- `python scripts/run_full_pytest.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`

