# TRACE: Learning Shadow-Eval Results

Date: 2026-06-26

## Decision

Add a candidate-only shadow-eval result harness after the proposed-change
artifact layer.

## Why

The learning loop needs a deterministic gate that distinguishes "a proposed
change exists" from "synthetic eval evidence supports this change." Without this
gate, roadmap language could make draft proposals look ready for promotion
before fixture evidence, guardrail replay, and owner review exist.

## Implemented Surface

- `run-learning-shadow-eval` command.
- `LearningShadowEvalFixtureResult`, `LearningShadowEvalResult`, and
  `LearningShadowEvalResultReport` candidate schemas.
- Synthetic fixture results under `examples/synthetic/learning/`.
- Tests for passing owner-review-required results, missing fixture blocking,
  failed guardrails/evals, CLI output, and fixture mismatch fail-closed behavior.

## Boundary

The result harness does not apply proposed changes, mutate baselines, mutate
profiles/templates/budgets/carrier guidelines, write Lake or SQLite records,
authorize promotion, perform external writes, or replace sibling-repo review.

## Red-Team Notes

- A synthetic passing result proves only that a local fixture replay matched its
  declared checks; it is not production readiness.
- Missing fixture evidence must block rather than pass by absence.
- Failed eval suites or regression guardrails must fail the report even if other
  candidates pass.
- Cross-repo owners still control promotion decisions and runtime adoption.

## Validation Plan

- Export schemas.
- Run focused learning tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
