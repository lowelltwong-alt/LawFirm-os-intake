import hashlib
import json
import subprocess

from lawfirm_os_intake.cli import main


def _run_checker(repo_root, *, root, bundle, out):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo_root / "rust" / "fixture-boundary-checker" / "Cargo.toml"),
        "--bin",
        "ui_bundle_source_hash_checker",
        "--",
        "--root",
        str(root),
        "--bundle",
        str(bundle),
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


def _sha(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _bundle(detail_reports):
    return {
        "schema_version": "0.1",
        "ui_review_data_bundle_id": "ui_review_data_bundle_test",
        "status": "ready_for_review",
        "run_root_ref": "<test-run-root>",
        "detail_report_count": len(detail_reports),
        "required_detail_report_count": len(
            [report for report in detail_reports if report["required"]]
        ),
        "present_detail_report_count": len(
            [report for report in detail_reports if report["present"]]
        ),
        "missing_required_detail_report_count": 0,
        "external_write_report_count": 0,
        "detail_reports": detail_reports,
        "required_next_actions": ["ready"],
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
        "generated_at": "2026-07-05T00:00:00Z",
    }


def _detail(
    *,
    detail_report_id,
    report_kind,
    file_name,
    source_sha256=None,
    artifact_ref=None,
    present=True,
    required=True,
):
    return {
        "detail_report_id": detail_report_id,
        "label": detail_report_id,
        "report_kind": report_kind,
        "file_name": file_name,
        "required": required,
        "present": present,
        "status": "ready",
        "renderer": "TestPanel",
        "artifact_ref": artifact_ref or file_name,
        "source_sha256": source_sha256,
        "candidate_only": True,
        "synthetic_only": True,
        "external_writes_performed": False,
        "notes": ["test detail"],
    }


def test_rust_ui_bundle_source_hash_checker_passes_run_root_and_demo_resolution(
    repo_root,
    tmp_path,
):
    root = tmp_path / "fixtures"
    run_report = root / "quality" / "synthetic_confidence_summary_report.json"
    demo_report = root / "demo-synthetic-qa-review-run-report.json"
    _write_json(run_report, {"status": "synthetic_confidence_summary_ready_for_review"})
    _write_json(demo_report, {"status": "synthetic_qa_review_run_ready"})
    bundle_path = root / "demo-ui-review-data-bundle.json"
    _write_json(
        bundle_path,
        _bundle(
            [
                _detail(
                    detail_report_id="synthetic-confidence-summary",
                    report_kind="synthetic_confidence_summary",
                    file_name="synthetic_confidence_summary_report.json",
                    artifact_ref="<demo-run-root>\\quality\\synthetic_confidence_summary_report.json",
                    source_sha256=_sha(run_report),
                ),
                _detail(
                    detail_report_id="synthetic-qa-review-run",
                    report_kind="synthetic_qa_review_run",
                    file_name="synthetic_qa_review_run_report.json",
                    artifact_ref="<demo-run-root>\\synthetic_qa_review_run_report.json",
                    source_sha256=_sha(demo_report),
                ),
                _detail(
                    detail_report_id="optional-missing",
                    report_kind="optional_missing",
                    file_name="optional_missing_report.json",
                    present=False,
                    required=False,
                ),
            ]
        ),
    )
    out = tmp_path / "out" / "rust_ui_bundle_source_hash_report.json"

    completed = _run_checker(repo_root, root=root, bundle=bundle_path, out=out)

    assert completed.returncode == 0, completed.stderr
    report = _load(out)
    assert report["status"] == "passed"
    assert report["detail_report_count"] == 3
    assert report["present_detail_report_count"] == 2
    assert report["checked_detail_report_count"] == 2
    assert report["matched_detail_report_count"] == 2
    assert report["hash_mismatch_count"] == 0
    assert report["missing_source_file_count"] == 0
    assert report["invalid_source_hash_count"] == 0
    assert report["skipped_detail_report_count"] == 1
    assert report["failure_count"] == 0
    strategies = {
        detail["file_name"]: detail["resolution_strategy"] for detail in report["details"]
    }
    assert strategies["synthetic_confidence_summary_report.json"] == "run_root_file_name"
    assert strategies["synthetic_qa_review_run_report.json"] == "demo_fixture_name"
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False


def test_rust_ui_bundle_source_hash_checker_fails_closed_on_bad_sources(
    repo_root,
    tmp_path,
):
    root = tmp_path / "fixtures"
    changed_report = root / "changed_report.json"
    _write_json(changed_report, {"status": "changed"})
    bundle_path = root / "demo-ui-review-data-bundle.json"
    _write_json(
        bundle_path,
        _bundle(
            [
                _detail(
                    detail_report_id="changed",
                    report_kind="changed",
                    file_name="changed_report.json",
                    source_sha256="sha256:" + ("0" * 64),
                ),
                _detail(
                    detail_report_id="missing",
                    report_kind="missing",
                    file_name="missing_report.json",
                    source_sha256="sha256:" + ("1" * 64),
                ),
                _detail(
                    detail_report_id="invalid",
                    report_kind="invalid",
                    file_name="invalid_report.json",
                    source_sha256="not-a-sha",
                ),
            ]
        ),
    )
    out = tmp_path / "out" / "rust_ui_bundle_source_hash_report.json"

    completed = _run_checker(repo_root, root=root, bundle=bundle_path, out=out)

    assert completed.returncode == 1
    report = _load(out)
    assert report["status"] == "failed"
    assert report["checked_detail_report_count"] == 1
    assert report["hash_mismatch_count"] == 1
    assert report["missing_source_file_count"] == 1
    assert report["invalid_source_hash_count"] == 1
    assert report["failure_count"] == 3
    failures = {(failure["detail_report_id"], failure["check"]) for failure in report["failures"]}
    assert ("changed", "ui_detail_source_hash_mismatch") in failures
    assert ("missing", "ui_detail_source_file_missing") in failures
    assert ("invalid", "ui_detail_source_hash_invalid") in failures


def test_rust_ui_bundle_source_hash_checker_refuses_out_of_root_artifact_ref(
    repo_root,
    tmp_path,
):
    root = tmp_path / "fixtures"
    root.mkdir()
    outside = tmp_path / "outside" / "ui_review_manifest.json"
    _write_json(outside, {"status": "outside"})
    bundle_path = root / "ui_review_data_bundle.json"
    _write_json(
        bundle_path,
        _bundle(
            [
                _detail(
                    detail_report_id="ui-review-manifest",
                    report_kind="ui_review_manifest",
                    file_name="ui_review_manifest.json",
                    artifact_ref=str(outside),
                    source_sha256=_sha(outside),
                )
            ]
        ),
    )
    out = tmp_path / "out" / "rust_ui_bundle_source_hash_report.json"

    completed = _run_checker(repo_root, root=root, bundle=bundle_path, out=out)

    assert completed.returncode == 1
    report = _load(out)
    assert report["status"] == "failed"
    assert report["missing_source_file_count"] == 1
    assert report["failure_count"] == 1
    assert report["failures"][0]["check"] == "ui_detail_source_file_missing"


def test_rust_ui_bundle_source_hash_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    root = tmp_path / "fixtures"
    source = root / "ui_review_manifest.json"
    _write_json(source, {"status": "ready"})
    bundle_path = root / "ui_review_data_bundle.json"
    _write_json(
        bundle_path,
        _bundle(
            [
                _detail(
                    detail_report_id="ui-review-manifest",
                    report_kind="ui_review_manifest",
                    file_name="ui_review_manifest.json",
                    source_sha256=_sha(source),
                )
            ]
        ),
    )
    out_dir = tmp_path / "cli-out"

    code = main(
        [
            "build-rust-ui-bundle-source-hash-report",
            "--root",
            str(root),
            "--bundle",
            str(bundle_path),
            "--out-dir",
            str(out_dir),
            "--repo-root",
            str(repo_root),
        ]
    )
    captured = capsys.readouterr()

    report = _load(out_dir / "rust_ui_bundle_source_hash_report.json")
    assert code == 0
    assert report["status"] == "passed"
    assert report["matched_detail_report_count"] == 1
    assert report["candidate_only"] is True
    assert '"lake_write_performed": false' in captured.out
