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
        "src/fixtures/demo-synthetic-confidence-summary-report.json",
        "src/fixtures/demo-poc-qa-triage-report.json",
        "src/fixtures/demo-synthetic-qa-blocker-report.json",
        "src/fixtures/demo-synthetic-qa-bundle-report.json",
        "src/fixtures/demo-synthetic-qa-review-outcome-report.json",
        "src/fixtures/demo-synthetic-qa-review-run-report.json",
        "src/fixtures/demo-ui-review-data-bundle.json",
        "src/fixtures/demo-rust-fixture-boundary-report.json",
        "src/fixtures/demo-rust-fixture-manifest-report.json",
        "src/fixtures/demo-validation-suite-evidence-report.json",
        "src/fixtures/demo-matter-linking-preflight-report.json",
        "src/fixtures/demo-matter-linking-qa-gate-report.json",
        "src/fixtures/demo-matter-linking-review-outcome-report.json",
        "src/fixtures/demo-labor-employment-qa-matrix-report.json",
        "src/fixtures/demo-labor-employment-executable-coverage-report.json",
        "src/fixtures/demo-labor-employment-blocked-driver-impact-review-report.json",
        "src/fixtures/demo-labor-employment-budget-output-expectations-report.json",
        "src/fixtures/demo-labor-employment-budget-qa-gate-report.json",
        "src/fixtures/demo-labor-employment-budget-learning-fixtures-report.json",
        "src/fixtures/demo-labor-employment-budget-outcome-replay-builder-binding-report.json",
        "src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json",
        "src/fixtures/demo-budget-learning-loop-report.json",
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
        "synthetic_qa_review_run_report.json",
        "rust_fixture_boundary_report.json",
        "rust_fixture_manifest_report.json",
        "synthetic_confidence_summary_report.json",
        "poc_qa_triage_report.json",
        "synthetic_qa_blocker_report.json",
        "matter_linking_preflight_report.json",
        "matter_linking_qa_gate_report.json",
        "matter_linking_review_outcome_report.json",
        "synthetic_fixture_depth_audit_report.json",
        "budget_calibration_readiness_report.json",
        "budget_calibration_starter_pack_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_fixture_family_pack_report.json",
        "labor_employment_executable_fixtures_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_executable_fact_binding_report.json",
        "labor_employment_executable_driver_binding_report.json",
        "labor_employment_executable_driver_impact_report.json",
        "labor_employment_driver_impact_review_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_budget_qa_gate_report.json",
        "labor_employment_budget_learning_fixtures_report.json",
        "labor_employment_budget_outcome_replay_readiness_report.json",
        "labor_employment_budget_outcome_replay_execution_report.json",
        "labor_employment_budget_outcome_replay_builder_binding_report.json",
        "labor_employment_budget_outcome_replay_confidence_status_report.json",
        "labor_employment_budget_fact_gold_report.json",
        "validation_suite_evidence_report.json",
        "budget_human_review_packet.json",
        "carrier_rejection_decision_ledger_report.json",
        "budget_actual_variance_ledger_report.json",
        "budget_learning_loop_report.json",
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
        "synthetic_qa_review_run",
        "synthetic_confidence_summary",
        "poc_qa_triage",
        "synthetic_qa_blocker_report",
        "matter_linking_preflight",
        "matter_linking_qa_gate",
        "synthetic_fixture_depth",
        "budget_calibration_readiness",
        "labor_employment_qa_matrix",
        "labor_employment_fixture_family_pack",
        "labor_employment_executable_fixtures",
        "labor_employment_executable_coverage",
        "labor_employment_executable_fact_binding",
        "labor_employment_executable_driver_binding",
        "labor_employment_executable_driver_impact",
        "labor_employment_driver_impact_review",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
        "labor_employment_budget_learning_fixtures",
        "labor_employment_budget_outcome_replay_readiness",
        "labor_employment_budget_outcome_replay_execution",
        "labor_employment_budget_outcome_replay_builder_binding",
        "labor_employment_budget_outcome_replay_confidence_status",
        "budget_learning_loop",
        "labor_employment_budget_fact_gold",
        "validation_suite_evidence",
        "full_pytest",
        "smoke_demo",
    } <= {gate["gateId"] for gate in manifest["qualityGates"]}
    assert all(gate["evidenceFile"] for gate in manifest["qualityGates"])


def test_legal_intake_budget_demo_ui_review_data_bundle_is_local_and_no_write(repo_root):
    bundle = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-ui-review-data-bundle.json").read_text(
            encoding="utf-8"
        )
    )
    detail_reports = {report["file_name"]: report for report in bundle["detail_reports"]}

    assert bundle["status"] == "ready_for_review"
    assert bundle["detail_report_count"] == len(bundle["detail_reports"]) == 21
    assert bundle["required_detail_report_count"] == 13
    assert bundle["present_detail_report_count"] == 21
    assert bundle["missing_required_detail_report_count"] == 0
    assert bundle["external_write_report_count"] == 0
    assert bundle["candidate_only"] is True
    assert bundle["synthetic_only"] is True
    assert bundle["non_authoritative"] is True
    assert bundle["local_json_only"] is True
    assert bundle["budget_amount_output_authorized"] is False
    assert bundle["budget_submission_authorized"] is False
    assert bundle["lake_write_performed"] is False
    assert bundle["sqlite_write_performed"] is False
    assert bundle["external_writes_performed"] is False
    assert bundle["silent_learning_performed"] is False
    assert {
        "ui_review_manifest.json",
        "synthetic_confidence_summary_report.json",
        "synthetic_qa_blocker_report.json",
        "synthetic_qa_review_outcome_report.json",
        "synthetic_qa_review_run_report.json",
        "rust_fixture_boundary_report.json",
        "rust_fixture_manifest_report.json",
        "matter_linking_preflight_report.json",
        "matter_linking_qa_gate_report.json",
        "matter_linking_review_outcome_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_budget_qa_gate_report.json",
        "labor_employment_budget_learning_fixtures_report.json",
        "labor_employment_budget_outcome_replay_readiness_report.json",
        "labor_employment_budget_outcome_replay_execution_report.json",
        "labor_employment_budget_outcome_replay_builder_binding_report.json",
        "labor_employment_budget_outcome_replay_confidence_status_report.json",
        "budget_learning_loop_report.json",
    } <= set(detail_reports)
    assert all(report["present"] is True for report in bundle["detail_reports"])
    assert all(report["source_sha256"].startswith("sha256:") for report in bundle["detail_reports"])
    assert all(report["external_writes_performed"] is False for report in bundle["detail_reports"])


