from hashlib import sha256
import shutil

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicDataCacheAuditReport
from lawfirm_os_intake.public_data_cache import run_public_data_cache_audit
from lawfirm_os_intake.util import load_json, write_json


def _sample_cache_entry(cache_root, *, source_id="fjc-idb", content=None):
    sample = content or b'{"fields":["nature_of_suit","filing_date","disposition"]}\n'
    sample_path = cache_root / "fjc" / "sample-field-shape.json"
    sample_path.parent.mkdir(parents=True)
    sample_path.write_bytes(sample)
    return {
        "source_id": source_id,
        "source_url": "https://www.fjc.gov/research/idb",
        "source_type": "aggregate_case_metadata",
        "retrieved_at": "2026-07-01T00:00:00Z",
        "sha256": sha256(sample).hexdigest(),
        "byte_count": len(sample),
        "cache_ref": "fjc/sample-field-shape.json",
        "license_terms_note": "Public methodology reference; review terms before use.",
        "allowed_use": "Field-shape and aggregate distribution methodology review only.",
        "prohibited_use": "Runtime intake, identity reconstruction, legal or budget inference.",
        "retention_posture": "Ignored local cache; delete or regenerate after review.",
    }


def _write_manifest(cache_root, entries):
    return write_json(cache_root / "public_data_cache_manifest.json", {"sources": entries})


def _copy_public_data_repo(tmp_path, repo_root):
    tmp_repo = tmp_path / "repo"
    (tmp_repo / "config").mkdir(parents=True)
    (tmp_repo / "examples").mkdir(parents=True)
    shutil.copytree(repo_root / "examples/public", tmp_repo / "examples/public")
    shutil.copy(repo_root / "config/data_policy.yaml", tmp_repo / "config/data_policy.yaml")
    return tmp_repo


def test_public_data_cache_audit_ready_for_human_review(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_cache_entry(cache_root)
    _write_manifest(cache_root, [entry])

    report, run_dir = run_public_data_cache_audit(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "cache-audit",
    )
    persisted = PublicDataCacheAuditReport.model_validate(
        load_json(run_dir / "public_data_cache_audit_report.json")
    )

    assert persisted.public_data_cache_audit_report_id == report.public_data_cache_audit_report_id
    assert persisted.status == "ready_for_human_public_data_cache_review"
    assert persisted.manifest_entry_count == 1
    assert persisted.valid_manifest_entry_count == 1
    assert persisted.cache_sample_count == 1
    assert persisted.unknown_source_ids == []
    assert persisted.failed_hash_source_ids == []
    assert persisted.missing_cache_file_source_ids == []
    assert persisted.rust_custody_status == "passed"
    assert persisted.rust_custody_failure_count == 0
    assert persisted.rust_custody_checked_source_count == 1
    assert persisted.rust_custody_checked_sample_count == 1
    assert persisted.rust_custody_report_ref is not None
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.public_cache_samples_present is True
    assert persisted.direct_runtime_ingestion_allowed is False
    assert persisted.public_records_runtime_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.tracked_public_payload_committed is False
    assert persisted.connector_implemented is False
    assert persisted.synthetic_fixtures_created is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False

    notes = (run_dir / "public_data_cache_audit_report.md").read_text(encoding="utf-8")
    assert "Tracked public payload committed: False" in notes
    assert "**Rust custody status:** passed" in notes
    assert "human_public_data_cache_review" in notes


def test_public_data_cache_blocks_unknown_catalog_source(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_cache_entry(cache_root, source_id="uncataloged-public-source")
    _write_manifest(cache_root, [entry])

    report, _ = run_public_data_cache_audit(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "cache-audit-unknown",
    )

    assert report.status == "blocked_public_data_cache"
    assert report.unknown_source_ids == ["uncataloged-public-source"]
    assert any(
        check.check_id == "manifest_sources_are_cataloged" and check.status == "blocked"
        for check in report.checks
    )


def test_public_data_cache_blocks_hash_or_size_drift(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_cache_entry(cache_root)
    (cache_root / entry["cache_ref"]).write_text("changed after manifest\n", encoding="utf-8")
    _write_manifest(cache_root, [entry])

    report, _ = run_public_data_cache_audit(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "cache-audit-hash-drift",
    )

    assert report.status == "blocked_public_data_cache"
    assert report.failed_hash_source_ids == ["fjc-idb"]
    assert report.rust_custody_status == "failed"
    assert report.rust_custody_failure_count >= 1
    assert any(
        check.check_id == "cache_hashes_and_sizes_match" and check.status == "failed"
        for check in report.checks
    )
    assert any(
        check.check_id == "rust_public_data_cache_custody_passes" and check.status == "failed"
        for check in report.checks
    )


def test_public_data_cache_blocks_tracked_repo_payload_path(tmp_path, repo_root):
    tmp_repo = _copy_public_data_repo(tmp_path, repo_root)
    cache_root = tmp_repo / "examples/public"
    entry = _sample_cache_entry(cache_root)
    _write_manifest(cache_root, [entry])

    report, _ = run_public_data_cache_audit(
        repo_root=tmp_repo,
        cache_root=cache_root,
        out_dir=tmp_path / "cache-audit-tracked",
    )

    assert report.status == "blocked_public_data_cache"
    assert report.rust_custody_status == "failed"
    assert "examples/public/fjc/sample-field-shape.json" in report.blocked_path_refs
    assert any(
        check.check_id == "cache_root_is_ignored_or_external" and check.status == "blocked"
        for check in report.checks
    )
    assert any(
        check.check_id == "public_data_boundary_passes" and check.status == "failed"
        for check in report.checks
    )


def test_public_data_cache_cli_writes_report(tmp_path, repo_root, capsys):
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_cache_entry(cache_root)
    _write_manifest(cache_root, [entry])
    run_dir = tmp_path / "cache-audit-cli"

    exit_code = main(
        [
            "audit-public-data-cache",
            "--repo-root",
            str(repo_root),
            "--cache-root",
            str(cache_root),
            "--out-dir",
            str(run_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_public_data_cache_review"' in captured.out
    assert '"direct_runtime_ingestion_allowed": false' in captured.out
    assert '"rust_custody_status": "passed"' in captured.out
    assert (run_dir / "public_data_cache_audit_report.json").is_file()
