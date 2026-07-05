# TRACE 2026-07-05: Complete UI Demo Run Root

## Decision

Make the synthetic QA run-root promotion-ready by emitting every default UI
demo fixture promotion source at its exact allowlisted path.

The synthetic run now consumes prebuilt validation-suite evidence from
`scripts/run_validation_suite.py --report-out`, stages it as
`quality/validation_suite_evidence_report.json`, and emits
`quality/poc_qa_triage_report.json` from the final local QA artifacts. It also
stages the L&E replay-readiness report directly under `quality/` so promotion
does not rely on recursive filename fallback.

## Rationale

The read-only UI imported checked demo fixtures that were broader than the
generated run-root. Promotion correctly failed closed when
`poc_qa_triage_report.json` and `validation_suite_evidence_report.json` were
missing from static source paths. Validation evidence must stay honest: the
synthetic QA builder may consume a wrapper-produced validation report, but it
must not pretend to run full pytest or smoke checks internally.

## Expected Deterministic Behavior

- `build-synthetic-qa-review-run --validation-suite-evidence-report ...` stages
  validation evidence under the canonical run-root filename.
- The generated run-root includes every source ref in the default UI demo
  fixture promotion allowlist.
- POC QA triage clears only when validation evidence proves passed
  `full_pytest` and `smoke_demo` wrapper steps.
- Missing validation evidence remains fail-closed for POC QA readiness.
- Promotion does not rely on recursive fallback for the replay-readiness report.

## Prohibited Outcomes

- No internal full-validation simulation by the synthetic QA builder.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite
  write, connector write, or silent learning.
- No real case data, public payload, private rates, or production authority.

## Validation

Focused checks:

```text
python scripts\run_full_pytest.py tests\test_synthetic_qa_review_run.py tests\test_ui_foundation_contract.py::test_legal_intake_budget_ui_required_files_exist -q
```

Observed:

```text
2 passed
```
