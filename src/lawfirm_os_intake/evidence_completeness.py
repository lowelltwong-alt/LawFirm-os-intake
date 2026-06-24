from __future__ import annotations

from collections import Counter
from typing import Any

from .models import (
    EvidenceCompletenessCheck,
    EvidenceCompletenessReport,
    EvidenceRef,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


REQUIRED_PROHIBITED_NEXT_STEPS = {
    "do_not_clear_conflicts",
    "do_not_accept_representation",
    "do_not_send_client_or_carrier_communications",
    "do_not_open_matter_or_imanage_workspace",
    "do_not_docket_deadlines",
    "do_not_submit_budget",
}


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[EvidenceRef] | None = None,
    details: dict[str, Any] | None = None,
) -> EvidenceCompletenessCheck:
    return EvidenceCompletenessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=(evidence_refs or [])[:25],
        details=details or {},
    )


def _dedup_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    dedup: dict[tuple[str, str, int, int, str], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.source_id, ref.segment_id, ref.start_offset, ref.end_offset, ref.sha256)] = ref
    return list(dedup.values())


def _surface_refs(packet: IntakePreflightPacket) -> dict[str, list[EvidenceRef]]:
    refs: dict[str, list[EvidenceRef]] = {
        "party_candidates": [
            ref for party in packet.party_candidates for ref in party.evidence_refs
        ],
        "party_role_candidates": [
            ref
            for party in packet.party_candidates
            for role in party.role_candidates
            for ref in role.evidence_refs
        ],
        "inbound_event_candidates": [
            ref
            for candidate in packet.inbound_event_candidates
            for ref in candidate.observed_evidence_refs
        ],
        "matter_family_candidates": [
            ref
            for candidate in packet.matter_family_candidates
            for ref in candidate.observed_evidence_refs
        ],
        "representation_posture_candidates": [
            ref
            for candidate in packet.representation_posture_candidates
            for ref in candidate.observed_evidence_refs
        ],
        "deadline_candidates": [
            ref for candidate in packet.deadline_candidates for ref in candidate.evidence_refs
        ],
        "missing_information_candidates": [
            ref
            for candidate in packet.missing_information_candidates
            for ref in candidate.evidence_refs
        ],
        "critic_findings": [
            ref for finding in packet.critic_findings for ref in finding.evidence_refs
        ],
    }
    return {surface: _dedup_refs(values) for surface, values in refs.items()}


def _surface_counts(packet: IntakePreflightPacket) -> dict[str, int]:
    return {
        "party_candidates": len(packet.party_candidates),
        "party_role_candidates": sum(
            len(party.role_candidates) for party in packet.party_candidates
        ),
        "inbound_event_candidates": len(packet.inbound_event_candidates),
        "matter_family_candidates": len(packet.matter_family_candidates),
        "representation_posture_candidates": len(packet.representation_posture_candidates),
        "deadline_candidates": len(packet.deadline_candidates),
        "missing_information_candidates": len(packet.missing_information_candidates),
        "critic_findings": len(packet.critic_findings),
    }


def _missing_party_refs(packet: IntakePreflightPacket) -> list[str]:
    missing: list[str] = []
    for party in packet.party_candidates:
        if not party.evidence_refs:
            missing.append(party.name)
    return missing


def _missing_role_refs(packet: IntakePreflightPacket) -> list[str]:
    missing: list[str] = []
    for party in packet.party_candidates:
        for role in party.role_candidates:
            if not role.evidence_refs:
                missing.append(f"{party.name}:{role.role}")
    return missing


def _missing_scored_refs(packet: IntakePreflightPacket) -> list[str]:
    missing: list[str] = []
    for surface, candidates in {
        "inbound_event": packet.inbound_event_candidates,
        "matter_family": packet.matter_family_candidates,
        "representation_posture": packet.representation_posture_candidates,
    }.items():
        for candidate in candidates:
            if not candidate.observed_evidence_refs:
                missing.append(f"{surface}:{candidate.label}")
    return missing


def _missing_deadline_refs(packet: IntakePreflightPacket) -> list[str]:
    return [
        candidate.expression
        for candidate in packet.deadline_candidates
        if not candidate.evidence_refs
    ]


def _unsafe_deadline_review(packet: IntakePreflightPacket) -> list[str]:
    return [
        candidate.expression
        for candidate in packet.deadline_candidates
        if not candidate.requires_human_verification
    ]


def _missing_gap_refs(packet: IntakePreflightPacket) -> list[str]:
    return [
        candidate.field_name
        for candidate in packet.missing_information_candidates
        if not candidate.evidence_refs
    ]


def _missing_critic_refs(packet: IntakePreflightPacket) -> list[str]:
    return [finding.code for finding in packet.critic_findings if not finding.evidence_refs]


def _source_status_counts(packet: IntakePreflightPacket) -> dict[str, int]:
    statuses = Counter(
        candidate.source_evidence_status
        for candidate in [
            *packet.inbound_event_candidates,
            *packet.matter_family_candidates,
            *packet.representation_posture_candidates,
        ]
    )
    return dict(sorted(statuses.items()))


def _unknown_surfaces_missing(packet: IntakePreflightPacket) -> list[str]:
    missing: list[str] = []
    for surface, candidates in {
        "inbound_event_candidates": packet.inbound_event_candidates,
        "matter_family_candidates": packet.matter_family_candidates,
        "representation_posture_candidates": packet.representation_posture_candidates,
    }.items():
        if not any(
            candidate.label == "unknown"
            and candidate.source_evidence_status == "unknown_option"
            and candidate.observed_evidence_refs
            for candidate in candidates
        ):
            missing.append(surface)
    return missing


