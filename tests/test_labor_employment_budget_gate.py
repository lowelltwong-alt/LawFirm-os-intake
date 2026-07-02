import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.labor_employment_budget_facts import (
    run_labor_employment_budget_fact_audit,
)
from lawfirm_os_intake.labor_employment_executable_driver_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_driver_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_driver_impact import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME,
    run_labor_employment_executable_driver_impact_audit,
)
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from lawfirm_os_intake.models import (
    BudgetPreconditionReport,
    BudgetProposal,
    HumanConfirmation,
    IntakePreflightPacket,
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentExecutableDriverImpactReport,
)
from lawfirm_os_intake.preconditions import build_budget_precondition_report
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


MANIFEST_REF = "examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json"
PROFILE_REF = "context/synthetic-profiles/insurance-defense.yaml"
INTAKE_REF = "examples/synthetic/inbound/carrier-assignment-medmal.json"
CONFIRMATION_REF = (
    "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
)
EXECUTABLE_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
EXECUTABLE_BINDING_REF = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)


def _confirmed_budget_inputs(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / INTAKE_REF,
        repo_root / PROFILE_REF,
        tmp_path / "preflight",
    )
    raw = load_json(repo_root / CONFIRMATION_REF)
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    return run_dir / "intake_preflight_packet.json", confirmation_path


def _labor_employment_fact_report(tmp_path, repo_root):
    _report, run_dir = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "le-budget-facts",
    )
    return run_dir / "labor_employment_budget_fact_audit_report.json"


def _noncritical_report(tmp_path, report_path):
    payload = load_json(report_path)
    payload["budget_readiness_state"] = "range_only_pending_human_review"
    payload["critical_gap_count"] = 0
    for gap in payload["gaps"]:
        gap["severity"] = "warning"
        gap["blocks_precise_budget"] = False
    return write_json(tmp_path / "le-budget-facts-noncritical.json", payload)


def _labor_employment_driver_impact_report(tmp_path, repo_root):
    _, executable_run_dir = run_labor_employment_executable_fixture_audit(
        manifest_path=repo_root / EXECUTABLE_MANIFEST_REF,
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fixtures",
    )
    _, fact_binding_run_dir = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=repo_root / EXECUTABLE_BINDING_REF,
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-fact-binding",
    )
    _, driver_binding_run_dir = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=(
            executable_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
        ),
        executable_fact_binding_report_path=(
            fact_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
        ),
        repo_root=repo_root,
        out_dir=tmp_path / "le-executable-driver-binding",
    )
    _, impact_run_dir = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=(
            driver_binding_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
        ),
        out_dir=tmp_path / "le-executable-driver-impact",
    )
    return impact_run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME


def _nonblocking_driver_impact_report(tmp_path, impact_report_path):
    report = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(impact_report_path)
    )
    selected = next(
        case
        for case in report.cases
        if case.executable_fixture_id == "le-admin-exhaustion-clean.executable.v0_1"
    )
    filtered = LaborEmploymentExecutableDriverImpactReport(
        executable_driver_impact_report_id=f"{report.executable_driver_impact_report_id}_admin",
        status="labor_employment_executable_driver_impacts_ready_for_review",
        executable_driver_binding_report_ref=report.executable_driver_binding_report_ref,
        case_count=1,
        failed_case_count=0,
        impact_item_count=selected.impact_item_count,
        source_bound_impact_count=selected.source_bound_impact_count,
        block_amount_budget_impact_count=selected.block_amount_budget_impact_count,
        range_widening_impact_count=selected.range_widening_impact_count,
        scenario_fork_impact_count=selected.scenario_fork_impact_count,
        rate_guideline_review_impact_count=selected.rate_guideline_review_impact_count,
        human_review_impact_count=selected.human_review_impact_count,
        max_range_widening_factor=selected.max_range_widening_factor,
        impact_policy_dimensions=report.impact_policy_dimensions,
        missing_impact_policy_dimensions=[],
        cases=[selected],
        checks=report.checks,
        required_next_gates=report.required_next_gates,
        generated_at=report.generated_at,
    )
    return write_json(
        tmp_path / "le-driver-impact-nonblocking.json",
        filtered.model_dump(mode="json"),
    )


def test_critical_le_budget_fact_gaps_block_budget_before_proposal(tmp_path, repo_root):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    fact_report_path = _labor_employment_fact_report(tmp_path, repo_root)
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="labor_employment_budget_fact_no_critical_gaps"):
        run_budget(
            preflight_packet_path,
            confirmation_path,
            repo_root / PROFILE_REF,
            budget_dir,
            labor_employment_budget_fact_report=fact_report_path,
        )

    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "labor_employment_budget_facts_blocked"
    assert report.labor_employment_budget_fact_report_ref == str(fact_report_path)
    assert report.labor_employment_budget_readiness_state == "blocked_missing_critical_facts"
    assert report.labor_employment_budget_treatment == "block_amount_budget"
    assert report.labor_employment_critical_gap_count > 0
    assert any(
        check.check_id == "labor_employment_budget_fact_no_critical_gaps"
        and check.status == "failed"
        for check in report.checks
    )
    assert candidates[0]["local_event_label"] == "labor_employment_budget_facts_blocked"
    assert str(fact_report_path) in candidates[0]["structured_refs"]
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "conflict_search_seed_packet.json").exists()
    assert not (budget_dir / "matter_opening_review_package.md").exists()


