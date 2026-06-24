from __future__ import annotations

from collections import defaultdict
from typing import Literal

from .models import (
    ExceptionLakeCandidate,
    ExceptionLakeHandoffCheck,
    ExceptionLakeHandoffLabelSummary,
    ExceptionLakeHandoffManifest,
    ExceptionLakeReadinessReport,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


def _check(
    check_id: str,
    passed: bool,
    message: str,
    candidate_ids: list[str] | None = None,
) -> ExceptionLakeHandoffCheck:
    return ExceptionLakeHandoffCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        candidate_ids=candidate_ids or [],
    )


def _failed_ids(candidates: list[ExceptionLakeCandidate], predicate) -> list[str]:
    return [candidate.candidate_id for candidate in candidates if not predicate(candidate)]


def _support_modes(candidate: ExceptionLakeCandidate) -> list[str]:
    modes = []
    if candidate.source_inventory_refs:
        modes.append("source_inventory_ref")
    if candidate.evidence_refs:
        modes.append("source_evidence_ref")
    if candidate.structured_refs:
        modes.append("structured_ref")
    if candidate.blocked_state:
        modes.append("blocked_state")
    return modes


def _label_summaries(
    candidates: list[ExceptionLakeCandidate],
) -> list[ExceptionLakeHandoffLabelSummary]:
    grouped: dict[tuple[str, str], list[ExceptionLakeCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate.local_event_label, candidate.canonical_lake_class)].append(candidate)

    summaries = []
    for (label, lake_class), items in sorted(grouped.items()):
        support_modes = sorted({mode for item in items for mode in _support_modes(item)})
        summaries.append(
            ExceptionLakeHandoffLabelSummary(
                local_event_label=label,
                canonical_lake_class=lake_class,  # type: ignore[arg-type]
                count=len(items),
                candidate_ids=[item.candidate_id for item in items],
                support_modes=support_modes,  # type: ignore[arg-type]
                source_inventory_ref_count=sum(len(item.source_inventory_refs) for item in items),
                evidence_ref_count=sum(len(item.evidence_refs) for item in items),
                structured_ref_count=sum(len(item.structured_refs) for item in items),
                blocked_states=sorted(
                    {item.blocked_state for item in items if item.blocked_state is not None}
                ),
            )
        )
    return summaries


def build_exception_lake_handoff_manifest(
    *,
    packet: IntakePreflightPacket,
    candidates: list[ExceptionLakeCandidate],
    candidate_file_refs: list[str],
    readiness_report: ExceptionLakeReadinessReport,
    readiness_report_ref: str,
    stage: Literal["preflight", "budget_combined", "budget_precondition_blocked"],
) -> ExceptionLakeHandoffManifest:
    dry_run_failures = _failed_ids(
        candidates, lambda candidate: candidate.status == "dry_run_candidate"
    )
    raw_payload_failures = _failed_ids(
        candidates, lambda candidate: candidate.raw_payload_included is False
    )
    promotion_failures = _failed_ids(
        candidates, lambda candidate: candidate.canonical_promotion_required is True
    )
    target_failures = _failed_ids(
        candidates,
        lambda candidate: candidate.target_runtime_repo == "LawFirm-os-exceptions-lake-runtime",
    )
    support_failures = _failed_ids(
        candidates,
        lambda candidate: bool(_support_modes(candidate)),
    )
    label_class_failures = _failed_ids(
        candidates,
        lambda candidate: bool(candidate.local_event_label and candidate.canonical_lake_class),
    )
    file_refs_declared = bool(candidate_file_refs) and all(candidate_file_refs)

    checks = [
        _check(
            "readiness_report_passed",
            readiness_report.status == "passed"
            and readiness_report.admission_state == "dry_run_not_admitted",
            "The paired readiness report passed and remains dry-run only.",
        ),
        _check(
            "dry_run_only",
            not dry_run_failures,
            "Every candidate remains a dry-run candidate, not a Lake admission.",
            dry_run_failures,
        ),
        _check(
            "raw_payload_excluded",
            not raw_payload_failures,
            "No candidate includes raw source payload text.",
            raw_payload_failures,
        ),
        _check(
            "canonical_promotion_required",
            not promotion_failures,
            "Every local label requires future canonical promotion or reviewed mapping.",
            promotion_failures,
        ),
        _check(
            "target_runtime_is_exception_lake",
            not target_failures,
            "Every candidate targets the Exception Lake runtime owner.",
            target_failures,
        ),
        _check(
            "candidate_support_modes_present",
            not support_failures,
            "Every candidate has inventory, source evidence, structured refs, or blocked-state support.",
            support_failures,
        ),
        _check(
            "labels_and_classes_present",
            not label_class_failures,
            "Every candidate has a local event label and broad Lake class.",
            label_class_failures,
        ),
        _check(
            "candidate_files_declared",
            file_refs_declared,
            "Candidate file refs are declared for the future Lake handoff boundary.",
        ),
        _check(
            "no_sqlite_or_external_write_here",
            True,
            "Intake writes only local dry-run artifacts; SQLite persistence belongs to the Exception Lake runtime.",
        ),
    ]
    status = (
        "dry_run_ready_not_admitted"
        if all(check.status == "passed" for check in checks)
        else "failed"
    )
    return ExceptionLakeHandoffManifest(
        exception_lake_handoff_manifest_id=new_id("exchandoff"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        stage=stage,
        status=status,
        candidate_count=len(candidates),
        candidate_file_refs=candidate_file_refs,
        readiness_report_ref=readiness_report_ref,
        readiness_status=readiness_report.status,
        label_summaries=_label_summaries(candidates),
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_exception_lake_handoff_manifest(manifest: ExceptionLakeHandoffManifest) -> None:
    if manifest.status == "dry_run_ready_not_admitted":
        return
    failed = [check.check_id for check in manifest.checks if check.status == "failed"]
    raise ValueError("exception lake handoff manifest failed: " + ", ".join(failed))
