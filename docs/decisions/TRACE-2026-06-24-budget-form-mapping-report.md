# TRACE-2026-06-24 - Budget Form Mapping Report

## Situation

The intake vertical can render a budget proposal into a UTBMS-style budget workbook, but the fill-existing path needs a durable proof that a carrier-style template is structurally safe before amounts are written into it.

The supplied sanitized workbook is reference material, not a repo fixture. It showed the right UTBMS rows and `Original Budgeted Amount` column, while also exposing why formula validation must happen before any filled workbook is trusted.

## Decision

Add `budget_form_mapping_report.json` for template-backed budget-form rendering.

The report records the template hash, sheet name, header coordinates, total cell, UTBMS code-to-row/write-cell mappings, L/E amount totals, missing/duplicate/unmapped codes, formula checks, and non-submission boundary flags.

Template-backed rendering now builds and enforces the report before writing the filled workbook. If the original-budget total, phase subtotal, task remaining formulas, headers, or budget-code mappings fail validation, rendering blocks and the report remains available for review.

## Non-Decision

Do not commit the sanitized workbook binary. Tests use a committed structural JSON fixture that mirrors the sanitized form layout without private workbook content.

Do not repair carrier formulas in the output copy. This slice validates only.

## Authority Impact

Local candidate/evaluation artifact only. UTBMS remains an `external_code_candidate`; any promoted mapping belongs in Semantic Substrate. Budget submission, carrier delivery, engagement, and matter opening remain out of scope.

## Validation

Coverage includes successful mapping into a sanitized-form-shaped workbook, L/E amount totals, missing phase formula failure, missing budget-code row failure, CLI report emission, schema export, and full repo validation.
