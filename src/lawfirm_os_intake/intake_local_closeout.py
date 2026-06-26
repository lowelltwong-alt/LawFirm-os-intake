from __future__ import annotations

from pathlib import Path

from .models import (
    CrossRepoOwnerAdoptionReport,
    CrossRepoOwnerIssueDraftReport,
    IntakeLocalCloseoutCheck,
    IntakeLocalCloseoutReport,
    IntakeVerticalReadinessAuditReport,
    PRReviewChecklistReport,
)
from .util import digest_text, load_json, now_iso, write_json


INTAKE_LOCAL_CLOSEOUT_REPORT_FILENAME = "intake_local_closeout_report.json"
INTAKE_LOCAL_CLOSEOUT_NOTES_FILENAME = "intake_local_closeout_report.md"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    artifact_refs: list[str],
) -> IntakeLocalCloseoutCheck:
    return IntakeLocalCloseoutCheck(
        check_id=check_id,
        status=("passed" if passed else "blocked"),
        message=message,
        artifact_refs=artifact_refs,
    )


def _no_write_flags_false(*values: bool) -> bool:
    return not any(values)


def _closeout_checks(
    *,
    readiness_report: IntakeVerticalReadinessAuditReport,
    readiness_report_ref: str,
    pr_review_checklist: PRReviewChecklistReport,
    pr_review_checklist_ref: str,
    owner_adoption_report: CrossRepoOwnerAdoptionReport,
    owner_adoption_report_ref: str,
    owner_issue_draft_report: CrossRepoOwnerIssueDraftReport,
    owner_issue_draft_report_ref: str,
) -> list[IntakeLocalCloseoutCheck]:
    return [
        _check(
            "readiness_audit_ready",
            readiness_report.status == "ready_for_pr_review_external_adoption_required"
            and readiness_report.review_readiness == "ready_for_human_pr_review_not_auto_marked"
            and not any(check.status == "failed" for check in readiness_report.artifact_checks),
            "Readiness audit must be ready for human PR review with no failed artifact checks.",
            [readiness_report_ref],
        ),
        _check(
            "pr_review_checklist_ready",
            pr_review_checklist.status == "ready_for_human_pr_review"
            and pr_review_checklist.blocking_item_count == 0,
            "PR checklist must be ready for human review with no blocking items.",
            [pr_review_checklist_ref],
        ),
        _check(
            "owner_adoption_packets_ready",
            owner_adoption_report.status == "owner_adoption_packets_ready"
            and owner_adoption_report.blocked_packet_count == 0,
            "Owner-adoption packets must be ready for owner review with no blocked packets.",
            [owner_adoption_report_ref],
        ),
        _check(
            "owner_issue_drafts_ready",
            owner_issue_draft_report.status == "issue_drafts_ready_for_manual_creation"
            and owner_issue_draft_report.blocked_draft_count == 0,
            "Owner issue drafts must be ready for manual creation with no blocked drafts.",
            [owner_issue_draft_report_ref],
        ),
        _check(
            "github_and_sibling_writes_absent",
            _no_write_flags_false(
                pr_review_checklist.github_write_performed,
                owner_adoption_report.github_write_performed,
                owner_adoption_report.sibling_repo_write_performed,
                owner_issue_draft_report.github_write_performed,
                owner_issue_draft_report.sibling_repo_write_performed,
            ),
            "No GitHub state change, issue creation, PR creation, or sibling-repo write may have occurred.",
            [
                pr_review_checklist_ref,
                owner_adoption_report_ref,
                owner_issue_draft_report_ref,
            ],
        ),
        _check(
            "promotion_lake_sqlite_learning_absent",
            _no_write_flags_false(
                readiness_report.promotion_authorized,
                readiness_report.proposed_changes_applied,
                readiness_report.lake_write_performed,
                readiness_report.sqlite_write_performed,
                readiness_report.silent_learning_performed,
                owner_adoption_report.promotion_authorized,
                owner_adoption_report.lake_write_performed,
                owner_adoption_report.sqlite_write_performed,
                owner_adoption_report.silent_learning_performed,
                owner_issue_draft_report.promotion_authorized,
                owner_issue_draft_report.lake_write_performed,
                owner_issue_draft_report.sqlite_write_performed,
                owner_issue_draft_report.silent_learning_performed,
            ),
            "No promotion, proposed-change application, Lake write, SQLite write, or silent learning may have occurred.",
            [
                readiness_report_ref,
                owner_adoption_report_ref,
                owner_issue_draft_report_ref,
            ],
        ),
        _check(
            "manual_actions_remain_explicit",
            pr_review_checklist.required_human_decisions
            and owner_adoption_report.required_next_gates
            and owner_issue_draft_report.required_next_gates,
            "Manual PR decision, owner issue creation, owner triage, and owner implementation gates must remain explicit.",
            [
                pr_review_checklist_ref,
                owner_adoption_report_ref,
                owner_issue_draft_report_ref,
            ],
        ),
    ]


