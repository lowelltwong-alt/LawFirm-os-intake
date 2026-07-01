import pytest
import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_facts import (
    run_labor_employment_budget_fact_audit,
)
from lawfirm_os_intake.models import LaborEmploymentBudgetFactAuditReport
from lawfirm_os_intake.util import load_json, write_json


MANIFEST_REF = "examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json"


def test_labor_employment_budget_fact_audit_surfaces_blocking_unknowns(tmp_path, repo_root):
    report, run_dir = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "le-budget-facts",
    )
    persisted = LaborEmploymentBudgetFactAuditReport.model_validate(
        load_json(run_dir / "labor_employment_budget_fact_audit_report.json")
    )

    assert persisted.labor_employment_budget_fact_audit_report_id == (
        report.labor_employment_budget_fact_audit_report_id
    )
    assert persisted.status == "labor_employment_budget_facts_ready_for_review"
    assert persisted.budget_readiness_state == "blocked_missing_critical_facts"
    assert persisted.finding_count >= 15
    assert persisted.source_bound_finding_count >= 6
    assert persisted.unknown_finding_count >= 5
    assert persisted.critical_gap_count >= 5
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.conflict_conclusion_emitted is False
    assert persisted.matter_opening_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False

    by_fact = {finding.fact_id: finding for finding in persisted.findings}
    assert by_fact["employee_claimant_identity"].source_bound is True
    assert by_fact["employer_or_defendant_identity"].source_bound is True
    assert by_fact["individual_supervisor_or_manager_defendants"].current_state == (
        "unknown_missing"
    )
    assert by_fact["joint_employer_or_affiliate_structure"].current_state == "unknown_missing"
    assert by_fact["prospective_client_payer_carrier_posture"].current_state == (
        "synthetic_context_requires_confirmation"
    )

    topology = persisted.relationship_topology
    assert topology.budget_treatment == "block_amount_budget"
    assert topology.person_candidate_count == 1
    assert topology.organization_candidate_count == 1
    assert topology.source_bound_relationship_count == 3
    assert topology.missing_or_review_relationship_count == 3
    assert topology.critical_relationship_gap_count == 3
    assert topology.unresolved_relationship_fact_ids == [
        "prospective_client_payer_carrier_posture",
        "individual_supervisor_or_manager_defendants",
        "joint_employer_or_affiliate_structure",
    ]
    assert topology.canonical_role_promotion_authorized is False
    assert topology.relationship_classification_authoritative is False

    critical_gap_ids = {gap.fact_id for gap in persisted.gaps if gap.severity == "critical"}
    assert "damages_categories_and_exposure" in critical_gap_ids
    assert "esi_custodians_and_sources" in critical_gap_ids
    assert "anticipated_depositions" in critical_gap_ids
    assert "carrier_guideline_and_rate_source" in critical_gap_ids

    notes = (run_dir / "labor_employment_budget_fact_audit_report.md").read_text(encoding="utf-8")
    assert "**Budget readiness:** blocked_missing_critical_facts" in notes
    assert "## Relationship Topology" in notes
    assert "individual_supervisor_or_manager_defendants" in notes
    assert "Budget submission authorized: False" in notes


def test_source_bound_budget_fact_findings_keep_exact_refs(tmp_path, repo_root):
    report, _ = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "source-bound-le-budget-facts",
    )

    for finding in report.findings:
        if finding.current_state == "unknown_missing":
            assert not finding.sources
            continue
        assert finding.sources, f"{finding.fact_id} has no source-bound support"
        for source in finding.sources:
            assert source.source_ref.source_segment_id
            assert source.source_ref.start_offset < source.source_ref.end_offset
            assert source.source_ref.sha256.startswith("sha256:")


def test_missing_employee_or_person_relationship_blocks_budget_readiness(
    tmp_path,
    repo_root,
):
    manifest = load_json(repo_root / MANIFEST_REF)
    manifest["conflict_seed_labels"] = [
        label
        for label in manifest["conflict_seed_labels"]
        if label["label_id"] != "label-conflict-employee"
    ]
    manifest_path = write_json(tmp_path / "missing-employee-manifest.json", manifest)

    report, _ = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=manifest_path,
        out_dir=tmp_path / "missing-employee-le-budget-facts",
    )

    employee_finding = next(
        finding for finding in report.findings if finding.fact_id == "employee_claimant_identity"
    )
    employee_gap = next(gap for gap in report.gaps if gap.fact_id == "employee_claimant_identity")
    assert employee_finding.current_state == "unknown_missing"
    assert employee_gap.severity == "critical"
    assert employee_gap.blocks_precise_budget is True
    assert report.budget_readiness_state == "blocked_missing_critical_facts"
    assert report.budget_amount_output_authorized is False
    assert "employee_claimant_identity" in (
        report.relationship_topology.unresolved_relationship_fact_ids
    )
    assert report.relationship_topology.person_candidate_count == 0
    assert report.relationship_topology.critical_relationship_gap_count == 4


def test_relationship_topology_counts_are_validated(tmp_path, repo_root):
    report, _ = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "relationship-topology-counts",
    )
    payload = report.model_dump(mode="json")
    payload["relationship_topology"]["critical_relationship_gap_count"] = 0

    with pytest.raises(ValueError, match="critical relationship gap count mismatch"):
        LaborEmploymentBudgetFactAuditReport.model_validate(payload)


def test_relationship_topology_check_fails_when_policy_bucket_is_missing(
    tmp_path,
    repo_root,
):
    policy = yaml.safe_load(
        (repo_root / "config" / "labor-employment-budget-fact-needs.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy["fact_needs"].append(
        {
            "fact_id": "union_or_agency_relationship",
            "fact_category": "entity_relationship",
            "required_level": "critical",
            "question": "Is a union, agency, DOL, NLRB, or other third-party employment actor implicated?",
            "budget_effects": ["party_count", "agency_record_review", "conflict_seed"],
            "human_confirmation_required": True,
            "recommended_budget_treatment": "hours_only_or_broad_range",
            "match": {"conflict_observed_roles": ["union", "agency"]},
        }
    )
    policy_path = tmp_path / "le-policy-with-unmapped-relationship.yaml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")

    report, _ = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        policy_path=policy_path,
        out_dir=tmp_path / "unmapped-relationship-policy",
    )

    check = next(
        check
        for check in report.checks
        if check.check_id == "relationship_topology_includes_entity_relationship_findings"
    )
    assert report.status == "blocked_labor_employment_budget_fact_audit"
    assert check.status == "failed"
    assert check.details["missing_from_topology"] == ["union_or_agency_relationship"]


def test_critical_budget_fact_gaps_must_block_budget_readiness(tmp_path, repo_root):
    report, _ = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "critical-gap-contract",
    )
    payload = report.model_dump(mode="json")
    payload["budget_readiness_state"] = "candidate_ready_for_budget_review"

    with pytest.raises(ValueError, match="critical gaps require blocked budget readiness"):
        LaborEmploymentBudgetFactAuditReport.model_validate(payload)


def test_labor_employment_budget_fact_audit_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-labor-employment-budget-facts",
            "--repo-root",
            str(repo_root),
            "--manifest",
            str(repo_root / MANIFEST_REF),
            "--out-dir",
            str(tmp_path / "le-budget-facts-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "labor_employment_budget_facts_ready_for_review"' in captured.out
    assert '"budget_readiness_state": "blocked_missing_critical_facts"' in captured.out
    assert '"budget_amount_output_authorized": false' in captured.out
    assert (
        tmp_path / "le-budget-facts-cli" / "labor_employment_budget_fact_audit_report.json"
    ).is_file()
