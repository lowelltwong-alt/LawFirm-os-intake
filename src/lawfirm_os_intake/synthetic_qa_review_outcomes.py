from __future__ import annotations

from pathlib import Path

from .models import (
    SyntheticQABlockerReport,
    SyntheticQABlockerReviewDecision,
    SyntheticQABlockerReviewOutcomeRecord,
    SyntheticQABlockerReviewOutcomeReport,
)
from .util import append_jsonl, digest_json, load_json, now_iso, write_json


SYNTHETIC_QA_REVIEW_OUTCOME_RECORD_FILENAME = "synthetic_qa_review_outcome_record.json"
SYNTHETIC_QA_REVIEW_OUTCOME_HISTORY_FILENAME = "synthetic_qa_review_outcome_history.jsonl"
SYNTHETIC_QA_REVIEW_OUTCOME_REPORT_FILENAME = "synthetic_qa_review_outcome_report.json"
SYNTHETIC_QA_REVIEW_OUTCOME_NOTES_FILENAME = "synthetic_qa_review_outcome_report.md"

SYNTHETIC_QA_REVIEW_OUTCOME_REQUIRED_NEXT_ACTIONS = [
    "Keep this synthetic QA review outcome candidate-only and local.",
    "Resolve needs-fix followups before treating affected QA rows as accepted.",
    "Route deferred rows into the remaining roadmap rather than calibration or production learning.",
    "Do not write this outcome to Exception Lake/SQLite until the owning runtime approves admission.",
]


def _row_ids(report: SyntheticQABlockerReport) -> set[str]:
    return {row.row_id for row in report.rows}


def _bind_record_to_report(
    *,
    report: SyntheticQABlockerReport,
    record: SyntheticQABlockerReviewOutcomeRecord,
) -> SyntheticQABlockerReviewOutcomeRecord:
    if record.synthetic_qa_blocker_report_id != report.synthetic_qa_blocker_report_id:
        raise ValueError(
            "synthetic QA review outcome source report id mismatch: "
            f"{record.synthetic_qa_blocker_report_id} != {report.synthetic_qa_blocker_report_id}"
        )
    known_rows = _row_ids(report)
    unknown_rows = sorted({decision.row_id for decision in record.decisions} - known_rows)
    if unknown_rows:
        raise ValueError(
            "synthetic QA review outcome targets unknown blocker rows: " + ", ".join(unknown_rows)
        )
    return record


def _required_followups(decisions: list[SyntheticQABlockerReviewDecision]) -> list[str]:
    return [
        followup
        for decision in decisions
        for followup in decision.required_followups
        if followup.strip()
    ]


def _candidate_lake_event_labels(decisions: list[SyntheticQABlockerReviewDecision]) -> list[str]:
    labels = {"synthetic_qa_review_outcome_recorded_candidate"}
    outcomes = {decision.outcome for decision in decisions}
    if "accepted_for_poc_review" in outcomes:
        labels.add("synthetic_qa_poc_acceptance_candidate")
    if "needs_fix" in outcomes:
        labels.add("synthetic_qa_fix_followup_candidate")
    if "defer_to_roadmap" in outcomes:
        labels.add("synthetic_qa_roadmap_deferred_candidate")
    if "not_applicable" in outcomes:
        labels.add("synthetic_qa_not_applicable_candidate")
    for decision in decisions:
        labels.update(decision.candidate_exception_lake_labels)
    return sorted(labels)


def _status(
    *,
    source_report: SyntheticQABlockerReport,
    unreviewed_count: int,
    required_followup_count: int,
) -> str:
    if source_report.status == "failed_synthetic_qa_blocker_boundary":
        return "blocked_by_synthetic_qa_review_outcome"
    if unreviewed_count or required_followup_count:
        return "synthetic_qa_review_outcome_recorded_pending_followup"
    return "synthetic_qa_review_outcome_recorded"


