import json
import subprocess

from lawfirm_os_intake.cli import main


def _run_scanner(repo_root, *, root, out):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo_root / "rust" / "fixture-boundary-checker" / "Cargo.toml"),
        "--bin",
        "fixture_manifest_scanner",
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


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_rust_fixture_manifest_scanner_hashes_ui_fixture_bundle(repo_root, tmp_path):
    fixtures = repo_root / "apps" / "legal-intake-budget" / "src" / "fixtures"
    out = tmp_path / "rust_fixture_manifest_report.json"

    completed = _run_scanner(repo_root, root=fixtures, out=out)

    assert completed.returncode == 0, completed.stderr
    report = _load(out)
    assert report["status"] == "passed"
    assert report["scanner"] == "fixture-manifest-scanner"
    assert report["manifest_sha256"].startswith("sha256:")
    assert report["checked_json_file_count"] >= 20
    assert report["parsed_json_file_count"] == report["checked_json_file_count"]
    assert report["parse_error_count"] == 0
    assert report["skipped_file_count"] >= 1
    assert report["failure_count"] == 0
    assert report["total_byte_count"] > 0
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert all(file["sha256"].startswith("sha256:") for file in report["files"])
    assert any(
        file["path"] == "demo-ui-review-data-bundle.json" for file in report["skipped_files"]
    )
    assert any(
        file["path"] == "demo-run-manifest.json" and file["top_level_type"] == "object"
        for file in report["files"]
    )


def test_rust_fixture_manifest_cli_writes_candidate_report(repo_root, tmp_path, capsys):
    fixtures = repo_root / "apps" / "legal-intake-budget" / "src" / "fixtures"
    out_dir = tmp_path / "rust-manifest"

    code = main(
        [
            "build-rust-fixture-manifest-report",
            "--root",
            str(fixtures),
            "--out-dir",
            str(out_dir),
            "--repo-root",
            str(repo_root),
        ]
    )
    captured = capsys.readouterr()

    report = _load(out_dir / "rust_fixture_manifest_report.json")
    assert code == 0
    assert report["status"] == "passed"
    assert report["failure_count"] == 0
    assert report["manifest_sha256"].startswith("sha256:")
    assert report["skipped_file_count"] >= 1
    assert '"lake_write_performed": false' in captured.out


def test_rust_fixture_manifest_scanner_fails_closed_on_invalid_json(repo_root, tmp_path):
    root = tmp_path / "fixtures"
    root.mkdir()
    (root / "good.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "status": "ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
            }
        ),
        encoding="utf-8",
    )
    (root / "bad.json").write_text("{not-json", encoding="utf-8")
    out = tmp_path / "rust_fixture_manifest_report.json"

    completed = _run_scanner(repo_root, root=root, out=out)

    assert completed.returncode == 1
    report = _load(out)
    assert report["status"] == "failed"
    assert report["checked_json_file_count"] == 2
    assert report["parsed_json_file_count"] == 1
    assert report["parse_error_count"] == 1
    assert report["skipped_file_count"] == 0
    assert report["failure_count"] == 1
    assert report["failures"][0]["path"] == "bad.json"
    assert report["failures"][0]["check"] == "json_fixture_manifest_parse"
