import json
import subprocess

from lawfirm_os_intake.cli import main


def _run_manifest_scanner(repo_root, *, root, out):
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


def _run_snapshot_checker(repo_root, *, root, expected_manifest, out):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo_root / "rust" / "fixture-boundary-checker" / "Cargo.toml"),
        "--bin",
        "fixture_snapshot_coherence",
        "--",
        "--root",
        str(root),
        "--expected-manifest",
        str(expected_manifest),
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


def _write_fixture(path, *, fixture_id, status):
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "fixture_id": fixture_id,
                "status": status,
                "data_origin": "synthetic",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _build_expected_manifest(repo_root, tmp_path):
    root = tmp_path / "fixtures"
    root.mkdir()
    _write_fixture(root / "alpha.json", fixture_id="fixture.alpha", status="ready")
    _write_fixture(root / "beta.json", fixture_id="fixture.beta", status="ready")
    expected_manifest = tmp_path / "expected" / "rust_fixture_manifest_report.json"
    expected_manifest.parent.mkdir()

    completed = _run_manifest_scanner(repo_root, root=root, out=expected_manifest)

    assert completed.returncode == 0, completed.stderr
    return root, expected_manifest


def test_rust_fixture_snapshot_coherence_passes_clean_snapshot(repo_root, tmp_path):
    root, expected_manifest = _build_expected_manifest(repo_root, tmp_path)
    out = tmp_path / "coherence" / "rust_fixture_snapshot_coherence_report.json"

    completed = _run_snapshot_checker(
        repo_root,
        root=root,
        expected_manifest=expected_manifest,
        out=out,
    )

    assert completed.returncode == 0, completed.stderr
    report = _load(out)
    assert report["status"] == "passed"
    assert report["checker"] == "fixture-snapshot-coherence-checker"
    assert report["expected_file_count"] == 2
    assert report["current_file_count"] == 2
    assert report["matched_file_count"] == 2
    assert report["changed_file_count"] == 0
    assert report["missing_file_count"] == 0
    assert report["unexpected_file_count"] == 0
    assert report["failure_count"] == 0
    assert report["expected_manifest_sha256"].startswith("sha256:")
    assert report["current_manifest_sha256"] == report["expected_manifest_sha256"]
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["silent_learning_performed"] is False


def test_rust_fixture_snapshot_coherence_fails_closed_on_drift(repo_root, tmp_path):
    root, expected_manifest = _build_expected_manifest(repo_root, tmp_path)
    _write_fixture(root / "alpha.json", fixture_id="fixture.alpha", status="changed")
    (root / "beta.json").unlink()
    _write_fixture(root / "gamma.json", fixture_id="fixture.gamma", status="new")
    out = tmp_path / "coherence" / "rust_fixture_snapshot_coherence_report.json"

    completed = _run_snapshot_checker(
        repo_root,
        root=root,
        expected_manifest=expected_manifest,
        out=out,
    )

    assert completed.returncode == 1, completed.stderr
    report = _load(out)
    assert report["status"] == "failed"
    assert report["expected_file_count"] == 2
    assert report["current_file_count"] == 2
    assert report["matched_file_count"] == 0
    assert report["changed_file_count"] == 1
    assert report["missing_file_count"] == 1
    assert report["unexpected_file_count"] == 1
    assert report["failure_count"] == 3
    failures = {(failure["path"], failure["check"]) for failure in report["failures"]}
    assert ("alpha.json", "fixture_hash_changed") in failures
    assert ("beta.json", "fixture_missing") in failures
    assert ("gamma.json", "fixture_unexpected") in failures


def test_rust_fixture_snapshot_coherence_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    root, expected_manifest = _build_expected_manifest(repo_root, tmp_path)
    _write_fixture(root / "alpha.json", fixture_id="fixture.alpha", status="changed")
    out_dir = tmp_path / "coherence-cli"

    code = main(
        [
            "build-rust-fixture-snapshot-coherence-report",
            "--root",
            str(root),
            "--expected-manifest",
            str(expected_manifest),
            "--out-dir",
            str(out_dir),
            "--repo-root",
            str(repo_root),
        ]
    )
    captured = capsys.readouterr()

    report = _load(out_dir / "rust_fixture_snapshot_coherence_report.json")
    assert code == 2
    assert report["status"] == "failed"
    assert report["changed_file_count"] == 1
    assert report["failure_count"] == 1
    assert '"lake_write_performed": false' in captured.out
