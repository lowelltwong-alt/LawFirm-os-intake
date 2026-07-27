# TRACE-2026-06-24 - Context Counterfactual Audit

## Situation

The starter Definition of Done requires practice context to change rankings without changing observed source evidence. The repo had a deterministic unit test for this behavior, but no durable run artifact proving it during smoke.

Because practice context can easily blur into asserted fact, this invariant needs a first-class local audit.

## Decision

Add `ContextCounterfactualAuditReport` and `ContextCounterfactualAuditCheck`, export their schema, and add `scripts/audit_context_counterfactual.py`.

The audit runs the same synthetic source under two practice profiles:

- baseline: `context/synthetic-profiles/insurance-defense.yaml`;
- comparison: `context/synthetic-profiles/plaintiff-personal-injury.yaml`.

It verifies:

- both preflight runs complete as synthetic human-review packets;
- source inventory state, source hashes, and coverage inputs are unchanged;
- segment source IDs, types, structural paths, offsets, and hashes are unchanged;
- observed evidence ref signatures for common matter labels are unchanged;
- the plaintiff profile increases the `plaintiff_personal_injury` candidate score;
- the defense-profile `medical_malpractice_defense` context candidate is `source_anchor_only`, carries context refs, and has only `anchors_matter_family_candidate` graph edges;
- the observed plaintiff candidate keeps `supports_matter_candidate`;
- the explicit `unknown` option remains available for human review.

Wire the audit into `scripts/smoke_demo.sh`.

## Non-decision

This does not promote practice profiles, priors, matter taxonomies, event classes, route IDs, or evidence graph conventions to Semantic Substrate. It does not authorize any legal classification, conflict conclusion, engagement, docketing, matter opening, budget approval, or external write.

## Authority impact

This is a local intake evaluation artifact only. Practice-context canon and promoted taxonomies remain under Semantic Substrate authority. Orchestrator remains the future runtime owner. Intake remains a proving ground and evaluation harness.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 1 file reformatted, then 61 files left unchanged on rerun
- `python -m pytest tests\test_context_counterfactual_audit.py tests\test_context_counterfactual.py -q` - passed
- `python scripts\export_schemas.py` - exported 29 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 82 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - passed
- `python scripts\validate_repo.py` - passed after generated caches were cleaned
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed and wrote starter, blocked-budget, and context-counterfactual audit reports
