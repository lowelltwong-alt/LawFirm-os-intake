from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_blocked_driver_impact_review import (
    LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_blocked_driver_impact_review,
)
from lawfirm_os_intake.labor_employment_budget_output_expectations import (
    LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
    run_labor_employment_budget_output_expectations_audit,
)
from lawfirm_os_intake.labor_employment_driver_impact_review import (
    LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_driver_impact_review,
)
from lawfirm_os_intake.labor_employment_executable_driver_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_driver_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_driver_impact import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME,
    run_labor_employment_executable_driver_impact_audit,
)
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.models import LaborEmploymentBudgetOutputExpectationReport
from lawfirm_os_intake.util import load_json, write_json


EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)
REVIEW_SPEC_PATH = "examples/synthetic/gold/labor-employment-driver-impact-review.json"


def _driver_review_chain(repo_root, tmp_path, *, review_spec_path=None):
    _, executable_run_dir = run_labor_employment_executable_fixture_audit(
        manifest_path=repo_root / EXECUTABLE_MANIFEST_PATH,
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fixtures",
    )
    _, fact_binding_run_dir = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=repo_root / BINDING_MANIFEST_PATH,
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fact-binding",
    )
    _, driver_binding_run_dir = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        executable_fact_binding_report_path=(
            fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-driver-binding",
    )
    _, impact_run_dir = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=(
            driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-executable-driver-impact",
    )
    _, driver_review_run_dir = run_labor_employment_driver_impact_review(
        review_spec_path=review_spec_path or repo_root / REVIEW_SPEC_PATH,
        driver_impact_report_path=(
            impact_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-driver-impact-review",
    )
    _, blocked_review_run_dir = run_labor_employment_blocked_driver_impact_review(
        fact_binding_report_path=(
            fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        driver_binding_report_path=(
            driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        driver_impact_report_path=(
            impact_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-blocked-driver-impact-review",
    )
    return impact_run_dir, driver_review_run_dir, blocked_review_run_dir


def test_labor_employment_budget_output_expectations_classifies_every_case(
    repo_root,
    tmp_path,
):
    impact_dir, driver_review_dir, blocked_review_dir = _driver_review_chain(repo_root, tmp_path)

    report, run_dir = run_labor_employment_budget_output_expectations_audit(
        driver_impact_report_path=(
            impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        driver_impact_review_report_path=(
            driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        blocked_driver_impact_review_report_path=(
            blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-budget-output-expectations",
    )
    persisted = LaborEmploymentBudgetOutputExpectationReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME)
    )
    cases = {case.executable_fixture_id: case for case in persisted.cases}

    assert report.status == "labor_employment_budget_output_expectations_ready_for_review"
    assert persisted.case_count == 28
    assert persisted.failed_case_count == 0
    assert persisted.blocked_amount_budget_case_count == 14
    assert persisted.range_or_hours_only_case_count == 5
    assert persisted.candidate_range_after_review_case_count == 9
    assert persisted.reviewed_nonblocking_case_count == 14
    assert persisted.blocked_review_case_count == 14
    assert all(check.status == "passed" for check in persisted.checks)
    assert "candidate_only_budget_review_required" in persisted.candidate_exception_lake_labels
    assert "budget_amount_blocked_pending_labor_employment_driver_review" in (
        persisted.candidate_exception_lake_labels
    )
    assert "labor_employment_reviewed_nonblocking_budget_gate_replay" in (
        persisted.candidate_exception_lake_labels
    )

    blocked = cases["le-epli-carrier-missing-attachment.executable.v0_1"]
    assert blocked.final_allowed_budget_output == "blocked_amount_budget"
    assert blocked.expectation_state == "blocked_amount_budget_pending_driver_review"
    assert blocked.amount_budget_blocked is True
    assert blocked.blocked_case_review_present is True
    assert blocked.selected_for_reviewed_nonblocking_slice is False
    assert blocked.candidate_exception_lake_labels
    assert blocked.required_next_gates
    ada_blocked = cases["le-ada-fmla-adversarial.executable.v0_1"]
    assert ada_blocked.final_allowed_budget_output == "blocked_amount_budget"
    assert ada_blocked.amount_budget_blocked is True
    assert ada_blocked.blocked_case_review_present is True
    assert "budget_amount_blocked_pending_labor_employment_driver_review" in (
        ada_blocked.candidate_exception_lake_labels
    )
    discrimination_adversarial = cases["le-discrimination-harassment-adversarial.executable.v0_1"]
    assert discrimination_adversarial.final_allowed_budget_output == "blocked_amount_budget"
    assert discrimination_adversarial.amount_budget_blocked is True
    assert discrimination_adversarial.blocked_case_review_present is True
    assert discrimination_adversarial.selected_for_reviewed_nonblocking_slice is False
    assert discrimination_adversarial.block_amount_budget_impact_count == 3
    assert discrimination_adversarial.critical_review_only_impact_count == 3
    assert discrimination_adversarial.range_widening_impact_count == 4
    assert discrimination_adversarial.scenario_fork_impact_count == 1
    assert discrimination_adversarial.rate_guideline_review_impact_count == 2
    assert "prompt_injection_source_content" in (
        discrimination_adversarial.candidate_exception_lake_labels
    )
    assert "labor_employment_missing_critical_budget_fact" in (
        discrimination_adversarial.candidate_exception_lake_labels
    )
    epli_adversarial = cases["le-epli-carrier-adversarial.executable.v0_1"]
    assert epli_adversarial.final_allowed_budget_output == "blocked_amount_budget"
    assert epli_adversarial.amount_budget_blocked is True
    assert epli_adversarial.blocked_case_review_present is True
    assert epli_adversarial.block_amount_budget_impact_count == 3
    assert "prompt_injection_source_content" in epli_adversarial.candidate_exception_lake_labels
    class_missing = cases["le-class-collective-missing-attachment.executable.v0_1"]
    assert class_missing.final_allowed_budget_output == "blocked_amount_budget"
    assert class_missing.amount_budget_blocked is True
    assert class_missing.blocked_case_review_present is True
    assert class_missing.block_amount_budget_impact_count == 2
    assert "source_missing" in class_missing.candidate_exception_lake_labels
    retaliation_missing = cases[
        "le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"
    ]
    assert retaliation_missing.final_allowed_budget_output == "blocked_amount_budget"
    assert retaliation_missing.amount_budget_blocked is True
    assert retaliation_missing.blocked_case_review_present is True
    assert retaliation_missing.block_amount_budget_impact_count == 3
    assert "source_missing" in retaliation_missing.candidate_exception_lake_labels
    admin_missing = cases["le-admin-exhaustion-missing-attachment.executable.v0_1"]
    assert admin_missing.final_allowed_budget_output == "blocked_amount_budget"
    assert admin_missing.amount_budget_blocked is True
    assert admin_missing.blocked_case_review_present is True
    assert admin_missing.block_amount_budget_impact_count == 1
    assert "source_missing" in admin_missing.candidate_exception_lake_labels
    wage_adversarial = cases["le-wage-hour-adversarial.executable.v0_1"]
    assert wage_adversarial.final_allowed_budget_output == "blocked_amount_budget"
    assert wage_adversarial.amount_budget_blocked is True
    assert wage_adversarial.blocked_case_review_present is True
    assert wage_adversarial.block_amount_budget_impact_count == 2
    assert "prompt_injection_source_content" in (wage_adversarial.candidate_exception_lake_labels)
    restrictive_adversarial = cases["le-restrictive-covenant-adversarial.executable.v0_1"]
    assert restrictive_adversarial.final_allowed_budget_output == "blocked_amount_budget"
    assert restrictive_adversarial.amount_budget_blocked is True
    assert restrictive_adversarial.blocked_case_review_present is True
    assert restrictive_adversarial.selected_for_reviewed_nonblocking_slice is False
    assert restrictive_adversarial.block_amount_budget_impact_count == 1
    assert "labor_employment_missing_critical_budget_fact" in (
        restrictive_adversarial.candidate_exception_lake_labels
    )

    nonblocking = cases["le-admin-exhaustion-clean.executable.v0_1"]
    assert (
        nonblocking.final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert nonblocking.selected_for_reviewed_nonblocking_slice is True
    assert nonblocking.amount_budget_blocked is False
    assert nonblocking.blocked_case_review_present is False
    assert nonblocking.block_amount_budget_impact_count == 0
    assert (
        cases[
            "le-retaliation-wrongful-termination-clean.executable.v0_1"
        ].final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases[
            "le-retaliation-wrongful-termination-clean.executable.v0_1"
        ].selected_for_reviewed_nonblocking_slice
        is True
    )
    assert (
        cases["le-wage-hour-clean.executable.v0_1"].final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-wage-hour-messy-thread.executable.v0_1"].final_allowed_budget_output
        == "range_or_hours_only_pending_review"
    )
    assert cases[
        "le-wage-hour-messy-thread.executable.v0_1"
    ].selected_for_reviewed_nonblocking_slice
    assert cases["le-wage-hour-messy-thread.executable.v0_1"].block_amount_budget_impact_count == 0
    assert cases["le-wage-hour-messy-thread.executable.v0_1"].critical_review_only_impact_count == 3
    assert (
        cases["le-epli-carrier-clean.executable.v0_1"].final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-ada-fmla-clean.executable.v0_1"].final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert cases["le-ada-fmla-clean.executable.v0_1"].selected_for_reviewed_nonblocking_slice
    assert (
        cases["le-epli-carrier-messy-thread.executable.v0_1"].final_allowed_budget_output
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-epli-carrier-messy-thread.executable.v0_1"].expectation_state
        == "range_or_hours_only_pending_human_review"
    )
    assert (
        cases["le-class-collective-clean.executable.v0_1"].final_allowed_budget_output
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-class-collective-clean.executable.v0_1"].selected_for_reviewed_nonblocking_slice
        is True
    )
    assert (
        cases["le-class-collective-messy-thread.executable.v0_1"].final_allowed_budget_output
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases[
            "le-class-collective-messy-thread.executable.v0_1"
        ].selected_for_reviewed_nonblocking_slice
        is True
    )
    assert (
        cases[
            "le-discrimination-harassment-clean.executable.v0_1"
        ].selected_for_reviewed_nonblocking_slice
        is True
    )
    discrimination_messy = cases["le-discrimination-harassment-messy-thread.executable.v0_1"]
    assert (
        discrimination_messy.final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert discrimination_messy.selected_for_reviewed_nonblocking_slice is True
    assert discrimination_messy.amount_budget_blocked is False
    assert discrimination_messy.blocked_case_review_present is False
    assert discrimination_messy.block_amount_budget_impact_count == 0
    assert discrimination_messy.critical_review_only_impact_count == 4
    assert discrimination_messy.range_widening_impact_count == 7
    assert discrimination_messy.scenario_fork_impact_count == 2
    assert "labor_employment_critical_fact_review_only" in (
        discrimination_messy.candidate_exception_lake_labels
    )
    restrictive_clean = cases["le-restrictive-covenant-clean.executable.v0_1"]
    assert (
        restrictive_clean.final_allowed_budget_output
        == "candidate_range_after_review_pending_human_review"
    )
    assert restrictive_clean.selected_for_reviewed_nonblocking_slice is True
    assert restrictive_clean.block_amount_budget_impact_count == 0
    assert restrictive_clean.critical_review_only_impact_count == 3
    assert "labor_employment_critical_fact_review_only" in (
        restrictive_clean.candidate_exception_lake_labels
    )
    restrictive_messy = cases["le-restrictive-covenant-messy-thread.executable.v0_1"]
    assert restrictive_messy.final_allowed_budget_output == "range_or_hours_only_pending_review"
    assert restrictive_messy.selected_for_reviewed_nonblocking_slice is True
    assert restrictive_messy.block_amount_budget_impact_count == 0
    assert restrictive_messy.critical_review_only_impact_count == 3
    assert restrictive_messy.range_widening_impact_count == 6
    assert restrictive_messy.scenario_fork_impact_count == 2
    assert "labor_employment_budget_output_range_or_hours_only" in (
        restrictive_messy.candidate_exception_lake_labels
    )

    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_output_expectations_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not compute dollar amounts" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_budget_output_expectations_blocks_missing_reviewed_slice(
    repo_root,
    tmp_path,
):
    review_spec = load_json(repo_root / REVIEW_SPEC_PATH)
    review_spec["review_spec_id"] = "le_budget_output_expectation_missing_slice.v0_1"
    review_spec["required_selected_case_count"] = 1
    review_spec["cases"] = [
        case
        for case in review_spec["cases"]
        if case["executable_fixture_id"] == "le-admin-exhaustion-clean.executable.v0_1"
    ]
    partial_review_spec_path = write_json(tmp_path / "partial-review-spec.json", review_spec)
    impact_dir, driver_review_dir, blocked_review_dir = _driver_review_chain(
        repo_root,
        tmp_path,
        review_spec_path=partial_review_spec_path,
    )

    report, _ = run_labor_employment_budget_output_expectations_audit(
        driver_impact_report_path=(
            impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        driver_impact_review_report_path=(
            driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        blocked_driver_impact_review_report_path=(
            blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        out_dir=tmp_path / "blocked-le-budget-output-expectations",
    )
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}
    failed_cases = {
        case.executable_fixture_id: case for case in report.cases if case.status == "failed"
    }

    assert report.status == "blocked_by_labor_employment_budget_output_expectations"
    assert report.failed_case_count == 13
    assert "source_reports_ready" in failed_checks
    assert "nonblocking_cases_are_reviewed_for_replay" in failed_checks
    assert "le-retaliation-wrongful-termination-messy-thread.executable.v0_1" in failed_cases
    assert "le-retaliation-wrongful-termination-clean.executable.v0_1" in failed_cases
    assert "le-wage-hour-messy-thread.executable.v0_1" in failed_cases
    assert "le-discrimination-harassment-messy-thread.executable.v0_1" in failed_cases
    assert "review_result_missing" in (
        failed_cases["le-retaliation-wrongful-termination-messy-thread.executable.v0_1"].failure_ids
    )
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False


def test_labor_employment_budget_output_expectations_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    impact_dir, driver_review_dir, blocked_review_dir = _driver_review_chain(repo_root, tmp_path)

    exit_code = main(
        [
            "audit-labor-employment-budget-output-expectations",
            "--driver-impact-report",
            str(impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME),
            "--driver-impact-review-report",
            str(driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME),
            "--blocked-driver-impact-review-report",
            str(blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME),
            "--out-dir",
            str(tmp_path / "le-budget-output-expectations-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-budget-output-expectations-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_budget_output_expectations_ready_for_review"
    assert report["case_count"] == 28
    assert report["blocked_amount_budget_case_count"] == 14
    assert report["candidate_range_after_review_case_count"] == 9
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
