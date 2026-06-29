from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import (
    CarrierRejectionRoadmapAuditCheck,
    CarrierRejectionRoadmapAuditReport,
    CarrierRejectionRoadmapSliceStatus,
)
from .util import now_iso, write_json


ROADMAP_AUDIT_FILENAME = "carrier_rejection_roadmap_audit_report.json"
ROADMAP_AUDIT_NOTES_FILENAME = "carrier_rejection_roadmap_audit_report.md"


@dataclass(frozen=True)
class SliceDefinition:
    slice_id: int
    title: str
    requirement_summary: str
    proof_artifact_refs: tuple[str, ...]
    command_refs: tuple[str, ...]
    runtime_owner_repo: str
    remaining_external_actions: tuple[str, ...]


REQUIRED_SLICES: tuple[SliceDefinition, ...] = (
    SliceDefinition(
        slice_id=1,
        title="Candidate rejection and appeal schemas",
        requirement_summary=(
            "Local candidate contracts exist for carrier rejection notices, "
            "remediation cases, appeal results, and source bundles."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/models.py",
            "src/lawfirm_os_intake/carrier_rejections.py",
            "schemas/carrier-rejection-notice.schema.json",
            "schemas/carrier-rejection-remediation-case.schema.json",
            "schemas/carrier-appeal-result.schema.json",
            "schemas/carrier-rejection-capture-source-bundle.schema.json",
            "tests/test_carrier_rejection_capture.py",
        ),
        command_refs=("capture-carrier-rejections",),
        runtime_owner_repo="LawFirm-os-intake",
        remaining_external_actions=(
            "Review candidate schemas before any Semantic Substrate promotion.",
        ),
    ),
    SliceDefinition(
        slice_id=2,
        title="Dry-run Exception Lake mapping package",
        requirement_summary=(
            "Carrier rejection labels map to broad dry-run Lake classes without "
            "admission, SQLite writes, or canonical event-class assignment."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/exception_mapping.py",
            "schemas/exception-lake-mapping-package.schema.json",
            "tests/test_exception_lake_mapping_package.py",
            "DATA_FLOW_MAP.md",
        ),
        command_refs=(),
        runtime_owner_repo="LawFirm-os-exceptions-lake-runtime",
        remaining_external_actions=(
            "Exception Lake must review and implement any runtime admission mapping.",
            "Semantic Substrate must promote any canonical event classes first.",
        ),
    ),
    SliceDefinition(
        slice_id=3,
        title="Deterministic response reconciliation",
        requirement_summary=(
            "Expected carrier responses reconcile against captured notices, "
            "duplicates, unlinked notices, parser failures, and missing SLA responses."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejections.py",
            "schemas/carrier-response-reconciliation-report.schema.json",
            "tests/test_carrier_rejection_capture.py",
            "docs/carrier-rejection-learning-loop-roadmap.md",
        ),
        command_refs=("capture-carrier-rejections",),
        runtime_owner_repo="LawFirm-os-orchestrator",
        remaining_external_actions=(
            "Orchestrator must own production response-state ledgers and connectors.",
        ),
    ),
    SliceDefinition(
        slice_id=4,
        title="Synthetic rejection source fixtures",
        requirement_summary=(
            "Synthetic portal/email/workbook-style fixture covers duplicate, unlinked, "
            "missing, malformed, partial allowance, and appeal-result cases."
        ),
        proof_artifact_refs=(
            "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
            "tests/test_carrier_rejection_capture.py",
        ),
        command_refs=("capture-carrier-rejections",),
        runtime_owner_repo="LawFirm-os-intake",
        remaining_external_actions=(
            "Add more carrier and matter counterfactual fixtures as future eval depth.",
        ),
    ),
    SliceDefinition(
        slice_id=5,
        title="Human rejection review packet",
        requirement_summary=(
            "Reconciliation reports turn into review packets, recommendations, "
            "red-team notes, and append-only decision templates."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejection_review.py",
            "schemas/carrier-rejection-review-packet.schema.json",
            "schemas/carrier-rejection-review-decision-template.schema.json",
            "tests/test_carrier_rejection_review.py",
            "docs/decisions/TRACE-2026-06-26-carrier-rejection-review-packet.md",
        ),
        command_refs=("review-carrier-rejections",),
        runtime_owner_repo="LawFirm-os-intake",
        remaining_external_actions=(
            "Orchestrator must own production human pause state and reviewer identity binding.",
        ),
    ),
    SliceDefinition(
        slice_id=6,
        title="Reviewed learning-candidate report",
        requirement_summary=(
            "Review packets create blocked learning proposals for guideline, budget, "
            "template, narrative, preapproval, parser, reconciliation, SLA, validation, "
            "and appeal-outcome loops without silent mutation."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejection_learning.py",
            "schemas/carrier-rejection-learning-report.schema.json",
            "schemas/carrier-rejection-learning-proposal.schema.json",
            "tests/test_carrier_rejection_learning.py",
            "docs/decisions/TRACE-2026-06-26-carrier-rejection-learning-report.md",
        ),
        command_refs=("propose-carrier-rejection-learning",),
        runtime_owner_repo="LawFirm-os-intake",
        remaining_external_actions=(
            "Owning repos must review learning candidates before changing profiles, templates, or rules.",
        ),
    ),
    SliceDefinition(
        slice_id=7,
        title="Orchestrator interface draft",
        requirement_summary=(
            "Candidate interface names future Orchestrator connector channels, "
            "response-state ledger duties, human pauses, appeal-submission gates, "
            "and guarded Lake handoff."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejection_orchestrator_interface.py",
            "schemas/carrier-rejection-orchestrator-interface-draft.schema.json",
            "tests/test_carrier_rejection_orchestrator_interface.py",
            "promotion/cross_repo_promotion_package.json",
            "docs/decisions/TRACE-2026-06-26-carrier-rejection-orchestrator-interface.md",
        ),
        command_refs=("draft-carrier-rejection-orchestrator-interface",),
        runtime_owner_repo="LawFirm-os-orchestrator",
        remaining_external_actions=(
            "Orchestrator must implement any production connector capture or appeal submission.",
            "Human authorization is required before any external appeal submission.",
        ),
    ),
    SliceDefinition(
        slice_id=8,
        title="Exception Lake admission proposal",
        requirement_summary=(
            "Candidate Lake admission proposal defines append-only record families, "
            "idempotency, hashes, Orchestrator packet prerequisites, and supersession."
        ),
        proof_artifact_refs=(
            "src/lawfirm_os_intake/carrier_rejection_lake_admission.py",
            "schemas/carrier-rejection-lake-admission-proposal.schema.json",
            "tests/test_carrier_rejection_lake_admission.py",
            "promotion/cross_repo_promotion_package.json",
            "docs/decisions/TRACE-2026-06-26-carrier-rejection-lake-admission-proposal.md",
        ),
        command_refs=("draft-carrier-rejection-lake-admission",),
        runtime_owner_repo="LawFirm-os-exceptions-lake-runtime",
        remaining_external_actions=(
            "Exception Lake must own runtime admission schemas, SQLite tables, and record hashes.",
        ),
    ),
)

