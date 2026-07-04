from pathlib import Path

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_qa_review_run import (
    SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
)
from lawfirm_os_intake.util import load_json, write_json


def test_synthetic_qa_review_run_cli_builds_review_cockpit_inputs(
    tmp_path,
    repo_root,
    capsys,
):
    run_root = tmp_path / "synthetic-qa-review-run"
    quality_dir = run_root / "quality"
    quality_dir.mkdir(parents=True)
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
    steps = {step["step_id"]: step for step in report["steps"]}

    assert code == 0
    assert report["status"] == "synthetic_qa_review_run_ready"
    assert report["step_count"] == len(report["steps"]) == 21
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
        "labor_employment_budget_fact_gold",
        "synthetic_qa_bundle",
        "ui_review_manifest",
        "ui_review_data_bundle",
        "synthetic_confidence_summary",
    } == set(steps)
    assert all(step["status"] == "passed" for step in report["steps"])
    assert all(Path(step["artifact_ref"]).is_file() for step in report["steps"])

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
        "synthetic_qa_bundle",
        "matter_linking_preflight",
        "matter_linking_review_outcome",
        "matter_linking_qa_gate",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
    } <= {gate["gateId"] for gate in ui_manifest["qualityGates"]}
    assert ui_data_bundle["status"] == "ready_for_review"
    ui_detail_reports = {
        report["report_kind"]: report for report in ui_data_bundle["detail_reports"]
    }
    assert ui_data_bundle["detail_report_count"] == 12
    assert ui_data_bundle["present_detail_report_count"] == 12
    assert ui_detail_reports["synthetic_qa_review_run"]["present"] is True
    assert ui_detail_reports["synthetic_qa_review_run"]["artifact_ref"] == str(
        run_root / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME
    )
    assert ui_detail_reports["matter_linking_preflight"]["present"] is True
    assert ui_detail_reports["matter_linking_review_outcome"]["present"] is True
    assert ui_detail_reports["matter_linking_qa_gate"]["present"] is True
    assert ui_detail_reports["labor_employment_executable_coverage"]["present"] is True
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
