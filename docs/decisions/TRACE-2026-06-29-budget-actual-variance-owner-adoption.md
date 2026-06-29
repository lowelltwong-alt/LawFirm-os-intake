# TRACE: Budget Actual Variance Owner Adoption

Date: 2026-06-29

## Decision

Add a local candidate owner-adoption package for budget actual-cost variance
evidence. The package consumes `budget_actual_comparison_report.json` and
`budget_actual_variance_ledger_report.json`, then emits owner-specific packets
for Semantic Substrate, Orchestrator, and Exception Lake.

## Why

Budget-to-actual comparison creates useful pressure, but the next steps belong
to different owners:

- Semantic Substrate must decide whether any variance, missing-actuals, or
  actuals-without-budget labels deserve canonical treatment.
- Orchestrator must own any future governed billing-actuals read, human
  follow-up workflow, revised-baseline handling, and evidence packet assembly.
- Exception Lake must own append-only actual-variance admission, idempotency,
  record hashes, supersession, and SQLite migrations.

Keeping this as a local packet prevents intake from quietly becoming a billing
connector, Lake runtime, or learning authority.

## Red-Team Notes

- Missing actuals are source-chain evidence, not proof that a budget was
  accurate.
- Actuals-without-budget may reflect template mapping, scope expansion, or
  billing-code mismatch; it must not collapse into ordinary overrun semantics.
- Phase and code variance events can double-count financial impact unless Lake
  admission defines explicit scope and idempotency.
- Human-revised budgets can hide or amplify variance unless the comparison
  baseline is preserved.
- Variance driver candidates are not learning changes until a reviewed learning
  gate, synthetic fixture update, shadow eval, and owning-repo review exist.

## Boundaries

The implementation performs no billing connector read or write, no GitHub issue
or PR creation, no sibling repo write, no canonical promotion, no Lake/SQLite
admission, no budget/profile/template/guideline mutation, no budget or appeal
submission, and no silent learning.

## Validation

The slice adds deterministic model validation, CLI output, owner-packet tests,
lineage mismatch blocking tests, schema exports, and readiness-audit coverage.
