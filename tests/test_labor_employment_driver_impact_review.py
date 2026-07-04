from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_driver_impact_review import (
    LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME,
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
from lawfirm_os_intake.models import (
    LaborEmploymentDriverImpactReviewReport,
    LaborEmploymentExecutableDriverImpactReport,
)
from lawfirm_os_intake.util import load_json, write_json


EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)
REVIEW_SPEC_PATH = "examples/synthetic/gold/labor-employment-driver-impact-review.json"


def _driver_impact_report(repo_root, tmp_path):
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
    return impact_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME


def test_labor_employment_driver_impact_review_materializes_nonblocking_slice(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_driver_impact_review(
        review_spec_path=repo_root / REVIEW_SPEC_PATH,
        driver_impact_report_path=_driver_impact_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-driver-impact-review",
    )

    persisted = LaborEmploymentDriverImpactReviewReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME)
    )
    slice_report = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
    assert persisted.selected_case_count == 15
    assert persisted.failed_case_count == 0
    assert persisted.block_amount_budget_impact_count == 0
    assert persisted.range_widening_impact_count > 0
    assert persisted.scenario_fork_impact_count > 0
    assert persisted.reviewed_slice_report_ref
    assert slice_report.case_count == 15
    assert slice_report.block_amount_budget_impact_count == 0
    assert {case.executable_fixture_id for case in slice_report.cases} == {
        "le-discrimination-harassment-clean.executable.v0_1",
        "le-discrimination-harassment-messy-thread.executable.v0_1",
        "le-wage-hour-clean.executable.v0_1",
        "le-wage-hour-messy-thread.executable.v0_1",
        "le-class-collective-clean.executable.v0_1",
        "le-class-collective-messy-thread.executable.v0_1",
        "le-epli-carrier-clean.executable.v0_1",
        "le-ada-fmla-clean.executable.v0_1",
        "le-epli-carrier-messy-thread.executable.v0_1",
        "le-admin-exhaustion-clean.executable.v0_1",
        "le-admin-exhaustion-messy-thread.executable.v0_1",
        "le-retaliation-wrongful-termination-clean.executable.v0_1",
        "le-retaliation-wrongful-termination-messy-thread.executable.v0_1",
        "le-restrictive-covenant-clean.executable.v0_1",
        "le-restrictive-covenant-messy-thread.executable.v0_1",
    }
    assert slice_report.status == "labor_employment_executable_driver_impacts_ready_for_review"
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "labor_employment_driver_impact_review_report.md").read_text(
        encoding="utf-8"
    )
    assert "candidate-only synthetic evidence" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_driver_impact_review_blocks_blocking_case(
    repo_root,
    tmp_path,
):
    review_spec = load_json(repo_root / REVIEW_SPEC_PATH)
    review_spec["review_spec_id"] = "le_driver_impact_blocking_case_review.v0_1"
    review_spec["cases"] = [review_spec["cases"][0]]
    review_spec["required_selected_case_count"] = 1
    review_spec["cases"][0]["executable_fixture_id"] = (
        "le-class-collective-adversarial.executable.v0_1"
    )
    review_spec["cases"][0]["expected_allowed_budget_output"] = "blocked_amount_budget"
    blocked_spec_path = write_json(tmp_path / "blocking-review-spec.json", review_spec)

    report, run_dir = run_labor_employment_driver_impact_review(
        review_spec_path=blocked_spec_path,
        driver_impact_report_path=_driver_impact_report(repo_root, tmp_path),
        out_dir=tmp_path / "blocked-driver-impact-review",
    )

    assert report.status == "blocked_by_labor_employment_driver_impact_review"
    assert report.selected_case_count == 0
    assert report.failed_case_count == 1
    assert report.reviewed_slice_report_ref is None
    assert "amount_budget_block_present" in report.case_results[0].failure_ids
    assert not (run_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME).exists()


def test_labor_employment_driver_impact_review_blocks_missing_nonblocking_case(
    repo_root,
    tmp_path,
):
    review_spec = load_json(repo_root / REVIEW_SPEC_PATH)
    review_spec["review_spec_id"] = "le_driver_impact_missing_nonblocking_case_review.v0_1"
    review_spec["required_selected_case_count"] = 1
    review_spec["cases"] = [
        case
        for case in review_spec["cases"]
        if case["executable_fixture_id"] == "le-admin-exhaustion-clean.executable.v0_1"
    ]
    partial_spec_path = write_json(tmp_path / "partial-review-spec.json", review_spec)

    report, run_dir = run_labor_employment_driver_impact_review(
        review_spec_path=partial_spec_path,
        driver_impact_report_path=_driver_impact_report(repo_root, tmp_path),
        out_dir=tmp_path / "partial-driver-impact-review",
    )
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_driver_impact_review"
    assert report.selected_case_count == 1
    assert report.failed_case_count == 0
    assert "reviewed_slice_covers_all_nonblocking_source_cases" in failed_checks
    assert (
        "le-retaliation-wrongful-termination-messy-thread.executable.v0_1"
        in failed_checks["reviewed_slice_covers_all_nonblocking_source_cases"].blocking_refs
    )
    assert report.reviewed_slice_report_ref is None
    assert not (run_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME).exists()


def test_labor_employment_driver_impact_review_cli_writes_review_and_slice(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "review-labor-employment-driver-impact-slice",
            "--review-spec",
            str(repo_root / REVIEW_SPEC_PATH),
            "--driver-impact-report",
            str(_driver_impact_report(repo_root, tmp_path)),
            "--out-dir",
            str(tmp_path / "le-driver-impact-review-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-driver-impact-review-cli"
        / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
    assert report["selected_case_count"] == 15
    assert report["block_amount_budget_impact_count"] == 0
    assert (
        (tmp_path / "le-driver-impact-review-cli")
        .joinpath(LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME)
        .is_file()
    )
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
