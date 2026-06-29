from __future__ import annotations

from .models import (
    ConfirmedParty,
    EvidenceRef,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
)
from .util import new_id


def _normal(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


def _dedup_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    dedup: dict[tuple[str, str, int, int, str], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.source_id, ref.segment_id, ref.start_offset, ref.end_offset, ref.sha256)] = ref
    return list(dedup.values())


def _candidate_refs(
    packet: IntakePreflightPacket, label: str | None, kind: str
) -> list[EvidenceRef]:
    if not label:
        return []
    groups = {
        "inbound": packet.inbound_event_candidates,
        "matter": packet.matter_family_candidates,
        "posture": packet.representation_posture_candidates,
    }
    return [
        ref
        for candidate in groups[kind]
        if candidate.label == label
        for ref in candidate.observed_evidence_refs
    ]


def _party_refs(packet: IntakePreflightPacket, party: ConfirmedParty) -> list[EvidenceRef]:
    names = {_normal(party.name), *(_normal(alias) for alias in party.aliases)}
    refs = []
    for candidate in packet.party_candidates:
        candidate_names = {
            _normal(candidate.name),
            *(_normal(alias) for alias in candidate.aliases),
        }
        if names.intersection(candidate_names):
            refs.extend(candidate.evidence_refs)
    return _dedup_refs(refs)


def bind_confirmation_to_packet_evidence(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
) -> HumanConfirmation:
    parties = []
    decision_refs = list(confirmation.decision_evidence_refs)
    for party in confirmation.confirmed_parties:
        party_refs = party.evidence_refs or _party_refs(packet, party)
        decision_refs.extend(party_refs)
        parties.append(party.model_copy(update={"evidence_refs": party_refs}))

    decision_refs.extend(
        _candidate_refs(packet, confirmation.confirmed_inbound_event, "inbound")
        + _candidate_refs(packet, confirmation.confirmed_matter_family, "matter")
        + _candidate_refs(packet, confirmation.confirmed_representation_posture, "posture")
    )

    return confirmation.model_copy(
        update={
            "confirmed_parties": parties,
            "decision_evidence_refs": _dedup_refs(decision_refs),
        }
    )


def _required_next_gate(status: str) -> str:
    if status == "confirmed":
        return "budget_precondition_gate"
    if status == "needs_more_information":
        return "collect_missing_information"
    if status == "unknown":
        return "human_classification_correction"
    if status == "human_only":
        return "human_only_handling"
    return "declined_or_referred_handoff"


def build_human_review_outcome_record(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
) -> HumanReviewOutcomeRecord:
    party_refs = [ref for party in confirmation.confirmed_parties for ref in party.evidence_refs]
    matches_preflight_packet = confirmation.preflight_packet_id == packet.packet_id
    return HumanReviewOutcomeRecord(
        review_outcome_id=new_id("reviewoutcome"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_preflight_packet_id=confirmation.preflight_packet_id,
        confirmation_id=confirmation.confirmation_id,
        status=confirmation.status,
        reviewer_id=confirmation.reviewer_id,
        reviewed_at=confirmation.reviewed_at,
        supersedes_confirmation_id=confirmation.supersedes_confirmation_id,
        matches_preflight_packet=matches_preflight_packet,
        budget_stage_allowed=confirmation.status == "confirmed" and matches_preflight_packet,
        required_next_gate=_required_next_gate(confirmation.status),
        decision_evidence_refs=confirmation.decision_evidence_refs,
        confirmed_party_evidence_refs=_dedup_refs(party_refs),
        confirmed_party_count=len(confirmation.confirmed_parties),
        notes=confirmation.notes,
    )
