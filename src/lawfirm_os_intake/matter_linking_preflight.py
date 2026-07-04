from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    MatterLinkingPreflightCheck,
    MatterLinkingPreflightCluster,
    MatterLinkingPreflightReport,
)
from .util import digest_json, load_json, now_iso, write_json


MATTER_LINKING_PREFLIGHT_REPORT_FILENAME = "matter_linking_preflight_report.json"
MATTER_LINKING_PREFLIGHT_NOTES_FILENAME = "matter_linking_preflight_report.md"

AMBIGUOUS_REQUIRED_EXCEPTION_LABELS = {
    "source_matter_link_ambiguous",
    "multiple_possible_matters_same_sender",
    "missing_official_matter_number",
    "document_cluster_split_required",
}

RESOLVED_SPLIT_REQUIRED_EXCEPTION_LABELS = {
    "source_matter_link_resolved_candidate",
    "missing_official_matter_number",
    "document_cluster_split_resolved_candidate",
    "human_matter_linking_confirmation_required",
}

RESOLVED_SINGLE_REQUIRED_EXCEPTION_LABELS = {
    "source_matter_link_resolved_candidate",
    "missing_official_matter_number",
    "human_matter_linking_confirmation_required",
}

WEAK_ONLY_REQUIRED_EXCEPTION_LABELS = {
    "source_matter_link_weak_only_candidate",
    "missing_official_matter_number",
    "sender_reference_followup_required",
    "human_matter_linking_confirmation_required",
}

BASE_REQUIRED_NEXT_GATES = [
    "human_matter_linking_review",
    "conflict_seed_review",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_matter_linking_preflight",
]
SENDER_REFERENCE_FOLLOWUP_GATE = "sender_reference_followup"
REQUIRED_NEXT_GATES = [*BASE_REQUIRED_NEXT_GATES, SENDER_REFERENCE_FOLLOWUP_GATE]

RESOLVED_LINK_STATES = {
    "resolved_split_candidates_pending_human_confirmation",
    "resolved_single_candidate_pending_human_confirmation",
}

WEAK_ONLY_LINK_STATES = {
    "weak_single_candidate_requires_followup",
    "weak_cluster_candidate_requires_followup",
}

RESOLUTION_SIGNAL_TYPES = {
    "sender_followup_claim_cluster_confirmation",
    "sender_confirmed_document_cluster",
    "upfront_like_request_id",
}

PROHIBITED_BOUNDARY_FLAGS = [
    "upfront_connector_implemented",
    "vendor_api_called",
    "external_write_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "matter_opening_authorized",
    "budget_amount_output_authorized",
    "budget_submission_authorized",
    "conflict_conclusion_emitted",
    "screen_created",
    "silent_learning_performed",
]

WEAK_OR_NON_UNIQUE_SIGNAL_TYPES = {
    "same_sender",
    "same_carrier",
    "sender_internal_reference",
}