def test_noncritical_le_budget_fact_report_surfaces_supported_budget_unknowns(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    fact_report_path = _noncritical_report(
        tmp_path,
        _labor_employment_fact_report(tmp_path, repo_root),
    )

    _proposal, budget_dir = run_budget(
        preflight_packet_path,
        confirmation_path,
        repo_root / PROFILE_REF,
        tmp_path / "budget",
        labor_employment_budget_fact_report=fact_report_path,
    )

    precondition = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    budget = BudgetProposal.model_validate(load_json(budget_dir / "legal_budget_proposal.json"))
    manifest = load_json(budget_dir / "review_package_manifest.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")
    budget_review_text = (budget_dir / "legal_budget_review_form.md").read_text(encoding="utf-8")
    candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert precondition.status == "passed"
    assert precondition.labor_employment_budget_fact_report_ref == str(fact_report_path)
    assert precondition.labor_employment_budget_readiness_state == (
        "range_only_pending_human_review"
    )
    assert precondition.labor_employment_budget_treatment == "hours_only_or_broad_range"
    assert precondition.labor_employment_critical_gap_count == 0
    assert manifest["artifact_refs"]["labor_employment_budget_fact_report"] == str(fact_report_path)
    assert any(
        item.source_kind == "labor_employment_budget_fact_report"
        for item in budget.budget_support_items
    )
    assert any("L&E budget fact needs review:" in unknown for unknown in budget.unknowns)
    assert "L&E budget fact report ref:" in review_text
    assert "L&E budget treatment: hours_only_or_broad_range" in review_text
    assert "labor_employment_budget_fact_report" in budget_review_text
    assert any(
        candidate["local_event_label"] == "budget_unknowns_require_review"
        and any(
            "labor-employment-budget-fact-report://" in ref for ref in candidate["structured_refs"]
        )
        for candidate in candidates
    )


def test_le_driver_impact_blocks_budget_before_proposal_when_amount_budget_blocked(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    impact_report_path = _labor_employment_driver_impact_report(tmp_path, repo_root)
    budget_dir = tmp_path / "budget-driver-blocked"

    with pytest.raises(ValueError, match="labor_employment_driver_impact_no_amount_budget_blocks"):
        run_budget(
            preflight_packet_path,
            confirmation_path,
            repo_root / PROFILE_REF,
            budget_dir,
            labor_employment_driver_impact_report=impact_report_path,
        )

    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "labor_employment_driver_impacts_blocked"
    assert report.labor_employment_driver_impact_report_ref == str(impact_report_path)
    assert report.labor_employment_driver_allowed_budget_output == "blocked_amount_budget"
    assert report.labor_employment_driver_block_amount_budget_impact_count > 0
    assert candidates[0]["local_event_label"] == "labor_employment_driver_impacts_blocked"
    assert str(impact_report_path) in candidates[0]["structured_refs"]
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "conflict_search_seed_packet.json").exists()


def test_nonblocking_le_driver_impact_surfaces_range_scenario_and_rate_review(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    impact_report_path = _nonblocking_driver_impact_report(
        tmp_path,
        _labor_employment_driver_impact_report(tmp_path, repo_root),
    )

    _proposal, budget_dir = run_budget(
        preflight_packet_path,
        confirmation_path,
        repo_root / PROFILE_REF,
        tmp_path / "budget-driver-impact",
        labor_employment_driver_impact_report=impact_report_path,
    )

    precondition = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    budget = BudgetProposal.model_validate(load_json(budget_dir / "legal_budget_proposal.json"))
    manifest = load_json(budget_dir / "review_package_manifest.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")
    candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert precondition.status == "passed"
    assert precondition.labor_employment_driver_impact_report_ref == str(impact_report_path)
    assert precondition.labor_employment_driver_block_amount_budget_impact_count == 0
    assert precondition.labor_employment_driver_range_widening_impact_count > 0
    assert precondition.labor_employment_driver_scenario_fork_impact_count > 0
    assert precondition.labor_employment_driver_allowed_budget_output == (
        "range_or_hours_only_pending_review"
    )
    assert manifest["artifact_refs"]["labor_employment_driver_impact_report"] == str(
        impact_report_path
    )
    assert budget.display_banner["labor_employment_driver_impact_report_ref"] == str(
        impact_report_path
    )
    assert any(
        item.source_kind == "labor_employment_driver_impact_report"
        for item in budget.budget_support_items
    )
    assert any(
        "L&E driver impact report requires scenario-fork review" in unknown
        for unknown in budget.unknowns
    )
    assert "L&E driver impact report ref:" in review_text
    assert any(
        candidate["local_event_label"] == "budget_unknowns_require_review"
        and any(
            "labor-employment-driver-impact-report://" in ref
            for ref in candidate["structured_refs"]
        )
        for candidate in candidates
    )


def test_le_budget_fact_precondition_resolves_structured_ref_without_path(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    fact_report_path = _noncritical_report(
        tmp_path,
        _labor_employment_fact_report(tmp_path, repo_root),
    )
    packet = IntakePreflightPacket.model_validate(load_json(preflight_packet_path))
    confirmation = HumanConfirmation.model_validate(load_json(confirmation_path))
    fact_report = LaborEmploymentBudgetFactAuditReport.model_validate(load_json(fact_report_path))

    report = build_budget_precondition_report(
        packet,
        confirmation,
        [str(preflight_packet_path), str(confirmation_path)],
        labor_employment_budget_fact_report=fact_report,
    )

    assert report.status == "passed"
    assert report.labor_employment_budget_fact_report_ref == (
        "labor-employment-budget-fact-report://"
        f"{fact_report.labor_employment_budget_fact_audit_report_id}"
    )
    assert all(
        check.evidence_refs for check in report.checks if check.check_id.startswith("labor_")
    )
