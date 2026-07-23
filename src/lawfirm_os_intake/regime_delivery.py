"""CW7 — economic regime seam + end-of-program delivery packet.

Loads the data-only economic regime catalog (insurance-defense active; white-shoe
stub proving the seam) and assembles the delivery packet: capabilities, boundaries,
synthetic status, the hostile-swept artifact list, and the firm-data recalibration
path. Candidate-only, synthetic-only.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    DeliveryPacket,
    EconomicRegimeCatalog,
    EconomicRegimeProfile,
)
from .util import digest_json, now_iso

ECONOMIC_REGIME_CATALOG_REF = "config/synthetic-economic-regime-profiles.yaml"

HOSTILE_SWEPT_ARTIFACTS = (
    "PackSelectionDecision",
    "AdjustmentLedger",
    "SizedWorkPlan",
    "ProportionalityAssessment",
    "SettlementPostureAnalysis",
    "FirmExcelBudgetExport",
    "RouterEvaluationReport",
    "FirmCheckpointPacket",
    "OCGContractReconciliationReport",
)


def load_economic_regime_catalog(path: str | Path) -> EconomicRegimeCatalog:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("economic regime catalog must be a mapping")
    if payload.get("contains_real_firm_data", False):
        raise ValueError("real firm regime profiles are prohibited in this repository")
    if payload.get("data_origin") != "synthetic" or payload.get("candidate_only") is not True:
        raise ValueError("economic regime catalog must be synthetic candidate-only")
    profiles = [
        EconomicRegimeProfile(
            regime_id=str(profile["regime_id"]),
            label=str(profile["label"]),
            active=bool(profile["active"]),
            is_stub=bool(profile.get("is_stub", False)),
            payer=str(profile["payer"]),  # type: ignore[arg-type]
            rate_source=str(profile["rate_source"]),  # type: ignore[arg-type]
            constraint_pack_kind=str(profile["constraint_pack_kind"]),  # type: ignore[arg-type]
            proportionality_policy=str(profile["proportionality_policy"]),  # type: ignore[arg-type]
            staffing_norm=str(profile["staffing_norm"]),  # type: ignore[arg-type]
            transport=str(profile["transport"]),  # type: ignore[arg-type]
            notes=str(profile.get("notes", "")),
        )
        for profile in payload.get("profiles", [])
    ]
    return EconomicRegimeCatalog(
        catalog_id=str(payload.get("catalog_id", "unknown")),
        profiles=profiles,
        active_regime_id=str(payload["active_regime_id"]),
        corporate_ocg_as_pack_note=str(payload["corporate_ocg_as_pack_note"]),
    )


def build_delivery_packet(
    *, repo_root: str | Path, generated_at: str | None = None
) -> DeliveryPacket:
    root = Path(repo_root)
    catalog = load_economic_regime_catalog(root / ECONOMIC_REGIME_CATALOG_REF)
    capabilities = [
        "Fail-closed carrier pack selection (blocked_missing_context, no default fallback).",
        "Ordered, exact-minor-unit adjustment ledger reconciled to category and total deltas.",
        "Case sizing with a proportionality gate and settlement-posture cost-of-risk arithmetic.",
        "Exporter seam + firm-Excel renderer with corrected subtotal/grand-total formulas.",
        "Deterministic routing evaluation with abstention correctness and injection inertness.",
        "No-data firm checkpoint packet of three synthetic cases end to end.",
        "OCG IR contract reconciliation via candidate extensions + a local non-canonical adapter.",
        "Data-only economic regime seam (insurance-defense active; white-shoe stub).",
    ]
    boundaries = [
        "Synthetic-only, candidate-only; no real client/carrier/rate/firm data.",
        "No calibration or real-world accuracy claim (win probability is a declared input).",
        "No new rule language; Substrate owns the canonical OCG IR; no canonical IDs authored.",
        "Budget core is independent of the guideline compiler; work-plan total never overwritten.",
        "No budget submission, matter opening, connector, Lake/SQLite write, or external write.",
        "Human gates preserved: contract/sizing/export/routing review, firm checkpoint, Substrate review.",
    ]
    recalibration_path = [
        "Manually encode one real firm rate schedule + one real carrier/program pack in shadow mode with human reconciliation.",
        "Capture real outcomes (initial budget version, allowed hours/costs, censoring, pack version, line dispositions, reasons, appeals).",
        "Only after real dispositions exist do accuracy claims begin; ML runs as a shadow challenger, dollars stay deterministic from governed rates.",
        "All ingestion via the section 18 governance gate and the production data gate; no silent ingestion or learning.",
    ]
    open_gates = [
        "CW5 firm checkpoint: real firm dispositions (synthetic placeholders do not satisfy it).",
        "CW6 Substrate-owner review of the OCG IR extension proposal.",
        "Per-wave contract-review gates (CW1-CW4, CW7 delivery review).",
    ]
    basis = {"regime": catalog.active_regime_id, "artifacts": list(HOSTILE_SWEPT_ARTIFACTS)}
    return DeliveryPacket(
        packet_id="delivery-" + digest_json(basis).removeprefix("sha256:")[:16],
        program="Converged intake -> budget -> guideline-adjusted-reimbursement vertical (CW0-CW7).",
        capabilities=capabilities,
        boundaries=boundaries,
        hostile_sweep_artifacts=list(HOSTILE_SWEPT_ARTIFACTS),
        firm_data_recalibration_path=recalibration_path,
        open_human_gates=open_gates,
        active_regime_id=catalog.active_regime_id,
        generated_at=generated_at or now_iso(),
    )
