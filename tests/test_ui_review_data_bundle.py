from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_review_data_bundle import build_ui_review_data_bundle
from lawfirm_os_intake.util import load_json, write_json


def _write_ui_detail_reports(
    run_root,
    *,
    include_blocked_review=True,
    include_executable_coverage=True,
    include_output_expectations=True,
    include_budget_qa_gate=True,
    include_budget_learning_fixtures=True,
    include_budget_outcome_replay_readiness=True,
    include_budget_outcome_replay_execution=True,
    include_budget_outcome_replay_builder_binding=True,
    include_budget_outcome_replay_confidence_status=True,
    include_budget_learning_loop=True,
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
    if include_budget_qa_gate:
        write_json(
            quality_dir / "labor_employment_budget_qa_gate_report.json",
            {
                "status": "labor_employment_budget_qa_gate_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
            },
        )
    if include_budget_learning_fixtures:
        write_json(
            quality_dir / "labor_employment_budget_learning_fixtures_report.json",
            {
                "status": "labor_employment_budget_learning_fixtures_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "budget_submission_authorized": False,
                "matter_opening_authorized": False,
                "silent_learning_performed": False,
            },
        )
    if include_budget_outcome_replay_readiness:
        write_json(
            quality_dir / "labor_employment_budget_outcome_replay_readiness_report.json",
            {
                "status": "labor_employment_budget_outcome_replay_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "budget_submission_authorized": False,
                "matter_opening_authorized": False,
                "silent_learning_performed": False,
            },
        )
    if include_budget_outcome_replay_execution:
        write_json(
            quality_dir / "labor_employment_budget_outcome_replay_execution_report.json",
            {
                "status": "labor_employment_budget_outcome_replay_execution_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "local_json_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "budget_submission_authorized": False,
                "matter_opening_authorized": False,
                "runtime_artifacts_created": False,
                "runtime_artifact_count": 0,
                "silent_learning_performed": False,
            },
        )
    if include_budget_outcome_replay_builder_binding:
        write_json(
            quality_dir / "labor_employment_budget_outcome_replay_builder_binding_report.json",
            {
                "status": "labor_employment_budget_replay_builder_binding_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "local_json_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "budget_submission_authorized": False,
                "matter_opening_authorized": False,
                "runtime_artifacts_created": False,
                "silent_learning_performed": False,
            },
        )
    if include_budget_outcome_replay_confidence_status:
        write_json(
            quality_dir / "labor_employment_budget_outcome_replay_confidence_status_report.json",
            {
                "status": "labor_employment_budget_outcome_replay_confidence_pending_inputs",
                "candidate_only": True,
                "synthetic_only": True,
                "non_authoritative": True,
                "local_json_only": True,
                "human_review_required": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "budget_submission_authorized": False,
                "matter_opening_authorized": False,
                "silent_learning_performed": False,
            },
        )
    if include_budget_learning_loop:
        write_json(
            quality_dir / "budget_learning_loop_report.json",
            {
                "status": "budget_learning_loop_ready_for_review",
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
                "lake_write_performed": False,
                "sqlite_write_performed": False,
                "appeal_submission_performed": False,
                "silent_learning_performed": False,
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


def _write_rust_fixture_boundary_report(run_root):
    write_json(
        run_root / "quality" / "rust_fixture_boundary_report.json",
        {
            "schema_version": "0.1",
            "checker": "fixture-boundary-checker",
            "status": "passed",
            "root": str(run_root),
            "ui_bundle_ref": str(run_root / "ui_review_data_bundle.json"),
            "checked_json_file_count": 4,
            "checked_object_count": 12,
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


def _write_rust_fixture_manifest_report(run_root):
    write_json(
        run_root / "quality" / "rust_fixture_manifest_report.json",
        {
            "schema_version": "0.1",
            "scanner": "fixture-manifest-scanner",
            "status": "passed",
            "root": str(run_root),
            "manifest_sha256": "sha256:" + "a" * 64,
            "checked_json_file_count": 1,
            "parsed_json_file_count": 1,
            "parse_error_count": 0,
            "skipped_file_count": 0,
            "skipped_files": [],
            "total_byte_count": 123,
            "files": [
                {
                    "path": "ui_review_data_bundle.json",
                    "sha256": "sha256:" + "b" * 64,
                    "byte_count": 123,
                    "top_level_type": "object",
                    "schema_version": "0.1",
                    "status": "ready_for_review",
                    "report_kind": None,
                    "data_origin": None,
                    "candidate_only": True,
                    "synthetic_only": True,
                    "external_writes_performed": False,
                    "id_fields": [],
                }
            ],
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


def _write_matter_linking_review_outcome_report(run_root):
    write_json(
        run_root / "quality" / "matter_linking_review_outcome_report.json",
        {
            "status": "matter_linking_review_outcome_recorded",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "matter_opening_authorized": False,
            "budget_amount_output_authorized": False,
            "conflict_conclusion_emitted": False,
            "silent_learning_performed": False,
        },
    )


def _write_matter_linking_qa_gate_report(run_root):
    write_json(
        run_root / "quality" / "matter_linking_qa_gate_report.json",
        {
            "status": "matter_linking_qa_gate_ready_for_review",
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
    assert bundle.detail_report_count == 27
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 13
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
        "rust_fixture_boundary",
        "rust_fixture_manifest",
        "public_data_cache_audit",
        "rust_public_data_cache_custody",
        "public_derived_synthetic_qa_gate",
        "matter_linking_preflight",
        "matter_linking_review_outcome",
        "matter_linking_qa_gate",
        "labor_employment_qa_matrix",
        "labor_employment_executable_coverage",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
        "labor_employment_budget_learning_fixtures",
        "labor_employment_budget_outcome_replay_readiness",
        "labor_employment_budget_outcome_replay_execution",
        "labor_employment_budget_outcome_replay_builder_binding",
        "labor_employment_budget_outcome_replay_confidence_status",
        "budget_learning_loop",
        "ui_demo_qa_recipe",
        "crosswalk_audit",
        "ocg_rule_ir_adoption",
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
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 14
    assert details["synthetic_qa_review_run"].present is True
    assert details["synthetic_qa_review_run"].required is False
    assert details["synthetic_qa_review_run"].renderer == "SyntheticQAReviewRunPanel"
    assert details["synthetic_qa_review_run"].source_sha256.startswith("sha256:")
    assert details["synthetic_confidence_summary"].present is True
    assert details["synthetic_confidence_summary"].required is True
    assert details["synthetic_confidence_summary"].renderer == "SyntheticConfidenceSummaryPanel"
    assert details["rust_fixture_boundary"].present is False
    assert details["rust_fixture_boundary"].required is False
    assert details["rust_fixture_boundary"].renderer == "RustFixtureBoundaryPanel"
    assert details["rust_fixture_manifest"].present is False
    assert details["rust_fixture_manifest"].required is False
    assert details["rust_fixture_manifest"].renderer == "RustFixtureManifestPanel"


def test_build_ui_review_data_bundle_includes_optional_rust_fixture_boundary(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_rust_fixture_boundary_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 15
    assert details["rust_fixture_boundary"].present is True
    assert details["rust_fixture_boundary"].required is False
    assert details["rust_fixture_boundary"].renderer == "RustFixtureBoundaryPanel"
    assert details["rust_fixture_boundary"].source_sha256.startswith("sha256:")


def test_build_ui_review_data_bundle_includes_optional_rust_fixture_manifest(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_rust_fixture_manifest_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 15
    assert details["rust_fixture_manifest"].present is True
    assert details["rust_fixture_manifest"].required is False
    assert details["rust_fixture_manifest"].renderer == "RustFixtureManifestPanel"
    assert details["rust_fixture_manifest"].source_sha256.startswith("sha256:")


def test_build_ui_review_data_bundle_includes_optional_public_data_custody_reports(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    write_json(
        run_root / "public_data_cache_audit_report.json",
        {
            "status": "blocked_public_data_cache",
            "candidate_only": True,
            "external_writes_performed": False,
        },
    )
    write_json(
        run_root / "rust_public_data_cache_custody_report.json",
        {
            "status": "failed",
            "checker": "public-data-cache-custody-checker",
            "candidate_only": True,
            "external_writes_performed": False,
        },
    )
    write_json(
        run_root / "public_derived_synthetic_qa_gate_report.json",
        {
            "status": "public_derived_synthetic_qa_ready_for_review",
            "candidate_only": True,
            "metadata_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "fixture_files_mutated": False,
            "github_pr_created": False,
        },
    )

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 16
    assert details["public_data_cache_audit"].present is True
    assert details["public_data_cache_audit"].required is False
    assert details["public_data_cache_audit"].status == "blocked_public_data_cache"
    assert details["public_data_cache_audit"].renderer == "PublicDataCacheAuditPanel"
    assert details["rust_public_data_cache_custody"].present is True
    assert details["rust_public_data_cache_custody"].required is False
    assert details["rust_public_data_cache_custody"].status == "failed"
    assert details["rust_public_data_cache_custody"].renderer == "RustPublicDataCacheCustodyPanel"
    assert details["public_derived_synthetic_qa_gate"].present is True
    assert details["public_derived_synthetic_qa_gate"].required is False
    assert details["public_derived_synthetic_qa_gate"].status == (
        "public_derived_synthetic_qa_ready_for_review"
    )
    assert details["public_derived_synthetic_qa_gate"].renderer == (
        "PublicDerivedSyntheticQAGatePanel"
    )


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
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 15
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
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 14
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
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 15
    assert details["matter_linking_preflight"].present is True
    assert details["matter_linking_preflight"].required is False
    assert details["matter_linking_preflight"].renderer == "MatterLinkingPreflightPanel"
    assert details["matter_linking_preflight"].external_writes_performed is False


def test_build_ui_review_data_bundle_includes_optional_matter_linking_review_outcome(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_matter_linking_preflight_report(run_root)
    _write_matter_linking_review_outcome_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 16
    assert details["matter_linking_review_outcome"].present is True
    assert details["matter_linking_review_outcome"].required is False
    assert details["matter_linking_review_outcome"].renderer == "MatterLinkingReviewOutcomePanel"
    assert details["matter_linking_review_outcome"].external_writes_performed is False


def test_build_ui_review_data_bundle_includes_optional_matter_linking_qa_gate(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root)
    _write_synthetic_qa_review_run_report(run_root)
    _write_matter_linking_preflight_report(run_root)
    _write_matter_linking_review_outcome_report(run_root)
    _write_matter_linking_qa_gate_report(run_root)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )
    details = {report.report_kind: report for report in bundle.detail_reports}

    assert bundle.status == "ready_for_review"
    assert bundle.detail_report_count == 27
    assert bundle.present_detail_report_count == 17
    assert details["matter_linking_qa_gate"].present is True
    assert details["matter_linking_qa_gate"].required is False
    assert details["matter_linking_qa_gate"].renderer == "MatterLinkingQAGatePanel"
    assert details["matter_linking_qa_gate"].external_writes_performed is False


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
    assert bundle.detail_report_count == 27
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_executable_coverage"].present is False
    assert details["labor_employment_executable_coverage"].required is True
    assert details["labor_employment_executable_coverage"].renderer == (
        "LaborEmploymentExecutableCoveragePanel"
    )


def test_build_ui_review_data_bundle_requires_labor_employment_budget_learning_fixtures(
    tmp_path,
):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_learning_fixtures=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_budget_learning_fixtures"].present is False
    assert details["labor_employment_budget_learning_fixtures"].required is True
    assert details["labor_employment_budget_learning_fixtures"].renderer == (
        "LaborEmploymentBudgetLearningFixturesPanel"
    )


def test_build_ui_review_data_bundle_requires_labor_employment_budget_outcome_replay_readiness(
    tmp_path,
):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_outcome_replay_readiness=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_budget_outcome_replay_readiness"].present is False
    assert details["labor_employment_budget_outcome_replay_readiness"].required is True
    assert details["labor_employment_budget_outcome_replay_readiness"].renderer == (
        "LaborEmploymentBudgetOutcomeReplayReadinessPanel"
    )


def test_build_ui_review_data_bundle_requires_labor_employment_budget_outcome_replay_execution(
    tmp_path,
):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_outcome_replay_execution=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_budget_outcome_replay_execution"].present is False
    assert details["labor_employment_budget_outcome_replay_execution"].required is True
    assert details["labor_employment_budget_outcome_replay_execution"].renderer == (
        "LaborEmploymentBudgetOutcomeReplayExecutionPanel"
    )


def test_build_ui_review_data_bundle_requires_labor_employment_budget_outcome_replay_builder_binding(
    tmp_path,
):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_outcome_replay_builder_binding=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_budget_outcome_replay_builder_binding"].present is False
    assert details["labor_employment_budget_outcome_replay_builder_binding"].required is True
    assert details["labor_employment_budget_outcome_replay_builder_binding"].renderer == (
        "LaborEmploymentBudgetOutcomeReplayBuilderBindingPanel"
    )


def test_build_ui_review_data_bundle_requires_labor_employment_budget_outcome_replay_confidence_status(
    tmp_path,
):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_outcome_replay_confidence_status=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["labor_employment_budget_outcome_replay_confidence_status"].present is False
    assert details["labor_employment_budget_outcome_replay_confidence_status"].required is True
    assert details["labor_employment_budget_outcome_replay_confidence_status"].renderer == (
        "LaborEmploymentBudgetOutcomeReplayConfidenceStatusPanel"
    )


def test_build_ui_review_data_bundle_requires_budget_learning_loop(tmp_path):
    run_root = tmp_path / "demo"
    run_root.mkdir()
    _write_ui_detail_reports(run_root, include_budget_learning_loop=False)

    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=run_root / "ui_review_data_bundle.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    details = {report.report_kind: report for report in bundle.detail_reports}
    assert bundle.status == "blocked_missing_required_reports"
    assert bundle.required_detail_report_count == 13
    assert bundle.present_detail_report_count == 12
    assert bundle.missing_required_detail_report_count == 1
    assert details["budget_learning_loop"].present is False
    assert details["budget_learning_loop"].required is True
    assert details["budget_learning_loop"].renderer == "BudgetLearningLoopPanel"


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
