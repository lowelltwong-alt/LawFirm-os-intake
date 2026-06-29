import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation, RunEvent
from lawfirm_os_intake.run_ledger import (
    build_run_ledger_integrity_report,
    enforce_run_ledger_integrity,
)
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import (
    PREFLIGHT_REQUIRED_LEDGER_STEPS,
    run_budget,
    run_preflight,
)


def _confirmation(packet, repo_root, *, status: str = "confirmed") -> HumanConfirmation:
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    raw["status"] = status
    confirmation = HumanConfirmation.model_validate(raw)
    return bind_confirmation_to_packet_evidence(packet, confirmation)


def _ledger_events(path) -> list[RunEvent]:
    return [RunEvent.model_validate(event) for event in load_jsonl(path)]


def test_preflight_writes_passing_run_ledger_integrity_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    report = load_json(run_dir / "run_ledger_integrity_report.json")

    assert packet.run_ledger_integrity_report_ref == str(
        run_dir / "run_ledger_integrity_report.json"
    )
    assert report["status"] == "passed"
    assert report["stage"] == "preflight"
    assert report["terminal_step_name"] == "preflight_packet_built"
    assert report["terminal_status"] == "completed"
    assert report["local_artifact_refs_only"] is True
    assert report["external_writes_performed"] is False
    assert "contract_state_gate" in report["required_steps"]
    assert "preflight_packet_built" in report["observed_steps"]
    assert {check["status"] for check in report["checks"]} == {"passed"}


def test_budget_package_carries_run_ledger_integrity_reports(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    _, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )

    report = load_json(budget_dir / "run_ledger_integrity_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    completeness = load_json(budget_dir / "review_package_completeness_report.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert report["status"] == "passed"
    assert report["stage"] == "budget_success"
    assert report["terminal_step_name"] == "conflict_seed_and_budget_proposal_built"
    assert report["terminal_status"] == "completed"
    assert manifest["artifact_refs"]["preflight_run_ledger_integrity_report"] == str(
        preflight_dir / "run_ledger_integrity_report.json"
    )
    assert manifest["artifact_refs"]["budget_run_ledger_integrity_report"] == str(
        budget_dir / "run_ledger_integrity_report.json"
    )
    assert set(manifest["run_ledger_integrity_report_refs"]) == {
        str(preflight_dir / "run_ledger_integrity_report.json"),
        str(budget_dir / "run_ledger_integrity_report.json"),
    }
    assert any(
        check["check_id"] == "run_ledger_integrity_reports_passed" and check["status"] == "passed"
        for check in completeness["checks"]
    )
    assert "### Run Ledger Integrity" in review_text
    assert "budget_success: status=passed" in review_text


def test_blocked_budget_writes_blocked_run_ledger_integrity_report(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root, status="needs_more_information")
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            preflight_dir / "intake_preflight_packet.json",
            confirmation_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "budget",
        )

    report = load_json(tmp_path / "budget/run_ledger_integrity_report.json")

    assert report["status"] == "passed"
    assert report["stage"] == "budget_precondition_blocked"
    assert report["terminal_step_name"] == "budget_generation_blocked"
    assert report["terminal_status"] == "blocked"
    assert report["external_writes_performed"] is False
    assert not (tmp_path / "budget/legal_budget_proposal.json").exists()


def test_run_ledger_integrity_fails_when_required_gate_is_missing(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    events = [
        event
        for event in _ledger_events(run_dir / "run_ledger.jsonl")
        if event.step_name != "data_origin_gate"
    ]

    report = build_run_ledger_integrity_report(
        run_id=packet.run_id,
        stage="preflight",
        run_ledger_ref=str(run_dir / "run_ledger.jsonl"),
        events=events,
        required_steps=PREFLIGHT_REQUIRED_LEDGER_STEPS,
        terminal_step_name="preflight_packet_built",
        terminal_status="completed",
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "required_steps_present_in_order" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="run ledger integrity failed"):
        enforce_run_ledger_integrity(report)
