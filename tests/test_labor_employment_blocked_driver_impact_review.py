from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_blocked_driver_impact_review import (
    LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_blocked_driver_impact_review,
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
from lawfirm_os_intake.models import LaborEmploymentBlockedDriverImpactReviewReport
from lawfirm_os_intake.util import load_json


EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)


def _driver_chain(repo_root, tmp_path):
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
    return fact_binding_run_dir, driver_binding_run_dir, impact_run_dir


def test_labor_employment_blocked_driver_impact_review_explains_blockers(
    repo_root,
    tmp_path,
):
    fact_dir, driver_dir, impact_dir = _driver_chain(repo_root, tmp_path)

    report, run_dir = run_labor_employment_blocked_driver_impact_review(
        fact_binding_report_path=fact_dir
        / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
        driver_binding_report_path=(
            driver_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        driver_impact_report_path=(
            impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-blocked-driver-impact-review",
    )
    persisted = LaborEmploymentBlockedDriverImpactReviewReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME)
    )
    cases = {case.executable_fixture_id: case for case in persisted.case_reviews}

    assert report.status == "labor_employment_blocked_driver_impacts_ready_for_review"
    assert persisted.case_count == 8
    assert persisted.blocked_case_count == 6
    assert persisted.nonblocking_case_count == 2
    assert persisted.blocker_fact_count == 8
    assert persisted.block_amount_budget_impact_count == 12
    assert "source_missing" in persisted.candidate_exception_lake_labels
    assert "prompt_injection_source_content" in persisted.candidate_exception_lake_labels
    assert "labor_employment_critical_budget_fact_block" in (
        persisted.candidate_exception_lake_labels
    )
    assert all(case.allowed_budget_output == "blocked_amount_budget" for case in cases.values())
    assert all(case.blocker_facts for case in cases.values())
    assert all(case.critical_driver_dimensions for case in cases.values())
    assert all(case.unblock_actions for case in cases.values())

    epli = cases["le-epli-carrier-missing-attachment.executable.v0_1"]
    assert "carrier_guideline_rate_context" in epli.critical_driver_dimensions
    assert any(
        fact.fact_id == "carrier_guideline_and_rate_source"
        and "source_missing" in fact.candidate_exception_lake_labels
        for fact in epli.blocker_facts
    )
    assert any(
        action.startswith("collect_or_confirm_unavailable_source:")
        for action in epli.unblock_actions
    )
    class_case = cases["le-class-collective-adversarial.executable.v0_1"]
    assert "prompt_injection_source_content" in class_case.candidate_exception_lake_labels
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "labor_employment_blocked_driver_impact_review_report.md").read_text(
        encoding="utf-8"
    )
    assert "why amount-budget output remains blocked" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_blocked_driver_impact_review_cli_writes_packet(
    repo_root,
    tmp_path,
    capsys,
):
    fact_dir, driver_dir, impact_dir = _driver_chain(repo_root, tmp_path)

    exit_code = main(
        [
            "review-labor-employment-blocked-driver-impacts",
            "--fact-binding-report",
            str(fact_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME),
            "--driver-binding-report",
            str(driver_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME),
            "--driver-impact-report",
            str(impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME),
            "--out-dir",
            str(tmp_path / "le-blocked-driver-impact-review-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-blocked-driver-impact-review-cli"
        / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_blocked_driver_impacts_ready_for_review"
    assert report["blocked_case_count"] == 6
    assert report["blocker_fact_count"] == 8
    assert report["block_amount_budget_impact_count"] == 12
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
