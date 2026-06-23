from lawfirm_os_intake.workflow import run_preflight


def test_prompt_injection_remains_data_and_cannot_expand_authority(tmp_path, repo_root):
    packet, _ = run_preflight(
        repo_root / "examples/synthetic/inbound/prompt-injection-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    assert any("Ignore all previous instructions" in s.text for s in packet.segments)
    assert "do_not_open_matter_or_imanage_workspace" in packet.prohibited_next_steps
    assert "do_not_clear_conflicts" in packet.prohibited_next_steps
    assert packet.human_confirmation_required is True