def run_matter_linking_preflight(
    *,
    input_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkingPreflightReport, Path]:
    source_path = Path(input_path)
    payload = load_json(source_path)
    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref=str(source_path),
        generated_at=generated_at or now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / MATTER_LINKING_PREFLIGHT_NOTES_FILENAME).write_text(
        render_matter_linking_preflight_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def build_matter_linking_preflight_report(
    *,
    payload: dict[str, Any],
    source_artifact_ref: str,
    generated_at: str,
) -> MatterLinkingPreflightReport:
    if not isinstance(payload, dict):
        raise ValueError("matter-linking preflight input must be a JSON object")

    source_system = _mapping(payload.get("source_system"))
    linking = _mapping(payload.get("matter_linking"))
    boundaries = _mapping(payload.get("output_boundaries"))
    source_hashes_by_id = _source_hashes_by_id(payload)
    clusters = _clusters(linking, source_hashes_by_id)
    negative_split_required = _negative_split_evidence_required(
        linking=linking,
        cluster_count=len(clusters),
    )
    weak_signals = _list_of_mappings(linking.get("weak_signals_not_sufficient_for_merge"))
    weak_signal_types = sorted(
        {
            str(signal.get("signal_type"))
            for signal in weak_signals
            if isinstance(signal.get("signal_type"), str)
        }
    )
    labels = sorted(str(label) for label in payload.get("candidate_exception_lake_labels", []))
    required_next_gates = _required_next_gates(payload=payload, linking=linking)

    checks = _checks(
        payload=payload,
        source_system=source_system,
        linking=linking,
        boundaries=boundaries,
        clusters=clusters,
        weak_signal_types=weak_signal_types,
        labels=labels,
        source_hashes_by_id=source_hashes_by_id,
        negative_split_required=negative_split_required,
    )
    if any(check.status == "failed" for check in checks):
        status = "blocked_matter_linking_preflight"
    elif _is_resolved_link_state(linking):
        status = "matter_linking_preflight_resolved_candidate_requires_review"
    else:
        status = "matter_linking_preflight_requires_review"
    report_core = {
        "source_artifact_id": payload.get("artifact_id", "unknown"),
        "source_artifact_hash": digest_json(payload),
        "cluster_ids": [cluster.cluster_id for cluster in clusters],
        "weak_signal_types": weak_signal_types,
        "labels": labels,
        "failed_checks": [check.check_id for check in checks if check.status == "failed"],
    }
    return MatterLinkingPreflightReport(
        matter_linking_preflight_report_id=(
            "matterlinkpreflight_" + digest_json(report_core)[len("sha256:") : len("sha256:") + 20]
        ),
        status=status,
        source_artifact_ref=source_artifact_ref,
        source_artifact_id=str(payload.get("artifact_id", "unknown")),
        source_artifact_type=str(payload.get("artifact_type", "unknown")),
        source_artifact_status=str(payload.get("status", "unknown")),
        source_artifact_hash=digest_json(payload),
        data_origin=str(payload.get("data_origin", "unknown")),
        source_system_name=str(source_system.get("system_name", "unknown")),
        real_upfront_export=bool(source_system.get("real_upfront_export")),
        api_contract_verified=bool(source_system.get("api_contract_verified")),
        official_matter_number_status=str(linking.get("official_matter_number_status", "unknown")),
        overall_link_state=str(linking.get("overall_link_state", "unknown")),
        requires_human_confirmation=bool(linking.get("requires_human_confirmation")),
        requires_sender_followup=bool(linking.get("requires_sender_followup")),
        cluster_count=len(clusters),
        high_evidence_candidate_count=sum(
            1 for cluster in clusters if "high_evidence" in cluster.match_strength
        ),
        weak_signal_count=len(weak_signals),
        weak_only_candidate_count=sum(1 for cluster in clusters if cluster.weak_only_candidate),
        negative_split_evidence_required=negative_split_required,
        strong_negative_signal_count=sum(
            cluster.strong_negative_signal_count for cluster in clusters
        ),
        source_count=len(source_hashes_by_id),
        source_hashes_by_id=source_hashes_by_id,
        weak_merge_signal_types=weak_signal_types,
        candidate_exception_lake_labels=labels,
        clusters=clusters,
        checks=checks,
        required_next_gates=required_next_gates,
        sender_followup_required=bool(linking.get("requires_sender_followup")),
        upfront_connector_implemented=bool(boundaries.get("upfront_connector_implemented")),
        vendor_api_called=bool(boundaries.get("vendor_api_called")),
        external_write_performed=bool(boundaries.get("external_write_performed")),
        lake_write_performed=bool(boundaries.get("lake_write_performed")),
        sqlite_write_performed=bool(boundaries.get("sqlite_write_performed")),
        matter_opening_authorized=bool(boundaries.get("matter_opening_authorized")),
        budget_amount_output_authorized=bool(boundaries.get("budget_amount_output_authorized")),
        budget_submission_authorized=bool(boundaries.get("budget_submission_authorized")),
        conflict_conclusion_emitted=bool(boundaries.get("conflict_conclusion_emitted")),
        screen_created=bool(boundaries.get("screen_created")),
        silent_learning_performed=bool(boundaries.get("silent_learning_performed")),
        generated_at=generated_at,
    )


def render_matter_linking_preflight_report(report: MatterLinkingPreflightReport) -> str:
    lines = [
        "# Matter-Linking Preflight Report",
        "",
        f"**Report ID:** {report.matter_linking_preflight_report_id}",
        f"**Status:** {report.status}",
        f"**Source artifact:** `{report.source_artifact_ref}`",
        f"**Source artifact ID:** `{report.source_artifact_id}`",
        f"**Overall link state:** {report.overall_link_state}",
        f"**Official matter number status:** {report.official_matter_number_status}",
        "",
        "## Summary",
        "",
        f"- Candidate clusters: {report.cluster_count}",
        f"- High-evidence candidates, not authorized: {report.high_evidence_candidate_count}",
        f"- Weak-only candidates blocked: {report.weak_only_candidate_count}",
        f"- Weak merge signals rejected: {report.weak_signal_count}",
        f"- Negative split evidence required: {report.negative_split_evidence_required}",
        f"- Strong negative split signals: {report.strong_negative_signal_count}",
        f"- Requires human confirmation: {report.requires_human_confirmation}",
        f"- Requires sender follow-up: {report.requires_sender_followup}",
        f"- Candidate-only resolved status: {report.status}",
        "",
        "## Clusters",
        "",
    ]
    for cluster in report.clusters:
        lines.extend(
            [
                f"- `{cluster.cluster_id}`: {cluster.match_strength}",
                f"  Label: {cluster.proposed_short_label or 'unknown'}",
                f"  Sources: {', '.join(f'`{source_id}`' for source_id in cluster.source_ids)}",
                f"  Source-bound strong support: {cluster.source_bound_strong_support_present}",
                f"  Weak-only candidate: {cluster.weak_only_candidate}",
                f"  Negative split evidence required: {cluster.negative_split_evidence_required}",
                f"  Supporting signal types: {', '.join(cluster.supporting_signal_types)}",
                f"  Negative signal types: {', '.join(cluster.negative_signal_types)}",
            ]
        )
    lines.extend(["", "## Weak Signals Not Sufficient For Merge", ""])
    lines.extend(f"- `{signal_type}`" for signal_type in report.weak_merge_signal_types)
    lines.extend(["", "## Candidate Exception Lake Labels", ""])
    lines.extend(f"- `{label}`" for label in report.candidate_exception_lake_labels)
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        blocking = (
            "; blocking refs=" + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
            if check.blocking_refs
            else ""
        )
        lines.append(f"- `{check.check_id}`: {check.status}; {check.message}{blocking}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report is a local synthetic/candidate-only matter-linking audit. "
            "It does not call Upfront, create a screen, clear conflicts, output a budget "
            "amount, open a matter, write Lake/SQLite records, submit a budget, or learn "
            "from reviewer corrections.",
            "",
        ]
    )
    return "\n".join(lines)


