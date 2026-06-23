from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Iterable

from .models import (
    CriticFinding,
    DeadlineCandidate,
    EffectiveContext,
    EscalationDecision,
    EvidenceRef,
    MissingInformationCandidate,
    PartyCandidate,
    RoleCandidate,
    ScoredCandidate,
    Segment,
    SourceBundle,
    SourceInventoryItem,
)
from .util import digest_text, new_id


MATTER_SIGNALS: dict[str, list[str]] = {
    "medical_malpractice_defense": [
        "medical malpractice",
        "malpractice",
        "physician",
        "doctor",
        "dr.",
        "hospital",
        "patient",
        "surgery",
        "clinical",
        "standard of care",
    ],
    "insurance_coverage": [
        "coverage opinion",
        "reservation of rights",
        "coverage position",
        "policy exclusion",
        "duty to defend",
        "duty to indemnify",
    ],
    "general_liability_defense": [
        "premises",
        "slip and fall",
        "bodily injury",
        "general liability",
        "negligence claim",
    ],
    "auto_liability_defense": ["vehicle", "collision", "automobile", "auto claim", "motorist"],
    "commercial_litigation": ["breach of contract", "commercial dispute", "business dispute"],
    "plaintiff_personal_injury": ["injured", "compensation", "my injuries", "help me sue"],
}

INBOUND_SIGNALS: dict[str, list[str]] = {
    "carrier_assignment": ["assigning defense", "new assignment", "claim number", "insured"],
    "demand_received": ["demand letter", "settlement demand", "demand amount"],
    "complaint_or_suit_received": ["complaint", "summons", "served"],
    "coverage_inquiry": ["coverage opinion", "coverage position", "reservation of rights"],
    "prospective_client_help_request": ["need help", "can you help", "looking for an attorney"],
    "correspondence_dump": ["correspondence dump", "email chain", "attached materials"],
}

POSTURE_SIGNALS: dict[str, list[str]] = {
    "defense_of_insured": ["assigning defense", "defend", "insured", "defense counsel"],
    "coverage_advice_to_carrier": ["coverage opinion", "coverage advice", "reservation of rights"],
    "coverage_litigation": ["declaratory judgment", "coverage litigation"],
    "direct_corporate_defense": ["direct corporate", "company defense"],
    "claimant_or_plaintiff_representation": ["need help", "my injuries", "help me sue"],
}

ORG_RE = re.compile(
    r"\b(?:[A-Z][\w&.'-]*\s+){0,5}(?:Insurance|Indemnity|Hospital|Medical Center|Clinic|LLC|Inc\.?|Corporation|Corp\.?|Company|Co\.?)\b"
)
PERSON_RE = re.compile(r"\b(?:Dr\.\s+)?[A-Z][a-z]+\s+[A-Z][a-z]+\b")
DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b"
)
RELATIVE_RE = re.compile(r"\bwithin\s+(\d{1,3})\s+days\b", re.I)


def evidence_for_text(segments: list[Segment], needle: str) -> list[EvidenceRef]:
    lowered = needle.lower()
    matches = [s for s in segments if lowered in s.text.lower()]
    if not matches and segments:
        matches = [segments[0]]
    return [_evidence_ref(s) for s in matches[:3]]


def _first_refs(segments: list[Segment], count: int = 1) -> list[EvidenceRef]:
    return [_evidence_ref(s) for s in segments[:count]]


def _evidence_ref(segment: Segment) -> EvidenceRef:
    return EvidenceRef(
        source_id=segment.source_id,
        segment_id=segment.segment_id,
        start_offset=segment.start_offset,
        end_offset=segment.end_offset,
        sha256=segment.sha256,
    )


