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
    assert persisted.case_count == 27
    assert persisted.failed_case_count == 0
    assert persisted.fact_binding_count == 104
    assert persisted.critical_fact_binding_count == 55
    assert persisted.missing_critical_fact_count == 20
    assert persisted.source_present_confirmation_fact_count == 65
    assert persisted.source_present_unresolved_critical_driver_count == 2
    assert persisted.evidence_bound_fact_count == 104
    assert persisted.exception_bound_fact_count == 26
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
    discrimination_messy_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-discrimination-harassment-messy-thread.executable.v0_1"
        ].fact_bindings
    }
    assert set(discrimination_messy_bindings) == {
        "individual_supervisor_or_manager_defendants",
        "administrative_exhaustion_and_agency_record",
        "relevant_employment_timeline",
        "esi_custodians_and_sources",
        "forum_removed_and_arbitration_posture",
        "policy_handbook_contract_documents",
    }
    assert (
        discrimination_messy_bindings[
            "individual_supervisor_or_manager_defendants"
        ].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        discrimination_messy_bindings["relevant_employment_timeline"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        discrimination_messy_bindings["esi_custodians_and_sources"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        discrimination_messy_bindings["forum_removed_and_arbitration_posture"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert (
        discrimination_messy_bindings["policy_handbook_contract_documents"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert all(
        binding.blocks_precise_budget is False for binding in discrimination_messy_bindings.values()
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
    wage_messy_bindings = {
        binding.fact_id: binding
        for binding in cases["le-wage-hour-messy-thread.executable.v0_1"].fact_bindings
    }
    assert set(wage_messy_bindings) == {
        "class_collective_or_group_scope",
        "wage_hour_pay_period_and_employee_volume",
        "esi_custodians_and_sources",
        "expert_and_vendor_needs",
    }
    assert (
        wage_messy_bindings["class_collective_or_group_scope"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        wage_messy_bindings["wage_hour_pay_period_and_employee_volume"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert "18 hourly employees" in (
        wage_messy_bindings["wage_hour_pay_period_and_employee_volume"].matched_source_signal_terms
    )
    assert "42 hourly employees" in (
        wage_messy_bindings["wage_hour_pay_period_and_employee_volume"].matched_source_signal_terms
    )
    assert all(binding.blocks_precise_budget is False for binding in wage_messy_bindings.values())
    wage_adversarial_bindings = {
        binding.fact_id: binding
        for binding in cases["le-wage-hour-adversarial.executable.v0_1"].fact_bindings
    }
    assert set(wage_adversarial_bindings) == {
        "employee_claimant_identity",
        "employer_or_defendant_identity",
        "claims_and_causes_of_action",
        "wage_hour_pay_period_and_employee_volume",
        "carrier_guideline_and_rate_source",
    }
    assert (
        wage_adversarial_bindings["employee_claimant_identity"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        wage_adversarial_bindings["employer_or_defendant_identity"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        wage_adversarial_bindings["claims_and_causes_of_action"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        wage_adversarial_bindings["wage_hour_pay_period_and_employee_volume"].fact_resolution_state
        == "source_present_unresolved_driver"
    )
    assert wage_adversarial_bindings[
        "wage_hour_pay_period_and_employee_volume"
    ].matched_exception_labels == ["prompt_injection_source_content"]
    assert (
        wage_adversarial_bindings["carrier_guideline_and_rate_source"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert wage_adversarial_bindings[
        "carrier_guideline_and_rate_source"
    ].matched_exception_labels == ["prompt_injection_source_content"]
    assert (
        sum(1 for binding in wage_adversarial_bindings.values() if binding.blocks_precise_budget)
        == 3
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
    epli_adversarial_bindings = {
        binding.fact_id: binding
        for binding in cases["le-epli-carrier-adversarial.executable.v0_1"].fact_bindings
    }
    assert epli_adversarial_bindings["employee_claimant_identity"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert epli_adversarial_bindings["employer_or_defendant_identity"].fact_resolution_state == (
        "missing_critical_fact"
    )
    assert (
        epli_adversarial_bindings["prospective_client_payer_carrier_posture"].fact_resolution_state
        == "source_present_unresolved_critical_driver"
    )
    assert epli_adversarial_bindings[
        "prospective_client_payer_carrier_posture"
    ].matched_exception_labels == ["prompt_injection_source_content"]
    assert epli_adversarial_bindings["claims_and_causes_of_action"].fact_resolution_state == (
        "source_present_needs_confirmation"
    )
    assert epli_adversarial_bindings[
        "carrier_guideline_and_rate_source"
    ].matched_exception_labels == ["prompt_injection_source_content"]
    assert epli_adversarial_bindings["carrier_guideline_and_rate_source"].blocks_precise_budget
    assert (
        sum(1 for binding in epli_adversarial_bindings.values() if binding.blocks_precise_budget)
        == 4
    )
    retaliation_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-clean.executable.v0_1"
        ].fact_bindings
    }
    assert set(retaliation_bindings) == {
        "individual_supervisor_or_manager_defendants",
        "relevant_employment_timeline",
        "damages_categories_and_exposure",
        "policy_handbook_contract_documents",
        "anticipated_depositions",
        "forum_removed_and_arbitration_posture",
        "expert_and_vendor_needs",
    }
    assert retaliation_bindings["individual_supervisor_or_manager_defendants"].required_level == (
        "critical"
    )
    assert (
        retaliation_bindings["individual_supervisor_or_manager_defendants"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        retaliation_bindings["relevant_employment_timeline"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert retaliation_bindings["damages_categories_and_exposure"].required_level == "critical"
    assert retaliation_bindings["anticipated_depositions"].required_level == "critical"
    assert all(binding.blocks_precise_budget is False for binding in retaliation_bindings.values())
    retaliation_missing_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"
        ].fact_bindings
    }
    assert set(retaliation_missing_bindings) == {
        "prospective_client_payer_carrier_posture",
        "carrier_guideline_and_rate_source",
        "policy_handbook_contract_documents",
        "relevant_employment_timeline",
    }
    assert (
        retaliation_missing_bindings[
            "prospective_client_payer_carrier_posture"
        ].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        retaliation_missing_bindings["carrier_guideline_and_rate_source"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        retaliation_missing_bindings["policy_handbook_contract_documents"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert (
        retaliation_missing_bindings["relevant_employment_timeline"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert retaliation_missing_bindings[
        "prospective_client_payer_carrier_posture"
    ].matched_source_ids == ["syn-le-retaliation-carrier-assignment-missing-001"]
    assert retaliation_missing_bindings["carrier_guideline_and_rate_source"].matched_source_ids == [
        "syn-le-retaliation-guideline-rate-missing-001"
    ]
    assert retaliation_missing_bindings[
        "policy_handbook_contract_documents"
    ].matched_source_ids == ["syn-le-retaliation-discipline-policy-missing-001"]
    assert all(
        "source_missing" in binding.matched_exception_labels
        for fact_id, binding in retaliation_missing_bindings.items()
        if fact_id != "relevant_employment_timeline"
    )
    retaliation_messy_bindings = {
        binding.fact_id: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-messy-thread.executable.v0_1"
        ].fact_bindings
    }
    assert retaliation_messy_bindings["forum_removed_and_arbitration_posture"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert retaliation_messy_bindings["forum_removed_and_arbitration_posture"].required_level == (
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
    restrictive_clean_bindings = {
        binding.fact_id: binding
        for binding in cases["le-restrictive-covenant-clean.executable.v0_1"].fact_bindings
    }
    assert set(restrictive_clean_bindings) == {
        "forum_removed_and_arbitration_posture",
        "relevant_employment_timeline",
        "damages_categories_and_exposure",
        "policy_handbook_contract_documents",
        "esi_custodians_and_sources",
        "expert_and_vendor_needs",
    }
    assert (
        restrictive_clean_bindings["relevant_employment_timeline"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert restrictive_clean_bindings["relevant_employment_timeline"].required_level == "critical"
    assert (
        restrictive_clean_bindings["damages_categories_and_exposure"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert restrictive_clean_bindings["esi_custodians_and_sources"].required_level == "critical"
    restrictive_messy_bindings = {
        binding.fact_id: binding
        for binding in cases["le-restrictive-covenant-messy-thread.executable.v0_1"].fact_bindings
    }
    assert set(restrictive_messy_bindings) == {
        "joint_employer_or_affiliate_structure",
        "forum_removed_and_arbitration_posture",
        "esi_custodians_and_sources",
        "expert_and_vendor_needs",
        "policy_handbook_contract_documents",
    }
    assert all(
        binding.binding_state == "source_bound_gap_candidate"
        for binding in restrictive_messy_bindings.values()
    )
    assert all(
        binding.fact_resolution_state == "source_present_needs_confirmation"
        for binding in restrictive_messy_bindings.values()
    )
    assert restrictive_messy_bindings["joint_employer_or_affiliate_structure"].required_level == (
        "critical"
    )
    assert restrictive_messy_bindings["esi_custodians_and_sources"].required_level == "critical"
    assert (
        restrictive_messy_bindings["expert_and_vendor_needs"].recommended_budget_treatment
        == "candidate_range_budget_after_review"
    )
    restrictive_adversarial_bindings = {
        binding.fact_id: binding
        for binding in cases["le-restrictive-covenant-adversarial.executable.v0_1"].fact_bindings
    }
    assert set(restrictive_adversarial_bindings) == {
        "employee_claimant_identity",
        "employer_or_defendant_identity",
        "claims_and_causes_of_action",
        "forum_removed_and_arbitration_posture",
        "damages_categories_and_exposure",
        "policy_handbook_contract_documents",
    }
    assert (
        restrictive_adversarial_bindings["employee_claimant_identity"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        restrictive_adversarial_bindings["employer_or_defendant_identity"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        restrictive_adversarial_bindings["policy_handbook_contract_documents"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert (
        restrictive_adversarial_bindings["claims_and_causes_of_action"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert (
        restrictive_adversarial_bindings["damages_categories_and_exposure"].fact_resolution_state
        == "source_present_needs_confirmation"
    )
    assert all(
        binding.binding_state == "source_bound_gap_candidate"
        for binding in restrictive_adversarial_bindings.values()
    )
    assert restrictive_clean_bindings["expert_and_vendor_needs"].binding_state == (
        "source_bound_gap_candidate"
    )
    assert all(
        binding.blocks_precise_budget is False for binding in restrictive_clean_bindings.values()
    )
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
    admin_missing_bindings = {
        binding.fact_id: binding
        for binding in cases["le-admin-exhaustion-missing-attachment.executable.v0_1"].fact_bindings
    }
    assert set(admin_missing_bindings) == {
        "administrative_exhaustion_and_agency_record",
        "relevant_employment_timeline",
        "forum_removed_and_arbitration_posture",
    }
    assert (
        admin_missing_bindings["administrative_exhaustion_and_agency_record"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert (
        admin_missing_bindings["relevant_employment_timeline"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert (
        admin_missing_bindings["forum_removed_and_arbitration_posture"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert admin_missing_bindings[
        "administrative_exhaustion_and_agency_record"
    ].matched_source_ids == ["syn-le-admin-exhaustion-agency-record-missing-001"]
    assert admin_missing_bindings["relevant_employment_timeline"].matched_source_ids == [
        "syn-le-admin-exhaustion-timeline-missing-001"
    ]
    assert admin_missing_bindings["forum_removed_and_arbitration_posture"].matched_source_ids == [
        "syn-le-admin-exhaustion-forum-removal-missing-001"
    ]
    assert all(
        "source_missing" in binding.matched_exception_labels
        for binding in admin_missing_bindings.values()
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
    class_missing_bindings = {
        binding.fact_id: binding
        for binding in cases["le-class-collective-missing-attachment.executable.v0_1"].fact_bindings
    }
    assert set(class_missing_bindings) == {
        "class_collective_or_group_scope",
        "wage_hour_pay_period_and_employee_volume",
        "forum_removed_and_arbitration_posture",
        "policy_handbook_contract_documents",
    }
    assert class_missing_bindings["class_collective_or_group_scope"].required_level == "critical"
    assert (
        class_missing_bindings["class_collective_or_group_scope"].fact_resolution_state
        == "missing_critical_fact"
    )
    assert class_missing_bindings["class_collective_or_group_scope"].blocks_precise_budget is True
    assert class_missing_bindings["class_collective_or_group_scope"].matched_source_ids == [
        "syn-le-class-collective-class-list-missing-001"
    ]
    assert (
        class_missing_bindings["wage_hour_pay_period_and_employee_volume"].fact_resolution_state
        == "missing_noncritical_fact"
    )
    assert class_missing_bindings[
        "wage_hour_pay_period_and_employee_volume"
    ].matched_source_ids == ["syn-le-class-collective-payroll-export-missing-001"]
    assert class_missing_bindings["forum_removed_and_arbitration_posture"].matched_source_ids == [
        "syn-le-class-collective-arbitration-policy-missing-001"
    ]
    assert class_missing_bindings["policy_handbook_contract_documents"].matched_source_ids == [
        "syn-le-class-collective-arbitration-policy-missing-001"
    ]
    assert all(
        binding.binding_state == "source_and_exception_bound_gap_candidate"
        for binding in class_missing_bindings.values()
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
    assert len(manifest.bindings) == 27


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
    assert report["case_count"] == 27
    assert report["fact_binding_count"] == 104
    assert report["missing_critical_fact_count"] == 20
    assert report["source_present_confirmation_fact_count"] == 65
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
