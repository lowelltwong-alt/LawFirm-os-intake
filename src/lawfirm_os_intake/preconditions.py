from __future__ import annotations

from .models import (
    BudgetPreconditionCheck,
    BudgetPreconditionReport,
    HumanConfirmation,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


PROHIBITED_PRECONDITION_FAILURE_OUTPUTS = [
    "conflict_search_seed_packet",
    "legal_budget_proposal",
    "legal_budget_review_form",
    "matter_opening_readiness",
    "matter_opening_review_package",
    "review_package_manifest",
    "safety_gate_report",
]


def _check(
    check_id: str,
    ok: bool,
    message: str,
    evidence_refs: list[str],
) -> BudgetPreconditionCheck:
    return BudgetPreconditionCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence_refs=evidence_refs,
    )


def build_budget_precondition_report(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    input_refs: list[str],
) -> BudgetPreconditionReport:
    confirmation_ref = f"human-confirmation://{confirmation.confirmation_id}"
    packet_ref = f"intake-preflight-packet://{packet.packet_id}"
    confirmed_status = confirmation.status == "confirmed"
    checks = [
        _check(
            "preflight_requires_human_review",
            packet.status == "human_intake_review_required"
            and packet.human_confirmation_required is True,
            "Preflight packet is in the human-review-required state.",
            [packet_ref],
        ),
        _check(
            "confirmation_matches_preflight_packet",
            confirmation.preflight_packet_id == packet.packet_id,
            "Human confirmation must bind to the exact preflight packet.",
            [packet_ref, confirmation_ref],
        ),
        _check(
            "confirmation_status_confirmed",
            confirmed_status,
            "Budget generation requires confirmation status to be confirmed.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_matter_family_present",
            bool(confirmation.confirmed_matter_family),
            "Budget generation requires a human-confirmed matter family.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_representation_posture_present",
            bool(confirmation.confirmed_representation_posture),
            "Budget generation requires a human-confirmed representation posture.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_principal_party_roles_present",
            bool(confirmation.confirmed_parties),
            "Budget generation requires human-confirmed principal party roles.",
            [confirmation_ref],
        ),
    ]
    failed = [check.check_id for check in checks if check.status == "failed"]
    status = "passed" if not failed else "failed"
    blocked_state = None
    if failed:
        blocked_state = (
            "budget_blocked_before_human_confirmation"
            if "confirmation_status_confirmed" in failed
            else "budget_precondition_failed"
        )
    return BudgetPreconditionReport(
        budget_precondition_report_id=new_id("budgetprecondition"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status=status,
        checks=checks,
        blocked_state=blocked_state,
        input_refs=input_refs,
        prohibited_outputs=PROHIBITED_PRECONDITION_FAILURE_OUTPUTS,
        generated_at=now_iso(),
    )


def enforce_budget_preconditions(report: BudgetPreconditionReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("budget precondition gate failed: " + ", ".join(failed))
