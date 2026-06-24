from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.models import (  # noqa: E402
    BudgetProposal,
    BudgetPreconditionReport,
    BudgetSupportItem,
    ContractStateDependency,
    ContractStateReport,
    ConflictSeedPacket,
    EffectiveContext,
    EvidenceGraph,
    ExceptionLakeCandidate,
    ExceptionLakeReadinessReport,
    FixtureGoldReport,
    FixtureGoldSpec,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IngestionResult,
    IngestionVolumeProfile,
    IntakePreflightPacket,
    ModelAdapterReport,
    PartyCandidate,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
    RunEvent,
    RustIngestionReadinessReport,
    SafetyGateReport,
    Segment,
    SourceBundle,
    StarterReleaseAuditReport,
)

MODELS = {
    "source-bundle.schema.json": SourceBundle,
    "ingestion-result.schema.json": IngestionResult,
    "ingestion-volume-profile.schema.json": IngestionVolumeProfile,
    "rust-ingestion-readiness-report.schema.json": RustIngestionReadinessReport,
    "segment.schema.json": Segment,
    "effective-context.schema.json": EffectiveContext,
    "party-candidate.schema.json": PartyCandidate,
    "contract-state-dependency.schema.json": ContractStateDependency,
    "contract-state-report.schema.json": ContractStateReport,
    "model-adapter-report.schema.json": ModelAdapterReport,
    "fixture-gold-spec.schema.json": FixtureGoldSpec,
    "fixture-gold-report.schema.json": FixtureGoldReport,
    "intake-preflight-packet.schema.json": IntakePreflightPacket,
    "human-confirmation.schema.json": HumanConfirmation,
    "human-review-outcome-record.schema.json": HumanReviewOutcomeRecord,
    "conflict-seed-packet.schema.json": ConflictSeedPacket,
    "budget-precondition-report.schema.json": BudgetPreconditionReport,
    "legal-budget-proposal.schema.json": BudgetProposal,
    "budget-support-item.schema.json": BudgetSupportItem,
    "evidence-graph.schema.json": EvidenceGraph,
    "run-ledger-event.schema.json": RunEvent,
    "exception-lake-candidate.schema.json": ExceptionLakeCandidate,
    "exception-lake-readiness-report.schema.json": ExceptionLakeReadinessReport,
    "review-package-manifest.schema.json": ReviewPackageManifest,
    "review-package-completeness-report.schema.json": ReviewPackageCompletenessReport,
    "starter-release-audit-report.schema.json": StarterReleaseAuditReport,
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
