# TRACE: Budget Fixture Update Review Record

Date: 2026-06-26

## Decision

Add a candidate-only fixture-update review recorder after budget calibration
readiness.

## Why

Calibration readiness proves that approved synthetic replay outputs are ready
for manual fixture-update review. It does not record the actual human decision
about whether those outputs should be accepted, rejected, corrected, or held for
more information. The workflow needs an explicit review artifact before any
separate fixture-update PR can be considered.

## Implemented Surface

- Add `record-budget-fixture-update-review`.
- Add `BudgetFixtureUpdateReviewRecord`, `BudgetFixtureUpdateReviewCheck`, and
  `BudgetFixtureUpdateReviewReport` local candidate schemas.
- Write `budget_fixture_update_review_record.json`,
  `budget_fixture_update_review_history.jsonl`,
  `budget_fixture_update_review_report.json`, and Markdown notes.
- Validate that accepted output refs and target fixture refs are bound to the
  supplied `budget_calibration_readiness_report.json`.
- Record accepted decisions as requiring a separate human-reviewed fixture-update
  PR, without creating the PR or mutating fixtures.

## Boundary

This slice records local review evidence only. It does not update fixtures,
create a PR, apply calibration, apply learning, mutate budgets, profiles,
templates, or carrier guidelines, write Lake/SQLite records, submit budgets,
open matters, or authorize external action.

## Red-Team Notes

- A reviewer acceptance can be misread as learning approval. It is not.
- A fixture-update PR can accidentally encode a bad replay output as reviewed
  gold if the output and target fixture are not inspected together.
- Rejected or needs-more-information decisions must remain first-class evidence,
  not be overwritten by a later acceptance without a superseding record.
- Accepted fixture-update decisions still require regression checks, shadow eval,
  and owner review before any candidate learning changes.

## Validation Plan

- Test accepted, rejected, blocked-readiness, CLI, history, and unbound-ref
  paths.
- Export schemas.
- Rerun final readiness, PR checklist, owner-adoption, local-closeout, full
  tests, smoke demo, and repository validation.