def test_legal_intake_budget_budget_learning_loop_fixture_is_review_only(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-budget-learning-loop-report.json").read_text(
            encoding="utf-8"
        )
    )
    actuals = report["actuals"]
    carrier = report["carrier_rejections"]
    learning_gate = report["reviewed_learning_gate"]

    assert report["status"] == "budget_learning_loop_ready_for_review"
    assert report["run_id"]
    assert report["preflight_packet_id"]
    assert report["budget_proposal_id"]
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["not_authorized_for_lake_write"] is True
    assert report["not_authorized_for_sqlite_write"] is True
    assert report["not_authorized_for_budget_submission"] is True
    assert report["not_authorized_for_matter_opening"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["appeal_submission_performed"] is False
    assert report["silent_learning_performed"] is False
    assert (
        actuals["ledger_entry_count"]
        == actuals["phase_event_count"]
        + actuals["code_event_count"]
        + actuals["revision_context_event_count"]
    )
    assert (
        carrier["expected_response_count"]
        == carrier["reconciled_response_count"] + carrier["missing_response_count"]
    )
    assert (
        learning_gate["candidate_count"]
        == learning_gate["carrier_learning_candidate_count"]
        + learning_gate["budget_revision_candidate_count"]
        + learning_gate["budget_actual_variance_candidate_count"]
    )
    assert learning_gate["reviewed_outcome_required"] is True
    assert learning_gate["shadow_eval_required"] is True
    assert len(report["lifecycle_lanes"]) >= 4
    assert all(lane["evidence_refs"] for lane in report["lifecycle_lanes"])
    assert all(lane["candidate_exception_lake_labels"] for lane in report["lifecycle_lanes"])


def test_legal_intake_budget_demo_synthetic_qa_review_run_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-review-run-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "synthetic_qa_review_run_ready"
    assert report["step_count"] == len(report["steps"]) == 30
    assert report["failed_step_count"] == 0
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert all(step["status"] == "passed" for step in report["steps"])
    assert {
        "budget_coherence",
        "matter_linking_preflight",
        "matter_linking_qa_gate",
        "matter_linking_review_outcome",
        "matter_linking_weak_only_holdout",
        "synthetic_qa_bundle",
        "ui_review_manifest",
        "ui_review_data_bundle",
        "rust_fixture_boundary",
        "rust_fixture_manifest",
        "synthetic_confidence_summary",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
        "labor_employment_budget_learning_fixtures",
        "labor_employment_budget_outcome_replay_readiness",
        "labor_employment_budget_outcome_replay_execution",
        "labor_employment_budget_outcome_replay_builder_binding",
        "labor_employment_budget_outcome_replay_confidence_status",
        "budget_learning_loop",
    } <= {step["step_id"] for step in report["steps"]}


def test_legal_intake_budget_demo_rust_fixture_boundary_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-rust-fixture-boundary-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["checker"] == "fixture-boundary-checker"
    assert report["status"] == "passed"
    assert report["failure_count"] == 0
    assert report["checked_json_file_count"] >= 20
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_rust_fixture_manifest_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-rust-fixture-manifest-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["scanner"] == "fixture-manifest-scanner"
    assert report["status"] == "passed"
    assert report["manifest_sha256"].startswith("sha256:")
    assert report["failure_count"] == 0
    assert report["checked_json_file_count"] >= 20
    assert report["parsed_json_file_count"] == report["checked_json_file_count"]
    assert report["parse_error_count"] == 0
    assert report["skipped_file_count"] >= 1
    assert any(
        item["reason"] == "ui_review_data_bundle_wrapper_circular_hash"
        for item in report["skipped_files"]
    )
    assert report["total_byte_count"] > 0
    assert report["files"]
    assert all(file["sha256"].startswith("sha256:") for file in report["files"])
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["silent_learning_performed"] is False


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


def test_legal_intake_budget_demo_executable_coverage_is_complete_and_no_write(repo_root):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-executable-coverage-report.json"
        ).read_text(encoding="utf-8")
    )
    families = {family["family"]: family for family in report["family_coverage"]}
    detail_bundle = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-ui-review-data-bundle.json").read_text(
            encoding="utf-8"
        )
    )
    detail_reports = {report["report_kind"]: report for report in detail_bundle["detail_reports"]}

    assert report["status"] == "labor_employment_executable_coverage_ready_for_review"
    assert report["coverage_state"] == "complete_executable_coverage"
    assert report["pack_case_count"] == 32
    assert report["executable_fixture_count"] == 31
    assert report["covered_pack_case_count"] == 32
    assert report["missing_executable_pack_case_count"] == 0
    assert report["covered_family_count"] == 8
    assert report["missing_family_count"] == 0
    assert report["covered_family_variant_count"] == len(report["covered_pack_case_ids"]) == 32
    assert (
        report["missing_family_variant_count"]
        == len(report["missing_executable_pack_case_ids"])
        == 0
    )
    assert "discrimination_harassment:clean" not in report["missing_family_variant_refs"]
    assert "discrimination_harassment:messy_thread" not in (report["missing_family_variant_refs"])
    assert "discrimination_harassment:adversarial" not in report["missing_family_variant_refs"]
    assert "wage_hour_flsa_state:clean" not in report["missing_family_variant_refs"]
    assert "wage_hour_flsa_state:messy_thread" not in report["missing_family_variant_refs"]
    assert "wage_hour_flsa_state:adversarial" not in report["missing_family_variant_refs"]
    assert "retaliation_wrongful_termination:clean" not in report["missing_family_variant_refs"]
    assert (
        "retaliation_wrongful_termination:missing_attachment"
        not in report["missing_family_variant_refs"]
    )
    assert (
        "retaliation_wrongful_termination:adversarial" not in report["missing_family_variant_refs"]
    )
    assert "restrictive_covenant_trade_secret:clean" not in (report["missing_family_variant_refs"])
    assert (
        "restrictive_covenant_trade_secret:adversarial"
        not in (report["missing_family_variant_refs"])
    )
    assert (
        "administrative_exhaustion_agency_record:missing_attachment"
        not in report["missing_family_variant_refs"]
    )
    assert (
        "administrative_exhaustion_agency_record:messy_thread"
        not in report["missing_family_variant_refs"]
    )
    assert (
        "administrative_exhaustion_agency_record:adversarial"
        not in report["missing_family_variant_refs"]
    )
    assert (
        "class_collective_paga_representative:clean" not in (report["missing_family_variant_refs"])
    )
    assert (
        "class_collective_paga_representative:messy_thread"
        not in (report["missing_family_variant_refs"])
    )
    assert (
        "class_collective_paga_representative:missing_attachment"
        not in (report["missing_family_variant_refs"])
    )
    assert families["ada_fmla_accommodation_leave"]["covered_case_count"] == 4
    assert families["ada_fmla_accommodation_leave"]["missing_variants"] == []
    assert families["epli_carrier_assignment"]["covered_case_count"] == 4
    assert families["epli_carrier_assignment"]["missing_variants"] == []
    assert "le-epli-carrier-adversarial.v0_1" in report["covered_pack_case_ids"]
    assert families["discrimination_harassment"]["covered_case_count"] == 4
    assert families["discrimination_harassment"]["missing_variants"] == []
    assert "le-discrimination-harassment-messy-thread.v0_1" in (report["covered_pack_case_ids"])
    assert "le-discrimination-harassment-adversarial.v0_1" in (report["covered_pack_case_ids"])
    assert families["class_collective_paga_representative"]["covered_case_count"] == 4
    assert families["class_collective_paga_representative"]["missing_variants"] == []
    assert "le-class-collective-missing-attachment.v0_1" in report["covered_pack_case_ids"]
    assert families["administrative_exhaustion_agency_record"]["covered_case_count"] == 4
    assert families["administrative_exhaustion_agency_record"]["missing_variants"] == []
    assert "le-admin-exhaustion-clean.v0_1" in report["covered_pack_case_ids"]
    assert "le-admin-exhaustion-messy-thread.v0_1" in report["covered_pack_case_ids"]
    assert "le-admin-exhaustion-missing-attachment.v0_1" in report["covered_pack_case_ids"]
    assert "le-admin-exhaustion-adversarial.v0_1" in report["covered_pack_case_ids"]
    assert families["wage_hour_flsa_state"]["covered_case_count"] == 4
    assert families["wage_hour_flsa_state"]["missing_variants"] == []
    assert "le-wage-hour-messy-thread.v0_1" in report["covered_pack_case_ids"]
    assert "le-wage-hour-adversarial.v0_1" in report["covered_pack_case_ids"]
    assert families["restrictive_covenant_trade_secret"]["covered_case_count"] == 4
    assert families["restrictive_covenant_trade_secret"]["missing_variants"] == []
    assert "le-restrictive-covenant-clean.v0_1" in report["covered_pack_case_ids"]
    assert "le-restrictive-covenant-messy-thread.v0_1" in report["covered_pack_case_ids"]
    assert "le-restrictive-covenant-adversarial.v0_1" in report["covered_pack_case_ids"]
    assert (
        "le-retaliation-wrongful-termination-adversarial.v0_1" in (report["covered_pack_case_ids"])
    )
    assert all(check["status"] == "passed" for check in report["checks"])
    assert report["candidate_only"] is True
    assert report["non_authoritative"] is True
    assert report["synthetic_only"] is True
    assert report["human_review_required"] is True
    assert report["fixture_generation_authorized"] is False
    assert report["calibration_approved"] is False
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert detail_reports["labor_employment_executable_coverage"]["present"] is True
    assert detail_reports["labor_employment_executable_coverage"]["required"] is True
    assert detail_reports["labor_employment_executable_coverage"]["renderer"] == (
        "LaborEmploymentExecutableCoveragePanel"
    )


