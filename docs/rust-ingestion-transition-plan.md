# Rust Ingestion Transition Plan

## Purpose

Python remains the reference implementation for intake preflight. Rust is a future implementation option only for high-volume or compute-constrained deterministic ingestion work.

The goal is to make a later Rust adapter cheap to review, not to add a second runtime before profiling proves a bottleneck.

## Approved Boundary

Rust may be proposed only for this hot path:

- source inventory;
- source coverage summary;
- structural segmentation;
- SHA-256 hashing;
- segment-level `EvidenceRef` emission;
- schema-compatible `IngestionResult` JSON serialization.

Rust may run only after the same `DataScopeGateReport` has passed. It must never write raw payload before the data-scope gate, relax synthetic-only checks, or become a separate data-origin authority.

Rust must not own:

- legal classification;
- party-role assignment;
- matter routing;
- deadline docketing;
- conflict clearance;
- engagement decisions;
- budget decisions;
- human confirmation;
- Exception Lake persistence;
- connector or external writes;
- canonical authority changes.

## Current Preparation

Each preflight run writes four Rust-related artifacts:

- `data_scope_gate_report.json`: the upstream synthetic-only gate that must pass before any ingestion worker runs;
- `ingestion_result.json`: the Python parity oracle under `rust_ready_ingestion_v0_1`;
- `ingestion_volume_profile.json`: deterministic source and segment scale signals;
- `rust_ingestion_readiness_report.json`: proof that the run is a valid future parity target.

The local candidate policy lives at `config/rust-ingestion-transition-policy.json`.
It names profiling thresholds, required benchmark dimensions, candidate Rust
hot-path scope, forbidden Rust scope, parity dimensions, and transition gates.
It is not Semantic Substrate canon and does not authorize a Rust runtime.

`ingestion_volume_profile.json` now carries:

- `rust_transition_policy_ref`;
- `decision`;
- `performance_profile_required_before_rust`;
- `compute_pressure_signals`;
- `required_performance_profile_dimensions`;
- `candidate_rust_hot_path_scope`;
- `rust_adapter_proposal_state`;
- `required_rust_transition_gates`;
- `rust_replacement_allowed=false`.

The final review package renders the profile decision, compute pressure signals, required benchmark dimensions, candidate hot-path scope, and transition gates so a reviewer can see when volume pressure exists without opening JSON.

Required performance profile dimensions are intentionally implementation-neutral:

- wall clock time by ingestion stage;
- peak memory;
- characters and sources per second;
- segment count and segment size distribution;
- hashing and segmentation CPU time;
- serialized `IngestionResult` byte size;
- bounded concurrency plan;
- Python-to-Rust parity diff count.

## Transition Gates

A Rust adapter may be proposed only after these gates are satisfied:

- `hot_path_performance_profile`: deterministic ingestion is measured and shown to be the bottleneck;
- `python_reference_golden_parity`: Python output remains the approval oracle;
- `synthetic_fixture_and_holdout_parity`: Rust output matches fixtures and holdouts for offsets, hashes, source states, segment structure, prompt-injection flags, and evidence refs;
- `schema_compatibility_export`: generated JSON validates against exported schemas;
- `orchestrator_adapter_review`: runtime ownership and adapter selection remain with Orchestrator;
- `semantic_substrate_contract_review_if_promoted`: any promoted contract changes go through Semantic Substrate.

Crossing a local volume threshold means profiling is required before a Rust proposal. It does not prove Rust is required and does not authorize replacement.

## Acceptance For A Future Rust PR

A future Rust PR should include:

- a separate adapter behind the existing worker/runtime interface;
- proof that it only runs after a passing `DataScopeGateReport`;
- no production connectors and no external writes;
- golden parity tests against `ingestion_result.json`;
- hidden or holdout parity fixtures, including correspondence dumps with repeated message boundaries;
- schema export and validation;
- a performance profile covering the required dimensions above;
- strict evidence-ref checks for source IDs, segment IDs, offsets, and hashes;
- review-package visibility showing `rust_replacement_allowed=false` until a governed adapter decision changes that outside this repo.

## Rollback

The Python path remains the reference. If a Rust adapter fails parity, remove or disable the adapter and continue using the Python output contract.
