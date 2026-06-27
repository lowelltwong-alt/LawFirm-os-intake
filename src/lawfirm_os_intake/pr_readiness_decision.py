from __future__ import annotations

from pathlib import Path

from .models import (
    IntakeLocalCloseoutReport,
    PRReadinessDecisionCheck,
    PRReadinessDecisionRecord,
    PRReadinessDecisionReport,
    PRReviewChecklistReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


PR_READINESS_DECISION_RECORD_FILENAME = "pr_readiness_decision_record.json"
PR_READINESS_DECISION_HISTORY_FILENAME = "pr_readiness_decision_history.jsonl"
PR_READINESS_DECISION_REPORT_FILENAME = "pr_readiness_decision_report.json"
PR_READINESS_DECISION_NOTES_FILENAME = "pr_readiness_decision_report.md"

READY_CHECKLIST_STATUS = "ready_for_human_pr_review"
READY_CLOSEOUT_STATUS = "intake_local_closeout_ready_manual_actions_required"

PR_READINESS_DECISION_REQUIRED_NEXT_GATES = [
    "manual_github_pr_state_change_if_accepted",
    "owner_issue_creation_remains_manual",
    "cross_repo_validation_after_owner_changes",
    "no_automated_github_write",
    "no_sibling_repo_or_lake_write",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> PRReadinessDecisionCheck:
    return PRReadinessDecisionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _checklist_boundary_clear(report: PRReviewChecklistReport) -> bool:
    return (
        report.pr_marked_ready is False
        and report.github_write_performed is False
        and report.promotion_authorized is False
        and report.proposed_changes_applied is False
        and report.no_connector_implemented is True
        and report.no_lake_admission_performed is True
        and report.no_sibling_repo_writes is True
        and report.no_canonical_mutation is True
        and report.sqlite_write_performed is False
        and report.lake_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _closeout_boundary_clear(report: IntakeLocalCloseoutReport) -> bool:
    return (
        report.pr_state_change_performed is False
        and report.github_issue_created is False
        and report.github_pr_created is False
        and report.github_write_performed is False
        and report.sibling_repo_write_performed is False
        and report.promotion_authorized is False
        and report.proposed_changes_applied is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _record_boundary_clear(record: PRReadinessDecisionRecord) -> bool:
    return (
        record.pr_marked_ready is False
        and record.github_write_performed is False
        and record.github_issue_created is False
        and record.github_pr_created is False
        and record.sibling_repo_write_performed is False
        and record.promotion_authorized is False
        and record.proposed_changes_applied is False
        and record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.silent_learning_performed is False
    )


def _bind_record(
    *,
    record: PRReadinessDecisionRecord,
    checklist: PRReviewChecklistReport,
    closeout: IntakeLocalCloseoutReport,
) -> PRReadinessDecisionRecord:
    if record.checklist_report_id != checklist.checklist_report_id:
        raise ValueError(
            "PR readiness decision checklist_report_id does not match: "
            f"{record.checklist_report_id} != {checklist.checklist_report_id}"
        )
    if record.closeout_report_id != closeout.closeout_report_id:
        raise ValueError(
            "PR readiness decision closeout_report_id does not match: "
            f"{record.closeout_report_id} != {closeout.closeout_report_id}"
        )
    known_item_ids = {item.item_id for item in checklist.items}
    unknown_items = sorted(set(record.accepted_checklist_item_ids) - known_item_ids)
    if unknown_items:
        raise ValueError(
            "PR readiness decision accepted checklist item IDs are not in checklist: "
            + ", ".join(unknown_items)
        )
    return record


def build_pr_readiness_decision_report(
    *,
    checklist: PRReviewChecklistReport,
    checklist_ref: str,
    closeout: IntakeLocalCloseoutReport,
    closeout_ref: str,
    decision_record: PRReadinessDecisionRecord,
    history_ref: str,
) -> PRReadinessDecisionReport:
    ready_decision = decision_record.decision == "mark_ready_for_review"
    checklist_item_ids = {item.item_id for item in checklist.items}
    accepted_items_complete = checklist_item_ids.issubset(
        set(decision_record.accepted_checklist_item_ids)
    )
    checks = [
        _check(
            "pr_review_checklist_ready_without_writes",
            checklist.status == READY_CHECKLIST_STATUS
            and checklist.blocking_item_count == 0
            and _checklist_boundary_clear(checklist),
            "PR review checklist is ready and preserves no-write boundaries.",
            artifact_refs=[checklist_ref],
        ),
        _check(
            "local_closeout_ready_without_writes",
            closeout.status == READY_CLOSEOUT_STATUS
            and closeout.blocking_check_count == 0
            and _closeout_boundary_clear(closeout),
            "Local closeout is ready and preserves manual-action/no-write boundaries.",
            artifact_refs=[closeout_ref],
        ),
        _check(
            "decision_record_matches_sources",
            decision_record.checklist_report_id == checklist.checklist_report_id
            and decision_record.closeout_report_id == closeout.closeout_report_id,
            "PR readiness decision record is bound to the supplied checklist and closeout reports.",
            artifact_refs=[checklist_ref, closeout_ref],
        ),
        _check(
            "ready_decision_accepts_all_checklist_items",
            (not ready_decision) or accepted_items_complete,
            "Mark-ready decisions accept every checklist item.",
            artifact_refs=decision_record.accepted_checklist_item_ids,
            blocking_refs=sorted(
                checklist_item_ids - set(decision_record.accepted_checklist_item_ids)
            ),
        ),
        _check(
            "ready_decision_has_validation_evidence",
            (not ready_decision) or bool(decision_record.validation_evidence_refs),
            "Mark-ready decisions cite validation evidence refs.",
            artifact_refs=decision_record.validation_evidence_refs,
        ),
        _check(
            "draft_or_work_decision_has_followups",
            decision_record.decision == "mark_ready_for_review"
            or bool(decision_record.required_followups),
            "Draft/work decisions include required followups.",
            artifact_refs=decision_record.required_followups,
        ),
        _check(
            "no_side_effects_from_decision_recording",
            _record_boundary_clear(decision_record),
            "Recording the PR readiness decision did not mark the PR ready, write GitHub, write sibling repos, admit Lake records, or apply learning.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "blocked_by_pr_readiness_decision_evidence"
    elif decision_record.decision == "mark_ready_for_review":
        status = "pr_readiness_decision_recorded_manual_ready_action_required"
    elif decision_record.decision == "keep_draft":
        status = "pr_readiness_decision_recorded_keep_draft"
    elif decision_record.decision == "split_followup_work":
        status = "pr_readiness_decision_recorded_split_followup_work"
    else:
        status = "pr_readiness_decision_recorded_more_work_required"
    return PRReadinessDecisionReport(
        pr_readiness_decision_report_id=_stable_id(
            "prreadinessdecisionreport",
            "|".join(
                [
                    checklist.checklist_report_id,
                    closeout.closeout_report_id,
                    decision_record.pr_readiness_decision_id,
                    decision_record.decision,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_pr_review_checklist_id=checklist.checklist_report_id,
        source_pr_review_checklist_ref=checklist_ref,
        source_pr_review_checklist_status=checklist.status,
        source_closeout_report_id=closeout.closeout_report_id,
        source_closeout_report_ref=closeout_ref,
        source_closeout_status=closeout.status,
        pr_readiness_decision_id=decision_record.pr_readiness_decision_id,
        observed_pr_number=decision_record.observed_pr_number,
        observed_pr_url=decision_record.observed_pr_url,
        observed_pr_state=decision_record.observed_pr_state,
        reviewer_id=decision_record.reviewer_id,
        decision=decision_record.decision,
        decision_reason=decision_record.decision_reason,
        accepted_checklist_item_ids=decision_record.accepted_checklist_item_ids,
        validation_evidence_refs=decision_record.validation_evidence_refs,
        required_followups=decision_record.required_followups,
        red_team_notes=decision_record.red_team_notes,
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=PR_READINESS_DECISION_REQUIRED_NEXT_GATES,
        manual_ready_action_required=(
            status == "pr_readiness_decision_recorded_manual_ready_action_required"
        ),
        generated_at=now_iso(),
    )


def render_pr_readiness_decision_report(report: PRReadinessDecisionReport) -> str:
    lines = [
        "# PR Readiness Decision Report",
        "",
        f"**Report ID:** {report.pr_readiness_decision_report_id}",
        f"**Status:** {report.status}",
        f"**Decision:** {report.decision}",
        f"**Reviewer:** {report.reviewer_id}",
        f"**Observed PR:** {report.observed_pr_number or 'not supplied'}",
        f"**Observed PR state:** {report.observed_pr_state}",
        f"**Checklist:** `{report.source_pr_review_checklist_ref}`",
        f"**Closeout:** `{report.source_closeout_report_ref}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Human Decision",
        "",
        f"- Decision reason: {report.decision_reason}",
        f"- Accepted checklist items: {len(report.accepted_checklist_item_ids)}",
        f"- Validation evidence refs: {len(report.validation_evidence_refs)}",
        f"- Required followups: {len(report.required_followups)}",
        f"- Manual ready action required: {report.manual_ready_action_required}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary",
            "",
            f"- PR marked ready: {report.pr_marked_ready}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Proposed changes applied: {report.proposed_changes_applied}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report records the local human PR readiness decision only. It does not mark a PR ready, call GitHub write APIs, create issues, write sibling repos, admit Lake records, write SQLite, promote canon, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_pr_readiness_decision_record(
    *,
    pr_review_checklist_path: str | Path,
    intake_local_closeout_report_path: str | Path,
    decision_path: str | Path,
    out_dir: str | Path,
) -> tuple[PRReadinessDecisionReport, Path]:
    checklist_path = Path(pr_review_checklist_path)
    closeout_path = Path(intake_local_closeout_report_path)
    record_path = Path(decision_path)
    checklist = PRReviewChecklistReport.model_validate(load_json(checklist_path))
    closeout = IntakeLocalCloseoutReport.model_validate(load_json(closeout_path))
    raw_record = PRReadinessDecisionRecord.model_validate(load_json(record_path))
    record = _bind_record(record=raw_record, checklist=checklist, closeout=closeout)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    history_path = run_dir / PR_READINESS_DECISION_HISTORY_FILENAME
    report = build_pr_readiness_decision_report(
        checklist=checklist,
        checklist_ref=str(checklist_path),
        closeout=closeout,
        closeout_ref=str(closeout_path),
        decision_record=record,
        history_ref=str(history_path),
    )
    write_json(run_dir / PR_READINESS_DECISION_RECORD_FILENAME, record.model_dump(mode="json"))
    append_jsonl(history_path, record.model_dump(mode="json"))
    write_json(run_dir / PR_READINESS_DECISION_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / PR_READINESS_DECISION_NOTES_FILENAME).write_text(
        render_pr_readiness_decision_report(report),
        encoding="utf-8",
    )
    return report, run_dir
