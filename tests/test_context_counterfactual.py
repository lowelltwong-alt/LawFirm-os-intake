import pytest

from lawfirm_os_intake.context_boundary import (
    build_context_boundary_report,
    enforce_context_boundary_report,
)
from lawfirm_os_intake.models import ContextBoundaryReport
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight


def test_same_evidence_different_practice_profile_changes_ranking_not_segments(tmp_path, repo_root):
    input_path = repo_root / "examples/synthetic/inbound/help-email.json"
    defense_packet, defense_run_dir = run_preflight(
        input_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "defense",
    )
    plaintiff_packet, _ = run_preflight(
        input_path,
        repo_root / "context/synthetic-profiles/plaintiff-personal-injury.yaml",
        tmp_path / "plaintiff",
    )
    assert [s.sha256 for s in defense_packet.segments] == [
        s.sha256 for s in plaintiff_packet.segments
    ]
    defense_scores = {c.label: c.confidence for c in defense_packet.matter_family_candidates}
    plaintiff_scores = {c.label: c.confidence for c in plaintiff_packet.matter_family_candidates}
    assert (
        plaintiff_scores["plaintiff_personal_injury"] > defense_scores["plaintiff_personal_injury"]
    )

    observed = next(
        c for c in defense_packet.matter_family_candidates if c.label == "plaintiff_personal_injury"
    )
    context_only = next(
        c
        for c in defense_packet.matter_family_candidates
        if c.label == "medical_malpractice_defense"
    )
    unknown = next(c for c in defense_packet.matter_family_candidates if c.label == "unknown")
    assert observed.source_evidence_status == "observed_support"
    assert context_only.calibration_label == "context_influenced"
    assert context_only.source_evidence_status == "source_anchor_only"
    assert context_only.observed_evidence_refs
    assert context_only.context_signal_refs
    assert unknown.source_evidence_status == "unknown_option"

    graph = load_json(defense_run_dir / "evidence_graph.json")
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    assert nodes[context_only.candidate_id]["attributes"]["source_evidence_status"] == (
        "source_anchor_only"
    )
    context_edges = [
        edge for edge in graph["edges"] if edge["target_node_id"] == context_only.candidate_id
    ]
    observed_edges = [
        edge for edge in graph["edges"] if edge["target_node_id"] == observed.candidate_id
    ]
    assert {edge["relationship"] for edge in context_edges} == {"anchors_matter_family_candidate"}
    assert {edge["relationship"] for edge in observed_edges} == {"supports_matter_candidate"}


def test_preflight_writes_context_boundary_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/help-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    report_path = run_dir / "context_boundary_report.json"
    report = ContextBoundaryReport.model_validate(load_json(report_path))

    assert packet.context_boundary_report_ref == str(report_path)
    assert report.status == "passed"
    assert report.observed_source_evidence_precedence is True
    assert report.practice_context_is_observed_evidence is False
    assert report.human_confirmation_required is True
    assert report.context_signal_candidate_count > 0
    assert report.context_only_candidate_count > 0
    assert report.external_writes_performed is False
    assert report.non_authoritative is True
    assert {
        "context_precedence_preserves_observed_evidence",
        "context_refs_are_structured_profile_refs",
        "context_influence_not_observed_fact",
        "context_candidates_remain_packet_anchored",
        "unknown_options_preserved_for_human_review",
        "human_confirmation_required_for_context_ranked_candidates",
    } == {check.check_id for check in report.checks}
    assert {check.status for check in report.checks} == {"passed"}


def test_context_boundary_report_fails_when_context_prior_becomes_observed_fact(
    tmp_path, repo_root
):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/help-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    corrupted = packet.model_copy(deep=True)
    context_only = next(
        candidate
        for candidate in corrupted.matter_family_candidates
        if candidate.calibration_label == "context_influenced"
    )
    context_only.source_evidence_status = "observed_support"

    report = build_context_boundary_report(corrupted)

    assert report.status == "failed"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "context_influence_not_observed_fact" in failed
    with pytest.raises(ValueError, match="context_influence_not_observed_fact"):
        enforce_context_boundary_report(report)
