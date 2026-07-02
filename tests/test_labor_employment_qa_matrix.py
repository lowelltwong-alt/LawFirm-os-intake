from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_qa_matrix import (
    LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
    run_labor_employment_qa_matrix,
)
from lawfirm_os_intake.models import LaborEmploymentQAMatrixReport
from lawfirm_os_intake.util import load_json


def test_labor_employment_qa_matrix_covers_blocked_and_range_only_cases(
    tmp_path,
    repo_root,
):
    report, run_dir = run_labor_employment_qa_matrix(
        repo_root=repo_root,
        out_dir=tmp_path / "le-qa-matrix",
    )
    persisted = LaborEmploymentQAMatrixReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME)
    )
    cases = {case.case_id: case for case in persisted.cases}

    assert persisted.labor_employment_qa_matrix_report_id == (
        report.labor_employment_qa_matrix_report_id
    )
    assert persisted.status == "labor_employment_qa_matrix_ready_for_review"
    assert persisted.case_count == 2
    assert persisted.failed_case_count == 0

    blocked = cases["critical_fact_gaps_block_amount_budget"]
    assert blocked.status == "passed"
    assert blocked.actual_budget_readiness_state == "blocked_missing_critical_facts"
    assert blocked.actual_budget_gate_effect == "block_amount_budget_before_proposal"
    assert blocked.critical_gap_count > 0
    assert blocked.relationship_budget_treatment == "block_amount_budget"

    ready = cases["ready_critical_facts_still_range_only"]
    assert ready.status == "passed"
    assert ready.actual_budget_readiness_state == "range_only_pending_human_review"
    assert ready.actual_budget_gate_effect == "allow_range_or_hours_only_pending_review"
    assert ready.critical_gap_count == 0
    assert ready.gap_count > 0

    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.conflict_conclusion_emitted is False
    assert persisted.matter_opening_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    for case in persisted.cases:
        assert (
            run_dir / "cases" / case.case_id / "labor_employment_budget_fact_audit_report.json"
        ).is_file()


def test_labor_employment_qa_matrix_cli_writes_candidate_report(
    tmp_path,
    repo_root,
    capsys,
):
    exit_code = main(
        [
            "build-labor-employment-qa-matrix",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-qa-matrix-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(tmp_path / "le-qa-matrix-cli" / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME)

    assert exit_code == 0
    assert report["status"] == "labor_employment_qa_matrix_ready_for_review"
    assert report["case_count"] == 2
    assert report["failed_case_count"] == 0
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
