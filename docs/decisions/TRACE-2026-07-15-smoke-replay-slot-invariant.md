# TRACE: Smoke Replay Slot Invariant

## Decision

Replace hard-coded Labor & Employment replay slot counts in the smoke script with
deterministic consistency checks between the execution and builder-binding reports.

## Why

The scoped replay contract reduced the truthful synthetic slot count from 40 to
36. The contract and unit tests changed together, but the integration smoke
script retained the old literal and failed despite a valid replay report.

## Guardrails

- The execution report must have a positive expected slot count.
- Every expected execution slot must be materialized as a candidate slot.
- No runtime artifact may be created.
- The builder-binding slot and bound-slot counts must equal the execution
  report's expected slot count.
- Unknown builder artifacts remain prohibited.

## Scope

This changes only the local synthetic smoke acceptance check. It does not alter
budget calculations, replay source data, authority boundaries, or external
writes.
