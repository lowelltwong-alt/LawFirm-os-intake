# TRACE 2026-06-24: Exception Lake Budget Change And Actuals Package

## Decision

The budget stage now emits a dry-run Exception Lake mapping package and a phase-level budget actual-comparison report.

## Rationale

Budget governance needs more than template and calculation checks. Human budget changes must be preserved as append-only or superseding evidence, and budgets must eventually be compared against actual costs by phase. Those signals are valuable Exception Lake evidence, but this intake repo must not become the Lake, a billing connector, or a budget-approval system.

## Implementation

- `exception_lake_mapping_package.json` maps budget template formula failures, missing budget code mappings, unknown budget drivers, guideline/cap issues, human budget changes, and actual-cost variance to broad Lake classes.
- Budget exception candidates now include specific labels for unknown budget drivers and guideline/cap review issues.
- Workbook mapping failures can be converted into dry-run candidates for broken original-budget formulas and missing/duplicate/unmapped UTBMS code rows.
- `budget_actual_comparison_report.json` compares budgeted and actual fees/expenses by phase when synthetic actuals are supplied; normal starter runs record `actuals_not_available`.
- Actual comparison explicitly records `billing_connector_read_performed=false`, `billing_connector_write_performed=false`, and `external_writes_performed=false`.

## Human Budget Changes

Human budget edits should be stored as append-only or superseding records with reviewer, timestamp, proposal/version, target phase/task/code, previous value, new value, reason, and support refs. Intake maps the future `budget_human_change_recorded` evidence family but does not silently mutate proposals or admit Lake records.

## Authority Boundary

This slice is local, synthetic, and non-authoritative. It does not write SQLite, read billing, write billing, submit budgets, approve budgets, create canonical Lake event classes, or promote budget taxonomies. Exception Lake runtime remains the owner of admission, persistence, and audit storage.
