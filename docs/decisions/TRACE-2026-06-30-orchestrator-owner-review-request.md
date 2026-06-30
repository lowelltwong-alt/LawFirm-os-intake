# TRACE-2026-06-30 - Orchestrator Owner Review Request

## Context

Orchestrator now has a local `intake prepare-owner-packet` command that accepts
an `intake_owner_review_request.v0_1` payload. Intake already emits many
candidate owner-adoption packets, but it did not yet have a concrete request
artifact that can be handed to that Orchestrator surface without writing a
sibling repo.

## Decision

Add `build-orchestrator-owner-review-request` as a local, synthetic-only request
builder. It consumes the intake preflight packet, human confirmation, budget
proposal, optional budget precondition report, optional actuals comparison, and
optional carrier rejection source/ledger artifacts, then writes:

- `orchestrator_owner_review_request.json`
- `orchestrator_owner_review_request.md`

The JSON uses the exact local Orchestrator workflow label
`orchestrator.local.intake_to_budget_owner_review` and schema version
`intake_owner_review_request.v0_1`.

## Boundary

- The request builder does not call Orchestrator.
- It writes no sibling repos.
- It does not approve, submit, or mutate budgets.
- It does not submit appeals.
- It does not read or write billing, email, carrier portals, Lake, or SQLite.
- It creates no canonical route IDs, event classes, taxonomies, or decision
  authority.

## Red-Team Notes

- A green local request build still may contain pending human pauses and missing
  budget preconditions; those are visible blockers, not failures to hide.
- Carrier source refs must be request-level source refs too, otherwise
  rejection notices can look source-bound while failing Orchestrator inventory
  checks.
- The request normalizes source hashes to bare 64-character SHA-256 only because
  that is the current Orchestrator validator's accepted shape.
- Real carrier notices, real actuals, or production connector outputs remain out
  of scope until Orchestrator and Lake owner contracts approve them separately.

## Validation

Validation is recorded on the implementing PR.
