"""CW7 — hostile-fixture sweep: every new serialized artifact fails closed on tamper.

Applies the workbench trust-suite methodology to the CW1-CW6 artifacts: build a
valid instance, tamper one reconciled field, and assert model_validate rejects it.
"""

import pytest

from lawfirm_os_intake.case_sizing import (
    CASE_SIZING_POLICY_REF,
    build_case_sizing_report,
    load_case_sizing_policy,
    rank_settlement_postures,
)
from lawfirm_os_intake.firm_checkpoint import build_firm_checkpoint_packet
from lawfirm_os_intake.guidelines import (
    build_carrier_compliant_projection,
    load_carrier_guideline,
    select_pack,
)
from lawfirm_os_intake.models import (
    AdjustmentLedger,
    BudgetProposal,
    CaseSizingReport,
    FirmCheckpointPacket,
    FirmExcelBudgetExport,
    OCGContractReconciliationReport,
    PackSelectionDecision,
    ProportionalityAssessment,
    RouterEvaluationReport,
    SettlementPostureAnalysis,
    SettlementPostureInput,
    SizedWorkPlan,
)
from lawfirm_os_intake.ocg_contract_reconciliation import build_ocg_contract_reconciliation_report
from lawfirm_os_intake.routing_eval import build_router_evaluation_report
from lawfirm_os_intake.util import load_json

_BUDGET_REF = "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"


def _budget(repo_root):
    return BudgetProposal.model_validate(load_json(repo_root / _BUDGET_REF))


def _projection(repo_root):
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    return build_carrier_compliant_projection(
        _budget(repo_root),
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id="synthetic-carrier-a",
    )


def _sizing(repo_root):
    policy = load_case_sizing_policy(repo_root / CASE_SIZING_POLICY_REF)
    return build_case_sizing_report(
        case_type="premises_liability",
        base_work_plan_total_minor_units=1_000_000,
        drivers={
            "party_count": 2,
            "injury_severity": "surgical",
            "liability_clarity": "disputed",
            "exposure_band": "medium",
            "venue": "state_default",
        },
        posture_input=SettlementPostureInput(
            exposure_minor_units=1_000_000,
            settlement_value_minor_units=60_000,
            settlement_value_after_defense_minor_units=90_000,
            win_probability_percent=45.0,
            defense_cost_settle_now_minor_units=25_000,
            defense_cost_defend_settle_minor_units=180_000,
            defense_cost_try_minor_units=520_000,
        ),
        policy=policy,
        generated_at="2026-07-23T00:00:00Z",
    )


def _assert_tamper_rejected(model_cls, payload, field, value):
    tampered = {**payload, field: value}
    with pytest.raises(ValueError):
        model_cls.model_validate(tampered)


def test_pack_selection_decision_fails_closed_on_tamper(repo_root):
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    decision = select_pack(guideline, carrier_id="synthetic-carrier-a")
    _assert_tamper_rejected(PackSelectionDecision, decision.model_dump(), "selected_pack_id", None)


def test_adjustment_ledger_fails_closed_on_tamper(repo_root):
    ledger = _projection(repo_root).adjustment_ledger
    payload = ledger.model_dump()
    _assert_tamper_rejected(
        AdjustmentLedger, payload, "total_delta_minor_units", payload["total_delta_minor_units"] + 1
    )


def test_sized_work_plan_fails_closed_on_tamper(repo_root):
    sized = _sizing(repo_root).sized_work_plan
    payload = sized.model_dump()
    _assert_tamper_rejected(
        SizedWorkPlan,
        payload,
        "sized_work_plan_total_minor_units",
        payload["sized_work_plan_total_minor_units"] + 1,
    )


def test_proportionality_assessment_fails_closed_on_tamper(repo_root):
    prop = _sizing(repo_root).proportionality
    payload = prop.model_dump()
    _assert_tamper_rejected(ProportionalityAssessment, payload, "ratio", payload["ratio"] + 5.0)


def test_settlement_posture_analysis_fails_closed_on_tamper(repo_root):
    analysis = rank_settlement_postures(
        SettlementPostureInput(
            exposure_minor_units=2_000_000,
            settlement_value_minor_units=50_000,
            settlement_value_after_defense_minor_units=80_000,
            win_probability_percent=50.0,
            defense_cost_settle_now_minor_units=20_000,
            defense_cost_defend_settle_minor_units=150_000,
            defense_cost_try_minor_units=600_000,
        )
    )
    payload = analysis.model_dump()
    _assert_tamper_rejected(SettlementPostureAnalysis, payload, "recommended_posture", "try")


def test_case_sizing_report_fails_closed_on_tamper(repo_root):
    report = _sizing(repo_root)
    payload = report.model_dump()
    payload["proportionality"]["work_plan_total_minor_units"] += 1
    with pytest.raises(ValueError):
        CaseSizingReport.model_validate(payload)


def test_firm_excel_export_fails_closed_on_tamper(repo_root):
    export = FirmExcelBudgetExport(
        export_id="x",
        phases=[
            {
                "utbms_phase_code": "L100",
                "phase_name": "Assessment",
                "tasks": [
                    {
                        "utbms_task_code": "L110",
                        "task_name": "Fact",
                        "original_amount_minor_units": 100000,
                        "billed_amount_minor_units": 0,
                        "new_amount_minor_units": 100000,
                    }
                ],
            }
        ],
    )
    payload = export.model_dump()
    _assert_tamper_rejected(
        FirmExcelBudgetExport,
        payload,
        "new_total_minor_units",
        payload["new_total_minor_units"] + 1,
    )


def test_router_evaluation_report_fails_closed_on_tamper(repo_root):
    report = build_router_evaluation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    payload = report.model_dump()
    _assert_tamper_rejected(
        RouterEvaluationReport, payload, "correct_count", payload["correct_count"] + 1
    )


def test_firm_checkpoint_packet_fails_closed_on_tamper(repo_root):
    packet = build_firm_checkpoint_packet(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    payload = packet.model_dump()
    payload["cases"][0]["trips_proportionality_gate"] = not payload["cases"][0][
        "trips_proportionality_gate"
    ]
    with pytest.raises(ValueError):
        FirmCheckpointPacket.model_validate(payload)


def test_ocg_reconciliation_report_fails_closed_on_tamper(repo_root):
    report = build_ocg_contract_reconciliation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    _assert_tamper_rejected(
        OCGContractReconciliationReport,
        report.model_dump(),
        "adapter_canonical_rule_id_violation_count",
        1,
    )
