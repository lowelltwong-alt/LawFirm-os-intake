# TRACE: Public Source Methodology Audit

Date: 2026-06-26

## Decision

Add a planning-only public-source methodology audit for Phase 2 research.

## Why

The repo already blocks direct public-reference ingestion, but Phase 2 needs a
stronger review surface before public structures influence synthetic fixture
design. A source being public does not make it safe for runtime ingestion,
identity enrichment, legal conclusions, conflicts work, or budget assumptions.

## Implemented Surface

- `audit-public-source-methodology` command.
- `PublicSourceMethodologySource`, `PublicSourceMethodologyCheck`, and
  `PublicSourceMethodologyReport` candidate schemas.
- Expanded `examples/public/catalog.yaml` with methodology roles, safe uses,
  prohibited uses, required review gates, synthetic-conversion rules, retention
  posture, privacy posture, and `adapter_status=not_authorized`.
- Tests for passing methodology audit, missing required Phase 2 sources,
  direct-ingestion/payload-field blocking, and CLI output.

## Boundary

The audit does not ingest public records, commit public payloads, create a
public-source adapter, authorize Legal Knowledge Runtime use, write Lake or
SQLite records, create external writes, or approve real-data pilots.

## Red-Team Notes

- Public court and public agency records are still real-world matters or events;
  public availability is not a runtime authorization.
- Aggregate/public datasets can overfit synthetic fixture distributions if the
  transformation process is not reviewed.
- Email corpora can stress parsers without representing legal intake,
  privilege, or law-firm attachment patterns.
- A passing audit means only ready for methodology review, not adapter approval.

## Validation Plan

- Export schemas.
- Run focused public-data and public-source methodology tests.
- Run lint, formatting, repo validation, full tests, smoke demo, and front-door
  validators before reporting success.
