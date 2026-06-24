# TRACE-2026-06-24-deadline-docketing-guard-report

## Decision

Add a local `DeadlineDocketingGuardReport` artifact to every preflight run and carry it into the final matter-opening review package.

## Context

The starter workflow already extracted date/deadline candidates, rendered them as not docketed, emitted prohibited-transition exception candidates when untrusted source text attempted docketing, and checked `deadline_not_docketed` in the safety gate.

That proof was spread across several artifacts. The v1.0 goal needs a complete review package that proves the workflow never makes unauthorized docketing decisions. Deadline candidates therefore need their own typed local proof that they are source-bound, review-only, and not docketed.

## Change

- Added `DeadlineDocketingGuardItem`, `DeadlineDocketingGuardCheck`, and `DeadlineDocketingGuardReport`.
- Added deterministic report construction and enforcement in `deadline_guard.py`.
- Preflight now writes `deadline_docketing_guard_report.json`.
- Budget package manifests carry `preflight_deadline_docketing_guard_report`.
- The final review package renders deadline guard status, candidate counts, no-docket flags, `human_deadline_review`, candidate evidence refs, and prohibited-transition refs.
- The safety gate verifies the deadline guard report is carried forward.
- The review package completeness report requires the artifact, verifies no docketing was performed or allowed, verifies every candidate remains human-review-only and evidence-bound, and verifies the human-readable package renders the guard.

## Authority Impact

This is a local vertical proof artifact only. It does not promote a Semantic Substrate schema, create a canonical route ID or event class, characterize the legal effect of a deadline, docket a date, write to a calendar/court/docketing system, approve engagement, open a matter, admit an Exception Lake record, or authorize any external write.

The only proposed next gate is `human_deadline_review`.

## Validation

- Unit coverage for preflight artifact creation and source-bound candidate refs.
- Fail-closed coverage for evidence-free deadline candidates.
- Fail-closed coverage when a deadline candidate stops requiring human review.
- Runtime drift coverage when a report is mutated to say docketing occurred.
- Review package coverage for manifest refs, rendered guard lines, and completeness checks.
- Smoke coverage for the north-star demo artifact, rendered guard lines, and completeness check.

## Follow-Up

If this contract is later promoted, the owning Semantic Substrate change should decide the canonical field names, route/event labels, and relationship to Orchestrator's future execution passport. Intake should then consume the promoted contract read-only.
