from __future__ import annotations

from collections import Counter

from .models import IngestionResult, IngestionVolumeProfile
from .util import new_id, now_iso


PROFILE_THRESHOLDS = {
    "source_count": 10,
    "total_source_characters": 5000,
    "max_source_characters": 3000,
    "segment_count": 60,
    "max_segment_characters": 2500,
}

REQUIRED_RUST_TRANSITION_GATES = [
    "hot_path_performance_profile",
    "python_reference_golden_parity",
    "synthetic_fixture_and_holdout_parity",
    "schema_compatibility_export",
    "orchestrator_adapter_review",
    "semantic_substrate_contract_review_if_promoted",
]

CANDIDATE_RUST_HOT_PATH_SCOPE = [
    "source_inventory",
    "source_coverage_summary",
    "structural_segmentation",
    "sha256_hashing",
    "segment_evidence_ref_emission",
    "schema_compatible_ingestion_result_serialization",
]

REQUIRED_PERFORMANCE_PROFILE_DIMENSIONS = [
    "wall_clock_ms_by_ingestion_stage",
    "peak_memory_mb",
    "characters_per_second",
    "sources_per_second",
    "segment_count_and_segment_size_distribution",
    "hashing_and_segmentation_cpu_time",
    "serialized_ingestion_result_bytes",
    "bounded_concurrency_plan",
    "python_to_rust_parity_diff_count",
]


def _counts(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _state_counts(result: IngestionResult) -> dict[str, int]:
    states = [f"{item.read_state}/{item.availability_state}" for item in result.source_inventory]
    return _counts(states)


def build_ingestion_volume_profile(
    *, run_id: str, ingestion_result: IngestionResult
) -> IngestionVolumeProfile:
    source_lengths = [item.character_count for item in ingestion_result.source_inventory]
    segment_lengths = [
        segment.end_offset - segment.start_offset for segment in ingestion_result.segments
    ]
    source_count = len(ingestion_result.source_inventory)
    segment_count = len(ingestion_result.segments)
    total_source_characters = sum(source_lengths)
    total_segment_characters = sum(segment_lengths)
    max_source_characters = max(source_lengths, default=0)
    max_segment_characters = max(segment_lengths, default=0)

    scale_signals = []
    observed_values = {
        "source_count": source_count,
        "total_source_characters": total_source_characters,
        "max_source_characters": max_source_characters,
        "segment_count": segment_count,
        "max_segment_characters": max_segment_characters,
    }
    for key, threshold in PROFILE_THRESHOLDS.items():
        if observed_values[key] >= threshold:
            scale_signals.append(f"{key}_at_or_above_profile_threshold")

    requires_profile = bool(scale_signals)
    compute_pressure_signals = []
    if requires_profile:
        compute_pressure_signals.extend(
            [
                "local_ingestion_scale_threshold_crossed",
                "measure_before_rust_adapter_proposal",
            ]
        )
    rationale = [
        "Python remains the reference ingestion oracle.",
        "Rust replacement requires profiling plus golden parity before any adapter work.",
    ]
    if requires_profile:
        rationale.append(
            "Observed synthetic volume crosses a local profiling threshold; benchmark before proposing Rust."
        )
    else:
        rationale.append(
            "Observed synthetic volume stays below local profiling thresholds; keep Python reference."
        )

    return IngestionVolumeProfile(
        ingestion_volume_profile_id=new_id("ingestion_volume"),
        run_id=run_id,
        ingestion_result_id=ingestion_result.ingestion_result_id,
        bundle_id=ingestion_result.bundle_id,
        source_count=source_count,
        total_source_characters=total_source_characters,
        max_source_characters=max_source_characters,
        segment_count=segment_count,
        total_segment_characters=total_segment_characters,
        max_segment_characters=max_segment_characters,
        source_type_counts=_counts(
            [item.source_type for item in ingestion_result.source_inventory]
        ),
        source_state_counts=_state_counts(ingestion_result),
        segment_type_counts=_counts(
            [segment.segment_type for segment in ingestion_result.segments]
        ),
        profile_thresholds=PROFILE_THRESHOLDS,
        scale_signals=scale_signals,
        compute_pressure_signals=compute_pressure_signals,
        required_performance_profile_dimensions=REQUIRED_PERFORMANCE_PROFILE_DIMENSIONS,
        candidate_rust_hot_path_scope=CANDIDATE_RUST_HOT_PATH_SCOPE,
        observed_scale_band="profile_candidate" if requires_profile else "starter_fixture",
        performance_profile_required_before_rust=requires_profile,
        rust_replacement_allowed=False,
        rust_adapter_proposal_state=(
            "profiling_required_before_adapter_proposal" if requires_profile else "not_warranted"
        ),
        required_rust_transition_gates=REQUIRED_RUST_TRANSITION_GATES,
        decision="profile_before_rust_adapter" if requires_profile else "keep_python_reference",
        rationale=rationale,
        generated_at=now_iso(),
    )
