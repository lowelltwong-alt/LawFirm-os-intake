from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_preflight


def test_structured_model_adapter_writes_dry_run_guard_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
        adapter="structured-model",
    )

    report = load_json(run_dir / "model_adapter_report.json")
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")
    adapter_event = next(event for event in ledger if event["step_name"] == "adapter_selected")

    assert packet.model_adapter_report_ref == str(run_dir / "model_adapter_report.json")
    assert report["status"] == "passed"
    assert report["adapter_name"] == "structured-model"
    assert report["adapter_mode"] == "dry_run"
    assert report["provider_call_performed"] is False
    assert report["model_calls_allowed"] is False
    assert report["external_tools_allowed"] is False
    assert report["network_access_allowed"] is False
    assert report["external_writes_allowed"] is False
    assert report["raw_payload_externalized"] is False
    assert report["approved_for_real_data"] is False
    assert report["typed_json_only"] is True
    assert report["model_budget"]["max_model_calls"] == 0
    assert report["baseline_comparison_state"] == "dry_run_no_provider_output"
    assert "matter-router" in report["prompt_hashes"]
    assert report["prompt_hashes"]["matter-router"].startswith("sha256:")
    assert "network" in report["tool_denylist"]
    assert "matter_family_confirmation" in report["required_human_gates"]
    assert {check["status"] for check in report["checks"]} == {"passed"}
    assert str(run_dir / "model_adapter_report.json") in adapter_event["output_refs"]
