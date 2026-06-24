from __future__ import annotations

from .models import (
    ExceptionLakeCandidate,
    ExceptionLakeReadinessCheck,
    ExceptionLakeReadinessReport,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


KNOWN_LAKE_CLASSES = {
    "retrieval_miss",
    "workflow_escalation",
    "authority_conflict_override",
}


def _check(
    check_id: str,
    passed: bool,
    message: str,
    candidate_ids: list[str] | None = None,
) -> ExceptionLakeReadinessCheck:
    return ExceptionLakeReadinessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        candidate_ids=candidate_ids or [],
    )


def _failed_ids(candidates: list[ExceptionLakeCandidate], predicate) -> list[str]:
    return [candidate.candidate_id for candidate in candidates if not predicate(candidate)]


def _evidence_refs_match_packet(
    packet: IntakePreflightPacket,
    candidates: list[ExceptionLakeCandidate],
) -> list[str]:
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    failed: list[str] = []
    for candidate in candidates:
        for ref in candidate.evidence_refs:
            segment = segments_by_id.get(ref.segment_id)
            if (
                segment is None
                or ref.source_id != segment.source_id
                or ref.start_offset != segment.start_offset
                or ref.end_offset != segment.end_offset
                or ref.sha256 != segment.sha256
            ):
                failed.append(candidate.candidate_id)
                break
    return sorted(set(failed))


def _source_inventory_refs_known(
    packet: IntakePreflightPacket,
    candidates: list[ExceptionLakeCandidate],
) -> list[str]:
    source_ids = {item.source_id for item in packet.source_inventory}
    failed = []
    for candidate in candidates:
        if any(source_id not in source_ids for source_id in candidate.source_inventory_refs):
            failed.append(candidate.candidate_id)
    return failed


def build_exception_lake_readiness_report(
    packet: IntakePreflightPacket,
    candidates: list[ExceptionLakeCandidate],
    candidate_file_refs: list[str],
) -> ExceptionLakeReadinessReport:
    dry_run_failures = _failed_ids(
        candidates, lambda candidate: candidate.status == "dry_run_candidate"
    )
    raw_payload_failures = _failed_ids(
        candidates, lambda candidate: candidate.raw_payload_included is False
    )
    promotion_failures = _failed_ids(
        candidates, lambda candidate: candidate.canonical_promotion_required is True
    )
    class_failures = _failed_ids(
        candidates, lambda candidate: candidate.canonical_lake_class in KNOWN_LAKE_CLASSES
    )
    target_failures = _failed_ids(
        candidates,
        lambda candidate: candidate.target_runtime_repo == "LawFirm-os-exceptions-lake-runtime",
    )
    support_failures = _failed_ids(
        candidates,
        lambda candidate: bool(
            candidate.source_inventory_refs
            or candidate.evidence_refs
            or candidate.structured_refs
            or candidate.blocked_state
        ),
    )
    evidence_failures = _evidence_refs_match_packet(packet, candidates)
    source_ref_failures = _source_inventory_refs_known(packet, candidates)

    checks = [
        _check(
            "candidate_identity_present",
            all(candidate.candidate_id and candidate.local_event_label for candidate in candidates),
            "Every dry-run candidate has a local candidate ID and local event label.",
        ),
        _check(
            "dry_run_only",
            not dry_run_failures,
            "Exception candidates remain dry-run records, not Lake admissions.",
            dry_run_failures,
        ),
        _check(
            "raw_payload_excluded",
            not raw_payload_failures,
            "Exception candidates explicitly exclude raw source payloads.",
            raw_payload_failures,
        ),
        _check(
            "canonical_promotion_required",
            not promotion_failures,
            "Exception candidates require future canonical promotion or reviewed mapping.",
            promotion_failures,
        ),
        _check(
            "known_broad_lake_class",
            not class_failures,
            "Exception candidates map only to known broad Lake classes.",
            class_failures,
        ),
        _check(
            "target_runtime_repo_declared",
            not target_failures,
            "Exception candidates target the Exception Lake runtime repo.",
            target_failures,
        ),
        _check(
            "support_pointer_present",
            not support_failures,
            "Each candidate has source inventory refs, evidence refs, structured refs, or a blocked state.",
            support_failures,
        ),
        _check(
            "evidence_refs_match_packet_segments",
            not evidence_failures,
            "Candidate evidence refs match packet segment source IDs, offsets, and hashes.",
            evidence_failures,
        ),
        _check(
            "source_inventory_refs_known",
            not source_ref_failures,
            "Candidate source inventory refs exist in the packet source inventory.",
            source_ref_failures,
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ExceptionLakeReadinessReport(
        exception_lake_readiness_report_id=new_id("excready"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        status=status,
        candidate_count=len(candidates),
        candidate_file_refs=candidate_file_refs,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_exception_lake_readiness(report: ExceptionLakeReadinessReport) -> None:
    if report.status != "passed":
        failed = [check.check_id for check in report.checks if check.status == "failed"]
        raise ValueError("exception lake readiness failed: " + ", ".join(failed))
