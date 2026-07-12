# TRACE-2026-07-12 - Cross-Repo Contract Proof

## Context

Intake already built a local `intake_owner_review_request.v0_1` artifact, and
the owner repositories separately exposed synthetic no-write validators. A
matching Pydantic model in Intake was useful but did not prove that the current
merged owner implementations could consume one real synthetic request end to
end.

## Decision

Add `lawfirm-os-intake prove-cross-repo-contract`. It accepts one synthetic
Intake request plus clean local worktrees for Orchestrator and Exception Lake,
then runs this narrow chain:

1. Orchestrator `intake prepare-owner-packet`.
2. Orchestrator `intake build-lake-admission-review-packet`.
3. Exception Lake `validate_intake_lake_admission_review_packet.py`.

The resulting local report records the two owner commits and SHA-256 hashes of
every handoff artifact. The expected success condition is still blocked:
Orchestrator requires owner review and Exception Lake validates only a
candidate admission-review packet.

## Boundary

- Both owner worktrees must be clean and explicitly supplied.
- Outputs must be outside both owner repositories.
- The command accepts synthetic requests without real firm, client, matter, or
  privileged data only.
- It rejects any result that authorizes Lake admission, SQLite writes, raw
  payload storage, external submission, or client use.
- It creates no canonical contract, route, event class, persistent state,
  connector, or sibling-repository write.

## Red-Team Notes

- A passing proof demonstrates only the pinned commit pair. It is a regression
  signal, not owner acceptance or production authorization.
- Dirty owner worktrees can hide uncommitted interface changes, so the command
  fails before invoking either owner CLI.
- The command retains no copied raw source payload. Its report carries paths,
  hashes, statuses, and commit identifiers only.

## Validation

Run the contract proof against clean local owner worktrees, then validate the
reported blocked states and boundary flags. The existing Intake owner-request
tests remain the focused local compatibility coverage.
