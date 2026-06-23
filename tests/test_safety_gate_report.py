import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    ConflictSeedPacket,
    BudgetPreconditionReport,
    HumanConfirmation,
    MatterOpeningReadiness,
    ReviewPackageManifest,
    SafetyGateReport,
)
from lawfirm_os_intake.safety import build_safety_gate_report, enforce_safety_gate
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def _budget_run(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return packet, confirmation, budget, budget_dir


def test_budget_run_writes_passing_safety_gate_report(tmp_path, repo_root):
    _, _, _, budget_dir = _budget_run(tmp_path, repo_root)

    report = SafetyGateReport.model_validate(load_json(budget_dir / "safety_gate_report.json"))
    precondition_report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    manifest = ReviewPackageManifest.model_validate(
        load_json(budget_dir / "review_package_manifest.json")
    )
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert report.status == "passed"
    assert all(check.status == "passed" for check in report.checks)
    assert report.external_writes_performed is False
    assert report.final_boundary == "blocked_pending_conflicts_and_engagement"
    assert precondition_report.status == "passed"
    assert all(check.status == "passed" for check in precondition_report.checks)
    assert "contract_state_report_carried_forward" in {check.check_id for check in report.checks}
    assert manifest.safety_gate_report_ref == str(budget_dir / "safety_gate_report.json")
    assert manifest.artifact_refs["safety_gate_report"] == str(
        budget_dir / "safety_gate_report.json"
    )
    assert "## Safety Gate" in review_text
    assert "Status: passed" in review_text
    assert "no_conflict_conclusion" in {check.check_id for check in report.checks}


def test_safety_gate_fails_closed_on_forbidden_conflict_conclusion(tmp_path, repo_root):
    packet, confirmation, budget, budget_dir = _budget_run(tmp_path, repo_root)
    conflict_seed = ConflictSeedPacket.model_validate(
        load_json(budget_dir / "conflict_search_seed_packet.json")
    )
    readiness = MatterOpeningReadiness.model_validate(
        load_json(budget_dir / "matter_opening_readiness.json")
    )
    manifest = ReviewPackageManifest.model_validate(
        load_json(budget_dir / "review_package_manifest.json")
    )
    unsafe_seed = conflict_seed.model_copy(update={"conclusion": "conflicts_cleared"})

    report = build_safety_gate_report(
        packet,
        confirmation,
        unsafe_seed,
        budget,
        readiness,
        manifest.artifact_refs,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "no_conflict_conclusion" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="safety gate failed"):
        enforce_safety_gate(report)
