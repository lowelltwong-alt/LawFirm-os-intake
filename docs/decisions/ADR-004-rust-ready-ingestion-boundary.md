# ADR-004 - Keep Ingestion Rust-Ready Without Adding A Second Runtime Yet

**Status:** Accepted

## Decision

Python remains the reference implementation for the starter workflow. The ingestion hot path must stay portable enough that source inventory, structural segmentation, hashing, and `EvidenceRef` emission can later move to Rust if document volume or constrained compute makes that necessary.

The Rust boundary is narrow:

- input: validated synthetic `SourceBundle` JSON;
- output: `IngestionResult` JSON containing `SourceInventoryItem`, `Segment`, source coverage summary, and source-bound `EvidenceRef` JSON matching the current candidate schemas;
- no legal classification, matter routing, role assignment, conflict conclusion, budget decision, connector write, or authority change inside the Rust layer.

## Required Parity Before Rust Adoption

A Rust implementation must pass golden parity tests against the Python reference for:

- exact source IDs;
- segment IDs or a declared deterministic replacement strategy;
- segment type and structural path;
- parent segment IDs;
- attachment refs;
- start and end offsets;
- SHA-256 hashes;
- prompt-injection source-content flags;
- duplicate and missing-source inventory states;
- serialized schema compatibility.

The Python implementation remains the readable reference until the Rust path proves parity on synthetic fixtures and holdouts.

The starter now emits `ingestion_result.json` as the Python parity oracle under `rust_ready_ingestion_v0_1`.

Preflight runs also emit `rust_ingestion_readiness_report.json`. That report verifies the Python adapter boundary is locked, source inventory rows cover the source bundle, source hashes and character counts recompute, segment offsets stay within source bounds, segment hashes recompute, segment evidence refs match segments, and no legal-decision fields have entered the ingestion artifact. A passing report is only parity-readiness evidence. It does not authorize Rust replacement.

## Preparation Now

Keep the future Rust seam cheap to adopt by preserving:

- schema-first JSON inputs and outputs;
- a typed `IngestionResult` artifact that can be compared across implementations;
- a typed `IngestionVolumeProfile` artifact that records volume pressure, compute pressure signals, required benchmark dimensions, candidate Rust hot-path scope, proposal posture, and required transition gates;
- a typed `RustIngestionReadinessReport` artifact that proves a run is suitable as a future Rust parity target;
- deterministic fixture and holdout coverage for ingestion outputs;
- exact offset/hash validation in the Python reference;
- no hidden Python object state in persisted artifacts;
- adapter selection behind the existing worker/runtime interface.

Do not add a Rust crate, FFI bridge, or dual implementation until profiling shows source inventory, segmentation, hashing, or evidence-ref emission is the bottleneck.

## Reason

Large legal intake bundles may make document walking, hashing, boundary detection, and serialization the dominant cost. Rust is a good future fit for those deterministic mechanics because it can reduce memory overhead, improve throughput, and make bounded concurrency easier to reason about.

The same hot path is also where provenance mistakes are most dangerous. A faster implementation is unacceptable unless it preserves offsets, hashes, source boundaries, and untrusted-data treatment exactly.

## Consequence

When profiling justifies Rust, add it behind an explicit adapter and keep the current Python outputs as the approval oracle.

Any Rust worker remains subordinate to Semantic Substrate contracts and Orchestrator execution authority. It is an implementation detail, not a new LawFirm OS authority plane.
