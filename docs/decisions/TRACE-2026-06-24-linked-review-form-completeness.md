# TRACE-2026-06-24 - Linked Review Form Completeness

## Situation

The budget run emitted three human-facing review surfaces: `intake_review_form.md`, `legal_budget_review_form.md`, and the consolidated `matter_opening_review_package.md`. The completeness report already proved that the consolidated package retained required sections and boundary text, but it did not inspect the linked intake or budget review forms beyond file existence.

That left a gap: the standalone first-pause and budget-review forms could lose source coverage, outcome handling, budget lines, support items, or submission-boundary content while the final package still passed.

## Decision

Extend `ReviewPackageCompletenessReport` with a `linked_review_forms_complete` check.

The check reads:

- `preflight_intake_review_form`;
- `legal_budget_review_form`.

It fails if the intake form is missing source coverage, candidate review, reviewer decision, review outcome handling, or prohibited-next-step sections. It fails if the budget form is missing calculation report, budget lines, evidence-bound supports, review checks, or submission boundary sections.

## Non-decision

This does not change package schemas, review form schemas, budget math, approval state, human outcome semantics, Exception Lake admission, route IDs, event classes, or external write behavior.

## Authority impact

This is local package-acceptance validation in `LawFirm-os-intake`. Orchestrator remains the future owner of runtime package assembly and human pause routing. Semantic Substrate remains the authority for promoted review-package contracts.

## Evidence

- The final manifest already links both review forms.
- The final package completeness report already reads the consolidated review package.
- The intake and budget forms now contain important human-review sections that should be protected by run-level acceptance checks.

## Alternatives rejected

- Rely on smoke tests only: rejected because every run should emit its own deterministic proof.
- Only check file existence: rejected because a present but hollow review form weakens human review.
- Fold the forms into the final package only: rejected because standalone review surfaces remain useful artifacts for separate human pauses.

## Risks and rollback

The risk is additional completeness failures if section headings change without updating the required-section list. That is acceptable because heading changes affect reviewer navigation. Rollback removes the linked-form check without changing generated review forms.

## Validation

- `python -m ruff format src tests scripts` -> 1 file reformatted, 47 files left unchanged.
- `python -m pytest tests/test_review_package_completeness.py tests/test_review_package.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` -> passed.

## Human gates

The check protects review surfaces only. Human intake confirmation, conflicts clearance, engagement authorization, budget review, and matter-opening authorization remain required and outside autonomous control.
