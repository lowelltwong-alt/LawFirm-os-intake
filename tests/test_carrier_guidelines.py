from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.guidelines import load_carrier_guideline
from lawfirm_os_intake.models import ExceptionLakeMappingPackage, HumanConfirmation
from lawfirm_os_intake.util import load_json, load_jsonl
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


def test_carrier_guideline_projection_keeps_proposal_lines_unchanged(tmp_path, repo_root):
    budget, _run_dir = _run_medmal_budget(tmp_path, repo_root)
    projection = budget.carrier_compliant_projection

    assert projection is not None
    assert projection.status == "projected_for_human_review"
    assert projection.basis.guideline_ref == "config/synthetic-carrier-guideline.yaml"
    assert projection.basis.carrier_id == "synthetic-carrier-a"
    assert projection.basis.proposal_lines_unchanged is True
    assert projection.rewrites_budget is False
    assert projection.external_writes_performed is False
    assert projection.not_authorized_for_client_submission is True

    partner_lines = [line for line in budget.lines if line.staffing_role == "partner"]
    assert partner_lines
    assert {line.hourly_rate for line in partner_lines} == {450.0}
    assert all(flag.rewrites_budget is False for flag in budget.guideline_flags)


def test_carrier_guideline_projection_applies_rate_and_expense_caps(tmp_path, repo_root):
    budget, _run_dir = _run_medmal_budget(tmp_path, repo_root)
    projection = budget.carrier_compliant_projection
    assert projection is not None

    assert budget.total_proposed_budget is not None
    assert projection.proposed_total == budget.total_proposed_budget
    assert projection.compliant_total is not None
    assert projection.proposed_total > projection.compliant_total
    assert projection.over_cap_amount > 0
    assert projection.rate_cap_delta > 0
    assert projection.expense_cap_delta > 0
    assert projection.capped_line_count > 0

    partner_projection_lines = [
        line for line in projection.lines if line.staffing_role == "partner"
    ]
    assert any(line.rate_cap_applied for line in partner_projection_lines)
    assert all(
        line.compliant_rate == 425.0 for line in partner_projection_lines if line.rate_cap_applied
    )

    expert_expense_line = next(line for line in projection.lines if line.expense_code == "E119")
    assert expert_expense_line.proposed_expenses == 34020.0
    assert expert_expense_line.compliant_expenses == 25000.0
    assert expert_expense_line.expense_cap_applied is True
    assert expert_expense_line.disallowed is False


def test_carrier_guideline_projection_applies_staffing_rules_and_leverage(
    tmp_path,
    repo_root,
):
    budget, _run_dir = _run_medmal_budget(tmp_path, repo_root)
    projection = budget.carrier_compliant_projection
    assert projection is not None

    proposal_line = next(line for line in budget.lines if line.external_code_candidate == "L310")
    projected_line = next(
        line for line in projection.lines if line.external_code_candidate == "L310"
    )

    assert proposal_line.staffing_role == "associate"
    assert proposal_line.hourly_rate == 250.0
    assert projected_line.staffing_role == "associate"
    assert projected_line.compliant_staffing_role == "paralegal"
    assert projected_line.staffing_rule_applied is True
    assert projected_line.staffing_rule_rate == 160.0
    assert projected_line.compliant_rate == 160.0
    assert projected_line.staffing_rule_delta > 0
    assert "staffing_rules/task_role_overrides/L310" in projected_line.guideline_refs[0]

    assert projection.basis.staffing_task_role_overrides["L310"] == "paralegal"
    assert projection.staffing_rule_adjusted_line_count >= 1
    assert projection.staffing_rule_delta >= projected_line.staffing_rule_delta
    assert projection.proposed_blended_rate is not None
    assert projection.compliant_blended_rate is not None
    assert projection.proposed_blended_rate > projection.compliant_blended_rate
    assert projection.blended_rate_delta > 0

    associate = next(
        summary for summary in projection.leverage_summary if summary.role == "associate"
    )
    paralegal = next(
        summary for summary in projection.leverage_summary if summary.role == "paralegal"
    )
    assert associate.compliant_hours < associate.proposed_hours
    assert paralegal.compliant_hours > paralegal.proposed_hours
    assert projection.rewrites_budget is False
    assert projection.not_authorized_for_client_submission is True
    assert projection.external_writes_performed is False


