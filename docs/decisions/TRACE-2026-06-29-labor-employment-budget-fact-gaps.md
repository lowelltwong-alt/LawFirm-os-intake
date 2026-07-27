# TRACE-2026-06-29 - Labor/Employment Budget Fact Gaps

## Context

The next budget-learning pressure is labor and employment intake. The user flagged a core risk: inbound documents may name people and companies without enough relationship, claim, damages, discovery, or guideline facts to support a useful budget. Entity understanding matters because a person, employer, supervisor, HR actor, parent/subsidiary, joint employer, carrier, agency, or union can change conflict seeds and litigation budget drivers.

## Decision

Add a candidate-only L&E budget fact-gap audit:

- `config/labor-employment-budget-fact-needs.yaml`;
- `LaborEmploymentBudgetFact*` report models and exported schemas;
- `audit-labor-employment-budget-facts`;
- tests covering blocking unknowns, exact source refs, missing employee/person relationships, and CLI output.

The audit reads the existing synthetic CourtListener-style L&E manifest and classifies source-bound candidate facts versus explicit unknowns. Critical missing or review-only facts set `budget_readiness_state=blocked_missing_critical_facts`.

## Red-Team Notes

- A source-bound label is not a human-confirmed fact.
- Synthetic wrapper context cannot become observed evidence.
- Missing supervisors, joint-employer structure, claims, damages, ESI/custodians, depositions, experts, policy documents, or carrier/rate context must widen or block budget posture instead of silently defaulting.
- The audit must not approve a budget, infer rates, clear conflicts, open a matter, write to the Exception Lake, create SQLite records, ingest public records, create training data, or learn from corrections.

## Scope

This is a local review/audit surface only. It does not change budget math, promote canonical roles or taxonomies, add connectors, ingest real/public records, or authorize Rust replacement.

## Validation

- `python -m pytest tests/test_labor_employment_budget_facts.py -q`
- `python -m pytest tests/test_validation_runtime_policy.py tests/test_labor_employment_budget_facts.py -q`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/export_schemas.py`
- `python scripts/run_full_pytest.py`
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'`
- `python scripts/validate_repo.py`
