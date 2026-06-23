# ADR-004 - Keep Ingestion Rust-Ready Without Adding A Second Runtime Yet

**Status:** Accepted

## Decision

Python remains the reference implementation for the starter workflow. The ingestion hot path must stay portable enough that source inventory, structural segmentation, hashing, and `EvidenceRef` emission can later move to Rust if document volume or constrained compute makes that necessary.

The Rust boundary is narrow:

- input: validated synthetic `SourceBundle` JSON;
- output: `SourceInventoryItem`, `Segment`, and source-bound `EvidenceRef` JSON matching the current candidate schemas;
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

## Reason

Large legal intake bundles may make document walking, hashing, boundary detection, and serialization the dominant cost. Rust is a good future fit for those deterministic mechanics because it can reduce memory overhead, improve throughput, and make bounded concurrency easier to reason about.

The same hot path is also where provenance mistakes are most dangerous. A faster implementation is unacceptable unless it preserves offsets, hashes, source boundaries, and untrusted-data treatment exactly.

## Consequence

Do not add a Rust crate, FFI bridge, or dual implementation until profiling shows the Python path is a bottleneck. When that happens, add Rust behind an explicit adapter and keep the current Python outputs as the approval oracle.

Any Rust worker remains subordinate to Semantic Substrate contracts and Orchestrator execution authority. It is an implementation detail, not a new LawFirm OS authority plane.
