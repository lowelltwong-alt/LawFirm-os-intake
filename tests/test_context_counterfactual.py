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
