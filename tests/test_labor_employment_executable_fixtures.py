import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentExecutableFixtureAuditReport,
    LaborEmploymentExecutableFixtureManifest,
)
from lawfirm_os_intake.util import load_json, write_json


MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)


def test_labor_employment_executable_fixtures_run_preflight_and_preserve_boundaries(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_executable_fixture_audit(
        manifest_path=repo_root / MANIFEST_PATH,
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fixtures",
    )
    persisted = LaborEmploymentExecutableFixtureAuditReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_executable_fixtures_ready_for_review"
    assert persisted.fixture_count == 12
    assert persisted.preflight_executed_count == 12
    assert persisted.failed_case_count == 0
    assert persisted.missing_pack_link_count == 0
    assert persisted.missing_source_signal_count == 0
    assert persisted.missing_expected_exception_label_count == 0
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(case.status == "passed" for case in persisted.cases)
    assert all(case.preflight_packet_ref for case in persisted.cases)
    assert all(case.budget_fact_audit_required is True for case in persisted.cases)
    assert all(case.budget_amount_output_authorized is False for case in persisted.cases)
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
    assert cases["le-wage-hour-missing-attachment.executable.v0_1"].missing_source_count == 2
    assert cases["le-wage-hour-clean.executable.v0_1"].missing_source_count == 0
    assert (
        cases["le-wage-hour-clean.executable.v0_1"].expected_budget_treatment
        == "candidate_range_budget_after_review"
    )
    assert cases["le-discrimination-harassment-clean.executable.v0_1"].missing_source_count == 0
    assert "critic_date_or_deadline_requires_review" in (
        cases["le-discrimination-harassment-clean.executable.v0_1"].exception_labels
    )
    assert cases["le-epli-carrier-missing-attachment.executable.v0_1"].missing_source_count == 2
    assert cases["le-epli-carrier-clean.executable.v0_1"].missing_source_count == 0
    assert "critic_role_candidates_ambiguous" in (
        cases["le-epli-carrier-clean.executable.v0_1"].exception_labels
    )
    assert cases["le-epli-carrier-messy-thread.executable.v0_1"].duplicate_source_count == 1
    assert "duplicate_source_detected" in (
        cases["le-epli-carrier-messy-thread.executable.v0_1"].exception_labels
    )
    assert "critic_role_candidates_ambiguous" in (
        cases["le-epli-carrier-messy-thread.executable.v0_1"].exception_labels
    )
    epli_packet = load_json(cases["le-epli-carrier-clean.executable.v0_1"].preflight_packet_ref)
    epli_roles = {
        party["name"]: {role["role"] for role in party["role_candidates"]}
        for party in epli_packet["party_candidates"]
    }
    assert {"insurance_carrier", "payer", "instructing_source"} <= epli_roles["Granite Shield EPLI"]
    assert {"insured", "employer_or_defendant", "prospective_represented_client"} <= epli_roles[
        "Brightline Foods Inc."
    ]
    assert "claimant" in epli_roles["Talia Nguyen"]
    assert (
        cases[
            "le-discrimination-harassment-missing-attachment.executable.v0_1"
        ].missing_source_count
        == 3
    )
    assert "source_missing" in (
        cases["le-discrimination-harassment-missing-attachment.executable.v0_1"].exception_labels
    )
    assert (
        cases[
            "le-retaliation-wrongful-termination-messy-thread.executable.v0_1"
        ].duplicate_source_count
        == 1
    )
    assert "duplicate_source_detected" in (
        cases["le-retaliation-wrongful-termination-messy-thread.executable.v0_1"].exception_labels
    )
    assert (
        cases["le-restrictive-covenant-missing-attachment.executable.v0_1"].missing_source_count
        == 3
    )
    assert "source_missing" in (
        cases["le-restrictive-covenant-missing-attachment.executable.v0_1"].exception_labels
    )
    assert (
        cases["le-admin-exhaustion-clean.executable.v0_1"].expected_budget_treatment
        == "candidate_range_budget_after_review"
    )
    assert "critic_date_or_deadline_requires_review" in (
        cases["le-admin-exhaustion-clean.executable.v0_1"].exception_labels
    )
    assert "prompt_injection_source_content" not in (
        cases["le-admin-exhaustion-clean.executable.v0_1"].exception_labels
    )
    assert cases["le-ada-fmla-missing-thread.executable.v0_1"].duplicate_source_count == 1
    assert "prompt_injection_source_content" in (
        cases["le-class-collective-adversarial.executable.v0_1"].exception_labels
    )
    assert "prohibited_transition_attempted_budget_submitted" in (
        cases["le-class-collective-adversarial.executable.v0_1"].exception_labels
    )

    notes = (run_dir / "labor_employment_executable_fixtures_report.md").read_text(encoding="utf-8")
    assert "Budget fact audit required: True" in notes
    assert "does not produce an amount budget" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_executable_manifest_is_synthetic_only(repo_root):
    manifest = LaborEmploymentExecutableFixtureManifest.model_validate(
        load_json(repo_root / MANIFEST_PATH)
    )

    assert manifest.synthetic_only is True
    assert manifest.candidate_only is True
    assert manifest.fixture_generation_authorized is False
    assert manifest.calibration_approved is False
    assert manifest.lake_write_performed is False
    assert manifest.sqlite_write_performed is False
    assert manifest.external_writes_performed is False
    assert {fixture.data_origin for fixture in manifest.fixtures} == {"synthetic"}
    assert all(fixture.holdout_excluded_from_prompt_assembly for fixture in manifest.fixtures)
    assert all(fixture.expected_source_signal_terms for fixture in manifest.fixtures)


def test_labor_employment_executable_fixture_audit_blocks_missing_pack_link(
    repo_root,
    tmp_path,
):
    payload = load_json(repo_root / MANIFEST_PATH)
    payload["fixtures"][0]["linked_pack_case_ids"] = ["missing-pack-case.v0_1"]
    broken_manifest_path = write_json(tmp_path / "broken-executable-manifest.json", payload)

    report, _ = run_labor_employment_executable_fixture_audit(
        manifest_path=broken_manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "broken-le-executable-fixtures",
    )

    assert report.status == "blocked_by_labor_employment_executable_fixtures"
    assert report.failed_case_count == 1
    assert report.missing_pack_link_count == 1
    assert any(
        check.check_id == "pack_case_links_valid" and check.status == "failed"
        for check in report.checks
    )


def test_labor_employment_executable_fixture_audit_rejects_pack_path_outside_repo(
    repo_root,
    tmp_path,
):
    outside_pack = write_json(
        tmp_path / "outside-pack.json",
        load_json(
            repo_root
            / "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
        ),
    )

    with pytest.raises(ValueError, match="escapes repo root"):
        run_labor_employment_executable_fixture_audit(
            manifest_path=repo_root / MANIFEST_PATH,
            pack_path=outside_pack,
            repo_root=repo_root,
            out_dir=tmp_path / "pack-escape",
        )


def test_labor_employment_executable_fixtures_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-executable-fixtures",
            "--manifest",
            str(repo_root / MANIFEST_PATH),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-executable-fixtures-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-executable-fixtures-cli"
        / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_executable_fixtures_ready_for_review"
    assert report["fixture_count"] == 12
    assert report["preflight_executed_count"] == 12
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
