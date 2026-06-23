from __future__ import annotations

from .models import (
    BudgetProposal,
    ConflictSeedPacket,
    HumanConfirmation,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    SafetyGateCheck,
    SafetyGateReport,
)
from .util import new_id, now_iso


def _check(
    check_id: str,
    ok: bool,
    message: str,
    evidence_refs: list[str],
) -> SafetyGateCheck:
    return SafetyGateCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence_refs=evidence_refs,
    )


def _contains(items: list[str], expected: str) -> bool:
    return expected in set(items)


def build_safety_gate_report(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
    artifact_refs: dict[str, str],
) -> SafetyGateReport:
    checks = [
        _check(
            "synthetic_only",
            packet.data_origin == "synthetic",
            "Input remains synthetic-only.",
            [artifact_refs["preflight_packet"]],
        ),
        _check(
            "human_intake_confirmation_present",
            confirmation.status == "confirmed"
            and confirmation.preflight_packet_id == packet.packet_id,
            "Budget generation depends on a matching human confirmation artifact.",
            [artifact_refs["human_confirmation"], artifact_refs["preflight_packet"]],
        ),
        _check(
            "no_conflict_conclusion",
            conflict_seed.conclusion == "no_conflict_conclusion",
            "Conflict packet contains search seeds only, not a clearance conclusion.",
            [artifact_refs["conflict_search_seed"]],
        ),
        _check(
            "budget_not_authorized_for_submission",
            budget.approval_state == "proposed_for_human_review"
            and budget.not_authorized_for_client_submission is True,
            "Budget remains proposed for human review and is not client/carrier-submittable.",
            [artifact_refs["legal_budget_proposal"]],
        ),
        _check(
            "matter_opening_blocked",
            readiness.status == "blocked_pending_conflicts_and_engagement",
            "Readiness remains blocked pending conflicts, engagement, and matter-opening approval.",
            [artifact_refs["matter_opening_readiness"]],
        ),
        _check(
            "engagement_not_authorized",
            _contains(readiness.blockers, "engagement_not_authorized"),
            "Engagement authorization remains a blocker.",
            [artifact_refs["matter_opening_readiness"]],
        ),
        _check(
            "matter_not_opened",
            _contains(readiness.blockers, "matter_opening_not_approved")
            and _contains(readiness.prohibited_actions, "do_not_create_matter"),
            "Matter creation/opening remains prohibited.",
            [artifact_refs["matter_opening_readiness"]],
        ),
        _check(
            "imanage_not_created",
            _contains(readiness.prohibited_actions, "do_not_open_imanage"),
            "iManage workspace creation remains prohibited.",
            [artifact_refs["matter_opening_readiness"]],
        ),
        _check(
            "deadline_not_docketed",
            _contains(packet.prohibited_next_steps, "do_not_docket_deadlines"),
            "Deadline candidates remain review-only and are not docketed.",
            [artifact_refs["preflight_packet"]],
        ),
        _check(
            "budget_not_submitted_or_billed",
            _contains(readiness.prohibited_actions, "do_not_submit_budget"),
            "Budget submission and billing handoff remain prohibited.",
            [artifact_refs["matter_opening_readiness"], artifact_refs["legal_budget_proposal"]],
        ),
        _check(
            "no_external_write_artifacts",
            _artifact_refs_are_local(artifact_refs),
            "Artifact references are local files, not external connector targets.",
            sorted(artifact_refs.values()),
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return SafetyGateReport(
        safety_gate_report_id=new_id("safety"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status=status,
        checks=checks,
        prohibited_actions_verified=sorted(
            set(packet.prohibited_next_steps + readiness.prohibited_actions)
        ),
        final_boundary=readiness.status,
        generated_at=now_iso(),
    )


def enforce_safety_gate(report: SafetyGateReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("safety gate failed: " + ", ".join(failed))


def _artifact_refs_are_local(artifact_refs: dict[str, str]) -> bool:
    external_prefixes = ("http://", "https://", "imap://", "smtp://", "s3://", "gs://")
    forbidden_terms = (
        "imanage",
        "gmail",
        "outlook",
        "conflicts_system",
        "carrier_portal",
        "court",
        "billing",
    )
    for value in artifact_refs.values():
        lowered = value.casefold()
        if lowered.startswith(external_prefixes):
            return False
        if any(term in lowered for term in forbidden_terms):
            return False
    return True
