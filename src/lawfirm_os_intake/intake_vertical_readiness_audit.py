from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import ValidationError

from .models import (
    BudgetCalibrationReadinessReport,
    BudgetFixtureUpdatePRPackageReport,
    BudgetFixtureUpdateReviewReport,
    BudgetLakeAdmissionBundleReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
    LearningOwnerHandoffReport,
    LearningPromotionReadinessReport,
    LearningProposedChangeSet,
    LearningShadowEvalPlan,
    LearningShadowEvalResultReport,
    ReviewedLearningGateReport,
    StrictModel,
)
from .util import load_json, now_iso, write_json


INTAKE_VERTICAL_READINESS_AUDIT_FILENAME = "intake_vertical_readiness_audit_report.json"
INTAKE_VERTICAL_READINESS_AUDIT_NOTES_FILENAME = "intake_vertical_readiness_audit_report.md"


@dataclass(frozen=True)
class SliceDefinition:
    slice_id: int
    title: str
    requirement_summary: str
    proof_artifact_refs: tuple[str, ...]
    command_refs: tuple[str, ...]
    target_owner_repos: tuple[str, ...]
    remaining_external_actions: tuple[str, ...]


REQUIRED_SLICES: tuple[SliceDefinition, ...] = (
    SliceDefinition(
        slice_id=1,
        title="Core intake-to-budget gates",
        requirement_summary=(
            "Preflight, human confirmation, conflict seed, budget proposal, safety, "
            "and review-package completeness stay local, synthetic, and human-gated."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/workflow.py",
            "schemas/intake-preflight-packet.schema.json",
            "schemas/legal-budget-proposal.schema.json",
            "schemas/budget-precondition-report.schema.json",
            "schemas/safety-gate-report.schema.json",
            "schemas/review-package-completeness-report.schema.json",
            "tests/test_cli_demo.py",
            "tests/test_safety_gate_report.py",
        ),
        command_refs=("preflight", "build-budget", "demo"),
        target_owner_repos=("LawFirm-os-intake", "LawFirm-os-orchestrator"),
        remaining_external_actions=(
            "Orchestrator must own any production workflow execution.",
            "Human review remains required before conflicts, engagement, matter opening, or budget submission.",
        ),
    ),
    SliceDefinition(
        slice_id=2,
        title="Budget revisions and actuals lifecycle",
        requirement_summary=(
            "Human budget changes and actual-vs-budget variance remain append-only "
            "candidate evidence without mutating original proposals."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_revisions.py",
            "src/lawfirm_os_intake/budget_actuals.py",
            "schemas/budget-review-change-record.schema.json",
            "schemas/budget-revision-report.schema.json",
            "schemas/budget-actual-comparison-report.schema.json",
            "tests/test_budget_revisions_and_actuals.py",
        ),
        command_refs=("record-budget-review", "compare-budget-actuals"),
        target_owner_repos=("LawFirm-os-intake", "LawFirm-os-exceptions-lake-runtime"),
        remaining_external_actions=(
            "Exception Lake must own admitted records and SQLite persistence.",
            "Future real actuals must arrive through Orchestrator under a governed billing-read contract.",
        ),
    ),
    SliceDefinition(
        slice_id=3,
        title="Carrier rejection capture and learning lane",
        requirement_summary=(
            "Carrier rejection capture, review, learning proposals, Orchestrator interface, "
            "Lake admission proposal, and carrier roadmap audit exist as local candidates."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejections.py",
            "src/lawfirm_os_intake/carrier_rejection_review.py",
            "src/lawfirm_os_intake/carrier_rejection_learning.py",
            "src/lawfirm_os_intake/carrier_rejection_orchestrator_interface.py",
            "src/lawfirm_os_intake/carrier_rejection_lake_admission.py",
            "src/lawfirm_os_intake/carrier_rejection_roadmap_audit.py",
            "tests/test_carrier_rejection_capture.py",
            "tests/test_carrier_rejection_roadmap_audit.py",
        ),
        command_refs=(
            "capture-carrier-rejections",
            "review-carrier-rejections",
            "propose-carrier-rejection-learning",
            "draft-carrier-rejection-orchestrator-interface",
            "draft-carrier-rejection-lake-admission",
            "audit-carrier-rejection-roadmap",
        ),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ),
        remaining_external_actions=(
            "Orchestrator must own production portal/email/workbook capture and appeal submission.",
            "Exception Lake must own append-only admitted rejection records.",
        ),
    ),
    SliceDefinition(
        slice_id=4,
        title="Reviewed learning gate",
        requirement_summary=(
            "Carrier learning proposals, human budget revision deltas, and actual variance "
            "drivers aggregate into blocked reviewed-learning candidates."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/reviewed_learning_gate.py",
            "schemas/reviewed-learning-gate-candidate.schema.json",
            "schemas/reviewed-learning-gate-report.schema.json",
            "tests/test_reviewed_learning_gate.py",
            "docs/decisions/TRACE-2026-06-26-reviewed-learning-gate.md",
        ),
        command_refs=("review-learning-gate",),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Human-reviewed outcome evidence is required before learning review can continue.",
        ),
    ),
    SliceDefinition(
        slice_id=5,
        title="Promotion readiness and proposed changes",
        requirement_summary=(
            "Readiness audit, shadow-eval plan, and proposed-change artifacts exist "
            "without applying or promoting candidate changes."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/learning_promotion_readiness.py",
            "src/lawfirm_os_intake/learning_proposed_changes.py",
            "schemas/learning-promotion-readiness-report.schema.json",
            "schemas/learning-proposed-change-set.schema.json",
            "tests/test_learning_promotion_readiness.py",
            "tests/test_learning_proposed_changes.py",
        ),
        command_refs=("audit-learning-promotion-readiness", "draft-learning-proposed-changes"),
        target_owner_repos=("LawFirm-os-intake", "LawFirm-os-semantic-substrate"),
        remaining_external_actions=(
            "Owning repos must review proposed changes before implementation or promotion.",
        ),
    ),
    SliceDefinition(
        slice_id=6,
        title="Shadow-eval results",
        requirement_summary=(
            "Synthetic fixture results distinguish passed, failed, and blocked proposed "
            "changes while keeping owner review required."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/learning_shadow_eval_fixture_results.py",
            "src/lawfirm_os_intake/learning_shadow_eval_results.py",
            "schemas/learning-shadow-eval-fixture-evidence-report.schema.json",
            "schemas/learning-shadow-eval-fixture-result.schema.json",
            "schemas/learning-shadow-eval-result-report.schema.json",
            "tests/test_learning_shadow_eval_fixture_results.py",
            "tests/test_learning_shadow_eval_results.py",
            "docs/decisions/TRACE-2026-06-26-learning-shadow-eval-fixture-evidence.md",
            "docs/decisions/TRACE-2026-06-26-learning-shadow-eval-results.md",
        ),
        command_refs=(
            "record-learning-shadow-eval-fixture-results",
            "run-learning-shadow-eval",
        ),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Passing synthetic eval evidence must still be reviewed by the owning repo.",
        ),
    ),
    SliceDefinition(
        slice_id=7,
        title="Owner handoff packages",
        requirement_summary=(
            "Passed, failed, and blocked learning candidates are separated by owning repo "
            "without sibling-repo writes or promotion."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/learning_owner_handoffs.py",
            "schemas/learning-owner-handoff-report.schema.json",
            "schemas/learning-owner-handoff-package.schema.json",
            "tests/test_learning_owner_handoffs.py",
            "docs/decisions/TRACE-2026-06-26-learning-owner-handoffs.md",
        ),
        command_refs=("build-learning-owner-handoffs",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
            "LawFirm-os-semantic-substrate",
        ),
        remaining_external_actions=(
            "Sibling repo owners must decide whether any implementation work is warranted.",
        ),
    ),
    SliceDefinition(
        slice_id=8,
        title="Cross-repo promotion package and docs",
        requirement_summary=(
            "Promotion inventory, data-flow map, endpoints, roadmap, and evaluation plan "
            "describe candidate contracts and external adoption boundaries."
        ),
        proof_artifact_refs=(
            "promotion/cross_repo_promotion_package.json",
            "docs/cross-repo-promotion-package.md",
            "DATA_FLOW_MAP.md",
            "ENDPOINTS_AND_COMMANDS.md",
            "docs/roadmap.md",
            "docs/evaluation-plan.md",
        ),
        command_refs=(),
        target_owner_repos=(
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ),
        remaining_external_actions=(
            "Semantic Substrate, Orchestrator, and Exception Lake must promote/adopt any accepted pieces inside their own repos.",
        ),
    ),
    SliceDefinition(
        slice_id=9,
        title="Budget event Lake review bundle",
        requirement_summary=(
            "Budget change, actual-variance, and carrier-rejection decision ledgers "
            "can be bundled into hash-addressed candidate evidence for Exception Lake owner review."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_lake_admission_bundle.py",
            "schemas/budget-lake-admission-bundle-report.schema.json",
            "schemas/budget-lake-evidence-artifact.schema.json",
            "tests/test_budget_lake_admission_bundle.py",
            "docs/decisions/TRACE-2026-06-26-budget-event-lake-bundle.md",
        ),
        command_refs=("build-budget-event-lake-bundle",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-exceptions-lake-runtime",
            "LawFirm-os-orchestrator",
        ),
        remaining_external_actions=(
            "Exception Lake must validate and admit any runtime records under its own schemas.",
            "Orchestrator must assemble governed evidence packets before real Lake handoff.",
        ),
    ),
    SliceDefinition(
        slice_id=10,
        title="Budget calibration readiness",
        requirement_summary=(
            "Synthetic corpus replay, human replay outcome, fixture-binding candidates, "
            "and fixture-update handoff are auditable before any manual fixture-update PR."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_calibration_readiness.py",
            "schemas/budget-calibration-readiness-report.schema.json",
            "schemas/budget-calibration-readiness-check.schema.json",
            "tests/test_budget_calibration_readiness.py",
            "docs/decisions/TRACE-2026-06-26-budget-calibration-readiness.md",
        ),
        command_refs=("audit-budget-calibration-readiness",),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Humans must review any fixture update in a separate change before learning use.",
        ),
    ),
    SliceDefinition(
        slice_id=11,
        title="Manual fixture-update review record",
        requirement_summary=(
            "Approved synthetic replay outputs can be accepted or rejected for a separate "
            "fixture-update PR with append-only local review evidence and no fixture mutation."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_fixture_update_review.py",
            "schemas/budget-fixture-update-review-record.schema.json",
            "schemas/budget-fixture-update-review-report.schema.json",
            "tests/test_budget_fixture_update_review.py",
            "docs/decisions/TRACE-2026-06-26-budget-fixture-update-review.md",
        ),
        command_refs=("record-budget-fixture-update-review",),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Any accepted fixture update must happen in a separate human-reviewed PR.",
        ),
    ),
    SliceDefinition(
        slice_id=12,
        title="Manual fixture-update PR package",
        requirement_summary=(
            "Accepted fixture-update review decisions can be packaged as a separate "
            "manual PR plan without creating a PR or editing fixtures."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_fixture_update_pr_package.py",
            "schemas/budget-fixture-update-pr-package-report.schema.json",
            "schemas/budget-fixture-update-pr-package-item.schema.json",
            "tests/test_budget_fixture_update_pr_package.py",
            "docs/decisions/TRACE-2026-06-26-budget-fixture-update-pr-package.md",
        ),
        command_refs=("build-budget-fixture-update-pr-package",),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Humans must create, review, and merge any fixture update in a separate PR.",
        ),
    ),
    SliceDefinition(
        slice_id=13,
        title="Budget lifecycle audit",
        requirement_summary=(
            "Budget change, actual variance, carrier rejection, and Lake-bundle evidence "
            "can be audited together as one local lifecycle review surface."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_lifecycle_audit.py",
            "schemas/budget-lifecycle-audit-report.schema.json",
            "schemas/budget-lifecycle-financial-summary.schema.json",
            "tests/test_budget_lifecycle_audit.py",
            "docs/decisions/TRACE-2026-06-26-budget-lifecycle-audit.md",
        ),
        command_refs=("audit-budget-lifecycle",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ),
        remaining_external_actions=(
            "Orchestrator and Exception Lake owners must still adopt runtime capture and admission.",
        ),
    ),
    SliceDefinition(
        slice_id=14,
        title="Budget lifecycle owner adoption packets",
        requirement_summary=(
            "Budget lifecycle audit evidence can be routed to Semantic Substrate, "
            "Orchestrator, and Exception Lake owner-review packets without sibling writes."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/budget_lifecycle_owner_adoption.py",
            "schemas/budget-lifecycle-owner-adoption-report.schema.json",
            "schemas/budget-lifecycle-owner-adoption-packet.schema.json",
            "tests/test_budget_lifecycle_owner_adoption.py",
            "docs/decisions/TRACE-2026-06-26-budget-lifecycle-owner-adoption.md",
        ),
        command_refs=("build-budget-lifecycle-owner-adoption",),
        target_owner_repos=(
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ),
        remaining_external_actions=(
            "Owning repos must review and implement any accepted lifecycle adoption work.",
        ),
    ),
    SliceDefinition(
        slice_id=15,
        title="Public source methodology audit",
        requirement_summary=(
            "Planning-only public-source methodology can be reviewed without ingesting "
            "public records, committing payloads, authorizing adapters, or permitting runtime use."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/public_source_methodology.py",
            "schemas/public-source-methodology-report.schema.json",
            "schemas/public-source-methodology-source.schema.json",
            "tests/test_public_source_methodology.py",
            "docs/decisions/TRACE-2026-06-26-public-source-methodology-audit.md",
            "examples/public/catalog.yaml",
            "docs/public-data-test-plan.md",
        ),
        command_refs=("audit-public-source-methodology",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-legal-knowledge-runtime",
        ),
        remaining_external_actions=(
            "Humans must review source license, privacy, and retention posture before any public-source adapter.",
            "Legal Knowledge Runtime must own any future public-source lookup adapter.",
        ),
    ),
    SliceDefinition(
        slice_id=16,
        title="Public synthetic fixture conversion plan",
        requirement_summary=(
            "Public-source methodology can be mapped to human-reviewed synthetic "
            "fixture conversion specs without ingesting public payloads, mutating "
            "fixtures, authorizing adapters, or writing Lake/SQLite records."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/public_synthetic_fixture_conversion.py",
            "schemas/public-synthetic-fixture-conversion-plan.schema.json",
            "schemas/public-synthetic-fixture-conversion-spec.schema.json",
            "tests/test_public_synthetic_fixture_conversion.py",
            "docs/decisions/TRACE-2026-06-26-public-synthetic-fixture-conversion-plan.md",
            "docs/public-data-test-plan.md",
        ),
        command_refs=("plan-public-synthetic-fixture-conversion",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-legal-knowledge-runtime",
        ),
        remaining_external_actions=(
            "Humans must review conversion specs before any synthetic fixture PR.",
            "Fixture generation must happen in a separate reviewed PR.",
            "Legal Knowledge Runtime must own any future lookup or retrieval adapter.",
        ),
    ),
    SliceDefinition(
        slice_id=17,
        title="Public synthetic fixture conversion review packet",
        requirement_summary=(
            "Public synthetic fixture conversion specs can be packaged for human "
            "review with recommendations, why-notes, red-team notes, and append-only "
            "decision templates without approving fixture generation or creating fixture PRs."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/public_synthetic_fixture_conversion_review.py",
            "schemas/public-synthetic-fixture-conversion-review-packet.schema.json",
            "schemas/public-synthetic-fixture-conversion-review-decision-template.schema.json",
            "tests/test_public_synthetic_fixture_conversion_review.py",
            "docs/decisions/TRACE-2026-06-26-public-synthetic-fixture-conversion-review.md",
            "docs/public-data-test-plan.md",
        ),
        command_refs=("review-public-synthetic-fixture-conversion",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-legal-knowledge-runtime",
        ),
        remaining_external_actions=(
            "Humans must record an append-only conversion review outcome before any fixture PR.",
            "Fixture generation must happen in a separate reviewed PR.",
            "Legal Knowledge Runtime must own any future lookup or retrieval adapter.",
        ),
    ),
    SliceDefinition(
        slice_id=18,
        title="Public synthetic fixture conversion review outcome record",
        requirement_summary=(
            "Human public synthetic fixture conversion decisions can be recorded as "
            "append-only local evidence without creating fixtures, ingesting public records, "
            "authorizing adapters, or writing Lake/SQLite records."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/public_synthetic_fixture_conversion_review_outcomes.py",
            "schemas/public-synthetic-fixture-conversion-review-record.schema.json",
            "schemas/public-synthetic-fixture-conversion-review-outcome-report.schema.json",
            "tests/test_public_synthetic_fixture_conversion_review_outcomes.py",
            "docs/decisions/TRACE-2026-06-26-public-synthetic-fixture-conversion-review-outcome.md",
            "docs/public-data-test-plan.md",
        ),
        command_refs=("record-public-synthetic-fixture-conversion-review",),
        target_owner_repos=(
            "LawFirm-os-intake",
            "LawFirm-os-legal-knowledge-runtime",
        ),
        remaining_external_actions=(
            "Fixture generation must still happen in a separate reviewed PR if a human approves conversion.",
            "Legal Knowledge Runtime must own any future lookup or retrieval adapter.",
            "Exception Lake must own any future admitted review-outcome event.",
        ),
    ),
    SliceDefinition(
        slice_id=19,
        title="Final intake vertical readiness audit",
        requirement_summary=(
            "A deterministic final audit checks local surfaces plus the generated learning "
            "artifact chain, budget-event Lake bundle, calibration-readiness chain, "
            "fixture-update review record, and fixture-update PR package before humans consider marking the PR ready."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/intake_vertical_readiness_audit.py",
            "schemas/intake-vertical-readiness-audit-report.schema.json",
            "schemas/intake-vertical-readiness-artifact-check.schema.json",
            "tests/test_intake_vertical_readiness_audit.py",
        ),
        command_refs=("audit-intake-vertical-readiness",),
        target_owner_repos=("LawFirm-os-intake",),
        remaining_external_actions=(
            "Humans must review this audit before changing PR draft/ready state.",
        ),
    ),
)

