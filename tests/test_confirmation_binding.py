import pytest
from lawfirm_os_intake.util import load_json, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def test_confirmation_must_bind_to_packet(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = "wrong-packet"
    confirmation = write_json(tmp_path / "confirmation.json", raw)
    with pytest.raises(ValueError):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "budget",
        )
