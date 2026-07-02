import json


UI_ROOT = "apps/legal-intake-budget"


def test_legal_intake_budget_ui_required_files_exist(repo_root):
    required = [
        "README.md",
        "CLAUDE_DESIGN_BRIEF.md",
        "package.json",
        "index.html",
        "src/App.tsx",
        "src/styles.css",
        "src/types.ts",
        "src/data-contract.ts",
        "src/fixtures/demo-run-manifest.json",
        "src/fixtures/demo-labor-employment-qa-matrix-report.json",
    ]

    for relative_path in required:
        assert (repo_root / UI_ROOT / relative_path).is_file()


def test_legal_intake_budget_ui_has_no_publish_or_deploy_scripts(repo_root):
    package = json.loads((repo_root / UI_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})

    assert package["private"] is True
    assert "deploy" not in scripts
    assert "publish" not in scripts
    assert "postinstall" not in scripts


def test_legal_intake_budget_ui_data_contract_lists_required_artifacts(repo_root):
    contract = (repo_root / UI_ROOT / "src/data-contract.ts").read_text(encoding="utf-8")

    expected_artifacts = [
        "intake_preflight_packet.json",
        "human_gate_status_report.json",
        "conflict_search_seed_packet.json",
        "legal_budget_proposal.json",
        "matter_opening_readiness.json",
        "budget_submission_guard_report.json",
        "exception_lake_handoff_manifest.json",
        "run_ledger_integrity_report.json",
        "budget_coherence_report.json",
        "synthetic_qa_bundle_report.json",
        "synthetic_fixture_depth_audit_report.json",
        "budget_calibration_readiness_report.json",
        "budget_calibration_starter_pack_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_fixture_family_pack_report.json",
        "labor_employment_executable_fixtures_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_executable_fact_binding_report.json",
        "labor_employment_executable_driver_binding_report.json",
        "labor_employment_budget_fact_gold_report.json",
        "budget_human_review_packet.json",
        "carrier_rejection_decision_ledger_report.json",
        "budget_actual_variance_ledger_report.json",
        "public_source_methodology_report.json",
        "public_data_cache_audit_report.json",
    ]

    for artifact in expected_artifacts:
        assert artifact in contract
    assert "networkCallsAllowed: false" in contract
    assert "mutationCommandsAllowed: false" in contract
    assert "exceptionLakeWritesAllowed: false" in contract
    assert "sqliteWritesAllowed: false" in contract
    assert "budgetSubmissionAllowed: false" in contract
    assert "matterOpeningAllowed: false" in contract


def test_legal_intake_budget_demo_manifest_is_read_only_and_candidate_only(repo_root):
    manifest = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-run-manifest.json").read_text(encoding="utf-8")
    )

    flags = manifest["boundaryFlags"]
    assert flags["readOnly"] is True
    assert flags["localJsonOnly"] is True
    assert flags["networkCallsAllowed"] is False
    assert flags["mutationCommandsAllowed"] is False
    assert flags["exceptionLakeWritesAllowed"] is False
    assert flags["sqliteWritesAllowed"] is False
    assert flags["publicRuntimeIngestionAllowed"] is False
    assert flags["budgetSubmissionAllowed"] is False
    assert flags["matterOpeningAllowed"] is False
    assert all(artifact["candidateOnly"] is True for artifact in manifest["artifacts"])
    assert all(artifact["externalWritesPerformed"] is False for artifact in manifest["artifacts"])
    assert manifest["qualityGates"]
    assert {
        "budget_coherence",
        "synthetic_qa_bundle",
        "synthetic_fixture_depth",
        "budget_calibration_readiness",
        "labor_employment_qa_matrix",
        "labor_employment_fixture_family_pack",
        "labor_employment_executable_fixtures",
        "labor_employment_executable_coverage",
        "labor_employment_executable_fact_binding",
        "labor_employment_executable_driver_binding",
        "labor_employment_budget_fact_gold",
        "full_pytest",
        "smoke_demo",
    } <= {gate["gateId"] for gate in manifest["qualityGates"]}
    assert all(gate["evidenceFile"] for gate in manifest["qualityGates"])


def test_legal_intake_budget_demo_le_matrix_is_synthetic_and_no_write(repo_root):
    matrix = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-labor-employment-qa-matrix-report.json"
        ).read_text(encoding="utf-8")
    )
    cases = {case["case_id"]: case for case in matrix["cases"]}

    assert matrix["status"] == "labor_employment_qa_matrix_ready_for_review"
    assert matrix["case_count"] == len(matrix["cases"]) == 2
    assert matrix["failed_case_count"] == 0
    assert matrix["candidate_only"] is True
    assert matrix["non_authoritative"] is True
    assert matrix["synthetic_only"] is True
    assert matrix["budget_amount_output_authorized"] is False
    assert matrix["budget_submission_authorized"] is False
    assert matrix["lake_write_performed"] is False
    assert matrix["sqlite_write_performed"] is False
    assert matrix["external_writes_performed"] is False
    assert matrix["silent_learning_performed"] is False
    assert (
        cases["critical_fact_gaps_block_amount_budget"]["actual_budget_gate_effect"]
        == "block_amount_budget_before_proposal"
    )
    assert cases["critical_fact_gaps_block_amount_budget"]["critical_gap_count"] > 0
    assert (
        cases["ready_critical_facts_still_range_only"]["actual_budget_gate_effect"]
        == "allow_range_or_hours_only_pending_review"
    )
    assert cases["ready_critical_facts_still_range_only"]["critical_gap_count"] == 0


def test_legal_intake_budget_ui_disclaims_mutating_authority(repo_root):
    readme = (repo_root / UI_ROOT / "README.md").read_text(encoding="utf-8")
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (repo_root / UI_ROOT / "src/styles.css").read_text(encoding="utf-8")

    assert "read-only" in readme.lower()
    assert "local JSON" in readme
    assert "Exception Lake writer" in readme
    assert "Local JSON only" in app
    assert "QA Gates" in app
    assert "L&amp;E Budget Fact QA" in app
    assert "assertLaborEmploymentQAMatrixReport" in app
    assert "failingQualityGates" in app
    assert "grid-template-columns" in styles
