# TRACE: Public Synthetic Fixture Conversion Review Outcome

## Context

The public synthetic fixture conversion review packet gives humans recommendations
and decision templates, but a packet is not a decision. Without an append-only
outcome record, fixture-generation planning could mistake review readiness for
approval.

## Decision

Add `record-public-synthetic-fixture-conversion-review`.

The command consumes `public_synthetic_fixture_conversion_review_packet.json`
and an explicit human decision JSON, then writes:

- `public_synthetic_fixture_conversion_review_record.json`;
- `public_synthetic_fixture_conversion_review_history.jsonl`;
- `public_synthetic_fixture_conversion_review_outcome_report.json`;
- `public_synthetic_fixture_conversion_review_outcome_report.md`.

The record binds the reviewer outcome to the review packet, conversion plan,
source, conversion spec, decision template, evidence refs, required gates,
reasons, followups, and any supersession ref.

## Boundary

Approved outcomes mean only that a separate reviewed fixture-generation PR is
required if humans choose to proceed. Recording the outcome does not create
fixtures, create PRs, ingest public records, commit raw public payloads,
authorize adapters, write Lake/SQLite records, perform external writes, or apply
learning.

## Red-Team Notes

- A ready review packet can be mistaken for approval unless the decision is
  separate and append-only.
- An approval outcome can be overread as fixture-generation authority unless the
  report preserves `fixture_generation_authorized=false`.
- Public records are real matters; identity reconstruction and payload
  contamination checks still belong in the later fixture PR review.
- Future Lake admission, if accepted, belongs in the Exception Lake runtime repo,
  not this intake repository.

## Validation Plan

- Test approved outcome recording with all required gates and no mutation/write
  flags.
- Test needs-more-information recording with required followups and no fixture
  PR requirement.
- Test approval without required gates fails closed.
- Test unbound source/spec decisions fail closed.
- Export schemas for the record, checks, and outcome report.
