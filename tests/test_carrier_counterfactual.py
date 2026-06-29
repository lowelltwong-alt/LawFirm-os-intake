from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.guidelines import (
    build_carrier_compliant_projection,
    build_carrier_preapproval_report,
    load_carrier_guideline,
)
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run_medmal_budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    return run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )


def _proposal_line_snapshot(budget):
    return [
        line.model_dump(
            mode="json",
            include={
                "phase_id",
                "task_id",
                "external_code_candidate",
                "expense_code",
                "staffing_role",
                "estimated_hours",
                "hourly_rate",
                "estimated_fees",
                "estimated_expenses",
            },
        )
        for line in budget.lines
    ]


def test_same_budget_projects_differently_under_second_synthetic_carrier(
    tmp_path,
    repo_root,
):
    budget, _run_dir = _run_medmal_budget(tmp_path, repo_root)
    guideline_ref = "config/synthetic-carrier-guideline.yaml"
    guideline = load_carrier_guideline(repo_root / guideline_ref)
    proposal_before = _proposal_line_snapshot(budget)

    harbor_projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref=guideline_ref,
        carrier_id="synthetic-carrier-a",
    )
    cascade_projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref=guideline_ref,
        carrier_id="synthetic-carrier-b",
    )
    proposal_after = _proposal_line_snapshot(budget)

    assert proposal_before == proposal_after
    assert harbor_projection is not None
    assert cascade_projection is not None
    assert harbor_projection.basis.carrier_id == "synthetic-carrier-a"
    assert cascade_projection.basis.carrier_id == "synthetic-carrier-b"
    assert harbor_projection.proposed_total == cascade_projection.proposed_total
    assert harbor_projection.compliant_total != cascade_projection.compliant_total
    assert harbor_projection.basis.proposal_lines_unchanged is True
    assert cascade_projection.basis.proposal_lines_unchanged is True
    assert harbor_projection.rewrites_budget is False
    assert cascade_projection.rewrites_budget is False

    assert harbor_projection.basis.contingency_allowed is True
    assert cascade_projection.basis.contingency_allowed is False
    assert cascade_projection.contingency_delta > harbor_projection.contingency_delta
    assert cascade_projection.rate_cap_delta > harbor_projection.rate_cap_delta
    assert cascade_projection.expense_cap_delta > harbor_projection.expense_cap_delta
    assert cascade_projection.staffing_rule_delta != harbor_projection.staffing_rule_delta
    assert "L340" in cascade_projection.basis.staffing_task_role_overrides
    assert "L340" not in harbor_projection.basis.staffing_task_role_overrides

    cascade_refs = {
        ref
        for line in cascade_projection.lines
        for ref in line.guideline_refs
        if "synthetic-carrier-b" in ref
    }
    assert any("rate_caps/partner" in ref for ref in cascade_refs)
    assert any("expense_caps/E119" in ref for ref in cascade_refs)
    assert any("staffing_rules/task_role_overrides/L340" in ref for ref in cascade_refs)

    assert cascade_projection.not_authorized_for_client_submission is True
    assert cascade_projection.external_writes_performed is False


def test_second_synthetic_carrier_has_distinct_preapproval_thresholds(tmp_path, repo_root):
    budget, _run_dir = _run_medmal_budget(tmp_path, repo_root)
    guideline_ref = "config/synthetic-carrier-guideline.yaml"
    guideline = load_carrier_guideline(repo_root / guideline_ref)

    harbor_report = build_carrier_preapproval_report(
        budget,
        guideline=guideline,
        guideline_ref=guideline_ref,
        carrier_id="synthetic-carrier-a",
    )
    cascade_report = build_carrier_preapproval_report(
        budget,
        guideline=guideline,
        guideline_ref=guideline_ref,
        carrier_id="synthetic-carrier-b",
    )

    assert harbor_report is not None
    assert cascade_report is not None
    assert harbor_report.carrier_id == "synthetic-carrier-a"
    assert cascade_report.carrier_id == "synthetic-carrier-b"
    assert cascade_report.required_count >= harbor_report.required_count
    assert {
        requirement.threshold_id: requirement.threshold_value
        for requirement in cascade_report.requirements
    }["expert_spend_over_amount"] == 20000.0
    assert all(
        requirement.rewrites_budget is False
        and requirement.preapproval_obtained is False
        and requirement.carrier_submission_authorized is False
        for requirement in cascade_report.requirements
    )