COMMAND_SEARCH_REFS = (
    "src/lawfirm_os_intake/cli.py",
    "ENDPOINTS_AND_COMMANDS.md",
    "README.md",
    "DATA_FLOW_MAP.md",
    "docs/roadmap.md",
)

REQUIRED_EXTERNAL_ADOPTION_ACTIONS = (
    "Human reviewer must decide whether PR #7 should leave draft state.",
    "Semantic Substrate must own any canonical schema, event-label, route-ID, or lifecycle promotion.",
    "Orchestrator must own production workflow execution, connectors, human pauses, billing reads, and appeal submission gates.",
    "Exception Lake must own append-only runtime evidence admission, SQLite migrations if approved, record hashes, and supersession.",
    "Exception Lake must review the budget-event Lake bundle before any budget, actuals, rejection, appeal, or financial-outcome event is admitted.",
    "Real client, matter, carrier guideline, actual-cost, and rate data require separate governance approval before pilot use.",
)

T = TypeVar("T", bound=StrictModel)


def _read_command_surface(repo_root: Path) -> str:
    chunks: list[str] = []
    for ref in COMMAND_SEARCH_REFS:
        path = repo_root / ref
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _resolve_ref(ref: str | None, *, repo_root: Path, base_dir: Path | None = None) -> Path | None:
    if not ref:
        return None
    path = Path(ref)
    if path.is_absolute():
        return path
    if base_dir is not None and (base_dir / path).exists():
        return base_dir / path
    return repo_root / path


