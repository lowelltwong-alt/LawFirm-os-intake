# Decision Trace

## Situation

The budget run already wrote a typed `evidence_graph.json` and linked it from the manifest and artifact references. The final human-readable review package still did not summarize that graph, so a reviewer could not quickly see whether the package connected sources, segments, candidates, human confirmation, conflict terms, budget lines, support items, and structured refs.

## Decision

Render `## Evidence Graph Summary` in `matter_opening_review_package.md`.

The section shows the preflight and budget graph refs, graph ID, node count, edge count, node-type counts, relationship counts, and representative provenance edges for human confirmation, party-role candidates, conflict-search terms, budget lines, budget support items, and budget-proposal support.

`ReviewPackageCompletenessReport` now requires the evidence-graph summary section before package acceptance.

## Non-decision

This does not change the graph schema, create a graph database, introduce GraphRAG, promote graph conventions to Semantic Substrate, admit Exception Lake records, clear conflicts, authorize engagement, approve budgets, docket deadlines, open matters, or write externally.

## Authority impact

This is local candidate review-package rendering in `LawFirm-os-intake`. Semantic Substrate remains the authority for promoted evidence graph conventions, Orchestrator remains the future evidence-packet assembly owner, and Exception Lake remains the future append-only admission owner.

## Evidence

- `evidence_graph.json` already exists in both preflight and budget outputs.
- The budget graph already includes `party_role_candidate`, `human_review_outcome`, `conflict_search_term`, `budget_line`, `budget_support_item`, and `structured_ref` nodes.
- Existing tests already prove important graph node and relationship types exist; this change makes those facts visible in the final package.

## Alternatives rejected

- Keep only artifact links: rejected because the north-star package should tell a lawyer what exists and why the workflow is blocked without requiring immediate JSON inspection.
- Add new graph schema fields: rejected because the current graph already carries enough structure for a review summary.
- Move graph ownership into this repo: rejected because this remains a vertical evaluation repo, not the canonical graph/evidence authority.

## Risks and rollback

The risk is a noisier review package. The change is contained to Markdown rendering, package-completeness requirements, tests, smoke checks, and docs. Rollback removes the summary section and required-section entry without changing the underlying evidence graph artifacts.

## Validation

- `python -m ruff format src tests scripts` -> 48 files left unchanged.
- `python -m pytest tests/test_review_package.py tests/test_review_package_completeness.py tests/test_north_star_demo.py -q` -> passed.
- `python scripts/export_schemas.py` -> exported 22 schemas.
- `python -m pytest -q` -> passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> 48 files already formatted.
- `python scripts/validate_repo.py` -> repository validation passed.
- `bash scripts/smoke_demo.sh` in Git Bash could not find `python`; rerun with the local Python path exported passed:
  `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'`.

## Human gates

Human review remains required for conflicts clearance, engagement authorization, budget review, and matter-opening authorization.
