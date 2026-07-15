import json
from pathlib import Path

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.rust_fixture_snapshot_coherence import (
    run_rust_fixture_snapshot_coherence_check,
)
from lawfirm_os_intake.rust_ui_bundle_source_hash import run_rust_ui_bundle_source_hash_check
from lawfirm_os_intake.ui_demo_fixture_refresh import refresh_ui_demo_fixtures
from lawfirm_os_intake.ui_review_data_bundle import DETAIL_REPORT_SPECS
from lawfirm_os_intake.util import load_json


UI_FIXTURES = Path("apps/legal-intake-budget/src/fixtures")


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _bundle(details):
    return {
        "schema_version": "0.1",
        "ui_review_data_bundle_id": "ui_review_data_bundle_test",
        "status": "ready_for_review",
        "run_root_ref": "<demo-run-root>",
        "detail_report_count": len(details),
        "required_detail_report_count": len([detail for detail in details if detail["required"]]),
        "present_detail_report_count": len([detail for detail in details if detail["present"]]),
        "missing_required_detail_report_count": 0,
        "external_write_report_count": 0,
        "detail_reports": details,
        "required_next_actions": ["ready"],
        "candidate_only": True,
        "synthetic_only": True,
        "non_authoritative": True,
        "local_json_only": True,
        "not_authorized_for_external_write": True,
        "not_authorized_for_lake_write": True,
        "not_authorized_for_sqlite_write": True,
        "not_authorized_for_budget_submission": True,
        "not_authorized_for_matter_opening": True,
        "not_authorized_for_calibration": True,
        "budget_amount_output_authorized": False,
        "budget_submission_authorized": False,
        "conflict_conclusion_emitted": False,
        "matter_opening_authorized": False,
        "training_pipeline_created": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "silent_learning_performed": False,
        "generated_at": "2026-07-05T00:00:00Z",
    }


def _detail(*, detail_report_id, report_kind, file_name, source_sha256=None, required=True):
    return {
        "detail_report_id": detail_report_id,
        "label": detail_report_id,
        "report_kind": report_kind,
        "file_name": file_name,
        "required": required,
        "present": True,
        "status": "ready",
        "renderer": "TestPanel",
        "artifact_ref": f"<demo-run-root>\\quality\\{file_name}",
        "source_sha256": source_sha256,
        "candidate_only": True,
        "synthetic_only": True,
        "external_writes_performed": False,
        "notes": ["test detail"],
    }


def _seed_refresh_fixture_root(tmp_path):
    root = tmp_path / "fixtures"
    _write_json(root / "demo-run-manifest.json", {"overallStatus": "blocked"})
    _write_json(
        root / "demo-synthetic-confidence-summary-report.json",
        {"status": "synthetic_confidence_summary_ready_for_review"},
    )
    _write_json(
        root / "demo-rust-fixture-manifest-report.json",
        {
            "schema_version": "0.1",
            "scanner": "fixture-manifest-scanner",
            "status": "passed",
            "manifest_sha256": "sha256:" + ("0" * 64),
            "checked_json_file_count": 0,
            "parsed_json_file_count": 0,
            "parse_error_count": 0,
            "skipped_file_count": 0,
            "skipped_files": [],
            "total_byte_count": 0,
            "files": [],
            "failure_count": 0,
            "failures": [],
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
        },
    )
    stale = "sha256:" + ("1" * 64)
    _write_json(
        root / "demo-ui-review-data-bundle.json",
        _bundle(
            [
                _detail(
                    detail_report_id="ui-review-manifest",
                    report_kind="ui_review_manifest",
                    file_name="ui_review_manifest.json",
                    source_sha256=stale,
                ),
                _detail(
                    detail_report_id="synthetic-confidence-summary",
                    report_kind="synthetic_confidence_summary",
                    file_name="synthetic_confidence_summary_report.json",
                    source_sha256=stale,
                ),
                _detail(
                    detail_report_id="rust-fixture-manifest",
                    report_kind="rust_fixture_manifest",
                    file_name="rust_fixture_manifest_report.json",
                    source_sha256=stale,
                    required=False,
                ),
            ]
        ),
    )
    existing_ids = {
        "ui-review-manifest",
        "synthetic-confidence-summary",
        "rust-fixture-manifest",
    }
    for spec in DETAIL_REPORT_SPECS:
        if not spec.required or spec.detail_report_id in existing_ids:
            continue
        _write_json(
            root / ("demo-" + spec.file_name[:-5].replace("_", "-") + ".json"),
            {
                "status": "synthetic_fixture_ready",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
            },
        )
    return root


