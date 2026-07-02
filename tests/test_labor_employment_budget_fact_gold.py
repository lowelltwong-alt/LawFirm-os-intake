from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_fact_gold import (
    LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME,
    run_labor_employment_budget_fact_gold_validation,
)
from lawfirm_os_intake.models import (
    LaborEmploymentBudgetFactGoldReport,
    LaborEmploymentBudgetFactGoldSpec,
)
from lawfirm_os_intake.util import load_json, write_json


GOLD_REF = "examples/synthetic/gold/labor-employment-budget-fact-gold.json"


def test_labor_employment_budget_fact_gold_validation_passes_and_persists_case_reports(
    tmp_path,
    repo_root,
):
    report, run_dir = run_labor_employment_budget_fact_gold_validation(
        gold_path=repo_root / GOLD_REF,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-fact-gold",
    )
    persisted = LaborEmploymentBudgetFactGoldReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME)
    )

    assert report.status == "passed"
    assert persisted.case_count == 2
    assert persisted.failed_case_count == 0
    assert persisted.failed_check_count == 0
    assert all(case.status == "passed" for case in persisted.cases)
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.reviewed_gold is True
    assert persisted.data_scope == "synthetic"
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    assert all(case.report_ref for case in persisted.cases)
    for case in persisted.cases:
        assert (
            run_dir / "cases" / case.case_id / "labor_employment_budget_fact_audit_report.json"
        ).is_file()

    notes = (run_dir / "labor_employment_budget_fact_gold_report.md").read_text(encoding="utf-8")
    assert "reviewed synthetic-gold report" in notes
    assert "does not resolve facts" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_budget_fact_gold_spec_is_synthetic_candidate_only(repo_root):
    gold = LaborEmploymentBudgetFactGoldSpec.model_validate(load_json(repo_root / GOLD_REF))

    assert gold.reviewed is True
    assert gold.data_scope == "synthetic"
    assert gold.candidate_only is True
    assert gold.non_authoritative is True
    assert gold.budget_amount_output_authorized is False
    assert gold.budget_submission_authorized is False
    assert gold.lake_write_performed is False
    assert gold.sqlite_write_performed is False
    assert gold.external_writes_performed is False
    assert len(gold.cases) == 2


def test_labor_employment_budget_fact_gold_validation_fails_closed_on_drift(
    tmp_path,
    repo_root,
):
    payload = load_json(repo_root / GOLD_REF)
    payload["cases"][0]["expected_critical_gap_count"] = 99
    broken_gold = write_json(tmp_path / "broken-le-budget-fact-gold.json", payload)

    report, _ = run_labor_employment_budget_fact_gold_validation(
        gold_path=broken_gold,
        repo_root=repo_root,
        out_dir=tmp_path / "broken-le-budget-fact-gold",
    )

    assert report.status == "failed"
    assert report.failed_case_count == 1
    assert report.failed_check_count >= 1
    assert any(
        check.check_id == "counts_match_gold" and check.status == "failed"
        for check in report.checks
    )
    failed_case = next(case for case in report.cases if case.status == "failed")
    assert "counts_match_gold" in failed_case.failed_expectation_ids


def test_labor_employment_budget_fact_gold_cli_writes_report(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "validate-labor-employment-budget-fact-gold",
            "--gold",
            str(repo_root / GOLD_REF),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-budget-fact-gold-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path / "le-budget-fact-gold-cli" / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "passed"
    assert report["case_count"] == 2
    assert '"reviewed_gold": true' in captured.out
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