def _slice_status(
    definition: SliceDefinition,
    *,
    repo_root: Path,
    command_surface: str,
) -> IntakeVerticalReadinessSliceStatus:
    missing_artifacts = [
        ref for ref in definition.proof_artifact_refs if not (repo_root / ref).is_file()
    ]
    missing_commands = [
        command for command in definition.command_refs if command not in command_surface
    ]
    status = (
        "implemented_local_candidate"
        if not missing_artifacts and not missing_commands
        else "missing_required_artifact"
    )
    return IntakeVerticalReadinessSliceStatus(
        slice_id=definition.slice_id,
        title=definition.title,
        status=status,
        requirement_summary=definition.requirement_summary,
        proof_artifact_refs=list(definition.proof_artifact_refs),
        missing_artifact_refs=missing_artifacts,
        command_refs=list(definition.command_refs),
        missing_command_refs=missing_commands,
        target_owner_repos=list(definition.target_owner_repos),  # type: ignore[arg-type]
        remaining_external_actions=list(definition.remaining_external_actions),
    )


def _artifact_check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_ref: str | None = None,
    missing_refs: list[str] | None = None,
) -> IntakeVerticalReadinessArtifactCheck:
    return IntakeVerticalReadinessArtifactCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        artifact_ref=artifact_ref,
        message=message,
        missing_refs=missing_refs or [],
    )


