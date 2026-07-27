# TRACE-2026-06-24 - Final Package Evidence Ref Hashes

## Situation

Structured packets already carried full `EvidenceRef` objects with source ID, segment ID, offsets, and `sha256`. Strict validation also checked refs against the segment table. The human-facing Markdown package rendered only source ID, segment ID, and offsets, so reviewers still had to open JSON artifacts to see the hash.

## Decision

Render evidence refs as `source/segment[start:end] sha=<hash>` in review Markdown through the shared `_ref_text` helper.

Completeness and smoke coverage now require the final matter-opening review package to contain reviewer-facing evidence hashes.

## Non-decision

This does not change the `EvidenceRef` schema, promote an evidence-ref contract to Semantic Substrate, add a new authority plane, approve any legal conclusion, create connectors, or write externally.

## Authority impact

This is local candidate review-package rendering in `LawFirm-os-intake`. Semantic Substrate remains the authority for any promoted evidence-ref contract, and Orchestrator remains the future execution owner.

## Evidence

- Existing packet schemas already include `sha256` on `EvidenceRef`.
- Existing strict validators already reject evidence refs whose source ID, offsets, or hash drift from the cited segment.
- Human-review package lines already used a shared evidence-ref renderer, so one rendering change exposes the full pointer wherever refs are shown.

## Alternatives rejected

- Keep hashes JSON-only: rejected because the north-star review package should expose source refs, offsets, and hashes without requiring a reviewer to inspect JSON first.
- Render shortened hashes only: rejected because the exact hash is already available and is the useful verification value.
- Add a new schema field: rejected because the existing `EvidenceRef.sha256` field is sufficient.

## Risks and rollback

The main risk is longer Markdown lines in dense review sections. The change is contained to rendering, tests, smoke checks, and documentation. Rollback restores `_ref_text` to source/segment/offset rendering without touching packet schemas.

## Validation

- `python -m ruff format src tests scripts` -> 1 file reformatted, 47 files left unchanged.
- `python -m pytest tests/test_review_package.py tests/test_review_package_completeness.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` -> passed.

## Human gates

Human review remains required for matter family, representation posture, principal party roles, conflicts clearance, engagement authorization, budget review, and matter-opening authorization.
