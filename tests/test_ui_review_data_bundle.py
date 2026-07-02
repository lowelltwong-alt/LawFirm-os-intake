from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_review_data_bundle import build_ui_review_data_bundle
from lawfirm_os_intake.util import load_json, write_json


def _write_ui_detail_reports(run_root, *, include_blocked_review=True, external_write=False):
    quality_dir = run_root / "quality"
    quality_dir.mkdir(parents=True)
    write_json(
        run_root / "ui_review_manifest.json",
        {
            "overallStatus": "passed",
            "boundaryFlags": {"readOnly": True, "localJsonOnly": True},
            "external_writes_performed": False,
        },
    )
    write_json(
        quality_dir / "labor_employment_qa_matrix_report.json",
        {
            "status": "labor_employment_qa_matrix_ready_for_review",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": external_write,
        },
    )
    if include_blocked_review:
        write_json(
            quality_dir / "labor_employment_blocked_driver_impact_review_report.json",
            {
                "status": "labor_employment_blocked_driver_impacts_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
            },
        )


def test_build_ui_review_data_bundle_tracks_renderable_local_json(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    out = run_root / "ui_review_data_bundle.json"

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=out,
        generated_at="2026-07-02T00:00:00Z",
    )

    assert out.is_file()
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 3
    assert bundle.required_detail_report_count == 3
    assert bundle.present_detail_report_count == 3
    assert bundle.missing_required_detail_report_count == 0
    assert bundle.external_write_report_count == 0
    assert bundle.local_json_only is True
    assert bundle.lake_write_performed is False
    assert bundle.sqlite_write_performed is False
    assert bundle.external_writes_performed is False
    assert {report.report_kind for report in bundle.detail_reports} == {
        "ui_review_manifest",
        "labor_employment_qa_matrix",
        "labor_employment_blocked_driver_impact_review",
    }
    assert all(report.source_sha256.startswith("sha256:") for report in bundle.detail_reports)


def test_build_ui_review_data_bundle_blocks_missing_required_report(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_blocked_review=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.missing_required_detail_report_count == 1
    missing = [report for report in bundle.detail_reports if not report.present]
    assert missing[0].file_name == "labor_employment_blocked_driver_impact_review_report.json"
    assert bundle.external_writes_performed is False


def test_build_ui_review_data_bundle_fails_side_effect_boundary(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, external_write=True)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    assert bundle.status == "failed_side_effect_boundary"
    assert bundle.external_write_report_count == 1
    assert bundle.external_writes_performed is False
    assert "prohibited write signal" in " ".join(bundle.required_next_actions)


def test_build_ui_review_data_bundle_cli_writes_local_json(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    out = run_root / "ui_review_data_bundle.json"

    code = main(
        [
            "build-ui-review-data-bundle",
            "--run-root",
            str(run_root),
            "--out",
            str(out),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )

    bundle = load_json(out)
    assert code == 0
    assert bundle["status"] == "ready_for_review"
    assert bundle["external_writes_performed"] is False
    assert bundle["lake_write_performed"] is False
    assert bundle["sqlite_write_performed"] is False
