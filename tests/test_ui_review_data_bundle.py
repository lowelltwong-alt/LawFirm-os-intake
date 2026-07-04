from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_review_data_bundle import build_ui_review_data_bundle
from lawfirm_os_intake.util import load_json, write_json


def _write_ui_detail_reports(
    run_root,
    *,
    include_blocked_review=True,
    include_executable_coverage=True,
    include_output_expectations=True,
    external_write=False,
):
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
    if include_executable_coverage:
        write_json(
            quality_dir / "labor_employment_executable_coverage_report.json",
            {
                "status": "labor_employment_executable_coverage_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
            },
        )
    if include_output_expectations:
        write_json(
            quality_dir / "labor_employment_budget_output_expectations_report.json",
            {
                "status": "labor_employment_budget_output_expectations_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
            },
        )
    write_json(
        quality_dir / "synthetic_confidence_summary_report.json",
        {
            "status": "synthetic_confidence_summary_ready_for_review",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )


def _write_synthetic_qa_review_run_report(run_root):
    write_json(
        run_root / "synthetic_qa_review_run_report.json",
        {
            "status": "synthetic_qa_review_run_ready",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )


def _write_synthetic_qa_blocker_report(run_root):
    write_json(
        run_root / "quality" / "synthetic_qa_blocker_report.json",
        {
            "status": "synthetic_qa_blocker_report_ready_for_review",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )


def _write_synthetic_qa_review_outcome_report(run_root):
    write_json(
        run_root / "quality" / "synthetic_qa_review_outcome_report.json",
        {
            "status": "synthetic_qa_review_outcome_recorded_pending_followup",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )


def _write_matter_linking_preflight_report(run_root):
    write_json(
        run_root / "quality" / "matter_linking_preflight_report.json",
        {
            "status": "matter_linking_preflight_resolved_candidate_requires_review",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "matter_opening_authorized": False,
            "budget_amount_output_authorized": False,
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
    assert bundle.detail_report_count == 10
    assert bundle.required_detail_report_count == 6
    assert bundle.present_detail_report_count == 6
    assert bundle.missing_required_detail_report_count == 0
    assert bundle.external_write_report_count == 0
    assert bundle.local_json_only is True
    assert bundle.lake_write_performed is False
    assert bundle.sqlite_write_performed is False
    assert bundle.external_writes_performed is False
    assert {report.report_kind for report in bundle.detail_reports} == {
        "ui_review_manifest",
        "synthetic_qa_review_run",
        "synthetic_confidence_summary",
        "synthetic_qa_blocker_report",
        "synthetic_qa_review_outcome",
        "matter_linking_preflight",
        "labor_employment_qa_matrix",
        "labor_employment_executable_coverage",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
    }
    present = [report for report in bundle.detail_reports if report.present]
    optional = [
        report
        for report in bundle.detail_reports
        if report.report_kind == "synthetic_qa_review_run"
    ][0]
    assert optional.required is False
    assert optional.present is False
    assert all(report.source_sha256.startswith("sha256:") for report in present)


def test_build_ui_review_data_bundle_includes_optional_synthetic_qa_review_run(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 10
    assert bundle.present_detail_report_count == 7
    assert details["synthetic_qa_review_run"].present is True
    assert details["synthetic_qa_review_run"].required is False
    assert details["synthetic_qa_review_run"].renderer == "SyntheticQAReviewRunPanel"
    assert details["synthetic_qa_review_run"].source_sha256.startswith("sha256:")
    assert details["synthetic_confidence_summary"].present is True
    assert details["synthetic_confidence_summary"].required is True
    assert details["synthetic_confidence_summary"].renderer == "SyntheticConfidenceSummaryPanel"


def test_build_ui_review_data_bundle_includes_optional_synthetic_qa_blocker_report(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_synthetic_qa_blocker_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 10
    assert bundle.present_detail_report_count == 8
    assert details["synthetic_qa_blocker_report"].present is True
    assert details["synthetic_qa_blocker_report"].required is False
    assert details["synthetic_qa_blocker_report"].renderer == "SyntheticQABlockerDrilldownPanel"
    assert details["synthetic_qa_blocker_report"].source_sha256.startswith("sha256:")


def test_build_ui_review_data_bundle_includes_optional_synthetic_qa_review_outcome(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_outcome_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 10
    assert bundle.present_detail_report_count == 7
    assert details["synthetic_qa_review_outcome"].present is True
    assert details["synthetic_qa_review_outcome"].required is False
    assert details["synthetic_qa_review_outcome"].renderer == "SyntheticQAReviewOutcomePanel"
    assert details["synthetic_qa_review_outcome"].source_sha256.startswith("sha256:")
    assert details["synthetic_qa_review_outcome"].external_writes_performed is False


def test_build_ui_review_data_bundle_includes_optional_matter_linking_preflight(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_matter_linking_preflight_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 10
    assert bundle.present_detail_report_count == 8
    assert details["matter_linking_preflight"].present is True
    assert details["matter_linking_preflight"].required is False
    assert details["matter_linking_preflight"].renderer == "MatterLinkingPreflightPanel"
    assert details["matter_linking_preflight"].external_writes_performed is False


def test_build_ui_review_data_bundle_requires_labor_employment_executable_coverage(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_executable_coverage=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.detail_report_count == 10
    assert bundle.required_detail_report_count == 6
    assert bundle.present_detail_report_count == 5
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_executable_coverage"].present is False
    assert details["labor_employment_executable_coverage"].required is True
    assert details["labor_employment_executable_coverage"].renderer == (
        "LaborEmploymentExecutableCoveragePanel"
    )


def test_build_ui_review_data_bundle_blocks_missing_required_report(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_output_expectations=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.missing_required_detail_report_count == 1
    missing = [report for report in bundle.detail_reports if report.required and not report.present]
    assert missing[0].file_name == "labor_employment_budget_output_expectations_report.json"
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
