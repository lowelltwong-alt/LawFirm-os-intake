# TRACE: Learning Shadow-Eval Fixture Evidence

Date: 2026-06-26

## Decision

Add a candidate-only fixture evidence recorder between draft learning proposed
changes and the shadow-eval result harness.

## Why

Static fixture-result files can go stale when proposed-change IDs are generated
from the current learning chain. The repo needs a deterministic way for a human
review record to bind reviewed synthetic evidence to the live
`learning_proposed_change_set.json` without silently applying a learning change.

## Implemented Surface

- `record-learning-shadow-eval-fixture-results` command.
- `LearningShadowEvalFixtureReviewItem`,
  `LearningShadowEvalFixtureReviewRecord`,
  `LearningShadowEvalFixtureEvidenceCheck`, and
  `LearningShadowEvalFixtureEvidenceReport` candidate schemas.
- `run-learning-shadow-eval --fixture-result-report` support.
- Tests for full reviewer-approved evidence, partial evidence, mismatch
  fail-closed behavior, and CLI handoff into shadow eval.

## Boundary

The recorder writes local synthetic evidence only. It does not apply proposed
changes, mutate baselines, mutate profiles/templates/budgets/carrier
guidelines, write Lake or SQLite records, authorize promotion, perform external
writes, or replace owning-repo review.

## Red-Team Notes

- A reviewer could rubber-stamp weak fixture evidence; passing still means only
  ready for owner review.
- Fixture evidence can overfit a narrow synthetic case; owner promotion still
  requires regression and counterfactual review.
- Missing or mismatched proposed-change IDs must block rather than be repaired
  silently.
- The recorder must not become an implicit learning database or Exception Lake.

## Validation Plan

- Export schemas.
- Run focused learning fixture-evidence and shadow-eval tests.
- Run lint, formatting, repo validation, full tests, smoke demo, and front-door
  validators before reporting closeout.
