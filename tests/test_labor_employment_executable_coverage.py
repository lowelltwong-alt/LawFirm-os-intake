import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_executable_coverage import (
    LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
    run_labor_employment_executable_coverage_audit,
)
from lawfirm_os_intake.models import LaborEmploymentExecutableCoverageReport
from lawfirm_os_intake.util import load_json, write_json


MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
PACK_PATH = "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"


def test_labor_employment_executable_coverage_reports_partial_pack_coverage(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_executable_coverage_audit(
        manifest_path=repo_root / MANIFEST_PATH,
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-coverage",
    )
    persisted = LaborEmploymentExecutableCoverageReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_executable_coverage_ready_for_review"
    assert persisted.coverage_state == "partial_executable_coverage"
    assert persisted.pack_case_count == 32
    assert persisted.executable_fixture_count == 27
    assert persisted.executable_pack_case_link_count == 28
    assert persisted.covered_pack_case_count == 28
    assert persisted.missing_executable_pack_case_count == 4
    assert persisted.covered_family_count == 8
    assert persisted.missing_family_count == 0
    assert persisted.covered_family_variant_count == 28
    assert persisted.missing_family_variant_count == 4
    assert set(persisted.covered_pack_case_ids) == {
        "le-discrimination-harassment-clean.v0_1",
        "le-discrimination-harassment-messy-thread.v0_1",
        "le-discrimination-harassment-missing-attachment.v0_1",
        "le-retaliation-wrongful-termination-clean.v0_1",
        "le-retaliation-wrongful-termination-messy-thread.v0_1",
        "le-retaliation-wrongful-termination-missing-attachment.v0_1",
        "le-restrictive-covenant-clean.v0_1",
        "le-restrictive-covenant-messy-thread.v0_1",
        "le-restrictive-covenant-missing-attachment.v0_1",
        "le-restrictive-covenant-adversarial.v0_1",
        "le-admin-exhaustion-clean.v0_1",
        "le-admin-exhaustion-missing-attachment.v0_1",
        "le-wage-hour-clean.v0_1",
        "le-wage-hour-messy-thread.v0_1",
        "le-wage-hour-missing-attachment.v0_1",
        "le-wage-hour-adversarial.v0_1",
        "le-ada-fmla-clean.v0_1",
        "le-ada-fmla-adversarial.v0_1",
        "le-ada-fmla-messy-thread.v0_1",
        "le-ada-fmla-missing-attachment.v0_1",
        "le-epli-carrier-clean.v0_1",
        "le-epli-carrier-messy-thread.v0_1",
        "le-epli-carrier-missing-attachment.v0_1",
        "le-epli-carrier-adversarial.v0_1",
        "le-class-collective-clean.v0_1",
        "le-class-collective-messy-thread.v0_1",
        "le-class-collective-missing-attachment.v0_1",
        "le-class-collective-adversarial.v0_1",
    }
    assert "le-discrimination-harassment-clean.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-discrimination-harassment-messy-thread.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-wage-hour-clean.v0_1" not in persisted.missing_executable_pack_case_ids
    assert "le-wage-hour-messy-thread.v0_1" not in persisted.missing_executable_pack_case_ids
    assert "le-wage-hour-adversarial.v0_1" not in persisted.missing_executable_pack_case_ids
    assert "le-retaliation-wrongful-termination-clean.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-retaliation-wrongful-termination-missing-attachment.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-admin-exhaustion-missing-attachment.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-restrictive-covenant-clean.v0_1" not in (persisted.missing_executable_pack_case_ids)
    assert "le-restrictive-covenant-messy-thread.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-restrictive-covenant-adversarial.v0_1" not in (
        persisted.missing_executable_pack_case_ids
    )
    assert "le-ada-fmla-clean.v0_1" not in persisted.missing_executable_pack_case_ids
    assert "le-ada-fmla-adversarial.v0_1" not in (persisted.missing_executable_pack_case_ids)
    assert "discrimination_harassment:messy_thread" not in persisted.missing_family_variant_refs
    assert "discrimination_harassment:adversarial" in persisted.missing_family_variant_refs
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.fixture_generation_authorized is False
    assert persisted.calibration_approved is False
    assert persisted.budget_amount_output_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    family = {item.family: item for item in persisted.family_coverage}
    assert family["ada_fmla_accommodation_leave"].covered_case_count == 4
    assert family["ada_fmla_accommodation_leave"].missing_variants == []
    assert family["discrimination_harassment"].covered_case_count == 3
    assert family["discrimination_harassment"].missing_case_count == 1
    assert family["discrimination_harassment"].missing_variants == ["adversarial"]
    assert family["wage_hour_flsa_state"].covered_case_count == 4
    assert family["wage_hour_flsa_state"].missing_case_count == 0
    assert family["wage_hour_flsa_state"].missing_variants == []
    assert family["epli_carrier_assignment"].covered_case_count == 4
    assert family["epli_carrier_assignment"].missing_variants == []
    assert family["retaliation_wrongful_termination"].covered_case_count == 3
    assert family["retaliation_wrongful_termination"].missing_case_count == 1
    assert family["restrictive_covenant_trade_secret"].covered_case_count == 4
    assert family["restrictive_covenant_trade_secret"].missing_case_count == 0
    assert family["restrictive_covenant_trade_secret"].missing_variants == []
    assert family["administrative_exhaustion_agency_record"].covered_case_count == 2
    assert family["administrative_exhaustion_agency_record"].missing_case_count == 2
    assert family["class_collective_paga_representative"].covered_case_count == 4
    assert family["class_collective_paga_representative"].missing_variants == []
    assert all(item.covered_case_count > 0 for item in persisted.family_coverage)
    notes = (run_dir / "labor_employment_executable_coverage_report.md").read_text(encoding="utf-8")
    assert "Missing executable pack cases: 4" in notes
    assert "does not generate fixtures" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_executable_coverage_blocks_missing_pack_link(
    repo_root,
    tmp_path,
):
    payload = load_json(repo_root / MANIFEST_PATH)
    payload["fixtures"][0]["linked_pack_case_ids"] = ["missing-pack-case.v0_1"]
    broken_manifest_path = write_json(tmp_path / "broken-executable-manifest.json", payload)

    report, _ = run_labor_employment_executable_coverage_audit(
        manifest_path=broken_manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "broken-le-executable-coverage",
    )

    assert report.status == "blocked_labor_employment_executable_coverage"
    assert any(
        check.check_id == "executable_pack_links_exist" and check.status == "failed"
        for check in report.checks
    )


def test_labor_employment_executable_coverage_rejects_pack_path_outside_repo(
    repo_root,
    tmp_path,
):
    outside_pack = write_json(tmp_path / "outside-pack.json", load_json(repo_root / PACK_PATH))

    with pytest.raises(ValueError, match="escapes repo root"):
        run_labor_employment_executable_coverage_audit(
            manifest_path=repo_root / MANIFEST_PATH,
            pack_path=outside_pack,
            repo_root=repo_root,
            out_dir=tmp_path / "pack-escape",
        )


def test_labor_employment_executable_coverage_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-executable-coverage",
            "--manifest",
            str(repo_root / MANIFEST_PATH),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-executable-coverage-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-executable-coverage-cli"
        / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_executable_coverage_ready_for_review"
    assert report["coverage_state"] == "partial_executable_coverage"
    assert report["missing_executable_pack_case_count"] == 4
    assert '"fixture_generation_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
