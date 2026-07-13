from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_readiness import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_readiness_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentBudgetOutcomeReplayReadinessReport,
    LaborEmploymentBudgetOutcomeReplaySeedManifest,
)
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


def test_labor_employment_budget_outcome_replay_readiness_covers_seeded_loops(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=_seed_manifest(repo_root),
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-readiness",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayReadinessReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME)
    )

    assert persisted.outcome_replay_readiness_report_id == (
        report.outcome_replay_readiness_report_id
    )
    assert report.status == "labor_employment_budget_outcome_replay_ready_for_review"
    assert report.fixture_count == 8
    assert report.seed_spec_count == 8
    assert report.loop_requirement_count == 20
    assert report.seeded_loop_requirement_count == 20
    assert report.missing_loop_requirement_count == 0
    assert report.unresolved_source_ref_count == 0
    assert report.expected_replay_artifact_count == 9
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
    assert "labor_employment_budget_outcome_replay_seed_candidate" in (
        report.candidate_exception_lake_labels
    )
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_outcome_replay_readiness_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not execute replay commands" in notes


def test_labor_employment_budget_outcome_seed_manifest_is_candidate_only(repo_root):
    manifest = LaborEmploymentBudgetOutcomeReplaySeedManifest.model_validate(
        load_json(_seed_manifest(repo_root))
    )

    assert manifest.status == "candidate_labor_employment_budget_outcome_replay_seed_manifest"
    assert manifest.practice_area == "labor_employment"
    assert manifest.candidate_only is True
    assert manifest.synthetic_only is True
    assert manifest.budget_submission_authorized is False
    assert manifest.lake_write_performed is False
    assert manifest.sqlite_write_performed is False
    assert manifest.external_writes_performed is False
    assert manifest.silent_learning_performed is False


def test_labor_employment_budget_outcome_replay_readiness_blocks_missing_seed(
    repo_root,
    tmp_path,
):
    manifest = load_json(_seed_manifest(repo_root))
    manifest["seeds"] = [
        seed
        for seed in manifest["seeds"]
        if seed["learning_fixture_id"] != "le-learning-ada-fmla-adversarial.v0_1"
    ]
    manifest_path = write_json(tmp_path / "missing-outcome-seed.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=manifest_path,
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "blocked-missing-seed",
    )
    failed = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_outcome_replay"
    assert report.failed_case_count == 1
    assert report.missing_loop_requirement_count == 1
    assert "all_learning_fixture_cases_have_outcome_seeds" in failed
    assert "le-learning-ada-fmla-adversarial.v0_1" in (
        failed["all_learning_fixture_cases_have_outcome_seeds"].blocking_refs
    )
    assert report.lake_write_performed is False
    assert report.silent_learning_performed is False


def test_labor_employment_budget_outcome_replay_readiness_blocks_unresolved_ref(
    repo_root,
    tmp_path,
):
    manifest = load_json(_seed_manifest(repo_root))
    manifest["seeds"][0]["replay_seed_refs_by_loop"]["actuals_variance"].append(
        "examples/synthetic/labor-employment/missing-outcome-seed.json"
    )
    manifest_path = write_json(tmp_path / "missing-ref-outcome-seed.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=manifest_path,
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "blocked-unresolved-ref",
    )
    failed_case = next(case for case in report.cases if case.status == "failed")
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_outcome_replay"
    assert report.unresolved_source_ref_count == 1
    assert failed_case.learning_fixture_id == "le-learning-discrimination-harassment-clean.v0_1"
    assert "unresolved_replay_seed_refs" in failed_case.failure_ids
    assert "replay_seed_refs_resolve" in failed_checks


def test_labor_employment_budget_outcome_replay_readiness_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    learning_report = _learning_report(repo_root, tmp_path)
    exit_code = main(
        [
            "audit-labor-employment-budget-outcome-replay-readiness",
            "--seed-manifest",
            str(_seed_manifest(repo_root)),
            "--learning-fixture-report",
            str(learning_report),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-budget-outcome-replay-readiness-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "labor_employment_budget_outcome_replay_ready_for_review"' in captured.out
    assert '"fixture_count": 8' in captured.out
    assert '"loop_requirement_count": 20' in captured.out
    assert '"unresolved_source_ref_count": 0' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path
        / "le-budget-outcome-replay-readiness-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME
    ).is_file()
