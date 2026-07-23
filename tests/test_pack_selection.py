"""CW1.1 — typed, fail-closed carrier pack selection.

A missing or wrong confirmed carrier must produce a typed
``blocked_missing_context`` decision and must NEVER silently fall back to the
guideline's ``default_carrier_id`` or price against it.
"""

import pytest

from lawfirm_os_intake.guidelines import (
    build_carrier_compliant_projection,
    load_carrier_guideline,
    select_pack,
)
from lawfirm_os_intake.models import BudgetProposal, PackSelectionDecision
from lawfirm_os_intake.util import load_json


def _guideline(repo_root):
    return load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")


def _budget(repo_root):
    payload = load_json(
        repo_root
        / "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
    )
    return BudgetProposal.model_validate(payload)


def test_select_pack_selects_confirmed_carrier_with_revision_and_content_hash(repo_root):
    decision = select_pack(_guideline(repo_root), carrier_id="synthetic-carrier-a")

    assert isinstance(decision, PackSelectionDecision)
    assert decision.status == "selected"
    assert decision.selected_pack_id == "synthetic-carrier-a"
    assert decision.selected_content_hash.startswith("sha256:")
    assert decision.selected_revision
    assert decision.blocked_reason is None
    selected = [pack for pack in decision.considered_packs if pack.included]
    assert [pack.pack_id for pack in selected] == ["synthetic-carrier-a"]


def test_select_pack_blocks_missing_carrier_without_default_fallback(repo_root):
    guideline = _guideline(repo_root)
    assert guideline.get("default_carrier_id")  # a default exists and must NOT be used

    decision = select_pack(guideline, carrier_id=None)

    assert decision.status == "blocked_missing_context"
    assert decision.selected_pack_id is None
    assert decision.selected_content_hash is None
    assert decision.blocked_reason == "missing_confirmed_carrier"
    # No pack — least of all the default — may be silently selected.
    assert not any(pack.included for pack in decision.considered_packs)


def test_select_pack_blocks_wrong_carrier_as_typed_missing_context(repo_root):
    decision = select_pack(_guideline(repo_root), carrier_id="carrier-not-in-guideline")

    assert decision.status == "blocked_missing_context"
    assert decision.selected_pack_id is None
    assert decision.blocked_reason == "confirmed_carrier_not_in_guideline"


def test_select_pack_content_hash_is_per_pack(repo_root):
    guideline = _guideline(repo_root)
    a = select_pack(guideline, carrier_id="synthetic-carrier-a")
    b = select_pack(guideline, carrier_id="synthetic-carrier-b")

    assert a.selected_content_hash != b.selected_content_hash


def test_projection_blocks_missing_carrier_instead_of_pricing_against_default(repo_root):
    guideline = _guideline(repo_root)
    budget = _budget(repo_root)

    # Missing confirmed carrier: must NOT produce a projection priced against the
    # default carrier. The old code silently priced against default_carrier_id.
    blocked = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id=None,
    )
    assert blocked is None

    # A confirmed carrier still projects, and carries the typed selection decision.
    selected = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id="synthetic-carrier-a",
    )
    assert selected is not None
    assert selected.pack_selection is not None
    assert selected.pack_selection.status == "selected"
    assert selected.pack_selection.selected_pack_id == "synthetic-carrier-a"


def test_pack_selection_decision_is_candidate_and_non_authoritative(repo_root):
    decision = select_pack(_guideline(repo_root), carrier_id="synthetic-carrier-a")
    dumped = decision.model_dump(mode="json")
    assert dumped["data_scope"] == "synthetic_only"
    assert dumped["non_authoritative"] is True
    with pytest.raises(ValueError):
        # Selected decisions must carry a pack id; a selected/None mismatch is rejected.
        PackSelectionDecision.model_validate({**dumped, "selected_pack_id": None})
