from __future__ import annotations

from typing import Any

from .models import BudgetLine, BudgetProposal, HumanConfirmation, IntakePreflightPacket
from .util import new_id


def _budget_template(profile: dict[str, Any], matter_family: str) -> dict[str, Any] | None:
    templates = profile.get("budget_templates", {})
    return templates.get(matter_family)


def build_budget_proposal(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    profile: dict[str, Any],
) -> BudgetProposal:
    if confirmation.status != "confirmed":
        raise ValueError("human confirmation must be confirmed before budget generation")
    if (
        not confirmation.confirmed_matter_family
        or not confirmation.confirmed_representation_posture
    ):
        raise ValueError("confirmed matter family and representation posture are required")

    template = _budget_template(profile, confirmation.confirmed_matter_family)
    if not template:
        return BudgetProposal(
            budget_proposal_id=new_id("budget"),
            preflight_packet_id=packet.packet_id,
            confirmation_id=confirmation.confirmation_id,
            practice_profile_id=str(profile["profile_id"]),
            matter_family=confirmation.confirmed_matter_family,
            representation_posture=confirmation.confirmed_representation_posture,
            pricing_status="insufficient_information",
            lines=[],
            unknowns=[
                "no approved synthetic budget template exists for the confirmed matter family"
            ],
            exclusions=[
                "client submission",
                "carrier submission",
                "matter opening",
                "conflict clearance",
            ],
        )

    rates = {str(k): float(v) for k, v in profile.get("synthetic_hourly_rates", {}).items()}
    lines: list[BudgetLine] = []
    all_priced = True
    evidence_refs = (
        packet.matter_family_candidates[0].observed_evidence_refs[:3]
        if packet.matter_family_candidates
        else []
    )

    for phase in template.get("phases", []):
        for task in phase.get("tasks", []):
            role = str(task["staffing_role"])
            hours = float(task["estimated_hours"])
            rate = rates.get(role)
            fees = round(hours * rate, 2) if rate is not None else None
            if rate is None:
                all_priced = False
            lines.append(
                BudgetLine(
                    phase_id=str(phase["phase_id"]),
                    phase_name=str(phase["phase_name"]),
                    task_id=str(task["task_id"]),
                    task_name=str(task["task_name"]),
                    staffing_role=role,
                    estimated_hours=hours,
                    hourly_rate=rate,
                    estimated_fees=fees,
                    estimated_expenses=float(task.get("estimated_expenses", 0.0)),
                    external_code_candidate=task.get("external_code_candidate"),
                    assumptions=list(task.get("assumptions", [])),
                    evidence_refs=evidence_refs,
                )
            )

    subtotal_fees = (
        round(sum(line.estimated_fees or 0 for line in lines), 2) if all_priced else None
    )
    subtotal_expenses = round(sum(line.estimated_expenses for line in lines), 2)
    contingency_percent = float(template.get("contingency_percent", 0.0))
    contingency_amount = (
        round((subtotal_fees or 0) * contingency_percent / 100, 2) if all_priced else None
    )
    total = (
        round((subtotal_fees or 0) + subtotal_expenses + (contingency_amount or 0), 2)
        if all_priced
        else None
    )

    return BudgetProposal(
        budget_proposal_id=new_id("budget"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        practice_profile_id=str(profile["profile_id"]),
        matter_family=confirmation.confirmed_matter_family,
        representation_posture=confirmation.confirmed_representation_posture,
        pricing_status="priced" if all_priced else "hours_only",
        lines=lines,
        subtotal_fees=subtotal_fees,
        subtotal_expenses=subtotal_expenses,
        contingency_percent=contingency_percent,
        contingency_amount=contingency_amount,
        total_proposed_budget=total,
        assumptions=list(template.get("assumptions", [])),
        exclusions=list(template.get("exclusions", []))
        + [
            "conflict clearance",
            "engagement authorization",
            "carrier/client submission",
            "court filing",
        ],
        unknowns=list(template.get("unknowns", [])),
    )