def test_refresh_ui_demo_fixtures_requires_explicit_write_flag(repo_root, tmp_path):
    root = _seed_refresh_fixture_root(tmp_path)
    before = (root / "demo-ui-review-data-bundle.json").read_text(encoding="utf-8")

    code = main(
        [
            "refresh-ui-demo-fixtures",
            "--fixtures-root",
            str(root),
            "--out-dir",
            str(tmp_path / "out"),
            "--repo-root",
            str(repo_root),
        ]
    )

    report = load_json(tmp_path / "out" / "ui_demo_fixture_refresh_report.json")
    assert code == 2
    assert report["status"] == "ui_demo_fixture_refresh_blocked_write_flag_required"
    assert report["local_fixture_updates_performed"] is False
    assert (root / "demo-ui-review-data-bundle.json").read_text(encoding="utf-8") == before


def test_refresh_ui_demo_fixtures_updates_bundle_and_manifest(repo_root, tmp_path):
    root = _seed_refresh_fixture_root(tmp_path)

    report, report_path = refresh_ui_demo_fixtures(
        fixtures_root=root,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        generated_at="2026-07-05T00:00:00Z",
    )

    bundle = load_json(root / "demo-ui-review-data-bundle.json")
    detail_hashes = {
        detail["file_name"]: detail["source_sha256"] for detail in bundle["detail_reports"]
    }
    manifest = load_json(root / "demo-rust-fixture-manifest-report.json")
    persisted = load_json(report_path)
    assert report.status == "ui_demo_fixture_refresh_verified"
    assert persisted["status"] == "ui_demo_fixture_refresh_verified"
    assert report.local_fixture_updates_performed is True
    assert report.source_hash_update_count == 3
    assert report.manifest_status == "passed"
    assert report.source_hash_gate_status == "passed"
    assert report.snapshot_gate_status == "passed"
    assert bundle["ui_review_data_bundle_id"].startswith("ui_review_data_bundle_")
    assert detail_hashes["ui_review_manifest.json"].startswith("sha256:")
    assert detail_hashes["synthetic_confidence_summary_report.json"].startswith("sha256:")
    assert detail_hashes["rust_fixture_manifest_report.json"].startswith("sha256:")
    assert manifest["status"] == "passed"
    assert any(
        skipped["path"] == "demo-ui-review-data-bundle.json"
        for skipped in manifest["skipped_files"]
    )


def test_refresh_ui_demo_fixtures_blocks_detail_without_explicit_boundary_fields(
    repo_root, tmp_path
):
    root = _seed_refresh_fixture_root(tmp_path)
    bundle_path = root / "demo-ui-review-data-bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["detail_reports"][0].pop("candidate_only")
    bundle_path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")

    report, _report_path = refresh_ui_demo_fixtures(
        fixtures_root=root,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        generated_at="2026-07-15T00:00:00Z",
    )

    assert report.status == "ui_demo_fixture_refresh_failed"


def test_checked_ui_demo_fixture_wrappers_are_rust_verified(repo_root, tmp_path):
    fixtures = repo_root / UI_FIXTURES

    source_hash_report, _ = run_rust_ui_bundle_source_hash_check(
        root=fixtures,
        bundle=fixtures / "demo-ui-review-data-bundle.json",
        out_dir=tmp_path / "source-hash",
        repo_root=repo_root,
    )
    snapshot_report, _ = run_rust_fixture_snapshot_coherence_check(
        root=fixtures,
        expected_manifest=fixtures / "demo-rust-fixture-manifest-report.json",
        out_dir=tmp_path / "snapshot",
        repo_root=repo_root,
    )

    assert source_hash_report.status == "passed"
    assert source_hash_report.hash_mismatch_count == 0
    assert source_hash_report.missing_source_file_count == 0
    assert snapshot_report.status == "passed"
    assert snapshot_report.failure_count == 0
