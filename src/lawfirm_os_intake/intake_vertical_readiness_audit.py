from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import ValidationError

from .models import (
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
            "src/lawfirm_os_intake/learning_shadow_eval_results.py",
            "schemas/learning-shadow-eval-fixture-result.schema.json",
            "schemas/learning-shadow-eval-result-report.schema.json",
            "tests/test_learning_shadow_eval_results.py",
            "docs/decisions/TRACE-2026-06-26-learning-shadow-eval-results.md",
        ),
        command_refs=("run-learning-shadow-eval",),
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
        title="Final intake vertical readiness audit",
        requirement_summary=(
            "A deterministic final audit checks local surfaces plus the generated learning "
            "artifact chain before humans consider marking the PR ready."
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


def build_intake_vertical_readiness_audit(
    *,
    owner_handoff_report_path: str | Path,
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
    artifact_chain_passed = bool(artifact_checks) and all(
        check.status == "passed" for check in artifact_checks
    )
    local_slices_passed = implemented_count == len(REQUIRED_SLICES) and not (
        missing_artifacts or missing_commands
    )
    if not local_slices_passed:
        status = "incomplete_missing_local_artifacts"
        review_readiness = "not_ready_missing_local_artifacts"
    elif not artifact_chain_passed:
        status = "blocked_missing_or_failed_learning_artifacts"
        review_readiness = "not_ready_learning_artifact_chain_blocked"
    else:
        status = "ready_for_pr_review_external_adoption_required"
        review_readiness = "ready_for_human_pr_review_not_auto_marked"

    return IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-audit.v0_1",
        status=status,  # type: ignore[arg-type]
        review_readiness=review_readiness,  # type: ignore[arg-type]
        source_owner_handoff_report_ref=str(owner_handoff_report_path),
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
    lines.extend(["## Generated Learning Artifact Chain", ""])
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
    out_dir: str | Path,
    repo_root: str | Path = ".",
) -> tuple[IntakeVerticalReadinessAuditReport, Path]:
    report = build_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        repo_root=repo_root,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / INTAKE_VERTICAL_READINESS_AUDIT_FILENAME
    notes_path = run_dir / INTAKE_VERTICAL_READINESS_AUDIT_NOTES_FILENAME
    write_json(json_path, report.model_dump(mode="json"))
    notes_path.write_text(render_intake_vertical_readiness_audit(report), encoding="utf-8")
    return report, run_dir
