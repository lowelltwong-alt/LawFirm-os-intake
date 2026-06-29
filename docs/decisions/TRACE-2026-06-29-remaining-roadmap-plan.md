# TRACE-2026-06-29 - Remaining Roadmap Plan

## Context

The intake build-out now has local readiness, PR checklist, owner-adoption,
owner issue-draft, local closeout, and PR readiness decision surfaces. Reviewers
still need one compact, typed answer to "what next?" that separates easy
human/local actions from critical owner-gated work.

## Decision

Add `plan-remaining-roadmap`, a local candidate-only command that consumes:

- `intake_vertical_readiness_audit_report.json`;
- `intake_local_closeout_report.json`;
- optional `pr_readiness_decision_report.json`.

It writes:

- `remaining_roadmap_report.json`;
- `remaining_roadmap_items.jsonl`;
- `remaining_roadmap_report.md`.

The report names workstream, owner, effort, risk, gate, status, source evidence,
required next actions, acceptance evidence, red-team notes, required gates, and
next recommended item IDs.

## Boundaries

- No GitHub PR state change.
- No GitHub issue or PR creation.
- No sibling repo write.
- No Semantic Substrate promotion.
- No Orchestrator runtime adoption.
- No Exception Lake or SQLite write.
- No real-data pilot approval.
- No proposed-change application.
- No silent learning.

## Rationale

Human reviewers need an execution map, but intake is not the authority for most
remaining work. A typed roadmap makes the easy pieces visible while forcing
critical items through owner repo review, governance approval, production pilot
approval, and cross-repo validation.

## Red-Team Notes

- Local readiness can be mistaken for production readiness if the roadmap omits
  owner gates.
- Manually creating every generated issue draft can overload owner repos without
  triage.
- Real-data pilot work is the most tempting shortcut and must stay deferred
  until cross-repo governance approves data classes, retention, access controls,
  connector boundaries, Lake admission, and shadow-mode gates.
- Critical items must never be gated only by local candidate or manual PR review.

## Acceptance

- Ready source evidence produces `remaining_roadmap_ready_manual_execution_required`.
- Failed readiness or closeout evidence blocks the roadmap report.
- The report distinguishes easy, medium, large, critical, owner-gated, and
  local/human-gated items deterministically.
- The CLI writes JSON, JSONL, and Markdown outputs without external writes.
- The readiness audit includes the command, schemas, tests, and this decision
  trace as a local candidate slice.
