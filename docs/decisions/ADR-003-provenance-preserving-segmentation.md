# ADR-003 — Preserve Structural Parent Units Before Token Chunking

**Status:** Accepted

## Decision

Email/document segmentation preserves structural boundaries, offsets, and hashes before any future token subdivision or retrieval indexing.

## Reason

Fixed-token chunking can destroy message authorship, quoted-history boundaries, attachment relationships, and legal document structure. It can also smuggle legal classifications into the chunker.

## Consequence

Segment records contain structure and provenance only. Legal statuses remain candidate or human-review objects.
