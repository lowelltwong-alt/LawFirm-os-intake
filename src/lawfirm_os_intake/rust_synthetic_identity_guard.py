from __future__ import annotations

from pathlib import Path
import subprocess

from .models import RustSyntheticIdentityGuardReport
from .util import load_json, write_json


RUST_SYNTHETIC_IDENTITY_GUARD_REPORT_FILENAME = "rust_synthetic_identity_guard_report.json"
RUST_SYNTHETIC_IDENTITY_GUARD_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"


def run_rust_synthetic_identity_guard(
    *,
    root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    timeout_seconds: int = 240,
) -> tuple[RustSyntheticIdentityGuardReport, Path]:
    repo = Path(repo_root).resolve()
    out_path = Path(out_dir) / RUST_SYNTHETIC_IDENTITY_GUARD_REPORT_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_SYNTHETIC_IDENTITY_GUARD_CARGO_MANIFEST_REF),
        "--bin",
        "synthetic_identity_guard",
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
            check="rust_synthetic_identity_guard_invocation",
            message=f"Rust synthetic identity guard did not complete: {exc}",
        )
        write_json(out_path, fallback)
        return RustSyntheticIdentityGuardReport.model_validate(fallback), out_path

    if not out_path.is_file():
        fallback = _failed_report(
            root=root,
            check="rust_synthetic_identity_guard_report_missing",
            message=(
                "Rust synthetic identity guard did not emit a report; "
                f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
            ),
        )
        write_json(out_path, fallback)
        return RustSyntheticIdentityGuardReport.model_validate(fallback), out_path

    report = RustSyntheticIdentityGuardReport.model_validate(load_json(out_path))
    if completed.returncode != 0 and report.status == "passed":
        fallback = _failed_report(
            root=root,
            check="rust_synthetic_identity_guard_return_code",
            message=f"Rust scanner returned {completed.returncode} but report status was passed.",
        )
        write_json(out_path, fallback)
        return RustSyntheticIdentityGuardReport.model_validate(fallback), out_path
    return report, out_path


def _failed_report(*, root: str | Path, check: str, message: str) -> dict:
    return {
        "schema_version": "0.1",
        "checker": "synthetic-fixture-identity-guard",
        "status": "failed",
        "root": str(root),
        "checked_json_file_count": 0,
        "checked_string_count": 0,
        "checked_email_count": 0,
        "allowed_email_count": 0,
        "blocked_email_count": 0,
        "checked_url_count": 0,
        "allowed_url_count": 0,
        "blocked_url_count": 0,
        "synthetic_flag_violation_count": 0,
        "forbidden_provenance_count": 1,
        "failure_count": 1,
        "failures": [
            {
                "path": str(root),
                "json_path": "$",
                "check": check,
                "value": "",
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
