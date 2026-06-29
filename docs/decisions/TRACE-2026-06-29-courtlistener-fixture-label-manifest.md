# TRACE-2026-06-29 - CourtListener Fixture Label Manifest

## Context

The CourtListener dataset strategy established an offline, labor/employment-first public-derived corpus plan. The next gap was concrete fixture shape: how a docket snapshot, synthetic wrapper, and candidate labels preserve source refs without ingesting public records or creating a training pipeline.

## Decision

Add one synthetic CourtListener-style removal snapshot and a dataset manifest with document-stage, conflict-seed, budget-driver, and person-timeline labels. Add `audit-courtlistener-fixture` to validate the fixture before any future dataset expansion.

## Scope

Added:

- `examples/synthetic/courtlistener-derived/labor-employment-removal-snapshot.json`;
- `examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json`;
- local candidate schemas for snapshot, label source refs, label families, synthetic wrapper, dataset manifest, and fixture audit report;
- CLI audit and regression tests for source-ref hash drift and post-discovery positive-corpus leakage.

## Boundary

This fixture is synthetic. It does not contain real CourtListener records, real party names, real docket numbers, real public payload text, real client data, real matter data, or privileged material.

The audit records:

- no live calls;
- no public-record ingestion;
- no PACER or RECAP Fetch purchase;
- no uploads;
- no court writes;
- no training pipeline;
- no budget accuracy claim;
- no Lake/SQLite writes;
- no external writes.

## Reason

The repo needs source-bound labels before any public-derived or synthetic training/evaluation corpus can be trusted. The fixture proves the shape of labels and refs while staying inside the repo's synthetic-only authority boundary.

## Rejected

- Real CourtListener snapshot now: rejected because public court records are real matters and the repo has no approved public-record ingestion path.
- Live CourtListener adapter now: rejected because the current phase requires offline fixture and schema coverage first.
- Rust implementation now: rejected because this slice only defines deterministic parity targets and review gates.
