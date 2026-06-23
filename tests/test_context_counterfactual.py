from lawfirm_os_intake.workflow import run_preflight


def test_same_evidence_different_practice_profile_changes_ranking_not_segments(tmp_path, repo_root):
    input_path = repo_root / "examples/synthetic/inbound/help-email.json"
    defense_packet, _ = run_preflight(
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
