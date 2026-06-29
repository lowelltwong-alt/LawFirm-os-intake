import yaml
import pytest

from lawfirm_os_intake.public_data import validate_public_data_boundary
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_preflight


def test_public_data_boundary_accepts_metadata_only_catalog(repo_root):
    ok, details = validate_public_data_boundary(repo_root)

    assert ok is True
    assert details["source_count"] >= 1
    assert details["direct_ingestion_source_ids"] == []
    assert details["unexpected_public_files"] == []


def test_public_data_boundary_rejects_catalog_direct_runtime_ingestion(tmp_path, repo_root):
    tmp_repo = tmp_path / "repo"
    (tmp_repo / "config").mkdir(parents=True)
    (tmp_repo / "examples/public").mkdir(parents=True)
    policy = yaml.safe_load((repo_root / "config/data_policy.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load(
        (repo_root / "examples/public/catalog.yaml").read_text(encoding="utf-8")
    )
    catalog["sources"][0]["direct_runtime_ingestion"] = True
    (tmp_repo / "config/data_policy.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_repo / "examples/public/catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_repo / "examples/public/README.md").write_text(
        "Planning-only public metadata catalog.\n",
        encoding="utf-8",
    )

    ok, details = validate_public_data_boundary(tmp_repo)

    assert ok is False
    assert "catalog_source_allows_direct_runtime_ingestion" in details["failures"]
    assert details["direct_ingestion_source_ids"] == ["courtlistener-recap"]


def test_public_reference_bundle_blocks_before_raw_storage(tmp_path, repo_root):
    data = load_json(repo_root / "examples/synthetic/inbound/help-email.json")
    data["data_origin"] = "public_reference"
    input_path = tmp_path / "public-reference-input.json"
    write_json(input_path, data)

    with pytest.raises(ValueError, match="data scope gate failed"):
        run_preflight(
            input_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "preflight",
        )

    run_dir = next((tmp_path / "preflight").iterdir())
    report = load_json(run_dir / "data_scope_gate_report.json")
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert report["status"] == "blocked"
    assert report["data_origin"] == "public_reference"
    assert "public_reference_not_runtime_ingested" in {
        check["check_id"] for check in report["checks"] if check["status"] == "failed"
    }
    assert not (run_dir / "raw_input.json").exists()
    assert any(
        event["step_name"] == "data_origin_gate" and event["status"] == "blocked"
        for event in ledger
    )
