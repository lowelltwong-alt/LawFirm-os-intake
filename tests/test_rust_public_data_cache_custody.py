from hashlib import sha256

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import RustPublicDataCacheCustodyReport
from lawfirm_os_intake.rust_public_data_cache_custody import (
    run_rust_public_data_cache_custody_check,
)
from lawfirm_os_intake.util import load_json, write_json


def _write_manifest(cache_root, entries):
    return write_json(cache_root / "public_data_cache_manifest.json", {"sources": entries})


def _sample_entry(cache_root, *, source_id="fjc-idb", content=b"public structure sample\n"):
    sample_path = cache_root / "fjc" / f"{source_id}.json"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_bytes(content)
    return {
        "source_id": source_id,
        "cache_ref": f"fjc/{source_id}.json",
        "sha256": sha256(content).hexdigest(),
        "byte_count": len(content),
    }


def test_rust_public_data_cache_custody_passes_external_cache(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_entry(cache_root)
    _write_manifest(cache_root, [entry])

    report, report_path = run_rust_public_data_cache_custody_check(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "rust-custody",
    )
    persisted = RustPublicDataCacheCustodyReport.model_validate(load_json(report_path))

    assert persisted.status == report.status == "passed"
    assert persisted.manifest_entry_count == 1
    assert persisted.checked_source_count == 1
    assert persisted.checked_sample_count == 1
    assert persisted.total_checked_sample_bytes == entry["byte_count"]
    assert persisted.failure_count == 0
    assert persisted.samples[0].status == "passed"
    assert persisted.direct_runtime_ingestion_allowed is False
    assert persisted.public_records_runtime_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.tracked_public_payload_committed is False
    assert persisted.external_writes_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False


def test_rust_public_data_cache_custody_cli_writes_report(tmp_path, repo_root, capsys):
    cache_root = tmp_path / "public-data-cache"
    _write_manifest(cache_root, [_sample_entry(cache_root)])
    run_dir = tmp_path / "rust-custody-cli"

    exit_code = main(
        [
            "build-rust-public-data-cache-custody-report",
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
    assert '"status": "passed"' in captured.out
    assert '"direct_runtime_ingestion_allowed": false' in captured.out
    assert (run_dir / "rust_public_data_cache_custody_report.json").is_file()


def test_rust_public_data_cache_custody_blocks_path_refs(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    cache_root.mkdir()
    digest = sha256(b"irrelevant").hexdigest()
    _write_manifest(
        cache_root,
        [
            {
                "source_id": "parent-traversal",
                "cache_ref": "../outside.json",
                "sha256": digest,
                "byte_count": 10,
            },
            {
                "source_id": "posix-absolute",
                "cache_ref": "/tmp/public.json",
                "sha256": digest,
                "byte_count": 10,
            },
            {
                "source_id": "drive-like",
                "cache_ref": "C:/public.json",
                "sha256": digest,
                "byte_count": 10,
            },
            {
                "source_id": "backslash",
                "cache_ref": "..\\outside.json",
                "sha256": digest,
                "byte_count": 10,
            },
        ],
    )

    report, _ = run_rust_public_data_cache_custody_check(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "rust-custody-blocked-paths",
    )

    assert report.status == "failed"
    assert report.blocked_path_count == 4
    assert report.failure_count == 4
    checks = {failure.check for failure in report.failures}
    assert "cache_ref_parent_dir" in checks
    assert "cache_ref_absolute_path" in checks
    assert "cache_ref_contains_drive_or_scheme_separator" in checks
    assert "cache_ref_contains_backslash_separator" in checks
    assert {sample.status for sample in report.samples} == {"blocked"}


def test_rust_public_data_cache_custody_distinguishes_hash_and_byte_drift(tmp_path, repo_root):
    cache_root = tmp_path / "public-data-cache"
    hash_only = _sample_entry(cache_root, source_id="hash-only", content=b"abc")
    hash_only["sha256"] = sha256(b"def").hexdigest()
    byte_only = _sample_entry(cache_root, source_id="byte-only", content=b"stable")
    byte_only["byte_count"] = len(b"stable") + 1
    _write_manifest(cache_root, [hash_only, byte_only])

    report, _ = run_rust_public_data_cache_custody_check(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "rust-custody-drift",
    )

    assert report.status == "failed"
    assert report.hash_mismatch_count == 1
    assert report.byte_count_mismatch_count == 1
    assert report.failure_count == 2
    assert {failure.check for failure in report.failures} == {
        "sha256_mismatch",
        "byte_count_mismatch",
    }
    assert [sample.status for sample in report.samples] == ["failed", "failed"]


def test_rust_public_data_cache_custody_blocks_tracked_repo_payload_root(tmp_path, repo_root):
    cache_root = repo_root / "examples" / "public"
    report, _ = run_rust_public_data_cache_custody_check(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "rust-custody-tracked",
    )

    assert report.status == "failed"
    assert report.root_violation_count >= 2
    assert any(failure.check == "cache_root_tracked_payload_path" for failure in report.failures)
    assert any(failure.check == "manifest_tracked_payload_path" for failure in report.failures)
