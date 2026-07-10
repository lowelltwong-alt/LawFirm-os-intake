from pathlib import Path

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_qa_review_run import (
    SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
)
from lawfirm_os_intake.ui_demo_fixture_promotion import DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS
from lawfirm_os_intake.util import load_json, write_json


def test_synthetic_qa_review_run_cli_builds_review_cockpit_inputs(
    tmp_path,
    repo_root,
    capsys,
):
    run_root = tmp_path / "synthetic-qa-review-run"
    quality_dir = run_root / "quality"
    quality_dir.mkdir(parents=True)
    fixture_boundary_report = write_json(
        tmp_path / "rust_fixture_boundary_report.json",
        {
            "schema_version": "0.1",
            "checker": "fixture-boundary-checker",
            "status": "passed",
            "root": str(run_root),
            "ui_bundle_ref": str(run_root / "ui_review_data_bundle.json"),
            "checked_json_file_count": 12,
            "checked_object_count": 120,
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
    fixture_manifest_report = write_json(
        tmp_path / "rust_fixture_manifest_report.json",
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
                    "path": "synthetic_qa_review_run_report.json",
                    "sha256": "sha256:" + "b" * 64,
                    "byte_count": 123,
                    "top_level_type": "object",
                    "schema_version": "0.1",
                    "status": "synthetic_qa_review_run_ready",
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
    validation_suite_evidence_report = (
        repo_root
        / "apps"
        / "legal-intake-budget"
        / "src"
        / "fixtures"
        / "demo-validation-suite-evidence-report.json"
    )
    write_json(
        quality_dir / "labor_employment_qa_matrix_report.json",
        {"status": "failed", "external_writes_performed": False},
    )

    code = main(
        [
            "build-synthetic-qa-review-run",
            "--repo-root",
            str(repo_root),
            "--run-root",
            str(run_root),
            "--fixture-boundary-report",
            str(fixture_boundary_report),
            "--fixture-manifest-report",
            str(fixture_manifest_report),
            "--validation-suite-evidence-report",
            str(validation_suite_evidence_report),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    report = load_json(run_root / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME)
    bundle = load_json(run_root / "quality" / "synthetic_qa_bundle_report.json")
    staged_matrix = load_json(run_root / "quality" / "labor_employment_qa_matrix_report.json")
    ui_manifest = load_json(run_root / "ui_review_manifest.json")
    ui_data_bundle = load_json(run_root / "ui_review_data_bundle.json")
    poc_qa_triage = load_json(run_root / "quality" / "poc_qa_triage_report.json")
    validation_evidence = load_json(run_root / "quality" / "validation_suite_evidence_report.json")
    steps = {step["step_id"]: step for step in report["steps"]}

    assert code == 0
    assert report["status"] == "synthetic_qa_review_run_ready"
    assert report["step_count"] == len(report["steps"]) == 32
    assert report["failed_step_count"] == 0
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["local_json_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["silent_learning_performed"] is False
    assert {
        "budget_coherence",
        "matter_linking_preflight",
        "matter_linking_review_outcome",
        "matter_linking_weak_only_holdout",
        "matter_linking_qa_gate",
        "budget_calibration_starter_pack",
        "labor_employment_qa_matrix",
        "labor_employment_fixture_family_pack",
        "labor_employment_executable_fixtures",
        "labor_employment_executable_coverage",
        "labor_employment_executable_fact_binding",
        "labor_employment_executable_driver_binding",
        "labor_employment_executable_driver_impact",
        "labor_employment_driver_impact_review",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
        "labor_employment_budget_learning_fixtures",
        "labor_employment_budget_outcome_replay_readiness",
        "labor_employment_budget_outcome_replay_execution",
        "labor_employment_budget_outcome_replay_builder_binding",
        "labor_employment_budget_outcome_replay_confidence_status",
        "labor_employment_budget_fact_gold",
        "budget_learning_loop",
        "public_derived_synthetic_qa_gate",
        "synthetic_qa_bundle",
        "ui_review_manifest",
        "ui_review_data_bundle",
        "rust_fixture_boundary",
        "rust_fixture_manifest",
        "validation_suite_evidence",
        "synthetic_confidence_summary",
    } == set(steps)
    assert all(step["status"] == "passed" for step in report["steps"])
    assert all(Path(step["artifact_ref"]).is_file() for step in report["steps"])
    assert all(
        (run_root / spec.source_ref).is_file() for spec in DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS
    )

    assert bundle["status"] == "pending_review"
    assert bundle["missing_required_artifact_count"] == 0
    assert bundle["blocked_artifact_count"] == 0
    assert bundle["ui_manifest_ref"] == str(run_root / "ui_review_manifest.json")
    assert bundle["ui_data_bundle_ref"] == str(run_root / "ui_review_data_bundle.json")
    assert staged_matrix["status"] == "labor_employment_qa_matrix_ready_for_review"
    assert ui_manifest["boundaryFlags"]["readOnly"] is True
    assert ui_manifest["boundaryFlags"]["networkCallsAllowed"] is False
    assert {
        "synthetic_qa_review_run",
        "synthetic_confidence_summary",
        "synthetic_qa_blocker_report",
        "poc_qa_triage",
        "synthetic_qa_bundle",
        "validation_suite_evidence",
        "full_pytest",
        "smoke_demo",
        "matter_linking_preflight",
        "matter_linking_review_outcome",
        "matter_linking_qa_gate",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
        "labor_employment_budget_learning_fixtures",
        "labor_employment_budget_outcome_replay_readiness",
        "labor_employment_budget_outcome_replay_execution",
        "labor_employment_budget_outcome_replay_builder_binding",
        "labor_employment_budget_outcome_replay_confidence_status",
        "public_derived_synthetic_qa_gate",
    } <= {gate["gateId"] for gate in ui_manifest["qualityGates"]}
    assert ui_data_bundle["status"] == "ready_for_review"
    assert poc_qa_triage["status"] == "poc_qa_ready_for_review"
    assert poc_qa_triage["source_validation_suite_evidence_report_id"].startswith(
        "validation_suite_evidence_"
    )
    assert validation_evidence["status"] == "validation_suite_passed"
    ui_detail_reports = {
        report["report_kind"]: report for report in ui_data_bundle["detail_reports"]
    }
    assert ui_data_bundle["detail_report_count"] == 27
    assert ui_data_bundle["present_detail_report_count"] == 22
    assert ui_detail_reports["ui_demo_qa_recipe"]["present"] is False
    assert ui_detail_reports["ui_demo_qa_recipe"]["required"] is False
    assert ui_detail_reports["synthetic_qa_review_run"]["present"] is True
    assert ui_detail_reports["synthetic_qa_review_run"]["artifact_ref"] == str(
        run_root / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME
    )
    assert ui_detail_reports["rust_fixture_boundary"]["present"] is True
    assert ui_detail_reports["rust_fixture_boundary"]["required"] is False
    assert ui_detail_reports["rust_fixture_boundary"]["status"] == "passed"
    assert ui_detail_reports["rust_fixture_boundary"]["renderer"] == "RustFixtureBoundaryPanel"
    assert ui_detail_reports["rust_fixture_manifest"]["present"] is True
    assert ui_detail_reports["rust_fixture_manifest"]["required"] is False
    assert ui_detail_reports["rust_fixture_manifest"]["status"] == "passed"
    assert ui_detail_reports["rust_fixture_manifest"]["renderer"] == "RustFixtureManifestPanel"
    assert ui_detail_reports["matter_linking_preflight"]["present"] is True
    assert ui_detail_reports["matter_linking_review_outcome"]["present"] is True
    assert ui_detail_reports["matter_linking_qa_gate"]["present"] is True
    assert ui_detail_reports["labor_employment_executable_coverage"]["present"] is True
    assert ui_detail_reports["labor_employment_budget_qa_gate"]["present"] is True
    assert ui_detail_reports["labor_employment_budget_learning_fixtures"]["present"] is True
    assert ui_detail_reports["labor_employment_budget_learning_fixtures"]["required"] is True
    assert ui_detail_reports["labor_employment_budget_learning_fixtures"]["status"] == (
        "labor_employment_budget_learning_fixtures_ready_for_review"
    )
    assert ui_detail_reports["labor_employment_budget_outcome_replay_readiness"]["present"] is True
    assert ui_detail_reports["labor_employment_budget_outcome_replay_readiness"]["required"] is True
    assert ui_detail_reports["labor_employment_budget_outcome_replay_readiness"]["status"] == (
        "labor_employment_budget_outcome_replay_ready_for_review"
    )
    assert ui_detail_reports["labor_employment_budget_outcome_replay_execution"]["present"] is True
    assert ui_detail_reports["labor_employment_budget_outcome_replay_execution"]["required"] is True
    assert ui_detail_reports["labor_employment_budget_outcome_replay_execution"]["status"] == (
        "labor_employment_budget_outcome_replay_execution_ready_for_review"
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_builder_binding"]["present"]
        is True
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_builder_binding"]["required"]
        is True
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_builder_binding"]["status"]
        == "labor_employment_budget_replay_builder_binding_ready_for_review"
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_confidence_status"]["present"]
        is True
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_confidence_status"]["required"]
        is True
    )
    assert (
        ui_detail_reports["labor_employment_budget_outcome_replay_confidence_status"]["status"]
        == "labor_employment_budget_outcome_replay_confidence_pending_inputs"
    )
    assert ui_detail_reports["budget_learning_loop"]["present"] is True
    assert ui_detail_reports["budget_learning_loop"]["required"] is True
    assert ui_detail_reports["budget_learning_loop"]["status"] == (
        "blocked_by_budget_learning_loop"
    )
    assert steps["budget_learning_loop"]["observed_status"] == ("blocked_by_budget_learning_loop")
    quality_gates = {gate["gateId"]: gate for gate in ui_manifest["qualityGates"]}
    assert quality_gates["budget_learning_loop"]["status"] == "pending_review"
    assert ui_detail_reports["public_derived_synthetic_qa_gate"]["present"] is True
    assert ui_detail_reports["public_derived_synthetic_qa_gate"]["required"] is False
    assert ui_detail_reports["public_derived_synthetic_qa_gate"]["status"] == (
        "public_derived_synthetic_qa_ready_for_review"
    )
    assert ui_detail_reports["synthetic_confidence_summary"]["present"] is True
    assert ui_detail_reports["synthetic_qa_blocker_report"]["present"] is True
    assert ui_detail_reports["synthetic_qa_review_outcome"]["present"] is True
    assert ui_detail_reports["synthetic_qa_review_outcome"]["required"] is False
    assert ui_detail_reports["synthetic_qa_blocker_report"]["status"] == (
        "synthetic_qa_blocker_report_ready_for_review"
    )
    assert ui_detail_reports["synthetic_confidence_summary"]["status"] == (
        "synthetic_confidence_summary_ready_for_review"
    )
    assert ui_detail_reports["matter_linking_preflight"]["status"] == (
        "matter_linking_preflight_resolved_candidate_requires_review"
    )
    assert ui_data_bundle["external_writes_performed"] is False
    assert ui_data_bundle["lake_write_performed"] is False
    assert ui_data_bundle["sqlite_write_performed"] is False
    assert not list(run_root.rglob("*.sqlite"))
    assert not list(run_root.rglob("*.db"))
    assert '"external_writes_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
