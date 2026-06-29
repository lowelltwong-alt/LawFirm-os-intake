# Decision Trace - Budget Uncertainty Exception Candidates

## Situation

The budget proposal exposed unknowns, missing templates, and hours-only pricing states, but the budget-stage `exception_lake_candidates.jsonl` only emitted the final matter-opening blocker. Budget uncertainty was visible to a human reviewer, yet it was not separately captured as structured dry-run Exception Lake evidence.

## Decision

Extend local `ExceptionLakeCandidate` with `structured_refs` and emit budget-stage workflow-escalation candidates for:

- budget unknowns that require review;
- missing approved synthetic budget template;
- hours-only proposals caused by missing authorized rates.

The candidates remain dry-run only, include no raw payload, and use broad canonical Lake classes already allowed by the local mapping.

## Non-decision

This does not approve budgets, submit budgets, invent rates, create a SQLite Lake store, or promote intake-specific event labels into Semantic Substrate canon.

## Authority Impact

This is local candidate-surface work in `LawFirm-os-intake`. Exception Lake admission, SQLite schema, canonical event classes, and route IDs remain owned by the governing platform repos.

## Evidence

- `BudgetProposal` already records `pricing_status`, `unknowns`, `calculation_report`, and `budget_support_items`.
- Budget support items already require source-bound evidence refs or structured refs.
- The budget stage already writes dry-run `exception_lake_candidates.jsonl` with `raw_payload_included=false`.

## Alternatives Rejected

- Leave uncertainty only in the Markdown review package: rejected because downstream Lake evaluation needs typed records.
- Treat missing rates as an error: rejected because hours-only mode is the governed fallback.
- Add canonical budget event labels directly: rejected because Semantic Substrate must own canonical promotion.

## Risks And Rollback

The main risk is more budget exception candidates in normal demo output because the synthetic template intentionally contains unknowns. That is acceptable and reviewable. Rollback would remove budget uncertainty candidates and the `structured_refs` field, but would weaken Exception Lake readiness.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/export_schemas.py` - exported 18 schemas.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest` - 44 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check src tests scripts` - all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff format --check src tests scripts` - 41 files already formatted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash scripts/smoke_demo.sh` - completed without error.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/validate_repo.py` - repository validation passed.

## Human Gates

These candidates are escalation evidence only. They do not authorize rates, approve a budget, submit a budget, clear conflicts, engage a client, bill, or open a matter.
