# TRACE-2026-06-23 - Python Reference Ingestion Boundary

## Context

The project needs to be ready for high-volume document intake, but adding Rust before profiling would create a second runtime and a larger review burden. The existing Python path already builds source inventory and segments, but there was no single typed artifact that a future Rust adapter would have to match.

## Decision

Add `IngestionResult` and write `ingestion_result.json` during preflight. This artifact contains:

- source inventory;
- source coverage summary;
- structural segments;
- one segment-level `EvidenceRef` per segment;
- an explicit `rust_ready_ingestion_v0_1` parity contract;
- `rust_replacement_allowed=false`.

The preflight packet now references this artifact while preserving the existing `source_inventory.json`, `segments.json`, and CLI behavior.

## Safety Boundary

This does not add Rust, FFI, provider calls, external writes, legal classification, role assignment, matter routing, conflict conclusions, budget decisions, docketing, billing, or matter opening.

The artifact is an implementation and evaluation seam only. It remains subordinate to Semantic Substrate authority and Orchestrator execution ownership.

## Validation

- Unit coverage proves every segment-level evidence ref matches segment source ID, offsets, and hash.
- Unit coverage proves duplicate and missing source states remain visible in the ingestion result.
- Unit coverage proves preflight writes `ingestion_result.json` and keeps legacy segment/source-inventory outputs in sync.
- Unit coverage fails closed when an ingestion evidence ref drifts from the cited segment.

## Follow-Up

If profiling later shows ingestion as the bottleneck, add a Rust adapter behind this boundary and compare its output against `ingestion_result.json` on synthetic fixtures and hidden holdouts before allowing replacement.
