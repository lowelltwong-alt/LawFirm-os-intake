# Decision Trace

## Situation

The final review package listed local exception labels and linked the Exception Lake readiness report, but did not render the safety posture or support pointers for each dry-run candidate. That meant a reviewer could see that an exception existed, but had to open JSON/JSONL artifacts to verify raw-payload exclusion, dry-run admission state, canonical-promotion requirement, target runtime repo, evidence refs, structured refs, and blocked state.

## Decision

Render `### Exception Lake Readiness` and `### Exception Candidate Details` inside `matter_opening_review_package.md`.

The readiness subsection shows status, admission state, target runtime repo, candidate count, candidate files, and readiness checks. The candidate-detail subsection shows each local candidate's class, status, raw-payload flag, promotion requirement, target runtime repo, blocked state, source refs, evidence refs, and structured refs.

`ReviewPackageCompletenessReport` now requires both exception subsections before package acceptance.

## Non-decision

This does not admit records to the Exception Lake, create SQLite storage, promote event classes, create route IDs, change Lake contracts, store raw payloads, or write externally.

## Authority impact

This is local candidate review-package rendering in `LawFirm-os-intake`. Semantic Substrate remains the authority for canonical event classes and route IDs. Exception Lake runtime remains the owner of admission validation, persistence, append-only semantics, and any future SQLite schema.

## Evidence

- Preflight and budget runs already emit `exception_lake_candidates.jsonl`.
- Preflight and budget runs already emit `exception_lake_readiness_report.json`.
- The readiness report already verifies dry-run posture, raw-payload exclusion, promotion requirement, target repo, and support refs.
- This change exposes that existing proof in the human-readable north-star package.

## Alternatives rejected

- Keep exception proof in JSON only: rejected because exception awareness is central to the v1.0 north-star package.
- Add new Lake admission behavior: rejected because this repo must not own Exception Lake persistence.
- Promote local labels from intake: rejected because Semantic Substrate owns canonical event-class authority.

## Risks and rollback

The risk is a longer package when many exception candidates exist. The change is contained to rendering, completeness requirements, tests, smoke checks, and docs. Rollback removes the two subsections and required-section entries without changing emitted candidate files.

## Validation

- `python -m ruff format src tests scripts` -> 48 files left unchanged.
- `python -m pytest tests/test_review_package.py tests/test_review_package_completeness.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash scripts/smoke_demo.sh` in Git Bash could not find `python`; rerun with the local Python path exported passed:
  `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'`.

## Human gates

Human review remains required for conflicts clearance, engagement authorization, budget review, matter opening, and any future Exception Lake admission or promotion decision.
