# TRACE-2026-06-24 - Linked Review Form Evidence And Boundaries

## Situation

The package completeness report now verified that the linked intake and budget review forms preserved required section headings. That was useful, but a form could still keep its headings while losing the evidence hashes or non-authorization boundary text that make the form safe for human review.

The v1.0 objective requires evidence-first and human-reviewable artifacts. Linked review forms should therefore prove both structure and critical content.

## Decision

Add `linked_review_forms_preserve_evidence_and_boundaries` to `ReviewPackageCompletenessReport`.

The check requires:

- `intake_review_form.md` to retain evidence hash rendering and the no-conflicts/no-docket/no-matter-opening boundary text;
- `legal_budget_review_form.md` to retain evidence hash rendering when the budget proposal has source-bound evidence refs and to retain client/carrier non-submission boundary text.

## Non-decision

This does not change schemas, review form generation, budget math, human outcome behavior, approval state, conflict clearance, engagement authority, docketing, billing, matter opening, connector behavior, or external writes.

## Authority impact

This is local package-acceptance validation in `LawFirm-os-intake`. Orchestrator remains the future runtime package owner. Semantic Substrate remains the authority for promoted package contracts and evidence-ref doctrine.

## Evidence

- Both linked forms are already referenced in the final manifest.
- The intake form renders source-bound evidence refs with hashes, and the budget form renders source-bound evidence refs with hashes when budget lines or support items carry them.
- The intake form and budget form already include boundary text stating what they do not authorize.

## Alternatives rejected

- Check only headings: rejected because headings do not prove evidence or safety content survived rendering.
- Rely on final package evidence only: rejected because the standalone forms are separate review surfaces.
- Add new form schemas: rejected because this slice only needs deterministic acceptance checks over generated Markdown.

## Risks and rollback

The risk is a tighter completeness gate when wording changes. That is acceptable because these phrases are part of reviewer safety. Rollback removes the content-level check and keeps the section-level linked-form check.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 48 files left unchanged
- `python -m pytest tests/test_review_package_completeness.py tests/test_exception_candidates.py::test_missing_budget_template_emits_budget_template_exception_candidate tests/test_review_package.py tests/test_north_star_demo.py -q` - passed
- `python -m pytest -q` - passed
- `python scripts/export_schemas.py` - exported 22 schemas
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 48 files already formatted
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

## Human gates

The check protects evidence and boundary content in review forms. It does not authorize conflicts clearance, engagement, budget submission, docketing, billing, matter opening, or Exception Lake admission.