def _clusters(
    linking: dict[str, Any],
    source_hashes_by_id: dict[str, str],
) -> list[MatterLinkingPreflightCluster]:
    clusters: list[MatterLinkingPreflightCluster] = []
    raw_clusters = _list_of_mappings(linking.get("candidate_clusters"))
    negative_split_required = _negative_split_evidence_required(
        linking=linking,
        cluster_count=len(raw_clusters),
    )
    for raw_cluster in raw_clusters:
        supporting = _list_of_mappings(raw_cluster.get("supporting_signals"))
        negative = _list_of_mappings(raw_cluster.get("negative_signals"))
        strong_supporting = [
            signal
            for signal in supporting
            if signal.get("weight_class") == "strong"
            and signal.get("signal_type") not in WEAK_OR_NON_UNIQUE_SIGNAL_TYPES
        ]
        source_bound_strong_support_present = bool(strong_supporting) and all(
            _signal_has_known_source_ref(signal, source_hashes_by_id)
            for signal in strong_supporting
        )
        source_ids = [str(source_id) for source_id in raw_cluster.get("source_ids", [])]
        unique_source_ids = sorted(set(source_ids))
        clusters.append(
            MatterLinkingPreflightCluster(
                cluster_id=str(raw_cluster.get("cluster_id", "unknown")),
                link_state=str(raw_cluster.get("link_state", "unknown")),
                match_strength=str(raw_cluster.get("match_strength", "unknown")),
                proposed_short_label=raw_cluster.get("proposed_short_label"),
                source_ids=source_ids,
                source_hashes=[
                    source_hashes_by_id[source_id]
                    for source_id in unique_source_ids
                    if source_id in source_hashes_by_id
                ],
                supporting_signal_count=len(supporting),
                strong_supporting_signal_count=len(strong_supporting),
                negative_signal_count=len(negative),
                strong_negative_signal_count=sum(
                    1 for signal in negative if signal.get("weight_class") == "strong"
                ),
                supporting_signal_types=sorted(
                    {
                        str(signal.get("signal_type"))
                        for signal in supporting
                        if isinstance(signal.get("signal_type"), str)
                    }
                ),
                negative_signal_types=sorted(
                    {
                        str(signal.get("signal_type"))
                        for signal in negative
                        if isinstance(signal.get("signal_type"), str)
                    }
                ),
                source_bound_strong_support_present=source_bound_strong_support_present,
                weak_only_candidate=not source_bound_strong_support_present,
                negative_split_evidence_required=negative_split_required,
            )
        )
    return clusters


