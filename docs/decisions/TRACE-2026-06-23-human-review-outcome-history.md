# Decision Trace - Human Review Outcome History

## Situation

The review design allowed outcomes such as `unknown`, `needs_more_information`, `human_only`, and `declined_or_referred`, but the budget path only consumed a confirmation file and then relied on the budget precondition report to block non-confirmed states. That proved safety, but it did not leave a first-class, append-only review-outcome artifact for corrections and supersession.

## Decision

Add `HumanReviewOutcomeRecord` as a local candidate artifact. Each budget attempt writes `human_review_outcome.<confirmation_id>.json` and appends the same object to `human_confirmation_history.jsonl` before the budget precondition gate runs.

All outcomes are recorded before the budget precondition gate. Only a `confirmed` outcome bound to the same preflight packet is marked budget-stage eligible, and it still must pass the full budget precondition checks. `unknown`, `needs_more_information`, `human_only`, `declined`, and `declined_or_referred` record a required next gate and block before conflict seed, budget, safety, readiness, or final package output.

## Non-decision

This does not create an interactive reviewer UI, approve budgets, clear conflicts, open matters, or promote a canonical review-outcome contract into Semantic Substrate.

## Authority Impact

This is local candidate-surface work in `LawFirm-os-intake`. Semantic Substrate remains the authority for promoted review outcome contracts and lifecycle policy. Orchestrator remains the future runtime owner for human pauses and approval state.

## Evidence

- `HumanConfirmation` already carries reviewer ID, timestamp, status, decisions, supersession ID, and source-bound evidence refs.
- `BudgetPreconditionReport` already blocks any non-confirmed or evidence-free confirmation before proposal output.
- `docs/human-review.md` requires corrections to append or supersede rather than silently overwrite history.

## Alternatives Rejected

- Use only `human_confirmation.json`: rejected because overwriting a latest confirmation does not prove append-only correction history.
- Put review outcome only in the run ledger: rejected because ledger events are operational; reviewers need a typed artifact with evidence refs and required next gate.
- Allow non-confirmed outcomes to produce partial budget artifacts: rejected because the workflow must fail closed when human confirmation is incomplete or redirects to human-only handling.

## Risks And Rollback

The main risk is artifact proliferation in budget run directories. The change is contained to local JSON/JSONL outputs and schemas. Rollback would remove the outcome record and history file, but that would weaken correction auditability.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/export_schemas.py` - exported 18 schemas.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest` - 42 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check src tests scripts` - all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff format --check src tests scripts` - 41 files already formatted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash scripts/smoke_demo.sh` - completed without error.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/validate_repo.py` - repository validation passed.

## Human Gates

The artifact records reviewer outcomes only. It does not approve representation, conflicts, budget submission, docketing, billing, or matter opening.
