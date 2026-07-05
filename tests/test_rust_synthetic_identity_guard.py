import json
import subprocess

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import RustSyntheticIdentityGuardReport
from lawfirm_os_intake.util import load_json


def _run_guard(repo_root, *, root, out):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo_root / "rust" / "fixture-boundary-checker" / "Cargo.toml"),
        "--bin",
        "synthetic_identity_guard",
        "--",
        "--root",
        str(root),
        "--out",
        str(out),
    ]
    return subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=240,
        check=False,
    )


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_rust_synthetic_identity_guard_passes_checked_synthetic_roots(repo_root, tmp_path):
    examples_out = tmp_path / "examples" / "rust_synthetic_identity_guard_report.json"
    ui_out = tmp_path / "ui" / "rust_synthetic_identity_guard_report.json"

    examples = _run_guard(repo_root, root=repo_root / "examples" / "synthetic", out=examples_out)
    ui = _run_guard(
        repo_root,
        root=repo_root / "apps" / "legal-intake-budget" / "src" / "fixtures",
        out=ui_out,
    )

    examples_report = RustSyntheticIdentityGuardReport.model_validate(load_json(examples_out))
    ui_report = RustSyntheticIdentityGuardReport.model_validate(load_json(ui_out))
    assert examples.returncode == 0, examples.stderr
    assert ui.returncode == 0, ui.stderr
    assert examples_report.status == "passed"
    assert examples_report.checked_json_file_count >= 100
    assert examples_report.checked_email_count > 0
    assert examples_report.blocked_email_count == 0
    assert examples_report.blocked_url_count == 0
    assert examples_report.synthetic_flag_violation_count == 0
    assert examples_report.forbidden_provenance_count == 0
    assert examples_report.failure_count == 0
    assert ui_report.status == "passed"
    assert ui_report.checked_json_file_count >= 20
    assert ui_report.failure_count == 0
    assert ui_report.external_writes_performed is False
    assert ui_report.lake_write_performed is False
    assert ui_report.sqlite_write_performed is False


def test_rust_synthetic_identity_guard_fails_real_domains_and_provenance(
    repo_root,
    tmp_path,
):
    root = tmp_path / "fixtures"
    _write_json(
        root / "bad-source-bundle.json",
        {
            "schema_version": "0.1",
            "bundle_id": "bad-realish-source",
            "data_origin": "production",
            "contains_real_client_data": True,
            "contains_real_matter_data": True,
            "contains_privileged_data": True,
            "sources": [
                {
                    "source_id": "bad-email-001",
                    "source_type": "email",
                    "text": (
                        "From: real.sender@gmail.com\n"
                        "See https://real-lawfirm.invalid.example.com for a safe URL, "
                        "but https://example-lawfirm.com is not a reserved fixture domain."
                    ),
                    "metadata": {"synthetic": False},
                }
            ],
        },
    )
    out = tmp_path / "out" / "rust_synthetic_identity_guard_report.json"

    completed = _run_guard(repo_root, root=root, out=out)

    report = RustSyntheticIdentityGuardReport.model_validate(load_json(out))
    checks = {failure.check for failure in report.failures}
    assert completed.returncode == 1
    assert report.status == "failed"
    assert report.blocked_email_count == 1
    assert report.blocked_url_count == 1
    assert report.synthetic_flag_violation_count == 1
    assert report.forbidden_provenance_count == 4
    assert report.failure_count == 7
    assert "non_reserved_email_domain" in checks
    assert "non_reserved_url_domain" in checks
    assert "synthetic_data_origin_required" in checks
    assert "synthetic_marker_false" in checks
    assert "forbidden_real_or_public_provenance" in checks


def test_rust_synthetic_identity_guard_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    root = tmp_path / "fixtures"
    _write_json(
        root / "safe-source-bundle.json",
        {
            "schema_version": "0.1",
            "bundle_id": "safe-synthetic-source",
            "data_origin": "synthetic",
            "contains_real_client_data": False,
            "contains_real_matter_data": False,
            "contains_privileged_data": False,
            "sources": [
                {
                    "source_id": "safe-email-001",
                    "source_type": "email",
                    "text": "From: sender@example.invalid\nTo: intake@synthetic-law.example",
                    "metadata": {"synthetic": True},
                }
            ],
        },
    )

    code = main(
        [
            "build-rust-synthetic-identity-guard-report",
            "--root",
            str(root),
            "--out-dir",
            str(tmp_path / "out"),
            "--repo-root",
            str(repo_root),
        ]
    )
    captured = capsys.readouterr()

    report = load_json(tmp_path / "out" / "rust_synthetic_identity_guard_report.json")
    assert code == 0
    assert report["status"] == "passed"
    assert report["checked_email_count"] == 2
    assert report["blocked_email_count"] == 0
    assert report["candidate_only"] is True
    assert report["external_writes_performed"] is False
    assert '"lake_write_performed": false' in captured.out