COMMAND_SEARCH_REFS = (
    "src/lawfirm_os_intake/cli.py",
    "ENDPOINTS_AND_COMMANDS.md",
    "docs/carrier-rejection-learning-loop-roadmap.md",
)

REQUIRED_EXTERNAL_ADOPTION_ACTIONS = (
    "Review and merge the intake PR after local candidate validation is green.",
    "Promote any canonical carrier rejection event classes or route IDs in Semantic Substrate.",
    "Implement production connector capture, response-state ledger, human pauses, and appeal submission gates in Orchestrator.",
    "Implement append-only admission, SQLite migrations if approved, validation, hashes, and supersession in Exception Lake.",
    "Approve real-data, real-guideline, and real-rate governance before using production carrier material.",
)


def _read_command_surface(repo_root: Path) -> str:
    chunks: list[str] = []
    for ref in COMMAND_SEARCH_REFS:
        path = repo_root / ref
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _slice_status(
    definition: SliceDefinition,
    *,
    repo_root: Path,
    command_surface: str,
) -> CarrierRejectionRoadmapSliceStatus:
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
    return CarrierRejectionRoadmapSliceStatus(
        slice_id=definition.slice_id,
        title=definition.title,
        status=status,
        requirement_summary=definition.requirement_summary,
        proof_artifact_refs=list(definition.proof_artifact_refs),
        missing_artifact_refs=missing_artifacts,
        command_refs=list(definition.command_refs),
        missing_command_refs=missing_commands,
        runtime_owner_repo=definition.runtime_owner_repo,  # type: ignore[arg-type]
        remaining_external_actions=list(definition.remaining_external_actions),
    )


def _check(
    check_id: str,
    passed: bool,
    message: str,
    missing_refs: list[str] | None = None,
) -> CarrierRejectionRoadmapAuditCheck:
    return CarrierRejectionRoadmapAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        missing_refs=missing_refs or [],
    )


