# TRACE-2026-06-29 - L&E Readiness Registration

## Context

The labor/employment budget fact-gap audit was added as a local candidate surface,
but the final vertical readiness audit still counted only the prior 27 slices.
That made the repo's machine-readable closeout evidence stale: the L&E budget
fact surface existed, but the remaining-phase audit did not prove it.

## Decision

Register the L&E fact-gap audit as a required local slice in
`audit-intake-vertical-readiness`.

The readiness audit now checks:

- `src/lawfirm_os_intake/labor_employment_budget_facts.py`;
- `config/labor-employment-budget-fact-needs.yaml`;
- exported L&E fact-gap schemas;
- `tests/test_labor_employment_budget_facts.py`;
- `docs/decisions/TRACE-2026-06-29-labor-employment-budget-fact-gaps.md`;
- command visibility for `audit-labor-employment-budget-facts`.

## Red-Team Notes

- Readiness registration is not production readiness.
- A passing L&E fact-gap audit is still a candidate review surface; it does not
  approve a budget, clear conflicts, submit a budget, open a matter, write Lake
  or SQLite records, promote canonical L&E taxonomies, or authorize runtime
  connectors.
- Critical L&E fact gaps must continue to block precise budget posture rather
  than becoming a hidden default.

## Validation

- `python -m pytest tests/test_intake_vertical_readiness_audit.py tests/test_labor_employment_budget_facts.py -q`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/export_schemas.py`
- `python scripts/run_full_pytest.py` - 373 passed in 299.69s
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'`
- `python scripts/validate_repo.py`
- Cross-repo AI front-door validation
- Cross-repo skill-agent control plane validation
