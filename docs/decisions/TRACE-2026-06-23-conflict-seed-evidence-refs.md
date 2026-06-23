# Decision Trace - Conflict Seed Evidence References

## Situation

The intake workflow already required source-bound evidence refs for preflight candidates and human confirmations. The downstream conflict-search seed still allowed normalized search terms to be emitted without their own evidence refs, which made the search packet harder to audit and weaker than the confirmation gate that produced it.

## Decision

Require every `ConflictSearchTerm` to carry source-bound `EvidenceRef` objects from the human confirmation. Conflict seed assembly now fails closed when a term lacks evidence refs.

## Non-decision

This does not clear conflicts, add a conflicts-system connector, create a SQLite Exception Lake store, or promote the local conflict seed schema into Semantic Substrate canon.

This also does not add Rust. Rust remains a future deterministic ingestion acceleration path only after profiling and golden parity justify it.

## Authority Impact

This is local candidate-surface work in `LawFirm-os-intake`. Semantic Substrate remains the authority for any promoted conflict seed contract, route ID, event class, or evidence-ref canon.

## Evidence

- `HumanConfirmation` already carries source-bound decision and confirmed-party evidence refs.
- `BudgetPreconditionReport` already blocks budget generation when confirmations are not evidence-bound.
- `ConflictSeedPacket` preserves `no_conflict_conclusion`.
- ADR-004 keeps high-volume ingestion Rust-ready without moving legal classification or authority decisions into Rust.

## Alternatives Rejected

- Emit search terms without evidence and rely on the parent confirmation: rejected because reviewers and downstream admission checks need term-level provenance.
- Treat aliases as evidence-free reviewer notes: rejected because aliases are still conflict-search terms and must stay reviewable.
- Add a Rust implementation now: rejected because profiling has not shown ingestion as the bottleneck and Python remains the reference oracle.

## Risks And Rollback

The main risk is older local examples that include `normalized_search_terms` without `evidence_refs`. The change is contained to the candidate schema and conflict seed builder. Rollback would restore optional term evidence refs, but that would weaken auditability.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/export_schemas.py` - exported 17 schemas.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest` - 36 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check src tests scripts` - all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff format --check src tests scripts` - 41 files already formatted.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash scripts/smoke_demo.sh` - completed without error.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/validate_repo.py` - repository validation passed.

## Human Gates

Conflict search remains a seed for human or governed conflicts review. It is not a conflict conclusion, engagement decision, or matter-opening authorization.