def build_carrier_rejection_roadmap_audit(
    repo_root: str | Path = ".",
) -> CarrierRejectionRoadmapAuditReport:
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
    complete = implemented_count == len(REQUIRED_SLICES) and not missing_artifacts
    status = (
        "local_candidate_complete_external_adoption_required"
        if complete and not missing_commands
        else "incomplete_missing_local_artifacts"
    )
    checks = [
        _check(
            "all_required_slice_artifacts_present",
            not missing_artifacts,
            "Every carrier-rejection roadmap slice has its required local proof artifacts.",
            missing_artifacts,
        ),
        _check(
            "required_cli_commands_present",
            not missing_commands,
            "Required CLI command names are present in the local command/docs surface.",
            missing_commands,
        ),
        _check(
            "external_adoption_still_required",
            True,
            "The audit keeps Orchestrator, Exception Lake, and Semantic Substrate adoption as remaining work rather than claiming production completion inside intake.",
        ),
        _check(
            "intake_boundary_preserved",
            True,
            "The audit performs no connector implementation, Lake admission, SQLite write, sibling repo write, external write, or canonical mutation.",
        ),
    ]
    return CarrierRejectionRoadmapAuditReport(
        audit_report_id="carrier-rejection-roadmap-audit.v0_1",
        status=status,
        total_slice_count=len(REQUIRED_SLICES),
        implemented_slice_count=implemented_count,
        missing_artifact_refs=missing_artifacts,
        missing_command_refs=missing_commands,
        slices=slices,
        checks=checks,
        required_external_adoption_actions=list(REQUIRED_EXTERNAL_ADOPTION_ACTIONS),
        external_adoption_target_repos=[
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
            "LawFirm-os-semantic-substrate",
        ],
        review_readiness=(
            "ready_for_intake_pr_review"
            if status == "local_candidate_complete_external_adoption_required"
            else "not_ready_missing_local_artifacts"
        ),
        generated_at=now_iso(),
    )


def render_carrier_rejection_roadmap_audit(
    report: CarrierRejectionRoadmapAuditReport,
) -> str:
    lines = [
        "# Carrier Rejection Roadmap Audit",
        "",
        f"**Audit report ID:** {report.audit_report_id}",
        f"**Status:** {report.status}",
        f"**Review readiness:** {report.review_readiness}",
        (
            f"**Implemented local slices:** {report.implemented_slice_count} / "
            f"{report.total_slice_count}"
        ),
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
                f"- Runtime owner for production: {slice_status.runtime_owner_repo}",
                f"- Requirement: {slice_status.requirement_summary}",
                f"- Proof artifacts: {', '.join(f'`{ref}`' for ref in slice_status.proof_artifact_refs)}",
                (
                    "- Missing artifacts: "
                    + (
                        ", ".join(f"`{ref}`" for ref in slice_status.missing_artifact_refs)
                        if slice_status.missing_artifact_refs
                        else "none"
                    )
                ),
                (
                    "- Command refs: "
                    + (
                        ", ".join(f"`{ref}`" for ref in slice_status.command_refs)
                        if slice_status.command_refs
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
    lines.extend(["## Checks", ""])
    for check in report.checks:
        suffix = ""
        if check.missing_refs:
            suffix = " Missing: " + ", ".join(f"`{ref}`" for ref in check.missing_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## External Adoption Still Required",
            "",
            *(f"- {action}" for action in report.required_external_adoption_actions),
            "",
            "## Boundary Flags",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- No connector implemented: {report.no_connector_implemented}",
            f"- No Lake admission performed: {report.no_lake_admission_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- No sibling repo writes: {report.no_sibling_repo_writes}",
            f"- No canonical mutation: {report.no_canonical_mutation}",
            "",
            "This audit proves local intake candidate coverage only. Production capture, admission, canonical promotion, real-data governance, and external submissions remain owned by sibling repos and human review.",
            "",
        ]
    )
    return "\n".join(lines)


def run_carrier_rejection_roadmap_audit(
    out_dir: str | Path,
    *,
    repo_root: str | Path = ".",
) -> tuple[CarrierRejectionRoadmapAuditReport, Path]:
    report = build_carrier_rejection_roadmap_audit(repo_root)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / ROADMAP_AUDIT_FILENAME
    notes_path = run_dir / ROADMAP_AUDIT_NOTES_FILENAME
    write_json(json_path, report.model_dump(mode="json"))
    notes_path.write_text(render_carrier_rejection_roadmap_audit(report), encoding="utf-8")
    return report, run_dir
