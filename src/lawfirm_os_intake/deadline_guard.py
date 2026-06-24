from __future__ import annotations

from .models import (
    DeadlineDocketingGuardCheck,
    DeadlineDocketingGuardItem,
    DeadlineDocketingGuardReport,
    EvidenceRef,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


DEADLINE_DOCKETING_TRANSITION_REF = (
    "workflow/prohibited-transitions.yaml#deadline_gap_candidates_ready->deadline_docketed"
)
DEADLINE_REVIEW_WORKFLOW_REF = "workflow/intake-to-budget.workflow.yaml#deadline_gap_candidates"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    evidence_refs: list[EvidenceRef] | None = None,
    structured_refs: list[str] | None = None,
) -> DeadlineDocketingGuardCheck:
    return DeadlineDocketingGuardCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        structured_refs=structured_refs or [],
    )


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


def build_deadline_docketing_guard_report(
    packet: IntakePreflightPacket,
) -> DeadlineDocketingGuardReport:
    structured_refs = [DEADLINE_REVIEW_WORKFLOW_REF, DEADLINE_DOCKETING_TRANSITION_REF]
    candidate_items = [
        DeadlineDocketingGuardItem(
            deadline_candidate_id=candidate.deadline_candidate_id,
            expression=candidate.expression,
            normalized_date=candidate.normalized_date,
            deadline_type_candidate=candidate.deadline_type_candidate,
            requires_human_verification=True,
            evidence_refs=candidate.evidence_refs,
            structured_refs=structured_refs,
        )
        for candidate in packet.deadline_candidates
    ]
    all_refs = [ref for candidate in packet.deadline_candidates for ref in candidate.evidence_refs]
    candidates_source_bound = all(
        candidate.evidence_refs for candidate in packet.deadline_candidates
    ) and _refs_match_packet_segments(packet, all_refs)
    all_candidates_require_review = all(
        candidate.requires_human_verification for candidate in packet.deadline_candidates
    )
    docketing_forbidden = "do_not_docket_deadlines" in set(packet.prohibited_next_steps)
    checks = [
        _check(
            "deadline_candidates_source_bound",
            candidates_source_bound,
            "Every deadline candidate carries evidence refs that match packet segments.",
            all_refs,
        ),
        _check(
            "deadline_candidates_require_human_review",
            all_candidates_require_review,
            "Every deadline candidate remains a candidate requiring human deadline review.",
            all_refs,
            [DEADLINE_REVIEW_WORKFLOW_REF],
        ),
        _check(
            "deadline_docketing_forbidden_by_policy",
            docketing_forbidden,
            "The preflight packet explicitly prohibits docketing candidate deadlines.",
            structured_refs=structured_refs,
        ),
        _check(
            "deadline_docketing_not_performed",
            True,
            "No docketing action, external write, or calendar/court/billing handoff was performed.",
            structured_refs=[DEADLINE_DOCKETING_TRANSITION_REF],
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return DeadlineDocketingGuardReport(
        deadline_docketing_guard_report_id=new_id("deadlineguard"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        status=status,
        candidate_count=len(candidate_items),
        review_required_count=sum(
            1 for item in candidate_items if item.requires_human_verification
        ),
        candidate_items=candidate_items,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_deadline_docketing_guard_report(
    report: DeadlineDocketingGuardReport,
) -> None:
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    if report.status != "passed":
        failed.append("deadline_guard_status")
    if report.docketing_action_performed is not False:
        failed.append("docketing_action_performed")
    if report.docketing_action_allowed is not False:
        failed.append("docketing_action_allowed")
    if report.external_writes_performed is not False:
        failed.append("external_writes_performed")
    if report.non_authoritative is not True:
        failed.append("non_authoritative")
    if report.candidate_count != len(report.candidate_items):
        failed.append("candidate_count")
    review_required = sum(1 for item in report.candidate_items if item.requires_human_verification)
    if report.review_required_count != review_required:
        failed.append("review_required_count")
    if any(not item.evidence_refs for item in report.candidate_items):
        failed.append("candidate_evidence_refs")
    if any(item.proposed_next_gate != "human_deadline_review" for item in report.candidate_items):
        failed.append("candidate_next_gate")
    if not failed:
        return
    raise ValueError("deadline docketing guard failed: " + ", ".join(failed))
