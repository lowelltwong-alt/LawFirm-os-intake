# TRACE 2026-07-04: QA Workbench UI

## Decision

Add a read-only `QAWorkbenchPanel` to the local legal-intake-budget UI. The panel
derives testing readiness and next QA targets from existing committed fixture
reports instead of introducing a new runtime artifact or authority surface.

## Rationale

After completing L&E executable fixture coverage, the dashboard needed a compact
operational view that shows whether the synthetic testing ladder is ready for
the next slice. The workbench summarizes validation evidence, executable
coverage, budget-output partitioning, and the review queue, then highlights
budget stress targets from the existing output-expectation report.

## Expected Deterministic Behavior

- Validation readiness comes from `demo-validation-suite-evidence-report.json`.
- L&E fixture readiness comes from
  `demo-labor-employment-executable-coverage-report.json`.
- Budget-output partitioning comes from
  `demo-labor-employment-budget-qa-gate-report.json`.
- Review queue posture comes from `demo-synthetic-qa-blocker-report.json` and
  `demo-poc-qa-triage-report.json`.
- Budget stress targets are sorted from existing local budget-output cases by
  amount blocks, critical review-only impacts, and range-widening impacts.

## Prohibited Outcomes

- No new backend command, schema authority, connector, Lake write, SQLite write,
  matter opening, conflict conclusion, calibration approval, or budget
  submission.
- No real data, public payload ingestion, or production rate inference.
- No new committed generated runtime directory.

## Validation

```text
npm run build
python scripts\run_full_pytest.py tests\test_ui_foundation_contract.py -q
python -m ruff check tests\test_ui_foundation_contract.py
python -m ruff format --check tests\test_ui_foundation_contract.py
```
