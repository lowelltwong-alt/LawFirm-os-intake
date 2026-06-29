# TRACE: Learning Proposed-Change Artifacts

Date: 2026-06-26

## Decision

Add a candidate-only proposed-change artifact layer after the reviewed learning
gate and promotion-readiness audit.

## Why

The learning loop needs a concrete handoff object between "we observed learning
pressure" and "an owning repo may evaluate a behavior change." Without this
layer, a future shadow eval would have to infer the intended change from raw
variance/rejection/correction pressure, which risks silent learning or
overfitting.

## Implemented Surface

- `draft-learning-proposed-changes` command.
- `LearningProposedChangeArtifact`, `LearningProposedChangeRedTeamNote`, and
  `LearningProposedChangeSet` candidate schemas.
- Synthetic fixture under `examples/synthetic/learning/`.
- Tests for reviewer notes, recommendations, red-team objections, owner routing,
  no-candidate handling, and mismatched readiness reports.

## Boundary

The artifacts are reviewer notes and shadow-eval inputs only. They do not apply
proposed changes, mutate baselines, mutate profiles/templates/budgets/carrier
guidelines, write Lake or SQLite records, authorize promotion, or perform
external writes.

## Red-Team Notes

- A single budget edit, carrier rejection, appeal result, or actual-cost
  variance may be an outlier rather than a durable rule.
- Budget math changes can overfit unless uncertainty, resolution path,
  staffing/leverage, carrier caps, and no-submission guardrails are replayed.
- Carrier behavior may be negotiated, matter-specific, stale, or appeal
  dependent; proposed firm math and carrier-compliant projections must remain
  separate.
- Intake cannot approve changes owned by Orchestrator, Exception Lake, or
  Semantic Substrate.

## Validation Plan

- Export schemas.
- Run focused learning tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
