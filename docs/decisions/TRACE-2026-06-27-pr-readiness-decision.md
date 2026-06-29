# TRACE 2026-06-27: PR Readiness Decision Record

## Decision

Add a deterministic `record-pr-readiness-decision` command after
`audit-intake-local-closeout`.

The command consumes:

- `pr_review_checklist.json`
- `intake_local_closeout_report.json`
- a human-authored PR readiness decision JSON

It writes:

- `pr_readiness_decision_record.json`
- `pr_readiness_decision_history.jsonl`
- `pr_readiness_decision_report.json`
- `pr_readiness_decision_report.md`

## Why

The PR checklist and local closeout report show that local candidate evidence is
ready for human review, but they do not record the human's actual PR decision.
This slice gives the branch an append-only local decision record without
collapsing the manual GitHub state-change gate.

## Red-Team Notes

- A mark-ready decision can be mistaken for a completed GitHub PR state change.
- A keep-draft decision can be lost if only the current report is inspected and
  not the append-only history.
- A stale checklist or closeout report can make a decision look better than the
  current branch state.
- Owner issue drafts can still be mistaken for created GitHub issues.
- Local PR readiness can still be mistaken for production readiness or sibling
  repo adoption.

## Boundary

The command records local human PR readiness evidence only. It does not mark a
PR ready, call GitHub write APIs, create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply proposed changes,
implement connectors, or apply learning.

## Tests

- Mark-ready decisions require every checklist item and validation evidence,
  then report that a manual GitHub ready action remains required.
- Keep-draft decisions require followups and do not require a manual ready
  action.
- Incomplete mark-ready decisions fail closed.
- CLI output preserves no-write and no-learning boundary flags.
