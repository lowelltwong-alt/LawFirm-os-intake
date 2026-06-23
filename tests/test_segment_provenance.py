import pytest

from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.segmenter import segment_bundle
from lawfirm_os_intake.util import digest_text, load_json, load_jsonl
from lawfirm_os_intake.workflow import _validate_refs, run_preflight


def test_segments_preserve_offsets_and_hashes(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json")
    )
    segments = segment_bundle(bundle)
    assert segments
    for segment in segments:
        assert segment.end_offset >= segment.start_offset
        assert segment.sha256 == digest_text(segment.text)
        assert segment.source_id


def test_preflight_evidence_refs_preserve_segment_offsets_and_hashes(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    refs = []
    refs.extend(ref for party in packet.party_candidates for ref in party.evidence_refs)
    refs.extend(
        ref
        for candidate in (
            packet.inbound_event_candidates
            + packet.matter_family_candidates
            + packet.representation_posture_candidates
        )
        for ref in candidate.observed_evidence_refs
    )
    refs.extend(ref for deadline in packet.deadline_candidates for ref in deadline.evidence_refs)
    refs.extend(
        ref for missing in packet.missing_information_candidates for ref in missing.evidence_refs
    )
    refs.extend(ref for finding in packet.critic_findings for ref in finding.evidence_refs)

    for ref in refs:
        segment = segments_by_id[ref.segment_id]
        assert ref.source_id == segment.source_id
        assert ref.start_offset == segment.start_offset
        assert ref.end_offset == segment.end_offset
        assert ref.sha256 == segment.sha256

    exception_refs = [
        ref
        for candidate in load_jsonl(run_dir / "exception_lake_candidates.jsonl")
        for ref in candidate["evidence_refs"]
    ]
    for ref in exception_refs:
        segment = segments_by_id[ref["segment_id"]]
        assert ref["source_id"] == segment.source_id
        assert ref["start_offset"] == segment.start_offset
        assert ref["end_offset"] == segment.end_offset
        assert ref["sha256"] == segment.sha256


def test_strict_evidence_validation_fails_on_offset_drift(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    corrupted = packet.model_copy(deep=True)
    corrupted.party_candidates[0].evidence_refs[0].start_offset += 1

    with pytest.raises(ValueError, match="offsets do not match"):
        _validate_refs(corrupted)