def test_carrier_guideline_projection_renders_in_review_forms(tmp_path, repo_root):
    budget, run_dir = _run_medmal_budget(tmp_path, repo_root)
    review_text = (run_dir / "legal_budget_review_form.md").read_text(encoding="utf-8")
    package_text = (run_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert budget.carrier_compliant_projection is not None
    assert "## Carrier-Compliant Projection" in review_text
    assert "### Carrier-Compliant Projection" in package_text
    assert "Projection rewrites budget: False" in review_text
    assert "Client/carrier submission authorized: False" in package_text
    assert "Staffing-rule delta:" in review_text
    assert "Blended-rate delta:" in review_text
    assert "Leverage summary:" in package_text
    assert "role=associate->paralegal" in package_text


def test_carrier_guideline_preapproval_thresholds_create_gate_and_dry_run_candidates(
    tmp_path,
    repo_root,
):
    budget, run_dir = _run_medmal_budget(tmp_path, repo_root)
    report = budget.carrier_preapproval_report

    assert report is not None
    assert report.status == "preapproval_required"
    assert report.required_count >= 3
    triggered = {
        requirement.threshold_id: requirement
        for requirement in report.requirements
        if requirement.status == "preapproval_required"
    }
    assert {"experts_over_count", "expert_spend_over_amount", "depositions_over_count"} <= set(
        triggered
    )
    assert triggered["experts_over_count"].current_value == 4
    assert triggered["expert_spend_over_amount"].current_value == 34020.0
    assert triggered["depositions_over_count"].current_value == 8
    assert all(
        requirement.required_human_gate == "human_carrier_preapproval"
        and requirement.preapproval_obtained is False
        and requirement.carrier_submission_authorized is False
        and requirement.rewrites_budget is False
        for requirement in triggered.values()
    )
    assert (run_dir / "carrier_preapproval_report.json").is_file()

    human_gate_report = load_json(run_dir / "human_gate_status_report.json")
    preapproval_gate = next(
        gate
        for gate in human_gate_report["gates"]
        if gate["gate_id"] == "human_carrier_preapproval"
    )
    assert preapproval_gate["status"] == "pending"
    assert preapproval_gate["completed_by_human"] is False
    assert "carrier_budget_submission" in preapproval_gate["blocks"]
    assert str(run_dir / "carrier_preapproval_report.json") in preapproval_gate["artifact_refs"]

    candidates = load_jsonl(run_dir / "exception_lake_candidates.jsonl")
    preapproval_candidates = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "carrier_preapproval_required"
    ]
    assert len(preapproval_candidates) == report.required_count
    assert all(
        candidate["canonical_lake_class"] == "workflow_escalation"
        and candidate["raw_payload_included"] is False
        and candidate["canonical_promotion_required"] is True
        for candidate in preapproval_candidates
    )

    mapping = ExceptionLakeMappingPackage.model_validate(
        load_json(run_dir / "exception_lake_mapping_package.json")
    )
    rule = next(
        item for item in mapping.rules if item.local_event_label == "carrier_preapproval_required"
    )
    assert rule.issue_family == "carrier_preapproval_required"
    assert rule.candidate_count == report.required_count
    assert "carrier_preapproval_report" in rule.support_ref_kinds


def test_carrier_guideline_preapproval_renders_in_review_forms(tmp_path, repo_root):
    budget, run_dir = _run_medmal_budget(tmp_path, repo_root)
    review_text = (run_dir / "legal_budget_review_form.md").read_text(encoding="utf-8")
    package_text = (run_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert budget.carrier_preapproval_report is not None
    assert "## Carrier Preapproval Requirements" in review_text
    assert "### Carrier Preapproval Requirements" in package_text
    assert "Preapproval status: preapproval_required" in review_text
    assert "Required human gate: human_carrier_preapproval" in package_text
    assert "Preapproval obtained: False" in package_text
    assert "Carrier submission authorized: False" in package_text


def test_real_carrier_guideline_artifact_is_rejected(tmp_path):
    path = tmp_path / "real-guideline.yaml"
    path.write_text(
        "\n".join(
            [
                "guideline_id: real",
                "status: candidate",
                "contains_real_carrier_guidelines: true",
                "data_scope: synthetic_only",
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_carrier_guideline(path)
    except ValueError as exc:
        assert "real carrier guidelines are prohibited" in str(exc)
    else:
        raise AssertionError("real carrier guideline fixture should be rejected")


def test_non_candidate_carrier_guideline_artifact_is_rejected(tmp_path):
    path = tmp_path / "promoted-guideline.yaml"
    path.write_text(
        "\n".join(
            [
                "guideline_id: promoted",
                "status: promoted",
                "contains_real_carrier_guidelines: false",
                "data_scope: synthetic_only",
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_carrier_guideline(path)
    except ValueError as exc:
        assert "candidate status" in str(exc)
    else:
        raise AssertionError("non-candidate guideline fixture should be rejected")
