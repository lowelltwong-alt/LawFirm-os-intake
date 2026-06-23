# ADR-002 — Human Confirmation Precedes Budget Generation

**Status:** Accepted

## Decision

A legal budget proposal may be generated only after a human confirms matter family, representation posture, and principal party roles.

## Reason

Budget phases, staffing, assumptions, and rates depend materially on the type and posture of the matter. Generating a budget from an unconfirmed classification creates false precision and downstream risk.

## Consequence

The CLI requires a `HumanConfirmation` artifact. The budget remains a proposal and cannot be submitted.
