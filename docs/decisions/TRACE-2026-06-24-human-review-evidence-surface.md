# TRACE-2026-06-24 - Human Review Evidence Surface

## Context

The structured preflight packet, confirmation, conflict seed, budget proposal, evidence graph, and safety gates carried source-bound evidence refs. Some human-facing Markdown review lines still summarized deadlines, missing information, critic findings, and confirmed facts without showing the refs inline.

The north-star demo should let a lawyer see what is known, what is uncertain, and why without first opening the JSON artifacts.

## Decision

Render source refs inline for:

- human-confirmation decision evidence;
- confirmed parties and roles;
- deadline candidates;
- missing-information candidates;
- critic findings;
- existing conflict-search terms and budget supports.

## Scope

This is a human-review rendering change only. It does not change schemas, promote canonical evidence-ref contracts, approve any legal classification, clear conflicts, authorize engagement, docket deadlines, open matters, bill, submit budgets, create connectors, or write externally.

## Validation

- Intake review form coverage requires missing-information evidence refs to render.
- Matter-opening review package coverage requires confirmation evidence, deadline evidence, missing-information evidence, and existing conflict/budget evidence to render.
- North-star smoke coverage requires the final review package to expose human-confirmation decision evidence.
