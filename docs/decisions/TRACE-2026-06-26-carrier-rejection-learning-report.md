# TRACE: Carrier Rejection Learning Candidate Report

## Context

The carrier rejection capture and review slices can now reconcile expected
responses, build remediation cases, surface human review recommendations, and
record red-team notes. The next risk is learning too eagerly: turning rejection
pressure into guideline, budget, template, parser, or preapproval changes before
a human-reviewed outcome exists.

## Decision

Add `CarrierRejectionLearningReport` and the
`propose-carrier-rejection-learning` command.

The command reads `carrier_rejection_review_packet.json` and writes:

- `carrier_rejection_learning_report.json`;
- `carrier_rejection_learning_report.md`.

The report groups recommendation-level learning disposition candidates into
proposal types and target loops. Each proposal carries source structured refs,
before/after candidate behavior, required evaluation, target owner, and the
required gates before the proposal may influence future behavior.

## Boundary

Every proposal remains blocked until human-reviewed rejection outcome evidence
exists. The report performs no profile mutation, template mutation, connector
mutation, Lake write, external submission, or silent learning.

Production connector capture and appeal submission remain Orchestrator-owned.
Append-only outcome admission, SQLite persistence, correction/supersession
records, and record hashes remain Exception Lake-owned. Canonical event or
schema promotion remains Semantic Substrate-owned.

## Validation

- Unit tests cover normal proposal generation, no-candidate behavior, blocked
  review packet behavior, and CLI output.
- Tests assert `silent_learning_performed=false`,
  `profile_mutation_performed=false`, `template_mutation_performed=false`,
  `connector_mutation_performed=false`, and `external_writes_performed=false`.
