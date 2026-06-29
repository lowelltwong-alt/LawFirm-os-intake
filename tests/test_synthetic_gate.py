import json
import pytest

from lawfirm_os_intake.data_scope import (
    build_data_scope_gate_report,
    enforce_data_scope_gate_report,
)
from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import _gate_bundle, run_preflight


def test_real_data_is_rejected(repo_root):
    data = json.loads((repo_root / "examples/synthetic/inbound/help-email.json").read_text())
    data["data_origin"] = "production"
    data["contains_real_client_data"] = True
    bundle = SourceBundle.model_validate(data)
    with pytest.raises(ValueError):
        _gate_bundle(bundle)


def test_data_scope_gate_report_passes_for_synthetic_bundle(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/help-email.json")
    )

    report = build_data_scope_gate_report("run_data_scope_test", bundle)

    assert report.status == "passed"
    assert report.data_origin == "synthetic"
    assert report.contains_real_client_data is False
    assert report.contains_real_matter_data is False
    assert report.contains_privileged_data is False
    assert report.raw_payload_written is False
    assert report.external_writes_performed is False
    assert {check.status for check in report.checks} == {"passed"}
    enforce_data_scope_gate_report(report)


def test_preflight_writes_data_scope_gate_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/help-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    report = load_json(run_dir / "data_scope_gate_report.json")
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert report["status"] == "passed"
    assert report["data_origin"] == "synthetic"
    assert packet.data_scope_gate_report_ref == str(run_dir / "data_scope_gate_report.json")
    assert any(
        event["step_name"] == "data_origin_gate"
        and event["status"] == "completed"
        and str(run_dir / "data_scope_gate_report.json") in event["output_refs"]
        for event in ledger
    )


def test_preflight_blocks_non_synthetic_scope_with_report(tmp_path, repo_root):
    data = load_json(repo_root / "examples/synthetic/inbound/help-email.json")
    data["data_origin"] = "production"
    data["contains_real_client_data"] = True
    input_path = tmp_path / "production-input.json"
    write_json(input_path, data)

    with pytest.raises(ValueError, match="data scope gate failed"):
        run_preflight(
            input_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "preflight",
        )

    run_dirs = list((tmp_path / "preflight").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    report = load_json(run_dir / "data_scope_gate_report.json")
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert report["status"] == "blocked"
    assert report["blocked_state"] == "data_scope_gate_failed"
    assert report["data_origin"] == "production"
    assert report["contains_real_client_data"] is True
    assert report["raw_payload_written"] is False
    assert not (run_dir / "raw_input.json").exists()
    assert not (run_dir / "intake_preflight_packet.json").exists()
    assert any(
        event["step_name"] == "data_origin_gate"
        and event["status"] == "blocked"
        and str(run_dir / "data_scope_gate_report.json") in event["output_refs"]
        for event in ledger
    )
