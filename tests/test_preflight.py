from lawfirm_os_intake.workflow import run_preflight


def test_preflight_produces_evidence_bound_candidates(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    assert packet.status == "human_intake_review_required"
    assert packet.human_confirmation_required is True
    assert packet.matter_family_candidates[0].label == "medical_malpractice_defense"
    assert packet.party_candidates
    assert all(p.evidence_refs for p in packet.party_candidates)
    assert packet.contract_state_report_ref == str(run_dir / "contract_state_report.json")
    assert (run_dir / "contract_state_report.json").exists()
    assert (run_dir / "evidence_graph.json").exists()
    assert (run_dir / "run_ledger.jsonl").exists()
