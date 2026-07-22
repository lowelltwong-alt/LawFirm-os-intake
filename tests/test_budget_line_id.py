"""CW1.2 — stable line_id on BudgetLine and projection lines."""

from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import BudgetLine, BudgetProposal, stable_budget_line_id
from lawfirm_os_intake.util import load_json


def _budget(repo_root):
    payload = load_json(
        repo_root
        / "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
    )
    return BudgetProposal.model_validate(payload)


def test_budget_line_id_is_recomputed_never_silently_empty():
    line = BudgetLine(
        phase_id="P100",
        phase_name="Assessment",
        task_id="L110",
        task_name="Fact investigation",
        staffing_role="associate",
        estimated_hours=10.0,
    )
    assert line.line_id
    assert line.line_id == stable_budget_line_id("P100", "L110", "associate", None)


def test_budget_line_id_is_stable_across_reconstruction(repo_root):
    first = _budget(repo_root)
    second = _budget(repo_root)
    assert [line.line_id for line in first.lines] == [line.line_id for line in second.lines]
    assert all(line.line_id for line in first.lines)


def test_projection_lines_inherit_source_line_id(repo_root):
    budget = _budget(repo_root)
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id="synthetic-carrier-a",
    )
    assert projection is not None
    source_ids = [line.line_id for line in budget.lines]
    projected_ids = [line.line_id for line in projection.lines]
    assert projected_ids == source_ids
    assert all(projected_ids)
