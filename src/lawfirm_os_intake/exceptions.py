from __future__ import annotations

import re

from .models import (
    BudgetProposal,
    BudgetSupportItem,
    BudgetPreconditionReport,
    CriticFinding,
    EscalationDecision,
    EvidenceRef,
    ExceptionLakeCandidate,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    Segment,
)
from .util import new_id


PROHIBITED_TRANSITION_PATTERNS: tuple[dict[str, object], ...] = (
    {
        "label": "prohibited_transition_attempted_conflicts_cleared",
        "transition_ref": (
            "workflow/prohibited-transitions.yaml#conflict_seed_ready->conflicts_cleared"
        ),
        "pattern": re.compile(
            r"\b(?:mark|treat|set|show|declare)\s+conflicts?\s+cleared\b"
            r"|\bconflicts?\s+(?:are|is)\s+cleared\b",
            re.IGNORECASE,
        ),
        "reason": "Untrusted source text attempts to turn a conflict-search seed into conflicts clearance.",
    },
    {
        "label": "prohibited_transition_attempted_matter_opened",
        "transition_ref": "workflow/prohibited-transitions.yaml#raw_received->matter_opened",
        "pattern": re.compile(
            r"\bopen\s+(?:a\s+)?matter\b|\bmatter\s+opened\b|\bcreate\s+(?:a\s+)?matter\b",
            re.IGNORECASE,
        ),
        "reason": "Untrusted source text attempts to open or create a matter.",
    },
    {
        "label": "prohibited_transition_attempted_imanage_workspace_created",
        "transition_ref": (
            "workflow/prohibited-transitions.yaml#matter_opening_readiness->"
            "imanage_workspace_created"
        ),
        "pattern": re.compile(
            r"\b(?:open|create)\s+(?:an?\s+)?(?:imanage|iManage)\s+workspace\b"
            r"|\bopen\s+(?:a\s+)?matter\s+in\s+(?:imanage|iManage)\b",
            re.IGNORECASE,
        ),
        "reason": "Untrusted source text attempts to create or open an iManage workspace.",
    },
    {
        "label": "prohibited_transition_attempted_deadline_docketed",
        "transition_ref": (
            "workflow/prohibited-transitions.yaml#deadline_gap_candidates_ready->deadline_docketed"
        ),
        "pattern": re.compile(r"\bdocket(?:\s+all)?\s+deadlines?\b", re.IGNORECASE),
        "reason": "Untrusted source text attempts to docket candidate deadlines.",
    },
    {
        "label": "prohibited_transition_attempted_budget_submitted",
        "transition_ref": (
            "workflow/prohibited-transitions.yaml#budget_proposal_ready->budget_submitted"
        ),
        "pattern": re.compile(
            r"\bsubmit\s+(?:the\s+)?budget\b|\bsend\s+(?:the\s+)?budget\s+to\b",
            re.IGNORECASE,
        ),
        "reason": "Untrusted source text attempts to submit a budget.",
    },
    {
        "label": "prohibited_transition_attempted_external_message_sent",
        "transition_ref": "workflow/prohibited-transitions.yaml#raw_received->external_message_sent",
        "pattern": re.compile(r"\bsend\s+this\s+message\b", re.IGNORECASE),
        "reason": "Untrusted source text attempts to send an external communication.",
    },
)


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


def _dedup_evidence_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    dedup: dict[tuple[str, str, int, int, str], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.source_id, ref.segment_id, ref.start_offset, ref.end_offset, ref.sha256)] = ref
    return list(dedup.values())


def _support_refs(items: list[BudgetSupportItem]) -> tuple[list[EvidenceRef], list[str]]:
    evidence_refs = _dedup_evidence_refs([ref for item in items for ref in item.evidence_refs])
    structured_refs = sorted(
        {item.structured_ref for item in items if item.structured_ref is not None}
    )
    return evidence_refs, structured_refs


def build_preflight_exception_candidates(
    packet: IntakePreflightPacket,
) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    candidates.extend(_source_inventory_candidates(packet))
    candidates.extend(_instruction_risk_candidates(packet))
    candidates.extend(_prohibited_transition_candidates(packet))
    candidates.extend(
        _critic_finding_candidates(packet.run_id, packet.packet_id, packet.critic_findings)
    )
    candidates.extend(_escalation_candidates(packet.run_id, packet.packet_id, packet.escalation))
    return candidates


