"""CW6 — OCG IR extension proposal + local adapter + sibling conformance."""

import pytest

from lawfirm_os_intake.models import (
    OCGContractReconciliationReport,
    OCGRuleKindExtensionProposal,
    SiblingConformanceReport,
)
from lawfirm_os_intake.ocg_contract_reconciliation import (
    build_extension_proposal,
    build_ocg_contract_reconciliation_report,
    run_sibling_conformance,
)
from lawfirm_os_intake.ocg_rule_ir import SUBSTRATE_OWNER


def test_extension_proposal_covers_three_kinds_and_authors_no_canonical_ids():
    proposal = build_extension_proposal()
    assert isinstance(proposal, OCGRuleKindExtensionProposal)
    assert proposal.authors_no_canonical_ids is True
    assert proposal.requires_substrate_owner_review is True
    assert proposal.source_owner_required == SUBSTRATE_OWNER
    assert {kind.proposed_kind for kind in proposal.proposed_kinds} == {
        "task_hour_allowance",
        "ordered_attribution",
        "applicability_envelope",
    }


def test_reconciliation_local_adapter_has_zero_canonical_id_violations(repo_root):
    report = build_ocg_contract_reconciliation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    assert isinstance(report, OCGContractReconciliationReport)
    assert report.adapter_canonical_rule_id_violation_count == 0
    assert report.adapter_source_owner_violation_count == 0
    assert report.adapter_blocker_count == 0
    assert report.requires_substrate_owner_review is True


def test_sibling_conformance_is_fail_closed_when_absent(repo_root):
    report = run_sibling_conformance(
        repo_root=repo_root,
        checked_refs=["carrier_compliant_projection:x"],
    )
    assert isinstance(report, SiblingConformanceReport)
    assert report.sibling_is_read_only_challenger is True
    # The sibling simulator is not present in this workspace -> typed blocked, never
    # an assumed-passing conformance.
    assert report.sibling_available is False
    assert report.status == "blocked_sibling_unavailable"
    assert report.checked_cw1_output_refs == ["carrier_compliant_projection:x"]


def test_reconciliation_report_is_deterministic(repo_root):
    first = build_ocg_contract_reconciliation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    second = build_ocg_contract_reconciliation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_reconciliation_report_rejects_canonical_id_violation(repo_root):
    report = build_ocg_contract_reconciliation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    dumped = report.model_dump()
    dumped["adapter_canonical_rule_id_violation_count"] = 1
    with pytest.raises(ValueError):
        OCGContractReconciliationReport.model_validate(dumped)
