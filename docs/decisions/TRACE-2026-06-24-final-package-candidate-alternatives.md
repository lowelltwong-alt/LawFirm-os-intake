# TRACE-2026-06-24 - Final Package Candidate Alternatives

## Context

The final matter-opening review package showed human-confirmed facts, unknowns, conflict seeds, budget proposal, exceptions, safety gate, blockers, and artifact refs. The top inbound-event, matter-family, representation-posture, and party-role alternatives were visible in the intake review form and JSON packets, but not inline in the final package.

The north-star package should let a lawyer review what was considered and what was confirmed without switching artifacts first.

## Decision

Add a `## Candidate Alternatives` section to `matter_opening_review_package.md` with:

- top inbound-event candidates;
- top matter-family candidates;
- top representation-posture candidates;
- party and role candidates;
- visible source evidence refs and context signals.

The review package completeness report now requires this section before package acceptance.

## Scope

This is a rendering and package-completeness change. It does not make candidates final, change schemas, promote taxonomies, clear conflicts, accept representation, docket deadlines, open matters, bill, submit budgets, create connectors, or write externally.

## Validation

- Review-package tests require candidate alternatives and party-role alternatives in the final Markdown.
- North-star demo tests and smoke checks require the `## Candidate Alternatives` section.
- Completeness metadata requires the section in `required_sections`.
