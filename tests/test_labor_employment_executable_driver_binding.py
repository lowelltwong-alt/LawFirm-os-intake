from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_executable_driver_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_driver_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.models import LaborEmploymentExecutableDriverBindingReport
from lawfirm_os_intake.util import load_json, write_json


EXECUTABLE_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
BINDING_MANIFEST_PATH = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)


def _run_fact_binding_chain(repo_root, tmp_path):
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
    return executable_run_dir, fact_binding_run_dir


def test_labor_employment_executable_driver_binding_maps_fact_gaps_to_budget_drivers(
    repo_root,
    tmp_path,
):
    executable_run_dir, fact_binding_run_dir = _run_fact_binding_chain(repo_root, tmp_path)

    report, run_dir = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        executable_fact_binding_report_path=(
            fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-driver-binding",
    )
    persisted = LaborEmploymentExecutableDriverBindingReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_executable_driver_bindings_ready_for_review"
    assert persisted.case_count == 27
    assert persisted.failed_case_count == 0
    assert persisted.driver_binding_count == 135
    assert persisted.source_bound_driver_count == 135
    assert persisted.unbound_driver_count == 0
    assert persisted.critical_driver_block_count == 22
    assert persisted.critical_driver_review_only_count == 43
    assert persisted.missing_driver_dimensions == []
    assert set(persisted.covered_driver_dimensions) == set(persisted.required_driver_dimensions)
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(case.status == "passed" for case in persisted.cases)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    cases = {case.executable_fixture_id: case for case in persisted.cases}
    wage_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-wage-hour-clean.executable.v0_1"].driver_bindings
    }
    assert wage_clean["wage_hour_volume"].matched_fact_ids == [
        "wage_hour_pay_period_and_employee_volume"
    ]
    discrimination_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-discrimination-harassment-clean.executable.v0_1"].driver_bindings
    }
    assert discrimination_clean["expert_vendor_needs"].matched_fact_ids == [
        "expert_and_vendor_needs"
    ]
    discrimination_messy = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-discrimination-harassment-messy-thread.executable.v0_1"
        ].driver_bindings
    }
    assert set(discrimination_messy) == {
        "party_topology",
        "administrative_exhaustion",
        "forum_arbitration",
        "employment_timeline",
        "esi_discovery",
        "deposition_plan",
        "policy_contract_documents",
    }
    assert discrimination_messy["party_topology"].critical_driver_review_only is True
    assert discrimination_messy["employment_timeline"].critical_driver_review_only is True
    assert discrimination_messy["esi_discovery"].critical_driver_review_only is True
    assert discrimination_messy["deposition_plan"].critical_driver_review_only is True
    assert discrimination_messy["forum_arbitration"].critical_driver_block is False
    assert discrimination_messy["policy_contract_documents"].critical_driver_block is False
    assert (
        cases[
            "le-discrimination-harassment-messy-thread.executable.v0_1"
        ].critical_driver_block_count
        == 0
    )
    wage_messy = {
        binding.driver_dimension: binding
        for binding in cases["le-wage-hour-messy-thread.executable.v0_1"].driver_bindings
    }
    assert set(wage_messy) == {
        "party_topology",
        "class_collective_scope",
        "damages_exposure",
        "wage_hour_volume",
        "esi_discovery",
        "expert_vendor_needs",
    }
    assert wage_messy["party_topology"].critical_driver_review_only is True
    assert wage_messy["class_collective_scope"].critical_driver_review_only is True
    assert wage_messy["esi_discovery"].critical_driver_review_only is True
    assert wage_messy["wage_hour_volume"].critical_driver_review_only is False
    assert wage_messy["expert_vendor_needs"].critical_driver_review_only is False
    assert wage_messy["wage_hour_volume"].critical_driver_block is False
    assert cases["le-wage-hour-messy-thread.executable.v0_1"].critical_driver_block_count == 0
    wage_adversarial = {
        binding.driver_dimension: binding
        for binding in cases["le-wage-hour-adversarial.executable.v0_1"].driver_bindings
    }
    assert set(wage_adversarial) == {
        "party_topology",
        "claim_family",
        "damages_exposure",
        "wage_hour_volume",
        "expert_vendor_needs",
        "carrier_guideline_rate_context",
    }
    assert wage_adversarial["party_topology"].critical_driver_block is True
    assert wage_adversarial["carrier_guideline_rate_context"].critical_driver_block is True
    assert wage_adversarial["claim_family"].critical_driver_review_only is True
    assert wage_adversarial["wage_hour_volume"].critical_driver_block is False
    assert wage_adversarial["wage_hour_volume"].matched_fact_ids == [
        "wage_hour_pay_period_and_employee_volume"
    ]
    assert cases["le-wage-hour-adversarial.executable.v0_1"].critical_driver_block_count == 2
    restrictive = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-restrictive-covenant-missing-attachment.executable.v0_1"
        ].driver_bindings
    }
    assert "esi_custodians_and_sources" in restrictive["esi_discovery"].matched_fact_ids
    assert restrictive["expert_vendor_needs"].exception_label_count == 1
    restrictive_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-restrictive-covenant-clean.executable.v0_1"].driver_bindings
    }
    assert set(restrictive_clean) == {
        "forum_arbitration",
        "employment_timeline",
        "damages_exposure",
        "esi_discovery",
        "expert_vendor_needs",
        "policy_contract_documents",
    }
    assert restrictive_clean["employment_timeline"].critical_driver_review_only is True
    assert restrictive_clean["damages_exposure"].critical_driver_review_only is True
    assert restrictive_clean["esi_discovery"].critical_driver_review_only is True
    assert restrictive_clean["expert_vendor_needs"].matched_fact_ids == ["expert_and_vendor_needs"]
    assert cases["le-restrictive-covenant-clean.executable.v0_1"].critical_driver_block_count == 0
    restrictive_messy = {
        binding.driver_dimension: binding
        for binding in cases["le-restrictive-covenant-messy-thread.executable.v0_1"].driver_bindings
    }
    assert set(restrictive_messy) == {
        "party_topology",
        "forum_arbitration",
        "esi_discovery",
        "deposition_plan",
        "expert_vendor_needs",
        "policy_contract_documents",
    }
    assert restrictive_messy["party_topology"].critical_driver_review_only is True
    assert restrictive_messy["esi_discovery"].critical_driver_review_only is True
    assert restrictive_messy["deposition_plan"].critical_driver_review_only is True
    assert restrictive_messy["expert_vendor_needs"].critical_driver_block is False
    assert restrictive_messy["policy_contract_documents"].matched_fact_ids == [
        "policy_handbook_contract_documents"
    ]
    assert cases["le-restrictive-covenant-messy-thread.executable.v0_1"].driver_binding_count == 6
    assert (
        cases["le-restrictive-covenant-messy-thread.executable.v0_1"].critical_driver_block_count
        == 0
    )
    restrictive_adversarial = {
        binding.driver_dimension: binding
        for binding in cases["le-restrictive-covenant-adversarial.executable.v0_1"].driver_bindings
    }
    assert set(restrictive_adversarial) == {
        "party_topology",
        "claim_family",
        "forum_arbitration",
        "damages_exposure",
        "esi_discovery",
        "policy_contract_documents",
    }
    assert restrictive_adversarial["party_topology"].critical_driver_block is True
    assert restrictive_adversarial["party_topology"].matched_fact_ids == [
        "employee_claimant_identity",
        "employer_or_defendant_identity",
    ]
    assert restrictive_adversarial["claim_family"].critical_driver_review_only is True
    assert restrictive_adversarial["damages_exposure"].critical_driver_review_only is True
    assert restrictive_adversarial["policy_contract_documents"].critical_driver_block is False
    assert (
        cases["le-restrictive-covenant-adversarial.executable.v0_1"].critical_driver_block_count
        == 1
    )
    admin = {
        binding.driver_dimension: binding
        for binding in cases["le-admin-exhaustion-clean.executable.v0_1"].driver_bindings
    }
    assert admin["administrative_exhaustion"].matched_fact_ids == [
        "administrative_exhaustion_and_agency_record"
    ]
    assert admin["employment_timeline"].matched_fact_ids == [
        "administrative_exhaustion_and_agency_record"
    ]
    assert cases["le-admin-exhaustion-clean.executable.v0_1"].critical_driver_block_count == 0
    admin_missing = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-admin-exhaustion-missing-attachment.executable.v0_1"
        ].driver_bindings
    }
    assert set(admin_missing) == {
        "administrative_exhaustion",
        "forum_arbitration",
        "employment_timeline",
    }
    assert admin_missing["employment_timeline"].critical_driver_block is True
    assert admin_missing["administrative_exhaustion"].critical_driver_block is False
    assert admin_missing["forum_arbitration"].critical_driver_block is False
    assert (
        cases["le-admin-exhaustion-missing-attachment.executable.v0_1"].critical_driver_block_count
        == 1
    )
    retaliation_clean = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-clean.executable.v0_1"
        ].driver_bindings
    }
    assert set(retaliation_clean) == {
        "party_topology",
        "forum_arbitration",
        "employment_timeline",
        "damages_exposure",
        "esi_discovery",
        "deposition_plan",
        "expert_vendor_needs",
        "policy_contract_documents",
    }
    assert retaliation_clean["party_topology"].critical_driver_review_only is True
    assert retaliation_clean["employment_timeline"].critical_driver_review_only is True
    assert retaliation_clean["damages_exposure"].critical_driver_review_only is True
    assert retaliation_clean["deposition_plan"].critical_driver_review_only is True
    assert (
        cases[
            "le-retaliation-wrongful-termination-clean.executable.v0_1"
        ].critical_driver_block_count
        == 0
    )
    retaliation_missing = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"
        ].driver_bindings
    }
    assert set(retaliation_missing) == {
        "party_topology",
        "representation_posture",
        "employment_timeline",
        "esi_discovery",
        "policy_contract_documents",
        "carrier_guideline_rate_context",
    }
    assert retaliation_missing["party_topology"].critical_driver_block is True
    assert retaliation_missing["representation_posture"].critical_driver_block is True
    assert retaliation_missing["carrier_guideline_rate_context"].critical_driver_block is True
    assert retaliation_missing["employment_timeline"].critical_driver_review_only is True
    assert (
        cases[
            "le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"
        ].critical_driver_block_count
        == 3
    )
    ada_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-ada-fmla-clean.executable.v0_1"].driver_bindings
    }
    assert ada_clean["employment_timeline"].critical_driver_review_only is True
    assert ada_clean["deposition_plan"].critical_driver_review_only is True
    assert ada_clean["expert_vendor_needs"].matched_fact_ids == ["expert_and_vendor_needs"]
    assert ada_clean["policy_contract_documents"].matched_fact_ids == [
        "policy_handbook_contract_documents"
    ]
    assert cases["le-ada-fmla-clean.executable.v0_1"].critical_driver_block_count == 0
    ada_adversarial = {
        binding.driver_dimension: binding
        for binding in cases["le-ada-fmla-adversarial.executable.v0_1"].driver_bindings
    }
    assert ada_adversarial["party_topology"].critical_driver_block is True
    assert ada_adversarial["representation_posture"].critical_driver_block is True
    assert set(ada_adversarial["party_topology"].matched_fact_ids) == {
        "employee_claimant_identity",
        "employer_or_defendant_identity",
        "prospective_client_payer_carrier_posture",
    }
    epli_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-epli-carrier-clean.executable.v0_1"].driver_bindings
    }
    assert epli_clean["party_topology"].critical_driver_review_only is True
    assert epli_clean["representation_posture"].critical_driver_review_only is True
    assert epli_clean["carrier_guideline_rate_context"].critical_driver_review_only is True
    assert epli_clean["carrier_guideline_rate_context"].critical_driver_block is False
    assert epli_clean["expert_vendor_needs"].matched_fact_ids == ["expert_and_vendor_needs"]
    epli_messy = {
        binding.driver_dimension: binding
        for binding in cases["le-epli-carrier-messy-thread.executable.v0_1"].driver_bindings
    }
    assert epli_messy["party_topology"].critical_driver_review_only is True
    assert epli_messy["representation_posture"].critical_driver_review_only is True
    assert epli_messy["deposition_plan"].critical_driver_review_only is True
    assert epli_messy["carrier_guideline_rate_context"].critical_driver_review_only is True
    assert all(
        not epli_messy[dimension].critical_driver_block
        for dimension in [
            "party_topology",
            "representation_posture",
            "deposition_plan",
            "carrier_guideline_rate_context",
        ]
    )
    assert epli_messy["forum_arbitration"].matched_fact_ids == [
        "forum_removed_and_arbitration_posture"
    ]
    epli_adversarial = {
        binding.driver_dimension: binding
        for binding in cases["le-epli-carrier-adversarial.executable.v0_1"].driver_bindings
    }
    assert epli_adversarial["party_topology"].critical_driver_block is True
    assert epli_adversarial["representation_posture"].critical_driver_block is True
    assert epli_adversarial["claim_family"].critical_driver_review_only is True
    assert epli_adversarial["carrier_guideline_rate_context"].critical_driver_block is True
    assert set(epli_adversarial["party_topology"].matched_fact_ids) == {
        "employee_claimant_identity",
        "employer_or_defendant_identity",
        "prospective_client_payer_carrier_posture",
    }
    assert set(epli_adversarial["carrier_guideline_rate_context"].matched_fact_ids) == {
        "carrier_guideline_and_rate_source",
        "prospective_client_payer_carrier_posture",
    }
    class_clean = {
        binding.driver_dimension: binding
        for binding in cases["le-class-collective-clean.executable.v0_1"].driver_bindings
    }
    assert class_clean["class_collective_scope"].critical_driver_review_only is True
    assert class_clean["wage_hour_volume"].matched_fact_ids == [
        "wage_hour_pay_period_and_employee_volume"
    ]
    assert class_clean["damages_exposure"].critical_driver_review_only is True
    class_messy = {
        binding.driver_dimension: binding
        for binding in cases["le-class-collective-messy-thread.executable.v0_1"].driver_bindings
    }
    assert class_messy["class_collective_scope"].critical_driver_review_only is True
    assert class_messy["esi_discovery"].critical_driver_review_only is True
    assert class_messy["expert_vendor_needs"].matched_fact_ids == [
        "expert_and_vendor_needs",
        "wage_hour_pay_period_and_employee_volume",
    ]
    class_missing = {
        binding.driver_dimension: binding
        for binding in cases[
            "le-class-collective-missing-attachment.executable.v0_1"
        ].driver_bindings
    }
    assert set(class_missing) == {
        "party_topology",
        "class_collective_scope",
        "forum_arbitration",
        "damages_exposure",
        "wage_hour_volume",
        "esi_discovery",
        "expert_vendor_needs",
        "policy_contract_documents",
    }
    assert class_missing["party_topology"].critical_driver_block is True
    assert class_missing["class_collective_scope"].critical_driver_block is True
    assert class_missing["wage_hour_volume"].matched_fact_ids == [
        "wage_hour_pay_period_and_employee_volume"
    ]
    assert class_missing["forum_arbitration"].matched_fact_ids == [
        "forum_removed_and_arbitration_posture"
    ]
    assert class_missing["policy_contract_documents"].matched_fact_ids == [
        "policy_handbook_contract_documents"
    ]

    notes = (run_dir / "labor_employment_executable_driver_binding_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not resolve driver values" in notes
    assert "write Lake/SQLite records" in notes
    assert not list(run_dir.rglob("*.sqlite"))
    assert not list(run_dir.rglob("*.db"))


def test_labor_employment_executable_driver_binding_blocks_missing_focus_dimension(
    repo_root,
    tmp_path,
    monkeypatch,
):
    executable_run_dir, fact_binding_run_dir = _run_fact_binding_chain(repo_root, tmp_path)
    import lawfirm_os_intake.labor_employment_executable_driver_binding as driver_binding

    monkeypatch.setattr(
        driver_binding,
        "REQUIRED_DRIVER_DIMENSIONS",
        [*driver_binding.REQUIRED_DRIVER_DIMENSIONS, "claim_family"],
    )
    patched_driver_fact_ids = dict(driver_binding.DRIVER_FACT_IDS)
    patched_driver_fact_ids.pop("claim_family")
    monkeypatch.setattr(driver_binding, "DRIVER_FACT_IDS", patched_driver_fact_ids)

    report, _ = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        executable_fact_binding_report_path=(
            fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "blocked-le-executable-driver-binding",
    )

    assert report.status == "blocked_by_labor_employment_executable_driver_bindings"
    assert report.missing_driver_dimensions == ["claim_family"]
    assert any(
        check.check_id == "required_driver_focus_dimensions_covered" and check.status == "failed"
        for check in report.checks
    )


def test_labor_employment_executable_driver_binding_cli_writes_candidate_report(
    repo_root,
    tmp_path,
    capsys,
):
    executable_run_dir, fact_binding_run_dir = _run_fact_binding_chain(repo_root, tmp_path)

    exit_code = main(
        [
            "audit-labor-employment-executable-driver-binding",
            "--executable-fixture-report",
            str(executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME),
            "--executable-fact-binding-report",
            str(fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-executable-driver-binding-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = load_json(
        tmp_path
        / "le-executable-driver-binding-cli"
        / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
    )

    assert exit_code == 0
    assert report["status"] == "labor_employment_executable_driver_bindings_ready_for_review"
    assert report["case_count"] == 27
    assert report["missing_driver_dimensions"] == []
    assert '"budget_amount_output_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out


def test_labor_employment_executable_driver_binding_rejects_pack_outside_repo(
    repo_root,
    tmp_path,
):
    executable_run_dir, fact_binding_run_dir = _run_fact_binding_chain(repo_root, tmp_path)
    outside_pack = write_json(
        tmp_path / "outside-pack.json",
        load_json(
            repo_root
            / "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
        ),
    )

    try:
        run_labor_employment_executable_driver_binding_audit(
            executable_fixture_report_path=(
                executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
            ),
            executable_fact_binding_report_path=(
                fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
            ),
            repo_root=repo_root,
            pack_path=outside_pack,
            out_dir=tmp_path / "pack-escape",
        )
    except ValueError as exc:
        assert "escapes repo root" in str(exc)
    else:
        raise AssertionError("expected pack path escape to fail")
