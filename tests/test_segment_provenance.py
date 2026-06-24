import pytest

from lawfirm_os_intake.evidence_completeness import (
    build_evidence_completeness_report,
    enforce_evidence_completeness_report,
)
from lawfirm_os_intake.models import EvidenceCompletenessReport
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
        for party in packet.party_candidates
        for role in party.role_candidates
        for ref in role.evidence_refs
    )
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


def test_preflight_writes_evidence_completeness_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    report_path = run_dir / "evidence_completeness_report.json"
    report = EvidenceCompletenessReport.model_validate(load_json(report_path))

    assert packet.evidence_completeness_report_ref == str(report_path)
    assert report.status == "passed"
    assert report.strict_evidence_required is True
    assert report.human_confirmation_required is True
    assert report.evidence_ref_count > 0
    assert report.external_writes_performed is False
    assert report.non_authoritative is True
    assert {
        "party_candidates_source_bound",
        "party_role_candidates_source_bound",
        "classification_candidates_source_bound",
        "unknown_options_preserved",
        "deadline_candidates_source_bound_and_review_only",
        "missing_information_candidates_source_bound",
        "critic_findings_source_bound",
        "evidence_refs_match_segments",
        "human_review_boundary_present",
    } == {check.check_id for check in report.checks}
    assert {check.status for check in report.checks} == {"passed"}


def test_evidence_completeness_report_fails_on_role_ref_drift(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    corrupted = packet.model_copy(deep=True)
    corrupted.party_candidates[0].role_candidates[0].evidence_refs = []

    report = build_evidence_completeness_report(corrupted)

    assert report.status == "failed"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "party_role_candidates_source_bound" in failed
    with pytest.raises(ValueError, match="party_role_candidates_source_bound"):
        enforce_evidence_completeness_report(report)


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


def test_strict_evidence_validation_fails_on_role_candidate_offset_drift(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    corrupted = packet.model_copy(deep=True)
    corrupted.party_candidates[0].role_candidates[0].evidence_refs[0].start_offset += 1

    with pytest.raises(ValueError, match="offsets do not match"):
        _validate_refs(corrupted)
