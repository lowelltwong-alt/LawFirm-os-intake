from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    ContextCounterfactualAuditCheck,
    ContextCounterfactualAuditReport,
    EvidenceRef,
    IntakePreflightPacket,
    ScoredCandidate,
)
from .util import load_json, new_id, now_iso, write_json
from .workflow import run_preflight


BASELINE_CONTEXT_ONLY_LABEL = "medical_malpractice_defense"
OBSERVED_LABEL = "plaintiff_personal_injury"
UNKNOWN_LABEL = "unknown"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> ContextCounterfactualAuditCheck:
    return ContextCounterfactualAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        details=details or {},
    )


def _ref_signature(ref: EvidenceRef) -> tuple[str, int, int, str]:
    return (ref.source_id, ref.start_offset, ref.end_offset, ref.sha256)


def _ref_signatures(refs: list[EvidenceRef]) -> list[tuple[str, int, int, str]]:
    return sorted({_ref_signature(ref) for ref in refs})


def _source_inventory_signature(packet: IntakePreflightPacket) -> list[tuple[Any, ...]]:
    return sorted(
        (
            item.source_id,
            item.source_type,
            item.read_state,
            item.availability_state,
            item.character_count,
            item.source_sha256,
            item.duplicate_of_source_id,
            tuple(item.attachment_refs),
        )
        for item in packet.source_inventory
    )


def _segment_signature(packet: IntakePreflightPacket) -> list[tuple[Any, ...]]:
    return sorted(
        (
            segment.source_id,
            segment.segment_type,
            segment.sequence,
            segment.start_offset,
            segment.end_offset,
            segment.sha256,
            segment.structural_path,
            segment.attachment_ref,
            segment.source_instruction_risk,
        )
        for segment in packet.segments
    )


def _candidate_map(packet: IntakePreflightPacket) -> dict[str, ScoredCandidate]:
    return {candidate.label: candidate for candidate in packet.matter_family_candidates}


def _evidence_by_label(packet: IntakePreflightPacket) -> dict[str, list[tuple[str, int, int, str]]]:
    return {
        candidate.label: _ref_signatures(candidate.observed_evidence_refs)
        for candidate in packet.matter_family_candidates
    }


def _edge_relationships_for_candidate(graph_path: Path, candidate_id: str) -> set[str]:
    graph = load_json(graph_path)
    return {
        edge["relationship"]
        for edge in graph.get("edges", [])
        if edge.get("target_node_id") == candidate_id
    }


