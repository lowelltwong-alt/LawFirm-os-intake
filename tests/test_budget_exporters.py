"""CW3 — exporter plugin seam + firm-Excel renderer.

The structured budget model is the source of truth; Excel is exporter #1. The
firm-Excel exporter matches the sanitized template shape (UTBMS phase/task rows;
Original / Billed / Remaining / New columns) with CORRECTED phase-subtotal and
grand-total formulas, and documents where it deviates from the template. A
round-trip (export -> re-read -> recompute) must reconcile to the model exactly.
"""

import pytest

from lawfirm_os_intake.budget_exporters import (
    FIRM_EXCEL_FORMAT_ID,
    firm_excel_export_from_projection_report,
    get_budget_exporter,
    list_budget_exporters,
    read_firm_excel_task_totals,
)
from lawfirm_os_intake.models import (
    FirmExcelBudgetExport,
    FirmExcelBudgetPhase,
    FirmExcelBudgetTaskRow,
)


def _export_model():
    return FirmExcelBudgetExport(
        export_id="synthetic-firm-excel-export.v0",
        phases=[
            FirmExcelBudgetPhase(
                utbms_phase_code="L100",
                phase_name="Case Assessment, Development and Administration",
                tasks=[
                    FirmExcelBudgetTaskRow(
                        utbms_task_code="L110",
                        task_name="Fact Investigation / Development",
                        original_amount_minor_units=1_200_00,
                        billed_amount_minor_units=200_00,
                        new_amount_minor_units=1_500_00,
                    ),
                    FirmExcelBudgetTaskRow(
                        utbms_task_code="L120",
                        task_name="Analysis / Strategy",
                        original_amount_minor_units=800_00,
                        billed_amount_minor_units=0,
                        new_amount_minor_units=900_00,
                    ),
                ],
            ),
            FirmExcelBudgetPhase(
                utbms_phase_code="L300",
                phase_name="Discovery",
                tasks=[
                    FirmExcelBudgetTaskRow(
                        utbms_task_code="L330",
                        task_name="Depositions",
                        original_amount_minor_units=2_000_00,
                        billed_amount_minor_units=500_00,
                        new_amount_minor_units=2_400_00,
                    ),
                ],
            ),
        ],
    )


def test_export_model_totals_recompute_fail_closed():
    model = _export_model()
    # 1200+800+2000 = 4000.00 original; 200+0+500 = 700.00 billed; 1500+900+2400 = 4800.00 new
    assert model.original_total_minor_units == 4_000_00
    assert model.billed_total_minor_units == 700_00
    assert model.new_total_minor_units == 4_800_00
    dumped = model.model_dump()
    with pytest.raises(ValueError):
        FirmExcelBudgetExport.model_validate(
            {**dumped, "new_total_minor_units": model.new_total_minor_units + 1}
        )


def test_exporter_registry_exposes_firm_excel():
    assert FIRM_EXCEL_FORMAT_ID in list_budget_exporters()
    exporter = get_budget_exporter(FIRM_EXCEL_FORMAT_ID)
    assert exporter.format_id == FIRM_EXCEL_FORMAT_ID


def test_firm_excel_round_trip_reconciles_to_model_exactly(tmp_path):
    model = _export_model()
    exporter = get_budget_exporter(FIRM_EXCEL_FORMAT_ID)
    result = exporter.export(model, tmp_path / "firm-budget.xlsx")

    assert result.format_id == FIRM_EXCEL_FORMAT_ID
    assert result.candidate_only is True
    assert result.external_writes_performed is False
    assert (tmp_path / "firm-budget.xlsx").is_file()

    totals = read_firm_excel_task_totals(tmp_path / "firm-budget.xlsx")
    assert totals["original_total_minor_units"] == model.original_total_minor_units
    assert totals["billed_total_minor_units"] == model.billed_total_minor_units
    assert totals["new_total_minor_units"] == model.new_total_minor_units
    # Per-phase subtotals reconcile too (grand total = sum of phase subtotals).
    assert (
        sum(totals["phase_original_subtotals_minor_units"].values())
        == model.original_total_minor_units
    )


def test_firm_excel_documents_template_deviations():
    model = _export_model()
    exporter = get_budget_exporter(FIRM_EXCEL_FORMAT_ID)
    text = " ".join(model.documented_deviations + exporter.documented_deviations())
    assert "G33" in text  # missing phase-subtotal formulas corrected
    assert "P129" in text  # P85 double-count corrected


def test_firm_excel_has_no_active_or_external_content(tmp_path):
    model = _export_model()
    exporter = get_budget_exporter(FIRM_EXCEL_FORMAT_ID)
    exporter.export(model, tmp_path / "firm-budget.xlsx")
    from zipfile import ZipFile

    with ZipFile(tmp_path / "firm-budget.xlsx") as archive:
        names = archive.namelist()
    forbidden = ("vbaProject", "externalLink", "connections.xml", "oleObject")
    assert not any(any(bad in name for bad in forbidden) for name in names)


def test_firm_excel_export_from_projection_report_keeps_dollars_per_task(repo_root):
    # The role/rate/hours decomposition stays internal; only dollars-per-task export.
    model = firm_excel_export_from_projection_report(repo_root=repo_root)
    assert isinstance(model, FirmExcelBudgetExport)
    assert model.phases
    for phase in model.phases:
        for task in phase.tasks:
            # dollars-per-task only — no role/rate/hours fields on the export row
            assert not hasattr(task, "staffing_role")
    assert model.original_total_minor_units > 0
