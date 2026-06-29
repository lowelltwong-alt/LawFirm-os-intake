# TRACE: Budget Lifecycle Audit

Date: 2026-06-26

## Decision

Add a candidate-only budget lifecycle audit that ties together the existing
human budget-change ledger, budget actual-variance ledger, carrier rejection
decision ledger, and budget-event Lake bundle.

## Why

The repo already records the three important streams separately: human budget
edits, actual-cost variance, and carrier rejection/fix/appeal pressure. Reviewers
also need one deterministic surface that proves those streams refer to the same
budget/preflight chain, shows the financial picture, and names pending human
decisions before any Exception Lake or learning owner treats the evidence as
usable.

## Implemented Surface

- Add `audit-budget-lifecycle`.
- Add `BudgetLifecycleAuditCheck`,
  `BudgetLifecycleFinancialSummary`, and `BudgetLifecycleAuditReport`.
- Consume `budget_change_ledger_report.json`,
  `budget_actual_variance_ledger_report.json`,
  `carrier_rejection_decision_ledger_report.json`, and
  `budget_event_lake_admission_bundle_report.json`.
- Write `budget_lifecycle_audit_report.json` and
  `budget_lifecycle_audit_report.md`.
- Fail closed on missing artifacts, inconsistent budget/preflight IDs, empty
  lifecycle streams, failed Lake-bundle readiness, missing lifecycle
  record-family coverage, or prohibited write/submission/mutation/silent-learning
  flag drift.
- Preserve pending human decisions and proposed next actions as review content,
  not as authorization for intake to fix, appeal, submit, or learn.

## Boundary

This audit is local candidate review evidence only. It does not implement
connectors, submit appeals or budgets, read or write billing, admit Exception
Lake records, write SQLite, mutate budgets, profiles, templates, or carrier
guidelines, write sibling repos, promote event classes, or apply learning.

## Red-Team Notes

- A green lifecycle audit can be mistaken for Lake admission; it is only
  owner-review input.
- Financial summaries are only as good as the synthetic ledgers they summarize.
- Pending human decisions must not become automatic appeal/fix/learning actions.
- Real actuals and carrier responses require Orchestrator-owned connector and
  evidence-packet contracts before use.

## Validation Plan

- Test ready lifecycle audit over synthetic generated ledgers and Lake bundle.
- Test missing artifact and budget-ID drift failures.
- Test CLI output and no-write/no-learning boundary flags.
- Export schemas, run focused tests, then full validation.
