# TRACE: Public Synthetic Fixture Conversion Review Packet

## Context

The public synthetic fixture conversion plan lists safe structure-only conversion
specs, but a plan is not a human decision. The next risk is that a ready plan
could be mistaken for permission to create fixtures, ingest public records, or
authorize adapters.

## Decision

Add `review-public-synthetic-fixture-conversion`.

The command consumes `public_synthetic_fixture_conversion_plan.json` and writes:

- `public_synthetic_fixture_conversion_review_packet.json`;
- `public_synthetic_fixture_conversion_review_packet.md`;
- `public_synthetic_fixture_conversion_review_decision_template.json`.

The packet gives the reviewer source-by-source recommendations, why-notes,
required human decisions, red-team notes, and append-only decision templates.

## Boundary

This slice is review support only. It does not approve fixture generation,
create fixture PRs, mutate fixtures, ingest public records, commit public
payloads, authorize adapters, write Lake/SQLite records, write sibling repos,
perform external writes, or apply learning.

## Red-Team Notes

- A recommendation is not authorization.
- Public court and public-use datasets can still identify real matters or people.
- Aggregate distributions can become identifying if overfit to rare combinations.
- Email-style fixtures must treat instruction-like text as untrusted synthetic data.
- Fixture generation still requires a separate human-reviewed PR.

## Validation

- Ready conversion plans produce one recommendation and decision template per
  source spec.
- Blocked conversion plans produce no recommendations or decision templates.
- CLI output exposes no-ingestion, no-fixture, no-PR, no-adapter, no-Lake, and
  no-learning flags.
- Final readiness audit now requires this local review-packet surface before PR
  review.
