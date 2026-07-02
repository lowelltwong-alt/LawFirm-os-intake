import pytest

from lawfirm_os_intake.benchmarks import replay_budget_benchmark_refs, validate_benchmark_snapshot
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.coherence import check_budget_coherence, check_projection_coherence
from lawfirm_os_intake.models import BenchmarkSnapshotManifest, HumanConfirmation
from lawfirm_os_intake.provenance import PNum, assert_priced_sources
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    confirmation_path = tmp_path / "confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    proposal, _run_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return proposal


def test_budget_coherence_validator_accepts_current_budget(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)

    assert check_budget_coherence(budget.model_dump(mode="json")) == []


def test_budget_coherence_validator_catches_line_sum_mismatch(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root).model_dump(mode="json")
    budget["subtotal_fees"] = 1

    violations = check_budget_coherence(budget)

    assert any(violation["code"] == "line_sum_mismatch" for violation in violations)


def test_projection_coherence_validator_accepts_partitioned_projection(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    projection = budget.carrier_compliant_projection

    assert projection is not None
    assert check_projection_coherence(projection.model_dump(mode="json")) == []


def test_provenance_number_requires_non_invented_sources():
    total = PNum(100, frozenset({"template:one"})).add(PNum(50, frozenset({"rate:cell"})))

    assert total.value == 150
    assert total.sources == frozenset({"template:one", "rate:cell"})
    with pytest.raises(ValueError, match="non-invented"):
        assert_priced_sources([PNum(1, frozenset({"invented"}))])


def test_benchmark_snapshot_replay_reports_missing_budget_refs(tmp_path, repo_root):
    budget = _budget(tmp_path, repo_root)
    first = budget.lines[0].model_copy(
        update={
            "estimate_basis": "benchmark_cell",
            "estimate_basis_refs": ["cell:missing"],
        }
    )
    budget = budget.model_copy(update={"lines": [first, *budget.lines[1:]]})
    manifest = validate_benchmark_snapshot(
        {
            "benchmark_snapshot_id": "synthetic-benchmark-snapshot",
            "created_at": "2026-07-02T00:00:00Z",
            "source_owner": "local_candidate_fixture",
            "pinned_hash": "sha256:" + "1" * 64,
            "cells": [
                {
                    "benchmark_cell_id": "cell:present",
                    "jurisdiction": "synthetic",
                    "role": "associate",
                    "experience_band": "mid",
                    "year": 2026,
                    "percentile": "p50",
                    "value": 250,
                    "benchmark_type": "synthetic_candidate",
                    "source_url": "https://example.invalid/synthetic",
                    "retrieved_at": "2026-07-02T00:00:00Z",
                    "page_sha256": "sha256:" + "0" * 64,
                    "quote_span": "synthetic test span",
                    "license_note": "synthetic test",
                    "grade": "ungraded",
                    "human_grading_status": "pending",
                }
            ],
        }
    )

    assert isinstance(manifest, BenchmarkSnapshotManifest)
    assert replay_budget_benchmark_refs(budget, manifest) == ["cell:missing"]
