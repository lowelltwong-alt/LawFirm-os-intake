from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .models import (
    DADReviewIssueOutboxCheck,
    DADReviewIssueOutboxMail,
    DADReviewIssueOutboxReport,
    DADReviewIssueRecord,
)
from .util import append_jsonl, digest_json, load_json, load_jsonl, now_iso, write_json


DAD_REVIEW_ISSUE_OUTBOX_REPORT_FILENAME = "dad_review_issue_outbox_report.json"
DEFAULT_DAD_OUTBOX_PATH = Path(".digital-asset/mail/outbox.jsonl")
MAX_TEXT_FIELD_LENGTH = 6000
MAX_MAIL_PAYLOAD_TEXT_LENGTH = 30000

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openai_api_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("email_address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ssn_like_identifier", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
)


def record_dad_review_issue_to_outbox(
    issue_path: str | Path,
    *,
    repo_root: str | Path = ".",
    outbox_path: str | Path | None = None,
    report_out: str | Path | None = None,
) -> tuple[DADReviewIssueOutboxReport, Path]:
    repo = Path(repo_root).resolve()
    issue = DADReviewIssueRecord.model_validate(load_json(issue_path))
    _validate_mail_safe_issue(issue)

    outbox = _resolve_outbox_path(repo, outbox_path)
    _ensure_mailbox(outbox)
    mail = _build_mail(issue=issue, repo=repo)
    existing = load_jsonl(outbox)
    duplicate = any(
        row.get("mail_id") == mail.mail_id or row.get("dedupe_key") == mail.dedupe_key
        for row in existing
        if isinstance(row, dict)
    )
    if not duplicate:
        append_jsonl(outbox, mail.model_dump(mode="json"))

    checks = _build_checks(issue=issue, mail=mail, duplicate=duplicate)
    report = DADReviewIssueOutboxReport(
        dad_review_issue_outbox_report_id=_stable_id(
            "dad_review_issue_outbox_report", issue.issue_id, issue.issue_version
        ),
        status=(
            "dad_review_issue_duplicate_suppressed"
            if duplicate
            else "dad_review_issue_recorded_to_outbox"
        ),
        source_issue_id=issue.issue_id,
        source_issue_version=issue.issue_version,
        severity=issue.severity,
        issue_classes=issue.issue_classes,
        candidate_exception_labels=issue.candidate_exception_labels,
        dad_mail_id=mail.mail_id,
        dad_thread_id=mail.thread_id,
        dedupe_key=mail.dedupe_key,
        outbox_ref=str(outbox),
        outbox_append_performed=not duplicate,
        outbox_duplicate_suppressed=duplicate,
        payload_sha256=digest_json(mail.model_dump(mode="json")),
        mail_payload=mail,
        checks=checks,
        generated_at=now_iso(),
    )

    if report_out:
        write_json(report_out, report.model_dump(mode="json"))
    return report, outbox


def _resolve_outbox_path(repo: Path, outbox_path: str | Path | None) -> Path:
    candidate = Path(outbox_path) if outbox_path is not None else DEFAULT_DAD_OUTBOX_PATH
    if not candidate.is_absolute():
        candidate = repo / candidate
    resolved = candidate.resolve()
    mailbox_root = (repo / ".digital-asset" / "mail").resolve()
    if mailbox_root not in [resolved, *resolved.parents]:
        raise ValueError("DAD review issue outbox must stay under .digital-asset/mail")
    if resolved.name != "outbox.jsonl":
        raise ValueError("DAD review issue outbox path must end with outbox.jsonl")
    return resolved


def _ensure_mailbox(outbox: Path) -> None:
    outbox.parent.mkdir(parents=True, exist_ok=True)
    readme = outbox.parent / "README.md"
    if not readme.exists():
        readme.write_text(
            "# DAD Mailbox\n\n"
            "This repo-local mailbox stores candidate DAD mail.\n"
            "`outbox.jsonl` is append-only operational state and should not be committed.\n",
            encoding="utf-8",
            newline="\n",
        )
    gitignore = outbox.parent / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*.jsonl\nlast_checked.json\n", encoding="utf-8", newline="\n")


