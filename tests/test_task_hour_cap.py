"""CW1.4 — one aggregate task x role hour cap, end-to-end and fail-closed."""

from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import BudgetProposal
from lawfirm_os_intake.util import load_json


def _projection(repo_root, carrier_id):
    budget = BudgetProposal.model_validate(
        load_json(
            repo_root
            / "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
        )
    )
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    return build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id=carrier_id,
    )


def test_aggregate_task_hour_cap_trips_and_reduces_hours(repo_root):
    projection = _projection(repo_root, "synthetic-carrier-a")
    capped = [line for line in projection.lines if line.task_hour_cap_applied]
    assert [(line.task_id, line.staffing_role) for line in capped] == [("L330", "senior_associate")]
    line = capped[0]
    assert line.compliant_hours == 24
    assert line.proposed_hours == 34
    # (34 - 24) hours * 325 synthetic rate = 3250 removed.
    assert line.task_hour_cap_delta_signed == 3250.0
    assert projection.task_hour_cap_delta == 3250.0


def test_task_hour_cap_is_ordered_first_in_the_ledger_and_reconciles(repo_root):
    projection = _projection(repo_root, "synthetic-carrier-a")
    ledger = projection.adjustment_ledger
    hour_cap_entries = [e for e in ledger.entries if e.rule_kind == "task_hour_cap"]
    assert hour_cap_entries and all(e.order_index == 1 for e in hour_cap_entries)
    assert ledger.category_delta_minor_units["task_hour_cap"] == 325000
    # Ledger still reconciles fail-closed with the new category present.
    assert ledger.total_delta_minor_units == sum(ledger.category_delta_minor_units.values())


def test_hour_cap_does_not_apply_where_no_cap_declared(repo_root):
    projection = _projection(repo_root, "synthetic-carrier-b")
    assert not any(line.task_hour_cap_applied for line in projection.lines)
    assert projection.task_hour_cap_delta == 0.0


def test_hour_cap_only_lowers_the_compliant_total(repo_root):
    capped = _projection(repo_root, "synthetic-carrier-a")
    # Metamorphic: the compliant total is not greater than the proposed total.
    assert capped.compliant_total is not None
    assert capped.compliant_total <= capped.proposed_total