def _checks(
    *,
    payload: dict[str, Any],
    source_system: dict[str, Any],
    linking: dict[str, Any],
    boundaries: dict[str, Any],
    clusters: list[MatterLinkingPreflightCluster],
    weak_signal_types: list[str],
    labels: list[str],
    source_hashes_by_id: dict[str, str],
    negative_split_required: bool,
) -> list[MatterLinkingPreflightCheck]:
    missing_boundary_flags = [flag for flag in PROHIBITED_BOUNDARY_FLAGS if flag not in boundaries]
    boundary_violations = [
        flag
        for flag in PROHIBITED_BOUNDARY_FLAGS
        if flag in boundaries and bool(boundaries.get(flag)) is not False
    ]
    cluster_refs_missing = _clusters_missing_source_bound_support(linking, source_hashes_by_id)
    weak_only_missing = [cluster.cluster_id for cluster in clusters if cluster.weak_only_candidate]
    weak_promoted = _clusters_with_promoted_weak_support(linking)
    negative_missing = (
        _clusters_missing_negative_split_support(linking, source_hashes_by_id)
        if negative_split_required
        else []
    )
    split_cardinality_failure = _split_cardinality_failure(
        linking=linking,
        cluster_count=len(clusters),
    )
    resolution_missing = (
        _clusters_missing_resolution_support(linking, source_hashes_by_id)
        if _is_resolved_link_state(linking)
        else []
    )
    missing_labels = sorted(_required_exception_labels(linking).difference(labels))
    return [
        _check(
            "input_is_synthetic_candidate_only",
            payload.get("data_origin") == "synthetic"
            and payload.get("candidate_only") is True
            and payload.get("synthetic_only") is True
            and payload.get("non_authoritative") is True,
            "Input remains synthetic, candidate-only, and non-authoritative.",
            evidence_refs=[str(payload.get("artifact_id", "unknown"))],
        ),
        _check(
            "not_real_upfront_export_or_api_contract",
            source_system.get("real_upfront_export") is False
            and source_system.get("api_contract_verified") is False,
            "The fixture is an Upfront-like public-research proxy, not a verified export/API contract.",
            evidence_refs=[str(source_system.get("system_name", "unknown"))],
        ),
        _check(
            "no_connector_or_external_write",
            not boundary_violations and not missing_boundary_flags,
            "No connector, vendor API call, external write, Lake/SQLite write, screen, matter opening, budget authorization, conflict conclusion, or silent learning is present.",
            blocking_refs=[*missing_boundary_flags, *boundary_violations],
        ),
        _check(
            "link_state_cluster_cardinality_valid",
            not split_cardinality_failure,
            "Split states require at least two candidate clusters; single-candidate states require exactly one cluster.",
            evidence_refs=[str(linking.get("overall_link_state", "unknown"))],
            blocking_refs=split_cardinality_failure,
        ),
        _check(
            "official_matter_number_missing_is_explicit",
            linking.get("official_matter_number_status") == "not_available",
            "Missing official firm matter number is explicit.",
            evidence_refs=["matter_linking.official_matter_number_status"],
        ),
        _check(
            "multiple_candidate_clusters_require_review",
            len(clusters) >= 1
            and str(linking.get("overall_link_state"))
            in {
                "ambiguous_multiple_candidates",
                *RESOLVED_LINK_STATES,
            }
            and linking.get("requires_human_confirmation") is True,
            "Candidate clusters remain blocked for human linking review.",
            evidence_refs=[cluster.cluster_id for cluster in clusters],
        ),
        _check(
            "weak_sender_carrier_signals_do_not_merge",
            {"same_sender", "same_carrier"}.issubset(set(weak_signal_types)),
            "Same sender and same carrier are recorded as weak signals, not merge authority.",
            evidence_refs=weak_signal_types,
        ),
        _check(
            "weak_only_candidates_block_matter_linking",
            not weak_only_missing,
            "A candidate matter link needs source-bound matter-specific strong support; same sender, same carrier, or sender references alone are not enough.",
            evidence_refs=[cluster.cluster_id for cluster in clusters],
            blocking_refs=weak_only_missing,
        ),
        _check(
            "weak_signals_cannot_be_promoted_to_strong_support",
            not weak_promoted,
            "Same sender, same carrier, and sender internal references cannot become strong matter-linking support.",
            evidence_refs=[cluster.cluster_id for cluster in clusters],
            blocking_refs=weak_promoted,
        ),
        _check(
            "clusters_have_source_bound_strong_support",
            not cluster_refs_missing,
            "Every cluster has source-bound strong support mapped to known source hashes.",
            evidence_refs=[cluster.cluster_id for cluster in clusters],
            blocking_refs=cluster_refs_missing,
        ),
        _check(
            "resolved_candidates_have_source_bound_resolution_signal",
            not resolution_missing,
            "Resolved candidates include source-bound sender/request resolution signals.",
            evidence_refs=[cluster.cluster_id for cluster in clusters],
            blocking_refs=resolution_missing,
        ),
        _check(
            "clusters_have_negative_split_evidence",
            not negative_missing,
            (
                "Competing clusters have strong negative split evidence against the other candidate matter."
                if negative_split_required
                else "Single-candidate matter-linking inputs do not require negative split evidence."
            ),
            evidence_refs=[cluster.cluster_id for cluster in clusters],
            blocking_refs=negative_missing,
        ),
        _check(
            "candidate_exception_labels_include_matter_linking",
            not missing_labels,
            "Candidate Exception Lake labels preserve the matter-linking ambiguity class.",
            evidence_refs=labels,
            blocking_refs=missing_labels,
        ),
        _check(
            "required_gates_block_budget_and_matter_opening",
            set(_required_next_gates(payload={}, linking=linking)).issubset(
                set(payload.get("required_next_gates", []))
            ),
            "Next gates block budget output and matter opening until linking and roles are confirmed.",
            evidence_refs=list(payload.get("required_next_gates", [])),
        ),
    ]


