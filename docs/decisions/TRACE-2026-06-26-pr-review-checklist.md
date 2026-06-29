# TRACE 2026-06-26: PR Review Checklist

## Decision

Add a deterministic `build-pr-review-checklist` command after
`audit-intake-vertical-readiness`.

The command consumes `intake_vertical_readiness_audit_report.json` and writes
`pr_review_checklist.json` plus `pr_review_checklist.md`.

## Why

The readiness audit proves local candidate surfaces and generated evidence
chains, but the final PR decision still needs a human-facing checklist that makes
the recommendation, reasons, red-team objections, required decisions, and
validation commands explicit.

## Red-Team Notes

- A ready readiness audit can be stale if generated before the latest commit.
- Local candidate proof can be mistaken for production readiness.
- External owner adoption can be skipped if the checklist does not name it.
- An automated GitHub state change would collapse the human review gate.
- A blocked readiness audit must not be papered over by a friendly checklist.

## Boundary

The checklist does not mark a PR ready, call GitHub write APIs, promote canon,
write sibling repos, admit Lake records, write SQLite, apply proposed changes,
implement connectors, or authorize production use.

## Tests

- Ready readiness audit produces `ready_for_human_pr_review` with no blocking
  items and no-write flags.
- Blocked readiness audit produces `blocked_by_readiness_audit` with a blocking
  item and a keep-draft recommendation.
- CLI writes the checklist artifacts and prints no-write boundary state.
