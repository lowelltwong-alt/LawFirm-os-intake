from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_qa_bundle import (
    SYNTHETIC_QA_BUNDLE_REPORT_FILENAME,
    run_synthetic_qa_bundle,
)
from lawfirm_os_intake.util import load_json, write_json


def _write_ready_labor_employment_qa_matrix(path):
    write_json(
        path,
        {
            "status": "labor_employment_qa_matrix_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_submission_authorized": False,
        },
    )


def _write_ready_labor_employment_fixture_family_pack(path):
    write_json(
        path,
        {
            "status": "labor_employment_fixture_family_pack_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "fixture_generation_authorized": False,
            "calibration_approved": False,
        },
    )


def _write_ready_labor_employment_executable_fixtures(path):
    write_json(
        path,
        {
            "status": "labor_employment_executable_fixtures_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_submission_authorized": False,
            "fixture_generation_authorized": False,
            "calibration_approved": False,
        },
    )


def _write_ready_labor_employment_executable_coverage(path):
    write_json(
        path,
        {
            "status": "labor_employment_executable_coverage_ready_for_review",
            "coverage_state": "partial_executable_coverage",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "fixture_generation_authorized": False,
            "calibration_approved": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_executable_fact_binding(path):
    write_json(
        path,
        {
            "status": "labor_employment_executable_budget_fact_bindings_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_executable_driver_binding(path):
    write_json(
        path,
        {
            "status": "labor_employment_executable_driver_bindings_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_executable_driver_impact(path):
    write_json(
        path,
        {
            "status": "labor_employment_executable_driver_impacts_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_budget_fact_gold(path):
    write_json(
        path,
        {
            "status": "passed",
            "reviewed_gold": True,
            "data_scope": "synthetic",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "silent_learning_performed": False,
        },
    )


def test_synthetic_qa_bundle_blocks_missing_calibration_and_builds_ui(tmp_path):
    run_root = tmp_path / "demo"
    budget_dir = run_root / "budget"
    quality_dir = run_root / "quality"
    external_depth_dir = tmp_path / "fixture-depth"
    budget_dir.mkdir(parents=True)
    quality_dir.mkdir()
    external_depth_dir.mkdir()
    write_json(
        budget_dir / "budget_coherence_report.json",
        {"status": "passed", "external_writes_performed": False},
    )
    write_json(
        external_depth_dir / "synthetic_fixture_depth_audit_report.json",
        {
            "status": "synthetic_fixture_depth_ready_for_review",
            "external_writes_performed": False,
        },
    )
    _write_ready_labor_employment_qa_matrix(quality_dir / "labor_employment_qa_matrix_report.json")
    _write_ready_labor_employment_fixture_family_pack(
        quality_dir / "labor_employment_fixture_family_pack_report.json"
    )
    _write_ready_labor_employment_executable_fixtures(
        quality_dir / "labor_employment_executable_fixtures_report.json"
    )
    _write_ready_labor_employment_executable_coverage(
        quality_dir / "labor_employment_executable_coverage_report.json"
    )
    _write_ready_labor_employment_executable_fact_binding(
        quality_dir / "labor_employment_executable_fact_binding_report.json"
    )
    _write_ready_labor_employment_executable_driver_binding(
        quality_dir / "labor_employment_executable_driver_binding_report.json"
    )
    _write_ready_labor_employment_executable_driver_impact(
        quality_dir / "labor_employment_executable_driver_impact_report.json"
    )
    _write_ready_labor_employment_budget_fact_gold(
        quality_dir / "labor_employment_budget_fact_gold_report.json"
    )

    report, run_dir, ui_manifest = run_synthetic_qa_bundle(
        run_root=run_root,
        out_dir=quality_dir,
        fixture_depth_report_path=(
            external_depth_dir / "synthetic_fixture_depth_audit_report.json"
        ),
        ui_manifest_out=run_root / "ui_review_manifest.json",
        generated_at="2026-07-02T00:00:00Z",
    )

    persisted = load_json(run_dir / SYNTHETIC_QA_BUNDLE_REPORT_FILENAME)
    gates = {gate["gateId"]: gate for gate in ui_manifest["qualityGates"]}
    assert report.status == "blocked"
    assert persisted["missing_required_artifact_count"] == 1
    assert persisted["lake_write_performed"] is False
    assert persisted["sqlite_write_performed"] is False
    assert persisted["budget_submission_performed"] is False
    assert (run_dir / "synthetic_fixture_depth_audit_report.json").is_file()
    assert gates["synthetic_qa_bundle"]["status"] == "blocked"
    assert gates["budget_coherence"]["status"] == "passed"
    assert ui_manifest["boundaryFlags"]["networkCallsAllowed"] is False


def test_synthetic_qa_bundle_can_generate_fixture_depth_from_manifest(tmp_path, repo_root):
    run_root = tmp_path / "demo"
    budget_dir = run_root / "budget"
    quality_dir = run_root / "quality"
    budget_dir.mkdir(parents=True)
    quality_dir.mkdir(parents=True)
    write_json(
        budget_dir / "budget_coherence_report.json",
        {"status": "passed", "external_writes_performed": False},
    )
    _write_ready_labor_employment_qa_matrix(quality_dir / "labor_employment_qa_matrix_report.json")
    _write_ready_labor_employment_fixture_family_pack(
        quality_dir / "labor_employment_fixture_family_pack_report.json"
    )
    _write_ready_labor_employment_executable_fixtures(
        quality_dir / "labor_employment_executable_fixtures_report.json"
    )
    _write_ready_labor_employment_executable_coverage(
        quality_dir / "labor_employment_executable_coverage_report.json"
    )
    _write_ready_labor_employment_executable_fact_binding(
        quality_dir / "labor_employment_executable_fact_binding_report.json"
    )
    _write_ready_labor_employment_executable_driver_binding(
        quality_dir / "labor_employment_executable_driver_binding_report.json"
    )
    _write_ready_labor_employment_executable_driver_impact(
        quality_dir / "labor_employment_executable_driver_impact_report.json"
    )
    _write_ready_labor_employment_budget_fact_gold(
        quality_dir / "labor_employment_budget_fact_gold_report.json"
    )

    report, run_dir, _ = run_synthetic_qa_bundle(
        run_root=run_root,
        out_dir=quality_dir,
        fixture_depth_manifest_path=(
            repo_root / "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"
        ),
        repo_root=repo_root,
        generated_at="2026-07-02T00:00:00Z",
    )

    artifacts = {artifact.artifact_id: artifact for artifact in report.artifacts}
    assert report.status == "blocked"
    assert artifacts["synthetic_fixture_depth"].present is True
    assert artifacts["synthetic_fixture_depth"].status == "pending_review"
    assert artifacts["budget_calibration_readiness"].status == "missing"
    assert (run_dir / "synthetic_fixture_depth_audit_report.json").is_file()


def test_synthetic_qa_bundle_cli_writes_bundle_and_manifest(tmp_path):
    run_root = tmp_path / "demo"
    quality_dir = run_root / "quality"
    quality_dir.mkdir(parents=True)
    for file_name in [
        "budget_coherence_report.json",
        "synthetic_fixture_depth_audit_report.json",
        "budget_calibration_readiness_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_fixture_family_pack_report.json",
        "labor_employment_executable_fixtures_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_executable_fact_binding_report.json",
        "labor_employment_executable_driver_binding_report.json",
        "labor_employment_executable_driver_impact_report.json",
        "labor_employment_budget_fact_gold_report.json",
    ]:
        write_json(
            quality_dir / file_name,
            {
                "status": (
                    "labor_employment_qa_matrix_ready_for_review"
                    if file_name == "labor_employment_qa_matrix_report.json"
                    else "labor_employment_fixture_family_pack_ready_for_review"
                    if file_name == "labor_employment_fixture_family_pack_report.json"
                    else "labor_employment_executable_fixtures_ready_for_review"
                    if file_name == "labor_employment_executable_fixtures_report.json"
                    else "labor_employment_executable_coverage_ready_for_review"
                    if file_name == "labor_employment_executable_coverage_report.json"
                    else "labor_employment_executable_driver_bindings_ready_for_review"
                    if file_name == "labor_employment_executable_driver_binding_report.json"
                    else "labor_employment_executable_driver_impacts_ready_for_review"
                    if file_name == "labor_employment_executable_driver_impact_report.json"
                    else "passed"
                    if file_name != "labor_employment_executable_fact_binding_report.json"
                    else "labor_employment_executable_budget_fact_bindings_ready_for_review"
                ),
                "external_writes_performed": False,
            },
        )

    code = main(
        [
            "build-synthetic-qa-bundle",
            "--run-root",
            str(run_root),
            "--out-dir",
            str(quality_dir),
            "--ui-manifest-out",
            str(run_root / "ui_review_manifest.json"),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )

    report = load_json(quality_dir / SYNTHETIC_QA_BUNDLE_REPORT_FILENAME)
    manifest = load_json(run_root / "ui_review_manifest.json")
    assert code == 0
    assert report["status"] == "pending_review"
    assert manifest["overallStatus"] in {"passed", "blocked"}
    assert any(gate["gateId"] == "synthetic_qa_bundle" for gate in manifest["qualityGates"])
