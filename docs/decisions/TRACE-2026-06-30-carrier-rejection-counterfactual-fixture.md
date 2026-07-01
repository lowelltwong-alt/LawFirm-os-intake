# TRACE-2026-06-30 - Carrier Rejection Counterfactual Fixture

## Decision

Add a second synthetic carrier-rejection holdout fixture for partial allowances,
guideline-version drift, rate reductions, stale appeal outcomes, and denied appeal
outcomes.

## Why

The first carrier-rejection fixture proves duplicate notice collapse, missing
responses, unlinked notices, parser failures, and a partial appeal recovery. It
does not prove that partial allowances from different carriers remain bounded to
their rejected portion, nor that stale or denied appeal results are captured as
append-only financial evidence without becoming profile learning or appeal
submission.

## Scope

- Add `examples/synthetic/carrier-rejections/partial-allowance-guideline-drift-stale-appeal.json`.
- Register it as a second `carrier_rejection_variants` holdout.
- Add deterministic capture assertions for reconciliation counts, candidate labels,
  decision-ledger totals, stale/denied appeal results, and no-write/no-learning
  guardrails.

## Boundaries

- Synthetic-only fixture data.
- Candidate-only local event labels.
- No new canonical route IDs, event classes, party roles, matter taxonomies, or
  budget taxonomies.
- No connector reads or writes.
- No SQLite or Exception Lake admission writes.
- No appeal submission, budget mutation, guideline mutation, profile mutation, or
  silent learning.

## Red-Team Notes

- Partial allowances can overstate exposure if the full submitted amount is reused
  as the disputed amount. The regression pins exposure to the rejected/disputed
  portion.
- A guideline-drift rejection can look like permission to update a carrier profile.
  The regression keeps it as an `authority_conflict_override` candidate requiring
  human and owning-repo review.
- Stale appeal results can be mistaken for a completed appeal success/failure loop.
  The regression captures the remaining write-down while preserving human review
  gates and prohibiting automatic learning.

## Validation

Planned validation:

- `python scripts/run_full_pytest.py -- -q tests/test_carrier_rejection_capture.py tests/test_synthetic_fixture_expansion.py`
- `python scripts/validate_repo.py`
- `python scripts/export_schemas.py`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/run_full_pytest.py`
- `bash scripts/smoke_demo.sh`
