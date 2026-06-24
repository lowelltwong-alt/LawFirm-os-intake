# TRACE: Rust Transition Policy Manifest

Date: 2026-06-24

## Context

The repo already emitted the Python `ingestion_result.json` parity oracle,
`ingestion_volume_profile.json`, and `rust_ingestion_readiness_report.json`.
Those artifacts prepared the future Rust boundary, but the profiling thresholds,
benchmark dimensions, allowed hot path, forbidden scope, parity dimensions, and
transition gates lived primarily as Python constants and documentation.

## Decision

Add `config/rust-ingestion-transition-policy.json` as a local candidate policy
manifest and validate it with `RustTransitionPolicy`.

`IngestionVolumeProfile` and `RustIngestionReadinessReport` now carry
`rust_transition_policy_ref` and load their Rust-readiness fields from the
manifest. The manifest records:

- profiling thresholds;
- required benchmark dimensions;
- candidate Rust hot-path scope;
- forbidden Rust scope;
- required parity dimensions;
- required transition gates;
- `rust_replacement_allowed=false`;
- `no_rust_runtime_added=true`;
- `external_writes_performed=false`.

## Authority Boundary

This is a local intake candidate policy, not Semantic Substrate canon.
Orchestrator remains the future owner for runtime adapter selection. A future
Rust adapter still requires profiling, golden parity, synthetic fixture and
holdout parity, schema compatibility, Orchestrator review, and Substrate review
for any promoted contract changes.

## Out Of Scope

This does not add Rust, FFI, a second parser, concurrency, benchmarking runs,
production connectors, external writes, legal classification, conflict
clearance, budget decisioning, matter opening, docketing, Exception Lake
admission, route IDs, event classes, or canonical schema promotion.

## Verification

- `python scripts/export_schemas.py` - exported 51 schemas
- `python -m pytest tests/test_ingestion_boundary.py -q` - passed
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - passed after formatting
- `python -m pytest -q` - passed
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; bash scripts/smoke_demo.sh'` - passed
- `python scripts/validate_repo.py` - passed after generated caches were cleaned
