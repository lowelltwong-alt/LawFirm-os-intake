from lawfirm_os_intake.budget_calibration_starter_pack import (
    BUDGET_CALIBRATION_STARTER_PACK_REPORT_FILENAME,
    run_budget_calibration_starter_pack,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_driver_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_driver_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_driver_impact import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME,
    run_labor_employment_executable_driver_impact_audit,
)
from lawfirm_os_intake.labor_employment_driver_impact_review import (
    LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_driver_impact_review,
)
from lawfirm_os_intake.labor_employment_blocked_driver_impact_review import (
    LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_blocked_driver_impact_review,
)
from lawfirm_os_intake.labor_employment_budget_output_expectations import (
    LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
    run_labor_employment_budget_output_expectations_audit,
)
from lawfirm_os_intake.labor_employment_budget_qa_gate import (
    run_labor_employment_budget_qa_gate,
)
from lawfirm_os_intake.labor_employment_budget_fact_gold import (
    run_labor_employment_budget_fact_gold_validation,
)
from lawfirm_os_intake.labor_employment_executable_coverage import (
    LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
    run_labor_employment_executable_coverage_audit,
)
from lawfirm_os_intake.labor_employment_fixture_family_pack import (
    run_labor_employment_fixture_family_pack_audit,
)
from lawfirm_os_intake.labor_employment_qa_matrix import run_labor_employment_qa_matrix
from lawfirm_os_intake.matter_linking_qa_gate import run_matter_linking_qa_gate
from lawfirm_os_intake.models import BudgetCalibrationStarterPackReport
from lawfirm_os_intake.synthetic_qa_bundle import run_synthetic_qa_bundle
from lawfirm_os_intake.util import load_json, write_json


def test_budget_calibration_starter_pack_builds_ready_candidate_chain(tmp_path, repo_root):
    report, run_dir = run_budget_calibration_starter_pack(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=tmp_path / "starter-pack",
        reviewed_at="2026-07-02T00:00:00Z",
    )
    persisted = BudgetCalibrationStarterPackReport.model_validate(
        load_json(run_dir / BUDGET_CALIBRATION_STARTER_PACK_REPORT_FILENAME)
    )
    readiness = load_json(
        run_dir / "budget-calibration-readiness" / "budget_calibration_readiness_report.json"
    )
    outcome_input = load_json(run_dir / "synthetic-replay-review-outcome-input.json")

    assert persisted.starter_pack_report_id == report.starter_pack_report_id
    assert report.status == "starter_pack_ready_for_manual_fixture_update_review"
    assert report.budget_calibration_readiness_status == "ready_for_manual_fixture_update_review"
    assert report.selected_artifact_kind == "budget_review_fixture"
    assert report.failed_step_count == 0
    assert all(step.status == "passed" for step in report.steps)
    assert readiness["status"] == "ready_for_manual_fixture_update_review"
    assert outcome_input["reviewer_id"] == "synthetic-qa-starter-reviewer"
    assert "not production human approval" in outcome_input["decision_reason"]
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.calibration_applied is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_budget_calibration_starter_pack_cli_writes_report(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "build-budget-calibration-starter-pack",
            "--corpus-root",
            str(repo_root / "examples/synthetic"),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "starter-pack-cli"),
            "--reviewed-at",
            "2026-07-02T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path / "starter-pack-cli" / "budget_calibration_starter_pack_report.json"
    )

    assert exit_code == 0
    assert report["status"] == "starter_pack_ready_for_manual_fixture_update_review"
    assert report["budget_calibration_readiness_status"] == (
        "ready_for_manual_fixture_update_review"
    )
    assert '"calibration_applied": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out


