from __future__ import annotations

from .models import (
    CriticFinding,
    EscalationDecision,
    EvidenceRef,
    ExceptionLakeCandidate,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    Segment,
)
from .util import new_id


def _evidence_ref(segment: Segment) -> EvidenceRef:
    return EvidenceRef(
        source_id=segment.source_id,
        segment_id=segment.segment_id,
        start_offset=segment.start_offset,
        end_offset=segment.end_offset,
        sha256=segment.sha256,
    )


def _source_instruction_refs(segments: list[Segment]) -> list[EvidenceRef]:
    return [_evidence_ref(segment) for segment in segments if segment.source_instruction_risk]


def build_preflight_exception_candidates(
    packet: IntakePreflightPacket,
) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    candidates.extend(_source_inventory_candidates(packet))
    candidates.extend(_instruction_risk_candidates(packet))
    candidates.extend(
        _critic_finding_candidates(packet.run_id, packet.packet_id, packet.critic_findings)
    )
    candidates.extend(_escalation_candidates(packet.run_id, packet.packet_id, packet.escalation))
    return candidates


def _source_inventory_candidates(packet: IntakePreflightPacket) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    for item in packet.source_inventory:
        if item.read_state in {"missing", "unreadable"}:
            label = "source_missing" if item.read_state == "missing" else "source_unreadable"
            candidates.append(
                ExceptionLakeCandidate(
                    candidate_id=new_id("exc"),
                    run_id=packet.run_id,
                    preflight_packet_id=packet.packet_id,
                    local_event_label=label,
                    canonical_lake_class="retrieval_miss",
                    reason=(
                        f"Source {item.source_id} is marked {item.read_state}; "
                        "downstream workers must not invent missing content."
                    ),
                    source_inventory_refs=[item.source_id],
                )
            )
        if item.availability_state == "duplicate":
            source_refs = [item.source_id]
            if item.duplicate_of_source_id:
                source_refs.append(item.duplicate_of_source_id)
            candidates.append(
                ExceptionLakeCandidate(
                    candidate_id=new_id("exc"),
                    run_id=packet.run_id,
                    preflight_packet_id=packet.packet_id,
                    local_event_label="duplicate_source_detected",
                    canonical_lake_class="workflow_escalation",
                    reason=(
                        f"Source {item.source_id} duplicates {item.duplicate_of_source_id}; "
                        "review should avoid double-counting observed evidence."
                    ),
                    source_inventory_refs=source_refs,
                )
            )
    return candidates


def _instruction_risk_candidates(packet: IntakePreflightPacket) -> list[ExceptionLakeCandidate]:
    refs = _source_instruction_refs(packet.segments)
    if not refs:
        return []
    source_ids = sorted({ref.source_id for ref in refs})
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=packet.run_id,
            preflight_packet_id=packet.packet_id,
            local_event_label="prompt_injection_source_content",
            canonical_lake_class="workflow_escalation",
            reason=(
                "Untrusted source text contains instructions that resemble attempts to expand "
                "workflow authority or perform prohibited actions."
            ),
            source_inventory_refs=source_ids,
            evidence_refs=refs,
            blocked_state=packet.status,
        )
    ]


def _critic_finding_candidates(
    run_id: str,
    packet_id: str,
    findings: list[CriticFinding],
) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    for finding in findings:
        if finding.severity not in {"warning", "blocker"}:
            continue
        candidates.append(
            ExceptionLakeCandidate(
                candidate_id=new_id("exc"),
                run_id=run_id,
                preflight_packet_id=packet_id,
                local_event_label=f"critic_{finding.code.casefold()}",
                canonical_lake_class="workflow_escalation",
                reason=finding.message,
                evidence_refs=finding.evidence_refs,
            )
        )
    return candidates


def _escalation_candidates(
    run_id: str,
    packet_id: str,
    escalation: EscalationDecision,
) -> list[ExceptionLakeCandidate]:
    if not escalation.required:
        return []
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=run_id,
            preflight_packet_id=packet_id,
            local_event_label="intake_escalation_required",
            canonical_lake_class="workflow_escalation",
            reason=(
                "Escalation is required by evidence, ambiguity, or prohibited-transition policy: "
                + ", ".join(escalation.triggers)
            ),
            blocked_state=escalation.recommended_target,
        )
    ]


def build_budget_exception_candidates(
    run_id: str,
    readiness: MatterOpeningReadiness,
    evidence_refs: list[EvidenceRef],
) -> list[ExceptionLakeCandidate]:
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=run_id,
            preflight_packet_id=readiness.preflight_packet_id,
            local_event_label="matter_opening_blocked_pending_conflicts_and_engagement",
            canonical_lake_class="workflow_escalation",
            reason=(
                "Matter opening remains blocked because conflicts, engagement, and matter-opening "
                "authorization are outside this vertical workflow."
            ),
            evidence_refs=evidence_refs,
            blocked_state=readiness.status,
        )
    ]
