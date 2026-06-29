# TRACE-2026-06-24 - Starter Release Audit

## Situation

The north-star demo now emits a complete review package, fixture-gold reports, safety gate, review-package completeness report, Exception Lake readiness reports, and run ledgers. Those artifacts prove important pieces of the starter goal, but the release-level proof was still spread across unit tests, smoke-script `grep` checks, and prose.

The project goal asks for a governed proving ground. That requires a durable artifact that says whether a generated demo satisfies starter release invariants without claiming platform authority.

## Decision

Add `StarterReleaseAuditReport` and `StarterReleaseAuditCheck`, export their schema, and add `scripts/audit_starter_release.py`.

The audit inspects an already-generated demo directory and checks:

- root front-door files and no nested duplicate repo root;
- required preflight and budget artifacts;
- synthetic-only scope;
- contract-state and model-adapter gates;
- candidate registries remain noncanonical;
- candidate and ingestion evidence refs validate against segments;
- Rust parity/readiness remains prepared but replacement is unauthorized;
- human confirmation and budget preconditions;
- carrier/client separation;
- conflict-search seed boundary and evidence;
- budget proposal boundary and deterministic math;
- terminal safety boundary;
- dry-run Exception Lake posture and expected labels;
- review package completeness and local artifact refs;
- reviewed fixture-gold gates;
- expected run-ledger gate steps.

Wire the audit into `scripts/smoke_demo.sh` so the smoke run writes `budget/starter_release_audit_report.json` and fails closed if any starter invariant drifts.

## Non-decision

This does not create canonical schemas, route IDs, event classes, real-data authorization, provider calls, connector writes, conflict clearance, engagement authorization, matter opening, docketing, budget approval, Exception Lake admission, or production readiness.

The audit is not a replacement for unit tests, CI, Semantic Substrate promotion, Orchestrator runtime ownership, or human legal review.

## Authority impact

This is a local intake evaluation artifact only. Semantic Substrate remains the authority for promoted contracts and canonical vocabularies. Orchestrator remains the future runtime owner. Exception Lake remains the owner of append-only admission and persistence.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 2 files reformatted, then 55 files left unchanged on rerun
- `python -m pytest tests\test_starter_release_audit.py -q` - passed
- `python scripts\export_schemas.py` - exported 27 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 78 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - passed
- `python scripts\validate_repo.py` - passed after generated caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed and wrote `budget/starter_release_audit_report.json`
