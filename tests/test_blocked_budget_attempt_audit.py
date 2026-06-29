import pytest

from lawfirm_os_intake.blocked_budget_audit import (
    build_blocked_budget_attempt_audit_report,
    enforce_blocked_budget_attempt_audit,
    run_blocked_budget_attempt_audit,
)
from lawfirm_os_intake.util import write_json
from lawfirm_os_intake.workflow import run_preflight


def _preflight(tmp_path, repo_root):
    return run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )


def test_blocked_budget_attempt_audit_proves_no_budget_outputs(tmp_path, repo_root):
    _, run_dir = _preflight(tmp_path, repo_root)

    report, audit_dir = run_blocked_budget_attempt_audit(
        preflight_packet_path=run_dir / "intake_preflight_packet.json",
        confirmation_template_path=(
            repo_root
            / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
        ),
        practice_profile_path=repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        out_dir=tmp_path / "blocked-budget",
    )

    assert report.status == "passed"
    assert report.exception_raised is True
    assert report.expected_blocked_state == "budget_blocked_before_human_confirmation"
    assert {check.status for check in report.checks} == {"passed"}
    assert (audit_dir / "blocked_budget_attempt_audit_report.json").exists()
    assert not (audit_dir / "budget/legal_budget_proposal.json").exists()
    assert not (audit_dir / "budget/conflict_search_seed_packet.json").exists()
    assert not (audit_dir / "budget/matter_opening_review_package.md").exists()


def test_blocked_budget_attempt_audit_fails_if_prohibited_artifact_appears(tmp_path, repo_root):
    _, run_dir = _preflight(tmp_path, repo_root)
    report, audit_dir = run_blocked_budget_attempt_audit(
        preflight_packet_path=run_dir / "intake_preflight_packet.json",
        confirmation_template_path=(
            repo_root
            / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
        ),
        practice_profile_path=repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        out_dir=tmp_path / "blocked-budget",
    )
    write_json(audit_dir / "budget/legal_budget_proposal.json", {"forbidden": True})

    drifted = build_blocked_budget_attempt_audit_report(
        preflight_packet_path=run_dir / "intake_preflight_packet.json",
        confirmation_path=audit_dir / "blocked_confirmation.json",
        budget_dir=audit_dir / "budget",
        exception_raised=report.exception_raised,
        blocked_error=report.blocked_error,
    )

    assert drifted.status == "failed"
    failed = {check.check_id for check in drifted.checks if check.status == "failed"}
    assert "no_prohibited_budget_outputs_emitted" in failed
    with pytest.raises(ValueError, match="no_prohibited_budget_outputs_emitted"):
        enforce_blocked_budget_attempt_audit(drifted)
