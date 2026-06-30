from __future__ import annotations

from pathlib import Path

from .models import (
    CrossRepoOwnerIssueDraft,
    CrossRepoOwnerIssueDraftQualityCheck,
    CrossRepoOwnerIssueDraftQualityItem,
    CrossRepoOwnerIssueDraftQualityReport,
    CrossRepoOwnerIssueDraftReport,
)
from .util import digest_text, load_json, now_iso, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
OWNER_ISSUE_DRAFT_QUALITY_REPORT_FILENAME = "owner_issue_draft_quality_report.json"
OWNER_ISSUE_DRAFT_QUALITY_NOTES_FILENAME = "owner_issue_draft_quality_report.md"

REQUIRED_SECTIONS = [
    "## Summary",
    "## Source Evidence",
    "## Candidate Proposals",
    "## Required Owner Actions",
    "## Acceptance Checks",
    "## Red-Team Notes",
    "## Required Next Gates",
    "## Boundary",
]

SOURCE_EVIDENCE_LABELS = [
    "Owner adoption packet:",
    "Promotion package:",
    "Readiness audit:",
    "PR review checklist:",
]

BOUNDARY_PHRASES = [
    "Intake did not create this issue.",
    "Intake did not write a sibling repo.",
    "Intake did not promote canonical schemas, event classes, route IDs, or skill trust records.",
    "Intake did not admit Lake records or write SQLite.",
    "Intake did not implement production connectors or external writes.",
    "Intake did not apply learning or mutate baselines.",
]

REQUIRED_NEXT_GATES = [
    "manual_owner_issue_creation_if_desired",
    "owning_repo_triage",
    "owner_repo_implementation_pr_if_accepted",
    "cross_repo_contract_validation_after_owner_changes",
    "no_intake_github_or_sibling_repo_write",
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
) -> CrossRepoOwnerIssueDraftQualityCheck:
    return CrossRepoOwnerIssueDraftQualityCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _report_boundary_clear(report: CrossRepoOwnerIssueDraftReport) -> bool:
    return (
        report.manual_creation_required is True
        and report.github_issue_created is False
        and report.github_pr_created is False
        and report.github_write_performed is False
        and report.sibling_repo_write_performed is False
        and report.promotion_authorized is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
        and all(_draft_boundary_clear(draft) for draft in report.drafts)
    )


def _draft_boundary_clear(draft: CrossRepoOwnerIssueDraft) -> bool:
    return (
        draft.manual_creation_required is True
        and draft.github_issue_created is False
        and draft.github_pr_created is False
        and draft.github_write_performed is False
        and draft.sibling_repo_write_performed is False
        and draft.promotion_authorized is False
        and draft.lake_write_performed is False
        and draft.sqlite_write_performed is False
        and draft.external_writes_performed is False
        and draft.silent_learning_performed is False
    )


def _resolve_markdown_ref(ref: str, base_dir: Path | None) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    candidates = []
    if base_dir is not None:
        candidates.append(base_dir / path)
    candidates.extend([REPO_ROOT / path, path])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _read_markdown(ref: str, base_dir: Path | None) -> tuple[bool, str]:
    path = _resolve_markdown_ref(ref, base_dir)
    if not path.is_file():
        return False, ""
    return True, path.read_text(encoding="utf-8")


def _quality_item(
    *,
    draft: CrossRepoOwnerIssueDraft,
    output_ref: str,
    output_ref_base_dir: Path | None,
) -> CrossRepoOwnerIssueDraftQualityItem:
    output_exists, output_text = _read_markdown(output_ref, output_ref_base_dir)
    text = draft.issue_body_markdown
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
    missing_source_labels = [label for label in SOURCE_EVIDENCE_LABELS if label not in text]
    missing_boundary = [phrase for phrase in BOUNDARY_PHRASES if phrase not in text]
    markdown_matches = output_exists and output_text == draft.issue_body_markdown
    quality_failed = (
        missing_sections
        or missing_source_labels
        or missing_boundary
        or not output_exists
        or not markdown_matches
        or not draft.suggested_labels
        or not draft.required_owner_actions
        or not draft.acceptance_checks
        or not draft.red_team_notes
        or not draft.required_next_gates
        or not _draft_boundary_clear(draft)
    )
    if draft.status != "ready_for_manual_issue_creation":
        status = "blocked_by_source_issue_draft"
    elif quality_failed:
        status = "failed_quality_gate"
    else:
        status = "ready_for_manual_owner_issue_review"
    return CrossRepoOwnerIssueDraftQualityItem(
        target_repo=draft.target_repo,
        issue_draft_id=draft.issue_draft_id,
        source_issue_draft_status=draft.status,
        status=status,  # type: ignore[arg-type]
        issue_draft_output_ref=output_ref,
        markdown_output_exists=output_exists,
        markdown_matches_embedded_body=markdown_matches,
        missing_required_sections=missing_sections,
        missing_source_evidence_labels=missing_source_labels,
        missing_boundary_phrases=missing_boundary,
        suggested_label_count=len(draft.suggested_labels),
        required_owner_action_count=len(draft.required_owner_actions),
        acceptance_check_count=len(draft.acceptance_checks),
        red_team_note_count=len(draft.red_team_notes),
        required_next_gate_count=len(draft.required_next_gates),
        proposal_count=draft.proposal_count,
    )


