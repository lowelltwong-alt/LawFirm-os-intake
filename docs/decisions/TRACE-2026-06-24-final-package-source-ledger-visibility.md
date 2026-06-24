# Decision Trace

## Situation

The north-star review package linked source inventory and run-ledger artifacts, but the human-facing Markdown did not show enough of that audit surface inline. A reviewer could see counts and artifact refs, but still had to open JSON/JSONL files to inspect each source state and the gate-by-gate workflow trail.

## Decision

Render `## Source Inventory` and `## Run Ledger Summary` in `matter_opening_review_package.md`.

The source section shows each source ID, type, read state, availability state, hash, filename, duplicate link, attachment refs, and metadata keys. The ledger section shows preflight and budget ledger refs plus step names, statuses, input counts, output counts, and notes.

`ReviewPackageCompletenessReport` now requires both sections before package acceptance.

## Non-decision

This does not change schemas, event classes, route IDs, runtime authority, or ledger persistence. It does not admit Exception Lake records, approve budgets, clear conflicts, open matters, docket deadlines, or write externally.

## Authority impact

This is local candidate review-package rendering in `LawFirm-os-intake`. Canonical run-ledger, evidence-packet, event-class, and package-acceptance authority remain with Semantic Substrate, Orchestrator, and Exception Lake as applicable.

## Evidence

- The north-star objective requires a complete review package with source inventory and run ledger.
- Existing artifacts already include `source_inventory.json`, preflight `run_ledger.jsonl`, and budget `run_ledger.jsonl`.
- The change surfaces those existing artifacts in Markdown without expanding the workflow authority.

## Alternatives rejected

- Link only to JSON artifacts: rejected because the human-facing package should make the audit trail inspectable without file hopping.
- Add new schema fields: rejected because the existing source inventory and ledger records already carry the needed data.
- Move ledger ownership into intake: rejected because Orchestrator remains the future runtime owner.

## Risks and rollback

The risk is review-package verbosity. The change is contained to rendering, completeness requirements, docs, smoke checks, and tests. Rollback removes the two sections and their completeness requirements without affecting the underlying structured artifacts.

## Validation

- `python -m ruff format src tests scripts` -> 48 files left unchanged.
- `python -m pytest tests/test_review_package.py tests/test_review_package_completeness.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash scripts/smoke_demo.sh` in Git Bash could not find `python`; rerun with the local Python path exported passed:
  `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'`.

## Human gates

Human review remains required for conflicts clearance, engagement authorization, budget review, and matter-opening authorization.
