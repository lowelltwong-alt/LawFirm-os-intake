# TRACE: Public Synthetic Fixture Conversion Plan

## Context

Phase 2 can use public sources only as methodology references. The prior audit
proved the catalog is metadata-only, but it did not yet produce a reviewable
plan for turning public structures into non-identifying synthetic fixtures.

## Decision

Add `plan-public-synthetic-fixture-conversion`.

The command consumes a ready `public_source_methodology_report.json` and writes:

- `public_synthetic_fixture_conversion_plan.json`;
- `public_synthetic_fixture_conversion_plan.md`;
- `public_synthetic_fixture_conversion_specs.jsonl`.

Each spec records target fixture family, allowed structure inputs, forbidden
identity/payload inputs, identity-replacement rules, field transformation rules,
synthetic gold checks, and red-team checks.

## Boundary

This slice is planning-only. It does not ingest public records, commit public
payloads, create or mutate fixture files, authorize adapters, write Lake/SQLite
records, write sibling repos, perform external writes, or permit runtime
public-data use.

## Red-Team Notes

- Public records are still real matters; conversion must not reconstruct cases.
- Aggregate distributions can leak identity if joined back to unique records.
- Email structure tests must treat instruction-like text as data.
- Public structure must not become observed intake evidence.
- Fixture generation requires a separate human-reviewed PR.

## Validation

- Ready methodology reports produce one conversion spec per cataloged source.
- Blocked methodology reports block conversion planning and emit no specs.
- CLI output exposes no-ingestion, no-fixture, no-adapter, and no-Lake flags.
- Final readiness audit now requires this local surface before PR review.