def test_legal_intake_budget_demo_blocked_driver_review_is_synthetic_and_no_write(repo_root):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-blocked-driver-impact-review-report.json"
        ).read_text(encoding="utf-8")
    )
    cases = {case["executable_fixture_id"]: case for case in report["case_reviews"]}

    assert report["status"] == "labor_employment_blocked_driver_impacts_ready_for_review"
    assert report["case_count"] == 31
    assert report["blocked_case_count"] == len(report["case_reviews"]) == 16
    assert report["nonblocking_case_count"] == 15
    assert report["blocker_fact_count"] == sum(
        case["blocker_fact_count"] for case in report["case_reviews"]
    )
    assert report["block_amount_budget_impact_count"] == sum(
        case["block_amount_budget_impact_count"] for case in report["case_reviews"]
    )
    assert report["candidate_only"] is True
    assert report["non_authoritative"] is True
    assert report["synthetic_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert (
        cases["le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"][
            "allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        "source_missing"
        in cases["le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-admin-exhaustion-missing-attachment.executable.v0_1"]["allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert cases["le-admin-exhaustion-missing-attachment.executable.v0_1"][
        "critical_driver_dimensions"
    ] == ["employment_timeline"]
    assert (
        "source_missing"
        in cases["le-admin-exhaustion-missing-attachment.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert "source_missing" in report["candidate_exception_lake_labels"]
    assert "prompt_injection_source_content" in report["candidate_exception_lake_labels"]
    assert (
        "labor_employment_critical_budget_fact_block" in (report["candidate_exception_lake_labels"])
    )
    assert all(case["allowed_budget_output"] == "blocked_amount_budget" for case in cases.values())
    assert all(case["amount_budget_blocked"] is True for case in cases.values())
    assert all(case["critical_driver_dimensions"] for case in cases.values())
    assert all(case["unblock_actions"] for case in cases.values())
    assert (
        "carrier_guideline_rate_context"
        in (
            cases["le-epli-carrier-missing-attachment.executable.v0_1"][
                "critical_driver_dimensions"
            ]
        )
    )
    assert (
        "prompt_injection_source_content"
        in (
            cases["le-class-collective-adversarial.executable.v0_1"][
                "candidate_exception_lake_labels"
            ]
        )
    )
    assert (
        "prompt_injection_source_content"
        in (cases["le-ada-fmla-adversarial.executable.v0_1"]["candidate_exception_lake_labels"])
    )
    assert (
        "prompt_injection_source_content"
        in (
            cases["le-discrimination-harassment-adversarial.executable.v0_1"][
                "candidate_exception_lake_labels"
            ]
        )
    )
    assert {"party_topology", "representation_posture", "carrier_guideline_rate_context"} <= set(
        cases["le-discrimination-harassment-adversarial.executable.v0_1"][
            "critical_driver_dimensions"
        ]
    )
    assert (
        "prompt_injection_source_content"
        in (cases["le-epli-carrier-adversarial.executable.v0_1"]["candidate_exception_lake_labels"])
    )
    assert {"party_topology", "representation_posture", "carrier_guideline_rate_context"} <= set(
        cases["le-epli-carrier-adversarial.executable.v0_1"]["critical_driver_dimensions"]
    )
    assert (
        "prompt_injection_source_content"
        in (
            cases["le-retaliation-wrongful-termination-adversarial.executable.v0_1"][
                "candidate_exception_lake_labels"
            ]
        )
    )
    assert {"party_topology", "representation_posture", "carrier_guideline_rate_context"} <= set(
        cases["le-retaliation-wrongful-termination-adversarial.executable.v0_1"][
            "critical_driver_dimensions"
        ]
    )
    assert (
        "prompt_injection_source_content"
        in (
            cases["le-admin-exhaustion-adversarial.executable.v0_1"][
                "candidate_exception_lake_labels"
            ]
        )
    )
    assert {"party_topology", "representation_posture", "carrier_guideline_rate_context"} <= set(
        cases["le-admin-exhaustion-adversarial.executable.v0_1"]["critical_driver_dimensions"]
    )
    assert (
        "source_missing"
        in (
            cases["le-class-collective-missing-attachment.executable.v0_1"][
                "candidate_exception_lake_labels"
            ]
        )
    )
    assert {"party_topology", "class_collective_scope"} <= set(
        cases["le-class-collective-missing-attachment.executable.v0_1"][
            "critical_driver_dimensions"
        ]
    )
    assert {"party_topology", "representation_posture"} <= set(
        cases["le-ada-fmla-adversarial.executable.v0_1"]["critical_driver_dimensions"]
    )
    assert all(check["status"] == "passed" for check in report["checks"])


def test_legal_intake_budget_demo_synthetic_confidence_summary_is_no_write(repo_root):
    report = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-synthetic-confidence-summary-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "synthetic_confidence_summary_ready_for_review"
    assert report["testing_readiness_state"] == "synthetic_qa_ready_pending_review"
    assert report["top_blockers"] == []
    assert report["qa_step_count"] == 30
    assert report["qa_failed_step_count"] == 0
    assert report["qa_missing_required_artifact_count"] == 0
    assert report["ui_detail_report_count"] == 21
    assert report["ui_present_detail_report_count"] == 21
    assert report["ui_missing_required_detail_report_count"] == 0
    assert report["display_banner"]["candidate_only"] is True
    assert report["display_banner"]["synthetic_only"] is True
    assert report["display_banner"]["not_production_ready"] is True
    assert report["display_banner"]["budget_submission_authorized"] is False
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert all(item["evidence_refs"] for item in report["readiness_items"])
    assert not list((repo_root / UI_ROOT / "src/fixtures").glob("*.sqlite"))
    assert not list((repo_root / UI_ROOT / "src/fixtures").glob("*.db"))


def test_legal_intake_budget_demo_poc_qa_triage_is_actionable_and_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-poc-qa-triage-report.json").read_text(
            encoding="utf-8"
        )
    )
    items = {item["item_id"]: item for item in report["items"]}

    assert report["status"] == "poc_qa_ready_for_review"
    assert report["item_count"] == len(report["items"]) == 11
    assert report["blocked_item_count"] == 0
    assert report["p0_blocked_item_count"] == 0
    assert report["needs_review_item_count"] == 6
    assert report["watch_item_count"] == 2
    assert report["passed_item_count"] == 3
    assert report["source_validation_suite_evidence_report_id"].startswith(
        "validation_suite_evidence_"
    )
    assert items["validation_evidence_not_fresh_in_ui_bundle"]["status"] == "passed"
    assert any(
        ref.endswith("validation_suite_evidence_report.json")
        or ref.endswith("demo-validation-suite-evidence-report.json")
        for ref in items["validation_evidence_not_fresh_in_ui_bundle"]["evidence_refs"]
    )
    assert items["matter_linking_requires_human_confirmation"]["status"] == "needs_review"
    assert items["budget_output_partition_visible"]["status"] == "needs_review"
    assert items["labor_employment_budget_qa_gate_ready"]["status"] == "needs_review"
    assert report["source_budget_qa_gate_report_id"].startswith("lebudgetqagate_")
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_matter_linking_exposes_weak_and_split_signals(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-matter-linking-preflight-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "matter_linking_preflight_resolved_candidate_requires_review"
    assert report["official_matter_number_status"] == "not_available"
    assert report["cluster_count"] == len(report["clusters"]) == 2
    assert report["high_evidence_candidate_count"] == 2
    assert report["weak_only_candidate_count"] == 0
    assert report["negative_split_evidence_required"] is True
    assert report["strong_negative_signal_count"] == 2
    assert report["source_count"] == len(report["source_hashes_by_id"]) == 6
    assert "same_sender" in report["weak_merge_signal_types"]
    assert "same_carrier" in report["weak_merge_signal_types"]
    assert all(
        cluster["source_bound_strong_support_present"] is True
        and cluster["weak_only_candidate"] is False
        and cluster["negative_split_evidence_required"] is True
        for cluster in report["clusters"]
    )
    assert report["budget_amount_output_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False


def test_legal_intake_budget_demo_matter_linking_qa_gate_covers_holdouts(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-matter-linking-qa-gate-report.json").read_text(
            encoding="utf-8"
        )
    )
    cases = {case["case_id"]: case for case in report["cases"]}

    assert report["status"] == "matter_linking_qa_gate_ready_for_review"
    assert report["case_count"] == len(report["cases"]) == 5
    assert report["failed_case_count"] == 0
    assert report["missing_coverage_tags"] == []
    assert report["observed_coverage_tag_count"] == report["required_coverage_tag_count"]
    assert {
        "ambiguous_same_sender_multi_case",
        "resolved_followup_split_candidate",
        "weak_only_followup_blocked",
        "resolved_single_candidate",
        "conflicting_identifier_blocked",
    } <= set(cases)
    assert cases["weak_only_followup_blocked"]["observed_status"] == (
        "blocked_matter_linking_preflight"
    )
    assert cases["conflicting_identifier_blocked"]["observed_status"] == (
        "blocked_matter_linking_preflight"
    )
    assert (
        "conflicting_identifiers_block_linking"
        in (cases["conflicting_identifier_blocked"]["observed_failed_check_ids"])
    )
    assert "matter_linking_qa_gate_candidate" in report["candidate_exception_lake_labels"]
    assert "no_lake_or_sqlite_write_from_matter_linking_qa_gate" in (report["required_next_gates"])
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_matter_linking_review_outcome_is_no_write(repo_root):
    report = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-matter-linking-review-outcome-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "matter_linking_review_outcome_recorded"
    assert report["overall_outcome"] == "confirm_split"
    assert report["source_cluster_count"] == 2
    assert report["reviewed_cluster_count"] == len(report["reviewed_cluster_ids"]) == 2
    assert report["unreviewed_cluster_count"] == 0
    assert report["unknown_cluster_count"] == 0
    assert report["split_decision_count"] == 1
    assert "matter_linking_confirmed_split_candidate" in (report["candidate_lake_event_labels"])
    assert (
        "principal_party_roles_still_require_confirmation"
        in (report["candidate_lake_event_labels"])
    )
    assert "append_only_matter_linking_review_outcome" in report["required_next_gates"]
    assert "no_budget_amount_until_cluster_and_roles_confirmed" in (report["required_next_gates"])
    assert report["append_only"] is True
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["conflict_conclusion_emitted"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_validation_suite_evidence_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-validation-suite-evidence-report.json").read_text(
            encoding="utf-8"
        )
    )
    steps = {step["step_id"]: step for step in report["steps"]}

    assert report["status"] == "validation_suite_passed"
    assert report["step_count"] == len(report["steps"]) == 7
    assert report["passed_step_count"] == 7
    assert report["failed_step_count"] == 0
    assert report["timed_out_step_count"] == 0
    assert report["policy_ref"] == "config/validation-runtime-policy.yaml"
    assert steps["full_pytest"]["status"] == "passed"
    assert steps["full_pytest"]["timeout_seconds"] >= 3600
    assert "scripts/run_full_pytest.py" in steps["full_pytest"]["evidence_refs"]
    assert steps["smoke_demo"]["status"] == "passed"
    assert "scripts/smoke_demo.sh" in steps["smoke_demo"]["evidence_refs"]
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_synthetic_qa_blocker_report_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-blocker-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "synthetic_qa_blocker_report_ready_for_review"
    assert report["row_count"] == len(report["rows"]) == 27
    assert report["failed_row_count"] == 0
    assert report["blocked_row_count"] == 0
    assert report["pending_review_row_count"] == 27
    assert report["blocked_action_count"] == 0
    assert report["needs_review_action_count"] == 27
    assert report["fixed_action_count"] == 0
    assert report["ready_action_count"] == 0
    assert report["review_queue_state"] == "needs_review"
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert {row["source"] for row in report["rows"]} == {"quality_gate", "readiness_item"}
    assert all(row["evidence_refs"] for row in report["rows"])
    assert all(row["action_state"] == "needs_review" for row in report["rows"])
    assert all(row["recommended_next_action"] for row in report["rows"])
    assert all(row["candidate_exception_lake_labels"] for row in report["rows"])
    assert all(row["notes"] for row in report["rows"])


def test_legal_intake_budget_demo_synthetic_qa_review_outcome_is_no_write(repo_root):
    report = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-review-outcome-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "synthetic_qa_review_outcome_recorded_pending_followup"
    assert report["source_row_count"] == 22
    assert report["reviewed_row_count"] == len(report["reviewed_row_ids"]) == 3
    assert report["unreviewed_row_count"] == len(report["unreviewed_row_ids"]) == 19
    assert report["decision_count"] == 3
    assert report["accepted_decision_count"] == 1
    assert report["needs_fix_decision_count"] == 1
    assert report["deferred_decision_count"] == 1
    assert report["unresolved_followup_count"] == len(report["required_followups"]) == 2
    assert report["append_only"] is True
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["not_authorized_for_calibration"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert (
        "synthetic_qa_review_outcome_recorded_candidate" in (report["candidate_lake_event_labels"])
    )
    assert all(report["required_next_actions"])


def test_legal_intake_budget_demo_budget_output_expectations_are_no_write(repo_root):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-output-expectations-report.json"
        ).read_text(encoding="utf-8")
    )
    cases = {case["executable_fixture_id"]: case for case in report["cases"]}

    assert report["status"] == "labor_employment_budget_output_expectations_ready_for_review"
    assert report["case_count"] == len(report["cases"]) == 31
    assert report["failed_case_count"] == 0
    assert report["blocked_amount_budget_case_count"] == 16
    assert report["range_or_hours_only_case_count"] == 5
    assert report["candidate_range_after_review_case_count"] == 10
    assert report["reviewed_nonblocking_case_count"] == 15
    assert report["blocked_review_case_count"] == 16
    assert report["candidate_only"] is True
    assert report["non_authoritative"] is True
    assert report["synthetic_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert "candidate_only_budget_review_required" in report["candidate_exception_lake_labels"]
    assert (
        cases["le-epli-carrier-missing-attachment.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-epli-carrier-missing-attachment.executable.v0_1"]["blocked_case_review_present"]
        is True
    )
    assert (
        cases["le-retaliation-wrongful-termination-clean.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-retaliation-wrongful-termination-clean.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-epli-carrier-clean.executable.v0_1"]["final_allowed_budget_output"]
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-ada-fmla-clean.executable.v0_1"]["final_allowed_budget_output"]
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-ada-fmla-clean.executable.v0_1"]["selected_for_reviewed_nonblocking_slice"]
        is True
    )
    assert (
        cases["le-ada-fmla-adversarial.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert cases["le-ada-fmla-adversarial.executable.v0_1"]["blocked_case_review_present"] is True
    assert (
        cases["le-discrimination-harassment-adversarial.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-discrimination-harassment-adversarial.executable.v0_1"][
            "blocked_case_review_present"
        ]
        is True
    )
    assert (
        "prompt_injection_source_content"
        in cases["le-discrimination-harassment-adversarial.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-class-collective-missing-attachment.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-class-collective-missing-attachment.executable.v0_1"][
            "blocked_case_review_present"
        ]
        is True
    )
    assert (
        cases["le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"][
            "blocked_case_review_present"
        ]
        is True
    )
    assert (
        "source_missing"
        in cases["le-retaliation-wrongful-termination-missing-attachment.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-admin-exhaustion-missing-attachment.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-admin-exhaustion-missing-attachment.executable.v0_1"][
            "blocked_case_review_present"
        ]
        is True
    )
    assert (
        cases["le-wage-hour-adversarial.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert cases["le-wage-hour-adversarial.executable.v0_1"]["blocked_case_review_present"] is True
    assert (
        "prompt_injection_source_content"
        in cases["le-wage-hour-adversarial.executable.v0_1"]["candidate_exception_lake_labels"]
    )
    assert (
        "source_missing"
        in cases["le-admin-exhaustion-missing-attachment.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-epli-carrier-adversarial.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-epli-carrier-adversarial.executable.v0_1"]["blocked_case_review_present"] is True
    )
    assert (
        cases["le-retaliation-wrongful-termination-adversarial.executable.v0_1"][
            "final_allowed_budget_output"
        ]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-retaliation-wrongful-termination-adversarial.executable.v0_1"][
            "blocked_case_review_present"
        ]
        is True
    )
    assert (
        "prompt_injection_source_content"
        in cases["le-retaliation-wrongful-termination-adversarial.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-admin-exhaustion-adversarial.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-admin-exhaustion-adversarial.executable.v0_1"]["blocked_case_review_present"]
        is True
    )
    assert (
        "prompt_injection_source_content"
        in cases["le-admin-exhaustion-adversarial.executable.v0_1"][
            "candidate_exception_lake_labels"
        ]
    )
    assert (
        cases["le-epli-carrier-messy-thread.executable.v0_1"]["final_allowed_budget_output"]
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-class-collective-clean.executable.v0_1"]["final_allowed_budget_output"]
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-class-collective-clean.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-class-collective-messy-thread.executable.v0_1"]["final_allowed_budget_output"]
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-class-collective-messy-thread.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-wage-hour-messy-thread.executable.v0_1"]["final_allowed_budget_output"]
        == "range_or_hours_only_pending_review"
    )
    assert (
        cases["le-wage-hour-messy-thread.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-admin-exhaustion-clean.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-admin-exhaustion-messy-thread.executable.v0_1"]["final_allowed_budget_output"]
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-admin-exhaustion-messy-thread.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert (
        cases["le-restrictive-covenant-clean.executable.v0_1"]["final_allowed_budget_output"]
        == "candidate_range_after_review_pending_human_review"
    )
    assert (
        cases["le-restrictive-covenant-clean.executable.v0_1"][
            "selected_for_reviewed_nonblocking_slice"
        ]
        is True
    )
    assert all(check["status"] == "passed" for check in report["checks"])


def test_legal_intake_budget_demo_labor_employment_budget_qa_gate_is_no_write(repo_root):
    report = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-labor-employment-budget-qa-gate-report.json"
        ).read_text(encoding="utf-8")
    )
    buckets = {bucket["output_state"]: bucket for bucket in report["output_state_buckets"]}

    assert report["status"] == "labor_employment_budget_qa_gate_ready_for_review"
    assert report["case_count"] == 31
    assert report["blocked_amount_budget_case_count"] == 16
    assert report["range_or_hours_only_case_count"] == 5
    assert report["candidate_range_after_review_case_count"] == 10
    assert report["reviewed_nonblocking_case_count"] == 15
    assert report["covered_required_family_count"] == report["required_family_count"] == 8
    assert report["required_families_missing"] == []
    assert report["missing_blocked_review_case_ids"] == []
    assert report["missing_nonblocking_review_case_ids"] == []
    assert buckets["blocked_amount_budget"]["case_count"] == 16
    assert buckets["range_or_hours_only_pending_review"]["case_count"] == 5
    assert buckets["candidate_range_after_review_pending_human_review"]["case_count"] == 10
    assert all(check["status"] == "passed" for check in report["checks"])
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["not_authorized_for_external_write"] is True
    assert report["not_authorized_for_lake_write"] is True
    assert report["not_authorized_for_sqlite_write"] is True
    assert report["not_authorized_for_budget_submission"] is True
    assert report["not_authorized_for_matter_opening"] is True
    assert report["not_authorized_for_calibration"] is True
    assert report["budget_amount_output_authorized"] is False
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert (
        "labor_employment_budget_qa_gate_candidate" in (report["candidate_exception_lake_labels"])
    )
    assert (
        "no_lake_or_sqlite_write_from_labor_employment_budget_qa_gate"
        in (report["required_next_gates"])
    )


def test_legal_intake_budget_demo_labor_employment_budget_learning_fixtures_are_no_write(
    repo_root,
):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-learning-fixtures-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "labor_employment_budget_learning_fixtures_ready_for_review"
    assert report["fixture_count"] == 8
    assert report["covered_required_family_count"] == report["required_family_count"] == 8
    assert report["missing_required_families"] == []
    assert set(report["covered_budget_output_states"]) == {
        "blocked_amount_budget",
        "range_or_hours_only_pending_review",
        "candidate_range_after_review_pending_human_review",
    }
    assert set(report["covered_learning_loop_types"]) == {
        "actuals_variance",
        "carrier_rejection_capture",
        "appeal_outcome",
        "reviewed_learning_gate",
        "blocked_budget_guard",
    }
    assert report["missing_learning_loop_types"] == []
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["local_json_only"] is True
    assert report["budget_submission_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_labor_employment_budget_outcome_replay_readiness_is_no_write(
    repo_root,
):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-outcome-replay-readiness-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "labor_employment_budget_outcome_replay_ready_for_review"
    assert report["fixture_count"] == 8
    assert report["seed_spec_count"] == 8
    assert report["failed_case_count"] == 0
    assert report["loop_requirement_count"] == 19
    assert report["seeded_loop_requirement_count"] == 19
    assert report["missing_loop_requirement_count"] == 0
    assert report["unresolved_source_ref_count"] == 0
    assert report["expected_replay_artifact_count"] == 9
    assert set(report["covered_learning_loop_types"]) == {
        "actuals_variance",
        "carrier_rejection_capture",
        "appeal_outcome",
        "reviewed_learning_gate",
        "blocked_budget_guard",
    }
    assert report["missing_learning_loop_types"] == []
    assert all(case["status"] == "passed" for case in report["cases"])
    assert all(check["status"] == "passed" for check in report["checks"])
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["local_json_only"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_labor_employment_budget_outcome_replay_execution_is_no_write(
    repo_root,
):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-outcome-replay-execution-report.json"
        ).read_text(encoding="utf-8-sig")
    )

    assert report["status"] == "labor_employment_budget_outcome_replay_execution_ready_for_review"
    assert report["fixture_count"] == 8
    assert report["materialized_case_count"] == 8
    assert report["failed_case_count"] == 0
    assert report["expected_artifact_slot_count"] == 38
    assert report["materialized_artifact_slot_count"] == 38
    assert report["runtime_artifact_count"] == 0
    assert set(report["covered_learning_loop_types"]) == {
        "actuals_variance",
        "carrier_rejection_capture",
        "appeal_outcome",
        "reviewed_learning_gate",
        "blocked_budget_guard",
    }
    assert report["missing_learning_loop_types"] == []
    assert all(case["status"] == "passed" for case in report["cases"])
    assert all(check["status"] == "passed" for check in report["checks"])
    assert all(
        slot["artifact_slot_ref"].endswith(".slot.json")
        for case in report["cases"]
        for slot in case["artifact_slots"]
    )
    assert report["runtime_artifacts_created"] is False
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["local_json_only"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_labor_employment_budget_outcome_replay_builder_binding_is_no_write(
    repo_root,
):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-outcome-replay-builder-binding-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "labor_employment_budget_replay_builder_binding_ready_for_review"
    assert report["fixture_count"] == 8
    assert report["case_count"] == 8
    assert report["slot_count"] == 38
    assert report["bound_slot_count"] == 38
    assert report["unknown_artifact_count"] == 0
    assert report["blocked_slot_count"] == 0
    assert report["replay_input_gap_count"] > 0
    assert report["missing_case_prerequisite_count"] > 0
    assert all(case["status"] == "passed" for case in report["cases"])
    assert all(check["status"] == "passed" for check in report["checks"])
    assert all(
        binding["expected_artifact_name"] in binding["emitted_output_filenames"]
        for case in report["cases"]
        for binding in case["bindings"]
    )
    assert report["runtime_artifacts_created"] is False
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["local_json_only"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False


def test_legal_intake_budget_demo_labor_employment_budget_outcome_replay_confidence_status_is_no_write(
    repo_root,
):
    report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json"
        ).read_text(encoding="utf-8")
    )

    assert report["status"] == "labor_employment_budget_outcome_replay_confidence_pending_inputs"
    assert report["stage_count"] == len(report["stages"]) == 4
    assert report["ready_stage_count"] == 2
    assert report["pending_stage_count"] == 2
    assert report["blocked_stage_count"] == 0
    assert report["builder_replay_input_gap_count"] > 0
    assert report["input_pack_missing_input_count"] > 0
    assert report["display_banner"]["candidate_only"] is True
    assert "budget_submission" in report["display_banner"]["blocked_actions"]
    assert "matter_opening" in report["display_banner"]["blocked_actions"]
    assert "lake_or_sqlite_write" in report["display_banner"]["blocked_actions"]
    assert all(stage["candidate_only"] is True for stage in report["stages"])
    assert all(stage["synthetic_only"] is True for stage in report["stages"])
    assert all(stage["local_json_only"] is True for stage in report["stages"])
    assert all(stage["evidence_refs"] for stage in report["stages"])
    assert report["candidate_only"] is True
    assert report["synthetic_only"] is True
    assert report["non_authoritative"] is True
    assert report["local_json_only"] is True
    assert report["human_review_required"] is True
    assert report["budget_submission_authorized"] is False
    assert report["matter_opening_authorized"] is False
    assert report["training_pipeline_created"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
    assert report["external_writes_performed"] is False
    assert report["silent_learning_performed"] is False
    assert (
        "deterministic_replay_confidence_status_aggregator"
        in (report["rust_transition_candidates"])
    )


def test_legal_intake_budget_ui_disclaims_mutating_authority(repo_root):
    readme = (repo_root / UI_ROOT / "README.md").read_text(encoding="utf-8")
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (repo_root / UI_ROOT / "src/styles.css").read_text(encoding="utf-8")

    assert "read-only" in readme.lower()
    assert "local JSON" in readme
    assert "Exception Lake writer" in readme
    assert "Local JSON only" in app
    assert "UI Review Data Bundle" in app
    assert "Confidence Summary" in app
    assert "POC QA Triage" in app
    assert "Validation Suite Evidence" in app
    assert "Synthetic QA Blocker Drilldown" in app
    assert "Synthetic QA Review Outcome" in app
    assert "Synthetic QA Review Run" in app
    assert "Matter-Linking Preflight" in app
    assert "Matter-Linking QA Gate" in app
    assert "Matter-Linking Review Outcome" in app
    assert "Weak Only" in app
    assert "Split Required" in app
    assert "QA Gates" in app
    assert "L&amp;E Budget Fact QA" in app
    assert "L&amp;E Budget Learning Fixtures" in app
    assert "L&amp;E Budget Outcome Replay Readiness" in app
    assert "L&amp;E Budget Outcome Replay Execution" in app
    assert "L&amp;E Budget Replay Builder Binding" in app
    assert "L&amp;E Budget Replay Confidence Status" in app
    assert "L&amp;E Executable Coverage" in app
    assert "L&amp;E Blocked Driver Review" in app
    assert "L&amp;E Budget Output Expectations" in app
    assert "L&amp;E Budget QA Gate" in app
    assert "L&amp;E Fixture Drilldown" in app
    assert "Testing Readiness And Next Targets" in app
    assert "Synthetic QA workbench" in app
    assert "Budget Stress Targets" in app
    assert "buildQAWorkbenchCards" in app
    assert "buildFixtureDrilldownRows" in app
    assert "assertUIReviewDataBundle" in app
    assert "assertSyntheticConfidenceSummaryReport" in app
    assert "assertPOCQATriageReport" in app
    assert "assertValidationSuiteEvidenceReport" in app
    assert "assertSyntheticQABlockerReport" in app
    assert "assertSyntheticQAReviewOutcomeReport" in app
    assert "assertSyntheticQAReviewRunReport" in app
    assert "assertMatterLinkingPreflightReport" in app
    assert "assertMatterLinkingQAGateReport" in app
    assert "assertMatterLinkingReviewOutcomeReport" in app
    assert "assertLaborEmploymentQAMatrixReport" in app
    assert "assertLaborEmploymentExecutableCoverageReport" in app
    assert "assertLaborEmploymentBlockedDriverImpactReviewReport" in app
    assert "assertLaborEmploymentBudgetOutputExpectationReport" in app
    assert "assertLaborEmploymentBudgetQAGateReport" in app
    assert "assertLaborEmploymentBudgetOutcomeReplayReadinessReport" in app
    assert "assertLaborEmploymentBudgetOutcomeReplayExecutionReport" in app
    assert "assertLaborEmploymentBudgetOutcomeReplayBuilderBindingReport" in app
    assert "assertLaborEmploymentBudgetOutcomeReplayConfidenceStatusReport" in app
    assert "failingQualityGates" in app
    assert "qa-blocker-panel" in styles
    assert "qa-review-outcome-panel" in styles
    assert "poc-triage-panel" in styles
    assert "validation-panel" in styles
    assert "triage-stack" in styles
    assert "validation-step-grid" in styles
    assert "outcome-grid" in styles
    assert "qa-blocker-table" in styles
    assert "empty-state" in styles
    assert "warning-strip" in styles
    assert "executable-coverage-panel" in styles
    assert "coverage-family-grid" in styles
    assert "fixture-drilldown-panel" in styles
    assert "fixture-family-grid" in styles
    assert "budget-bucket-grid" in styles
    assert "qa-workbench-panel" in styles
    assert "qa-workbench-grid" in styles
    assert "qa-workbench-list" in styles
    assert "grid-template-columns" in styles


def test_legal_intake_budget_qa_workbench_joins_ready_state_and_budget_targets(repo_root):
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    coverage = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-executable-coverage-report.json"
        ).read_text(encoding="utf-8")
    )
    budget_gate = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-labor-employment-budget-qa-gate-report.json"
        ).read_text(encoding="utf-8")
    )
    blocker = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-blocker-report.json").read_text(
            encoding="utf-8"
        )
    )
    poc = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-poc-qa-triage-report.json").read_text(
            encoding="utf-8"
        )
    )
    validation = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-validation-suite-evidence-report.json").read_text(
            encoding="utf-8"
        )
    )
    output = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-output-expectations-report.json"
        ).read_text(encoding="utf-8")
    )

    assert "QAWorkbenchPanel" in app
    assert "cards={qaWorkbenchCards}" in app
    assert "coverageReport: laborEmploymentExecutableCoverage" in app
    assert "budgetQAGateReport: laborEmploymentBudgetQAGate" in app
    assert "blockerReport: syntheticQABlockerReport" in app
    assert "pocReport: pocQATriage" in app
    assert "validationReport: validationSuiteEvidence" in app
    assert "review-only and remain outside calibration" in app
    assert "block_amount_budget_impact_count" in app
    assert "range_widening_impact_count" in app
    assert coverage["coverage_state"] == "complete_executable_coverage"
    assert coverage["missing_executable_pack_case_count"] == 0
    assert budget_gate["blocked_amount_budget_case_count"] == 16
    assert budget_gate["reviewed_nonblocking_case_count"] == 15
    assert blocker["failed_row_count"] == 0
    assert blocker["blocked_row_count"] == 0
    assert blocker["needs_review_action_count"] > 0
    assert poc["status"] == "poc_qa_ready_for_review"
    assert validation["status"] == "validation_suite_passed"
    assert validation["failed_step_count"] == 0
    assert any(
        case["block_amount_budget_impact_count"] > 0
        and case["final_allowed_budget_output"] == "blocked_amount_budget"
        for case in output["cases"]
    )


