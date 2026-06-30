from __future__ import annotations

from pathlib import Path

from .models import (
    IntakeVerticalReadinessAuditReport,
    PRReviewChecklistItem,
    PRReviewChecklistReport,
)
from .util import digest_text, load_json, now_iso, write_json


PR_REVIEW_CHECKLIST_REPORT_FILENAME = "pr_review_checklist.json"
PR_REVIEW_CHECKLIST_NOTES_FILENAME = "pr_review_checklist.md"

READY_STATUS = "ready_for_pr_review_external_adoption_required"
READY_REVIEW_READINESS = "ready_for_human_pr_review_not_auto_marked"

VALIDATION_COMMANDS = [
    "python scripts/validate_repo.py",
    "python scripts/export_schemas.py",
    "python -m ruff check src tests scripts",
    "python -m ruff format --check src tests scripts",
    "python scripts/run_full_pytest.py",
    "bash scripts/smoke_demo.sh",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _readiness_ready(report: IntakeVerticalReadinessAuditReport) -> bool:
    return report.status == READY_STATUS and report.review_readiness == READY_REVIEW_READINESS


def _failed_check_summaries(report: IntakeVerticalReadinessAuditReport) -> list[str]:
    return [
        f"{check.check_id}: {check.message}"
        for check in report.artifact_checks
        if check.status == "failed"
    ]


def _blocking_summary(report: IntakeVerticalReadinessAuditReport) -> str:
    blockers: list[str] = []
    if report.missing_artifact_refs:
        blockers.append("missing artifacts: " + ", ".join(report.missing_artifact_refs))
    if report.missing_command_refs:
        blockers.append("missing commands: " + ", ".join(report.missing_command_refs))
    blockers.extend(_failed_check_summaries(report))
    if not blockers:
        return "Readiness audit is not ready, but did not expose a detailed blocker."
    return "; ".join(blockers)


def _item(
    *,
    item_id: str,
    section: str,
    title: str,
    recommendation: str,
    why: str,
    red_team_note: str,
    artifact_refs: list[str] | None = None,
    required_human_decision: str | None = None,
    blocked: bool = False,
) -> PRReviewChecklistItem:
    return PRReviewChecklistItem(
        item_id=item_id,
        section=section,  # type: ignore[arg-type]
        title=title,
        recommendation=recommendation,  # type: ignore[arg-type]
        why=why,
        artifact_refs=artifact_refs or [],
        red_team_note=red_team_note,
        required_human_decision=required_human_decision,
        status=("blocked_by_readiness_audit" if blocked else "open_for_human_review"),
    )


def _checklist_items(
    *,
    report: IntakeVerticalReadinessAuditReport,
    readiness_audit_report_ref: str,
) -> list[PRReviewChecklistItem]:
    ready = _readiness_ready(report)
    items: list[PRReviewChecklistItem] = []
    if ready:
        items.append(
            _item(
                item_id="pr-review-readiness-audit-current",
                section="readiness_audit",
                title="Inspect the readiness audit as current branch evidence",
                recommendation="inspect",
                artifact_refs=[readiness_audit_report_ref],
                why=(
                    "The audit says local candidate slices, learning handoffs, and the "
                    "budget-event Lake bundle are ready for human PR review only, "
                    "with fixture-update review recorded but not applied."
                ),
                red_team_note=(
                    "A green readiness audit can still be stale if generated before the "
                    "latest commit; compare timestamps, branch SHA, and changed files."
                ),
                required_human_decision=(
                    "Confirm the readiness audit was generated from the branch under review."
                ),
            )
        )
    else:
        items.append(
            _item(
                item_id="pr-review-readiness-audit-blocker",
                section="readiness_audit",
                title="Do not advance PR review while readiness audit is blocked",
                recommendation="block_until_resolved",
                artifact_refs=[readiness_audit_report_ref],
                why=_blocking_summary(report),
                red_team_note=(
                    "A blocked audit means the human review checklist cannot paper over "
                    "missing evidence, failed Lake bundle checks, or failed learning-chain checks."
                ),
                required_human_decision=(
                    "Keep the PR draft or blocked until the readiness audit is regenerated cleanly."
                ),
                blocked=True,
            )
        )

    items.extend(
        [
            _item(
                item_id="pr-review-budget-event-lake-bundle",
                section="lake_bundle",
                title="Review budget-event Lake bundle evidence",
                recommendation="inspect",
                artifact_refs=[report.source_budget_event_lake_bundle_report_ref],
                why=(
                    "Budget changes, actual-cost variance, and carrier rejection decisions "
                    "must remain candidate evidence for Exception Lake owner review."
                ),
                red_team_note=(
                    "Look for any implied admission, SQLite write, canonical event class, "
                    "or record hash claim that intake is not authorized to make."
                ),
                required_human_decision=(
                    "Confirm the bundle is review evidence only and no Lake admission occurred."
                ),
            ),
            _item(
                item_id="pr-review-learning-owner-handoffs",
                section="learning_chain",
                title="Review learning owner handoffs and shadow-eval posture",
                recommendation="inspect",
                artifact_refs=[report.source_owner_handoff_report_ref],
                why=(
                    "Learning pressure must be routed to owning repos after reviewed "
                    "shadow-eval evidence, not silently applied inside intake."
                ),
                red_team_note=(
                    "Check whether any candidate guidance, profile, fixture, or budget "
                    "behavior was changed without the owner-handoff review path."
                ),
                required_human_decision=(
                    "Confirm learning remains candidate-only and owner-routed."
                ),
            ),
            _item(
                item_id="pr-review-budget-calibration-readiness",
                section="calibration_chain",
                title="Review budget calibration readiness evidence",
                recommendation="inspect",
                artifact_refs=[report.source_budget_calibration_readiness_report_ref],
                why=(
                    "Synthetic corpus replay and fixture-binding outputs must be ready "
                    "for manual fixture-update review before any calibration fixture changes."
                ),
                red_team_note=(
                    "Check that approved replay outputs were not automatically bound into "
                    "fixtures and that no calibration or silent learning was applied."
                ),
                required_human_decision=(
                    "Confirm calibration readiness is only a manual fixture-update review gate."
                ),
            ),
            _item(
                item_id="pr-review-budget-fixture-update-review",
                section="fixture_update_review",
                title="Review manual fixture-update decision evidence",
                recommendation="inspect",
                artifact_refs=[report.source_budget_fixture_update_review_report_ref],
                why=(
                    "Accepted replay outputs must become a separate fixture-update PR only "
                    "after explicit human review evidence; rejected or unclear outputs must stay blocked."
                ),
                red_team_note=(
                    "Confirm the review record did not mutate fixtures, create a PR, "
                    "apply calibration, or unlock silent learning."
                ),
                required_human_decision=(
                    "Confirm any accepted fixture update remains a separate human-reviewed PR."
                ),
            ),
            _item(
                item_id="pr-review-budget-fixture-update-pr-package",
                section="fixture_update_pr_package",
                title="Review fixture-update PR package instructions",
                recommendation="inspect",
                artifact_refs=[report.source_budget_fixture_update_pr_package_report_ref],
                why=(
                    "Accepted fixture-update decisions must be packaged as manual PR instructions "
                    "without editing fixtures or creating a GitHub PR from intake."
                ),
                red_team_note=(
                    "Confirm the package is not itself a patch, does not mark fixtures updated, "
                    "and does not unlock calibration or learning."
                ),
                required_human_decision=(
                    "Decide whether a separate fixture-update PR should be created manually."
                ),
            ),
            _item(
                item_id="pr-review-authority-boundaries",
                section="authority_boundary",
                title="Confirm no authority boundary was crossed",
                recommendation="confirm",
                artifact_refs=[readiness_audit_report_ref],
                why=(
                    "The branch should not promote canon, write sibling repos, implement "
                    "connectors, submit budgets, admit Lake records, or mutate baselines."
                ),
                red_team_note=(
                    "Search for optimistic language that turns local candidate proof into "
                    "production readiness or canonical platform authority."
                ),
                required_human_decision=(
                    "Confirm the boundary flags remain false before changing PR state."
                ),
            ),
            _item(
                item_id="pr-review-external-owner-adoption",
                section="external_owner_review",
                title="Route remaining external adoption to owning repos",
                recommendation="external_owner_review",
                artifact_refs=[readiness_audit_report_ref],
                why=(
                    "Semantic Substrate, Orchestrator, and Exception Lake remain the owners "
                    "for canon, runtime workflow, and append-only evidence storage."
                ),
                red_team_note=(
                    "Do not merge local candidate contracts as if they are already "
                    "platform contracts; create owner-reviewed follow-up work."
                ),
                required_human_decision=(
                    "Decide which external adoption items need separate owner PRs or issues."
                ),
            ),
            _item(
                item_id="pr-review-validation-commands",
                section="validation",
                title="Rerun validation commands immediately before PR state change",
                recommendation="confirm",
                artifact_refs=[],
                why=(
                    "The checklist is useful only if tests, schema export, repo validation, "
                    "format checks, and smoke demo still match the reviewed branch."
                ),
                red_team_note=(
                    "A passing narrow test is not enough for a close-out branch; require "
                    "the full validation set or record exactly what was skipped."
                ),
                required_human_decision=(
                    "Confirm the validation set passed or explicitly accept any skipped check."
                ),
            ),
            _item(
                item_id="pr-review-human-pr-decision",
                section="human_decision",
                title="Make the PR readiness decision manually",
                recommendation="confirm",
                artifact_refs=[readiness_audit_report_ref],
                why=(
                    "This artifact can make the review decision explicit, but it must not "
                    "mark the PR ready or call GitHub write APIs."
                ),
                red_team_note=(
                    "If automation changes PR state, the review gate is no longer a "
                    "human gate and should be treated as a boundary failure."
                ),
                required_human_decision=(
                    "After review, choose ready for review, keep draft, request changes, or split follow-up work."
                ),
            ),
        ]
    )
    return items


def _required_human_decisions(
    report: IntakeVerticalReadinessAuditReport,
) -> list[str]:
    decisions = [
        "Confirm the readiness audit and checklist were generated from the branch under review.",
        "Confirm no real client, matter, privileged, or real negotiated-rate data was introduced.",
        "Confirm no GitHub PR state, Lake, SQLite, sibling repo, connector, submission, or learning write occurred.",
        "Decide which external adoption tasks belong in Semantic Substrate, Orchestrator, and Exception Lake follow-up work.",
    ]
    if _readiness_ready(report):
        decisions.append(
            "After inspecting all artifacts, decide whether a human should mark the PR ready for review."
        )
    else:
        decisions.append("Resolve readiness audit blockers before marking the PR ready.")
    return decisions


def build_pr_review_checklist(
    *,
    readiness_audit_report: IntakeVerticalReadinessAuditReport,
    readiness_audit_report_ref: str,
) -> PRReviewChecklistReport:
    items = _checklist_items(
        report=readiness_audit_report,
        readiness_audit_report_ref=readiness_audit_report_ref,
    )
    ready = _readiness_ready(readiness_audit_report)
    blocking_count = sum(1 for item in items if item.recommendation == "block_until_resolved")
    return PRReviewChecklistReport(
        checklist_report_id=_stable_id(
            "prreviewchecklist",
            f"{readiness_audit_report.audit_report_id}|{readiness_audit_report_ref}",
        ),
        source_readiness_audit_report_ref=readiness_audit_report_ref,
        source_readiness_audit_report_id=readiness_audit_report.audit_report_id,
        source_readiness_status=readiness_audit_report.status,
        source_review_readiness=readiness_audit_report.review_readiness,
        status=("ready_for_human_pr_review" if ready else "blocked_by_readiness_audit"),
        recommendation=(
            "eligible_for_human_to_mark_ready_after_review"
            if ready
            else "keep_draft_until_human_review_complete"
        ),
        item_count=len(items),
        blocking_item_count=blocking_count,
        items=items,
        required_human_decisions=_required_human_decisions(readiness_audit_report),
        validation_commands=list(VALIDATION_COMMANDS),
        external_adoption_target_repos=readiness_audit_report.external_adoption_target_repos,
        generated_at=now_iso(),
    )


def render_pr_review_checklist(report: PRReviewChecklistReport) -> str:
    lines = [
        "# PR Review Checklist",
        "",
        f"**Checklist report ID:** {report.checklist_report_id}",
        f"**Status:** {report.status}",
        f"**Recommendation:** {report.recommendation}",
        f"**Source readiness audit:** `{report.source_readiness_audit_report_ref}`",
        f"**Source readiness status:** {report.source_readiness_status}",
        f"**Source review readiness:** {report.source_review_readiness}",
        "",
        "Do not mark the PR ready automatically. A human reviewer must inspect this checklist, the readiness audit, the learning owner handoffs, and the budget-event Lake bundle before any PR state change.",
        "",
        "## Checklist",
        "",
    ]
    for item in report.items:
        artifact_text = (
            ", ".join(f"`{ref}`" for ref in item.artifact_refs) if item.artifact_refs else "none"
        )
        lines.extend(
            [
                f"- [ ] **{item.title}**",
                f"  - Section: {item.section}",
                f"  - Recommendation: {item.recommendation}",
                f"  - Why: {item.why}",
                f"  - Artifact refs: {artifact_text}",
                f"  - Red-team note: {item.red_team_note}",
            ]
        )
        if item.required_human_decision:
            lines.append(f"  - Required human decision: {item.required_human_decision}")
        lines.append("")

    lines.extend(
        [
            "## Required Human Decisions",
            "",
            *(f"- [ ] {decision}" for decision in report.required_human_decisions),
            "",
            "## Validation Commands",
            "",
            *(f"- `{command}`" for command in report.validation_commands),
            "",
            "## Boundary Flags",
            "",
            f"- PR marked ready: {report.pr_marked_ready}",
            f"- GitHub write performed: {report.github_write_performed}",
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
            "This checklist is local PR-review evidence only. It does not mark a PR ready, call GitHub write APIs, promote canon, write sibling repos, admit Lake records, write SQLite, apply proposed changes, or authorize production use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_pr_review_checklist(
    *,
    readiness_audit_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[PRReviewChecklistReport, Path]:
    readiness_path = Path(readiness_audit_report_path)
    readiness_report = IntakeVerticalReadinessAuditReport.model_validate(load_json(readiness_path))
    report = build_pr_review_checklist(
        readiness_audit_report=readiness_report,
        readiness_audit_report_ref=str(readiness_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / PR_REVIEW_CHECKLIST_REPORT_FILENAME
    notes_path = run_dir / PR_REVIEW_CHECKLIST_NOTES_FILENAME
    write_json(json_path, report.model_dump(mode="json"))
    notes_path.write_text(render_pr_review_checklist(report), encoding="utf-8")
    return report, run_dir
