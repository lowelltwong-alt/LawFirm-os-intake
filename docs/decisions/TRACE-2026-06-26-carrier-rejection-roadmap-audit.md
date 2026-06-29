# TRACE-2026-06-26 - Carrier Rejection Roadmap Audit

## Context

The carrier rejection roadmap now has local candidate slices for capture,
reconciliation, dry-run mapping, human review, learning proposals, Orchestrator
interface drafting, and Exception Lake admission drafting. The next risk is
claiming that intake has completed production adoption simply because the local
candidate lane is broad.

## Decision

Add `audit-carrier-rejection-roadmap`.

The command writes:

- `carrier_rejection_roadmap_audit_report.json`;
- `carrier_rejection_roadmap_audit_report.md`.

The report verifies local proof artifacts and command refs for roadmap slices
1-8, marks the local candidate lane as complete only when those artifacts are
present, and records remaining external adoption work for Orchestrator,
Exception Lake, and Semantic Substrate.

## Boundary

The audit is candidate-only and local-file-only. It performs no connector
implementation, appeal submission, SQLite write, Lake admission, sibling repo
write, external write, canonical route assignment, or canonical event-class
promotion.

## Alternatives Rejected

- Mark the roadmap complete in prose only: rejected because future reviewers need
  a deterministic artifact that fails closed when local proof disappears.
- Implement Orchestrator or Exception Lake behavior from intake: rejected because
  that would violate repo authority boundaries.
- Treat the audit as production readiness: rejected because real-data,
  connector, canonical-promotion, and Lake-admission gates still belong to
  sibling repos and human governance.

## Verification

- Unit tests cover local-complete status, empty-root fail-closed status, JSON/MD
  output, and CLI output.
- Schema export includes the audit report, check, and slice status contracts.
- Documentation updates add the command to the endpoint list, roadmap, and data
  flow map.
