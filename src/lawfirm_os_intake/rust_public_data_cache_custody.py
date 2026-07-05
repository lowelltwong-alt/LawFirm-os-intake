from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustPublicDataCacheCustodyReport
from .util import load_json, write_json


PUBLIC_DATA_CACHE_MANIFEST_FILENAME = "public_data_cache_manifest.json"
RUST_PUBLIC_DATA_CACHE_CUSTODY_REPORT_FILENAME = "rust_public_data_cache_custody_report.json"
RUST_PUBLIC_DATA_CACHE_CUSTODY_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_public_data_cache_custody_check(
    *,
    repo_root: str | Path,
    cache_root: str | Path,
    out_dir: str | Path,
    manifest_path: str | Path | None = None,
    timeout_seconds: int = 240,
) -> tuple[RustPublicDataCacheCustodyReport, Path]:
    repo = Path(repo_root).resolve()
    cache = Path(cache_root).resolve()
    manifest = (
        Path(manifest_path).resolve()
        if manifest_path
        else cache / PUBLIC_DATA_CACHE_MANIFEST_FILENAME
    )
    out_path = Path(out_dir) / RUST_PUBLIC_DATA_CACHE_CUSTODY_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_PUBLIC_DATA_CACHE_CUSTODY_CARGO_MANIFEST_REF),
        "--bin",
        "public_data_cache_custody_checker",
        "--",
        "--repo-root",
        str(repo),
        "--cache-root",
        str(cache),
        "--manifest",
        str(manifest),
        "--out",
        str(out_path),
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fallback = _failed_report(
            repo_root=repo,
            cache_root=cache,
            manifest=manifest,
            check="rust_public_data_cache_custody_invocation",
            message=f"Rust public-data cache custody checker did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustPublicDataCacheCustodyReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            repo_root=repo,
            cache_root=cache,
            manifest=manifest,
            check="rust_public_data_cache_custody_report_missing",
            message=(
                "Rust public-data cache custody checker did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustPublicDataCacheCustodyReport.model_validate(fallback), out_path

    report = RustPublicDataCacheCustodyReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            repo_root=repo,
            cache_root=cache,
            manifest=manifest,
            check="rust_public_data_cache_custody_return_code",
            message=f"Rust checker returned {completed.returncode} but report status was passed.",
        )
        write_json(out_path, fallback)
        return RustPublicDataCacheCustodyReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(
    *,
    repo_root: Path,
    cache_root: Path,
    manifest: Path,
    check: str,
    message: str,
) -> dict:
    return {
        "schema_version": "0.1",
        "checker": "public-data-cache-custody-checker",
        "status": "failed",
        "repo_root": str(repo_root),
        "cache_root": str(cache_root),
        "manifest_ref": str(manifest),
        "manifest_sha256": "sha256:" + "0" * 64,
        "manifest_byte_count": 0,
        "manifest_entry_count": 0,
        "checked_source_count": 0,
        "checked_sample_count": 0,
        "total_checked_sample_bytes": 0,
        "root_violation_count": 0,
        "manifest_error_count": 1,
        "invalid_manifest_entry_count": 0,
        "blocked_path_count": 0,
        "missing_file_count": 0,
        "hash_mismatch_count": 0,
        "byte_count_mismatch_count": 0,
        "failure_count": 1,
        "failures": [
            {
                "source_id": "manifest",
                "path": str(manifest),
                "check": check,
                "expected": None,
                "actual": None,
                "message": message,
            }
        ],
        "samples": [],
        "candidate_only": True,
        "planning_only": True,
        "non_authoritative": True,
        "metadata_only_report": True,
        "local_file_custody_only": True,
        "public_cache_samples_may_be_present": False,
        "direct_runtime_ingestion_allowed": False,
        "public_records_runtime_ingested": False,
        "public_payload_committed": False,
        "raw_public_payload_committed": False,
        "tracked_public_payload_committed": False,
        "connector_implemented": False,
        "legal_knowledge_adapter_authorized": False,
        "synthetic_fixtures_created": False,
        "fixture_files_mutated": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "matter_opening_authorized": False,
        "budget_submission_authorized": False,
        "silent_learning_performed": False,
    }
