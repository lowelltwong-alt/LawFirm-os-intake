"""PR5: render a budget proposal into a UTBMS budget form workbook (.xlsx)."""

import re

from openpyxl import load_workbook

from lawfirm_os_intake.budget_form import AMOUNT_HEADER, form_amounts, render_budget_form
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight

_CODE_RE = re.compile(r"\((L\d{3}|E\d{3})\)")


def _budget(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, _ = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget


def _fee(budget, code):
    return next(
        line.estimated_fees for line in budget.lines if line.external_code_candidate == code
    )


def _amounts_by_code(ws):
    amount_col = None
    task_col = 1
    for r in range(1, 12):
        for c in range(1, ws.max_column + 1):
            value = ws.cell(row=r, column=c).value
            if value == AMOUNT_HEADER:
                amount_col = c
            elif isinstance(value, str) and "Phase / Task" in value:
                task_col = c
        if amount_col is not None:
            break
    out = {}
    for r in range(1, ws.max_row + 1):
        label = ws.cell(row=r, column=task_col).value
        if isinstance(label, str):
            match = _CODE_RE.search(label)
            if match:
                out[match.group(1)] = ws.cell(row=r, column=amount_col).value
    return out


def test_form_amounts_split_fees_and_expenses(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    amounts = form_amounts(budget)
    l_total = round(sum(v for k, v in amounts.items() if k.startswith("L")), 2)
    e_total = round(sum(v for k, v in amounts.items() if k.startswith("E")), 2)
    assert l_total == budget.subtotal_fees
    assert e_total == budget.subtotal_expenses
    assert amounts["E119"] == 30000.0  # expert vendor (E119) from L340
    assert amounts["L330"] == _fee(budget, "L330")


def test_synthetic_form_has_codes_and_total(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    out = tmp_path / "form.xlsx"
    render_budget_form(budget, out)
    assert out.exists()
    ws = load_workbook(out).active
    by_code = _amounts_by_code(ws)
    assert by_code["L330"] == _fee(budget, "L330")
    assert by_code["E119"] == 30000.0
    total = None
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "Total Budgeted ($)":
            total = ws.cell(row=r, column=2).value
    # The carrier form has no contingency line: form total is fees + expenses.
    assert total == round(budget.subtotal_fees + budget.subtotal_expenses, 2)


def test_fill_existing_form_writes_into_template(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    template = tmp_path / "template.xlsx"
    render_budget_form(budget, template)  # generate a form to reuse as the template
    filled = tmp_path / "filled.xlsx"
    render_budget_form(budget, filled, template_path=template)
    by_code = _amounts_by_code(load_workbook(filled).active)
    assert by_code["L330"] == _fee(budget, "L330")
    assert by_code["E119"] == 30000.0
