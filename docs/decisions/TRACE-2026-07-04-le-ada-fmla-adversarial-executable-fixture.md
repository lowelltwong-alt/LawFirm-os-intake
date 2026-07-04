# TRACE: ADA/FMLA Adversarial Executable Fixture

Date: 2026-07-04

## Decision

Add an adversarial ADA/FMLA accommodation and leave executable fixture to the
Labor & Employment synthetic QA ladder.

The fixture is candidate-only and synthetic-only. It expands executable L&E
coverage to 16 source bundles / 17 linked pack cases while keeping the amount
budget blocked when principal party identity, employer identity, and client
posture are missing.

## Rationale

The existing ADA/FMLA fixtures covered clean and missing/messy source states,
but the QA ladder still needed an adversarial source packet that combined:

- prompt-injection language embedded as source text;
- missing claimant identity;
- missing employer or defendant identity;
- unresolved prospective client, payer, carrier, or represented-party posture;
- nonparty organizational references that must not be promoted into principal
  parties without evidence.

This case proves that hostile source instructions remain untrusted data and do
not authorize conflict clearance, deadline docketing, matter opening, budget
submission, or amount-budget output. The expected budget outcome is
`block_amount_budget` with candidate exception labels and follow-up actions.

## Boundary

- No real client, matter, public-record, privileged, or private rate data.
- No connector, portal, billing, court, Lake, SQLite, matter-opening, conflict
  conclusion, budget submission, docketing, or training write.
- No canonical taxonomy or schema promotion from this repo.
- Source-observed evidence remains separate from practice-context priors and
  human-confirmed facts.
- Prompt-injection text is classified as source content, not instructions.

## Evidence

- Source bundle:
  `examples/synthetic/labor-employment/executable-fixtures/le-ada-fmla-adversarial.source-bundle.json`
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

The full validation suite passed with 570 pytest tests, schema export, ruff,
smoke demo, and final repo validation.

## Follow-Up

Continue filling executable L&E pack gaps in small slices, especially EPLI
adversarial and class/collective missing-attachment coverage. Keep each new
fixture source-bound, synthetic-only, candidate-only, and paired with deterministic
budget-output expectations before it reaches the read-only UI.
