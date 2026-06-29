# TRACE-2026-06-29 - CourtListener Dataset And Rust Strategy

## Context

The next roadmap pressure is larger public/synthetic legal-document evaluation, especially CourtListener/RECAP-derived early-case structures. The user also raised a compute concern: if intake grows into large document volumes, Rust may become necessary.

## Decision

Add a local candidate CourtListener early-case dataset strategy and audit. Extend the Rust transition policy candidate scope so future Rust work may cover deterministic public-corpus mechanics in shadow mode.

This remains planning and proof infrastructure only. It does not add a CourtListener adapter, make live calls, ingest public records, create a training pipeline, add a Rust crate, or replace the Python reference path.

## Why

The repo already has a Python ingestion parity oracle and Rust readiness report for source inventory, segmentation, hashing, and evidence refs. The new dataset direction needs the same discipline before public-derived fixtures or high-volume corpus work appear.

## Scope

Added:

- `config/courtlistener-dataset-strategy.yaml`;
- `docs/data/courtlistener-early-case-dataset-strategy.md`;
- `CourtListenerDatasetStrategyReport`;
- `audit-courtlistener-dataset-strategy`;
- tests for offline defaults, prohibited purchase/write paths, labor/employment corpus scope, removal proxy coverage, and Rust shadow boundaries.

## Non-Goals

This does not:

- build a raw PACER/RECAP scraper;
- authorize live CourtListener calls;
- purchase PACER or RECAP Fetch documents;
- upload documents;
- request sealed or restricted material;
- ingest real client or privileged data;
- create a production training pipeline;
- claim budget accuracy from public data;
- add Rust runtime code;
- promote schemas or event classes to Semantic Substrate canon.

## Rust Impact

Rust is allowed only as a future candidate acceleration path for deterministic corpus mechanics such as snapshot normalization, manifest indexing, hashing, duplicate detection, source-span indexing, and label-offset indexing.

Legal classification, role assignment, conflict clearance, matter opening, docketing, budget decisioning, budget submission, training-corpus admission, public-record purchase/download, Exception Lake persistence, and canonical promotion remain outside Rust scope.

## Verification

The new audit fails closed when live calls or purchase paths are enabled and records no external writes. `scripts/export_schemas.py` exports the report schemas for local candidate validation.
