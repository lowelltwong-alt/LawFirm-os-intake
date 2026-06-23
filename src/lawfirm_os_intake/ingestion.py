from __future__ import annotations

from .models import EvidenceRef, IngestionResult, Segment, SourceBundle
from .segmenter import segment_bundle
from .util import new_id, now_iso
from .workers import source_coverage_summary, source_inventory


def _segment_evidence_ref(segment: Segment) -> EvidenceRef:
    return EvidenceRef(
        source_id=segment.source_id,
        segment_id=segment.segment_id,
        start_offset=segment.start_offset,
        end_offset=segment.end_offset,
        sha256=segment.sha256,
    )


def segment_evidence_refs(segments: list[Segment]) -> list[EvidenceRef]:
    return [_segment_evidence_ref(segment) for segment in segments]


def validate_ingestion_result(result: IngestionResult) -> None:
    segments_by_id = {segment.segment_id: segment for segment in result.segments}
    source_ids = {item.source_id for item in result.source_inventory}

    if len(result.segment_evidence_refs) != len(result.segments):
        raise ValueError("ingestion result must include one evidence ref per segment")

    seen_segment_refs: set[str] = set()
    for ref in result.segment_evidence_refs:
        segment = segments_by_id.get(ref.segment_id)
        if segment is None:
            raise ValueError(f"ingestion evidence ref references unknown segment {ref.segment_id}")
        if ref.segment_id in seen_segment_refs:
            raise ValueError(f"duplicate ingestion evidence ref for segment {ref.segment_id}")
        seen_segment_refs.add(ref.segment_id)
        if ref.source_id != segment.source_id:
            raise ValueError(f"ingestion evidence ref source drift for segment {ref.segment_id}")
        if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
            raise ValueError(f"ingestion evidence ref offset drift for segment {ref.segment_id}")
        if ref.sha256 != segment.sha256:
            raise ValueError(f"ingestion evidence ref hash drift for segment {ref.segment_id}")

    for segment in result.segments:
        if segment.source_id not in source_ids:
            raise ValueError(f"segment {segment.segment_id} has no source inventory row")

    expected_summary = source_coverage_summary(result.source_inventory)
    if result.source_coverage_summary != expected_summary:
        raise ValueError("ingestion source coverage summary does not match inventory")


def build_ingestion_result(bundle: SourceBundle) -> IngestionResult:
    segments = segment_bundle(bundle)
    inventory = source_inventory(bundle, segments)
    result = IngestionResult(
        ingestion_result_id=new_id("ingestion"),
        bundle_id=bundle.bundle_id,
        source_inventory=inventory,
        source_coverage_summary=source_coverage_summary(inventory),
        segments=segments,
        segment_evidence_refs=segment_evidence_refs(segments),
        generated_at=now_iso(),
    )
    validate_ingestion_result(result)
    return result
