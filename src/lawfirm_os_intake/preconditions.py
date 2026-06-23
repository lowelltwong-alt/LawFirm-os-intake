from __future__ import annotations

from .models import (
    BudgetPreconditionCheck,
    BudgetPreconditionReport,
    EvidenceRef,
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
    party_evidence_refs = [
        ref for party in confirmation.confirmed_parties for ref in party.evidence_refs
    ]
    all_confirmation_refs = confirmation.decision_evidence_refs + party_evidence_refs
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
        _check(
            "decision_evidence_refs_present",
            bool(confirmation.decision_evidence_refs),
            "Human confirmation must include source-bound decision evidence refs.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_party_evidence_refs_present",
            bool(confirmation.confirmed_parties)
            and all(party.evidence_refs for party in confirmation.confirmed_parties),
            "Every confirmed party role must include source-bound evidence refs.",
            [confirmation_ref],
        ),
        _check(
            "confirmation_evidence_refs_match_preflight_segments",
            _refs_match_packet_segments(packet, all_confirmation_refs),
            "Confirmation evidence refs must match preflight segment source IDs, offsets, and hashes.",
            [confirmation_ref, packet_ref],
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
            if "confirmation_matches_preflight_packet" in failed
            else "budget_confirmation_evidence_missing"
            if any("evidence_refs" in check_id for check_id in failed)
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


def _refs_match_packet_segments(
    packet: IntakePreflightPacket,
    refs: list[EvidenceRef],
) -> bool:
    if not refs:
        return False
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    for ref in refs:
        segment = segments_by_id.get(ref.segment_id)
        if segment is None:
            return False
        if ref.source_id != segment.source_id:
            return False
        if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
            return False
        if ref.sha256 != segment.sha256:
            return False
    return True