def _ref_is_file(ref: str, *, repo_root: Path, base_dir: Path | None = None) -> bool:
    resolved = _resolve_ref(ref, repo_root=repo_root, base_dir=base_dir)
    return bool(resolved and resolved.is_file())


def _ref_matches_path(
    ref: str,
    target: Path,
    *,
    repo_root: Path,
    base_dir: Path | None = None,
) -> bool:
    resolved = _resolve_ref(ref, repo_root=repo_root, base_dir=base_dir)
    if resolved is None or not resolved.exists() or not target.exists():
        return False
    return resolved.resolve() == target.resolve()


def _load_model(
    model_type: type[T],
    path: Path | None,
    check_id: str,
    checks: list[IntakeVerticalReadinessArtifactCheck],
) -> T | None:
    if path is None or not path.is_file():
        checks.append(
            _artifact_check(
                check_id,
                False,
                "Required generated learning artifact is missing.",
                artifact_ref=str(path) if path else None,
                missing_refs=[str(path)] if path else [],
            )
        )
        return None
    try:
        model = model_type.model_validate(load_json(path))
    except (OSError, ValueError, ValidationError) as exc:
        checks.append(
            _artifact_check(
                check_id,
                False,
                f"Generated learning artifact failed validation: {exc}",
                artifact_ref=str(path),
            )
        )
        return None
    checks.append(
        _artifact_check(
            check_id,
            True,
            "Generated learning artifact exists and validates.",
            artifact_ref=str(path),
        )
    )
    return model


