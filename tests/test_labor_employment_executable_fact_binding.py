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
    assert persisted.case_count == 16
    assert persisted.failed_case_count == 0
    assert persisted.fact_binding_count == 49
    assert persisted.critical_fact_binding_count == 23
    assert persisted.missing_critical_fact_count == 8
    assert persisted.source_present_confirmation_fact_count == 33
    assert persisted.source_present_unresolved_critical_driver_count == 1
    assert persisted.evidence_bound_fact_count == 49
    assert persisted.exception_bound_fact_count == 12
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
    wage_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-wage-hour-clean.executable.v0_1"].fact_bindings
    }
    assert wage_clean_bindings["wage_hour_pay_period_and_employee_volume"].binding_state == (
        "source_bound_gap_candidate"
    )
    discrimination_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-discrimination-harassment-clean.executable.v0_1"].fact_bindings
    }
    assert discrimination_clean_bindings["expert_and_vendor_needs"].binding_state == (
        "source_bound_gap_candidate"
    )
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
    assert discrimination_bindings["carrier_guideline_and_rate_source"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert (
        discrimination_bindings["carrier_guideline_and_rate_source"].blocks_precise_budget is True
    )
    assert discrimination_bindings["carrier_guideline_and_rate_source"].matched_source_ids == [
        "syn-le-discrimination-guidelines-missing-001"
    ]
    assert (
        discrimination_bindings["administrative_exhaustion_and_agency_record"].binding_state
        == "source_and_exception_bound_gap_candidate"
    )
    epli_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-epli-carrier-clean.executable.v0_1"].fact_bindings
    }
    assert epli_clean_bindings["prospective_client_payer_carrier_posture"].required_level == (
        "critical"
    )
    assert (
        epli_clean_bindings["prospective_client_payer_carrier_posture"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        epli_clean_bindings["prospective_client_payer_carrier_posture"].blocks_precise_budget
        is False
    )
    assert epli_clean_bindings["carrier_guideline_and_rate_source"].fact_resolution_state == (
        "source_present_needs_confirmation"
    )
    assert epli_clean_bindings["carrier_guideline_and_rate_source"].blocks_precise_budget is False
    assert epli_clean_bindings["expert_and_vendor_needs"].binding_state == (
        "source_bound_gap_candidate"
    )
    epli_messy_bindings = {
        binding.fact_id: binding
        for binding in cases["le-epli-carrier-messy-thread.executable.v0_1"].fact_bindings
    }
    assert (
        epli_messy_bindings["prospective_client_payer_carrier_posture"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        epli_messy_bindings["joint_employer_or_affiliate_structure"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert epli_messy_bindings["carrier_guideline_and_rate_source"].fact_resolution_state == (
        "source_present_needs_confirmation"
    )
    assert all(
        epli_messy_bindings[fact_id].blocks_precise_budget is False
        for fact_id in [
            "prospective_client_payer_carrier_posture",
            "joint_employer_or_affiliate_structure",
            "carrier_guideline_and_rate_source",
        ]
    )
    assert epli_messy_bindings["forum_removed_and_arbitration_posture"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert epli_messy_bindings["forum_removed_and_arbitration_posture"].required_level == (
        "important"
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
    restrictive_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-restrictive-covenant-missing-attachment.executable.v0_1"
        ].fact_bindings
    }
    assert restrictive_bindings["esi_custodians_and_sources"].binding_state == (
        "source_and_exception_bound_gap_candidate"
    )
    assert restrictive_bindings["esi_custodians_and_sources"].required_level == "critical"
    assert restrictive_bindings["esi_custodians_and_sources"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert restrictive_bindings["esi_custodians_and_sources"].matched_source_ids == [
        "syn-le-restrictive-covenant-device-scope-missing-001"
    ]
    admin_bindings = {
        binding.fact_id: binding
        for binding in cases["le-admin-exhaustion-clean.executable.v0_1"].fact_bindings
    }
    assert admin_bindings["administrative_exhaustion_and_agency_record"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert admin_bindings["forum_removed_and_arbitration_posture"].binding_state == (
        "source_bound_gap_candidate"
    )
    ada_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-ada-fmla-clean.executable.v0_1"].fact_bindings
    }
    assert ada_clean_bindings["relevant_employment_timeline"].required_level == "critical"
    assert (
        ada_clean_bindings["relevant_employment_timeline"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert ada_clean_bindings["anticipated_depositions"].required_level == "critical"
    assert ada_clean_bindings["anticipated_depositions"].blocks_precise_budget is False
    assert ada_clean_bindings["policy_handbook_contract_documents"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert ada_clean_bindings["expert_and_vendor_needs"].binding_state == (
        "source_bound_gap_candidate"
    )
    ada_adversarial_bindings = {
        binding.fact_id: binding
        for binding in cases["le-ada-fmla-adversarial.executable.v0_1"].fact_bindings
    }
    assert ada_adversarial_bindings["employee_claimant_identity"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert ada_adversarial_bindings["employer_or_defendant_identity"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert ada_adversarial_bindings[
        "prospective_client_payer_carrier_posture"
    ].matched_exception_labels == ["prompt_injection_source_content"]
    assert all(binding.blocks_precise_budget for binding in ada_adversarial_bindings.values())
    class_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-class-collective-clean.executable.v0_1"].fact_bindings
    }
    assert class_clean_bindings["class_collective_or_group_scope"].required_level == "critical"
    assert (
        class_clean_bindings["class_collective_or_group_scope"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert class_clean_bindings["class_collective_or_group_scope"].blocks_precise_budget is False
    assert class_clean_bindings["wage_hour_pay_period_and_employee_volume"].binding_state == (
        "source_bound_gap_candidate"
    )
    class_messy_bindings = {
        binding.fact_id: binding
        for binding in cases["le-class-collective-messy-thread.executable.v0_1"].fact_bindings
    }
    assert (
        class_messy_bindings["class_collective_or_group_scope"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert class_messy_bindings["esi_custodians_and_sources"].required_level == "critical"
    assert (
        class_messy_bindings["esi_custodians_and_sources"].fact_resolution_state
        == "source_present_needs_confirmation"
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
    assert len(manifest.bindings) == 16


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
    assert "administrative_exhaustion_and_agency_record:missing_source_signal_terms" in (
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
    assert report["case_count"] == 16
    assert report["fact_binding_count"] == 49
    assert report["missing_critical_fact_count"] == 8
    assert report["source_present_confirmation_fact_count"] == 33
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
