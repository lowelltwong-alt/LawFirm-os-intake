from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_fixture_family_pack import (
    LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
    run_labor_employment_fixture_family_pack_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentSyntheticFixtureFamilyPack,
    LaborEmploymentSyntheticFixtureFamilyPackReport,
)
from lawfirm_os_intake.util import load_json, write_json


PACK_PATH = "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
FACT_NEEDS_PATH = "config/labor-employment-budget-fact-needs.yaml"


def test_labor_employment_fixture_family_pack_covers_required_matrix(repo_root, tmp_path):
    report, run_dir = run_labor_employment_fixture_family_pack_audit(
        pack_path=repo_root / PACK_PATH,
        fact_needs_path=repo_root / FACT_NEEDS_PATH,
        out_dir=tmp_path / "le-fixture-family-pack",
    )
    persisted = LaborEmploymentSyntheticFixtureFamilyPackReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_fixture_family_pack_ready_for_review"
    assert persisted.case_count == 32
    assert persisted.required_family_count == 8
    assert persisted.required_variant_count == 4
    assert persisted.complete_family_variant_count == 32
    assert persisted.missing_family_variant_count == 0
    assert persisted.missing_fact_need_ids == []
    assert persisted.missing_critical_fact_need_ids == []
    assert persisted.missing_budget_driver_dimensions == []
    assert persisted.blocked_case_count > 0
    assert persisted.range_only_case_count > 0
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.fixture_generation_authorized is False
    assert persisted.calibration_approved is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False


def test_labor_employment_fixture_family_pack_cases_are_synthetic_holdouts(repo_root):
    pack = LaborEmploymentSyntheticFixtureFamilyPack.model_validate(
        load_json(repo_root / PACK_PATH)
    )

    assert {case.variant for case in pack.cases} == set(pack.required_variants)
    assert {case.family for case in pack.cases} == set(pack.required_families)
    assert all(case.data_origin == "synthetic" for case in pack.cases)
    assert all(case.candidate_only is True for case in pack.cases)
    assert all(case.holdout_excluded_from_prompt_assembly is True for case in pack.cases)
    assert all(case.external_writes_performed is False for case in pack.cases)
    assert all(case.silent_learning_performed is False for case in pack.cases)
    adversarial = [case for case in pack.cases if case.variant == "adversarial"]
    assert len(adversarial) == len(pack.required_families)
    assert all(case.missing_critical_fact_ids for case in adversarial)


def test_labor_employment_fixture_family_pack_blocks_missing_variant(
    repo_root,
    tmp_path,
):
    payload = load_json(repo_root / PACK_PATH)
    payload["cases"] = [
        case for case in payload["cases"] if case["case_id"] != "le-wage-hour-adversarial.v0_1"
    ]
    broken_pack = tmp_path / "broken-le-pack.json"
    write_json(broken_pack, payload)

    report, _ = run_labor_employment_fixture_family_pack_audit(
        pack_path=broken_pack,
        fact_needs_path=repo_root / FACT_NEEDS_PATH,
        out_dir=tmp_path / "broken-report",
    )

    assert report.status == "blocked_by_labor_employment_fixture_family_pack"
    assert report.missing_family_variant_count == 1
    assert any(
        check.check_id == "family_variant_matrix_complete"
        and check.status == "failed"
        and "wage_hour_flsa_state:adversarial" in check.blocking_refs
        for check in report.checks
    )


def test_labor_employment_fixture_family_pack_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-fixture-family-pack",
            "--pack",
            str(repo_root / PACK_PATH),
            "--fact-needs",
            str(repo_root / FACT_NEEDS_PATH),
            "--out-dir",
            str(tmp_path / "le-fixture-family-pack-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-fixture-family-pack-cli"
        / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_fixture_family_pack_ready_for_review"
    assert report["case_count"] == 32
    assert report["missing_family_variant_count"] == 0
    assert '"fixture_generation_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
