from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.models import (  # noqa: E402
    BlockedBudgetAttemptAuditReport,
    BudgetActualComparisonReport,
    BudgetActualPhaseComparison,
    BudgetDriverEffect,
    BudgetDriverProfileSummary,
    BudgetGuidelineFlag,
    BudgetProposal,
    BudgetPreconditionReport,
    BudgetFormMappingReport,
    BudgetFormTemplateAuditReport,
    BudgetScenarioSet,
    BudgetSubmissionGuardReport,
    BudgetSupportItem,
    ContractStateDependency,
    ContractStateReport,
    ContextBoundaryReport,
    ContextCounterfactualAuditReport,
    ConflictSeedPacket,
    CrossRepoPromotionPackage,
    CrossRepoPromotionProposal,
    DataScopeGateReport,
    DeadlineDocketingGuardReport,
    EffectiveContext,
    EvidenceCompletenessReport,
    EvidenceGraph,
    ExceptionLakeCandidate,
    ExceptionLakeHandoffManifest,
    ExceptionLakeMappingPackage,
    ExceptionLakeMappingRule,
    ExceptionLakeReadinessReport,
    FixtureGoldReport,
    FixtureGoldSpec,
    HumanConfirmation,
    HumanGateStatusReport,
    HumanReviewOutcomeRecord,
    IngestionResult,
    IngestionVolumeProfile,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    ModelAdapterReport,
    PartyCandidate,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
    RunEvent,
    RunLedgerIntegrityReport,
    RustIngestionReadinessReport,
    RustTransitionPolicy,
    SafetyGateReport,
    Segment,
    SourceBundle,
    StarterReleaseAuditReport,
)

MODELS = {
    "source-bundle.schema.json": SourceBundle,
    "blocked-budget-attempt-audit-report.schema.json": BlockedBudgetAttemptAuditReport,
    "context-counterfactual-audit-report.schema.json": ContextCounterfactualAuditReport,
    "cross-repo-promotion-package.schema.json": CrossRepoPromotionPackage,
    "cross-repo-promotion-proposal.schema.json": CrossRepoPromotionProposal,
    "ingestion-result.schema.json": IngestionResult,
    "ingestion-volume-profile.schema.json": IngestionVolumeProfile,
    "rust-ingestion-readiness-report.schema.json": RustIngestionReadinessReport,
    "rust-transition-policy.schema.json": RustTransitionPolicy,
    "segment.schema.json": Segment,
    "effective-context.schema.json": EffectiveContext,
    "party-candidate.schema.json": PartyCandidate,
    "contract-state-dependency.schema.json": ContractStateDependency,
    "contract-state-report.schema.json": ContractStateReport,
    "context-boundary-report.schema.json": ContextBoundaryReport,
    "data-scope-gate-report.schema.json": DataScopeGateReport,
    "model-adapter-report.schema.json": ModelAdapterReport,
    "evidence-completeness-report.schema.json": EvidenceCompletenessReport,
    "fixture-gold-spec.schema.json": FixtureGoldSpec,
    "fixture-gold-report.schema.json": FixtureGoldReport,
    "intake-preflight-packet.schema.json": IntakePreflightPacket,
    "deadline-docketing-guard-report.schema.json": DeadlineDocketingGuardReport,
    "human-confirmation.schema.json": HumanConfirmation,
    "human-gate-status-report.schema.json": HumanGateStatusReport,
    "human-review-outcome-record.schema.json": HumanReviewOutcomeRecord,
    "conflict-seed-packet.schema.json": ConflictSeedPacket,
    "budget-precondition-report.schema.json": BudgetPreconditionReport,
    "budget-form-mapping-report.schema.json": BudgetFormMappingReport,
    "budget-form-template-audit-report.schema.json": BudgetFormTemplateAuditReport,
    "budget-submission-guard-report.schema.json": BudgetSubmissionGuardReport,
    "matter-opening-readiness.schema.json": MatterOpeningReadiness,
    "legal-budget-proposal.schema.json": BudgetProposal,
    "budget-actual-comparison-report.schema.json": BudgetActualComparisonReport,
    "budget-actual-phase-comparison.schema.json": BudgetActualPhaseComparison,
    "budget-driver-effect.schema.json": BudgetDriverEffect,
    "budget-driver-profile-summary.schema.json": BudgetDriverProfileSummary,
    "budget-guideline-flag.schema.json": BudgetGuidelineFlag,
    "budget-scenario-set.schema.json": BudgetScenarioSet,
    "budget-support-item.schema.json": BudgetSupportItem,
    "evidence-graph.schema.json": EvidenceGraph,
    "run-ledger-event.schema.json": RunEvent,
    "run-ledger-integrity-report.schema.json": RunLedgerIntegrityReport,
    "exception-lake-candidate.schema.json": ExceptionLakeCandidate,
    "exception-lake-readiness-report.schema.json": ExceptionLakeReadinessReport,
    "exception-lake-handoff-manifest.schema.json": ExceptionLakeHandoffManifest,
    "exception-lake-mapping-package.schema.json": ExceptionLakeMappingPackage,
    "exception-lake-mapping-rule.schema.json": ExceptionLakeMappingRule,
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