def _clusters_missing_source_bound_support(
    linking: dict[str, Any],
    source_hashes_by_id: dict[str, str],
) -> list[str]:
    missing: list[str] = []
    for raw_cluster in _list_of_mappings(linking.get("candidate_clusters")):
        cluster_id = str(raw_cluster.get("cluster_id", "unknown"))
        strong_signals = [
            signal
            for signal in _list_of_mappings(raw_cluster.get("supporting_signals"))
            if signal.get("weight_class") == "strong"
            and signal.get("signal_type") not in WEAK_OR_NON_UNIQUE_SIGNAL_TYPES
        ]
        if not strong_signals:
            missing.append(cluster_id)
            continue
        if any(
            not _signal_has_known_source_ref(signal, source_hashes_by_id)
            for signal in strong_signals
        ):
            missing.append(cluster_id)
    return sorted(set(missing))


def _clusters_with_promoted_weak_support(linking: dict[str, Any]) -> list[str]:
    promoted: list[str] = []
    for raw_cluster in _list_of_mappings(linking.get("candidate_clusters")):
        cluster_id = str(raw_cluster.get("cluster_id", "unknown"))
        if any(
            signal.get("weight_class") == "strong"
            and signal.get("signal_type") in WEAK_OR_NON_UNIQUE_SIGNAL_TYPES
            for signal in _list_of_mappings(raw_cluster.get("supporting_signals"))
        ):
            promoted.append(cluster_id)
    return sorted(set(promoted))


def _clusters_missing_negative_split_support(
    linking: dict[str, Any],
    source_hashes_by_id: dict[str, str],
) -> list[str]:
    missing: list[str] = []
    for raw_cluster in _list_of_mappings(linking.get("candidate_clusters")):
        cluster_id = str(raw_cluster.get("cluster_id", "unknown"))
        strong_negative = [
            signal
            for signal in _list_of_mappings(raw_cluster.get("negative_signals"))
            if signal.get("weight_class") == "strong"
        ]
        if not strong_negative:
            missing.append(cluster_id)
            continue
        if any(
            not _signal_has_known_source_ref(signal, source_hashes_by_id)
            for signal in strong_negative
        ):
            missing.append(cluster_id)
    return sorted(set(missing))


