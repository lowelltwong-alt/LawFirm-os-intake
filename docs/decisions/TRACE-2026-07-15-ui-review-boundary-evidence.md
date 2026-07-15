# TRACE: Explicit UI Review Boundary Evidence

## Decision

The read-only review workbench may show only local candidate artifacts, but the
presence of a JSON file is not proof that its safety boundary is intact. Each
present detail report must therefore carry explicit evidence that it is
candidate-only, either synthetic-only or metadata-only, and that it performed
no external writes. The serialized aggregate bundle must also explicitly carry
its own boundary fields; Pydantic defaults cannot be used as evidence.

The fixture refresher derives its aggregate `boundary_evidence_complete` marker
only from those explicit detail fields. A missing core field blocks the bundle.
Malformed bundles produce a deterministic failed refresh report without writing
fixture changes or running Rust gates.

Crosswalk and OCG evidence retain stronger, report-kind-specific checks. Their
raw payload must explicitly demonstrate the candidate and no-authority flags
that make the artifact read-only evidence rather than canonical or executable
business logic.

## Why

The workbench is intended to make uncertainty, blocked actions, and evidence
visible. Treating omitted booleans or model defaults as proof would make an
incomplete artifact look review-ready. The resulting false confidence is more
dangerous than a visible blocked review surface.

## Scope And Boundaries

This applies to the local UI review bundle and its checked synthetic demo
fixtures. It does not grant authority to ingest source records, write to a
carrier portal, send email, create a matter, submit a budget, make a conflict
conclusion, write the Exception Lake, or promote any candidate schema to
Semantic Substrate canon.

It does not apply to source-authority or canonical-contract validation, which
remain owned by their respective OS repositories.

## Tests

- Missing detail boundary declarations block bundle readiness.
- Missing top-level serialized bundle boundary declarations fail validation.
- Metadata-only local evidence remains explicitly reviewable without being
  claimed as synthetic payload.
- Crosswalk and OCG raw payloads missing required no-authority flags block the
  bundle.
- The fixture refresher reports malformed detail evidence as failed without
  mutating the checked fixture.

## Validation

Run the governed focused UI tests, schema export, frontend build and browser
smoke, then `python -B scripts/run_validation_suite.py` with its long timeout.
