# Decision Trace

## Situation

The Upfront-like matter-linking preflight could identify ambiguous or resolved
document clusters, but the QA flow did not yet have an append-only human review
outcome artifact for split, merge, unknown, or request-more-information
decisions. That left a gap between "candidate clusters require review" and a
reviewable local record that future Orchestrator and Exception Lake owners could
inspect.

## Decision

Add local candidate-only matter-linking review outcome models, fixtures, CLI,
tests, schema exports, synthetic QA recipe integration, and a read-only UI panel.
The new command writes `matter_linking_review_outcome_record.json`,
`matter_linking_review_outcome_history.jsonl`,
`matter_linking_review_outcome_report.json`, and Markdown notes. It supports
confirm split, confirm merge, confirm single candidate, unknown,
request-more-info, and declined/referred outcomes.

## Non-decision

This does not create an Upfront connector, verify the Upfront API contract,
create a screen, clear conflicts, output or submit a budget, open a matter,
write Lake/SQLite records, promote canon, mutate sibling repos, or learn from
reviewer corrections.

## Authority impact

This remains local `LawFirm-os-intake` candidate workflow evidence. Semantic
Substrate still owns canonical route/schema/taxonomy authority, Orchestrator
owns runtime workflow pauses and external actions, and Exception Lake owns any
future admission/storage contract.

## Evidence

- `examples/synthetic/upfront/matter-linking-review-confirm-split.outcome.json`
- `examples/synthetic/upfront/matter-linking-review-request-more-info.outcome.json`
- `src/lawfirm_os_intake/matter_linking_review_outcomes.py`
- `tests/test_matter_linking_review_outcomes.py`
- `apps/legal-intake-budget/src/fixtures/demo-matter-linking-review-outcome-report.json`
- `apps/legal-intake-budget/src/App.tsx`
- `docs/integrations/upfront-intake-integration-research.md`
- `docs/human-review.md`

## Alternatives rejected

- Treating preflight resolution as final was rejected because official matter
  authority, role confirmation, conflict review, and budget authority are still
  separate human/owner-gated steps.
- Writing directly to the Exception Lake was rejected because Lake admission,
  SQLite schema, idempotency, and storage hashing belong to the Exception Lake
  runtime, not this vertical repo.
- Letting the UI infer the review outcome was rejected because the frontend must
  render backend local JSON artifacts rather than becoming an authority surface.

## Risks and rollback

The main risk is a future caller treating a confirmed split as matter-opening or
budget authority. The models and UI carry explicit no-write/no-authority flags,
and tests assert those flags remain false. Rollback is removing the new command,
fixtures, schema exports, and UI panel; existing preflight behavior remains
separate.

## Validation

Initial focused validation passed:

```bash
python scripts/run_full_pytest.py tests/test_matter_linking_review_outcomes.py tests/test_matter_linking_preflight.py -q
```

Full validation for the PR must still run before merge.

## Human gates

Human review is still required before any candidate matter cluster can be used
for downstream conflict seed review, role confirmation, budget proposal work, or
owner adoption. Exception Lake owners must separately approve any future Lake
admission mapping.
