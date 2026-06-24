# TRACE-2026-06-24 - Fixture Gold Gate

## Situation

The repo had strong synthetic fixtures and tests, but no first-class reviewed gold artifact that a builder could pass to the CLI to score an emitted run. That left acceptance behavior spread across unit tests and smoke assertions instead of producing a durable run artifact.

The v1.0 goal calls for repeatable quality: fixtures, expected outputs, tests, schema export, data-flow docs, and CI. The evaluation plan also calls for top-three matter recall, role-candidate recall, deadline-candidate recall, missing-information coverage, exception recall, and end-state workflow evals.

## Decision

Add local `FixtureGoldSpec` and `FixtureGoldReport` models, export their schemas, and wire `--fixture-gold` into `preflight`, `build-budget`, and `demo`.

When supplied, the workflow writes `fixture_gold_report.json` and fails closed if reviewed synthetic expectations drift. The first reviewed gold file is `examples/synthetic/gold/north-star-messy-intake.fixture-gold.json`.

The gold report checks:

- reviewed synthetic-only gold status;
- source coverage and source inventory states;
- top-three matter candidate recall;
- top inbound-event and representation-posture candidates;
- party-role candidate recall and prohibited carrier/client role collapse;
- date/deadline candidate recall;
- missing-information recall;
- critic finding and dry-run exception label recall;
- source-bound evidence presence;
- human confirmation, conflict conclusion boundary, conflict term groups;
- budget proposal state, non-submission boundary, budget exceptions;
- budget precondition, safety gate, final blocker state, and no external writes.

## Non-decision

This does not create canonical labels, canonical taxonomies, route IDs, event classes, real-data evals, provider calls, external writes, conflict conclusions, engagement decisions, docketing, matter opening, budget approval, or client/carrier submission.

## Authority impact

The gold spec and report are local intake evaluation artifacts only. Semantic Substrate remains the authority for promoted schemas and canonical vocabularies. Orchestrator remains the future owner for runtime acceptance gates if this pattern is promoted.

## Alternatives rejected

- Keep gold in unit tests only: rejected because run-level acceptance should produce a durable artifact.
- Make gold labels canonical: rejected because reviewed fixture expectations are evaluation evidence, not platform authority.
- Grade raw text directly: rejected because the objective is to evaluate emitted packets and terminal state, not hidden internal trajectories.

## Risks and rollback

The main risk is brittle expectations when deterministic scoring changes. That is useful brittleness for reviewed synthetic acceptance; expectation updates should be explicit and reviewed. Rollback removes the models, evaluator, CLI flag, fixture, schemas, smoke checks, tests, and docs while leaving the core workflow intact.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 4 files reformatted, then 52 files left unchanged on rerun
- `python -m pytest tests/test_fixture_gold.py tests/test_north_star_demo.py tests/test_cli_demo.py tests/test_review_package.py tests/test_review_package_completeness.py -q` - passed
- `python scripts/export_schemas.py` - exported 26 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 75 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 52 files already formatted
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

Remaining before merge:

- pushed-branch CI.
