# TRACE: L&E Class/Collective Executable Fixtures

## Context

The labor and employment synthetic QA chain had coverage for several ordinary
and EPLI intake patterns, but the executable set did not yet include a
class/collective wage-hour pattern. That left a high-impact budget driver gap:
the same inbound packet can be budgetable as a broad range, hours-only, or
blocked depending on claimant count, class/collective/PAGA posture, arbitration,
forum, employee/pay-period volume, ESI scope, expert needs, and carrier
guideline pressure.

## Decision

Add two candidate-only executable source bundles for L&E class/collective
wage-hour intake:

- a clean assignment packet with source-present but unconfirmed
  class/collective, arbitration/forum, volume, exposure, and expert/vendor
  signals;
- a messy correspondence thread with duplicate text and unresolved ESI,
  class/collective, volume, expert/vendor, and forum/arbitration signals.

Bind both fixtures into the executable manifest, budget fact bindings, reviewed
driver-impact gold, budget-output expectations, and read-only UI demo artifacts.
The expected budget treatment remains review-gated: hours-only, broad range, or
candidate range after review. No fixture authorizes a client/carrier budget,
matter opening, conflict conclusion, or Lake write.

## Invariant Impact

- The executable fixture count increases from 12 to 14.
- Reviewed nonblocking driver-impact cases increase from 6 to 8.
- Executable pack coverage increases to 15 covered pack cases with 17 remaining
  missing executable pack cases.
- Fact bindings increase to 42 total, including 18 critical fact bindings.
- Budget-impact items increase to 61, with 19 critical review-only impacts.
- UI blocker rows increase to 21 pending-review rows.

## Boundary

This is local synthetic QA evidence only. It does not:

- ingest real cases or public payload text;
- classify or confirm representation posture, matter family, or party roles;
- create approved budgets or submit budget forms;
- clear conflicts, open matters, docket deadlines, or write to a carrier portal;
- write Exception Lake, SQLite, billing, email, or document-management records;
- promote L&E fact states, role labels, budget drivers, or event labels to
  Semantic Substrate canon;
- silently learn from refreshed fixture outcomes.

## Verification

- `python scripts/run_full_pytest.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`
- `python scripts/run_full_pytest.py tests/test_labor_employment_executable_fixtures.py tests/test_labor_employment_executable_coverage.py tests/test_labor_employment_executable_fact_binding.py tests/test_labor_employment_executable_driver_binding.py tests/test_labor_employment_executable_driver_impact.py tests/test_labor_employment_driver_impact_review.py tests/test_labor_employment_blocked_driver_impact_review.py tests/test_labor_employment_budget_output_expectations.py -q`
- `python scripts/run_full_pytest.py -q`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `npm run build` from `apps/legal-intake-budget`
- `bash scripts/smoke_demo.sh`
- `python scripts/validate_repo.py`
- `python scripts/export_schemas.py`

## Remaining Work

The goal is not complete until the fixture matrix covers the remaining
labor-employment pack cases, synthetic gold review is deeper than starter
review, and the frontend can inspect all QA/blocker/review artifacts without
manual fixture refreshes.
