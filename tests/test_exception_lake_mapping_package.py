from pathlib import Path

from lawfirm_os_intake.budget_actuals import build_budget_actual_comparison_report
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.exceptions import (
    build_budget_actual_variance_exception_candidates,
    build_budget_form_exception_candidates,
    build_budget_invariant_exception_candidates,
)
from lawfirm_os_intake.models import (
    BudgetFormFormulaCheck,
    BudgetFormMappingReport,
    BudgetProposal,
    ExceptionLakeCandidate,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def _run_budget(tmp_path, repo_root) -> tuple[BudgetProposal, Path, object]:
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget, budget_dir, packet


def test_budget_run_writes_exception_lake_mapping_package_and_actuals_report(tmp_path, repo_root):
    _, budget_dir, _ = _run_budget(tmp_path, repo_root)

    mapping = load_json(budget_dir / "exception_lake_mapping_package.json")
    actuals = load_json(budget_dir / "budget_actual_comparison_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")
    candidate_labels = {
        candidate["local_event_label"]
        for candidate in load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    }

    assert mapping["status"] == "passed"
    assert mapping["admission_state"] == "dry_run_not_admitted"
    assert mapping["sqlite_write_performed"] is False
    assert mapping["external_writes_performed"] is False
    assert {rule["issue_family"] for rule in mapping["rules"]} >= {
        "broken_template_formula",
        "missing_budget_code_mapping",
        "unknown_budget_driver",
        "guideline_or_cap_issue",
        "human_budget_change",
        "budget_actual_cost_variance",
        "carrier_rejection_capture",
        "carrier_rejection_reconciliation",
        "carrier_rejection_appeal_result",
        "carrier_rejection_learning",
        "budget_invariant_violation",
        "scenario_policy_invalid",
        "rate_resolution_ambiguous",
        "carrier_appeal_outcome",
        "matter_link_ambiguity",
        "matter_link_conflict",
        "human_correction_of_machine_output",
        "qa_gate_defect",
        "fixture_weakness",
        "workflow_discovery",
    }
    assert "budget_unknown_driver_requires_review" in candidate_labels
    assert "budget_guideline_or_cap_requires_review" in candidate_labels
    assert actuals["status"] == "actuals_not_available"
    assert actuals["comparison_scope"] == "phase"
    assert actuals["billing_connector_read_performed"] is False
    assert actuals["billing_connector_write_performed"] is False
    assert actuals["phase_comparisons"]
    assert manifest["artifact_refs"]["budget_exception_lake_mapping_package"] == str(
        budget_dir / "exception_lake_mapping_package.json"
    )
    assert manifest["artifact_refs"]["budget_actual_comparison_report"] == str(
        budget_dir / "budget_actual_comparison_report.json"
    )
    assert "### Exception Lake Mapping Package" in review_text
    assert "### Budget Actual Comparison" in review_text


def test_budget_form_mapping_failures_become_dry_run_exception_candidates():
    report = BudgetFormMappingReport(
        budget_form_mapping_report_id="budgetformmap-test",
        budget_proposal_id="budget-test",
        status="failed",
        template_sha256="sha256:test",
        sheet_name="Budget",
        missing_budget_mappings=["L330"],
        formula_checks=[
            BudgetFormFormulaCheck(
                check_id="phase_l300_original_budget_formula",
                status="failed",
                message="phase formula missing",
                cell="B30",
            )
        ],
        generated_at="2026-06-24T00:00:00Z",
    )

    candidates = build_budget_form_exception_candidates(
        run_id="run-test",
        preflight_packet_id="intake-test",
        report=report,
        report_ref="budget_form_mapping_report.json",
    )
    labels = {candidate.local_event_label: candidate for candidate in candidates}

    assert labels["budget_form_original_formula_broken"].canonical_lake_class == (
        "workflow_escalation"
    )
    assert labels["budget_form_code_mapping_missing"].canonical_lake_class == "retrieval_miss"
    assert all(candidate.raw_payload_included is False for candidate in candidates)
    assert all(candidate.canonical_promotion_required is True for candidate in candidates)


def test_phase_actual_variance_emits_dry_run_exception_candidate(tmp_path, repo_root):
    budget, _, packet = _run_budget(tmp_path, repo_root)
    report = build_budget_actual_comparison_report(
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        budget=budget,
        actuals_by_phase={"L300": {"fees": 999999.0, "expenses": 0.0}},
        actuals_source_ref="synthetic-actuals://unit-test",
    )

    candidates = build_budget_actual_variance_exception_candidates(
        report,
        "budget_actual_comparison_report.json",
    )

    assert report.status == "variance_review_required"
    assert candidates
    assert candidates[0].local_event_label == "budget_actual_cost_variance_requires_review"
    assert candidates[0].canonical_lake_class == "workflow_escalation"
    assert candidates[0].raw_payload_included is False


def test_exception_lake_mapping_rules_cover_fable_ex1_ex2_families(repo_root, tmp_path):
    _budget, budget_dir, _packet = _run_budget(tmp_path, repo_root)
    mapping = load_json(budget_dir / "exception_lake_mapping_package.json")
    rules = {rule["issue_family"]: rule for rule in mapping["rules"]}

    assert rules["budget_invariant_violation"]["mapping_id"] == "budget_invariant_violation.v1"
    assert rules["scenario_policy_invalid"]["local_event_label"] == "scenario_policy_invalid"
    assert rules["rate_resolution_ambiguous"]["canonical_lake_class"] == (
        "authority_conflict_override"
    )
    assert rules["matter_link_ambiguity"]["local_event_label"] == "source_matter_link_ambiguous"
    assert rules["matter_link_conflict"]["canonical_lake_class"] == "authority_conflict_override"
    assert rules["human_correction_of_machine_output"]["support_ref_kinds"] == [
        "human_review_outcome_record",
        "structured_ref",
    ]


def test_budget_invariant_failures_emit_exception_candidates():
    report = {
        "status": "failed",
        "violations": [
            {
                "invariant_id": "I1",
                "code": "line_fee_mismatch",
                "path": "$.lines[0].estimated_fees",
            },
            {
                "invariant_id": "I6",
                "code": "scenario_resolution_phase_not_included",
                "path": "$.scenario_set.scenarios[0].resolution_phase",
            },
        ],
    }

    candidates = build_budget_invariant_exception_candidates(
        run_id="run-test",
        preflight_packet_id="packet-test",
        report=report,
        report_ref="budget_invariant_report.json",
    )
    by_label = {candidate.local_event_label: candidate for candidate in candidates}

    invariant = by_label["budget_invariant_violation"]
    scenario = by_label["scenario_policy_invalid"]
    assert invariant.canonical_lake_class == "workflow_escalation"
    assert invariant.severity == "S0"
    assert scenario.blocked_state == "scenario_policy_invalid"
    assert scenario.severity == "S1"
    assert invariant.identity_key != scenario.identity_key
    assert all(candidate.raw_payload_included is False for candidate in candidates)


def test_candidate_identity_key_stability_for_mapping_inputs():
    first = ExceptionLakeCandidate(
        candidate_id="exc-1",
        run_id="run-1",
        preflight_packet_id="packet-1",
        local_event_label="matter_link_conflict",
        canonical_lake_class="authority_conflict_override",
        reason="conflicting identifiers",
        structured_refs=["matter-link-rule://strong-id-conflict"],
        blocked_state="matter_link_conflict",
    )
    repeat = ExceptionLakeCandidate(
        candidate_id="exc-2",
        run_id="run-2",
        preflight_packet_id="packet-2",
        local_event_label="matter_link_conflict",
        canonical_lake_class="authority_conflict_override",
        reason="same conflicting identifiers",
        structured_refs=["matter-link-rule://strong-id-conflict"],
        blocked_state="matter_link_conflict",
    )

    assert first.identity_key == repeat.identity_key
    assert first.severity == "S0"
    assert first.occurrence_hint == "count_recurrence_by_identity_key"
