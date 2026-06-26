import shutil

import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicSourceMethodologyReport
from lawfirm_os_intake.public_source_methodology import (
    run_public_source_methodology_audit,
)
from lawfirm_os_intake.util import load_json


def _copy_public_methodology_repo(tmp_path, repo_root):
    tmp_repo = tmp_path / "repo"
    (tmp_repo / "config").mkdir(parents=True)
    (tmp_repo / "examples").mkdir(parents=True)
    shutil.copytree(repo_root / "examples/public", tmp_repo / "examples/public")
    shutil.copy(repo_root / "config/data_policy.yaml", tmp_repo / "config/data_policy.yaml")
    return tmp_repo


def test_public_source_methodology_audit_ready_for_human_review(tmp_path, repo_root):
    report, run_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    persisted = PublicSourceMethodologyReport.model_validate(
        load_json(run_dir / "public_source_methodology_report.json")
    )

    assert persisted.public_source_methodology_report_id == (
        report.public_source_methodology_report_id
    )
    assert persisted.status == "ready_for_human_public_source_methodology_review"
    assert persisted.source_count >= 3
    assert persisted.missing_required_source_ids == []
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(
        source.status == "ready_for_human_methodology_review" for source in persisted.sources
    )
    assert persisted.direct_runtime_ingestion_allowed is False
    assert persisted.public_records_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.connector_implemented is False
    assert persisted.legal_knowledge_adapter_authorized is False
    assert persisted.external_writes_performed is False

    notes = (run_dir / "public_source_methodology_report.md").read_text(encoding="utf-8")
    assert "Public records ingested: False" in notes
    assert "owner_approval_before_adapter" in notes


def test_public_source_methodology_blocks_missing_required_source(tmp_path, repo_root):
    tmp_repo = _copy_public_methodology_repo(tmp_path, repo_root)
    catalog_path = tmp_repo / "examples/public/catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["sources"] = [
        source for source in catalog["sources"] if source["source_id"] != "fjc-idb"
    ]
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")

    report, _ = run_public_source_methodology_audit(
        repo_root=tmp_repo,
        out_dir=tmp_path / "public-source-methodology-missing",
    )

    assert report.status == "blocked_public_source_methodology"
    assert report.missing_required_source_ids == ["fjc-idb"]
    missing_check = next(
        check for check in report.checks if check.check_id == "phase_2_required_sources_present"
    )
    assert missing_check.status == "blocked"


def test_public_source_methodology_blocks_direct_ingestion_and_payload_fields(
    tmp_path,
    repo_root,
):
    tmp_repo = _copy_public_methodology_repo(tmp_path, repo_root)
    catalog_path = tmp_repo / "examples/public/catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["sources"][0]["direct_runtime_ingestion"] = True
    catalog["sources"][0]["raw_payload"] = "not allowed"
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")

    report, _ = run_public_source_methodology_audit(
        repo_root=tmp_repo,
        out_dir=tmp_path / "public-source-methodology-blocked",
    )

    assert report.status == "blocked_public_source_methodology"
    assert any(
        check.check_id == "public_data_boundary_passes" and check.status == "failed"
        for check in report.checks
    )
    source = next(source for source in report.sources if source.source_id == "courtlistener-recap")
    assert source.status == "blocked"
    assert "direct_runtime_ingestion_not_false" in source.blocking_reasons
    assert "source_contains_payload_field" in source.blocking_reasons


def test_public_source_methodology_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-public-source-methodology",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "public-source-methodology-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_public_source_methodology_review"' in captured.out
    assert '"direct_runtime_ingestion_allowed": false' in captured.out
    assert (
        tmp_path / "public-source-methodology-cli" / "public_source_methodology_report.json"
    ).is_file()