def _build_checks(
    *,
    source_report: CrossRepoOwnerIssueDraftReport,
    source_report_ref: str,
    quality_items: list[CrossRepoOwnerIssueDraftQualityItem],
) -> list[CrossRepoOwnerIssueDraftQualityCheck]:
    missing_outputs = [
        item.issue_draft_output_ref for item in quality_items if not item.markdown_output_exists
    ]
    mismatch_outputs = [
        item.issue_draft_output_ref
        for item in quality_items
        if item.markdown_output_exists and not item.markdown_matches_embedded_body
    ]
    missing_sections = [
        f"{item.target_repo}:{section}"
        for item in quality_items
        for section in item.missing_required_sections
    ]
    missing_source_labels = [
        f"{item.target_repo}:{label}"
        for item in quality_items
        for label in item.missing_source_evidence_labels
    ]
    missing_boundary = [
        f"{item.target_repo}:{phrase}"
        for item in quality_items
        for phrase in item.missing_boundary_phrases
    ]
    metadata_blockers = [
        item.target_repo
        for item in quality_items
        if not (
            item.suggested_label_count
            and item.required_owner_action_count
            and item.acceptance_check_count
            and item.red_team_note_count
            and item.required_next_gate_count
        )
    ]
    blocked_source_items = [
        item.target_repo for item in quality_items if item.status == "blocked_by_source_issue_draft"
    ]
    return [
        _check(
            "source_issue_draft_report_ready_without_writes",
            source_report.status == "issue_drafts_ready_for_manual_creation"
            and source_report.blocked_draft_count == 0
            and _report_boundary_clear(source_report),
            "Source issue draft report is ready and preserves manual/no-write boundaries.",
            artifact_refs=[source_report_ref],
        ),
        _check(
            "blocked_source_drafts_remain_blocked",
            not blocked_source_items,
            "Blocked source drafts are not treated as ready for manual owner issue creation.",
            artifact_refs=[source_report_ref],
            blocking_refs=blocked_source_items,
        ),
        _check(
            "issue_draft_markdown_outputs_exist_and_match",
            not missing_outputs and not mismatch_outputs,
            "Every markdown output ref exists and matches the embedded issue body.",
            artifact_refs=source_report.draft_output_refs,
            blocking_refs=[*missing_outputs, *mismatch_outputs],
        ),
        _check(
            "issue_draft_sections_complete",
            not missing_sections,
            "Every owner issue draft includes required review sections.",
            artifact_refs=source_report.draft_output_refs,
            blocking_refs=missing_sections,
        ),
        _check(
            "issue_draft_source_evidence_complete",
            not missing_source_labels,
            "Every owner issue draft exposes owner packet, promotion package, readiness audit, and PR checklist refs.",
            artifact_refs=source_report.draft_output_refs,
            blocking_refs=missing_source_labels,
        ),
        _check(
            "issue_draft_boundary_text_complete",
            not missing_boundary,
            "Every owner issue draft preserves explicit no-write/no-promotion/no-learning boundary text.",
            artifact_refs=source_report.draft_output_refs,
            blocking_refs=missing_boundary,
        ),
        _check(
            "issue_draft_metadata_complete",
            not metadata_blockers,
            "Every owner issue draft has labels, owner actions, acceptance checks, red-team notes, and next gates.",
            artifact_refs=source_report.draft_output_refs,
            blocking_refs=metadata_blockers,
        ),
    ]