def _required_next_actions(
    *,
    status: str,
    unreviewed_row_ids: list[str],
    required_followups: list[str],
) -> list[str]:
    if status == "blocked_by_synthetic_qa_review_outcome":
        return [
            "Repair the source synthetic QA blocker report before recording review outcomes.",
            "Do not use blocked QA review outcomes for calibration, learning, or production claims.",
        ]
    actions = list(SYNTHETIC_QA_REVIEW_OUTCOME_REQUIRED_NEXT_ACTIONS)
    if unreviewed_row_ids:
        actions.insert(
            0,
            "Record superseding synthetic QA review decisions for unreviewed rows: "
            + ", ".join(unreviewed_row_ids),
        )
    if required_followups:
        actions.insert(0, "Complete required synthetic QA followups before closing this review.")
    if status == "synthetic_qa_review_outcome_recorded":
        return [
            "Synthetic QA queue review is recorded; keep production/calibration gates blocked until owner adoption.",
            "Use this as local QA evidence only, not as budget approval or learning authorization.",
        ]
    return actions


def build_synthetic_qa_review_outcome_report(
    *,
    source_report: SyntheticQABlockerReport,
    source_report_ref: str,
    outcome_record: SyntheticQABlockerReviewOutcomeRecord,
    history_ref: str,
    generated_at: str | None = None,
) -> SyntheticQABlockerReviewOutcomeReport:
    reviewed_row_ids = sorted({decision.row_id for decision in outcome_record.decisions})
    source_row_ids = sorted(_row_ids(source_report))
    unreviewed_row_ids = sorted(set(source_row_ids) - set(reviewed_row_ids))
    unknown_row_ids = sorted(set(reviewed_row_ids) - set(source_row_ids))
    required_followups = _required_followups(outcome_record.decisions)
    accepted_count = sum(
        1 for decision in outcome_record.decisions if decision.outcome == "accepted_for_poc_review"
    )
    needs_fix_count = sum(
        1 for decision in outcome_record.decisions if decision.outcome == "needs_fix"
    )
    deferred_count = sum(
        1 for decision in outcome_record.decisions if decision.outcome == "defer_to_roadmap"
    )
    not_applicable_count = sum(
        1 for decision in outcome_record.decisions if decision.outcome == "not_applicable"
    )
    status = _status(
        source_report=source_report,
        unreviewed_count=len(unreviewed_row_ids),
        required_followup_count=len(required_followups),
    )
    report_core = {
        "source_synthetic_qa_blocker_report_id": source_report.synthetic_qa_blocker_report_id,
        "synthetic_qa_review_outcome_record_id": (
            outcome_record.synthetic_qa_review_outcome_record_id
        ),
        "reviewed_row_ids": reviewed_row_ids,
        "unreviewed_row_ids": unreviewed_row_ids,
        "required_followups": required_followups,
        "status": status,
    }
    return SyntheticQABlockerReviewOutcomeReport(
        synthetic_qa_review_outcome_report_id="synthetic_qa_review_outcome_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,  # type: ignore[arg-type]
        source_synthetic_qa_blocker_report_ref=source_report_ref,
        source_synthetic_qa_blocker_report_id=source_report.synthetic_qa_blocker_report_id,
        source_synthetic_qa_blocker_report_status=source_report.status,
        synthetic_qa_review_outcome_record_id=(
            outcome_record.synthetic_qa_review_outcome_record_id
        ),
        reviewer_id=outcome_record.reviewer_id,
        reviewed_at=outcome_record.reviewed_at,
        decision_reason=outcome_record.decision_reason,
        source_row_count=len(source_row_ids),
        decision_count=len(outcome_record.decisions),
        accepted_decision_count=accepted_count,
        needs_fix_decision_count=needs_fix_count,
        deferred_decision_count=deferred_count,
        not_applicable_decision_count=not_applicable_count,
        reviewed_row_count=len(reviewed_row_ids),
        unreviewed_row_count=len(unreviewed_row_ids),
        unknown_row_count=len(unknown_row_ids),
        unresolved_followup_count=len(required_followups),
        reviewed_row_ids=reviewed_row_ids,
        unreviewed_row_ids=unreviewed_row_ids,
        unknown_row_ids=unknown_row_ids,
        required_followups=required_followups,
        candidate_lake_event_labels=_candidate_lake_event_labels(outcome_record.decisions),
        append_only_history_ref=history_ref,
        required_next_actions=_required_next_actions(
            status=status,
            unreviewed_row_ids=unreviewed_row_ids,
            required_followups=required_followups,
        ),
        generated_at=generated_at or now_iso(),
    )


