"""Render a budget proposal into a UTBMS litigation budget form workbook.

Two modes:

- synthetic (``template_path=None``): build a clean UTBMS budget workbook that mirrors the
  carrier form layout (Phase/Task rows, an Original Budgeted Amount column, phase
  subtotals, and a grand total);
- fill-existing (``template_path`` given): open a copy of an existing UTBMS budget form,
  locate each UTBMS code in the Phase/Task column, and write the amount into the
  Original Budgeted Amount column - preserving the workbook's own subtotal/total formulas.

The form is "Original Budgeted Amount" only, matching the attorney's fill-out duty. The
carrier form has no contingency line, so the form total is fees + expenses; the model's
contingency stays in the JSON proposal, not the form. The output is a proposal and is not
authorized for submission. ``openpyxl`` is imported lazily so importing this module does
not require it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import BudgetProposal

AMOUNT_HEADER = "Original Budgeted Amount"
TASK_HEADER = "Phase / Task"
_CODE_RE = re.compile(r"\((L\d{3}|E\d{3})\)")

# The UTBMS litigation phase/task and expense code skeleton, in form order.
UTBMS_FORM_ROWS: list[tuple[str, str, str]] = [
    ("L100", "Case Assessment, Development and Administration", "phase"),
    ("L110", "Fact Investigation / Development", "task"),
    ("L120", "Analysis / Strategy", "task"),
    ("L130", "Experts / Consultants", "task"),
    ("L140", "Document / File Management", "task"),
    ("L150", "Budgeting", "task"),
    ("L160", "Settlement / Non-Binding ADR", "task"),
    ("L190", "Other Case Assessment, Development and Administration", "task"),
    ("L200", "Pre-Trial Pleading and Motions", "phase"),
    ("L210", "Pleading", "task"),
    ("L220", "Preliminary Injunctions / Provisional Remedies", "task"),
    ("L230", "Court Mandated Conferences", "task"),
    ("L240", "Dispositive Motions", "task"),
    ("L250", "Other Written Motions and Sanctions", "task"),
    ("L260", "Class Action Certification and Notice", "task"),
    ("L300", "Discovery", "phase"),
    ("L310", "Written Discovery", "task"),
    ("L320", "Document Production", "task"),
    ("L330", "Depositions", "task"),
    ("L340", "Expert Discovery", "task"),
    ("L350", "Discovery Motions", "task"),
    ("L390", "Other Discovery", "task"),
    ("L400", "Trial Preparation and Trial", "phase"),
    ("L410", "Fact Witnesses", "task"),
    ("L420", "Expert Witnesses", "task"),
    ("L430", "Written Motions and Submissions", "task"),
    ("L440", "Other Trial Preparation and Support", "task"),
    ("L450", "Trial and Hearing Attendance", "task"),
    ("L460", "Post-Trial Motions and Submissions", "task"),
    ("L470", "Enforcement", "task"),
    ("L500", "Appeal", "phase"),
    ("L510", "Appellate Motions and Submissions", "task"),
    ("L520", "Appellate Briefs", "task"),
    ("L530", "Oral Argument", "task"),
    ("E100", "Expenses", "phase"),
    ("E101", "Copying", "task"),
    ("E102", "Outside Printing", "task"),
    ("E103", "Word Processing", "task"),
    ("E104", "Facsimile", "task"),
    ("E105", "Telephone", "task"),
    ("E106", "Online Research", "task"),
    ("E107", "Messengers / Overnite", "task"),
    ("E108", "Postage", "task"),
    ("E109", "Local Travel", "task"),
    ("E110", "Out-of-Town Travel", "task"),
    ("E111", "Meals", "task"),
    ("E112", "Court Fees", "task"),
    ("E113", "Subpoena Fees", "task"),
    ("E114", "Witness Fees", "task"),
    ("E115", "Court Reporting & Transcripts", "task"),
    ("E116", "Trial Transcripts", "task"),
    ("E117", "Trial Exhibits", "task"),
    ("E118", "Litigation, Support Vendors", "task"),
    ("E119", "Experts", "task"),
    ("E120", "Private Investigators", "task"),
    ("E121", "Arbitrators / Mediators", "task"),
    ("E122", "Local Counsel", "task"),
    ("E123", "Other Professionals", "task"),
    ("E124", "Other", "task"),
]

# Each phase code mapped to its task codes, for subtotal computation.
_PHASE_TASKS: dict[str, list[str]] = {}
_current_phase = None
for _code, _label, _kind in UTBMS_FORM_ROWS:
    if _kind == "phase":
        _current_phase = _code
        _PHASE_TASKS[_code] = []
    elif _current_phase is not None:
        _PHASE_TASKS[_current_phase].append(_code)


def form_amounts(budget: BudgetProposal) -> dict[str, float]:
    """Amount per UTBMS code: L-codes carry fees, E-codes carry mapped expenses."""

    amounts: dict[str, float] = {}
    for line in budget.lines:
        code = line.external_code_candidate
        if code and code.startswith("L"):
            amounts[code] = round(amounts.get(code, 0.0) + (line.estimated_fees or 0.0), 2)
        expense_code = getattr(line, "expense_code", None)
        if expense_code and line.estimated_expenses:
            amounts[expense_code] = round(
                amounts.get(expense_code, 0.0) + float(line.estimated_expenses), 2
            )
    return amounts


def _phase_subtotals(amounts: dict[str, float]) -> dict[str, float]:
    return {
        phase: round(sum(amounts.get(task, 0.0) for task in tasks), 2)
        for phase, tasks in _PHASE_TASKS.items()
    }


def _build_synthetic_form(budget: BudgetProposal, amounts: dict[str, float], out_path: Path):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    subtotals = _phase_subtotals(amounts)
    grand_total = round(sum(subtotals.values()), 2)

    wb = Workbook()
    ws = wb.active
    ws.title = "Budget Form"
    bold = Font(bold=True)
    ws["A1"] = "BUDGET FORM"
    ws["A1"].font = bold
    ws["A2"] = (
        "Synthetic budget proposal - Original Budgeted Amount only. Proposal for human "
        "review; not authorized for client or carrier submission."
    )
    ws["A3"] = f"Budget proposal id: {budget.budget_proposal_id}"
    ws["A4"] = f"Matter family: {budget.matter_family} | currency: {budget.currency}"

    header_row = 6
    headers = [
        TASK_HEADER,
        AMOUNT_HEADER,
        "Amount Billed to Date",
        "Original Budget Amount Remaining",
        "New Budgeted Amount",
    ]
    for col, text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=text)
        cell.font = bold

    row = header_row + 1
    for code, label, kind in UTBMS_FORM_ROWS:
        if kind == "phase":
            ws.cell(row=row, column=1, value=f"({code}) {label}").font = bold
            ws.cell(row=row, column=2, value=subtotals.get(code, 0.0)).font = bold
        else:
            ws.cell(row=row, column=1, value=f"     ({code}) {label}")
            amount = amounts.get(code)
            if amount:
                ws.cell(row=row, column=2, value=amount)
        row += 1

    total_row = row + 1
    ws.cell(row=total_row, column=1, value="Total Budgeted ($)").font = bold
    ws.cell(row=total_row, column=2, value=grand_total).font = bold
    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 22

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return grand_total


def _fill_existing_form(template_path: Path, amounts: dict[str, float], out_path: Path) -> int:
    from openpyxl import load_workbook

    wb = load_workbook(template_path)
    ws = wb.active
    amount_col: int | None = None
    task_col = 1
    scan_rows = min(ws.max_row, 40)
    for r in range(1, scan_rows + 1):
        for c in range(1, ws.max_column + 1):
            value = ws.cell(row=r, column=c).value
            if not isinstance(value, str):
                continue
            if value.strip() == AMOUNT_HEADER:
                amount_col = c
            elif TASK_HEADER in value:
                task_col = c
        if amount_col is not None:
            break
    if amount_col is None:
        raise ValueError(f"template has no '{AMOUNT_HEADER}' column to fill")

    filled = 0
    for r in range(1, ws.max_row + 1):
        label = ws.cell(row=r, column=task_col).value
        if not isinstance(label, str):
            continue
        match = _CODE_RE.search(label)
        if match is None:
            continue
        code = match.group(1)
        if code in amounts:
            ws.cell(row=r, column=amount_col, value=amounts[code])
            filled += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return filled


def render_budget_form(
    budget: BudgetProposal,
    out_path: str | Path,
    template_path: str | Path | None = None,
) -> Path:
    """Render ``budget`` into a UTBMS budget form workbook at ``out_path``.

    With ``template_path`` the amounts are written into a copy of that existing form;
    without it, a synthetic UTBMS workbook is generated. Only fee/expense amounts are
    written; conflict, engagement, and submission remain out of scope.
    """

    out_path = Path(out_path)
    amounts = form_amounts(budget)
    if template_path is not None:
        _fill_existing_form(Path(template_path), amounts, out_path)
    else:
        _build_synthetic_form(budget, amounts, out_path)
    return out_path
