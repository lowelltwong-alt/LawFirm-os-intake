from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_execution import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_execution,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_readiness import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_readiness_audit,
)
from lawfirm_os_intake.models import LaborEmploymentBudgetOutcomeReplayExecutionReport
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"
LEARNING_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json"
)
OUTCOME_SEED_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-seeds.json"
)


def _qa_gate(repo_root):
    return repo_root / FIXTURE_ROOT / "demo-labor-employment-budget-qa-gate-report.json"


def _learning_manifest(repo_root):
    return repo_root / LEARNING_MANIFEST_REF


def _seed_manifest(repo_root):
    return repo_root / OUTCOME_SEED_MANIFEST_REF


def _learning_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=_learning_manifest(repo_root),
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "le-budget-learning-fixtures",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME


def _readiness_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=_seed_manifest(repo_root),
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-readiness",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME


def test_labor_employment_budget_outcome_replay_execution_materializes_slots(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=_seed_manifest(repo_root),
        readiness_report_path=_readiness_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-execution",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayExecutionReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME)
    )
    slot_paths = [
        slot.artifact_slot_ref
        for case in report.cases
        for slot in case.artifact_slots
        if slot.artifact_slot_status == "materialized_candidate_slot"
    ]

    assert persisted.outcome_replay_execution_report_id == (
        report.outcome_replay_execution_report_id
    )
    assert report.status == "labor_employment_budget_outcome_replay_execution_ready_for_review"
    assert report.fixture_count == 8
    assert report.materialized_case_count == 8
    assert report.failed_case_count == 0
    assert report.expected_artifact_slot_count == 36
    assert report.materialized_artifact_slot_count == 36
    assert report.runtime_artifact_count == 0
    assert set(report.covered_learning_loop_types) == {
        "actuals_variance",
        "carrier_rejection_capture",
        "appeal_outcome",
        "reviewed_learning_gate",
        "blocked_budget_guard",
    }
    assert report.missing_learning_loop_types == []
    assert all(case.status == "passed" for case in report.cases)
    assert all(check.status == "passed" for check in report.checks)
    assert len(slot_paths) == 36
    assert all(path.endswith(".slot.json") for path in slot_paths)
    assert all(load_json(path)["runtime_artifact_created"] is False for path in slot_paths)
    assert "labor_employment_budget_outcome_replay_execution_candidate" in (
        report.candidate_exception_lake_labels
    )
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_outcome_replay_execution_report.md").read_text(
        encoding="utf-8"
    )
    assert "materializes slot manifests" in notes
    assert "does not create billing, carrier" in notes


def test_labor_employment_budget_outcome_replay_execution_blocks_unready_readiness_report(
    repo_root,
    tmp_path,
):
    manifest = load_json(_seed_manifest(repo_root))
    manifest["seeds"][0]["replay_seed_refs_by_loop"]["actuals_variance"].append(
        "examples/synthetic/labor-employment/missing-outcome-seed.json"
    )
    manifest_path = write_json(tmp_path / "missing-ref-outcome-seed.json", manifest)
    _, readiness_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=manifest_path,
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "blocked-readiness",
        generated_at="2026-07-04T00:00:00Z",
    )
    blocked_readiness = (
        readiness_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME
    )

    report, _ = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=_seed_manifest(repo_root),
        readiness_report_path=blocked_readiness,
        out_dir=tmp_path / "blocked-execution",
        generated_at="2026-07-04T00:00:00Z",
    )
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_outcome_replay_execution"
    assert report.materialized_artifact_slot_count == 0
    assert report.runtime_artifact_count == 0
    assert "readiness_report_ready" in failed_checks
    assert all(case.status == "failed" for case in report.cases)
    assert all("source_readiness_report_not_ready" in case.failure_ids for case in report.cases)
    assert report.lake_write_performed is False
    assert report.silent_learning_performed is False


def test_labor_employment_budget_outcome_replay_execution_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "execute-labor-employment-budget-outcome-replay",
            "--seed-manifest",
            str(_seed_manifest(repo_root)),
            "--readiness-report",
            str(_readiness_report(repo_root, tmp_path)),
            "--out-dir",
            str(tmp_path / "le-budget-outcome-replay-execution-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        '"status": "labor_employment_budget_outcome_replay_execution_ready_for_review"'
        in captured.out
    )
    assert '"fixture_count": 8' in captured.out
    assert '"expected_artifact_slot_count": 36' in captured.out
    assert '"runtime_artifact_count": 0' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path
        / "le-budget-outcome-replay-execution-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME
    ).is_file()
