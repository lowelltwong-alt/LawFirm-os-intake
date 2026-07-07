# TRACE 2026-07-06: Rust Tool Ladder

## Status

Accepted as a local candidate-only intake slice.

## Context

Fable's Rust hard-kernel review recommended a promotion ladder before any Rust
replacement work. The repo already had Rust leaf checkers for fixture boundary,
fixture manifest, snapshot coherence, UI bundle source hashes, synthetic identity
guarding, and public-data cache custody. Those tools are useful, but they should
not drift from local QA evidence into runtime authority.

## Decision

Add `config/rust-tool-ladder.json` and `audit-rust-tool-ladder`.

The ladder records:

- stage order from `s0_candidate` through `s4_authoritative`;
- current stage, stage ceiling, review date, scope items, replacement target,
  wrapper/CLI/test refs, current-stage gate evidence, and append-only history
  for each tool;
- existing Rust leaf checkers at `s1_shadow`;
- planned source-inventory and artifact-validator tools at `s0_candidate`;
- no Rust replacement authority, no connector writes, no Lake/SQLite writes, no
  budget/matter authority, and no canonical promotion authority.

The audit fails closed when a tool:

- exceeds its stage ceiling;
- intersects forbidden Rust scope from `config/rust-ingestion-transition-policy.json`;
- lacks required local refs or gate evidence for its current stage;
- moves to `s2_audit` without parity corpus, Python oracle, reviewed frozen
  goldens, and CI wiring when the Rust tool targets replacement of a Python
  path;
- moves higher without adjudication, contract-lock, weekly parity, or Python
  oracle retention evidence.

## Boundary

This slice does not add a Rust ingestion adapter, source inventory Rust port,
artifact validator Rust port, runtime selection, public retrieval, connector,
Lake/SQLite write, budget submission, matter opening, learning promotion, or
canonical authority. Python remains the oracle.

## Validation

Focused validation should include:

```text
python scripts\run_full_pytest.py tests\test_rust_tool_ladder.py tests\test_skills_registry_specialist_review.py -q
python scripts\validate_repo.py
python scripts\export_schemas.py
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
```

Full validation remains:

```text
python scripts\run_validation_suite.py
```

## Follow-Ups

- PR-RS2 may add the source-inventory Rust leaf tool only after parity corpus
  design is accepted.
- PR-RS3 may add a schema-bound artifact validator only after exported schema
  churn and depth/size limits are explicit.
- BK5b headline intensity normalization remains paused until explicit human
  approval.