def _manual_actions(observed_pr_state: str) -> list[str]:
    actions = [
        "Human reviews the PR checklist and decides whether to mark PR #7 ready for review.",
        "Human manually creates any desired owner follow-up issues from the generated issue drafts.",
        "Owning repos triage candidate proposals and decide whether implementation PRs are warranted.",
        "Run cross-repo contract validation after any owning-repo implementation lands.",
    ]
    if observed_pr_state == "draft":
        actions.insert(0, "PR remains draft; no automated PR state change occurred.")
    elif observed_pr_state == "ready_for_review":
        actions.insert(
            0, "PR is already ready for review; verify that change was human-authorized."
        )
    else:
        actions.insert(0, "PR state was not supplied; verify state manually before acting.")
    return actions


def build_intake_local_closeout_report(
    *,
    readiness_report: IntakeVerticalReadinessAuditReport,
    readiness_report_ref: str,
    pr_review_checklist: PRReviewChecklistReport,
    pr_review_checklist_ref: str,
    owner_adoption_report: CrossRepoOwnerAdoptionReport,
    owner_adoption_report_ref: str,
    owner_issue_draft_report: CrossRepoOwnerIssueDraftReport,
    owner_issue_draft_report_ref: str,
    observed_pr_number: int | None = None,
    observed_pr_url: str | None = None,
    observed_pr_state: str = "not_supplied",
) -> IntakeLocalCloseoutReport:
    checks = _closeout_checks(
        readiness_report=readiness_report,
        readiness_report_ref=readiness_report_ref,
        pr_review_checklist=pr_review_checklist,
        pr_review_checklist_ref=pr_review_checklist_ref,
        owner_adoption_report=owner_adoption_report,
        owner_adoption_report_ref=owner_adoption_report_ref,
        owner_issue_draft_report=owner_issue_draft_report,
        owner_issue_draft_report_ref=owner_issue_draft_report_ref,
    )
    blocking_count = sum(1 for check in checks if check.status == "blocked")
    return IntakeLocalCloseoutReport(
        closeout_report_id=_stable_id(
            "intakelocalcloseout",
            "|".join(
                [
                    readiness_report.audit_report_id,
                    pr_review_checklist.checklist_report_id,
                    owner_adoption_report.owner_adoption_report_id,
                    owner_issue_draft_report.issue_draft_report_id,
                ]
            ),
        ),
        status=(
            "intake_local_closeout_ready_manual_actions_required"
            if blocking_count == 0
            else "blocked_by_closeout_evidence"
        ),
        observed_pr_number=observed_pr_number,
        observed_pr_url=observed_pr_url,
        observed_pr_state=observed_pr_state,  # type: ignore[arg-type]
        source_readiness_audit_report_id=readiness_report.audit_report_id,
        source_readiness_audit_report_ref=readiness_report_ref,
        source_readiness_status=readiness_report.status,
        source_review_readiness=readiness_report.review_readiness,
        source_pr_review_checklist_id=pr_review_checklist.checklist_report_id,
        source_pr_review_checklist_ref=pr_review_checklist_ref,
        source_pr_review_checklist_status=pr_review_checklist.status,
        source_pr_review_checklist_recommendation=pr_review_checklist.recommendation,
        source_owner_adoption_report_id=owner_adoption_report.owner_adoption_report_id,
        source_owner_adoption_report_ref=owner_adoption_report_ref,
        source_owner_adoption_status=owner_adoption_report.status,
        source_owner_issue_draft_report_id=owner_issue_draft_report.issue_draft_report_id,
        source_owner_issue_draft_report_ref=owner_issue_draft_report_ref,
        source_owner_issue_draft_status=owner_issue_draft_report.status,
        check_count=len(checks),
        passed_check_count=len(checks) - blocking_count,
        blocking_check_count=blocking_count,
        checks=checks,
        manual_actions_remaining=_manual_actions(observed_pr_state),
        generated_artifact_refs=[
            readiness_report_ref,
            pr_review_checklist_ref,
            owner_adoption_report_ref,
            owner_issue_draft_report_ref,
        ],
        generated_at=now_iso(),
    )