def build_owner_issue_draft_quality_report(
    *,
    issue_draft_report: CrossRepoOwnerIssueDraftReport,
    issue_draft_report_ref: str,
    issue_draft_report_base_dir: str | Path | None = None,
) -> CrossRepoOwnerIssueDraftQualityReport:
    base_dir = Path(issue_draft_report_base_dir) if issue_draft_report_base_dir else None
    quality_items = [
        _quality_item(
            draft=draft,
            output_ref=output_ref,
            output_ref_base_dir=base_dir,
        )
        for draft, output_ref in zip(
            issue_draft_report.drafts,
            issue_draft_report.draft_output_refs,
            strict=True,
        )
    ]
    checks = _build_checks(
        source_report=issue_draft_report,
        source_report_ref=issue_draft_report_ref,
        quality_items=quality_items,
    )
    failed_checks = [check for check in checks if check.status == "failed"]
    ready_count = sum(
        1 for item in quality_items if item.status == "ready_for_manual_owner_issue_review"
    )
    blocked_count = sum(
        1 for item in quality_items if item.status == "blocked_by_source_issue_draft"
    )
    failed_count = sum(1 for item in quality_items if item.status == "failed_quality_gate")
    return CrossRepoOwnerIssueDraftQualityReport(
        quality_report_id=_stable_id(
            "ownerissuedraftquality",
            f"{issue_draft_report.issue_draft_report_id}|{issue_draft_report_ref}",
        ),
        status=(
            "blocked_by_owner_issue_draft_quality"
            if failed_checks or blocked_count or failed_count
            else "owner_issue_draft_quality_ready_for_manual_review"
        ),
        source_issue_draft_report_id=issue_draft_report.issue_draft_report_id,
        source_issue_draft_report_ref=issue_draft_report_ref,
        source_issue_draft_status=issue_draft_report.status,
        draft_count=len(quality_items),
        ready_item_count=ready_count,
        blocked_item_count=blocked_count,
        failed_item_count=failed_count,
        target_repos=issue_draft_report.target_repos,
        quality_items=quality_items,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_owner_issue_draft_quality_report(
    report: CrossRepoOwnerIssueDraftQualityReport,
) -> str:
    lines = [
        "# Owner Issue Draft Quality Report",
        "",
        f"**Report ID:** {report.quality_report_id}",
        f"**Status:** {report.status}",
        f"**Source issue draft report:** `{report.source_issue_draft_report_ref}`",
        f"**Ready items:** {report.ready_item_count}",
        f"**Blocked items:** {report.blocked_item_count}",
        f"**Failed items:** {report.failed_item_count}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(["", "## Draft Items", ""])
    for item in report.quality_items:
        blockers = [
            *item.missing_required_sections,
            *item.missing_source_evidence_labels,
            *item.missing_boundary_phrases,
        ]
        lines.extend(
            [
                f"### {item.target_repo}",
                "",
                f"- Draft ID: `{item.issue_draft_id}`",
                f"- Status: {item.status}",
                f"- Source draft status: {item.source_issue_draft_status}",
                f"- Markdown ref: `{item.issue_draft_output_ref}`",
                f"- Markdown exists: {item.markdown_output_exists}",
                f"- Markdown matches embedded body: {item.markdown_matches_embedded_body}",
                "- Missing blockers: "
                + (", ".join(f"`{blocker}`" for blocker in blockers) or "none"),
                "",
            ]
        )
    lines.extend(
        [
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary Flags",
            "",
            f"- Manual creation required: {report.manual_creation_required}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This quality report is local review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_owner_issue_draft_quality_audit(
    *,
    issue_draft_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[CrossRepoOwnerIssueDraftQualityReport, Path]:
    report_path = Path(issue_draft_report_path)
    issue_draft_report = CrossRepoOwnerIssueDraftReport.model_validate(load_json(report_path))
    report = build_owner_issue_draft_quality_report(
        issue_draft_report=issue_draft_report,
        issue_draft_report_ref=str(report_path),
        issue_draft_report_base_dir=report_path.parent,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / OWNER_ISSUE_DRAFT_QUALITY_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / OWNER_ISSUE_DRAFT_QUALITY_NOTES_FILENAME).write_text(
        render_owner_issue_draft_quality_report(report),
        encoding="utf-8",
    )
    return report, run_dir
