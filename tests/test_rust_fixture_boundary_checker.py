import json
import subprocess


def _run_checker(repo_root, *, root, out, ui_bundle=None):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo_root / "rust" / "fixture-boundary-checker" / "Cargo.toml"),
        "--",
        "--root",
        str(root),
        "--out",
        str(out),
    ]
    if ui_bundle is not None:
        command.extend(["--ui-bundle", str(ui_bundle)])
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


def test_rust_fixture_boundary_checker_passes_ui_fixture_bundle(repo_root, tmp_path):
    fixtures = repo_root / "apps" / "legal-intake-budget" / "src" / "fixtures"
    out = tmp_path / "fixture_boundary_report.json"

    completed = _run_checker(
        repo_root,
        root=fixtures,
        ui_bundle=fixtures / "demo-ui-review-data-bundle.json",
        out=out,
    )

    assert completed.returncode == 0, completed.stderr
    report = _load(out)
    assert report["status"] == "passed"
    assert report["failure_count"] == 0
    assert report["checked_json_file_count"] >= 20
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False


def test_rust_fixture_boundary_checker_fails_closed_on_write_flags(repo_root, tmp_path):
    root = tmp_path / "fixtures"
    root.mkdir()
    (root / "bad-report.json").write_text(
        json.dumps(
            {
                "candidate_only": True,
                "synthetic_only": True,
                "non_authoritative": True,
                "local_json_only": True,
                "lake_write_performed": True,
                "rust_runtime_added": True,
                "rust_replacement_allowed": True,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "fixture_boundary_report.json"

    completed = _run_checker(repo_root, root=root, out=out)

    assert completed.returncode == 1
    report = _load(out)
    assert report["status"] == "failed"
    assert report["failure_count"] == 3
    failure_messages = {failure["message"] for failure in report["failures"]}
    assert all(failure["check"] == "required_false_boundary_flag" for failure in report["failures"])
    assert "lake_write_performed must be false when present" in failure_messages
    assert "rust_runtime_added must be false when present" in failure_messages
    assert "rust_replacement_allowed must be false when present" in failure_messages


def test_rust_fixture_boundary_checker_fails_missing_required_ui_detail(repo_root, tmp_path):
    root = tmp_path / "fixtures"
    root.mkdir()
    bundle_path = root / "demo-ui-review-data-bundle.json"
    bundle_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "status": "ready_for_review",
                "detail_report_count": 1,
                "required_detail_report_count": 1,
                "present_detail_report_count": 0,
                "missing_required_detail_report_count": 0,
                "external_write_report_count": 0,
                "candidate_only": True,
                "synthetic_only": True,
                "non_authoritative": True,
                "local_json_only": True,
                "budget_submission_authorized": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "external_writes_performed": False,
                "silent_learning_performed": False,
                "detail_reports": [
                    {
                        "file_name": "missing-required-report.json",
                        "required": True,
                        "present": False,
                        "candidate_only": True,
                        "synthetic_only": True,
                        "external_writes_performed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "fixture_boundary_report.json"

    completed = _run_checker(repo_root, root=root, ui_bundle=bundle_path, out=out)

    assert completed.returncode == 1
    failures = _load(out)["failures"]
    assert {failure["check"] for failure in failures} == {
        "required_detail_report_present",
        "ui_bundle_count_mismatch",
    }
    assert any("missing_required_detail_report_count" in failure["message"] for failure in failures)