def render_intake_local_closeout(report: IntakeLocalCloseoutReport) -> str:
    lines = [
        "# Intake Local Closeout Report",
        "",
        f"**Report ID:** {report.closeout_report_id}",
        f"**Status:** {report.status}",
        f"**Observed PR:** {report.observed_pr_number or 'not supplied'}",
        f"**Observed PR state:** {report.observed_pr_state}",
        f"**Observed PR URL:** {report.observed_pr_url or 'not supplied'}",
        "",
        "## Source Evidence",
        "",
        f"- Readiness audit: `{report.source_readiness_audit_report_ref}` ({report.source_readiness_status})",
        f"- PR checklist: `{report.source_pr_review_checklist_ref}` ({report.source_pr_review_checklist_status})",
        f"- Owner adoption: `{report.source_owner_adoption_report_ref}` ({report.source_owner_adoption_status})",
        f"- Owner issue drafts: `{report.source_owner_issue_draft_report_ref}` ({report.source_owner_issue_draft_status})",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        refs = ", ".join(f"`{ref}`" for ref in check.artifact_refs) or "none"
        lines.extend(
            [
                f"- {check.check_id}: {check.status}",
                f"  - {check.message}",
                f"  - Artifact refs: {refs}",
            ]
        )
    lines.extend(
        [
            "",
            "## Manual Actions Remaining",
            "",
            *(f"- [ ] {action}" for action in report.manual_actions_remaining),
            "",
            "## Boundary Flags",
            "",
            f"- Manual PR state change required: {report.manual_pr_state_change_required}",
            f"- Manual owner issue creation required: {report.manual_owner_issue_creation_required}",
            f"- PR state change performed: {report.pr_state_change_performed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Proposed changes applied: {report.proposed_changes_applied}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This closeout report is local evidence only. It does not mark a PR ready, create issues, open PRs, write sibling repos, promote canon, admit Lake records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_intake_local_closeout(
    *,
    readiness_audit_report_path: str | Path,
    pr_review_checklist_path: str | Path,
    owner_adoption_report_path: str | Path,
    owner_issue_draft_report_path: str | Path,
    out_dir: str | Path,
    observed_pr_number: int | None = None,
    observed_pr_url: str | None = None,
    observed_pr_state: str = "not_supplied",
) -> tuple[IntakeLocalCloseoutReport, Path]:
    readiness_path = Path(readiness_audit_report_path)
    checklist_path = Path(pr_review_checklist_path)
    adoption_path = Path(owner_adoption_report_path)
    issue_draft_path = Path(owner_issue_draft_report_path)
    report = build_intake_local_closeout_report(
        readiness_report=IntakeVerticalReadinessAuditReport.model_validate(
            load_json(readiness_path)
        ),
        readiness_report_ref=str(readiness_path),
        pr_review_checklist=PRReviewChecklistReport.model_validate(load_json(checklist_path)),
        pr_review_checklist_ref=str(checklist_path),
        owner_adoption_report=CrossRepoOwnerAdoptionReport.model_validate(load_json(adoption_path)),
        owner_adoption_report_ref=str(adoption_path),
        owner_issue_draft_report=CrossRepoOwnerIssueDraftReport.model_validate(
            load_json(issue_draft_path)
        ),
        owner_issue_draft_report_ref=str(issue_draft_path),
        observed_pr_number=observed_pr_number,
        observed_pr_url=observed_pr_url,
        observed_pr_state=observed_pr_state,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / INTAKE_LOCAL_CLOSEOUT_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / INTAKE_LOCAL_CLOSEOUT_NOTES_FILENAME).write_text(
        render_intake_local_closeout(report),
        encoding="utf-8",
    )
    return report, run_dir