def _check_learning_artifact_chain(
    *,
    owner_handoff_report_path: Path,
    repo_root: Path,
) -> list[IntakeVerticalReadinessArtifactCheck]:
    checks: list[IntakeVerticalReadinessArtifactCheck] = []
    owner_report = _load_model(
        LearningOwnerHandoffReport,
        owner_handoff_report_path,
        "owner_handoff_report_valid",
        checks,
    )
    if owner_report is None:
        return checks

    package_missing = [
        ref
        for ref in owner_report.package_output_refs
        if not _ref_is_file(
            ref,
            repo_root=repo_root,
            base_dir=owner_handoff_report_path.parent,
        )
    ]
    checks.append(
        _artifact_check(
            "owner_handoff_package_refs_exist",
            not package_missing
            and bool(owner_report.package_output_refs or not owner_report.packages),
            "Owner handoff package refs exist for every package.",
            artifact_ref=str(owner_handoff_report_path),
            missing_refs=package_missing,
        )
    )
    checks.append(
        _artifact_check(
            "owner_handoff_ready_without_writes",
            owner_report.status == "owner_handoff_ready_review_required"
            and owner_report.failed_candidate_count == 0
            and owner_report.blocked_candidate_count == 0
            and owner_report.promotion_authorized is False
            and owner_report.proposed_changes_applied is False
            and owner_report.external_writes_performed is False,
            "Owner handoff report is ready for human PR review, with no failed/blocked candidates and no writes.",
            artifact_ref=str(owner_handoff_report_path),
        )
    )

    shadow_path = _resolve_ref(
        owner_report.source_shadow_eval_result_report_ref,
        repo_root=repo_root,
        base_dir=owner_handoff_report_path.parent,
    )
    shadow_report = _load_model(
        LearningShadowEvalResultReport,
        shadow_path,
        "shadow_eval_result_report_valid",
        checks,
    )
    if shadow_report is None:
        return checks
    checks.append(
        _artifact_check(
            "shadow_eval_results_passed_without_writes",
            shadow_report.status == "shadow_eval_passed_owner_review_required"
            and shadow_report.failed_result_count == 0
            and shadow_report.blocked_result_count == 0
            and shadow_report.promotion_authorized is False
            and shadow_report.proposed_changes_applied is False
            and shadow_report.external_writes_performed is False,
            "Shadow eval report passed locally while preserving owner review and no-write boundaries.",
            artifact_ref=str(shadow_path),
        )
    )

    change_set_path = _resolve_ref(
        shadow_report.source_proposed_change_set_ref,
        repo_root=repo_root,
        base_dir=shadow_path.parent if shadow_path else None,
    )
    change_set = _load_model(
        LearningProposedChangeSet,
        change_set_path,
        "proposed_change_set_valid",
        checks,
    )
    if change_set is None:
        return checks
    checks.append(
        _artifact_check(
            "proposed_changes_draft_only",
            change_set.status == "draft_candidates_ready_for_human_review"
            and change_set.promotion_authorized is False
            and change_set.proposed_changes_applied is False
            and change_set.external_writes_performed is False,
            "Proposed changes remain draft-only and non-authoritative.",
            artifact_ref=str(change_set_path),
        )
    )

    plan_path = _resolve_ref(
        change_set.source_shadow_eval_plan_ref,
        repo_root=repo_root,
        base_dir=change_set_path.parent if change_set_path else None,
    )
    shadow_plan = _load_model(
        LearningShadowEvalPlan,
        plan_path,
        "shadow_eval_plan_valid",
        checks,
    )
    readiness_path = _resolve_ref(
        change_set.source_promotion_readiness_report_ref,
        repo_root=repo_root,
        base_dir=change_set_path.parent if change_set_path else None,
    )
    readiness = _load_model(
        LearningPromotionReadinessReport,
        readiness_path,
        "promotion_readiness_report_valid",
        checks,
    )
    if shadow_plan is None or readiness is None:
        return checks
    checks.append(
        _artifact_check(
            "promotion_readiness_still_blocks_promotion",
            shadow_plan.status == "shadow_eval_required"
            and readiness.status == "promotion_blocked_shadow_eval_required"
            and readiness.promotion_authorized is False
            and readiness.proposed_changes_applied is False
            and readiness.external_writes_performed is False,
            "Readiness artifacts still block promotion until owner review and do not apply changes.",
            artifact_ref=str(readiness_path),
        )
    )

    gate_path = _resolve_ref(
        shadow_plan.source_gate_report_ref,
        repo_root=repo_root,
        base_dir=plan_path.parent if plan_path else None,
    )
    gate = _load_model(
        ReviewedLearningGateReport,
        gate_path,
        "reviewed_learning_gate_report_valid",
        checks,
    )
    if gate is None:
        return checks
    checks.append(
        _artifact_check(
            "learning_chain_ids_consistent",
            owner_report.source_shadow_eval_result_report_id
            == shadow_report.shadow_eval_result_report_id
            and shadow_report.proposed_change_set_id == change_set.proposed_change_set_id
            and change_set.shadow_eval_plan_id == shadow_plan.shadow_eval_plan_id
            and readiness.shadow_eval_plan_id == shadow_plan.shadow_eval_plan_id
            and shadow_plan.reviewed_learning_gate_report_id
            == gate.reviewed_learning_gate_report_id,
            "Owner handoff, shadow eval, proposed-change, readiness, plan, and gate IDs line up.",
        )
    )
    checks.append(
        _artifact_check(
            "reviewed_learning_gate_ready_and_blocked",
            gate.status == "candidate_learning_gate_ready"
            and gate.shadow_eval_required is True
            and gate.owning_repo_review_required is True
            and gate.silent_learning_performed is False
            and gate.external_writes_performed is False,
            "Reviewed learning gate is ready for candidate review but still blocked from silent learning.",
            artifact_ref=str(gate_path),
        )
    )
    return checks


def _check_budget_event_lake_bundle(
    *,
    budget_event_lake_bundle_report_path: Path,
    repo_root: Path,
) -> list[IntakeVerticalReadinessArtifactCheck]:
    checks: list[IntakeVerticalReadinessArtifactCheck] = []
    bundle = _load_model(
        BudgetLakeAdmissionBundleReport,
        budget_event_lake_bundle_report_path,
        "budget_event_lake_bundle_report_valid",
        checks,
    )
    if bundle is None:
        return checks
    missing_artifact_refs = [
        artifact.artifact_ref
        for artifact in bundle.artifacts
        if not _ref_is_file(
            artifact.artifact_ref,
            repo_root=repo_root,
            base_dir=budget_event_lake_bundle_report_path.parent,
        )
    ]
    failed_bundle_checks = [check.check_id for check in bundle.checks if check.status == "failed"]
    checks.extend(
        [
            _artifact_check(
                "budget_event_lake_bundle_ready_without_writes",
                bundle.status == "ready_for_exception_lake_review"
                and not failed_bundle_checks
                and bundle.no_lake_admission_performed is True
                and bundle.sqlite_write_performed is False
                and bundle.lake_write_performed is False
                and bundle.external_writes_performed is False
                and bundle.billing_connector_read_performed is False
                and bundle.billing_connector_write_performed is False
                and bundle.carrier_portal_write_performed is False
                and bundle.email_send_performed is False
                and bundle.appeal_submission_performed is False
                and bundle.budget_mutation_performed is False
                and bundle.silent_learning_performed is False,
                "Budget-event Lake bundle is ready for Exception Lake owner review and preserves no-write/no-learning boundaries.",
                artifact_ref=str(budget_event_lake_bundle_report_path),
                missing_refs=failed_bundle_checks,
            ),
            _artifact_check(
                "budget_event_lake_bundle_artifact_refs_exist",
                not missing_artifact_refs and bool(bundle.artifacts),
                "Every artifact ref named by the budget-event Lake bundle exists.",
                artifact_ref=str(budget_event_lake_bundle_report_path),
                missing_refs=missing_artifact_refs,
            ),
            _artifact_check(
                "budget_event_lake_bundle_has_record_families",
                bool(bundle.candidate_record_families)
                and bool(bundle.local_event_labels)
                and bundle.artifact_count == len(bundle.artifacts),
                "Budget-event Lake bundle maps events to candidate record families and local labels.",
                artifact_ref=str(budget_event_lake_bundle_report_path),
            ),
        ]
    )
    return checks