def source_inventory(
    bundle: SourceBundle, segments: list[Segment] | None = None
) -> list[SourceInventoryItem]:
    seen: dict[str, str] = {}
    inventory: list[SourceInventoryItem] = []
    attachment_refs_by_source: dict[str, list[str]] = {}
    for segment in segments or []:
        if segment.attachment_ref:
            attachment_refs_by_source.setdefault(segment.source_id, []).append(
                segment.attachment_ref
            )

    for source in bundle.sources:
        source_hash = digest_text(source.text)
        duplicate_of = seen.get(source_hash)
        if duplicate_of is None:
            seen[source_hash] = source.source_id
        read_state = str(source.metadata.get("read_state", "read"))
        if source.metadata.get("missing") is True:
            read_state = "missing"
        if source.metadata.get("unreadable") is True:
            read_state = "unreadable"
        availability = "duplicate" if duplicate_of else "available"
        if read_state in {"missing", "unreadable"}:
            availability = read_state
        attachment_refs = list(source.metadata.get("attachment_refs", []))
        attachment_refs.extend(attachment_refs_by_source.get(source.source_id, []))
        inventory.append(
            SourceInventoryItem(
                source_id=source.source_id,
                source_type=source.source_type,
                filename=source.filename,
                read_state=read_state,  # type: ignore[arg-type]
                availability_state=availability,  # type: ignore[arg-type]
                character_count=len(source.text),
                source_sha256=source_hash,
                duplicate_of_source_id=duplicate_of,
                attachment_refs=sorted(set(attachment_refs)),
                metadata_keys=sorted(source.metadata.keys()),
            )
        )
    return inventory


def source_coverage_summary(inventory: list[SourceInventoryItem]) -> dict[str, Any]:
    total = len(inventory)
    return {
        "total_sources": total,
        "read_sources": sum(1 for item in inventory if item.read_state == "read"),
        "unread_sources": sum(1 for item in inventory if item.read_state == "unread"),
        "missing_sources": sum(1 for item in inventory if item.read_state == "missing"),
        "unreadable_sources": sum(1 for item in inventory if item.read_state == "unreadable"),
        "duplicate_sources": sum(1 for item in inventory if item.availability_state == "duplicate"),
        "attachment_reference_count": sum(len(item.attachment_refs) for item in inventory),
        "coverage_complete": all(item.read_state == "read" for item in inventory),
    }


