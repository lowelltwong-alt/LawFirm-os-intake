# TRACE 2026-07-06: Matter-Link Cluster Review Budget Gate

## Decision

Add an intake-local, candidate-only matter-linking cluster review outcome artifact and make it an optional budget precondition gate. When a matter-linking cluster report is supplied to `build-budget`, budget generation now requires a review outcome confirming exactly one budget-scope cluster with no unreviewed, unknown, held, or conflicted cluster blockers.

## Why

Inbound documents can come from the same sender but belong to different prospective matters. A budget proposal for a mixed bundle can corrupt party roles, conflict-search seeds, budget drivers, and later actuals comparison. The safe behavior is to fail closed until a human review artifact confirms the bundle is one budget scope or splits it before budget generation.

## Authority Boundary

This repo does not assert persistent matter identity, open matters, clear conflicts, write to the Exception Lake, or mutate Orchestrator state. The new artifact is local JSON only, synthetic-only, non-authoritative, append-only, and candidate evidence for later owner adoption.

## Implementation Notes

- `record-matter-linking-cluster-review-outcome` writes the review record, append-only history JSONL, JSON report, and Markdown report under the selected run directory.
- `build-budget` accepts optional `--matter-linking-cluster-report` and `--matter-linking-cluster-review-outcome-report` inputs.
- If matter-linking context is supplied without a confirmed single-cluster review, `budget_precondition_report.json` fails with `matter_linking_confirmation_blocked`.
- Exception candidates include the matter-linking cluster report and review report refs when available.

## Tests

- Confirmed single-cluster review produces no budget, matter-opening, conflict, Lake, SQLite, external-write, or learning side effects.
- Supplying a cluster report without a review outcome blocks before proposal artifacts.
- Supplying a confirmed single-cluster review allows the existing budget path to continue.
- Multi-cluster split review remains blocked for budget scope.
- CLI writes the append-only local review artifacts.
