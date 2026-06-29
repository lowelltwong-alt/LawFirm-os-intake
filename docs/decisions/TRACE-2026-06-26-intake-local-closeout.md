# TRACE 2026-06-26: Intake Local Closeout Audit

## Decision

Add `audit-intake-local-closeout` as the final local closeout artifact for the
current intake build-out branch.

The command consumes:

- `intake_vertical_readiness_audit_report.json`
- `pr_review_checklist.json`
- `cross_repo_owner_adoption_report.json`
- `cross_repo_owner_issue_draft_report.json`

It writes:

- `intake_local_closeout_report.json`
- `intake_local_closeout_report.md`

## Why

The repo now has several end-of-branch proof artifacts. The final closeout audit
keeps the human decision surface small: one report says whether local candidate
evidence is ready and which manual external actions remain.

## Red-Team Notes

- Local closeout readiness can be mistaken for production readiness.
- A passing closeout can be mistaken for marking the PR ready.
- Owner issue drafts can be mistaken for created GitHub issues.
- Sibling repo adoption can be skipped if manual owner gates are not named.
- Lake admission, canonical promotion, runtime adoption, and learning must remain
  owner-controlled.

## Boundary

The command does not mark a PR ready, create issues, open PRs, write sibling
repos, promote canon, admit Lake records, write SQLite, apply learning,
implement connectors, or authorize production use.

## Tests

- Ready evidence chain produces
  `intake_local_closeout_ready_manual_actions_required`.
- Blocked readiness/checklist/owner evidence blocks closeout.
- CLI writes the closeout report and preserves no-write boundary flags.
