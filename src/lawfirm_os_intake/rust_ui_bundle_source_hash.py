from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustUIBundleSourceHashReport
from .util import load_json, write_json


RUST_UI_BUNDLE_SOURCE_HASH_REPORT_FILENAME = "rust_ui_bundle_source_hash_report.json"
RUST_UI_BUNDLE_SOURCE_HASH_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_ui_bundle_source_hash_check(
    *,
    root: str | Path,
    bundle: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    timeout_seconds: int = 240,
) -> tuple[RustUIBundleSourceHashReport, Path]:
    repo = Path(repo_root).resolve()
    out_path = Path(out_dir) / RUST_UI_BUNDLE_SOURCE_HASH_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_UI_BUNDLE_SOURCE_HASH_CARGO_MANIFEST_REF),
        "--bin",
        "ui_bundle_source_hash_checker",
        "--",
        "--root",
        str(root),
        "--bundle",
        str(bundle),
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
            root=root,
            bundle=bundle,
            check="rust_ui_bundle_source_hash_invocation",
            message=f"Rust UI bundle source-hash checker did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustUIBundleSourceHashReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            root=root,
            bundle=bundle,
            check="rust_ui_bundle_source_hash_report_missing",
            message=(
                "Rust UI bundle source-hash checker did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustUIBundleSourceHashReport.model_validate(fallback), out_path

    report = RustUIBundleSourceHashReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            root=root,
            bundle=bundle,
            check="rust_ui_bundle_source_hash_return_code",
            message=f"Rust checker returned {completed.returncode} but report status was passed.",
        )
        write_json(out_path, fallback)
        return RustUIBundleSourceHashReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(*, root: str | Path, bundle: str | Path, check: str, message: str) -> dict:
    return {
        "schema_version": "0.1",
        "checker": "ui-bundle-source-hash-checker",
        "status": "failed",
        "root": str(root),
        "bundle_ref": str(bundle),
        "detail_report_count": 0,
        "present_detail_report_count": 0,
        "checked_detail_report_count": 0,
        "matched_detail_report_count": 0,
        "hash_mismatch_count": 0,
        "missing_source_file_count": 0,
        "invalid_source_hash_count": 0,
        "skipped_detail_report_count": 0,
        "checker_error_count": 1,
        "details": [],
        "failure_count": 1,
        "failures": [
            {
                "detail_report_id": None,
                "file_name": str(bundle),
                "check": check,
                "expected_sha256": None,
                "actual_sha256": None,
                "message": message,
            }
        ],
        "candidate_only": True,
        "synthetic_only": True,
        "non_authoritative": True,
        "local_json_only": True,
        "external_writes_performed": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "budget_submission_authorized": False,
        "matter_opening_authorized": False,
        "silent_learning_performed": False,
    }
