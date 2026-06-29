# TRACE 2026-06-29: Budget Human Review Outcome Record

## Decision

Add `record-budget-human-review-outcome` as the append-only local proof surface
for human budget lifecycle decisions after `build-budget-human-review-packet`.

## Why

The review packet gives humans recommendations, red-team notes, and decision
templates, but it is not itself a human decision. The budget lifecycle needs a
separate artifact that records what the reviewer actually decided about budget
correction, actual-cost variance follow-up, carrier appeal, write-off, owner
routing, and learning-loop pressure.

## Boundaries

- The record is candidate-only, synthetic-only, non-authoritative, and append or
  supersede only.
- Decisions must bind to packet templates and stay within template-allowed
  outcomes.
- Appeal, reopen, and needs-more-information decisions require owner, due date,
  and follow-up text.
- Owner-routing decisions require a target owner repo.
- Write-off decisions require a financial amount.
- Candidate Lake event labels are emitted for owner review only.
- The command does not submit budgets or appeals, write billing, admit
  Lake/SQLite records, mutate budgets/profiles/templates/guidelines, write
  sibling repos, promote canon, or apply learning.

## Validation

Tests cover append-only history writing, CLI output, unknown-template blocking,
and required appeal follow-up validation.
