"""CW1.5 — output-language split: work plan vs reimbursement vs exposure."""

import pytest

from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import BudgetProposal, ProjectionReport
from lawfirm_os_intake.util import load_json


def _projection(repo_root, carrier_id="synthetic-carrier-a"):
    budget = BudgetProposal.model_validate(
        load_json(
            repo_root
            / "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
        )
    )
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id=carrier_id,
    )
    return budget, projection


def test_projection_report_splits_the_three_outputs(repo_root):
    budget, projection = _projection(repo_root)
    report = projection.projection_report
    assert report is not None
    # Work-plan total is the immutable proposal baseline, never the reimbursement.
    assert report.work_plan_total == budget.total_proposed_budget
    assert report.guideline_adjusted_reimbursement == projection.compliant_total
    assert report.guideline_adjusted_reimbursement != report.work_plan_total
    # Exposure reconciles exactly.
    assert report.unreimbursed_exposure == round(
        report.work_plan_total - report.guideline_adjusted_reimbursement, 2
    )
    assert report.unreimbursed_exposure == round(projection.total_delta_signed, 2)


def test_work_plan_total_is_not_overwritten_by_reimbursement(repo_root):
    _, projection = _projection(repo_root)
    report = projection.projection_report
    # A guideline that reduces the reimbursement must leave the work plan untouched.
    assert report.work_plan_total == projection.proposed_total
    assert report.work_plan_total >= (report.guideline_adjusted_reimbursement or 0)


def test_projection_report_rejects_broken_exposure_fail_closed():
    with pytest.raises(ValueError, match="unreimbursed_exposure must equal"):
        ProjectionReport(
            work_plan_total=100000.0,
            guideline_adjusted_reimbursement=90000.0,
            unreimbursed_exposure=5000.0,  # should be 10000.0
            reimbursement_priced=True,
        )
    with pytest.raises(ValueError, match="must not carry reimbursement or exposure"):
        ProjectionReport(
            work_plan_total=100000.0,
            guideline_adjusted_reimbursement=90000.0,
            unreimbursed_exposure=None,
            reimbursement_priced=False,
        )
