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


def _write_ready_labor_employment_driver_impact_review(path):
    write_json(
        path,
        {
            "status": "labor_employment_driver_impact_review_ready_for_budget_gate_replay",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_blocked_driver_impact_review(path):
    write_json(
        path,
        {
            "status": "labor_employment_blocked_driver_impacts_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_budget_output_expectations(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_output_expectations_ready_for_review",
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_budget_qa_gate(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_qa_gate_ready_for_review",
            "case_count": 14,
            "blocked_amount_budget_case_count": 6,
            "range_or_hours_only_case_count": 3,
            "candidate_range_after_review_case_count": 5,
            "reviewed_nonblocking_case_count": 8,
            "covered_required_family_count": 8,
            "required_family_count": 8,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_labor_employment_budget_learning_fixtures(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_learning_fixtures_ready_for_review",
            "fixture_count": 8,
            "covered_required_family_count": 8,
            "required_family_count": 8,
            "missing_required_families": [],
            "missing_budget_output_states": [],
            "missing_learning_loop_types": [],
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


def _write_ready_labor_employment_budget_outcome_replay_readiness(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_outcome_replay_ready_for_review",
            "fixture_count": 8,
            "seed_spec_count": 8,
            "loop_requirement_count": 19,
            "seeded_loop_requirement_count": 19,
            "missing_loop_requirement_count": 0,
            "unresolved_source_ref_count": 0,
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


def _write_ready_labor_employment_budget_outcome_replay_execution(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_outcome_replay_execution_ready_for_review",
            "fixture_count": 8,
            "materialized_case_count": 8,
            "failed_case_count": 0,
            "expected_artifact_slot_count": 38,
            "materialized_artifact_slot_count": 38,
            "runtime_artifact_count": 0,
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


def _write_ready_labor_employment_budget_outcome_replay_builder_binding(path):
    write_json(
        path,
        {
            "status": "labor_employment_budget_replay_builder_binding_ready_for_review",
            "fixture_count": 8,
            "case_count": 8,
            "slot_count": 38,
            "bound_slot_count": 38,
            "unknown_artifact_count": 0,
            "blocked_slot_count": 0,
            "replay_input_gap_count": 8,
            "missing_case_prerequisite_count": 8,
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


def _write_ready_labor_employment_budget_outcome_replay_confidence_status(path):
    write_json(
        path,
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


def _write_ready_budget_learning_loop(path):
    write_json(
        path,
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


def _write_ready_matter_linking_qa_gate(path):
    write_json(
        path,
        {
            "status": "matter_linking_qa_gate_ready_for_review",
            "case_count": 5,
            "failed_case_count": 0,
            "missing_required_coverage_tags": [],
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )


def _write_ready_public_derived_synthetic_qa_gate(path):
    write_json(
        path,
        {
            "status": "public_derived_synthetic_qa_ready_for_review",
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "fixture_generation_authorized": False,
            "fixture_files_mutated": False,
            "github_pr_created": False,
            "public_records_ingested": False,
            "raw_public_payload_committed": False,
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
    _write_ready_labor_employment_driver_impact_review(
        quality_dir / "labor_employment_driver_impact_review_report.json"
    )
    _write_ready_labor_employment_blocked_driver_impact_review(
        quality_dir / "labor_employment_blocked_driver_impact_review_report.json"
    )
    _write_ready_labor_employment_budget_output_expectations(
        quality_dir / "labor_employment_budget_output_expectations_report.json"
    )
    _write_ready_labor_employment_budget_qa_gate(
        quality_dir / "labor_employment_budget_qa_gate_report.json"
    )
    _write_ready_labor_employment_budget_learning_fixtures(
        quality_dir / "labor_employment_budget_learning_fixtures_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_readiness(
        quality_dir / "labor_employment_budget_outcome_replay_readiness_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_execution(
        quality_dir / "labor_employment_budget_outcome_replay_execution_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_builder_binding(
        quality_dir / "labor_employment_budget_outcome_replay_builder_binding_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_confidence_status(
        quality_dir / "labor_employment_budget_outcome_replay_confidence_status_report.json"
    )
    _write_ready_labor_employment_budget_fact_gold(
        quality_dir / "labor_employment_budget_fact_gold_report.json"
    )
    _write_ready_budget_learning_loop(quality_dir / "budget_learning_loop_report.json")
    _write_ready_matter_linking_qa_gate(quality_dir / "matter_linking_qa_gate_report.json")
    _write_ready_public_derived_synthetic_qa_gate(
        quality_dir / "public_derived_synthetic_qa_gate_report.json"
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
    artifacts = {item["artifact_id"]: item for item in persisted["artifacts"]}
    ui_data_bundle = load_json(run_root / "ui_review_data_bundle.json")
    gates = {gate["gateId"]: gate for gate in ui_manifest["qualityGates"]}
    assert report.status == "blocked"
    assert persisted["missing_required_artifact_count"] == 1
    assert artifacts["budget_learning_loop"]["present"] is True
    assert artifacts["budget_learning_loop"]["status"] == "pending_review"
    assert artifacts["public_derived_synthetic_qa_gate"]["present"] is True
    assert artifacts["public_derived_synthetic_qa_gate"]["status"] == "pending_review"
    assert artifacts["labor_employment_budget_learning_fixtures"]["present"] is True
    assert artifacts["labor_employment_budget_learning_fixtures"]["status"] == "pending_review"
    assert artifacts["labor_employment_budget_outcome_replay_readiness"]["present"] is True
    assert artifacts["labor_employment_budget_outcome_replay_readiness"]["status"] == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_execution"]["present"] is True
    assert artifacts["labor_employment_budget_outcome_replay_execution"]["status"] == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_builder_binding"]["present"] is True
    assert artifacts["labor_employment_budget_outcome_replay_builder_binding"]["status"] == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_confidence_status"]["present"] is True
    assert artifacts["labor_employment_budget_outcome_replay_confidence_status"]["status"] == (
        "pending_review"
    )
    assert persisted["ui_manifest_ref"] == str(run_root / "ui_review_manifest.json")
    assert persisted["ui_data_bundle_ref"] == str(run_root / "ui_review_data_bundle.json")
    assert persisted["lake_write_performed"] is False
    assert persisted["sqlite_write_performed"] is False
    assert persisted["budget_submission_performed"] is False
    assert (run_dir / "synthetic_fixture_depth_audit_report.json").is_file()
    assert ui_data_bundle["status"] == "blocked_missing_required_reports"
    assert ui_data_bundle["local_json_only"] is True
    assert ui_data_bundle["external_writes_performed"] is False
    assert ui_data_bundle["lake_write_performed"] is False
    assert ui_data_bundle["sqlite_write_performed"] is False
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
    _write_ready_labor_employment_driver_impact_review(
        quality_dir / "labor_employment_driver_impact_review_report.json"
    )
    _write_ready_labor_employment_blocked_driver_impact_review(
        quality_dir / "labor_employment_blocked_driver_impact_review_report.json"
    )
    _write_ready_labor_employment_budget_output_expectations(
        quality_dir / "labor_employment_budget_output_expectations_report.json"
    )
    _write_ready_labor_employment_budget_qa_gate(
        quality_dir / "labor_employment_budget_qa_gate_report.json"
    )
    _write_ready_labor_employment_budget_learning_fixtures(
        quality_dir / "labor_employment_budget_learning_fixtures_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_readiness(
        quality_dir / "labor_employment_budget_outcome_replay_readiness_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_execution(
        quality_dir / "labor_employment_budget_outcome_replay_execution_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_builder_binding(
        quality_dir / "labor_employment_budget_outcome_replay_builder_binding_report.json"
    )
    _write_ready_labor_employment_budget_outcome_replay_confidence_status(
        quality_dir / "labor_employment_budget_outcome_replay_confidence_status_report.json"
    )
    _write_ready_labor_employment_budget_fact_gold(
        quality_dir / "labor_employment_budget_fact_gold_report.json"
    )
    _write_ready_budget_learning_loop(quality_dir / "budget_learning_loop_report.json")
    _write_ready_matter_linking_qa_gate(quality_dir / "matter_linking_qa_gate_report.json")
    _write_ready_public_derived_synthetic_qa_gate(
        quality_dir / "public_derived_synthetic_qa_gate_report.json"
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
    assert artifacts["labor_employment_budget_learning_fixtures"].status == "pending_review"
    assert artifacts["labor_employment_budget_outcome_replay_readiness"].status == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_execution"].status == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_builder_binding"].status == (
        "pending_review"
    )
    assert artifacts["labor_employment_budget_outcome_replay_confidence_status"].status == (
        "pending_review"
    )
    assert artifacts["budget_learning_loop"].status == "pending_review"
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
        "labor_employment_driver_impact_review_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_budget_qa_gate_report.json",
        "labor_employment_budget_learning_fixtures_report.json",
        "labor_employment_budget_outcome_replay_readiness_report.json",
        "labor_employment_budget_outcome_replay_execution_report.json",
        "labor_employment_budget_outcome_replay_builder_binding_report.json",
        "labor_employment_budget_outcome_replay_confidence_status_report.json",
        "labor_employment_budget_fact_gold_report.json",
        "budget_learning_loop_report.json",
        "matter_linking_qa_gate_report.json",
        "public_derived_synthetic_qa_gate_report.json",
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
                    else "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
                    if file_name == "labor_employment_driver_impact_review_report.json"
                    else "labor_employment_blocked_driver_impacts_ready_for_review"
                    if file_name == "labor_employment_blocked_driver_impact_review_report.json"
                    else "labor_employment_budget_output_expectations_ready_for_review"
                    if file_name == "labor_employment_budget_output_expectations_report.json"
                    else "labor_employment_budget_qa_gate_ready_for_review"
                    if file_name == "labor_employment_budget_qa_gate_report.json"
                    else "labor_employment_budget_learning_fixtures_ready_for_review"
                    if file_name == "labor_employment_budget_learning_fixtures_report.json"
                    else "labor_employment_budget_outcome_replay_ready_for_review"
                    if file_name == "labor_employment_budget_outcome_replay_readiness_report.json"
                    else "labor_employment_budget_outcome_replay_execution_ready_for_review"
                    if file_name == "labor_employment_budget_outcome_replay_execution_report.json"
                    else "labor_employment_budget_replay_builder_binding_ready_for_review"
                    if (
                        file_name
                        == "labor_employment_budget_outcome_replay_builder_binding_report.json"
                    )
                    else "labor_employment_budget_outcome_replay_confidence_pending_inputs"
                    if (
                        file_name
                        == "labor_employment_budget_outcome_replay_confidence_status_report.json"
                    )
                    else "budget_learning_loop_ready_for_review"
                    if file_name == "budget_learning_loop_report.json"
                    else "matter_linking_qa_gate_ready_for_review"
                    if file_name == "matter_linking_qa_gate_report.json"
                    else "public_derived_synthetic_qa_ready_for_review"
                    if file_name == "public_derived_synthetic_qa_gate_report.json"
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
    ui_data_bundle = load_json(run_root / "ui_review_data_bundle.json")
    assert code == 0
    assert report["status"] == "pending_review"
    artifact_ids = {artifact["artifact_id"] for artifact in report["artifacts"]}
    assert "labor_employment_budget_learning_fixtures" in artifact_ids
    assert "labor_employment_budget_outcome_replay_readiness" in artifact_ids
    assert "labor_employment_budget_outcome_replay_execution" in artifact_ids
    assert "labor_employment_budget_outcome_replay_builder_binding" in artifact_ids
    assert "labor_employment_budget_outcome_replay_confidence_status" in artifact_ids
    assert "budget_learning_loop" in artifact_ids
    assert "public_derived_synthetic_qa_gate" in artifact_ids
    assert report["ui_data_bundle_ref"] == str(run_root / "ui_review_data_bundle.json")
    assert manifest["overallStatus"] in {"passed", "blocked"}
    assert ui_data_bundle["status"] == "blocked_missing_required_reports"
    assert ui_data_bundle["external_writes_performed"] is False
    assert any(gate["gateId"] == "synthetic_qa_bundle" for gate in manifest["qualityGates"])