def _build_mail(issue: DADReviewIssueRecord, repo: Path) -> DADReviewIssueOutboxMail:
    payload = {
        "command_kind": "dad_review_issue_capture",
        "summary": issue.finding_summary,
        "issue_id": issue.issue_id,
        "issue_version": issue.issue_version,
        "source_repo_id": issue.source_repo_id,
        "originating_agent": issue.originating_agent,
        "review_context": issue.review_context,
        "finding_title": issue.finding_title,
        "severity": issue.severity,
        "issue_classes": issue.issue_classes,
        "observable_context": issue.observable_context,
        "observable_decision_logic": issue.observable_decision_logic,
        "solution_path": issue.solution_path,
        "fix_status": issue.fix_status,
        "fix_refs": issue.fix_refs,
        "test_refs": issue.test_refs,
        "artifact_refs": issue.artifact_refs,
        "candidate_exception_labels": issue.candidate_exception_labels,
        "applies_when": issue.applies_when,
        "does_not_apply_when": issue.does_not_apply_when,
        "danger_if_misapplied": issue.danger_if_misapplied,
        "reviewer_notes": issue.reviewer_notes,
        "red_team_notes": issue.red_team_notes,
        "promotion_boundary": (
            "Candidate mail only. DAD/human review is required before this becomes "
            "a deterministic learning rule, registry entry, or cross-repo default."
        ),
        "hidden_chain_of_thought_included": False,
        "raw_private_payload_included": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "silent_learning_performed": False,
    }
    return DADReviewIssueOutboxMail(
        mail_id=_stable_uuid("dad:mail", issue.issue_id, issue.issue_version, digest_json(payload)),
        thread_id=_stable_uuid("dad:mail-thread", issue.issue_id),
        source_repo=str(repo),
        created_at=issue.observed_at,
        dedupe_key=f"lawfirm-os-intake:dad-review-issue:{issue.issue_id}:{issue.issue_version}",
        payload=payload,
        evidence=_dedupe_preserve_order(
            [
                *issue.artifact_refs,
                *issue.fix_refs,
                *issue.test_refs,
                "LawFirm-os-intake DAD review issue outbox contract",
            ]
        ),
        suggested_actions=issue.suggested_actions,
        source_provenance={
            "canonical_source_repo": str(repo),
            "source_repo_id": "LawFirm-os-intake",
            "source_repo_alias": "LawFirm-os-intake",
            "source_visibility": "private",
            "original_source_chain": ["LawFirm-os-intake"],
            "return_address": str(repo / DEFAULT_DAD_OUTBOX_PATH),
            "original_mail_id": "",
            "composed_by": "lawfirm-os-intake",
            "collected_by": "",
            "collected_at": "",
            "received_at": issue.observed_at,
        },
        public_release={
            "target_visibility": "private",
            "target_public_facing": False,
            "public_release_required": False,
            "public_release_status": "not_required",
            "human_release_id": "",
            "release_reason": "private_to_private_candidate_mail",
        },
    )


def _build_checks(
    *,
    issue: DADReviewIssueRecord,
    mail: DADReviewIssueOutboxMail,
    duplicate: bool,
) -> list[DADReviewIssueOutboxCheck]:
    return [
        DADReviewIssueOutboxCheck(
            check_id="candidate_only_mail_boundary",
            status="passed",
            message="Review issue mail remains candidate-only and requires DAD review before promotion.",
        ),
        DADReviewIssueOutboxCheck(
            check_id="classified_issue_pattern_fields",
            status="passed",
            message="Issue carries severity, issue classes, exception labels, applicability limits, and fix status.",
            details={
                "severity": issue.severity,
                "issue_classes": issue.issue_classes,
                "candidate_exception_labels": issue.candidate_exception_labels,
            },
        ),
        DADReviewIssueOutboxCheck(
            check_id="observable_logic_without_hidden_chain_of_thought",
            status="passed",
            message=(
                "Mail carries observable context, decision logic, and solution path, "
                "but hidden chain-of-thought is explicitly excluded."
            ),
        ),
        DADReviewIssueOutboxCheck(
            check_id="no_lake_sqlite_or_external_write",
            status="passed",
            message="Recorder writes only repo-local DAD outbox JSONL and performs no Lake, SQLite, or external writes.",
        ),
        DADReviewIssueOutboxCheck(
            check_id="dedupe_outcome",
            status="passed",
            message="Duplicate DAD review issue was suppressed."
            if duplicate
            else "New DAD review issue was appended.",
            details={"mail_id": mail.mail_id, "dedupe_key": mail.dedupe_key},
        ),
    ]


def _validate_mail_safe_issue(issue: DADReviewIssueRecord) -> None:
    values = list(_iter_text_values(issue.model_dump(mode="json")))
    oversized = [value[:80] for value in values if len(value) > MAX_TEXT_FIELD_LENGTH]
    if oversized:
        raise ValueError("DAD review issue contains an oversized text field")
    total_text_length = sum(len(value) for value in values)
    if total_text_length > MAX_MAIL_PAYLOAD_TEXT_LENGTH:
        raise ValueError("DAD review issue mail payload is too large for DAD outbox")
    sensitive_hits = sorted(
        pattern_id
        for value in values
        for pattern_id, pattern in SENSITIVE_PATTERNS
        if pattern.search(value)
    )
    if sensitive_hits:
        raise ValueError(
            "DAD review issue contains sensitive-looking text: " + ",".join(sensitive_hits)
        )


def _iter_text_values(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_text_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_text_values(nested)


def _stable_uuid(prefix: str, *parts: str) -> str:
    name = "|".join(parts)
    return f"{prefix}:{uuid5(NAMESPACE_URL, name)}"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
