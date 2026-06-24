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

Each preflight run writes three Rust-related artifacts:

- `ingestion_result.json`: the Python parity oracle under `rust_ready_ingestion_v0_1`;
- `ingestion_volume_profile.json`: deterministic source and segment scale signals;
- `rust_ingestion_readiness_report.json`: proof that the run is a valid future parity target.

`ingestion_volume_profile.json` now carries:

- `decision`;
- `performance_profile_required_before_rust`;
- `rust_adapter_proposal_state`;
- `required_rust_transition_gates`;
- `rust_replacement_allowed=false`.

The final review package renders the profile decision and transition gates so a reviewer can see when volume pressure exists without opening JSON.

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
- no production connectors and no external writes;
- golden parity tests against `ingestion_result.json`;
- hidden or holdout parity fixtures;
- schema export and validation;
- strict evidence-ref checks for source IDs, segment IDs, offsets, and hashes;
- review-package visibility showing `rust_replacement_allowed=false` until a governed adapter decision changes that outside this repo.

## Rollback

The Python path remains the reference. If a Rust adapter fails parity, remove or disable the adapter and continue using the Python output contract.