def _normal(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def extract_parties(bundle: SourceBundle, segments: list[Segment]) -> list[PartyCandidate]:
    parties: list[PartyCandidate] = []
    hints = bundle.fixture_hints.get("entities", [])
    for item in hints:
        roles = [
            RoleCandidate(role=str(role["role"]), confidence=float(role.get("confidence", 0.7)))
            for role in item.get("role_candidates", [])
        ]
        parties.append(
            PartyCandidate(
                party_candidate_id=new_id("party"),
                name=str(item["name"]),
                normalized_name=_normal(str(item["name"])),
                aliases=list(item.get("aliases", [])),
                role_candidates=roles or [RoleCandidate(role="unknown", confidence=0.4)],
                evidence_refs=evidence_for_text(segments, str(item["name"])),
            )
        )

    if not hints:
        text = "\n".join(source.text for source in bundle.sources)
        found: dict[str, str] = {}
        for match in list(ORG_RE.finditer(text)) + list(PERSON_RE.finditer(text)):
            name = re.sub(r"\s+", " ", match.group(0).strip())
            found[_normal(name)] = name
        for normalized, name in sorted(found.items()):
            lower = name.lower()
            if "insurance" in lower or "indemnity" in lower:
                roles = [RoleCandidate(role="carrier_or_instructing_source", confidence=0.65)]
            elif name.startswith("Dr."):
                roles = [
                    RoleCandidate(role="insured_or_prospective_represented_client", confidence=0.55)
                ]
            else:
                roles = [RoleCandidate(role="unknown", confidence=0.4)]
            parties.append(
                PartyCandidate(
                    party_candidate_id=new_id("party"),
                    name=name,
                    normalized_name=normalized,
                    role_candidates=roles,
                    evidence_refs=evidence_for_text(segments, name),
                )
            )
    return parties


def _score_family(
    label: str,
    terms: Iterable[str],
    text: str,
    context: EffectiveContext,
    segments: list[Segment],
) -> ScoredCandidate:
    observed = [term for term in terms if term in text]
    base = min(0.72, 0.12 + 0.11 * len(observed)) if observed else 0.05
    prior = float(context.matter_family_priors.get(label, 0.0))
    score = min(0.98, base + (0.22 * prior))
    refs: list[EvidenceRef] = []
    for term in observed[:4]:
        refs.extend(evidence_for_text(segments, term))
    dedup: dict[tuple[str, str], EvidenceRef] = {(r.source_id, r.segment_id): r for r in refs}
    context_refs = []
    if prior:
        context_refs.append(f"practice-profile://{context.profile_id}/matter_family_priors/{label}")
    fallback_refs = _first_refs(segments)
    observed_refs = list(dedup.values()) or fallback_refs
    calibration = "context_influenced" if prior and not observed else "observed"
    return ScoredCandidate(
        candidate_id=new_id("matter"),
        label=label,
        confidence=round(score, 4),
        observed_evidence_refs=observed_refs,
        context_signal_refs=context_refs,
        calibration_label=calibration,
        support_summary=", ".join(observed)
        if observed
        else "No direct lexical signal; retained for comparison/context prior.",
    )


def _score_signal_set(
    signals: dict[str, list[str]],
    text: str,
    segments: list[Segment],
    prefix: str,
) -> list[ScoredCandidate]:
    candidates: list[ScoredCandidate] = []
    for label, terms in signals.items():
        observed = [term for term in terms if term in text]
        score = min(0.96, 0.15 + 0.18 * len(observed)) if observed else 0.03
        refs: list[EvidenceRef] = []
        for term in observed[:4]:
            refs.extend(evidence_for_text(segments, term))
        dedup = {(r.source_id, r.segment_id): r for r in refs}
        fallback_refs = _first_refs(segments)
        candidates.append(
            ScoredCandidate(
                candidate_id=new_id(prefix),
                label=label,
                confidence=round(score, 4),
                observed_evidence_refs=list(dedup.values()) or fallback_refs,
                support_summary=", ".join(observed)
                if observed
                else "No direct lexical signal; retained as alternative.",
            )
        )
    candidates.append(
        ScoredCandidate(
            candidate_id=new_id(prefix),
            label="unknown",
            confidence=0.2,
            observed_evidence_refs=_first_refs(segments),
            calibration_label="unknown_option",
            support_summary="Explicit unknown option preserved for human review.",
        )
    )
    return sorted(candidates, key=lambda c: c.confidence, reverse=True)


def classify_matter(
    bundle: SourceBundle,
    segments: list[Segment],
    context: EffectiveContext,
) -> tuple[list[ScoredCandidate], list[ScoredCandidate], list[ScoredCandidate]]:
    text = "\n".join(source.text for source in bundle.sources).lower()
    matter = [
        _score_family(label, terms, text, context, segments)
        for label, terms in MATTER_SIGNALS.items()
    ]
    matter.append(
        ScoredCandidate(
            candidate_id=new_id("matter"),
            label="unknown",
            confidence=0.2,
            observed_evidence_refs=_first_refs(segments),
            calibration_label="unknown_option",
            support_summary="Explicit unknown option preserved for human review.",
        )
    )
    matter.sort(key=lambda c: c.confidence, reverse=True)
    inbound = _score_signal_set(INBOUND_SIGNALS, text, segments, "inbound")
    posture = _score_signal_set(POSTURE_SIGNALS, text, segments, "posture")
    return inbound, matter, posture


def missing_information_candidates(
    missing: list[str], segments: list[Segment]
) -> list[MissingInformationCandidate]:
    refs = _first_refs(segments)
    return [
        MissingInformationCandidate(
            field_name=field,
            reason="Required intake field was not found in the permitted structured source segments.",
            evidence_refs=refs,
        )
        for field in missing
    ]


def extract_deadlines_and_gaps(
    bundle: SourceBundle,
    segments: list[Segment],
    context: EffectiveContext,
) -> tuple[list[DeadlineCandidate], list[str]]:
    text = "\n".join(source.text for source in bundle.sources)
    candidates: list[DeadlineCandidate] = []
    for match in DATE_RE.finditer(text):
        normalized = None
        try:
            normalized = datetime.strptime(match.group(0), "%B %d, %Y").date().isoformat()
        except ValueError:
            pass
        candidates.append(
            DeadlineCandidate(
                deadline_candidate_id=new_id("deadline"),
                expression=match.group(0),
                normalized_date=normalized,
                deadline_type_candidate="date_mentioned_requires_legal_characterization",
                confidence=0.62,
                evidence_refs=evidence_for_text(segments, match.group(0)),
            )
        )
    for match in RELATIVE_RE.finditer(text):
        candidates.append(
            DeadlineCandidate(
                deadline_candidate_id=new_id("deadline"),
                expression=match.group(0),
                normalized_date=None,
                deadline_type_candidate="relative_reporting_or_response_deadline_candidate",
                confidence=0.58,
                evidence_refs=evidence_for_text(segments, match.group(0)),
            )
        )

    provided = set(str(v) for v in bundle.fixture_hints.get("provided_fields", []))
    missing = [field for field in context.required_intake_fields if field not in provided]
    return candidates, missing


def review_evidence(
    parties: list[PartyCandidate],
    matter: list[ScoredCandidate],
    deadlines: list[DeadlineCandidate],
    missing: list[str],
    segments: list[Segment],
) -> tuple[list[CriticFinding], EscalationDecision]:
    findings: list[CriticFinding] = []
    triggers: list[str] = []
    fallback_refs = _first_refs(segments)

    if len(matter) >= 2 and (matter[0].confidence - matter[1].confidence) < 0.15:
        findings.append(
            CriticFinding(
                code="MATTER_CANDIDATES_CLOSE",
                severity="warning",
                message="Top matter-family candidates are too close for reliable automatic routing.",
                evidence_refs=matter[0].observed_evidence_refs[:2]
                + matter[1].observed_evidence_refs[:2],
            )
        )
        triggers.append("worker_disagreement_or_close_candidate_scores")

    role_names = {role.role for party in parties for role in party.role_candidates}
    carrier_present = any("carrier" in role for role in role_names)
    represented_candidate_present = any(
        "represented_client" in role or "insured" in role for role in role_names
    )
    if carrier_present and not represented_candidate_present:
        findings.append(
            CriticFinding(
                code="CARRIER_IS_NOT_AUTOMATICALLY_CLIENT",
                severity="blocker",
                message=(
                    "An instructing carrier or payer is present, but the prospective represented client "
                    "has not been identified. Human confirmation is mandatory."
                ),
                evidence_refs=[ref for party in parties for ref in party.evidence_refs][:5]
                or fallback_refs,
            )
        )
        triggers.append("represented_client_or_payer_relationship_ambiguous")

    if deadlines:
        findings.append(
            CriticFinding(
                code="DATE_OR_DEADLINE_REQUIRES_REVIEW",
                severity="warning",
                message="At least one date or relative deadline candidate requires human verification.",
                evidence_refs=[ref for item in deadlines for ref in item.evidence_refs][:5],
            )
        )
        triggers.append("deadline_or_time_sensitive_signal_detected")

    if missing:
        findings.append(
            CriticFinding(
                code="MISSING_REQUIRED_INTAKE_INFORMATION",
                severity="warning",
                message="Required intake fields remain missing: " + ", ".join(missing),
                evidence_refs=fallback_refs,
            )
        )
        triggers.append("missing_required_information")

    if any(not party.evidence_refs for party in parties):
        findings.append(
            CriticFinding(
                code="PARTY_WITHOUT_EVIDENCE_REF",
                severity="blocker",
                message="A party candidate lacks a source-bound evidence reference.",
                evidence_refs=fallback_refs,
            )
        )
        triggers.append("evidence_completeness_failure")

    target = "ordinary_human_intake_review"
    if any(f.severity == "blocker" for f in findings) or len(triggers) >= 3:
        target = "frontier_adjudicator_then_human"
    if "evidence_completeness_failure" in triggers:
        target = "human_only"

    return findings, EscalationDecision(
        required=bool(triggers),
        triggers=triggers,
        recommended_target=target,
        self_reported_confidence_used_as_sole_trigger=False,
    )
