# TRACE: Budget Fixture Update PR Package

Date: 2026-06-26

## Decision

Add a candidate-only package builder that turns accepted fixture-update review
decisions into manual PR instructions without editing fixtures or creating a
GitHub PR.

## Why

The fixture-update review record can say that accepted replay outputs should be
handled in a separate fixture-update PR. The repo still needs a deterministic
handoff artifact that tells a human what to inspect, what target fixture refs are
in scope, what accepted output refs support the change, and what guardrails must
hold before any fixture edit.

## Implemented Surface

- Add `build-budget-fixture-update-pr-package`.
- Add `BudgetFixtureUpdatePRPackageCheck`,
  `BudgetFixtureUpdatePRPackageItem`, and
  `BudgetFixtureUpdatePRPackageReport` local candidate schemas.
- Write `budget_fixture_update_pr_package_report.json`,
  `budget_fixture_update_pr_package_report.md`, and
  `budget_fixture_update_pr_package_items.jsonl` when manual package items
  exist.
- Treat accepted fixture-update review decisions as manual-PR-required package
  evidence.
- Treat rejected or needs-more-information decisions as no-package-needed
  evidence.
- Treat blocked fixture-update review evidence as a blocked package.

## Boundary

This slice creates manual review instructions only. It does not edit fixtures,
create a GitHub PR, apply calibration, apply learning, mutate budgets, profiles,
templates, or carrier guidelines, write Lake/SQLite records, submit budgets,
open matters, or authorize external action.

## Red-Team Notes

- A package item can look like a patch, but it is not a patch application.
- A separate fixture-update PR must preserve superseded evidence instead of
  silently rewriting calibration history.
- Fixture edits still require regression checks, replay checks, shadow eval, and
  owner review before any candidate learning change.
- A package must not be interpreted as approval to mutate carrier guidelines,
  budget math, templates, or profiles.

## Validation Plan

- Test accepted-review, rejected-review, blocked-review, CLI, JSONL item output,
  and no-side-effect boundary flags.
- Export schemas.
- Rerun final readiness, PR checklist, owner-adoption, local-closeout, full
  tests, smoke demo, and repository validation.
