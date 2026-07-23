"""CW1.3 — ordered, fail-closed AdjustmentLedger attribution."""

import pytest

from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import (
    ADJUSTMENT_LEDGER_ORDER,
    AdjustmentLedger,
    AdjustmentLedgerEntry,
    BudgetProposal,
)
from lawfirm_os_intake.util import load_json


def _projection(repo_root, carrier_id="synthetic-carrier-a"):
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


def test_projection_carries_ordered_reconciling_ledger(repo_root):
    projection = _projection(repo_root)
    ledger = projection.adjustment_ledger
    assert ledger is not None

    # Entries follow the declared attribution order.
    order_positions = [entry.order_index for entry in ledger.entries]
    assert order_positions == sorted(order_positions)
    assert ledger.entries[0].rule_kind == "pack_effective_selection"

    # Per-rule deltas sum to category deltas and to the total (exact minor units).
    recomputed: dict[str, int] = {}
    for entry in ledger.entries:
        recomputed[entry.rule_kind] = recomputed.get(entry.rule_kind, 0) + entry.delta_minor_units
    assert recomputed == ledger.category_delta_minor_units
    assert ledger.total_delta_minor_units == sum(ledger.category_delta_minor_units.values())
    assert ledger.total_delta_minor_units == sum(e.delta_minor_units for e in ledger.entries)


def test_ledger_total_reconciles_to_projection_signed_total(repo_root):
    projection = _projection(repo_root)
    ledger = projection.adjustment_ledger
    expected_minor = int(round(projection.total_delta_signed * 100))
    # Exact within a per-line rounding cent.
    assert abs(ledger.total_delta_minor_units - expected_minor) <= max(1, len(projection.lines))


def test_ledger_entries_reference_lines_by_stable_line_id(repo_root):
    projection = _projection(repo_root)
    line_ids = {line.line_id for line in projection.lines}
    for entry in projection.adjustment_ledger.entries:
        if entry.line_id is not None:
            assert entry.line_id in line_ids


def test_ledger_rejects_tampered_delta_fail_closed():
    good = AdjustmentLedgerEntry(
        order_index=3,
        rule_kind="rate_cap",
        rule_id="rate_cap::c::bl-1",
        line_id="bl-1",
        before_minor_units=10000,
        after_minor_units=9000,
        delta_minor_units=1000,
    )
    with pytest.raises(ValueError, match="category deltas do not equal"):
        AdjustmentLedger(
            entries=[good],
            category_delta_minor_units={"rate_cap": 999},  # tampered
            total_delta_minor_units=1000,
        )
    with pytest.raises(ValueError, match="after != before - delta"):
        AdjustmentLedgerEntry(
            order_index=3,
            rule_kind="rate_cap",
            rule_id="x",
            before_minor_units=10000,
            after_minor_units=9999,  # inconsistent
            delta_minor_units=1000,
        )


def test_adjustment_order_constant_is_the_declared_attribution_order():
    assert ADJUSTMENT_LEDGER_ORDER[:6] == (
        "pack_effective_selection",
        "task_hour_cap",
        "staffing_rule",
        "rate_cap",
        "expense_cap",
        "disallowance",
    )
