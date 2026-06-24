# TRACE-2026-06-24 - Compute-Constrained Rust Readiness

## Situation

The project may eventually receive large document intake batches where Python remains correct but deterministic ingestion becomes expensive under constrained compute.

The repo already had a Python ingestion parity oracle and Rust transition gates. It still needed a clearer artifact-level way to show when compute pressure exists and what must be measured before Rust is proposed.

## Decision

Extend `IngestionVolumeProfile` with:

- `compute_pressure_signals`;
- `required_performance_profile_dimensions`;
- `candidate_rust_hot_path_scope`.

For starter-scale runs, `compute_pressure_signals` stays empty and the decision remains `keep_python_reference`.

For profile-candidate runs, the profile records threshold-crossing pressure and requires benchmarking before a Rust adapter proposal. Required dimensions include wall clock time by ingestion stage, peak memory, characters and sources per second, segment distribution, hashing and segmentation CPU time, serialized artifact size, bounded concurrency plan, and Python-to-Rust parity diff count.

The final review package renders these fields so reviewers can see the Rust posture without opening JSON.

## Non-decision

This does not add Rust, a second runtime, FFI, Rayon, async ingestion, production connectors, model calls, legal classification, conflict clearance, matter opening, docketing, billing, budget approval, Exception Lake persistence, or platform canon.

## Authority impact

Rust remains a possible deterministic implementation adapter for source inventory, coverage summary, structural segmentation, hashing, evidence-ref emission, and schema-compatible `IngestionResult` serialization only.

Semantic Substrate remains the authority for promoted contracts. Orchestrator remains the future runtime owner for adapter selection.

## Validation

Unit tests assert starter-scale runs expose no compute pressure while still carrying benchmark dimensions and candidate hot-path scope. High-volume proxy tests assert profile-candidate runs emit compute pressure signals and still keep `rust_replacement_allowed=false`.

Review-package and smoke checks require the new Rust-readiness fields to remain visible.
