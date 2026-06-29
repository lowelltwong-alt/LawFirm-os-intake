# TRACE 2026-06-26 Learning Promotion Readiness

## Decision

Add a local candidate-only shadow-eval plan and promotion-readiness audit for
reviewed learning-gate candidates. The audit creates one blocked shadow-eval case
per candidate and records the proposed change, fixture update, shadow eval,
regression, and owning-repo review gates required before any promotion can be
considered.

## Why

The reviewed learning gate says which signals might justify future learning. The
next safety risk is treating that pressure as a change request. Promotion must
remain blocked until there is a proposed change artifact, synthetic fixture
coverage, a shadow eval result, regression guardrails, and the proper owning repo
review.

## Implemented

- `audit-learning-promotion-readiness` command.
- `LearningShadowEvalCase` and `LearningShadowEvalPlan` candidate schemas.
- `LearningPromotionReadinessCheck` and
  `LearningPromotionReadinessReport` candidate schemas.
- Outputs:
  - `learning_shadow_eval_plan.json`;
  - `learning_shadow_eval_plan.md`;
  - `learning_promotion_readiness_report.json`;
  - `learning_promotion_readiness_report.md`.

## Boundaries

- No proposed change application.
- No baseline mutation.
- No profile, template, connector, budget, or carrier-guideline mutation.
- No Lake or SQLite write.
- No external write.
- No promotion authorization.
- No canonical schema, route, event, or taxonomy promotion.
- No silent learning.

## Required Future Evidence

- Human-reviewed outcome evidence.
- Append-only evidence record.
- Proposed change artifact.
- Synthetic fixture update.
- Shadow eval result.
- Regression check.
- Owning-repo review.
