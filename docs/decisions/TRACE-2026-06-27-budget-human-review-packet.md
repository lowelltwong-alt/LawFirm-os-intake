# TRACE 2026-06-27: Budget Human Review Packet

## Decision

Add `build-budget-human-review-packet` as the Phase 6D human review surface for
budget lifecycle evidence.

The command consumes:

- `budget_lifecycle_audit_report.json`
- optional `budget_revision_report.json`
- optional `budget_actual_comparison_report.json`
- optional `carrier_rejection_review_packet.json`
- optional `carrier_rejection_learning_report.json`

It writes:

- `budget_human_review_packet.json`
- `budget_human_review_packet.md`
- `budget_human_review_decision_templates.json`

## Why

The repo already has separate evidence streams for human budget revisions,
actual-cost variance, carrier rejections, appeal outcomes, Lake handoff, and
learning pressure. Reviewers need one packet that shows the recommendation, why,
red-team objections, financial summary, and allowed append-only decisions before
any owner handoff or future runtime action is trusted.

## Red-Team Notes

- A consolidated packet can be mistaken for budget approval or appeal approval.
- Proposed and carrier-compliant numbers can collapse unless the reviewer sees
  the boundary explicitly.
- Actual variance can be compared against the wrong scenario.
- Duplicate carrier rejection notices can double-count disputed dollars.
- Learning pressure can silently mutate profiles, templates, budgets, carrier
  guidelines, or validation rules if append-only outcome gates are skipped.
- Lake handoff can be mistaken for Lake admission.

## Boundary

The packet is local review evidence only. It does not submit budgets or appeals,
write billing, admit Lake records, write SQLite, mutate budgets, profiles,
templates, or carrier guidelines, write sibling repos, promote canon, or apply
learning.

## Tests

- A ready lifecycle audit with optional source reports produces a ready human
  packet with recommendations, why-notes, red-team notes, and decision
  templates.
- A blocked lifecycle audit produces a blocked packet.
- CLI output preserves no budget submission, no appeal submission, no Lake or
  SQLite write, no mutation, and no silent-learning flags.
