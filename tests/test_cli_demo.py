from lawfirm_os_intake.cli import main


def test_cli_demo_end_to_end(tmp_path, repo_root):
    code = main(
        [
            "demo",
            "--input",
            str(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json"),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense.yaml"),
            "--confirmation-template",
            str(
                repo_root
                / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
            ),
            "--out-dir",
            str(tmp_path / "demo"),
        ]
    )
    assert code == 0
    assert (tmp_path / "demo/budget/legal_budget_proposal.json").exists()
    assert (tmp_path / "demo/budget/conflict_search_seed_packet.json").exists()
    assert (tmp_path / "demo/budget/matter_opening_readiness.json").exists()
