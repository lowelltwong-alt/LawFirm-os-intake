from lawfirm_os_intake.cli import main
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
from lawfirm_os_intake.models import LaborEmploymentExecutableDriverImpactReport
from lawfirm_os_intake.util import load_json


EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)


def _run_driver_binding_chain(repo_root, tmp_path):
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
    return driver_binding_run_dir


def test_labor_employment_executable_driver_impact_maps_drivers_to_budget_effects(
    repo_root,
    tmp_path,
):
    driver_binding_run_dir = _run_driver_binding_chain(repo_root, tmp_path)

    report, run_dir = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=(
            driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-executable-driver-impact",
    )
    persisted = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_executable_driver_impacts_ready_for_review"
    assert persisted.case_count == 12
    assert persisted.failed_case_count == 0
    assert persisted.impact_item_count == 48
    assert persisted.source_bound_impact_count == 48
    assert persisted.block_amount_budget_impact_count == 7
    assert persisted.critical_review_only_impact_count == 13
    assert persisted.range_widening_impact_count > 0
    assert persisted.scenario_fork_impact_count > 0
    assert persisted.rate_guideline_review_impact_count > 0
    assert persisted.human_review_impact_count == persisted.impact_item_count
    assert persisted.max_range_widening_factor >= 2.0
    assert persisted.missing_impact_policy_dimensions == []
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    cases = {case.executable_fixture_id: case for case in persisted.cases}
    wage_clean = cases["le-wage-hour-clean.executable.v0_1"]
    assert wage_clean.allowed_budget_output == "candidate_range_after_review_pending_human_review"
    assert wage_clean.block_amount_budget_impact_count == 0
    assert wage_clean.scenario_fork_impact_count >= 1
    discrimination_clean = cases["le-discrimination-harassment-clean.executable.v0_1"]
    assert discrimination_clean.allowed_budget_output == (
        "candidate_range_after_review_pending_human_review"
    )
    assert discrimination_clean.block_amount_budget_impact_count == 0
    class_case = cases["le-class-collective-adversarial.executable.v0_1"]
    assert class_case.allowed_budget_output == "blocked_amount_budget"
    assert class_case.block_amount_budget_impact_count > 0
    class_impacts = {item.driver_dimension: item for item in class_case.impact_items}
    assert "add_scenario_fork" in class_impacts["forum_arbitration"].impact_actions
    assert class_impacts["deposition_plan"].range_widening_factor == 1.7

    admin_case = cases["le-admin-exhaustion-clean.executable.v0_1"]
    assert admin_case.allowed_budget_output == "candidate_range_after_review_pending_human_review"
    assert admin_case.block_amount_budget_impact_count == 0
    admin_impacts = {item.driver_dimension: item for item in admin_case.impact_items}
    assert "add_scenario_fork" in admin_impacts["administrative_exhaustion"].impact_actions
    epli_clean = cases["le-epli-carrier-clean.executable.v0_1"]
    assert epli_clean.allowed_budget_output == "candidate_range_after_review_pending_human_review"
    assert epli_clean.block_amount_budget_impact_count == 0
    assert epli_clean.critical_review_only_impact_count == 3
    assert epli_clean.scenario_fork_impact_count == 1
    assert epli_clean.rate_guideline_review_impact_count == 2
    epli_messy = cases["le-epli-carrier-messy-thread.executable.v0_1"]
    assert epli_messy.allowed_budget_output == "range_or_hours_only_pending_review"
    assert epli_messy.block_amount_budget_impact_count == 0
    assert epli_messy.critical_review_only_impact_count == 4
    assert epli_messy.scenario_fork_impact_count == 1
    assert epli_messy.rate_guideline_review_impact_count == 2

    notes = (run_dir / "labor_employment_executable_driver_impact_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not compute dollar amounts" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_executable_driver_impact_blocks_missing_policy(
    repo_root,
    tmp_path,
    monkeypatch,
):
    driver_binding_run_dir = _run_driver_binding_chain(repo_root, tmp_path)
    import lawfirm_os_intake.labor_employment_executable_driver_impact as driver_impact

    policy = dict(driver_impact.DRIVER_IMPACT_POLICY)
    policy.pop("carrier_guideline_rate_context")
    monkeypatch.setattr(driver_impact, "DRIVER_IMPACT_POLICY", policy)

    report, _ = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=(
            driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        out_dir=tmp_path / "blocked-le-executable-driver-impact",
    )

    assert report.status == "blocked_by_labor_employment_executable_driver_impacts"
    assert report.missing_impact_policy_dimensions == ["carrier_guideline_rate_context"]
    assert any(
        check.check_id == "every_source_bound_driver_has_impact_policy" and check.status == "failed"
        for check in report.checks
    )


def test_labor_employment_executable_driver_impact_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    driver_binding_run_dir = _run_driver_binding_chain(repo_root, tmp_path)

    exit_code = main(
        [
            "audit-labor-employment-executable-driver-impact",
            "--executable-driver-binding-report",
            str(
                driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
            ),
            "--out-dir",
            str(tmp_path / "le-executable-driver-impact-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-executable-driver-impact-cli"
        / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_executable_driver_impacts_ready_for_review"
    assert report["case_count"] == 12
    assert report["impact_item_count"] == 48
    assert report["critical_review_only_impact_count"] == 13
    assert report["missing_impact_policy_dimensions"] == []
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
