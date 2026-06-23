# Decision Trace - Budget-Stage Evidence Graph

## Situation

The preflight evidence graph linked sources, segments, candidates, deadlines, missing-information candidates, and critic findings. The budget-stage graph only added human confirmation and budget proposal nodes, even though conflict-search terms and budget support items now carry evidence refs or structured refs.

## Decision

Extend `evidence_graph.json` after budget generation to include human review outcome, conflict seed packet, conflict search terms, budget lines, budget support items, and structured reference nodes. Add source-backed edges for conflict terms, budget lines, budget support items, and human confirmation evidence.

Also render conflict-search term evidence refs in the matter-opening review package.

## Non-decision

This does not introduce a graph database, GraphRAG, conflict-system connector, budget approval, or canonical graph schema promotion.

## Authority Impact

This is local candidate-surface graph work in `LawFirm-os-intake`. Semantic Substrate remains the authority for any promoted evidence graph conventions, and Orchestrator remains the future runtime owner for evidence packet assembly.

## Evidence

- Conflict search terms require source-bound evidence refs.
- Budget support items require either source-bound evidence refs or structured refs.
- Human review outcomes are now typed and append-only.
- The north-star package already emits a budget-stage `evidence_graph.json`.

## Alternatives Rejected

- Keep budget-stage graph shallow: rejected because the graph would not prove the same evidence links visible in packets and review forms.
- Put all budget provenance only in Markdown: rejected because downstream validation and Lake admission need typed graph evidence.
- Add a graph database now: rejected because the current need is inspectable JSON provenance, not traversal infrastructure.

## Risks And Rollback

The main risk is noisier graph output. The change is contained to local graph assembly and review text rendering. Rollback would remove the added nodes/edges but would weaken auditability of conflict seed and budget support provenance.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/export_schemas.py` - exported 18 schemas.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest` - 42 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check src tests scripts` - all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff format --check src tests scripts` - 41 files already formatted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash scripts/smoke_demo.sh` - completed without error.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/validate_repo.py` - repository validation passed.

## Human Gates

The graph records provenance for review. It does not approve representation, clear conflicts, docket deadlines, submit budgets, bill, or open matters.