def _check_budget_calibration_readiness(
    *,
    budget_calibration_readiness_report_path: Path,
    repo_root: Path,
) -> list[IntakeVerticalReadinessArtifactCheck]:
    checks: list[IntakeVerticalReadinessArtifactCheck] = []
    report = _load_model(
        BudgetCalibrationReadinessReport,
        budget_calibration_readiness_report_path,
        "budget_calibration_readiness_report_valid",
        checks,
    )
    if report is None:
        return checks
    failed_readiness_checks = [
        check.check_id for check in report.checks if check.status == "failed"
    ]
    missing_source_refs = [
        ref
        for ref in [
            report.source_corpus_report_ref,
            report.source_replay_plan_ref,
            report.source_replay_execution_report_ref,
            report.source_review_packet_ref,
            report.source_review_outcome_report_ref,
            report.source_fixture_binding_candidate_report_ref,
            report.source_fixture_binding_handoff_report_ref,
        ]
        if not _ref_is_file(
            ref,
            repo_root=repo_root,
            base_dir=budget_calibration_readiness_report_path.parent,
        )
    ]
    checks.extend(
        [
            _artifact_check(
                "budget_calibration_readiness_ready_without_writes",
                report.status == "ready_for_manual_fixture_update_review"
                and not failed_readiness_checks
                and report.ready_fixture_binding_handoff_count > 0
                and report.blocked_fixture_binding_handoff_count == 0
                and report.manual_fixture_update_review_required is True
                and report.fixture_update_authorized is False
                and report.fixture_update_pr_created is False
                and report.fixture_files_mutated is False
                and report.fixture_binding_applied is False
                and report.downstream_learning_gate_allowed is False
                and report.calibration_applied is False
                and report.lake_write_performed is False
                and report.sqlite_write_performed is False
                and report.external_writes_performed is False
                and report.silent_learning_performed is False,
                "Budget calibration readiness is ready for manual fixture-update review only and preserves no-write/no-learning boundaries.",
                artifact_ref=str(budget_calibration_readiness_report_path),
                missing_refs=failed_readiness_checks,
            ),
            _artifact_check(
                "budget_calibration_source_refs_exist",
                not missing_source_refs,
                "Every source report ref named by the budget calibration readiness report exists.",
                artifact_ref=str(budget_calibration_readiness_report_path),
                missing_refs=missing_source_refs,
            ),
            _artifact_check(
                "budget_calibration_binding_refs_present",
                bool(report.approved_output_refs) and bool(report.proposed_target_fixture_refs),
                "Budget calibration readiness report names approved output refs and proposed target fixture refs.",
                artifact_ref=str(budget_calibration_readiness_report_path),
            ),
        ]
    )
    return checks


def _check_budget_fixture_update_review(
    *,
    budget_fixture_update_review_report_path: Path,
    budget_calibration_readiness_report_path: Path,
    repo_root: Path,
) -> list[IntakeVerticalReadinessArtifactCheck]:
    checks: list[IntakeVerticalReadinessArtifactCheck] = []
    report = _load_model(
        BudgetFixtureUpdateReviewReport,
        budget_fixture_update_review_report_path,
        "budget_fixture_update_review_report_valid",
        checks,
    )
    if report is None:
        return checks
    failed_review_checks = [check.check_id for check in report.checks if check.status == "failed"]
    history_ref_exists = _ref_is_file(
        report.append_only_history_ref,
        repo_root=repo_root,
        base_dir=budget_fixture_update_review_report_path.parent,
    )
    source_calibration_ref_exists = _ref_is_file(
        report.source_budget_calibration_readiness_report_ref,
        repo_root=repo_root,
        base_dir=budget_fixture_update_review_report_path.parent,
    )
    source_calibration_matches_input = _ref_matches_path(
        report.source_budget_calibration_readiness_report_ref,
        budget_calibration_readiness_report_path,
        repo_root=repo_root,
        base_dir=budget_fixture_update_review_report_path.parent,
    )
    recorded_statuses = {
        "fixture_update_review_recorded_separate_pr_required",
        "fixture_update_review_recorded_no_fixture_pr",
    }
    checks.extend(
        [
            _artifact_check(
                "budget_fixture_update_review_recorded_without_writes",
                report.status in recorded_statuses
                and not failed_review_checks
                and report.source_budget_calibration_readiness_status
                == "ready_for_manual_fixture_update_review"
                and report.source_readiness_report_mutated is False
                and report.fixture_update_pr_created is False
                and report.fixture_files_mutated is False
                and report.fixture_binding_applied is False
                and report.downstream_learning_gate_allowed is False
                and report.calibration_applied is False
                and report.lake_write_performed is False
                and report.sqlite_write_performed is False
                and report.external_writes_performed is False
                and report.silent_learning_performed is False,
                "Budget fixture-update review is recorded locally and preserves no-write/no-learning boundaries.",
                artifact_ref=str(budget_fixture_update_review_report_path),
                missing_refs=failed_review_checks,
            ),
            _artifact_check(
                "budget_fixture_update_review_history_ref_exists",
                history_ref_exists,
                "Fixture-update review append-only local history ref exists.",
                artifact_ref=str(budget_fixture_update_review_report_path),
                missing_refs=[] if history_ref_exists else [report.append_only_history_ref],
            ),
            _artifact_check(
                "budget_fixture_update_review_source_calibration_ref_matches",
                source_calibration_ref_exists and source_calibration_matches_input,
                "Fixture-update review report is bound to the supplied calibration readiness report.",
                artifact_ref=str(budget_fixture_update_review_report_path),
                missing_refs=[]
                if source_calibration_ref_exists and source_calibration_matches_input
                else [report.source_budget_calibration_readiness_report_ref],
            ),
        ]
    )
    return checks


