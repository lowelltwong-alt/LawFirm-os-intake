# TRACE-2026-06-24 - Rust Ingestion Readiness Report

## Context

High-volume legal intake may eventually make deterministic document walking, source inventory, structural segmentation, hashing, and evidence-ref emission expensive enough to justify a Rust implementation. The repository already had a Python reference `IngestionResult` parity oracle, but there was no per-run report proving that a generated artifact was suitable as a future Rust comparison target.

## Decision

Add `RustIngestionReadinessReport` and write `rust_ingestion_readiness_report.json` during preflight.

The report verifies:

- the current adapter remains `python_reference_ingestion_adapter`;
- the parity contract is `rust_ready_ingestion_v0_1`;
- `rust_replacement_allowed=false`;
- source inventory rows cover the source bundle;
- source hashes and character counts recompute from source text;
- segment offsets stay within source bounds;
- segment hashes recompute from segment text;
- segment evidence refs match segment source IDs, offsets, and hashes;
- ingestion output contains no legal classification, party-role, conflict, budget, or human-confirmation scope.

## Scope

This adds a readiness artifact, schema export, smoke check, tests, and documentation. It does not add Rust, FFI, concurrency, a second parser, model calls, connector writes, legal classification, conflict clearance, budget approval, Exception Lake persistence, or platform canon.

## Alternatives Considered

- Add a Rust crate now: rejected because profiling has not shown ingestion as the bottleneck and a second runtime would increase review burden.
- Leave Rust readiness as documentation only: rejected because future parity needs machine-checkable evidence, not prose.
- Let Rust own broader extraction or classification: rejected because legal meaning, role classification, conflict conclusions, budget decisions, and authority policy remain outside the ingestion hot path.

## Validation

- Unit coverage proves normal preflight emits a passing readiness report.
- Unit coverage proves source hash drift fails the readiness report and enforcement.
- Smoke coverage requires the readiness report in the north-star demo.
