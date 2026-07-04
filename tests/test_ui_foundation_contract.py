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
        "src/fixtures/demo-validation-suite-evidence-report.json",
        "src/fixtures/demo-matter-linking-preflight-report.json",
        "src/fixtures/demo-matter-linking-qa-gate-report.json",
        "src/fixtures/demo-matter-linking-review-outcome-report.json",
        "src/fixtures/demo-labor-employment-qa-matrix-report.json",
        "src/fixtures/demo-labor-employment-executable-coverage-report.json",
        "src/fixtures/demo-labor-employment-blocked-driver-impact-review-report.json",
        "src/fixtures/demo-labor-employment-budget-output-expectations-report.json",
        "src/fixtures/demo-labor-employment-budget-qa-gate-report.json",
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
        "labor_employment_budget_fact_gold_report.json",
        "validation_suite_evidence_report.json",
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
    assert bundle["detail_report_count"] == len(bundle["detail_reports"]) == 13
    assert bundle["required_detail_report_count"] == 7
    assert bundle["present_detail_report_count"] == 13
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
        "matter_linking_preflight_report.json",
        "matter_linking_qa_gate_report.json",
        "matter_linking_review_outcome_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_budget_qa_gate_report.json",
    } <= set(detail_reports)
    assert all(report["present"] is True for report in bundle["detail_reports"])
    assert all(report["source_sha256"].startswith("sha256:") for report in bundle["detail_reports"])
    assert all(report["external_writes_performed"] is False for report in bundle["detail_reports"])


def test_legal_intake_budget_demo_synthetic_qa_review_run_is_no_write(repo_root):
    report = json.loads(
        (repo_root / UI_ROOT / "src/fixtures/demo-synthetic-qa-review-run-report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "synthetic_qa_review_run_ready"
    assert report["step_count"] == len(report["steps"]) == 22
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
        "synthetic_confidence_summary",
        "labor_employment_blocked_driver_impact_review",
        "labor_employment_budget_output_expectations",
        "labor_employment_budget_qa_gate",
    } <= {step["step_id"] for step in report["steps"]}


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


def test_legal_intake_budget_demo_executable_coverage_is_partial_and_no_write(repo_root):
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
    assert report["coverage_state"] == "partial_executable_coverage"
    assert report["pack_case_count"] == 32
    assert report["executable_fixture_count"] == 17
    assert report["covered_pack_case_count"] == 18
    assert report["missing_executable_pack_case_count"] == 14
    assert report["covered_family_count"] == 8
    assert report["missing_family_count"] == 0
    assert report["covered_family_variant_count"] == len(report["covered_pack_case_ids"]) == 18
    assert (
        report["missing_family_variant_count"]
        == len(report["missing_executable_pack_case_ids"])
        == 14
    )
    assert "discrimination_harassment:clean" not in report["missing_family_variant_refs"]
    assert "wage_hour_flsa_state:clean" not in report["missing_family_variant_refs"]
    assert (
        "class_collective_paga_representative:clean" not in (report["missing_family_variant_refs"])
    )
    assert (
        "class_collective_paga_representative:messy_thread"
        not in (report["missing_family_variant_refs"])
    )
    assert families["ada_fmla_accommodation_leave"]["covered_case_count"] == 4
    assert families["ada_fmla_accommodation_leave"]["missing_variants"] == []
    assert families["epli_carrier_assignment"]["covered_case_count"] == 4
    assert families["epli_carrier_assignment"]["missing_variants"] == []
    assert "le-epli-carrier-adversarial.v0_1" in report["covered_pack_case_ids"]
    assert families["class_collective_paga_representative"]["covered_case_count"] == 3
    assert families["class_collective_paga_representative"]["missing_variants"] == [
        "missing_attachment"
    ]
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
    assert report["case_count"] == 17
    assert report["blocked_case_count"] == len(report["case_reviews"]) == 8
    assert report["nonblocking_case_count"] == 9
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
        in (cases["le-epli-carrier-adversarial.executable.v0_1"]["candidate_exception_lake_labels"])
    )
    assert {"party_topology", "representation_posture", "carrier_guideline_rate_context"} <= set(
        cases["le-epli-carrier-adversarial.executable.v0_1"]["critical_driver_dimensions"]
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
    assert report["qa_step_count"] == 22
    assert report["qa_failed_step_count"] == 0
    assert report["qa_missing_required_artifact_count"] == 0
    assert report["ui_detail_report_count"] == 13
    assert report["ui_present_detail_report_count"] == 13
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
    assert report["row_count"] == len(report["rows"]) == 24
    assert report["failed_row_count"] == 0
    assert report["blocked_row_count"] == 0
    assert report["pending_review_row_count"] == 24
    assert report["blocked_action_count"] == 0
    assert report["needs_review_action_count"] == 24
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
    assert report["source_row_count"] == 24
    assert report["reviewed_row_count"] == len(report["reviewed_row_ids"]) == 3
    assert report["unreviewed_row_count"] == len(report["unreviewed_row_ids"]) == 21
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
    assert report["case_count"] == len(report["cases"]) == 17
    assert report["failed_case_count"] == 0
    assert report["blocked_amount_budget_case_count"] == 8
    assert report["range_or_hours_only_case_count"] == 3
    assert report["candidate_range_after_review_case_count"] == 6
    assert report["reviewed_nonblocking_case_count"] == 9
    assert report["blocked_review_case_count"] == 8
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
        cases["le-epli-carrier-adversarial.executable.v0_1"]["final_allowed_budget_output"]
        == "blocked_amount_budget"
    )
    assert (
        cases["le-epli-carrier-adversarial.executable.v0_1"]["blocked_case_review_present"] is True
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
        cases["le-admin-exhaustion-clean.executable.v0_1"][
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
    assert report["case_count"] == 17
    assert report["blocked_amount_budget_case_count"] == 8
    assert report["range_or_hours_only_case_count"] == 3
    assert report["candidate_range_after_review_case_count"] == 6
    assert report["reviewed_nonblocking_case_count"] == 9
    assert report["covered_required_family_count"] == report["required_family_count"] == 8
    assert report["required_families_missing"] == []
    assert report["missing_blocked_review_case_ids"] == []
    assert report["missing_nonblocking_review_case_ids"] == []
    assert buckets["blocked_amount_budget"]["case_count"] == 8
    assert buckets["range_or_hours_only_pending_review"]["case_count"] == 3
    assert buckets["candidate_range_after_review_pending_human_review"]["case_count"] == 6
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
    assert "L&amp;E Executable Coverage" in app
    assert "L&amp;E Blocked Driver Review" in app
    assert "L&amp;E Budget Output Expectations" in app
    assert "L&amp;E Budget QA Gate" in app
    assert "L&amp;E Fixture Drilldown" in app
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
    assert "grid-template-columns" in styles


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
