# TRACE-2026-06-24 - Candidate Source Evidence Status

## Situation

`ScoredCandidate.observed_evidence_refs` served two jobs: direct observed support and packet-binding fallback refs for context-only alternatives or the explicit unknown option. That kept strict evidence validation happy, but it made review text and graph edges risk overstating a practice-context prior as observed source evidence.

The v1.0 goal requires observed evidence to stay separate from practice-context priors and human-confirmed facts. Reviewers should see when a candidate is source-supported, context-influenced, or retained only as an unknown/comparison option.

## Decision

Add `source_evidence_status` to `ScoredCandidate` with three local candidate statuses:

- `observed_support`;
- `source_anchor_only`;
- `unknown_option`.

Keep `observed_evidence_refs` populated for packet binding, strict offset/hash validation, and backwards-compatible schema consumers. Render candidate review lines as `evidence:` only for `observed_support`; render context-only alternatives and unknown options as `source anchor:`. In the evidence graph, use `supports_*` edges only for observed support and `anchors_*` edges for source anchors.

Budget line evidence now comes from the human-confirmed matter candidate only when that candidate has `observed_support`, instead of borrowing the top-ranked matter candidate's refs.

## Non-decision

This does not promote a canonical Semantic Substrate schema, create new route IDs or Lake event classes, change matter taxonomy, add model autonomy, add Rust, alter human confirmation requirements, clear conflicts, approve engagement, open matters, docket deadlines, submit budgets, or write to external systems.

## Authority impact

This is a local intake candidate-contract and review-surface refinement. Semantic Substrate remains the authority for promoted schemas and canonical vocabularies. Orchestrator remains the future runtime owner, and Exception Lake remains the future append-only evidence owner.

## Evidence

- Practice-context docs already state context is a prior, never evidence.
- Counterfactual fixtures show the same source can produce different candidate rankings under different synthetic profiles.
- Strict validation still requires refs to point to real source segments with matching offsets and hashes.

## Alternatives rejected

- Remove fallback refs from context-only candidates: rejected because current strict packet validation and review binding require source refs.
- Treat all fallback refs as evidence: rejected because it blurs observed facts with practice-context priors.
- Promote a canonical status here: rejected because intake is not the platform authority plane.

## Risks and rollback

Older consumers may expect the phrase `evidence:` on every candidate line. That wording was less precise than the data model. Rollback removes the status field, renderer branching, graph anchor edges, tests, schema export, and documentation while preserving existing refs.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 3 files reformatted, then 49 files left unchanged on rerun
- `python -m pytest tests/test_context_counterfactual.py tests/test_source_inventory_and_review.py tests/test_budget_gate_and_math.py tests/test_north_star_demo.py -q` - passed
- `python scripts/export_schemas.py` - exported 23 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 71 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 49 files already formatted
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

Remaining before merge:

- pushed-branch CI.