def _clusters_missing_resolution_support(
    linking: dict[str, Any],
    source_hashes_by_id: dict[str, str],
) -> list[str]:
    missing: list[str] = []
    for raw_cluster in _list_of_mappings(linking.get("candidate_clusters")):
        cluster_id = str(raw_cluster.get("cluster_id", "unknown"))
        resolution_signals = [
            signal
            for signal in _list_of_mappings(raw_cluster.get("supporting_signals"))
            if signal.get("weight_class") == "strong"
            and signal.get("signal_type") in RESOLUTION_SIGNAL_TYPES
        ]
        if not resolution_signals or any(
            not _signal_has_known_source_ref(signal, source_hashes_by_id)
            for signal in resolution_signals
        ):
            missing.append(cluster_id)
    return sorted(set(missing))


def _required_exception_labels(linking: dict[str, Any]) -> set[str]:
    if _is_weak_only_link_state(linking):
        return WEAK_ONLY_REQUIRED_EXCEPTION_LABELS
    if _is_resolved_single_link_state(linking):
        return RESOLVED_SINGLE_REQUIRED_EXCEPTION_LABELS
    if _is_resolved_link_state(linking):
        return RESOLVED_SPLIT_REQUIRED_EXCEPTION_LABELS
    return AMBIGUOUS_REQUIRED_EXCEPTION_LABELS


def _required_next_gates(payload: dict[str, Any], linking: dict[str, Any]) -> list[str]:
    gates = set(BASE_REQUIRED_NEXT_GATES)
    if linking.get("requires_sender_followup") is True:
        gates.add(SENDER_REFERENCE_FOLLOWUP_GATE)
    gates.update(str(gate) for gate in payload.get("required_next_gates", []))
    return sorted(gates)


def _is_resolved_link_state(linking: dict[str, Any]) -> bool:
    return str(linking.get("overall_link_state")) in RESOLVED_LINK_STATES


def _is_resolved_single_link_state(linking: dict[str, Any]) -> bool:
    return str(linking.get("overall_link_state")) == (
        "resolved_single_candidate_pending_human_confirmation"
    )


def _is_weak_only_link_state(linking: dict[str, Any]) -> bool:
    return str(linking.get("overall_link_state")) in WEAK_ONLY_LINK_STATES


def _negative_split_evidence_required(*, linking: dict[str, Any], cluster_count: int) -> bool:
    return cluster_count > 1 or str(linking.get("overall_link_state")) in {
        "ambiguous_multiple_candidates",
        "resolved_split_candidates_pending_human_confirmation",
    }


def _split_cardinality_failure(*, linking: dict[str, Any], cluster_count: int) -> list[str]:
    state = str(linking.get("overall_link_state", "unknown"))
    if (
        state
        in {
            "ambiguous_multiple_candidates",
            "resolved_split_candidates_pending_human_confirmation",
        }
        and cluster_count < 2
    ):
        return [f"{state}:requires_at_least_two_clusters"]
    if (
        state
        in {
            "resolved_single_candidate_pending_human_confirmation",
            *WEAK_ONLY_LINK_STATES,
        }
        and cluster_count != 1
    ):
        return [f"{state}:requires_exactly_one_cluster"]
    return []


def _signal_has_known_source_ref(
    signal: dict[str, Any],
    source_hashes_by_id: dict[str, str],
) -> bool:
    refs = [str(ref) for ref in signal.get("source_refs", [])]
    if not refs:
        return False
    return all(_source_ref_is_known_and_located(ref, source_hashes_by_id) for ref in refs)


def _source_ref_is_known_and_located(
    ref: str,
    source_hashes_by_id: dict[str, str],
) -> bool:
    source_id, separator, locator = ref.partition(":")
    return bool(separator and locator and source_id in source_hashes_by_id)


def _source_id_from_ref(ref: str) -> str:
    return ref.split(":", 1)[0]


def _source_hashes_by_id(payload: dict[str, Any]) -> dict[str, str]:
    source_hashes: dict[str, str] = {}
    for source in _list_of_mappings(payload.get("source_inventory")):
        source_id = source.get("source_id")
        source_hash = source.get("source_hash")
        if isinstance(source_id, str) and isinstance(source_hash, str):
            source_hashes[source_id] = source_hash
    return source_hashes


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> MatterLinkingPreflightCheck:
    return MatterLinkingPreflightCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )
