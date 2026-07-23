"""CW7 — economic regime seam + delivery packet + differential/monotonicity fuzz."""

import pytest

from lawfirm_os_intake.guidelines import build_carrier_compliant_projection, load_carrier_guideline
from lawfirm_os_intake.models import (
    BudgetProposal,
    DeliveryPacket,
    EconomicRegimeCatalog,
)
from lawfirm_os_intake.regime_delivery import (
    ECONOMIC_REGIME_CATALOG_REF,
    HOSTILE_SWEPT_ARTIFACTS,
    build_delivery_packet,
    load_economic_regime_catalog,
)
from lawfirm_os_intake.util import load_json

_BUDGET_REF = "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"


def _budget(repo_root):
    return BudgetProposal.model_validate(load_json(repo_root / _BUDGET_REF))


def test_economic_regime_catalog_has_one_active_and_a_stub(repo_root):
    catalog = load_economic_regime_catalog(repo_root / ECONOMIC_REGIME_CATALOG_REF)
    assert isinstance(catalog, EconomicRegimeCatalog)
    active = [profile for profile in catalog.profiles if profile.active]
    assert len(active) == 1
    assert active[0].regime_id == "insurance_defense"
    assert active[0].payer == "carrier"
    stubs = [profile for profile in catalog.profiles if profile.is_stub]
    assert stubs and stubs[0].constraint_pack_kind == "corporate_ocg_pack"
    assert "same rule" in catalog.corporate_ocg_as_pack_note.lower()


def test_regime_catalog_rejects_two_active_profiles(repo_root):
    catalog = load_economic_regime_catalog(repo_root / ECONOMIC_REGIME_CATALOG_REF)
    dumped = catalog.model_dump()
    dumped["profiles"][1]["active"] = True  # activate the stub too
    with pytest.raises(ValueError):
        EconomicRegimeCatalog.model_validate(dumped)


def test_delivery_packet_lists_capabilities_boundaries_and_recalibration(repo_root):
    packet = build_delivery_packet(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    assert isinstance(packet, DeliveryPacket)
    assert packet.synthetic_status == "synthetic_only_candidate"
    assert packet.active_regime_id == "insurance_defense"
    assert packet.capabilities and packet.boundaries and packet.firm_data_recalibration_path
    assert set(packet.hostile_sweep_artifacts) == set(HOSTILE_SWEPT_ARTIFACTS)
    # The firm checkpoint remains an open human gate.
    assert any("firm checkpoint" in gate.lower() for gate in packet.open_human_gates)


def test_delivery_packet_is_deterministic(repo_root):
    first = build_delivery_packet(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    second = build_delivery_packet(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def _projection(repo_root, carrier_id):
    guideline = load_carrier_guideline(repo_root / "config/synthetic-carrier-guideline.yaml")
    return build_carrier_compliant_projection(
        _budget(repo_root),
        guideline=guideline,
        guideline_ref="config/synthetic-carrier-guideline.yaml",
        carrier_id=carrier_id,
    )


def test_differential_packs_are_internally_consistent_and_distinct(repo_root):
    a = _projection(repo_root, "synthetic-carrier-a")
    b = _projection(repo_root, "synthetic-carrier-b")
    assert a is not None and b is not None
    # Distinct packs -> distinct content hashes; each ledger reconciles fail-closed.
    assert a.pack_selection.selected_content_hash != b.pack_selection.selected_content_hash
    for projection in (a, b):
        ledger = projection.adjustment_ledger
        assert ledger is not None
        assert ledger.total_delta_minor_units == sum(e.delta_minor_units for e in ledger.entries)


def test_monotonicity_signed_deltas_partition_the_total(repo_root):
    # Category signed deltas partition the projection total delta (within rounding).
    for carrier_id in ("synthetic-carrier-a", "synthetic-carrier-b"):
        projection = _projection(repo_root, carrier_id)
        category_sum = round(
            projection.rate_cap_delta_signed
            + projection.expense_cap_delta_signed
            + projection.disallowed_delta_signed
            + projection.staffing_rule_delta_signed
            + projection.contingency_delta_signed
            + getattr(projection, "task_hour_cap_delta_signed", 0.0),
            2,
        )
        assert abs(category_sum - projection.total_delta_signed) <= 0.02