def build_context_counterfactual_audit_report(
    *,
    input_path: str | Path,
    baseline_profile_path: str | Path,
    comparison_profile_path: str | Path,
    baseline_packet: IntakePreflightPacket,
    comparison_packet: IntakePreflightPacket,
    baseline_run_dir: str | Path,
    comparison_run_dir: str | Path,
) -> ContextCounterfactualAuditReport:
    input_path = Path(input_path)
    baseline_profile_path = Path(baseline_profile_path)
    comparison_profile_path = Path(comparison_profile_path)
    baseline_run_dir = Path(baseline_run_dir)
    comparison_run_dir = Path(comparison_run_dir)

    baseline_candidates = _candidate_map(baseline_packet)
    comparison_candidates = _candidate_map(comparison_packet)
    baseline_observed = baseline_candidates.get(OBSERVED_LABEL)
    comparison_observed = comparison_candidates.get(OBSERVED_LABEL)
    baseline_context_only = baseline_candidates.get(BASELINE_CONTEXT_ONLY_LABEL)
    baseline_unknown = baseline_candidates.get(UNKNOWN_LABEL)
    evidence_stability_failures = []
    baseline_evidence_by_label = _evidence_by_label(baseline_packet)
    comparison_evidence_by_label = _evidence_by_label(comparison_packet)
    for label in sorted(set(baseline_evidence_by_label) & set(comparison_evidence_by_label)):
        if baseline_evidence_by_label[label] != comparison_evidence_by_label[label]:
            evidence_stability_failures.append(label)

    baseline_graph_path = baseline_run_dir / "evidence_graph.json"
    context_edges = (
        _edge_relationships_for_candidate(baseline_graph_path, baseline_context_only.candidate_id)
        if baseline_context_only
        else set()
    )
    observed_edges = (
        _edge_relationships_for_candidate(baseline_graph_path, baseline_observed.candidate_id)
        if baseline_observed
        else set()
    )

    checks = [
        _check(
            "both_preflight_runs_completed",
            baseline_packet.status == "human_intake_review_required"
            and comparison_packet.status == "human_intake_review_required"
            and baseline_packet.data_origin == "synthetic"
            and comparison_packet.data_origin == "synthetic",
            "Both counterfactual runs completed as synthetic human-review preflight packets.",
            artifact_refs=[
                str(baseline_run_dir / "intake_preflight_packet.json"),
                str(comparison_run_dir / "intake_preflight_packet.json"),
            ],
        ),
        _check(
            "source_inventory_stable",
            _source_inventory_signature(baseline_packet)
            == _source_inventory_signature(comparison_packet),
            "Source inventory state, hashes, and coverage inputs are unchanged across profiles.",
            artifact_refs=[
                str(baseline_run_dir / "source_inventory.json"),
                str(comparison_run_dir / "source_inventory.json"),
            ],
        ),
        _check(
            "segment_signatures_stable",
            _segment_signature(baseline_packet) == _segment_signature(comparison_packet),
            "Segment source IDs, types, offsets, hashes, and structural paths are unchanged across profiles.",
            artifact_refs=[
                str(baseline_run_dir / "segments.json"),
                str(comparison_run_dir / "segments.json"),
            ],
        ),
        _check(
            "observed_evidence_refs_stable",
            not evidence_stability_failures,
            "Observed evidence signatures for common matter labels are unchanged across profiles.",
            artifact_refs=[
                str(baseline_run_dir / "intake_preflight_packet.json"),
                str(comparison_run_dir / "intake_preflight_packet.json"),
            ],
            details={"labels_with_drift": evidence_stability_failures},
        ),
        _check(
            "practice_context_changes_ranking",
            bool(
                baseline_observed
                and comparison_observed
                and comparison_observed.confidence > baseline_observed.confidence
            ),
            "Practice profile changes candidate ranking/confidence without changing source evidence.",
            artifact_refs=[
                str(baseline_run_dir / "effective_context.json"),
                str(comparison_run_dir / "effective_context.json"),
            ],
            details={
                "baseline_label": OBSERVED_LABEL,
                "baseline_confidence": baseline_observed.confidence if baseline_observed else None,
                "comparison_confidence": comparison_observed.confidence
                if comparison_observed
                else None,
            },
        ),
        _check(
            "context_only_candidate_not_observed_fact",
            bool(
                baseline_context_only
                and baseline_context_only.calibration_label == "context_influenced"
                and baseline_context_only.source_evidence_status == "source_anchor_only"
                and baseline_context_only.context_signal_refs
                and context_edges == {"anchors_matter_family_candidate"}
            ),
            "Context-influenced candidate is anchored for review and not rendered as observed support.",
            artifact_refs=[str(baseline_graph_path)],
            details={
                "label": BASELINE_CONTEXT_ONLY_LABEL,
                "edge_relationships": sorted(context_edges),
            },
        ),
        _check(
            "observed_candidate_keeps_support_edge",
            bool(
                baseline_observed
                and baseline_observed.source_evidence_status == "observed_support"
                and observed_edges == {"supports_matter_candidate"}
            ),
            "Observed matter candidate keeps a support edge rather than context-only anchor semantics.",
            artifact_refs=[str(baseline_graph_path)],
            details={
                "label": OBSERVED_LABEL,
                "edge_relationships": sorted(observed_edges),
            },
        ),
        _check(
            "unknown_option_preserved",
            bool(
                baseline_unknown
                and baseline_unknown.source_evidence_status == "unknown_option"
                and baseline_unknown.calibration_label == "unknown_option"
            ),
            "Explicit unknown option remains available for human review.",
            artifact_refs=[str(baseline_run_dir / "intake_preflight_packet.json")],
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ContextCounterfactualAuditReport(
        context_counterfactual_audit_report_id=new_id("context_counterfactual_audit"),
        status=status,
        input_ref=str(input_path),
        baseline_profile_ref=str(baseline_profile_path),
        comparison_profile_ref=str(comparison_profile_path),
        baseline_run_dir=str(baseline_run_dir),
        comparison_run_dir=str(comparison_run_dir),
        checks=checks,
        generated_at=now_iso(),
    )


def run_context_counterfactual_audit(
    *,
    input_path: str | Path,
    baseline_profile_path: str | Path,
    comparison_profile_path: str | Path,
    out_dir: str | Path,
) -> tuple[ContextCounterfactualAuditReport, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_packet, baseline_run_dir = run_preflight(
        input_path,
        baseline_profile_path,
        out_dir / "baseline",
    )
    comparison_packet, comparison_run_dir = run_preflight(
        input_path,
        comparison_profile_path,
        out_dir / "comparison",
    )
    report = build_context_counterfactual_audit_report(
        input_path=input_path,
        baseline_profile_path=baseline_profile_path,
        comparison_profile_path=comparison_profile_path,
        baseline_packet=baseline_packet,
        comparison_packet=comparison_packet,
        baseline_run_dir=baseline_run_dir,
        comparison_run_dir=comparison_run_dir,
    )
    write_json(out_dir / "context_counterfactual_audit_report.json", report.model_dump(mode="json"))
    enforce_context_counterfactual_audit(report)
    return report, out_dir


def enforce_context_counterfactual_audit(report: ContextCounterfactualAuditReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("context counterfactual audit failed: " + ", ".join(failed))
