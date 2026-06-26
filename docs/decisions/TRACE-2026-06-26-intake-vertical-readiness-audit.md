# TRACE: Intake Vertical Readiness Audit

Date: 2026-06-26

## Decision

Add a candidate-only final readiness audit for the governed intake-to-budget
vertical.

## Why

The build-out now has many local artifacts: intake gates, budget revisions,
actual-cost comparison, carrier rejection capture/review/learning candidates,
learning gates, proposed changes, shadow evals, owner handoffs, and promotion
package docs. The project needs one deterministic close-out command that says
whether the local candidate evidence is ready for human PR review without
implying production readiness or external adoption.

## Implemented Surface

- `audit-intake-vertical-readiness` command.
- `IntakeVerticalReadinessSliceStatus`,
  `IntakeVerticalReadinessArtifactCheck`, and
  `IntakeVerticalReadinessAuditReport` candidate schemas.
- Required `budget_event_lake_admission_bundle_report.json` input, checked for
  ready-for-owner-review status, artifact refs, record families, and no-write
  boundaries.
- Required `budget_calibration_readiness_report.json` input, checked for manual
  fixture-update review readiness, source refs, approved replay-output refs,
  target fixture refs, and no fixture/calibration/Lake/SQLite/silent-learning
  side effects.
- Required `budget_fixture_update_review_report.json` input, checked for
  append-only local review history, accepted/rejected decision posture, source
  calibration-readiness binding, and no fixture/calibration/Lake/SQLite/silent
  learning side effects.
- Required `budget_fixture_update_pr_package_report.json` input, checked for
  manual PR package posture, source fixture-update review binding, item JSONL
  refs, and no GitHub PR, fixture/calibration/Lake/SQLite/silent-learning side
  effects.
- Add the budget lifecycle audit as a required local slice surface so final
  readiness knows the whole-life budget review command, schemas, tests, and
  trace exist.
- Synthetic reviewed-learning gate fixture used by the proposed-change shadow
  eval chain.
- Tests for ready, missing-local-surface, blocked-learning-chain,
  blocked-Lake-bundle, blocked-calibration-readiness,
  blocked-fixture-update-review, blocked-fixture-update-PR-package, and CLI
  paths.
- Data-flow, endpoint, roadmap, evaluation, and promotion-package updates.

## Boundary

The readiness audit is PR-review evidence only. It does not mark the PR ready,
promote canon, implement connectors, write sibling repos, admit Exception Lake
records, write SQLite, apply proposed learning changes, mutate profiles,
templates, budgets, carrier guidelines, or perform silent learning.

## Recommendation

Use the report as the next human-review checkpoint. If it passes, the easy
remaining work is packaging, reviewer notes, and synthetic fixture expansion.
The critical next work must move to the owning repos: Semantic Substrate for
canon and event labels, Orchestrator for runtime capture/workflow/appeal gates,
and Exception Lake for append-only admission and SQLite migrations.

## Red-Team Notes

- Local readiness can create false confidence if treated as production
  readiness.
- Passing synthetic shadow evals can overfit narrow fixtures.
- A green owner handoff is still only owner-review input; it is not approval.
- A green budget-event Lake bundle is only Exception Lake owner-review input; it
  is not admission, a SQLite write, or a record-hash assignment.
- A green budget calibration readiness report is only manual fixture-update
  review input; it is not approval to mutate fixtures or apply calibration.
- A green budget fixture-update review report can require a separate fixture
  update PR, but it is not that PR and it is not approval to apply calibration
  or learning.
- A green budget fixture-update PR package can guide a separate human PR, but it
  is not a patch, not a GitHub PR, and not fixture-update completion evidence.
- A green budget lifecycle audit summarizes review evidence; it is not connector
  capture, Lake admission, appeal authority, billing authority, or learning
  approval.
- Real budget actuals, carrier rejections, appeals, and guideline drift require
  governed connector capture and append-only evidence storage outside intake.
- Learning from human corrections must remain explicit, reviewed, replayed, and
  owner-approved.

## Validation Plan

- Export schemas.
- Run focused readiness, Lake-bundle, and learning-chain tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