def test_starter_pack_allows_synthetic_qa_bundle_to_reach_pending_review(
    tmp_path,
    repo_root,
):
    run_root = tmp_path / "demo"
    budget_dir = run_root / "budget"
    budget_dir.mkdir(parents=True)
    write_json(
        budget_dir / "budget_coherence_report.json",
        {"status": "passed", "external_writes_performed": False},
    )
    run_budget_calibration_starter_pack(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=run_root / "quality" / "calibration-starter",
        reviewed_at="2026-07-02T00:00:00Z",
    )
    run_labor_employment_qa_matrix(
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-qa-matrix",
    )
    run_labor_employment_fixture_family_pack_audit(
        pack_path=(
            repo_root
            / "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
        ),
        fact_needs_path=repo_root / "config/labor-employment-budget-fact-needs.yaml",
        out_dir=run_root / "quality" / "le-fixture-family-pack",
    )
    _, executable_fixture_run_dir = run_labor_employment_executable_fixture_audit(
        manifest_path=(
            repo_root
            / "examples/synthetic/labor-employment/"
            / "labor-employment-executable-fixtures-manifest.json"
        ),
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-executable-fixtures",
    )
    run_labor_employment_executable_coverage_audit(
        manifest_path=(
            repo_root
            / "examples/synthetic/labor-employment/"
            / "labor-employment-executable-fixtures-manifest.json"
        ),
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-executable-coverage",
    )
    _, executable_fact_binding_run_dir = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=(
            repo_root
            / "examples/synthetic/labor-employment/"
            / "labor-employment-executable-budget-fact-bindings.json"
        ),
        executable_fixture_report_path=(
            executable_fixture_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-executable-fact-binding",
    )
    _, executable_driver_binding_run_dir = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=(
            executable_fixture_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        executable_fact_binding_report_path=(
            executable_fact_binding_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-executable-driver-binding",
    )
    _, executable_driver_impact_run_dir = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=(
            executable_driver_binding_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        out_dir=run_root / "quality" / "le-executable-driver-impact",
    )
    _, driver_impact_review_run_dir = run_labor_employment_driver_impact_review(
        review_spec_path=(
            repo_root / "examples/synthetic/gold/labor-employment-driver-impact-review.json"
        ),
        driver_impact_report_path=(
            executable_driver_impact_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        out_dir=run_root / "quality" / "le-driver-impact-review",
    )
    _, blocked_driver_impact_review_run_dir = run_labor_employment_blocked_driver_impact_review(
        fact_binding_report_path=(
            executable_fact_binding_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        driver_binding_report_path=(
            executable_driver_binding_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        driver_impact_report_path=(
            executable_driver_impact_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        out_dir=run_root / "quality" / "le-blocked-driver-impact-review",
    )
    _, output_expectations_run_dir = run_labor_employment_budget_output_expectations_audit(
        driver_impact_report_path=(
            executable_driver_impact_run_dir
            / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        driver_impact_review_report_path=(
            driver_impact_review_run_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        blocked_driver_impact_review_report_path=(
            blocked_driver_impact_review_run_dir
            / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        out_dir=run_root / "quality" / "le-budget-output-expectations",
    )
    run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=(
            output_expectations_run_dir / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME
        ),
        blocked_driver_impact_review_report_path=(
            blocked_driver_impact_review_run_dir
            / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        executable_coverage_report_path=(
            run_root
            / "quality"
            / "le-executable-coverage"
            / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME
        ),
        out_dir=run_root / "quality" / "le-budget-qa-gate",
        generated_at="2026-07-02T00:00:00Z",
    )
    run_labor_employment_budget_fact_gold_validation(
        gold_path=repo_root / "examples/synthetic/gold/labor-employment-budget-fact-gold.json",
        repo_root=repo_root,
        out_dir=run_root / "quality" / "le-budget-fact-gold",
    )
    write_json(
        run_root / "quality" / "labor_employment_budget_learning_fixtures_report.json",
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
    write_json(
        run_root / "quality" / "labor_employment_budget_outcome_replay_readiness_report.json",
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
    write_json(
        run_root / "quality" / "labor_employment_budget_outcome_replay_execution_report.json",
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
    write_json(
        run_root / "quality" / "labor_employment_budget_outcome_replay_builder_binding_report.json",
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
    write_json(
        run_root / "quality" / "budget_learning_loop_report.json",
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
    run_matter_linking_qa_gate(
        repo_root=repo_root,
        out_dir=run_root / "quality" / "matter-linking-qa-gate",
        generated_at="2026-07-02T00:00:00Z",
    )

    bundle, _, ui_manifest = run_synthetic_qa_bundle(
        run_root=run_root,
        out_dir=run_root / "quality",
        fixture_depth_manifest_path=(
            repo_root / "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"
        ),
        repo_root=repo_root,
        ui_manifest_out=run_root / "ui_review_manifest.json",
        generated_at="2026-07-02T00:00:00Z",
    )
    gates = {gate["gateId"]: gate for gate in ui_manifest["qualityGates"]}

    assert bundle.status == "pending_review"
    assert bundle.missing_required_artifact_count == 0
    assert bundle.blocked_artifact_count == 0
    assert gates["synthetic_qa_bundle"]["status"] == "pending_review"
    assert gates["budget_calibration_readiness"]["status"] == "pending_review"
    assert gates["labor_employment_qa_matrix"]["status"] == "pending_review"
    assert gates["labor_employment_fixture_family_pack"]["status"] == "pending_review"
    assert gates["labor_employment_executable_fixtures"]["status"] == "pending_review"
    assert gates["labor_employment_executable_coverage"]["status"] == "pending_review"
    assert gates["labor_employment_executable_fact_binding"]["status"] == "pending_review"
    assert gates["labor_employment_executable_driver_binding"]["status"] == "pending_review"
    assert gates["labor_employment_executable_driver_impact"]["status"] == "pending_review"
    assert gates["labor_employment_driver_impact_review"]["status"] == "pending_review"
    assert gates["labor_employment_blocked_driver_impact_review"]["status"] == "pending_review"
    assert gates["labor_employment_budget_output_expectations"]["status"] == "pending_review"
    assert gates["labor_employment_budget_qa_gate"]["status"] == "pending_review"
    assert gates["labor_employment_budget_learning_fixtures"]["status"] == "pending_review"
    assert gates["labor_employment_budget_outcome_replay_readiness"]["status"] == "pending_review"
    assert gates["labor_employment_budget_outcome_replay_execution"]["status"] == "pending_review"
    assert (
        gates["labor_employment_budget_outcome_replay_builder_binding"]["status"]
        == "pending_review"
    )
    assert gates["labor_employment_budget_fact_gold"]["status"] == "passed"
    assert gates["budget_learning_loop"]["status"] == "pending_review"
    assert ui_manifest["overallStatus"] == "blocked"
