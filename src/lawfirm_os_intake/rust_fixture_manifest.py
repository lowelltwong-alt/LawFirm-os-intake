from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustFixtureManifestReport
from .util import load_json, write_json


RUST_FIXTURE_MANIFEST_REPORT_FILENAME = "rust_fixture_manifest_report.json"
RUST_FIXTURE_MANIFEST_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_fixture_manifest_scan(
    *,
    root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    timeout_seconds: int = 240,
) -> tuple[RustFixtureManifestReport, Path]:
    repo = Path(repo_root).resolve()
    out_path = Path(out_dir) / RUST_FIXTURE_MANIFEST_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_FIXTURE_MANIFEST_CARGO_MANIFEST_REF),
        "--bin",
        "fixture_manifest_scanner",
        "--",
        "--root",
        str(root),
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
            check="rust_fixture_manifest_invocation",
            message=f"Rust fixture manifest scanner did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustFixtureManifestReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            root=root,
            check="rust_fixture_manifest_report_missing",
            message=(
                "Rust fixture manifest scanner did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustFixtureManifestReport.model_validate(fallback), out_path

    report = RustFixtureManifestReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            root=root,
            check="rust_fixture_manifest_return_code",
            message=f"Rust scanner returned {completed.returncode} but report status was passed.",
        )
        write_json(out_path, fallback)
        return RustFixtureManifestReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(*, root: str | Path, check: str, message: str) -> dict:
    return {
        "schema_version": "0.1",
        "scanner": "fixture-manifest-scanner",
        "status": "failed",
        "root": str(root),
        "manifest_sha256": "sha256:" + "0" * 64,
        "checked_json_file_count": 0,
        "parsed_json_file_count": 0,
        "parse_error_count": 1,
        "skipped_file_count": 0,
        "skipped_files": [],
        "total_byte_count": 0,
        "files": [],
        "failure_count": 1,
        "failures": [
            {
                "path": str(root),
                "check": check,
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
