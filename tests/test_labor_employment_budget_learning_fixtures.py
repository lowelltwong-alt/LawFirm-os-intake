from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentBudgetLearningFixtureManifest,
    LaborEmploymentBudgetLearningFixtureReport,
)
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"
MANIFEST_REF = "examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json"


def _qa_gate(repo_root):
    return repo_root / FIXTURE_ROOT / "demo-labor-employment-budget-qa-gate-report.json"


def _manifest(repo_root):
    return repo_root / MANIFEST_REF


def test_labor_employment_budget_learning_fixture_audit_covers_l_and_e_loops(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=_manifest(repo_root),
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "le-budget-learning-fixtures",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetLearningFixtureReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME)
    )

    assert persisted.budget_learning_fixture_report_id == (report.budget_learning_fixture_report_id)
    assert report.status == "labor_employment_budget_learning_fixtures_ready_for_review"
    assert report.fixture_count == 8
    assert report.covered_required_family_count == report.required_family_count == 8
    assert report.missing_required_families == []
    assert set(report.covered_budget_output_states) == {
        "blocked_amount_budget",
        "range_or_hours_only_pending_review",
        "candidate_range_after_review_pending_human_review",
    }
    assert report.missing_budget_output_states == []
    assert set(report.covered_learning_loop_types) == {
        "actuals_variance",
        "carrier_rejection_capture",
        "appeal_outcome",
        "reviewed_learning_gate",
        "blocked_budget_guard",
    }
    assert report.missing_learning_loop_types == []
    assert report.blocked_budget_guard_fixture_count == 1
    assert report.actuals_variance_fixture_count == 6
    assert report.carrier_rejection_fixture_count == 4
    assert report.appeal_outcome_fixture_count == 2
    assert report.reviewed_learning_gate_fixture_count == 7
    assert all(check.status == "passed" for check in report.checks)
    assert "labor_employment_budget_learning_fixture_candidate" in (
        report.candidate_exception_lake_labels
    )
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_learning_fixtures_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not create actuals" in notes


def test_labor_employment_budget_learning_fixture_manifest_is_candidate_only(repo_root):
    manifest = LaborEmploymentBudgetLearningFixtureManifest.model_validate(
        load_json(_manifest(repo_root))
    )

    assert manifest.status == "candidate_labor_employment_budget_learning_fixture_manifest"
    assert manifest.practice_area == "labor_employment"
    assert manifest.candidate_only is True
    assert manifest.synthetic_only is True
    assert manifest.budget_submission_authorized is False
    assert manifest.lake_write_performed is False
    assert manifest.sqlite_write_performed is False
    assert manifest.external_writes_performed is False
    assert manifest.silent_learning_performed is False


def test_labor_employment_budget_learning_fixture_audit_blocks_missing_family(
    repo_root,
    tmp_path,
):
    manifest = load_json(_manifest(repo_root))
    manifest["fixtures"] = [
        fixture
        for fixture in manifest["fixtures"]
        if fixture["family"] != "ada_fmla_accommodation_leave"
    ]
    manifest_path = write_json(tmp_path / "missing-ada-fmla-learning-fixtures.json", manifest)

    report, _ = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=manifest_path,
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "blocked-missing-family",
    )
    failed = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_learning_fixtures"
    assert "ada_fmla_accommodation_leave" in report.missing_required_families
    assert "required_families_have_learning_fixtures" in failed
    assert "ada_fmla_accommodation_leave" in (
        failed["required_families_have_learning_fixtures"].blocking_refs
    )
    assert report.lake_write_performed is False
    assert report.silent_learning_performed is False


def test_labor_employment_budget_learning_fixture_audit_blocks_state_mismatch(
    repo_root,
    tmp_path,
):
    manifest = load_json(_manifest(repo_root))
    manifest["fixtures"][0]["expected_budget_output_state"] = "range_or_hours_only_pending_review"
    manifest_path = write_json(tmp_path / "wrong-state-learning-fixtures.json", manifest)

    report, _ = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=manifest_path,
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "blocked-state-mismatch",
    )
    failed_case = next(case for case in report.cases if case.status == "failed")
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_learning_fixtures"
    assert failed_case.learning_fixture_id == "le-learning-discrimination-harassment-clean.v0_1"
    assert "budget_output_state_mismatch" in failed_case.failure_ids
    assert "all_fixture_cases_pass" in failed_checks


def test_labor_employment_budget_learning_fixture_audit_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-budget-learning-fixtures",
            "--manifest",
            str(_manifest(repo_root)),
            "--budget-qa-gate-report",
            str(_qa_gate(repo_root)),
            "--out-dir",
            str(tmp_path / "le-budget-learning-fixtures-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "labor_employment_budget_learning_fixtures_ready_for_review"' in captured.out
    assert '"fixture_count": 8' in captured.out
    assert '"covered_required_family_count": 8' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path
        / "le-budget-learning-fixtures-cli"
        / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME
    ).is_file()
