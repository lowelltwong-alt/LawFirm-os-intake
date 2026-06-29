import pytest

from lawfirm_os_intake.contract_state import build_contract_state_report, enforce_contract_state
from lawfirm_os_intake.models import ContractStateReport
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_preflight


def test_contract_state_report_verifies_reviewed_seed_lock(repo_root):
    report = build_contract_state_report("run_contract_state_test", repo_root)

    assert report.status == "passed"
    assert report.lock_status == "reviewed_seed_lock"
    assert {dependency.repo for dependency in report.dependencies} == {
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
        "LawFirm-os-legal-knowledge-runtime",
        "LawFirm-os-skills-registry",
    }
    assert all(dependency.status == "verified" for dependency in report.dependencies)
    assert all(dependency.topology_matches_lock for dependency in report.dependencies)

    enforce_contract_state(report)


def test_preflight_writes_passing_contract_state_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    report = ContractStateReport.model_validate(load_json(run_dir / "contract_state_report.json"))
    ledger_events = load_jsonl(run_dir / "run_ledger.jsonl")

    assert packet.contract_state_report_ref == str(run_dir / "contract_state_report.json")
    assert report.status == "passed"
    assert any(
        event["step_name"] == "contract_state_gate" and event["status"] == "completed"
        for event in ledger_events
    )


def test_contract_state_gate_fails_closed_when_lock_files_are_missing(tmp_path):
    report = build_contract_state_report("run_missing_contract_state", tmp_path)

    assert report.status == "failed"
    assert {"contract_lockfile_present", "topology_lock_present"}.issubset(
        {check.check_id for check in report.checks if check.status == "failed"}
    )
    with pytest.raises(ValueError, match="contract state gate failed"):
        enforce_contract_state(report)
