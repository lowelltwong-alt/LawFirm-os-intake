# TRACE 2026-06-30: Owner Issue Draft Quality Audit

## Context

The intake vertical can draft owner-review issue text from cross-repo adoption
packets, but the repo must not create GitHub issues, open PRs, write sibling
repos, promote canon, admit Lake records, write SQLite, or apply learning.
Generated drafts are useful only if humans can trust that they preserve source
evidence, acceptance checks, red-team notes, and manual next gates.

## Decision

Add `audit-owner-issue-draft-quality` as a deterministic local gate over
`cross_repo_owner_issue_draft_report.json`.

The command writes `owner_issue_draft_quality_report.json` and
`owner_issue_draft_quality_report.md`. It checks each ready draft for required
sections, source-evidence labels, suggested labels, required owner actions,
acceptance checks, red-team notes, required next gates, explicit boundary text,
and a Markdown output file that exactly matches the embedded issue body. Blocked
source drafts remain blocked.

## Boundary

The audit is local candidate/eval evidence only. It does not create issues, open
PRs, write sibling repos, promote canonical schemas, event classes, route IDs, or
skill trust records, admit Lake/SQLite records, authorize production use, mutate
baselines, or apply learning.

## Rationale

Manual owner issue creation is a high-risk handoff because copied text can look
official even when it is missing source refs, owner actions, or boundary
warnings. A deterministic audit catches incomplete or tampered drafts before a
human relies on them, while still leaving every external action with the owning
repos.

## Red-Team Notes

- A ready issue draft with missing no-write boundary language must fail closed.
- A Markdown file that exists but does not match the embedded draft body must
  fail closed.
- Relative Markdown output refs must resolve from the source issue draft report
  directory so the audit is not dependent on the caller's current directory.
- A blocked source issue draft must stay blocked even if its Markdown file looks
  complete.
- Invalid source statuses or target-repo drift must fail schema validation.
- The audit must not treat quality readiness as permission to create an issue.
- The audit must not promote local candidate labels, schemas, or event classes.

## Acceptance

- New schema exports cover quality checks, items, and reports.
- CLI output returns exit code `0` only for
  `owner_issue_draft_quality_ready_for_manual_review`.
- Tests cover complete drafts, tampered boundary text, blocked source drafts,
  markdown mismatch, relative output refs, validator drift, and CLI report
  writing.
- The roadmap, evaluation plan, data-flow map, and governance mirror name the
  quality audit as a candidate-only owner handoff gate.
