# TRACE 2026-06-26: Cross-Repo Owner Issue Drafts

## Decision

Add `build-cross-repo-owner-issue-drafts` after
`build-cross-repo-owner-adoption`.

The command consumes `cross_repo_owner_adoption_report.json` and writes:

- `cross_repo_owner_issue_draft_report.json`
- `cross_repo_owner_issue_draft_report.md`
- `cross_repo_owner_issue_drafts.jsonl`
- per-owner Markdown and JSON drafts under `owner_issue_drafts/`

## Why

Owner-adoption packets are useful, but the next practical step is issue-shaped
text that a human can inspect and manually create in the owning repos. This
keeps the workflow moving while preserving intake's no-sibling-write boundary.

## Red-Team Notes

- Draft text can be mistaken for created issues.
- A generated title can be mistaken for an owner-approved scope.
- A local issue draft can still overstate production readiness if boundaries are
  missing.
- Creating issues or PRs from intake would become a GitHub/sibling-repo write.
- Owner adoption must still happen in the owning repos after triage.

## Boundary

The command does not create issues, open PRs, write sibling repos, promote
canon, admit Lake records, write SQLite, apply learning, implement connectors,
or authorize production use.

## Tests

- Ready owner-adoption packets produce five ready manual issue drafts.
- Blocked owner-adoption packets produce five blocked issue drafts.
- CLI writes the report, JSONL, Markdown drafts, JSON drafts, and no-write flags.
