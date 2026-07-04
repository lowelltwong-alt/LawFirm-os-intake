from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_qa_gate import (
    LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME,
    run_labor_employment_budget_qa_gate,
)
from lawfirm_os_intake.models import LaborEmploymentBudgetQAGateReport
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"


def _fixture(repo_root, name):
    return repo_root / FIXTURE_ROOT / name


def test_labor_employment_budget_qa_gate_aggregates_output_states(repo_root, tmp_path):
    report, run_dir = run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=_fixture(
            repo_root,
            "demo-labor-employment-budget-output-expectations-report.json",
        ),
        blocked_driver_impact_review_report_path=_fixture(
            repo_root,
            "demo-labor-employment-blocked-driver-impact-review-report.json",
        ),
        executable_coverage_report_path=_fixture(
            repo_root,
            "demo-labor-employment-executable-coverage-report.json",
        ),
        out_dir=tmp_path / "le-budget-qa-gate",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetQAGateReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME)
    )
    buckets = {bucket.output_state: bucket for bucket in persisted.output_state_buckets}

    assert report.status == "labor_employment_budget_qa_gate_ready_for_review"
    assert persisted.case_count == 24
    assert persisted.blocked_amount_budget_case_count == 12
    assert persisted.range_or_hours_only_case_count == 4
    assert persisted.candidate_range_after_review_case_count == 8
    assert persisted.reviewed_nonblocking_case_count == 12
    assert persisted.covered_required_family_count == persisted.required_family_count == 8
    assert persisted.required_families_missing == []
    assert persisted.missing_blocked_review_case_ids == []
    assert persisted.missing_nonblocking_review_case_ids == []
    assert buckets["blocked_amount_budget"].case_count == 12
    assert buckets["range_or_hours_only_pending_review"].case_count == 4
    assert buckets["candidate_range_after_review_pending_human_review"].case_count == 8
    assert all(check.status == "passed" for check in persisted.checks)
    assert "labor_employment_budget_qa_gate_candidate" in (
        persisted.candidate_exception_lake_labels
    )
    assert "budget_amount_blocked_pending_labor_employment_driver_review" in (
        persisted.candidate_exception_lake_labels
    )
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_qa_gate_report.md").read_text(encoding="utf-8")
    assert "does not compute dollar amounts" in notes
    assert "write Lake/SQLite records" in notes


def test_labor_employment_budget_qa_gate_fails_closed_without_all_output_states(
    repo_root,
    tmp_path,
):
    output = load_json(
        _fixture(repo_root, "demo-labor-employment-budget-output-expectations-report.json")
    )
    output["cases"] = [
        case
        for case in output["cases"]
        if case["final_allowed_budget_output"] != "range_or_hours_only_pending_review"
    ]
    output["case_count"] = len(output["cases"])
    output["range_or_hours_only_case_count"] = 0
    output["reviewed_nonblocking_case_count"] = sum(
        1 for case in output["cases"] if case["selected_for_reviewed_nonblocking_slice"]
    )
    output["candidate_exception_lake_labels"] = sorted(
        {label for case in output["cases"] for label in case["candidate_exception_lake_labels"]}
    )
    output_path = write_json(tmp_path / "budget-output-without-range.json", output)

    report, _ = run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=output_path,
        blocked_driver_impact_review_report_path=_fixture(
            repo_root,
            "demo-labor-employment-blocked-driver-impact-review-report.json",
        ),
        executable_coverage_report_path=_fixture(
            repo_root,
            "demo-labor-employment-executable-coverage-report.json",
        ),
        out_dir=tmp_path / "blocked-le-budget-qa-gate",
    )
    failed = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_qa_gate"
    assert "output_distribution_has_all_gate_states" in failed
    assert "range_or_hours_only_pending_review" in (
        failed["output_distribution_has_all_gate_states"].blocking_refs
    )
    assert report.external_writes_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False


def test_labor_employment_budget_qa_gate_fails_closed_on_lineage_mismatch(
    repo_root,
    tmp_path,
):
    output = load_json(
        _fixture(repo_root, "demo-labor-employment-budget-output-expectations-report.json")
    )
    output["source_blocked_driver_impact_review_report_id"] = (
        "leblockeddriverimpactreview_unrelated"
    )
    output_path = write_json(tmp_path / "budget-output-wrong-lineage.json", output)

    report, _ = run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=output_path,
        blocked_driver_impact_review_report_path=_fixture(
            repo_root,
            "demo-labor-employment-blocked-driver-impact-review-report.json",
        ),
        executable_coverage_report_path=_fixture(
            repo_root,
            "demo-labor-employment-executable-coverage-report.json",
        ),
        out_dir=tmp_path / "lineage-blocked-le-budget-qa-gate",
    )
    failed = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_qa_gate"
    assert "source_report_lineage_matches" in failed
    assert "source_blocked_driver_impact_review_report_id_mismatch" in (
        failed["source_report_lineage_matches"].blocking_refs
    )


def test_labor_employment_budget_qa_gate_fails_closed_on_coverage_mismatch(
    repo_root,
    tmp_path,
):
    coverage = load_json(
        _fixture(repo_root, "demo-labor-employment-executable-coverage-report.json")
    )
    for case in coverage["case_coverage"]:
        if case["executable_fixture_ids"]:
            case["executable_fixture_ids"] = []
            case["coverage_state"] = "missing_executable"
            break
    covered_cases = [
        case for case in coverage["case_coverage"] if case["coverage_state"] == "covered_executable"
    ]
    missing_cases = [
        case for case in coverage["case_coverage"] if case["coverage_state"] == "missing_executable"
    ]
    coverage["covered_pack_case_count"] = len(covered_cases)
    coverage["missing_executable_pack_case_count"] = len(missing_cases)
    coverage["covered_pack_case_ids"] = [case["pack_case_id"] for case in covered_cases]
    coverage["missing_executable_pack_case_ids"] = [case["pack_case_id"] for case in missing_cases]
    coverage_path = write_json(tmp_path / "coverage-missing-budget-case.json", coverage)

    report, _ = run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=_fixture(
            repo_root,
            "demo-labor-employment-budget-output-expectations-report.json",
        ),
        blocked_driver_impact_review_report_path=_fixture(
            repo_root,
            "demo-labor-employment-blocked-driver-impact-review-report.json",
        ),
        executable_coverage_report_path=coverage_path,
        out_dir=tmp_path / "coverage-blocked-le-budget-qa-gate",
    )
    failed = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_qa_gate"
    assert "coverage_fixture_ids_match_budget_output_cases" in failed
    assert any(
        ref.startswith("missing_from_coverage:")
        for ref in failed["coverage_fixture_ids_match_budget_output_cases"].blocking_refs
    )


def test_labor_employment_budget_qa_gate_cli_writes_report(repo_root, tmp_path, capsys):
    code = main(
        [
            "audit-labor-employment-budget-qa-gate",
            "--budget-output-expectations-report",
            str(
                _fixture(repo_root, "demo-labor-employment-budget-output-expectations-report.json")
            ),
            "--blocked-driver-impact-review-report",
            str(
                _fixture(
                    repo_root,
                    "demo-labor-employment-blocked-driver-impact-review-report.json",
                )
            ),
            "--executable-coverage-report",
            str(_fixture(repo_root, "demo-labor-employment-executable-coverage-report.json")),
            "--out-dir",
            str(tmp_path),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert '"status": "labor_employment_budget_qa_gate_ready_for_review"' in captured.out
    assert '"case_count": 24' in captured.out
    assert '"budget_submission_authorized": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME).is_file()
