# TRACE-2026-06-23 - Exception Lake Readiness Report

## Context

The workflow emits local `ExceptionLakeCandidate` records for source gaps, prompt-injection source content, critic findings, escalation triggers, budget blockers, unknowns, missing templates, and hours-only missing-rate states. Those records were dry-run candidates, but there was no deterministic report proving candidate files were safe to hand toward a future Exception Lake admission path.

## Decision

Add `ExceptionLakeReadinessReport` and write `exception_lake_readiness_report.json` for:

- preflight exception candidates;
- budget-stage exception candidates combined with preflight candidates;
- failed budget-precondition attempts before the budget workflow raises.

The report verifies dry-run status, raw-payload exclusion, canonical-promotion requirement, known broad Lake class, target runtime repo, support pointer presence, packet-bound evidence refs, and known source inventory refs.

## Safety Boundary

This does not admit records to the Exception Lake, create SQLite tables, promote event classes, define canonical route IDs, mutate schemas in sibling repos, or include raw legal payloads. It remains a local candidate-surface readiness check.

## Authority

Semantic Substrate remains the authority for promoted event classes and route IDs. Exception Lake runtime remains the owner of admission validation, persistence, append-only semantics, record hashing, correction/supersession behavior, and any future SQLite schema.

## Validation

- Preflight writes a passing readiness report for dry-run candidates.
- Budget writes a combined passing readiness report and includes it in the review manifest.
- Failed budget-precondition runs write a readiness report before raising.
- The readiness gate fails closed when a candidate claims raw payload inclusion.
- The readiness gate fails closed when a candidate evidence ref drifts from the packet segment table.