def _check_budget_fixture_update_pr_package(
    *,
    budget_fixture_update_pr_package_report_path: Path,
    budget_fixture_update_review_report_path: Path,
    repo_root: Path,
) -> list[IntakeVerticalReadinessArtifactCheck]:
    checks: list[IntakeVerticalReadinessArtifactCheck] = []
    report = _load_model(
        BudgetFixtureUpdatePRPackageReport,
        budget_fixture_update_pr_package_report_path,
        "budget_fixture_update_pr_package_report_valid",
        checks,
    )
    if report is None:
        return checks
    failed_package_checks = [check.check_id for check in report.checks if check.status == "failed"]
    package_item_ref_ok = report.item_count == 0 or bool(
        report.package_item_output_ref
        and _ref_is_file(
            report.package_item_output_ref,
            repo_root=repo_root,
            base_dir=budget_fixture_update_pr_package_report_path.parent,
        )
    )
    source_review_ref_exists = _ref_is_file(
        report.source_budget_fixture_update_review_report_ref,
        repo_root=repo_root,
        base_dir=budget_fixture_update_pr_package_report_path.parent,
    )
    source_review_matches_input = _ref_matches_path(
        report.source_budget_fixture_update_review_report_ref,
        budget_fixture_update_review_report_path,
        repo_root=repo_root,
        base_dir=budget_fixture_update_pr_package_report_path.parent,
    )
    package_ready_or_not_needed = report.status in {
        "fixture_update_pr_package_ready_for_manual_pr",
        "no_fixture_update_pr_package_needed",
    }
    package_state_consistent = (
        report.status == "no_fixture_update_pr_package_needed"
        and report.manual_fixture_update_pr_required is False
        and report.item_count == 0
    ) or (
        report.status == "fixture_update_pr_package_ready_for_manual_pr"
        and report.manual_fixture_update_pr_required is True
        and report.item_count > 0
        and report.ready_item_count == report.item_count
        and report.blocked_item_count == 0
        and bool(report.accepted_output_refs)
        and bool(report.target_fixture_refs)
    )
    checks.extend(
        [
            _artifact_check(
                "budget_fixture_update_pr_package_ready_without_writes",
                package_ready_or_not_needed
                and package_state_consistent
                and not failed_package_checks
                and report.github_pr_created is False
                and report.fixture_files_mutated is False
                and report.fixture_binding_applied is False
                and report.downstream_learning_gate_allowed is False
                and report.calibration_applied is False
                and report.lake_write_performed is False
                and report.sqlite_write_performed is False
                and report.external_writes_performed is False
                and report.silent_learning_performed is False,
                "Budget fixture-update PR package is ready or not needed and preserves no-PR/no-write/no-learning boundaries.",
                artifact_ref=str(budget_fixture_update_pr_package_report_path),
                missing_refs=failed_package_checks,
            ),
            _artifact_check(
                "budget_fixture_update_pr_package_item_ref_exists",
                package_item_ref_ok,
                "Fixture-update PR package JSONL item ref exists when package items are present.",
                artifact_ref=str(budget_fixture_update_pr_package_report_path),
                missing_refs=[]
                if package_item_ref_ok
                else [report.package_item_output_ref or "missing package_item_output_ref"],
            ),
            _artifact_check(
                "budget_fixture_update_pr_package_source_review_ref_matches",
                source_review_ref_exists and source_review_matches_input,
                "Fixture-update PR package is bound to the supplied fixture-update review report.",
                artifact_ref=str(budget_fixture_update_pr_package_report_path),
                missing_refs=[]
                if source_review_ref_exists and source_review_matches_input
                else [report.source_budget_fixture_update_review_report_ref],
            ),
        ]
    )
    return checks


def build_intake_vertical_readiness_audit(
    *,
    owner_handoff_report_path: str | Path,
    budget_event_lake_bundle_report_path: str | Path,
    budget_calibration_readiness_report_path: str | Path,
    budget_fixture_update_review_report_path: str | Path,
    budget_fixture_update_pr_package_report_path: str | Path,
    repo_root: str | Path = ".",
) -> IntakeVerticalReadinessAuditReport:
    root = Path(repo_root)
    command_surface = _read_command_surface(root)
    slices = [
        _slice_status(definition, repo_root=root, command_surface=command_surface)
        for definition in REQUIRED_SLICES
    ]
    missing_artifacts = sorted(
        {missing for slice_status in slices for missing in slice_status.missing_artifact_refs}
    )
    missing_commands = sorted(
        {missing for slice_status in slices for missing in slice_status.missing_command_refs}
    )
    implemented_count = sum(
        1 for slice_status in slices if slice_status.status == "implemented_local_candidate"
    )
    artifact_checks = _check_learning_artifact_chain(
        owner_handoff_report_path=Path(owner_handoff_report_path),
        repo_root=root,
    )
    learning_artifact_chain_passed = bool(artifact_checks) and all(
        check.status == "passed"
        for check in artifact_checks
        if not check.check_id.startswith("budget_event_lake_bundle")
    )
    lake_bundle_checks = _check_budget_event_lake_bundle(
        budget_event_lake_bundle_report_path=Path(budget_event_lake_bundle_report_path),
        repo_root=root,
    )
    artifact_checks.extend(lake_bundle_checks)
    lake_bundle_passed = bool(lake_bundle_checks) and all(
        check.status == "passed" for check in lake_bundle_checks
    )
    calibration_checks = _check_budget_calibration_readiness(
        budget_calibration_readiness_report_path=Path(budget_calibration_readiness_report_path),
        repo_root=root,
    )
    artifact_checks.extend(calibration_checks)
    calibration_passed = bool(calibration_checks) and all(
        check.status == "passed" for check in calibration_checks
    )
    fixture_update_review_checks = _check_budget_fixture_update_review(
        budget_fixture_update_review_report_path=Path(budget_fixture_update_review_report_path),
        budget_calibration_readiness_report_path=Path(budget_calibration_readiness_report_path),
        repo_root=root,
    )
    artifact_checks.extend(fixture_update_review_checks)
    fixture_update_review_passed = bool(fixture_update_review_checks) and all(
        check.status == "passed" for check in fixture_update_review_checks
    )
    fixture_update_pr_package_checks = _check_budget_fixture_update_pr_package(
        budget_fixture_update_pr_package_report_path=Path(
            budget_fixture_update_pr_package_report_path
        ),
        budget_fixture_update_review_report_path=Path(budget_fixture_update_review_report_path),
        repo_root=root,
    )
    artifact_checks.extend(fixture_update_pr_package_checks)
    fixture_update_pr_package_passed = bool(fixture_update_pr_package_checks) and all(
        check.status == "passed" for check in fixture_update_pr_package_checks
    )
    local_slices_passed = implemented_count == len(REQUIRED_SLICES) and not (
        missing_artifacts or missing_commands
    )
    if not local_slices_passed:
        status = "incomplete_missing_local_artifacts"
        review_readiness = "not_ready_missing_local_artifacts"
    elif not learning_artifact_chain_passed:
        status = "blocked_missing_or_failed_learning_artifacts"
        review_readiness = "not_ready_learning_artifact_chain_blocked"
    elif not lake_bundle_passed:
        status = "blocked_missing_or_failed_lake_bundle"
        review_readiness = "not_ready_lake_bundle_blocked"
    elif not calibration_passed:
        status = "blocked_missing_or_failed_calibration_readiness"
        review_readiness = "not_ready_calibration_readiness_blocked"
    elif not fixture_update_review_passed:
        status = "blocked_missing_or_failed_fixture_update_review"
        review_readiness = "not_ready_fixture_update_review_blocked"
    elif not fixture_update_pr_package_passed:
        status = "blocked_missing_or_failed_fixture_update_pr_package"
        review_readiness = "not_ready_fixture_update_pr_package_blocked"
    else:
        status = "ready_for_pr_review_external_adoption_required"
        review_readiness = "ready_for_human_pr_review_not_auto_marked"

    return IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-audit.v0_1",
        status=status,  # type: ignore[arg-type]
        review_readiness=review_readiness,  # type: ignore[arg-type]
        source_owner_handoff_report_ref=str(owner_handoff_report_path),
        source_budget_event_lake_bundle_report_ref=str(budget_event_lake_bundle_report_path),
        source_budget_calibration_readiness_report_ref=str(
            budget_calibration_readiness_report_path
        ),
        source_budget_fixture_update_review_report_ref=str(
            budget_fixture_update_review_report_path
        ),
        source_budget_fixture_update_pr_package_report_ref=str(
            budget_fixture_update_pr_package_report_path
        ),
        total_slice_count=len(REQUIRED_SLICES),
        implemented_slice_count=implemented_count,
        missing_artifact_refs=missing_artifacts,
        missing_command_refs=missing_commands,
        slices=slices,
        artifact_checks=artifact_checks,
        required_external_adoption_actions=list(REQUIRED_EXTERNAL_ADOPTION_ACTIONS),
        external_adoption_target_repos=[
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ],
        generated_at=now_iso(),
    )


