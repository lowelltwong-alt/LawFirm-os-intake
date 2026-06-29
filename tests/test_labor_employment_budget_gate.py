import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.labor_employment_budget_facts import (
    run_labor_employment_budget_fact_audit,
)
from lawfirm_os_intake.models import (
    BudgetPreconditionReport,
    BudgetProposal,
    HumanConfirmation,
    IntakePreflightPacket,
    LaborEmploymentBudgetFactAuditReport,
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
