from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.models import (  # noqa: E402
    BudgetProposal,
    BudgetSupportItem,
    ConflictSeedPacket,
    EffectiveContext,
    EvidenceGraph,
    ExceptionLakeCandidate,
    HumanConfirmation,
    IntakePreflightPacket,
    PartyCandidate,
    ReviewPackageManifest,
    RunEvent,
    SafetyGateReport,
    Segment,
    SourceBundle,
)

MODELS = {
    "source-bundle.schema.json": SourceBundle,
    "segment.schema.json": Segment,
    "effective-context.schema.json": EffectiveContext,
    "party-candidate.schema.json": PartyCandidate,
    "intake-preflight-packet.schema.json": IntakePreflightPacket,
    "human-confirmation.schema.json": HumanConfirmation,
    "conflict-seed-packet.schema.json": ConflictSeedPacket,
    "legal-budget-proposal.schema.json": BudgetProposal,
    "budget-support-item.schema.json": BudgetSupportItem,
    "evidence-graph.schema.json": EvidenceGraph,
    "run-ledger-event.schema.json": RunEvent,
    "exception-lake-candidate.schema.json": ExceptionLakeCandidate,
    "review-package-manifest.schema.json": ReviewPackageManifest,
    "safety-gate-report.schema.json": SafetyGateReport,
}


def main() -> int:
    target = ROOT / "schemas"
    target.mkdir(exist_ok=True)
    for filename, model in MODELS.items():
        (target / filename).write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"exported {len(MODELS)} schemas to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
