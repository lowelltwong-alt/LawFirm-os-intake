# TRACE-2026-06-24 - Budget Review Line Detail

## Situation

The final matter-opening review package rendered calculation summary, budget lines, and budget supports. The standalone `legal_budget_review_form.md` still showed only the calculation report, support items, and review checks. A pricing or budget reviewer could confirm that a budget proposal existed, but still had to open JSON or the final package to inspect line-level hours, rates, expenses, assumptions, formulas, and evidence refs.

The v1.0 goal calls for human-reviewable budget packets. The dedicated budget review surface should therefore expose the same line-level detail as the final package.

## Decision

Render a `Budget Lines` section in `legal_budget_review_form.md` using the existing budget-line renderer.

Add a `Submission Boundary` section showing:

- approval state;
- client/carrier submission authorization state;
- human budget review requirement;
- separate conflicts, engagement, and matter-opening blockers.

## Non-decision

This does not change budget math, budget schemas, rates, templates, budget approval state, conflict clearance, engagement authority, client/carrier submission authority, billing, matter opening, or external writes.

## Authority impact

This is local review-form rendering in `LawFirm-os-intake`. Orchestrator remains the future owner of approval routing and runtime pauses. Semantic Substrate remains the authority for promoted budget contracts and approval doctrine.

## Evidence

- `BudgetProposal.lines` already carries hours, ranges, rate source, synthetic-rate labels, expenses, assumptions, formula, external-code candidates, and evidence refs.
- The final matter-opening review package already renders the same line details.
- The budget proposal approval state remains `proposed_for_human_review` and `not_authorized_for_client_submission=true`.

## Alternatives rejected

- Keep line details only in JSON: rejected because the standalone budget review form should be usable by a human reviewer without first opening machine artifacts.
- Link only to the final package: rejected because budget review is its own review surface and should not be weaker than the consolidated package.
- Add new budget fields: rejected because existing proposal fields already contain the required review data.

## Risks and rollback

The risk is a longer budget review form. The change is contained to Markdown rendering, tests, smoke checks, and docs. Rollback removes the `Budget Lines` and `Submission Boundary` sections without changing proposal generation.

## Validation

- `python -m ruff format src tests scripts` -> 48 files left unchanged.
- `python -m pytest tests/test_conflict_budget_hardening.py tests/test_review_package.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` -> passed.

## Human gates

Human budget review remains required before any client or carrier delivery. Conflicts clearance, engagement authorization, and matter-opening authorization remain separate blockers.
