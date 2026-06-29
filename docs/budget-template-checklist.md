# Budget Template Checklist

This checklist is for local carrier-style UTBMS workbook templates before they are used with `lawfirm-os-intake budget-form`.

The workbook itself stays outside this repo. Store only synthetic structural fixtures or audit reports here.

## Known-Good Template Requirements

- One active worksheet contains the budget form to audit.
- The worksheet has a `Phase / Task` column.
- The worksheet has an `Original Budgeted Amount` column.
- Every expected UTBMS L/E phase and task code appears exactly once.
- `Total Budgeted ($)` points to a formula cell that sums original-budget phase subtotal cells.
- Each original-budget phase subtotal cell sums that phase's original-budget task cells.
- Task remaining formulas, when present, reference original budget minus amount billed to date.
- The template contains no real client data, real matter data, privileged facts, private negotiated rates, or carrier-submission authorization state.

## Audit Command

```powershell
lawfirm-os-intake budget-form-audit --template "C:\path\to\Budget Template Sanitized.xlsx" --out budget_form_template_audit_report.json
```

A passing report means the workbook is structurally suitable for template-backed rendering. A failed report should be repaired outside this repo and re-audited before rendering.

The audit is local validation evidence only. It does not approve a budget, submit a budget, mutate the workbook, or promote UTBMS to LawFirm OS canon.
