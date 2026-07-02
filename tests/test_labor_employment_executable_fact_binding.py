from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentExecutableBudgetFactBindingManifest,
    LaborEmploymentExecutableBudgetFactBindingReport,
)
from lawfirm_os_intake.util import load_json, write_json


BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)
EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)


def _run_executable_fixture_audit(repo_root, tmp_path):
    return run_labor_employment_executable_fixture_audit(
        manifest_path=repo_root / EXECUTABLE_MANIFEST_PATH,
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fixtures",
    )


def test_labor_employment_executable_fact_binding_binds_gaps_without_side_effects(
    repo_root,
    tmp_path,
):
    _, executable_run_dir = _run_executable_fixture_audit(repo_root, tmp_path)

    report, run_dir = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=repo_root / BINDING_MANIFEST_PATH,
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fact-binding",
    )
    persisted = LaborEmploymentExecutableBudgetFactBindingReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_executable_budget_fact_bindings_ready_for_review"
    assert persisted.case_count == 6
    assert persisted.failed_case_count == 0
    assert persisted.fact_binding_count == 13
    assert persisted.critical_fact_binding_count == 7
    assert persisted.evidence_bound_fact_count == 13
    assert persisted.exception_bound_fact_count == 7
    assert persisted.missing_policy_fact_count == 0
    assert persisted.missing_source_signal_count == 0
    assert persisted.missing_exception_label_count == 0
    assert persisted.missing_source_id_count == 0
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(case.status == "passed" for case in persisted.cases)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.conflict_conclusion_emitted is False
    assert persisted.matter_opening_authorized is False
    assert persisted.training_pipeline_created is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    cases = {case.executable_fixture_id: case for case in persisted.cases}
    wage_bindings = {
        binding.fact_id: binding
        for binding in cases["le-wage-hour-missing-attachment.executable.v0_1"].fact_bindings
    }
    assert wage_bindings["wage_hour_pay_period_and_employee_volume"].binding_state == (
        "source_and_exception_bound_gap_candidate"
    )
    assert wage_bindings["wage_hour_pay_period_and_employee_volume"].matched_source_ids == [
        "syn-le-wage-hour-payroll-export-missing-001",
        "syn-le-wage-hour-timekeeping-export-missing-001",
    ]
    assert wage_bindings["class_collective_or_group_scope"].binding_state == (
        "source_bound_gap_candidate"
    )
    discrimination_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-discrimination-harassment-missing-attachment.executable.v0_1"
        ].fact_bindings
    }
    assert discrimination_bindings["carrier_guideline_and_rate_source"].binding_state == (
        "source_and_exception_bound_gap_candidate"
    )
    assert discrimination_bindings["carrier_guideline_and_rate_source"].matched_source_ids == [
        "syn-le-discrimination-guidelines-missing-001"
    ]
    assert (
        discrimination_bindings["administrative_exhaustion_and_agency_record"].binding_state
        == "source_and_exception_bound_gap_candidate"
    )
    retaliation_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-messy-thread.executable.v0_1"
        ].fact_bindings
    }
    assert retaliation_bindings["forum_removed_and_arbitration_posture"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert retaliation_bindings["forum_removed_and_arbitration_posture"].required_level == (
        "important"
    )

    notes = (run_dir / "labor_employment_executable_fact_binding_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not resolve those facts" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_executable_fact_binding_manifest_is_candidate_only(repo_root):
    manifest = LaborEmploymentExecutableBudgetFactBindingManifest.model_validate(
        load_json(repo_root / BINDING_MANIFEST_PATH)
    )

    assert manifest.synthetic_only is True
    assert manifest.candidate_only is True
    assert manifest.human_review_required is True
    assert manifest.budget_amount_output_authorized is False
    assert manifest.budget_submission_authorized is False
    assert manifest.lake_write_performed is False
    assert manifest.sqlite_write_performed is False
    assert manifest.external_writes_performed is False
    assert len(manifest.bindings) == 6


def test_labor_employment_executable_fact_binding_blocks_missing_policy_fact(
    repo_root,
    tmp_path,
):
    _, executable_run_dir = _run_executable_fixture_audit(repo_root, tmp_path)
    payload = load_json(repo_root / BINDING_MANIFEST_PATH)
    payload["bindings"][0]["fact_bindings"][0]["fact_id"] = "missing_fact_need"
    broken_manifest_path = write_json(tmp_path / "broken-binding-manifest.json", payload)

    report, _ = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=broken_manifest_path,
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "broken-le-executable-fact-binding",
    )

    assert report.status == "blocked_by_labor_employment_executable_budget_fact_bindings"
    assert report.failed_case_count == 1
    assert report.missing_policy_fact_count == 1
    assert any(
        check.check_id == "all_bound_facts_exist_in_policy" and check.status == "failed"
        for check in report.checks
    )


def test_labor_employment_executable_fact_binding_blocks_missing_source_signal(
    repo_root,
    tmp_path,
):
    _, executable_run_dir = _run_executable_fixture_audit(repo_root, tmp_path)
    payload = load_json(repo_root / BINDING_MANIFEST_PATH)
    payload["bindings"][0]["fact_bindings"][0]["source_signal_terms"] = [
        "never present in this synthetic source"
    ]
    broken_manifest_path = write_json(tmp_path / "broken-binding-manifest.json", payload)

    report, _ = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=broken_manifest_path,
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "broken-le-executable-fact-binding",
    )

    assert report.status == "blocked_by_labor_employment_executable_budget_fact_bindings"
    assert report.failed_case_count == 1
    assert report.missing_source_signal_count == 1
    assert "class_collective_or_group_scope:missing_source_signal_terms" in (
        report.cases[0].failed_expectation_ids
    )


def test_labor_employment_executable_fact_binding_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    _, executable_run_dir = _run_executable_fixture_audit(repo_root, tmp_path)

    exit_code = main(
        [
            "audit-labor-employment-executable-fact-binding",
            "--binding-manifest",
            str(repo_root / BINDING_MANIFEST_PATH),
            "--executable-fixture-report",
            str(executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-executable-fact-binding-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-executable-fact-binding-cli"
        / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == ("labor_employment_executable_budget_fact_bindings_ready_for_review")
    assert report["case_count"] == 6
    assert report["fact_binding_count"] == 13
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
