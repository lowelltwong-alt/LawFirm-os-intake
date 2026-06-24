# TRACE-2026-06-24 - Exception Detail Evidence Ref Hashes

## Situation

The final review package rendered most source-bound evidence refs through the shared `_ref_text` helper, which now includes source ID, segment ID, offsets, and hash. Exception Candidate Details still rendered dry-run candidate evidence refs from dictionaries manually, omitting the hash from that subsection.

That created a reviewer-facing provenance gap: Exception Lake candidate JSON carried `sha256`, but the human-readable package did not show it beside exception evidence.

## Decision

Render exception candidate detail evidence refs as `source/segment[start:end] sha=<hash>` using a dictionary-specific helper.

Tests and smoke coverage now check the Exception Candidate Details section itself for evidence hashes, rather than relying on package-wide hash presence from other sections.

## Non-decision

This does not change `ExceptionLakeCandidate`, admit records to the Exception Lake, create SQLite storage, promote event classes, create route IDs, store raw payloads, or write externally.

## Authority impact

This is local review-package rendering in `LawFirm-os-intake`. Semantic Substrate remains the authority for canonical event classes and evidence contracts. Exception Lake runtime remains the owner of admission validation, persistence, append-only semantics, correction behavior, and any future SQLite schema.

## Evidence

- `ExceptionLakeCandidate.evidence_refs` already carries `sha256`.
- The readiness report already validates candidate support refs before future Lake handoff.
- The final package already includes an Exception Candidate Details section for reviewer inspection.

## Alternatives rejected

- Leave hashes visible only in JSON/JSONL: rejected because exceptions are part of the review package and should expose the same source-bound pointer shape as candidates, conflict terms, and budget supports.
- Reuse `_ref_text` by coercing dictionaries into model instances: rejected because the renderer only needs a simple, local formatting helper.
- Add schema fields: rejected because the existing dicts already contain the required hash.

## Risks and rollback

The risk is slightly longer exception-detail lines. The change is contained to Markdown rendering, tests, smoke checks, and docs. Rollback removes `_dict_ref_text` and restores source/segment/offset-only exception detail rendering.

## Validation

- `python -m ruff format src tests scripts` -> 1 file reformatted, 47 files left unchanged; after the smoke-script follow-up, 48 files left unchanged.
- `python -m pytest tests/test_review_package.py tests/test_north_star_demo.py tests/test_exception_candidates.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` -> passed.
- Initial CI run `28068842391` failed in `bash scripts/smoke_demo.sh` with exit 141 because the section-scoped `awk | grep -q` assertion interacted poorly with `pipefail`; the smoke script now captures the exception-detail section before grepping it.

## Human gates

Exception details remain review evidence only. Human review remains required for conflicts clearance, engagement authorization, budget review, matter opening, and any future Exception Lake admission or promotion decision.
