# TRACE: Labor/Employment Executable Fixture Preflight Gate

## Context

The L&E fixture-family pack proved spec coverage across families, variants, fact needs, and budget-driver dimensions, but it did not prove that any inbound L&E documents were runnable through the existing preflight pipeline. That left a gap between "we know which fixture families we need" and "we have actual source bundles that exercise source inventory, segmentation, evidence refs, exception candidates, and no-write boundaries."

## Decision

Add a candidate-only executable fixture manifest and audit command:

- `examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json`;
- selected synthetic source bundles under `examples/synthetic/labor-employment/executable-fixtures/`;
- `audit-labor-employment-executable-fixtures`;
- `labor_employment_executable_fixtures_report.json`;
- schemas, tests, smoke, QA bundle, and UI manifest registration.

The first executable fixtures cover wage/hour missing payroll/timekeeping attachments, EPLI carrier/client/payer ambiguity, class/collective adversarial source instructions, and ADA/FMLA missing/duplicate correspondence. Each fixture links back to the spec-only family pack and runs through deterministic `run_preflight`.

## Boundary

This gate proves preflight executability only. It does not:

- create an amount budget;
- perform L&E budget fact extraction from inbound source bundles;
- clear conflicts, authorize engagement, open a matter, submit a budget, or docket deadlines;
- write Exception Lake or SQLite records;
- promote role, matter, event, or budget taxonomy canon;
- learn from corrections or create training data.

Every case records `budget_fact_audit_required=true` so the next slice can bind executable preflight fixtures to the L&E fact-gap audit without overstating what this step proves.

## Verification

- `PYTHONPATH=src python scripts/run_full_pytest.py tests/test_labor_employment_executable_fixtures.py tests/test_synthetic_qa_bundle.py tests/test_ui_review_manifest.py tests/test_budget_calibration_starter_pack.py tests/test_ui_foundation_contract.py -q`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `PYTHONPATH=src python scripts/export_schemas.py`
