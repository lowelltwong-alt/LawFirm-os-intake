# TRACE: EPLI Carrier Adversarial Executable Fixture

Date: 2026-07-04

## Decision

Add an adversarial EPLI carrier-assignment executable fixture to the Labor &
Employment synthetic QA ladder.

The fixture is candidate-only and synthetic-only. It expands executable L&E
coverage to 17 source bundles / 18 linked pack cases and closes the EPLI
adversarial fixture-family gap while keeping amount-budget output blocked.

## Rationale

The existing EPLI executable fixtures covered clean, messy-thread, and
missing-attachment source states. The QA ladder still needed an adversarial
source packet that combined:

- prompt-injection language embedded as source text;
- a carrier or TPA attempting to collapse payer status into represented-client
  status;
- leaked or unauthorized rate language;
- missing claimant identity;
- missing employer or defendant identity;
- prohibited next-step language for conflicts, docketing, matter opening, and
  budget submission.

This case proves that carrier/payer/instructing-source evidence remains a
candidate role signal, not a represented-client confirmation. It also proves
that leaked or unauthorized rate language is treated as source-bound risk
evidence and a missing-authorized-guideline blocker, not as pricing authority.

The expected budget outcome is `block_amount_budget` with source-bound critical
drivers for party topology, representation posture, and carrier guideline/rate
context.

## Boundary

- No real client, matter, public-record, privileged, carrier, or private rate
  data.
- No connector, portal, billing, court, Lake, SQLite, matter-opening, conflict
  conclusion, budget submission, docketing, or training write.
- No canonical event class, party-role taxonomy, or rate taxonomy promotion from
  this repo.
- Prompt-injection and leaked-rate text are classified as untrusted source
  content, not instructions or authorized rates.
- Corrections, future appeal outcomes, or rejection learning remain append-only
  candidate evidence until owner repos promote contracts.

## Evidence

- Source bundle:
  `examples/synthetic/labor-employment/executable-fixtures/le-epli-carrier-adversarial.source-bundle.json`
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
  `python scripts/run_full_pytest.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`
- Full validation:
  `python scripts/run_validation_suite.py --report-out .lawfirm-os-intake/synthetic-qa-review/quality/validation_suite_evidence_report.json --generated-at 2026-07-04T00:00:00Z`

The full validation suite passed with 570 pytest tests, schema export, ruff,
smoke demo, and final repo validation.

## Follow-Up

Continue filling executable L&E pack gaps in small slices. Next high-leverage
coverage is class/collective missing-attachment and retaliation/wrongful
termination adversarial coverage, followed by budget-driver benchmark replay and
carrier rejection/appeal outcome loops.