def test_legal_intake_budget_qa_blocker_drilldown_tracks_review_queue(repo_root):
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    blocker_report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-blocker-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert "demoSyntheticQABlockerReport" in app
    assert "const syntheticQABlockerReport" in app
    assert "SyntheticQABlockerDrilldownPanel report={syntheticQABlockerReport}" in app
    assert "report.rows.map" in app
    assert "report.required_next_actions.map" in app
    assert "report.review_queue_state" in app
    assert "row.recommended_next_action" in app
    assert "row.candidate_exception_lake_labels" in app
    assert "qaActionClass" in app
    assert "No failed or blocked synthetic QA rows" in app
    assert "review, not calibration, submission, or" in app
    assert "Lake write" in app
    assert blocker_report["pending_review_row_count"] > 0
    assert blocker_report["needs_review_action_count"] == blocker_report["pending_review_row_count"]
    assert blocker_report["review_queue_state"] == "needs_review"
    assert blocker_report["failed_row_count"] == 0
    assert blocker_report["blocked_row_count"] == 0
    assert blocker_report["budget_submission_authorized"] is False
    assert blocker_report["lake_write_performed"] is False
    assert blocker_report["silent_learning_performed"] is False


def test_legal_intake_budget_qa_review_outcome_tracks_partial_review(repo_root):
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    outcome_report = json.loads(
        (
            repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-review-outcome-report.json"
        ).read_text(encoding="utf-8")
    )
    bundle = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-ui-review-data-bundle.json").read_text(
            encoding="utf-8"
        )
    )
    detail_reports = {report["report_kind"]: report for report in bundle["detail_reports"]}

    assert "demoSyntheticQAReviewOutcome" in app
    assert "const syntheticQAReviewOutcome" in app
    assert "SyntheticQAReviewOutcomePanel report={syntheticQAReviewOutcome}" in app
    assert "qaReviewOutcomeClass" in app
    assert "Calibration:" in app
    assert outcome_report["reviewed_row_count"] == 3
    assert outcome_report["unreviewed_row_count"] > 0
    assert outcome_report["unresolved_followup_count"] > 0
    assert outcome_report["not_authorized_for_calibration"] is True
    assert outcome_report["lake_write_performed"] is False
    assert outcome_report["silent_learning_performed"] is False
    assert detail_reports["synthetic_qa_review_outcome"]["present"] is True
    assert detail_reports["synthetic_qa_review_outcome"]["required"] is False
    assert detail_reports["synthetic_qa_review_outcome"]["renderer"] == (
        "SyntheticQAReviewOutcomePanel"
    )
    assert detail_reports["matter_linking_review_outcome"]["present"] is True
    assert detail_reports["matter_linking_review_outcome"]["required"] is False
    assert detail_reports["matter_linking_review_outcome"]["renderer"] == (
        "MatterLinkingReviewOutcomePanel"
    )
    assert detail_reports["matter_linking_qa_gate"]["present"] is True
    assert detail_reports["matter_linking_qa_gate"]["required"] is False
    assert detail_reports["matter_linking_qa_gate"]["renderer"] == "MatterLinkingQAGatePanel"


