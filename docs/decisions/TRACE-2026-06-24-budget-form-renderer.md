# TRACE-2026-06-24 - UTBMS Budget Form Renderer

## Situation

The model produces a UTBMS-coded, driver-scaled budget as JSON, but insurance-defense
attorneys deliver budgets on the carrier's UTBMS budget form (Phase/Task rows, an
"Original Budgeted Amount" column, phase subtotals, a grand total). The vertical needed a
way to render the proposal into that form.

## Decision

Add `src/lawfirm_os_intake/budget_form.py` with `render_budget_form(budget, out_path,
template_path=None)`:

- synthetic mode (no template): generate a clean UTBMS workbook mirroring the form layout,
  L-code rows = fees, E-code rows = expenses, phase subtotals and a grand total;
- fill-existing mode (template given): open a copy of an existing UTBMS form, find each
  UTBMS code in the Phase/Task column, and write the amount into the Original Budgeted
  Amount column - leaving the workbook's own subtotal/total formulas intact.

Carry `expense_code` from each fee task to `BudgetLine.expense_code` so the form's E-rows
receive per-category amounts (L330->E115, L340->E119, L160->E121, trial->E116/E117, etc.).
Add a `budget-form` CLI command and the `openpyxl` dependency.

## Non-decision

The form is "Original Budgeted Amount" only and is a proposal:
`not_authorized_for_client_submission` stays true; no submission, conflicts, engagement,
matter opening, or external write. The carrier form has no contingency line, so the form
total is fees + expenses; the model's contingency stays in the JSON proposal. UTBMS codes
remain `external_code_candidate`. The model's per-task math is unchanged - `expense_code`
is recorded but does not alter any amount. The real carrier workbook is not committed;
fill-existing mode targets it at runtime.

## Authority impact

Local rendering in `LawFirm-os-intake`. A UTBMS->canonical mapping, if adopted, is
Semantic Substrate's; submission routing is Orchestrator's.

## Evidence

- The supplied carrier form lays out UTBMS phases/tasks with an Original Budgeted Amount
  column and phase-subtotal/grand-total formulas; the renderer mirrors that layout and,
  in fill mode, preserves those formulas.
- `BudgetLine` already carried `external_code_candidate`; this slice adds the optional
  `expense_code` so expense amounts land on the correct E-rows.
- Tests assert L-amounts sum to `subtotal_fees`, E-amounts sum to `subtotal_expenses`,
  E119 = $30,000 expert vendor, and the form total = fees + expenses.

## Alternatives rejected

- Map expenses to E-codes with a hard-coded L->E table in the renderer: rejected in favor
  of `expense_code` task metadata, which keeps the mapping in the versioned profile.
- Commit the carrier workbook as a test fixture: rejected; the test generates a synthetic
  form and reuses it as the fill template, so no external file is committed.
- Put contingency on the form: rejected; the carrier form has no contingency line.

## Risks and rollback

`models.py`, `budget.py`, `cli.py`, both profiles, and `pyproject.toml` change; the model
field and CLI command are additive and the schema regenerates. Rollback removes
`budget_form.py`, the field, the command, the dependency, and the `expense_code` metadata.

## Validation

Isolated worktree, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- `python scripts/validate_repo.py` -> repository validation passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> already formatted.
- `python -m pytest -q` -> passed (budget-form tests added; existing suite unchanged).
- `python scripts/export_schemas.py` -> legal-budget-proposal schema regenerated with the
  new optional `expense_code` field.
- `bash scripts/smoke_demo.sh` -> passed.

## Human gates

Human confirmation still precedes budget generation. The rendered form is a proposal and
is not authorized for client or carrier submission. Conflicts clearance, engagement
authorization, and matter opening remain separate blockers.
