from __future__ import annotations

from typing import Any

from .models import ContextBoundaryCheck, ContextBoundaryReport, IntakePreflightPacket
from .util import new_id, now_iso


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    candidate_ids: list[str] | None = None,
    context_signal_refs: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> ContextBoundaryCheck:
    return ContextBoundaryCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        candidate_ids=candidate_ids or [],
        context_signal_refs=context_signal_refs or [],
        details=details or {},
    )


def _scored_candidates(packet: IntakePreflightPacket) -> list[tuple[str, Any]]:
    return [
        *[("inbound_event", candidate) for candidate in packet.inbound_event_candidates],
        *[("matter_family", candidate) for candidate in packet.matter_family_candidates],
        *[
            ("representation_posture", candidate)
            for candidate in packet.representation_posture_candidates
        ],
    ]


def _context_signal_refs(packet: IntakePreflightPacket) -> list[str]:
    refs = [
        ref for _, candidate in _scored_candidates(packet) for ref in candidate.context_signal_refs
    ]
    return sorted(set(refs))


def _unknown_option_failures(packet: IntakePreflightPacket) -> list[str]:
    failures: list[str] = []
    for surface, candidates in {
        "inbound_event": packet.inbound_event_candidates,
        "matter_family": packet.matter_family_candidates,
        "representation_posture": packet.representation_posture_candidates,
    }.items():
        if not any(
            candidate.label == "unknown"
            and candidate.source_evidence_status == "unknown_option"
            and candidate.calibration_label == "unknown_option"
            for candidate in candidates
        ):
            failures.append(surface)
    return failures


def build_context_boundary_report(packet: IntakePreflightPacket) -> ContextBoundaryReport:
    scored = _scored_candidates(packet)
    context_signal_candidates = [
        (surface, candidate) for surface, candidate in scored if candidate.context_signal_refs
    ]
    context_only = [
        (surface, candidate)
        for surface, candidate in context_signal_candidates
        if candidate.source_evidence_status == "source_anchor_only"
    ]
    observed_with_context = [
        (surface, candidate)
        for surface, candidate in context_signal_candidates
        if candidate.source_evidence_status == "observed_support"
    ]
    unknown_options = [
        (surface, candidate)
        for surface, candidate in scored
        if candidate.source_evidence_status == "unknown_option"
    ]
    context_refs = _context_signal_refs(packet)
    profile_ref_prefix = f"practice-profile://{packet.effective_context.profile_id}/"
    invalid_context_refs = [ref for ref in context_refs if not ref.startswith(profile_ref_prefix)]
    precedence = packet.effective_context.context_precedence
    context_influenced_leaks = [
        f"{surface}:{candidate.label}"
        for surface, candidate in context_signal_candidates
        if candidate.calibration_label == "context_influenced"
        and candidate.source_evidence_status != "source_anchor_only"
    ]
    source_anchor_calibration_failures = [
        f"{surface}:{candidate.label}"
        for surface, candidate in context_only
        if candidate.calibration_label != "context_influenced"
    ]
    observed_context_failures = [
        f"{surface}:{candidate.label}"
        for surface, candidate in observed_with_context
        if not candidate.observed_evidence_refs
        or candidate.calibration_label == "context_influenced"
    ]
    context_candidates_without_packet_anchor = [
        f"{surface}:{candidate.label}"
        for surface, candidate in context_signal_candidates
        if not candidate.observed_evidence_refs
    ]
    unknown_option_failures = _unknown_option_failures(packet)

    checks = [
        _check(
            "context_precedence_preserves_observed_evidence",
            bool(precedence and precedence[0] == "observed_source_evidence"),
            "Observed source evidence stays first in the effective context precedence.",
            details={"context_precedence": precedence},
        ),
        _check(
            "context_refs_are_structured_profile_refs",
            not invalid_context_refs,
            "Context influence refs stay structured practice-profile refs, not source evidence.",
            context_signal_refs=context_refs,
            details={"invalid_context_refs": invalid_context_refs},
        ),
        _check(
            "context_influence_not_observed_fact",
            not context_influenced_leaks
            and not source_anchor_calibration_failures
            and not observed_context_failures,
            "Context-influenced candidates stay source-anchor-only unless independently observed.",
            candidate_ids=[candidate.candidate_id for _, candidate in context_signal_candidates],
            context_signal_refs=context_refs,
            details={
                "context_influenced_leaks": context_influenced_leaks,
                "source_anchor_calibration_failures": source_anchor_calibration_failures,
                "observed_context_failures": observed_context_failures,
            },
        ),
        _check(
            "context_candidates_remain_packet_anchored",
            not context_candidates_without_packet_anchor,
            "Context-influenced alternatives remain bound to source anchors for review.",
            candidate_ids=[candidate.candidate_id for _, candidate in context_signal_candidates],
            details={
                "context_candidates_without_packet_anchor": (
                    context_candidates_without_packet_anchor
                )
            },
        ),
        _check(
            "unknown_options_preserved_for_human_review",
            not unknown_option_failures,
            "Unknown options remain available for human review on scored candidate surfaces.",
            details={"missing_unknown_option_surfaces": unknown_option_failures},
        ),
        _check(
            "human_confirmation_required_for_context_ranked_candidates",
            packet.human_confirmation_required is True,
            "Matter family, representation posture, and principal roles still require human confirmation.",
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ContextBoundaryReport(
        context_boundary_report_id=new_id("contextboundary"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        status=status,
        effective_context_id=packet.effective_context.context_id,
        profile_id=packet.effective_context.profile_id,
        profile_version=packet.effective_context.profile_version,
        profile_sha256=packet.effective_context.profile_sha256,
        human_confirmation_required=packet.human_confirmation_required,
        checked_candidate_count=len(scored),
        context_signal_candidate_count=len(context_signal_candidates),
        context_only_candidate_count=len(context_only),
        observed_with_context_candidate_count=len(observed_with_context),
        unknown_option_count=len(unknown_options),
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_context_boundary_report(report: ContextBoundaryReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("context boundary failed: " + ", ".join(failed))