def test_legal_intake_budget_fixture_drilldown_joins_existing_le_reports(repo_root):
    app = (repo_root / UI_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    output_report = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-budget-output-expectations-report.json"
        ).read_text(encoding="utf-8")
    )
    blocked_review = json.loads(
        (
            repo_root
            / UI_ROOT
            / "src/fixtures/demo-labor-employment-blocked-driver-impact-review-report.json"
        ).read_text(encoding="utf-8")
    )
    output_ids = {case["executable_fixture_id"] for case in output_report["cases"]}
    blocked_ids = {case["executable_fixture_id"] for case in blocked_review["case_reviews"]}

    assert "function buildFixtureDrilldownRows" in app
    assert "outputReport.cases.map" in app
    assert "blockedReviewReport.case_reviews.map" in app
    assert "blockedReviewReport={laborEmploymentBlockedDriverReview}" in app
    assert "outputReport={laborEmploymentBudgetOutputExpectations}" in app
    assert blocked_ids <= output_ids
    assert len(output_ids - blocked_ids) == (
        output_report["candidate_range_after_review_case_count"]
        + output_report["range_or_hours_only_case_count"]
    )
    assert all(case["candidate_only"] is True for case in output_report["cases"])
    assert all(case["external_writes_performed"] is False for case in output_report["cases"])