def _ref_mismatches(packet: IntakePreflightPacket, refs: list[EvidenceRef]) -> list[dict[str, Any]]:
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    mismatches: list[dict[str, Any]] = []
    for ref in refs:
        segment = segments_by_id.get(ref.segment_id)
        if segment is None:
            mismatches.append(
                {
                    "segment_id": ref.segment_id,
                    "source_id": ref.source_id,
                    "reason": "unknown_segment_id",
                }
            )
            continue
        reasons: list[str] = []
        if ref.source_id != segment.source_id:
            reasons.append("source_id")
        if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
            reasons.append("offsets")
        if ref.sha256 != segment.sha256:
            reasons.append("sha256")
        if reasons:
            mismatches.append(
                {
                    "segment_id": ref.segment_id,
                    "source_id": ref.source_id,
                    "expected_source_id": segment.source_id,
                    "reason": ",".join(reasons),
                }
            )
    return mismatches


def build_evidence_completeness_report(
    packet: IntakePreflightPacket,
    *,
    strict_evidence_required: bool = True,
) -> EvidenceCompletenessReport:
    surface_refs = _surface_refs(packet)
    all_refs = _dedup_refs([ref for refs in surface_refs.values() for ref in refs])
    surface_counts = _surface_counts(packet)
    missing_party_refs = _missing_party_refs(packet)
    missing_role_refs = _missing_role_refs(packet)
    missing_scored_refs = _missing_scored_refs(packet)
    missing_deadline_refs = _missing_deadline_refs(packet)
    unsafe_deadlines = _unsafe_deadline_review(packet)
    missing_gap_refs = _missing_gap_refs(packet)
    missing_critic_refs = _missing_critic_refs(packet)
    unknown_surfaces_missing = _unknown_surfaces_missing(packet)
    prohibited_missing = sorted(REQUIRED_PROHIBITED_NEXT_STEPS - set(packet.prohibited_next_steps))
    mismatches = _ref_mismatches(packet, all_refs)
    source_status_counts = _source_status_counts(packet)

    checks = [
        _check(
            "party_candidates_source_bound",
            not missing_party_refs,
            "Every party candidate carries source-bound evidence refs.",
            evidence_refs=surface_refs["party_candidates"],
            details={"missing_party_candidates": missing_party_refs},
        ),
        _check(
            "party_role_candidates_source_bound",
            not missing_role_refs,
            "Every party-role candidate carries source-bound evidence refs.",
            evidence_refs=surface_refs["party_role_candidates"],
            details={"missing_party_role_candidates": missing_role_refs},
        ),
        _check(
            "classification_candidates_source_bound",
            not missing_scored_refs,
            "Inbound-event, matter-family, and posture candidates stay packet-bound.",
            evidence_refs=[
                *surface_refs["inbound_event_candidates"],
                *surface_refs["matter_family_candidates"],
                *surface_refs["representation_posture_candidates"],
            ],
            details={
                "missing_classification_candidates": missing_scored_refs,
                "source_evidence_status_counts": source_status_counts,
            },
        ),
        _check(
            "unknown_options_preserved",
            not unknown_surfaces_missing,
            "Unknown options remain available and source-anchored for human review.",
            details={"missing_unknown_option_surfaces": unknown_surfaces_missing},
        ),
        _check(
            "deadline_candidates_source_bound_and_review_only",
            not missing_deadline_refs and not unsafe_deadlines,
            "Deadline candidates carry evidence refs and still require human review.",
            evidence_refs=surface_refs["deadline_candidates"],
            details={
                "missing_deadline_candidates": missing_deadline_refs,
                "deadline_candidates_without_human_review": unsafe_deadlines,
            },
        ),
        _check(
            "missing_information_candidates_source_bound",
            not missing_gap_refs,
            "Missing-information candidates carry source-bound evidence refs.",
            evidence_refs=surface_refs["missing_information_candidates"],
            details={"missing_gap_candidates": missing_gap_refs},
        ),
        _check(
            "critic_findings_source_bound",
            not missing_critic_refs,
            "Critic findings carry source-bound evidence refs.",
            evidence_refs=surface_refs["critic_findings"],
            details={"missing_critic_findings": missing_critic_refs},
        ),
        _check(
            "evidence_refs_match_segments",
            not mismatches,
            "All candidate evidence refs match packet source IDs, segment IDs, offsets, and hashes.",
            evidence_refs=all_refs,
            details={
                "mismatch_count": len(mismatches),
                "mismatches": mismatches[:25],
            },
        ),
        _check(
            "human_review_boundary_present",
            packet.human_confirmation_required is True and not prohibited_missing,
            "Packet keeps human confirmation required and preserves prohibited next steps.",
            details={"missing_prohibited_next_steps": prohibited_missing},
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return EvidenceCompletenessReport(
        evidence_completeness_report_id=new_id("evidencecomplete"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        status=status,
        strict_evidence_required=strict_evidence_required,
        checked_surfaces=list(surface_counts),
        surface_counts=surface_counts,
        evidence_ref_count=len(all_refs),
        source_evidence_status_counts=source_status_counts,
        human_confirmation_required=packet.human_confirmation_required,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_evidence_completeness_report(report: EvidenceCompletenessReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("evidence completeness failed: " + ", ".join(failed))
