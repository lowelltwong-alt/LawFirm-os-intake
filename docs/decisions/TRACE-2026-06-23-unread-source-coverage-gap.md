# Decision Trace - Unread Source Coverage Gap

## Situation

The source inventory model allowed `read_state="unread"`, but unread sources were not counted separately in source coverage, shown in review summary counts, or emitted as dry-run Exception Lake candidates. That made an unread attachment less visible than a missing or unreadable source even though downstream workers still must not invent its content.

## Decision

Add `unread_sources` to the source coverage summary, render unread-source counts in review artifacts, and emit `source_unread` dry-run Exception Lake candidates mapped to `retrieval_miss`.

## Non-decision

This does not ingest unread content, infer its contents, fetch attachments, add a connector, or change canonical Exception Lake classes.

## Authority Impact

This is local candidate-surface behavior in `LawFirm-os-intake`. Exception Lake admission and canonical event-class promotion remain owned by the governing platform repos.

## Evidence

- `SourceInventoryItem.read_state` already includes `unread`.
- The starter already emits dry-run candidates for missing and unreadable source coverage gaps.
- Human review docs require source coverage and unread sources to be visible.

## Alternatives Rejected

- Treat unread as available/read: rejected because it hides a coverage gap.
- Treat unread as missing: rejected because unread is a distinct operational state and may be resolved later without changing source identity.
- Store placeholder content: rejected because the workflow must not invent or smuggle unread material.

## Risks And Rollback

The main risk is one additional retrieval-miss candidate for fixtures with unread sources. The change is contained to summary counts, review text, and dry-run exception candidates. Rollback would remove the unread count and `source_unread` candidate.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/export_schemas.py` - exported 18 schemas.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest` - 45 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check src tests scripts` - all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff format --check src tests scripts` - 41 files already formatted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash scripts/smoke_demo.sh` - completed without error.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/validate_repo.py` - repository validation passed.

## Human Gates

Unread source gaps remain human-review items. They do not authorize downstream legal, conflict, budget, docketing, billing, or matter-opening decisions.