def render_synthetic_qa_review_outcome_report(
    report: SyntheticQABlockerReviewOutcomeReport,
) -> str:
    lines = [
        "# Synthetic QA Review Outcome Report",
        "",
        f"**Report ID:** `{report.synthetic_qa_review_outcome_report_id}`",
        f"**Status:** `{report.status}`",
        f"**Source blocker report:** `{report.source_synthetic_qa_blocker_report_id}`",
        f"**Outcome record:** `{report.synthetic_qa_review_outcome_record_id}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Coverage",
        "",
        f"- Source rows: {report.source_row_count}",
        f"- Reviewed rows: {report.reviewed_row_count}",
        f"- Unreviewed rows: {report.unreviewed_row_count}",
        f"- Required followups: {report.unresolved_followup_count}",
        "",
        "## Decisions",
        "",
        f"- Accepted for POC review: {report.accepted_decision_count}",
        f"- Needs fix: {report.needs_fix_decision_count}",
        f"- Deferred to roadmap: {report.deferred_decision_count}",
        f"- Not applicable: {report.not_applicable_decision_count}",
        "",
        "## Candidate Lake Labels",
        "",
        *(f"- {label}" for label in report.candidate_lake_event_labels),
        "",
        "## Required Next Actions",
        "",
        *(f"- {action}" for action in report.required_next_actions),
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Synthetic only: {report.synthetic_only}",
        f"- Append-only: {report.append_only}",
        f"- Calibration authorized: {not report.not_authorized_for_calibration}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "This report records local synthetic QA review outcome evidence only. It does not approve budgets, open matters, write Lake/SQLite records, mutate fixtures, or authorize calibration or learning.",
        "",
    ]
    return "\n".join(lines)


def run_synthetic_qa_review_outcome_record(
    *,
    synthetic_qa_blocker_report_path: str | Path,
    outcome_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[SyntheticQABlockerReviewOutcomeReport, Path]:
    blocker_report_path = Path(synthetic_qa_blocker_report_path)
    outcome_record_path = Path(outcome_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    source_report = SyntheticQABlockerReport.model_validate(load_json(blocker_report_path))
    raw_record = SyntheticQABlockerReviewOutcomeRecord.model_validate(
        load_json(outcome_record_path)
    )
    outcome_record = _bind_record_to_report(report=source_report, record=raw_record)
    history_path = run_dir / SYNTHETIC_QA_REVIEW_OUTCOME_HISTORY_FILENAME
    report = build_synthetic_qa_review_outcome_report(
        source_report=source_report,
        source_report_ref=str(blocker_report_path),
        outcome_record=outcome_record,
        history_ref=str(history_path),
        generated_at=generated_at,
    )
    write_json(
        run_dir / SYNTHETIC_QA_REVIEW_OUTCOME_RECORD_FILENAME,
        outcome_record.model_dump(mode="json"),
    )
    append_jsonl(history_path, outcome_record.model_dump(mode="json"))
    write_json(
        run_dir / SYNTHETIC_QA_REVIEW_OUTCOME_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / SYNTHETIC_QA_REVIEW_OUTCOME_NOTES_FILENAME).write_text(
        render_synthetic_qa_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir
