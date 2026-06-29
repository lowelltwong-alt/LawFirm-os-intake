# TRACE: Budget Lifecycle Owner Adoption

Date: 2026-06-26

## Decision

Add candidate-only owner adoption packets for the budget lifecycle audit.

## Why

The lifecycle audit shows the whole budget story: human edits, actual-cost
variance, carrier rejections, appeal/financial outcomes, and the Lake bundle.
That proof is useful only if the owning repos can see their exact adoption
responsibilities. Intake should prepare those handoffs without creating issues,
writing sibling repos, implementing connectors, admitting Lake records, or
promoting canon.

## Implemented Surface

- Add `build-budget-lifecycle-owner-adoption`.
- Add `BudgetLifecycleOwnerAdoptionPacket` and
  `BudgetLifecycleOwnerAdoptionReport`.
- Emit owner packets for:
  - Semantic Substrate: semantic contracts, event labels, lifecycle states, and
    correction/supersession semantics.
  - Orchestrator: runtime capture, connector boundaries, human pauses, appeal
    authorization, billing actuals read, and evidence packet assembly.
  - Exception Lake: append-only admission, idempotency, source/support/record
    hashes, correction/supersession, and SQLite migrations.
- Block owner packets when the source lifecycle audit is blocked.

## Boundary

This slice creates local owner-review packets only. It does not create GitHub
issues or PRs, write sibling repos, promote canonical contracts, implement
connectors, admit Lake records, write SQLite, submit budgets or appeals, mutate
budgets/profiles/templates/guidelines, or apply learning.

## Red-Team Notes

- A packet can look like an implementation plan, but it is not owner acceptance.
- Semantic labels must not become canon because they are tidy in one local audit.
- Orchestrator connector work must not inherit authority from intake CLI shape.
- Exception Lake must not treat dry-run report rows as admitted records.

## Validation Plan

- Test ready owner packets for the three required owners.
- Test blocked source lifecycle audit produces blocked packets.
- Test CLI output and no-write/no-connector/no-learning flags.
- Export schemas and run full validation.
