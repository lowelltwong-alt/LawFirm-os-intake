import pytest

from lawfirm_os_intake.deadline_guard import (
    build_deadline_docketing_guard_report,
    enforce_deadline_docketing_guard_report,
)
from lawfirm_os_intake.models import DeadlineDocketingGuardReport
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def _packet(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    return packet, run_dir


def test_preflight_writes_source_bound_deadline_docketing_guard(tmp_path, repo_root):
    packet, run_dir = _packet(tmp_path, repo_root)
    report = DeadlineDocketingGuardReport.model_validate(
        load_json(run_dir / "deadline_docketing_guard_report.json")
    )

    assert packet.deadline_docketing_guard_report_ref == str(
        run_dir / "deadline_docketing_guard_report.json"
    )
    assert report.status == "passed"
    assert report.candidate_count == len(packet.deadline_candidates)
    assert report.review_required_count == report.candidate_count
    assert report.docketing_action_performed is False
    assert report.docketing_action_allowed is False
    assert report.external_writes_performed is False
    assert report.proposed_next_gate == "human_deadline_review"
    assert {check.status for check in report.checks} == {"passed"}
    assert {
        "deadline_candidates_source_bound",
        "deadline_candidates_require_human_review",
        "deadline_docketing_forbidden_by_policy",
        "deadline_docketing_not_performed",
    } == {check.check_id for check in report.checks}
    assert report.candidate_items
    assert all(item.evidence_refs for item in report.candidate_items)
    assert all(item.requires_human_verification for item in report.candidate_items)

    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    for item in report.candidate_items:
        assert item.proposed_next_gate == "human_deadline_review"
        assert (
            "workflow/prohibited-transitions.yaml#deadline_gap_candidates_ready->deadline_docketed"
            in (item.structured_refs)
        )
        for ref in item.evidence_refs:
            segment = segments_by_id[ref.segment_id]
            assert ref.source_id == segment.source_id
            assert ref.start_offset == segment.start_offset
            assert ref.end_offset == segment.end_offset
            assert ref.sha256 == segment.sha256


def test_deadline_guard_fails_on_evidence_free_candidate(tmp_path, repo_root):
    packet, _ = _packet(tmp_path, repo_root)
    unsafe = packet.model_copy(deep=True)
    unsafe.deadline_candidates[0].evidence_refs = []

    report = build_deadline_docketing_guard_report(unsafe)

    assert report.status == "failed"
    assert any(
        check.check_id == "deadline_candidates_source_bound" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="deadline_candidates_source_bound"):
        enforce_deadline_docketing_guard_report(report)


def test_deadline_guard_fails_when_candidate_stops_requiring_human_review(tmp_path, repo_root):
    packet, _ = _packet(tmp_path, repo_root)
    unsafe = packet.model_copy(deep=True)
    unsafe.deadline_candidates[0].requires_human_verification = False

    report = build_deadline_docketing_guard_report(unsafe)

    assert report.status == "failed"
    assert any(
        check.check_id == "deadline_candidates_require_human_review" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="deadline_candidates_require_human_review"):
        enforce_deadline_docketing_guard_report(report)


def test_deadline_guard_enforcer_fails_on_runtime_docketing_drift(tmp_path, repo_root):
    packet, _ = _packet(tmp_path, repo_root)
    report = build_deadline_docketing_guard_report(packet)
    report.docketing_action_performed = True

    with pytest.raises(ValueError, match="docketing_action_performed"):
        enforce_deadline_docketing_guard_report(report)