def _source_inventory_candidates(packet: IntakePreflightPacket) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    for item in packet.source_inventory:
        if item.read_state in {"missing", "unread", "unreadable"}:
            label = {
                "missing": "source_missing",
                "unread": "source_unread",
                "unreadable": "source_unreadable",
            }[item.read_state]
            candidates.append(
                ExceptionLakeCandidate(
                    candidate_id=new_id("exc"),
                    run_id=packet.run_id,
                    preflight_packet_id=packet.packet_id,
                    local_event_label=label,
                    canonical_lake_class="retrieval_miss",
                    reason=(
                        f"Source {item.source_id} is marked {item.read_state}; "
                        "downstream workers must not invent unavailable or unread content."
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


def _prohibited_transition_candidates(
    packet: IntakePreflightPacket,
) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []
    for definition in PROHIBITED_TRANSITION_PATTERNS:
        pattern = definition["pattern"]
        assert isinstance(pattern, re.Pattern)
        matched_segments = [segment for segment in packet.segments if pattern.search(segment.text)]
        if not matched_segments:
            continue
        refs = _dedup_evidence_refs([_evidence_ref(segment) for segment in matched_segments])
        candidates.append(
            ExceptionLakeCandidate(
                candidate_id=new_id("exc"),
                run_id=packet.run_id,
                preflight_packet_id=packet.packet_id,
                local_event_label=str(definition["label"]),
                canonical_lake_class="workflow_escalation",
                reason=str(definition["reason"]),
                source_inventory_refs=sorted({ref.source_id for ref in refs}),
                evidence_refs=refs,
                structured_refs=[str(definition["transition_ref"])],
                blocked_state=packet.status,
            )
        )
    return candidates


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
    budget: BudgetProposal,
) -> list[ExceptionLakeCandidate]:
    candidates = [
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
    candidates.extend(_budget_uncertainty_candidates(run_id, readiness, evidence_refs, budget))
    return candidates


def _budget_uncertainty_candidates(
    run_id: str,
    readiness: MatterOpeningReadiness,
    fallback_refs: list[EvidenceRef],
    budget: BudgetProposal,
) -> list[ExceptionLakeCandidate]:
    candidates: list[ExceptionLakeCandidate] = []

    unknown_items = [item for item in budget.budget_support_items if item.item_type == "unknown"]
    if budget.unknowns or unknown_items:
        evidence_refs, structured_refs = _support_refs(unknown_items)
        candidates.append(
            ExceptionLakeCandidate(
                candidate_id=new_id("exc"),
                run_id=run_id,
                preflight_packet_id=readiness.preflight_packet_id,
                local_event_label="budget_unknowns_require_review",
                canonical_lake_class="workflow_escalation",
                reason=(
                    "Budget proposal contains unknowns that require human pricing/legal review: "
                    + "; ".join(budget.unknowns or [item.text for item in unknown_items])
                ),
                evidence_refs=evidence_refs,
                structured_refs=structured_refs,
                blocked_state="budget_unknowns_require_human_review",
            )
        )

    if budget.pricing_status == "insufficient_information":
        missing_template_items = [
            item for item in budget.budget_support_items if item.source_kind == "missing_template"
        ]
        evidence_refs, structured_refs = _support_refs(missing_template_items)
        candidates.append(
            ExceptionLakeCandidate(
                candidate_id=new_id("exc"),
                run_id=run_id,
                preflight_packet_id=readiness.preflight_packet_id,
                local_event_label="budget_template_missing",
                canonical_lake_class="workflow_escalation",
                reason=(
                    "Budget proposal is insufficient because no approved synthetic template "
                    "exists for the confirmed matter family."
                ),
                evidence_refs=evidence_refs,
                structured_refs=structured_refs,
                blocked_state="budget_insufficient_information",
            )
        )

    unpriced_lines = [line for line in budget.lines if line.hourly_rate is None]
    if budget.pricing_status == "hours_only" or unpriced_lines:
        refs = _dedup_evidence_refs([ref for line in unpriced_lines for ref in line.evidence_refs])
        candidates.append(
            ExceptionLakeCandidate(
                candidate_id=new_id("exc"),
                run_id=run_id,
                preflight_packet_id=readiness.preflight_packet_id,
                local_event_label="budget_hours_only_missing_rates",
                canonical_lake_class="workflow_escalation",
                reason=(
                    f"Budget remains hours-only because {len(unpriced_lines)} line(s) lack "
                    "authorized rates; the workflow did not invent rates or totals."
                ),
                evidence_refs=refs or fallback_refs,
                structured_refs=[f"budget-proposal://{budget.budget_proposal_id}"],
                blocked_state="budget_hours_only",
            )
        )

    return candidates


def build_budget_precondition_exception_candidates(
    report: BudgetPreconditionReport,
) -> list[ExceptionLakeCandidate]:
    if report.status == "passed":
        return []
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    label = report.blocked_state or "budget_precondition_failed"
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=report.run_id,
            preflight_packet_id=report.preflight_packet_id,
            local_event_label=label,
            canonical_lake_class="workflow_escalation",
            reason=(
                "Budget generation was blocked before proposal output because preconditions failed: "
                + ", ".join(failed)
            ),
            blocked_state=label,
        )
    ]
