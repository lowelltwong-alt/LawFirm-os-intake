# TRACE-2026-06-24 - Role Ambiguity Critic

## Situation

The workflow already emitted party-role alternatives with confidence values and source-bound evidence refs. It also produced dry-run Exception Lake candidates for generic critic findings. However, close party-role alternatives could remain visible only as candidate scores, without a specific critic finding or exception/evaluation record.

The v1.0 objective calls out role uncertainty as an exception-aware condition. Reviewers should not have to infer role ambiguity from nearby confidence scores alone.

## Decision

Add a deterministic `ROLE_CANDIDATES_AMBIGUOUS` critic finding when a party has at least two role alternatives whose confidence gap is no more than `0.25`.

The finding:

- names the close role alternatives;
- carries source-bound evidence refs from the role candidates;
- triggers the existing dry-run critic candidate path as `critic_role_candidates_ambiguous`;
- keeps human confirmation mandatory for principal party roles.

## Non-decision

This does not change party-role schemas, confidence math, human confirmation binding, conflict seeds, budget generation, canonical role taxonomy, route IDs, event classes, Exception Lake admission, or external writes.

## Authority impact

This is local intake critic/evaluation behavior. Semantic Substrate remains the authority for canonical role taxonomies and promoted event classes. The Exception Lake runtime remains the future owner for admitted append-only evidence.

## Evidence

- `RoleCandidate` already carries confidence and source-bound evidence refs.
- `CriticFinding` already carries source-bound evidence refs and maps to dry-run `workflow_escalation` candidates when warning or blocker severity is present.
- The misleading-sender/role-ambiguity synthetic holdout already has close role alternatives for carrier/payer and insured/prospective-client review.

## Alternatives rejected

- Leave role ambiguity as score-only context: rejected because exception-aware review should expose uncertainty as an explicit record.
- Add a new role-ambiguity schema: rejected because existing critic and exception candidate contracts are sufficient for this local slice.
- Promote role ambiguity as a canonical Lake event class here: rejected because intake is not a canonical authority plane.

## Risks and rollback

The threshold may produce extra warning candidates in synthetic demos with intentionally close role alternatives. That is acceptable because the output remains a dry-run review/evaluation record and does not block or authorize anything by itself.

Rollback removes the critic block, tests, smoke checks, and docs while preserving role alternatives and generic critic behavior.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 1 file reformatted, 48 files left unchanged
- `python -m pytest tests/test_exception_candidates.py tests/test_source_inventory_and_review.py tests/test_north_star_demo.py -q` - passed
- `python scripts/export_schemas.py` - exported 23 schemas
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 49 files already formatted
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 71 tests
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

## Human gates

This finding preserves human confirmation for matter family, representation posture, and principal party roles. It does not identify the represented client, clear conflicts, accept engagement, open a matter, docket deadlines, approve or submit a budget, admit Exception Lake records, or promote canonical roles.
