from __future__ import annotations

from .models import (
    BudgetProposal,
    ConflictSeedPacket,
    EvidenceRef,
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


def _refs_match_packet_segments(packet: IntakePreflightPacket, refs: list[EvidenceRef]) -> bool:
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


def _conflict_terms_are_evidence_bound(
    packet: IntakePreflightPacket, conflict_seed: ConflictSeedPacket
) -> bool:
    if not conflict_seed.normalized_search_terms:
        return False
    refs = [ref for term in conflict_seed.normalized_search_terms for ref in term.evidence_refs]
    return (
        bool(refs)
        and all(term.evidence_refs for term in conflict_seed.normalized_search_terms)
        and _refs_match_packet_segments(packet, refs)
    )


def _budget_lines_are_evidence_bound(packet: IntakePreflightPacket, budget: BudgetProposal) -> bool:
    refs = [ref for line in budget.lines for ref in line.evidence_refs]
    line_support_present = all(
        line.evidence_refs or line.estimate_basis_refs for line in budget.lines
    )
    return line_support_present and _refs_match_packet_segments(packet, refs)


def _budget_support_items_are_supported(
    packet: IntakePreflightPacket, budget: BudgetProposal
) -> bool:
    if not budget.budget_support_items:
        return False
    refs = [ref for item in budget.budget_support_items for ref in item.evidence_refs]
    if refs and not _refs_match_packet_segments(packet, refs):
        return False
    return all(item.evidence_refs or item.structured_ref for item in budget.budget_support_items)


def _budget_texts_are_supported(budget: BudgetProposal) -> bool:
    support_texts = {
        "assumption": {
            item.text for item in budget.budget_support_items if item.item_type == "assumption"
        },
        "exclusion": {
            item.text for item in budget.budget_support_items if item.item_type == "exclusion"
        },
        "unknown": {
            item.text for item in budget.budget_support_items if item.item_type == "unknown"
        },
    }
    return (
        set(budget.assumptions).issubset(support_texts["assumption"])
        and set(budget.exclusions).issubset(support_texts["exclusion"])
        and set(budget.unknowns).issubset(support_texts["unknown"])
    )


def _readiness_blockers_are_supported(
    packet: IntakePreflightPacket, readiness: MatterOpeningReadiness
) -> bool:
    details_by_code = {item.blocker_code: item for item in readiness.blocker_details}
    if not readiness.blockers or not details_by_code:
        return False
    for blocker_code in readiness.blockers:
        detail = details_by_code.get(blocker_code)
        if detail is None or not detail.required_human_gate:
            return False
        if not detail.structured_ref and not detail.evidence_refs:
            return False
        if detail.evidence_refs and not _refs_match_packet_segments(packet, detail.evidence_refs):
            return False
    budget_detail = details_by_code.get("budget_review_not_completed")
    return bool(
        budget_detail
        and budget_detail.required_human_gate == "human_budget_review"
        and budget_detail.structured_ref
    )


def _prohibited_actions_are_supported(readiness: MatterOpeningReadiness) -> bool:
    details_by_code = {item.action_code: item for item in readiness.prohibited_action_details}
    if not readiness.prohibited_actions or not details_by_code:
        return False
    for action_code in readiness.prohibited_actions:
        detail = details_by_code.get(action_code)
        if (
            detail is None
            or not detail.structured_ref
            or not detail.required_human_gate
            or not detail.transition_blocked
        ):
            return False
    return True


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
            "data_scope_gate_report_carried_forward",
            bool(packet.data_scope_gate_report_ref)
            and artifact_refs.get("data_scope_gate_report") == packet.data_scope_gate_report_ref,
            "Data-scope gate report is carried forward into the final package.",
            [artifact_refs.get("data_scope_gate_report", packet.data_scope_gate_report_ref or "")],
        ),
        _check(
            "contract_state_report_carried_forward",
            bool(packet.contract_state_report_ref)
            and artifact_refs.get("contract_state_report") == packet.contract_state_report_ref,
            "The budget package carries forward the preflight contract-state report.",
            [artifact_refs.get("contract_state_report", packet.contract_state_report_ref)],
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
            "conflict_seed_terms_evidence_bound",
            _conflict_terms_are_evidence_bound(packet, conflict_seed),
            "Every normalized conflict-search term carries source-bound evidence refs.",
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
            "budget_submission_guard_report_carried_forward",
            bool(artifact_refs.get("budget_submission_guard_report")),
            "The budget package carries a budget submission guard report.",
            [artifact_refs.get("budget_submission_guard_report", "")],
        ),
        _check(
            "budget_lines_evidence_bound",
            _budget_lines_are_evidence_bound(packet, budget),
            "Every budget line carries source-bound evidence refs when lines are present.",
            [artifact_refs["legal_budget_proposal"]],
        ),
        _check(
            "budget_support_items_supported",
            _budget_support_items_are_supported(packet, budget),
            "Every budget support item carries source-bound evidence refs or a structured ref.",
            [artifact_refs["legal_budget_proposal"]],
        ),
        _check(
            "budget_texts_have_support_items",
            _budget_texts_are_supported(budget),
            "Budget assumptions, exclusions, and unknowns are mirrored by support items.",
            [artifact_refs["legal_budget_proposal"]],
        ),
        _check(
            "matter_opening_blocked",
            readiness.status == "blocked_pending_conflicts_and_engagement",
            "Readiness remains blocked pending conflicts, engagement, and matter-opening approval.",
            [artifact_refs["matter_opening_readiness"]],
        ),
        _check(
            "matter_opening_blockers_supported",
            _readiness_blockers_are_supported(packet, readiness),
            "Matter-opening and submission blockers carry structured support and human-gate refs.",
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
            "deadline_guard_report_carried_forward",
            bool(packet.deadline_docketing_guard_report_ref)
            and artifact_refs.get("preflight_deadline_docketing_guard_report")
            == packet.deadline_docketing_guard_report_ref,
            "The budget package carries forward the preflight deadline docketing guard report.",
            [
                artifact_refs.get(
                    "preflight_deadline_docketing_guard_report",
                    packet.deadline_docketing_guard_report_ref or "",
                )
            ],
        ),
        _check(
            "deadline_not_docketed",
            _contains(packet.prohibited_next_steps, "do_not_docket_deadlines"),
            "Deadline candidates remain review-only and are not docketed.",
            [
                artifact_refs["preflight_packet"],
                artifact_refs.get("preflight_deadline_docketing_guard_report", ""),
            ],
        ),
        _check(
            "budget_not_submitted_or_billed",
            _contains(readiness.prohibited_actions, "do_not_submit_budget"),
            "Budget submission and billing handoff remain prohibited.",
            [
                artifact_refs["matter_opening_readiness"],
                artifact_refs["legal_budget_proposal"],
                artifact_refs.get("budget_submission_guard_report", ""),
            ],
        ),
        _check(
            "prohibited_actions_supported",
            _prohibited_actions_are_supported(readiness),
            "Prohibited readiness actions carry structured policy support and required human gates.",
            [artifact_refs["matter_opening_readiness"]],
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
