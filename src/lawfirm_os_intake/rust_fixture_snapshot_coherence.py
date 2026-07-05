from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustFixtureSnapshotCoherenceReport
from .util import load_json, write_json


RUST_FIXTURE_SNAPSHOT_COHERENCE_REPORT_FILENAME = "rust_fixture_snapshot_coherence_report.json"
RUST_FIXTURE_SNAPSHOT_COHERENCE_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_fixture_snapshot_coherence_check(
    *,
    root: str | Path,
    expected_manifest: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    timeout_seconds: int = 240,
) -> tuple[RustFixtureSnapshotCoherenceReport, Path]:
    repo = Path(repo_root).resolve()
    out_path = Path(out_dir) / RUST_FIXTURE_SNAPSHOT_COHERENCE_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_FIXTURE_SNAPSHOT_COHERENCE_CARGO_MANIFEST_REF),
        "--bin",
        "fixture_snapshot_coherence",
        "--",
        "--root",
        str(root),
        "--expected-manifest",
        str(expected_manifest),
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
            expected_manifest=expected_manifest,
            check="rust_fixture_snapshot_coherence_invocation",
            message=f"Rust fixture snapshot coherence checker did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustFixtureSnapshotCoherenceReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            root=root,
            expected_manifest=expected_manifest,
            check="rust_fixture_snapshot_coherence_report_missing",
            message=(
                "Rust fixture snapshot coherence checker did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustFixtureSnapshotCoherenceReport.model_validate(fallback), out_path

    report = RustFixtureSnapshotCoherenceReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            root=root,
            expected_manifest=expected_manifest,
            check="rust_fixture_snapshot_coherence_return_code",
            message=(f"Rust checker returned {completed.returncode} but report status was passed."),
        )
        write_json(out_path, fallback)
        return RustFixtureSnapshotCoherenceReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(
    *,
    root: str | Path,
    expected_manifest: str | Path,
    check: str,
    message: str,
) -> dict:
    return {
        "schema_version": "0.1",
        "checker": "fixture-snapshot-coherence-checker",
        "status": "failed",
        "root": str(root),
        "expected_manifest_ref": str(expected_manifest),
        "expected_manifest_sha256": "sha256:" + "0" * 64,
        "current_manifest_sha256": "sha256:" + "0" * 64,
        "expected_file_count": 0,
        "current_file_count": 0,
        "matched_file_count": 0,
        "changed_file_count": 0,
        "missing_file_count": 0,
        "unexpected_file_count": 0,
        "skipped_file_count": 0,
        "skipped_files": [],
        "failure_count": 1,
        "failures": [
            {
                "path": str(root),
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
