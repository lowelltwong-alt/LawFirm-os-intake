# TRACE-2026-06-24 - Intake Review Outcome Handling

## Situation

The final matter-opening review package had become highly auditable, but the earlier `intake_review_form.md` remained lighter. It showed candidate alternatives and reviewer checkboxes, but source inventory rows omitted useful details such as duplicate links, attachment refs, filenames, metadata keys, and character counts. It also did not explain what each reviewer outcome would do to the workflow.

The first human pause should reduce rubber-stamp behavior and make blocking consequences visible before a confirmation artifact is created.

## Decision

Render detailed source inventory rows in the intake review form using the same source inventory formatter used by the final review package.

Add a `Review Outcome Handling` section that maps:

- `confirmed` to `budget_precondition_gate`;
- `needs_more_information` to `collect_missing_information`;
- `unknown` to `human_classification_correction`;
- `human_only` to `human_only_handling`;
- `declined` and `declined_or_referred` to `declined_or_referred_handoff`;
- corrections to `append_or_supersede_only`.

The section states that confirmed outcomes may advance only after exact packet binding and evidence checks, while the other outcomes block budget-stage output.

## Non-decision

This does not change `HumanConfirmation`, `HumanReviewOutcomeRecord`, budget precondition behavior, schemas, route IDs, event classes, human approval authority, or any external write behavior.

## Authority impact

This is local human-review rendering in `LawFirm-os-intake`. Orchestrator remains the future owner of human pause/resume mechanics. Semantic Substrate remains the authority for promoted review outcome contracts and lifecycle policy.

## Evidence

- `build_human_review_outcome_record` already maps statuses to the required next gate.
- `build_budget_precondition_report` already blocks non-confirmed, mismatched, or evidence-free confirmations before conflict seed, budget, readiness, safety, or final package output.
- Source inventory rows already carry duplicate links, attachment refs, filenames, metadata keys, character counts, and hashes.

## Alternatives rejected

- Leave outcome behavior to budget-stage JSON: rejected because the reviewer should see consequences before creating a confirmation.
- Add a new review outcome schema: rejected because existing outcome records already model the behavior.
- Add an interactive review UI now: rejected because the local generated artifact is enough for this governed starter slice.

## Risks and rollback

The risk is a longer intake form. The change is contained to Markdown rendering, tests, smoke checks, and documentation. Rollback restores the lighter source rows and removes the outcome-handling section without changing packet schemas or gate behavior.

## Validation

- `python -m ruff format src tests scripts` -> 48 files left unchanged.
- `python -m pytest tests/test_source_inventory_and_review.py tests/test_confirmation_binding.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` -> passed.

## Human gates

Human intake confirmation remains required for matter family, representation posture, and principal party roles. This change makes the allowed outcomes and their blocking consequences clearer; it does not approve conflicts, engagement, budget submission, docketing, billing, or matter opening.
