# TRACE: Carrier Rejection Human Review Packet

## Context

The rejection reconciliation slice can capture duplicate notices, unlinked notices,
missing expected responses, parser failures, appeal results, and dry-run Exception
Lake candidates. That proves capture pressure, but a reviewer still needs one
human-facing artifact that says what to do next, why, and what could go wrong.

## Decision

Add `CarrierRejectionReviewPacket` and the `review-carrier-rejections` command.
The command reads `carrier_rejection_reconciliation_report.json` and writes:

- `carrier_rejection_review_packet.json`;
- `carrier_rejection_review_notes.md`;
- `carrier_rejection_review_decision_template.json`.

Each remediation case receives a deterministic recommendation, supporting
why-notes, required human decisions, linked dry-run Lake candidate IDs, and a
decision template. The packet also includes red-team checks for duplicate
double-counting, unlinked-source incidents, parser-failure loss, missing-response
capture gaps, learning-loop misuse, and authority-boundary drift.

## Boundary

This is local candidate review hardening only. It does not admit Exception Lake
records, submit appeals, approve budgets, accept write-downs, notify clients or
carriers, mutate guideline profiles, or promote event labels to canon.

Production connector capture and appeal submission remain Orchestrator-owned.
Append-only admission, SQLite persistence, correction/supersession records, and
record hashes remain Exception Lake-owned.

## Validation

- Unit tests cover ready-for-review, blocked-follow-up metadata, and CLI output.
- The review packet preserves `not_authorized_for_lake_write=true`,
  `not_authorized_for_external_submission=true`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.
