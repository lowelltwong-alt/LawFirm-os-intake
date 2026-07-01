# TRACE 2026-07-01: Public Data Cache And UI Foundation

## Decision

Add a governed public-data cache audit and a read-only review UI foundation before generating additional public-derived synthetic fixtures.

## Why

The confidence plan needs public sources for structure and methodology, but public records remain real matters. The repo therefore needs a deterministic proof that any downloaded public sample stays in an ignored local cache, has a source manifest and hash, and cannot become runtime intake input or committed fixture payload by accident.

The UI foundation gives Claude and future design agents stable drop-in paths while keeping the app subordinate to the Python artifact contracts and no-write boundaries.

## Implementation

- Added `PublicDataCacheSourceManifest`, `PublicDataCacheAuditCheck`, and `PublicDataCacheAuditReport`.
- Added `audit-public-data-cache` to validate cache location, manifest schema, catalog source IDs, cache refs, file presence, SHA-256 digests, byte counts, and no-runtime/no-write authority flags.
- Added `apps/legal-intake-budget/` as a static read-only local JSON review surface with a manifest data contract and demo manifest.
- Added tests for cache success/failure paths and UI boundary contracts.
- Updated public-data docs, AI front-door docs, data-flow map, schema exports, and governance mirror surfaces.

## Boundaries

- No public payloads are committed.
- No real party or real matter records are committed.
- No public data runtime ingestion is authorized.
- No fixture files are generated from public payloads in this slice.
- No connector, adapter, GitHub, email, billing, carrier portal, court, SQLite, Exception Lake, budget submission, matter opening, or external write authority is added.

## Follow-Up

The next slice can add deterministic sample download helpers for a tiny allowlisted subset, then run the cache audit as a prerequisite to public-source methodology and conversion-review packets.
