import pytest

from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_preflight


def test_structured_model_adapter_writes_dry_run_guard_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
        adapter="structured-model",
        fixture_gold=repo_root
        / "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json",
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
    assert report["baseline_comparison_state"] == "compared_to_deterministic_baseline"
    assert report["comparison_status"] == "passed"
    assert report["synthetic_gold_required"] is True
    assert report["synthetic_gold_compared"] is True
    assert report["fixture_gold_status"] == "passed"
    assert report["typed_json_validation_status"] == "passed"
    assert report["deterministic_baseline_hash"].startswith("sha256:")
    assert report["structured_candidate_hash"] == report["deterministic_baseline_hash"]
    assert "reviewed_synthetic_gold_gate" in report["comparison_basis"]
    assert report["independent_critic_finding_codes"] == sorted(
        finding.code for finding in packet.critic_findings
    )
    assert report["independent_critic_evidence_ref_count"] == sum(
        len(finding.evidence_refs) for finding in packet.critic_findings
    )
    assert any(
        check["check_id"] == "independent_critic_output_preserved" and check["status"] == "passed"
        for check in report["checks"]
    )
    assert "matter-router" in report["prompt_hashes"]
    assert report["prompt_hashes"]["matter-router"].startswith("sha256:")
    assert "network" in report["tool_denylist"]
    assert "matter_family_confirmation" in report["required_human_gates"]
    assert {check["status"] for check in report["checks"]} == {"passed"}
    assert str(run_dir / "model_adapter_report.json") in adapter_event["output_refs"]


def test_structured_model_adapter_requires_reviewed_synthetic_gold(tmp_path, repo_root):
    with pytest.raises(ValueError, match="reviewed_synthetic_gold_compared"):
        run_preflight(
            repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path,
            adapter="structured-model",
        )

    run_dirs = list(tmp_path.iterdir())
    assert len(run_dirs) == 1
    report = load_json(run_dirs[0] / "model_adapter_report.json")
    assert report["status"] == "failed"
    assert report["baseline_comparison_state"] == "failed_missing_synthetic_gold"
    assert report["synthetic_gold_required"] is True
    assert report["synthetic_gold_compared"] is False
    assert report["fixture_gold_status"] == "not_requested"
