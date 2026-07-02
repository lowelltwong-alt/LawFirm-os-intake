from lawfirm_os_intake.budget_calibration_starter_pack import (
    BUDGET_CALIBRATION_STARTER_PACK_REPORT_FILENAME,
    run_budget_calibration_starter_pack,
)
from lawfirm_os_intake.cli import main
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
    assert ui_manifest["overallStatus"] == "blocked"
