from lawfirm_os_intake.workflow import run_preflight


def test_carrier_is_not_automatically_represented_client(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    carrier = next(p for p in packet.party_candidates if p.name == "Harbor Point Insurance")
    roles = {r.role for r in carrier.role_candidates}
    assert "insurance_carrier" in roles
    assert "prospective_represented_client" not in roles
    assert all(role.evidence_refs for role in carrier.role_candidates)
    assert packet.human_confirmation_required
