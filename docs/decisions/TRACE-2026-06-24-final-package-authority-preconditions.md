# Decision Trace

## Situation

The final review package linked `contract_state_report.json`, `human_review_outcome.<confirmation_id>.json`, and `budget_precondition_report.json`, but did not render their gate results inline. That made the package weaker as a governed review artifact because a reviewer had to open separate JSON files to verify LawFirm OS lock state, human-review eligibility, and budget-stage preconditions.

## Decision

Render `## Authority And Preconditions` in `matter_opening_review_package.md`.

The section includes contract-state status, reviewed lock status, dependency pins, contract checks, human review outcome status, budget-stage eligibility, required next gate, budget precondition status, prohibited outputs on precondition failure, and external-write state.

`ReviewPackageCompletenessReport` now requires the authority/precondition section and its contract-state, human-review-outcome, and budget-precondition subsections before package acceptance.

## Non-decision

This does not change lock semantics, promote any local contract to canon, authorize budget generation without confirmation, clear conflicts, approve engagement, approve budgets, docket deadlines, open matters, create connectors, or write externally.

## Authority impact

This is local candidate review-package rendering in `LawFirm-os-intake`. Semantic Substrate remains the authority for canonical contract state and repo membership. Orchestrator remains the future owner of runtime gates and evidence packet assembly.

## Evidence

- Every preflight run already emits and enforces `contract_state_report.json`.
- Every budget attempt already writes `human_review_outcome.<confirmation_id>.json` and `budget_precondition_report.json` before proposal output.
- Existing safety and completeness gates already require those artifacts by reference; this change makes their key gate states visible in the human-readable package.

## Alternatives rejected

- Keep gate proof in JSON only: rejected because the north-star package should explain why the workflow is authorized to produce a proposal but blocked from opening/submitting.
- Add new gate schemas: rejected because the existing reports already carry the required facts.
- Move gate ownership into intake: rejected because intake remains a vertical evaluation repo, not the execution authority plane.

## Risks and rollback

The risk is additional review-package length. The change is contained to Markdown rendering, completeness requirements, tests, smoke checks, and docs. Rollback removes the section and required-section entries without changing underlying gate artifacts.

## Validation

- `python -m ruff format src tests scripts` -> 1 file reformatted.
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
