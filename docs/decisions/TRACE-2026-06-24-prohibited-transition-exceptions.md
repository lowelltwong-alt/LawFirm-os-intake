# TRACE-2026-06-24 - Prohibited Transition Exceptions

## Situation

The intake workflow already treated hostile source instructions as untrusted data and emitted a generic `prompt_injection_source_content` dry-run Exception Lake candidate. The data-flow map also named prohibited-transition attempts as workflow escalations, but the runtime did not yet emit specific records for those attempts.

The v1.0 goal requires exception-aware handling for prohibited transitions. A reviewer should be able to see exactly which forbidden action was attempted and which source segment supports that finding.

## Decision

Emit specific local `prohibited_transition_attempted_*` dry-run `ExceptionLakeCandidate` records when untrusted source text attempts to:

- clear conflicts;
- open or create a matter;
- create or open an iManage workspace;
- docket deadlines;
- submit a budget;
- send an external message.

Each candidate maps only to the broad `workflow_escalation` Lake class, carries source-bound evidence refs, includes no raw payload, and has a structured ref back to `workflow/prohibited-transitions.yaml`.

## Non-decision

This does not promote new canonical event classes, route IDs, workflow states, schemas, or taxonomies. It does not admit records into the Exception Lake, write SQLite, clear conflicts, accept engagement, docket deadlines, submit budgets, open matters, create workspaces, send messages, or call external connectors.

## Authority impact

This is local intake exception/evaluation behavior. Semantic Substrate remains the authority for canonical route/event promotion. Exception Lake remains the future append-only runtime evidence owner. Orchestrator remains the future runtime handoff owner.

## Evidence

- `workflow/prohibited-transitions.yaml` already declared local forbidden transitions for matter opening, conflicts clearance, budget submission, iManage workspace creation, and canonical semantic change.
- The hostile synthetic fixtures already include source text that attempts conflict clearance, matter opening, iManage creation, docketing, and message sending.
- `ExceptionLakeCandidate` already supports source-bound evidence refs and structured refs without raw payloads.

## Alternatives rejected

- Keep only the generic prompt-injection candidate: rejected because it hides which prohibited transition was attempted.
- Promote new canonical Lake event classes here: rejected because intake is not a canonical authority plane.
- Add connector-specific blockers: rejected because there are no production connectors in this repo and no external writes are in scope.

## Risks and rollback

The risk is overfitting local regex labels to synthetic wording. This is acceptable for the current deterministic fixture/eval layer because the labels are local candidates and remain broad Lake workflow escalations.

Rollback removes the specific prohibited-transition candidate builder, local transition rows, tests, smoke checks, and docs. The generic prompt-injection candidate remains.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 2 files reformatted, 47 files left unchanged
- `python -m pytest tests/test_exception_candidates.py tests/test_prompt_injection_is_data.py tests/test_north_star_demo.py tests/test_no_external_writes.py -q` - passed
- `python scripts/export_schemas.py` - exported 23 schemas
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 49 files already formatted
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 70 tests
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

## Human gates

These candidates are review evidence only. They do not authorize conflicts clearance, engagement, matter opening, iManage creation, docketing, billing, budget submission, external communication, Exception Lake admission, or canonical promotion.
