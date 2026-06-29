# TRACE-2026-06-24 - Budget Form Template Audit

## Situation

Template-backed budget rendering now validates a carrier-style UTBMS workbook while rendering, but reviewers also need to test a workbook before any matter-specific budget exists.

The supplied sanitized workbook showed why this matters: the structure can contain the expected UTBMS rows while still having broken original-budget formulas.

## Decision

Add `lawfirm-os-intake budget-form-audit` and `budget_form_template_audit_report.json`.

The audit checks the active worksheet, required headers, UTBMS L/E code rows, original-budget total formula, phase subtotal formulas, and task remaining formulas. It writes a local report and returns nonzero when the template is not safe to trust for rendering.

## Non-Decision

The audit does not repair formulas, fill amounts, create a budget, approve a budget, submit a budget, or mutate the workbook. The workbook remains local; the repo commits only synthetic structural fixtures and docs.

## Authority Impact

Local candidate/evaluation artifact only. UTBMS remains an external code candidate; promoted taxonomy or template policy belongs in Semantic Substrate. Runtime delivery remains Orchestrator scope.

## Validation

Coverage includes passing and failing structural template audits, CLI exit codes, schema export, and a sanity check that the sanitized local workbook currently fails with explicit formula findings.
