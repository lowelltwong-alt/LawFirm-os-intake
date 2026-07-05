from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustFixtureBoundaryReport
from .util import load_json, write_json


RUST_FIXTURE_BOUNDARY_REPORT_FILENAME = "rust_fixture_boundary_report.json"
RUST_FIXTURE_BOUNDARY_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_fixture_boundary_check(
    *,
    root: str | Path,
    ui_bundle_path: str | Path | None,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    timeout_seconds: int = 240,
) -> tuple[RustFixtureBoundaryReport, Path]:
    repo = Path(repo_root).resolve()
    out_path = Path(out_dir) / RUST_FIXTURE_BOUNDARY_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_FIXTURE_BOUNDARY_CARGO_MANIFEST_REF),
        "--",
        "--root",
        str(root),
        "--out",
        str(out_path),
    ]
    if ui_bundle_path is not None:
        command.extend(["--ui-bundle", str(ui_bundle_path)])

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
            ui_bundle_path=ui_bundle_path,
            check="rust_fixture_boundary_invocation",
            message=f"Rust fixture boundary checker did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustFixtureBoundaryReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            root=root,
            ui_bundle_path=ui_bundle_path,
            check="rust_fixture_boundary_report_missing",
            message=(
                "Rust fixture boundary checker did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustFixtureBoundaryReport.model_validate(fallback), out_path

    report = RustFixtureBoundaryReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            root=root,
            ui_bundle_path=ui_bundle_path,
            check="rust_fixture_boundary_return_code",
            message=f"Rust checker returned {completed.returncode} but report status was passed.",
        )
        write_json(out_path, fallback)
        return RustFixtureBoundaryReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(
    *,
    root: str | Path,
    ui_bundle_path: str | Path | None,
    check: str,
    message: str,
) -> dict:
    return {
        "schema_version": "0.1",
        "checker": "fixture-boundary-checker",
        "status": "failed",
        "root": str(root),
        "ui_bundle_ref": str(ui_bundle_path) if ui_bundle_path is not None else None,
        "checked_json_file_count": 0,
        "checked_object_count": 0,
        "failure_count": 1,
        "failures": [
            {
                "path": str(root),
                "json_path": "$",
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