def render_intake_vertical_readiness_audit(
    report: IntakeVerticalReadinessAuditReport,
) -> str:
    lines = [
        "# Intake Vertical Readiness Audit",
        "",
        f"**Audit report ID:** {report.audit_report_id}",
        f"**Status:** {report.status}",
        f"**Review readiness:** {report.review_readiness}",
        f"**Implemented local slices:** {report.implemented_slice_count} / {report.total_slice_count}",
        f"**Owner handoff report:** `{report.source_owner_handoff_report_ref}`",
        f"**Budget-event Lake bundle:** `{report.source_budget_event_lake_bundle_report_ref}`",
        f"**Budget calibration readiness:** `{report.source_budget_calibration_readiness_report_ref}`",
        f"**Budget fixture-update review:** `{report.source_budget_fixture_update_review_report_ref}`",
        f"**Budget fixture-update PR package:** `{report.source_budget_fixture_update_pr_package_report_ref}`",
        "",
        "## Local Slice Status",
        "",
    ]
    for slice_status in report.slices:
        lines.extend(
            [
                f"### {slice_status.slice_id}. {slice_status.title}",
                "",
                f"- Status: {slice_status.status}",
                f"- Requirement: {slice_status.requirement_summary}",
                (
                    "- Missing artifacts: "
                    + (
                        ", ".join(f"`{ref}`" for ref in slice_status.missing_artifact_refs)
                        if slice_status.missing_artifact_refs
                        else "none"
                    )
                ),
                (
                    "- Missing command refs: "
                    + (
                        ", ".join(f"`{ref}`" for ref in slice_status.missing_command_refs)
                        if slice_status.missing_command_refs
                        else "none"
                    )
                ),
                "- Remaining external actions: "
                + "; ".join(slice_status.remaining_external_actions),
                "",
            ]
        )
    lines.extend(["## Generated Artifact Checks", ""])
    for check in report.artifact_checks:
        suffix = ""
        if check.missing_refs:
            suffix = " Missing: " + ", ".join(f"`{ref}`" for ref in check.missing_refs)
        lines.append(
            f"- {check.check_id}: {check.status}; {check.message}"
            + (f" Artifact: `{check.artifact_ref}`" if check.artifact_ref else "")
            + suffix
        )
    lines.extend(
        [
            "",
            "## External Adoption Still Required",
            "",
            *(f"- {action}" for action in report.required_external_adoption_actions),
            "",
            "## Boundary Flags",
            "",
            f"- PR marked ready: {report.pr_marked_ready}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Proposed changes applied: {report.proposed_changes_applied}",
            f"- No connector implemented: {report.no_connector_implemented}",
            f"- No Lake admission performed: {report.no_lake_admission_performed}",
            f"- No sibling repo writes: {report.no_sibling_repo_writes}",
            f"- No canonical mutation: {report.no_canonical_mutation}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This audit is local PR-review evidence only. It does not mark a PR ready, promote canon, write sibling repos, admit Lake records, or authorize production use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_intake_vertical_readiness_audit(
    *,
    owner_handoff_report_path: str | Path,
    budget_event_lake_bundle_report_path: str | Path,
    budget_calibration_readiness_report_path: str | Path,
    budget_fixture_update_review_report_path: str | Path,
    budget_fixture_update_pr_package_report_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
) -> tuple[IntakeVerticalReadinessAuditReport, Path]:
    report = build_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=budget_event_lake_bundle_report_path,
        budget_calibration_readiness_report_path=budget_calibration_readiness_report_path,
        budget_fixture_update_review_report_path=budget_fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=(budget_fixture_update_pr_package_report_path),
        repo_root=repo_root,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / INTAKE_VERTICAL_READINESS_AUDIT_FILENAME
    notes_path = run_dir / INTAKE_VERTICAL_READINESS_AUDIT_NOTES_FILENAME
    write_json(json_path, report.model_dump(mode="json"))
    notes_path.write_text(render_intake_vertical_readiness_audit(report), encoding="utf-8")
    return report, run_dir
