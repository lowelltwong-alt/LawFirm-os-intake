# TRACE: Class/Collective Missing-Attachment Executable Fixture

Date: 2026-07-04

## Decision

Add a class/collective/PAGA-style missing-attachment executable fixture to the
Labor & Employment synthetic QA ladder.

The fixture is candidate-only and synthetic-only. It expands executable L&E
coverage to 18 source bundles / 19 linked pack cases and closes the
`class_collective_paga_representative:missing_attachment` coverage gap while
keeping amount-budget output blocked.

## Rationale

Class, collective, and representative wage/hour matters are budget-sensitive
because class size, opt-in counts, pay periods, arbitration posture, policy
documents, ESI scope, experts, and settlement administration can dominate the
budget. A cover email that says those materials were attached is not enough.

This fixture proves that when the inbound packet references but does not include
the class list, opt-in roster, payroll export, timekeeping export, arbitration
agreement, or handbook/policy documents, the system:

- inventories the missing attachments as source-state evidence;
- keeps class/collective scope source-bound but unresolved;
- refuses to invent employee counts, pay periods, or arbitration posture;
- maps missing class scope into amount-budget blockers;
- routes the case to follow-up and blocked-driver review before any amount
  budget can be displayed.

## Boundary

- No real client, matter, public-record, privileged, carrier, or private rate
  data.
- No connector, portal, billing, court, Lake, SQLite, matter-opening, conflict
  conclusion, budget submission, docketing, or training write.
- No canonical event class, party-role taxonomy, rate taxonomy, or L&E budget
  taxonomy promotion from this repo.
- Missing attachment placeholders are synthetic evidence fixtures only; they do
  not authorize production ingestion or public-data runtime use.
- Human corrections, future carrier responses, or learning loops remain
  append-only candidate evidence until owner repos promote contracts.

## Evidence

- Source bundle:
  `examples/synthetic/labor-employment/executable-fixtures/le-class-collective-missing-attachment.source-bundle.json`
- Executable manifest:
  `examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json`
- Fact-binding manifest:
  `examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json`
- Read-only UI fixture refresh:
  `apps/legal-intake-budget/src/fixtures/`
- QA trace:
  `scripts/smoke_demo.sh`

## Acceptance

- Focused L&E chain:
  `python scripts/run_full_pytest.py tests/test_labor_employment_executable_fixtures.py tests/test_labor_employment_executable_coverage.py tests/test_labor_employment_executable_fact_binding.py tests/test_labor_employment_executable_driver_binding.py tests/test_labor_employment_executable_driver_impact.py tests/test_labor_employment_blocked_driver_impact_review.py tests/test_labor_employment_budget_output_expectations.py tests/test_labor_employment_budget_qa_gate.py -q`
- Focused UI/POC chain:
  `python scripts/run_full_pytest.py tests/test_synthetic_qa_bundle.py tests/test_synthetic_confidence_summary.py tests/test_synthetic_qa_blocker_report.py tests/test_synthetic_qa_review_run.py tests/test_synthetic_qa_review_outcomes.py tests/test_ui_review_data_bundle.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`
- Full validation:
  `python scripts/run_validation_suite.py --report-out .lawfirm-os-intake/synthetic-qa-review/quality/validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`

## Follow-Up

Continue filling executable L&E pack gaps in small slices. Next high-leverage
coverage is retaliation/wrongful termination clean and adversarial coverage,
then wage/hour messy-thread or adversarial coverage.
