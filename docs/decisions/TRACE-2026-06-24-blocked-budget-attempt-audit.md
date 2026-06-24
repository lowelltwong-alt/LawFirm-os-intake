# TRACE-2026-06-24 - Blocked Budget Attempt Audit

## Situation

The starter release audit proves the successful north-star demo artifacts. The Definition of Done also requires budget generation to be blocked before confirmation, but that fail-closed behavior was mainly evidenced by unit tests and the `BudgetPreconditionReport` generated during negative-path tests.

The workflow needs a durable local artifact proving the starter canary: a non-confirmed human-review outcome must stop before conflict seed, budget proposal, readiness packet, safety gate, or final review package output.

## Decision

Add `BlockedBudgetAttemptAuditReport` and `BlockedBudgetAttemptAuditCheck`, export their schema, and add `scripts/audit_blocked_budget_attempt.py`.

The script uses an already-generated preflight packet, binds the synthetic confirmation template to source evidence, changes the review status to `needs_more_information`, and calls the normal budget workflow. The expected result is a `budget precondition gate failed` exception.

The audit verifies:

- the budget call raised before returning proposal output;
- `budget_precondition_report.json` failed with `budget_blocked_before_human_confirmation`;
- the human review outcome is recorded with `budget_stage_allowed=false` and `collect_missing_information`;
- append-only confirmation history is written;
- no conflict seed, budget proposal, legal budget review form, matter-opening readiness, safety gate, final review package, manifest, completeness report, or budget evidence graph is emitted;
- the blocked precondition exception candidate is dry-run only and not admitted to the Lake;
- the ledger records `budget_generation_blocked` and no post-precondition generation steps.

Wire the audit into `scripts/smoke_demo.sh` after the successful north-star demo audit.

## Non-decision

This does not create a new legal workflow state, canonical event class, route ID, production connector, conflict conclusion, engagement decision, docketing action, budget approval, matter-opening action, Exception Lake admission, or client/carrier submission.

## Authority impact

This is a local intake evaluation artifact only. Orchestrator remains the future runtime owner for human pauses and budget-stage execution. Semantic Substrate remains the authority for promoted state/event contracts. Exception Lake remains the owner of append-only admission and persistence.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 2 files reformatted, then 58 files left unchanged on rerun
- `python -m pytest tests\test_blocked_budget_attempt_audit.py tests\test_confirmation_binding.py -q` - passed
- `python scripts\export_schemas.py` - exported 28 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 80 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - passed
- `python scripts\validate_repo.py` - passed after generated caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed and wrote both starter and blocked-budget audit reports
