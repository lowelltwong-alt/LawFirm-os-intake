"""CW5 — no-data firm checkpoint packet.

Three synthetic cases run end-to-end (routed -> sized -> priced -> exported) with a
disposition sheet, packaged for a firm checkpoint. The real firm checkpoint is a
human gate; the dispositions here are clearly-labeled synthetic PLACEHOLDERS and
never constitute real firm validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .budget_exporters import get_budget_exporter, FIRM_EXCEL_FORMAT_ID
from .case_sizing import (
    CASE_SIZING_POLICY_REF,
    build_case_sizing_report,
    load_case_sizing_policy,
)
from .models import (
    FirmCheckpointCase,
    FirmCheckpointCaseDisposition,
    FirmCheckpointPacket,
    FirmExcelBudgetExport,
    FirmExcelBudgetPhase,
    FirmExcelBudgetTaskRow,
    SettlementPostureInput,
)
from .routing_eval import build_synthetic_intake_case, route_decision
from .models import RouterEvalCaseSpec
from .workers import classify_matter
from .routing_eval import _synthetic_context
from .util import digest_json, now_iso

# Expert preapproval trips above $25,000 of expert (E119) spend.
PREAPPROVAL_EXPERT_SPEND_THRESHOLD_MINOR = 2_500_000
_TMP = "2026-07-23T00:00:00Z"


def _route(family: str) -> tuple[str, str | None]:
    spec = RouterEvalCaseSpec(
        case_id=f"{family}-checkpoint",
        ground_truth_family=family,
        variant="clean",
        expected_decision="route",
    )
    case = build_synthetic_intake_case(spec)
    _inbound, matter, _posture = classify_matter(case.bundle, case.segments, _synthetic_context())
    predicted, decision, _reason = route_decision(matter)
    return decision, predicted


def _firm_excel(case_id: str, phases: list[tuple[str, str, list[tuple[str, str, int]]]]):
    export = FirmExcelBudgetExport(
        export_id=f"firm-excel-{case_id}",
        matter_label=f"SYNTHETIC CHECKPOINT MATTER {case_id} (candidate, not a real client)",
        phases=[
            FirmExcelBudgetPhase(
                utbms_phase_code=phase_code,
                phase_name=phase_name,
                tasks=[
                    FirmExcelBudgetTaskRow(
                        utbms_task_code=task_code,
                        task_name=task_name,
                        original_amount_minor_units=amount,
                        billed_amount_minor_units=0,
                        new_amount_minor_units=amount,
                    )
                    for task_code, task_name, amount in tasks
                ],
            )
            for phase_code, phase_name, tasks in phases
        ],
    )
    return export


def _expert_trip(export: FirmExcelBudgetExport) -> bool:
    return any(
        task.utbms_task_code == "E119"
        and task.original_amount_minor_units > PREAPPROVAL_EXPERT_SPEND_THRESHOLD_MINOR
        for phase in export.phases
        for task in phase.tasks
    )


def _placeholder_disposition() -> FirmCheckpointCaseDisposition:
    return FirmCheckpointCaseDisposition(
        disposition="pending_firm_review",
        is_synthetic_placeholder=True,
        reason="Synthetic placeholder — awaiting real firm disposition (useful / wrong workflow / missing rule).",
    )


def _case(
    *,
    case_id: str,
    label: str,
    family: str,
    case_type: str,
    base_work_plan_minor: int,
    drivers: dict[str, Any],
    posture_input: SettlementPostureInput,
    export_phases: list[tuple[str, str, list[tuple[str, str, int]]]],
    policy: dict[str, Any],
) -> FirmCheckpointCase:
    sizing = build_case_sizing_report(
        case_type=case_type,
        base_work_plan_total_minor_units=base_work_plan_minor,
        drivers=drivers,
        posture_input=posture_input,
        policy=policy,
        generated_at=_TMP,
    )
    decision, routed_family = _route(family)
    export = _firm_excel(case_id, export_phases)
    exporter = get_budget_exporter(FIRM_EXCEL_FORMAT_ID)
    assert exporter.format_id == FIRM_EXCEL_FORMAT_ID
    return FirmCheckpointCase(
        case_id=case_id,
        label=label,
        matter_family=family,
        routed_decision=decision,  # type: ignore[arg-type]
        routed_family=routed_family,
        case_sizing_report=sizing,
        trips_proportionality_gate=(
            sizing.proportionality.status == "blocked_disproportionate_budget"
        ),
        recommended_posture=sizing.settlement_posture_analysis.recommended_posture,
        expected_preapproval_trip=_expert_trip(export),
        firm_excel_export_id=export.export_id,
        firm_excel_original_total_minor_units=export.original_total_minor_units or 0,
        disposition=_placeholder_disposition(),
    )


def build_firm_checkpoint_packet(
    *, repo_root: str | Path, generated_at: str | None = None
) -> FirmCheckpointPacket:
    policy = load_case_sizing_policy(Path(repo_root) / CASE_SIZING_POLICY_REF)

    # 1) Small slip-and-fall: oversized vs a $10k exposure -> proportionality trips,
    #    small settlement value -> settle recommended.
    slip = _case(
        case_id="slip-and-fall",
        label="Small slip-and-fall (settle-lean; trips proportionality gate)",
        family="general_liability_defense",
        case_type="premises_liability",
        base_work_plan_minor=350_000,
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
        export_phases=[
            (
                "L100",
                "Case Assessment",
                [("L110", "Fact Investigation", 200_000), ("L120", "Analysis / Strategy", 150_000)],
            ),
            ("L300", "Discovery", [("L330", "Depositions", 250_000)]),
        ],
        policy=policy,
    )

    # 2) Mid-size EPLI with an expert-preapproval trip (E119 > $25k), within band.
    epli = _case(
        case_id="epli",
        label="Mid-size EPLI (within band; expert-preapproval trip)",
        family="discrimination_harassment",
        case_type="epli",
        base_work_plan_minor=1_200_000,
        drivers={
            "party_count": 1,
            "injury_severity": "soft_tissue",
            "liability_clarity": "comparative",
            "exposure_band": "high",
            "venue": "state_default",
        },
        posture_input=SettlementPostureInput(
            exposure_minor_units=5_000_000,
            settlement_value_minor_units=1_200_000,
            settlement_value_after_defense_minor_units=1_400_000,
            win_probability_percent=55.0,
            defense_cost_settle_now_minor_units=120_000,
            defense_cost_defend_settle_minor_units=600_000,
            defense_cost_try_minor_units=1_800_000,
        ),
        export_phases=[
            ("L100", "Case Assessment", [("L110", "Fact Investigation", 400_000)]),
            ("L300", "Discovery", [("L340", "Expert Discovery", 500_000)]),
            ("E100", "Expenses", [("E119", "Expert Fees", 3_000_000)]),
        ],
        policy=policy,
    )

    # 3) L&E wage-hour family case, within band.
    wage_hour = _case(
        case_id="wage-hour",
        label="Labor & Employment wage-hour (within band)",
        family="wage_hour_flsa_state",
        case_type="labor_employment",
        base_work_plan_minor=900_000,
        drivers={
            "party_count": 1,
            "injury_severity": "soft_tissue",
            "liability_clarity": "clear",
            "exposure_band": "medium",
            "venue": "state_default",
        },
        posture_input=SettlementPostureInput(
            exposure_minor_units=2_500_000,
            settlement_value_minor_units=700_000,
            settlement_value_after_defense_minor_units=850_000,
            win_probability_percent=60.0,
            defense_cost_settle_now_minor_units=90_000,
            defense_cost_defend_settle_minor_units=350_000,
            defense_cost_try_minor_units=900_000,
        ),
        export_phases=[
            ("L100", "Case Assessment", [("L110", "Fact Investigation", 300_000)]),
            ("L200", "Pre-Trial", [("L240", "Dispositive Motions", 250_000)]),
            ("L300", "Discovery", [("L310", "Written Discovery", 350_000)]),
        ],
        policy=policy,
    )

    cases = [slip, epli, wage_hour]
    basis = {"cases": [case.case_id for case in cases]}
    return FirmCheckpointPacket(
        packet_id="firmcheckpoint-" + digest_json(basis).removeprefix("sha256:")[:16],
        cases=cases,
        synthetic_placeholder_dispositions_used=any(
            case.disposition.is_synthetic_placeholder for case in cases
        ),
        generated_at=generated_at or now_iso(),
    )
