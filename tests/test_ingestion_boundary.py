import pytest

from lawfirm_os_intake.ingestion import build_ingestion_result, validate_ingestion_result
from lawfirm_os_intake.ingestion_volume import build_ingestion_volume_profile
from lawfirm_os_intake.models import (
    IngestionResult,
    IngestionVolumeProfile,
    RustIngestionReadinessReport,
    SourceBundle,
)
from lawfirm_os_intake.rust_readiness import (
    build_rust_ingestion_readiness_report,
    enforce_rust_ingestion_readiness,
)
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_preflight


def test_python_reference_ingestion_result_is_rust_parity_oracle(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(
            repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json"
        )
    )
    result = build_ingestion_result(bundle)
    segments_by_id = {segment.segment_id: segment for segment in result.segments}
    inventory = {item.source_id: item for item in result.source_inventory}

    assert result.adapter_kind == "python_reference_ingestion_adapter"
    assert result.parity_contract == "rust_ready_ingestion_v0_1"
    assert result.rust_replacement_allowed is False
    assert len(result.segment_evidence_refs) == len(result.segments)
    assert {ref.segment_id for ref in result.segment_evidence_refs} == set(segments_by_id)
    assert inventory["syn-email-dup-002"].availability_state == "duplicate"
    assert inventory["syn-attachment-missing-001"].read_state == "missing"
    assert result.source_coverage_summary["coverage_complete"] is False

    for ref in result.segment_evidence_refs:
        segment = segments_by_id[ref.segment_id]
        assert ref.source_id == segment.source_id
        assert ref.start_offset == segment.start_offset
        assert ref.end_offset == segment.end_offset
        assert ref.sha256 == segment.sha256


def test_preflight_writes_ingestion_result_matching_legacy_outputs(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    result = IngestionResult.model_validate(load_json(run_dir / "ingestion_result.json"))
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert packet.ingestion_result_ref == str(run_dir / "ingestion_result.json")
    assert packet.source_coverage_summary == result.source_coverage_summary
    assert [item.model_dump(mode="json") for item in packet.source_inventory] == [
        item.model_dump(mode="json") for item in result.source_inventory
    ]
    assert [segment.model_dump(mode="json") for segment in packet.segments] == [
        segment.model_dump(mode="json") for segment in result.segments
    ]
    assert load_json(run_dir / "segments.json") == [
        segment.model_dump(mode="json") for segment in result.segments
    ]
    assert load_json(run_dir / "source_inventory.json") == [
        item.model_dump(mode="json") for item in result.source_inventory
    ]
    assert any(event["step_name"] == "python_reference_ingestion" for event in ledger)


def test_preflight_writes_passing_rust_ingestion_readiness_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    report_path = run_dir / "rust_ingestion_readiness_report.json"
    report = RustIngestionReadinessReport.model_validate(load_json(report_path))
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert packet.rust_ingestion_readiness_report_ref == str(report_path)
    assert report.status == "passed"
    assert report.current_adapter_kind == "python_reference_ingestion_adapter"
    assert report.parity_contract == "rust_ready_ingestion_v0_1"
    assert report.rust_replacement_allowed is False
    assert "source_inventory" in report.eligible_hot_path_scope
    assert "legal_classification" in report.forbidden_rust_scope
    assert "source_hashes" in report.required_parity_dimensions
    assert {check.status for check in report.checks} == {"passed"}
    assert any(str(report_path) in event.get("output_refs", []) for event in ledger)


def test_preflight_writes_ingestion_volume_profile(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    profile_path = run_dir / "ingestion_volume_profile.json"
    profile = IngestionVolumeProfile.model_validate(load_json(profile_path))
    result = IngestionResult.model_validate(load_json(run_dir / "ingestion_result.json"))
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert packet.ingestion_volume_profile_ref == str(profile_path)
    assert profile.ingestion_result_id == result.ingestion_result_id
    assert profile.bundle_id == result.bundle_id
    assert profile.source_count == len(result.source_inventory)
    assert profile.segment_count == len(result.segments)
    assert profile.rust_replacement_allowed is False
    assert profile.performance_profile_required_before_rust is False
    assert profile.observed_scale_band == "starter_fixture"
    assert profile.decision == "keep_python_reference"
    assert any(str(profile_path) in event.get("output_refs", []) for event in ledger)


def test_ingestion_volume_profile_requires_profiling_for_high_volume_proxy(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/high-volume-ingestion-proxy.json")
    )
    result = build_ingestion_result(bundle)
    profile = build_ingestion_volume_profile(run_id="run_volume_proxy", ingestion_result=result)

    assert profile.source_count == 10
    assert profile.rust_replacement_allowed is False
    assert profile.performance_profile_required_before_rust is True
    assert profile.observed_scale_band == "profile_candidate"
    assert profile.decision == "profile_before_rust_adapter"
    assert "source_count_at_or_above_profile_threshold" in profile.scale_signals
    assert "legal_classification" not in profile.model_dump(mode="json")


def test_rust_ingestion_readiness_fails_on_source_hash_drift(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json")
    )
    result = build_ingestion_result(bundle)
    drifted = result.model_copy(deep=True)
    drifted.source_inventory[0].source_sha256 = "sha256:" + ("0" * 64)

    report = build_rust_ingestion_readiness_report(
        run_id="run_test",
        bundle=bundle,
        ingestion_result=drifted,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "source_inventory_hashes_recomputed" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="source_inventory_hashes_recomputed"):
        enforce_rust_ingestion_readiness(report)


def test_ingestion_result_validation_fails_on_reference_drift(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json")
    )
    result = build_ingestion_result(bundle)
    drifted = result.model_copy(deep=True)
    drifted.segment_evidence_refs[0].start_offset += 1

    with pytest.raises(ValueError, match="offset drift"):
        validate_ingestion_result(drifted)
