import pytest

from lawfirm_os_intake.ingestion import build_ingestion_result, validate_ingestion_result
from lawfirm_os_intake.models import IngestionResult, SourceBundle
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


def test_ingestion_result_validation_fails_on_reference_drift(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json")
    )
    result = build_ingestion_result(bundle)
    drifted = result.model_copy(deep=True)
    drifted.segment_evidence_refs[0].start_offset += 1

    with pytest.raises(ValueError, match="offset drift"):
        validate_ingestion_result(drifted)
