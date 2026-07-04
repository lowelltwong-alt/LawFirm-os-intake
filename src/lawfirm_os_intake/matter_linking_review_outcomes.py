from __future__ import annotations

from pathlib import Path

from .models import (
    MatterLinkingPreflightReport,
    MatterLinkingReviewDecision,
    MatterLinkingReviewOutcomeCheck,
    MatterLinkingReviewOutcomeRecord,
    MatterLinkingReviewOutcomeReport,
)
from .util import append_jsonl, digest_json, load_json, now_iso, write_json


MATTER_LINKING_REVIEW_OUTCOME_RECORD_FILENAME = "matter_linking_review_outcome_record.json"
MATTER_LINKING_REVIEW_OUTCOME_HISTORY_FILENAME = "matter_linking_review_outcome_history.jsonl"
MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME = "matter_linking_review_outcome_report.json"
MATTER_LINKING_REVIEW_OUTCOME_NOTES_FILENAME = "matter_linking_review_outcome_report.md"

MATTER_LINKING_REVIEW_OUTCOME_REQUIRED_NEXT_GATES = [
    "append_only_matter_linking_review_outcome",
    "conflict_seed_review_after_role_confirmation",
    "intake_preflight_orchestrator_owner_adoption_before_runtime_use",
    "exception_lake_owner_review_before_admission",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_intake",
    "no_silent_learning_from_matter_linking_review",
]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    decision_ids: list[str] | None = None,
    cluster_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> MatterLinkingReviewOutcomeCheck:
    return MatterLinkingReviewOutcomeCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        decision_ids=decision_ids or [],
        cluster_ids=cluster_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _preflight_boundary_clear(report: MatterLinkingPreflightReport) -> bool:
    return (
        report.status != "blocked_matter_linking_preflight"
        and report.candidate_only is True
        and report.synthetic_only is True
        and report.non_authoritative is True
        and report.local_json_only is True
        and report.human_review_required is True
        and report.upfront_connector_implemented is False
        and report.vendor_api_called is False
        and report.external_write_performed is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.matter_opening_authorized is False
        and report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.screen_created is False
        and report.silent_learning_performed is False
    )


def _record_boundary_clear(record: MatterLinkingReviewOutcomeRecord) -> bool:
    return (
        record.candidate_only is True
        and record.synthetic_only is True
        and record.non_authoritative is True
        and record.local_json_only is True
        and record.not_authorized_for_external_write is True
        and record.not_authorized_for_lake_write is True
        and record.not_authorized_for_sqlite_write is True
        and record.not_authorized_for_budget_submission is True
        and record.not_authorized_for_matter_opening is True
        and record.not_authorized_for_conflict_conclusion is True
        and record.budget_amount_output_authorized is False
        and record.budget_submission_authorized is False
        and record.conflict_conclusion_emitted is False
        and record.matter_opening_authorized is False
        and record.screen_created is False
        and record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.silent_learning_performed is False
    )


def _known_cluster_ids(report: MatterLinkingPreflightReport) -> set[str]:
    return {cluster.cluster_id for cluster in report.clusters}


def _selected_cluster_ids(decisions: list[MatterLinkingReviewDecision]) -> list[str]:
    return sorted(
        {cluster_id for decision in decisions for cluster_id in decision.selected_cluster_ids}
    )


def _required_followups(decisions: list[MatterLinkingReviewDecision]) -> list[str]:
    return [
        followup
        for decision in decisions
        for followup in decision.required_followups
        if followup.strip()
    ]


def _candidate_lake_event_labels(
    *,
    preflight_report: MatterLinkingPreflightReport,
    decisions: list[MatterLinkingReviewDecision],
) -> list[str]:
    labels = {
        "matter_linking_review_outcome_recorded_candidate",
        *preflight_report.candidate_exception_lake_labels,
    }
    outcomes = {decision.outcome for decision in decisions}
    if "confirm_split" in outcomes:
        labels.add("matter_linking_confirmed_split_candidate")
    if "confirm_merge" in outcomes:
        labels.add("matter_linking_confirmed_merge_candidate")
    if "confirm_single_candidate" in outcomes:
        labels.add("matter_linking_confirmed_single_candidate")
    if "unknown" in outcomes:
        labels.add("matter_linking_unknown_candidate")
    if "request_more_info" in outcomes:
        labels.add("matter_linking_followup_required_candidate")
    if "declined_or_referred" in outcomes:
        labels.add("matter_linking_declined_or_referred_candidate")
    for decision in decisions:
        labels.update(decision.candidate_exception_lake_labels)
    return sorted(labels)


def _required_next_gates(
    *,
    decisions: list[MatterLinkingReviewDecision],
    required_followups: list[str],
) -> list[str]:
    gates = set(MATTER_LINKING_REVIEW_OUTCOME_REQUIRED_NEXT_GATES)
    if required_followups or any(
        decision.outcome in {"unknown", "request_more_info", "declined_or_referred"}
        for decision in decisions
    ):
        gates.add("complete_matter_linking_followup_before_budget_or_opening")
    if any(decision.outcome in {"confirm_split", "confirm_merge"} for decision in decisions):
        gates.add("confirm_principal_party_roles_per_cluster_before_budget")
    return sorted(gates)


def build_matter_linking_review_outcome_report(
    *,
    matter_linking_preflight_report: MatterLinkingPreflightReport,
    matter_linking_preflight_report_ref: str,
    outcome_record: MatterLinkingReviewOutcomeRecord,
    history_ref: str,
    generated_at: str | None = None,
) -> MatterLinkingReviewOutcomeReport:
    known_cluster_ids = _known_cluster_ids(matter_linking_preflight_report)
    selected_cluster_ids = _selected_cluster_ids(outcome_record.decisions)
    unknown_cluster_ids = sorted(set(selected_cluster_ids) - known_cluster_ids)
    unreviewed_cluster_ids = sorted(known_cluster_ids - set(selected_cluster_ids))
    required_followups = _required_followups(outcome_record.decisions)
    candidate_lake_event_labels = _candidate_lake_event_labels(
        preflight_report=matter_linking_preflight_report,
        decisions=outcome_record.decisions,
    )
    preflight_ready = _preflight_boundary_clear(matter_linking_preflight_report)
    checks = [
        _check(
            "matter_linking_preflight_ready_without_writes",
            preflight_ready,
            "Source matter-linking preflight is reviewable and has no connector, Lake, SQLite, budget, matter-opening, conflict, screen, or learning side effects.",
            artifact_refs=[matter_linking_preflight_report_ref],
        ),
        _check(
            "outcome_record_matches_preflight",
            outcome_record.matter_linking_preflight_report_id
            == matter_linking_preflight_report.matter_linking_preflight_report_id,
            "Outcome record is bound to the supplied matter-linking preflight report.",
            artifact_refs=[matter_linking_preflight_report_ref],
        ),
        _check(
            "outcome_decisions_target_known_clusters",
            not unknown_cluster_ids,
            "Every selected cluster exists in the source matter-linking preflight report.",
            cluster_ids=unknown_cluster_ids,
            blocking_refs=unknown_cluster_ids,
        ),
        _check(
            "outcome_record_preserves_no_write_boundary",
            _record_boundary_clear(outcome_record),
            "Recording the matter-linking review outcome did not authorize budgets, matters, conflicts, screens, Lake/SQLite records, external writes, or learning.",
        ),
        _check(
            "human_outcome_record_complete",
            bool(
                outcome_record.reviewer_id.strip()
                and outcome_record.reviewed_at.strip()
                and outcome_record.decision_reason.strip()
                and outcome_record.decisions
            ),
            "Matter-linking review outcome includes reviewer, timestamp, reason, and decisions.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "blocked_by_matter_linking_review_outcome"
    elif unreviewed_cluster_ids or required_followups:
        status = "matter_linking_review_outcome_recorded_pending_followup"
    else:
        status = "matter_linking_review_outcome_recorded"
    report_core = {
        "matter_linking_preflight_report_id": (
            matter_linking_preflight_report.matter_linking_preflight_report_id
        ),
        "matter_linking_review_outcome_record_id": (
            outcome_record.matter_linking_review_outcome_record_id
        ),
        "selected_cluster_ids": selected_cluster_ids,
        "unknown_cluster_ids": unknown_cluster_ids,
        "status": status,
    }
    return MatterLinkingReviewOutcomeReport(
        matter_linking_review_outcome_report_id="matterlinkreviewoutcome_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status=status,  # type: ignore[arg-type]
        source_matter_linking_preflight_report_ref=matter_linking_preflight_report_ref,
        matter_linking_preflight_report_id=(
            matter_linking_preflight_report.matter_linking_preflight_report_id
        ),
        source_matter_linking_preflight_status=matter_linking_preflight_report.status,
        matter_linking_review_outcome_record_id=(
            outcome_record.matter_linking_review_outcome_record_id
        ),
        reviewer_id=outcome_record.reviewer_id,
        reviewed_at=outcome_record.reviewed_at,
        overall_outcome=outcome_record.overall_outcome,
        decision_reason=outcome_record.decision_reason,
        source_cluster_count=len(known_cluster_ids),
        decision_count=len(outcome_record.decisions),
        split_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "confirm_split"
        ),
        merge_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "confirm_merge"
        ),
        single_candidate_decision_count=sum(
            1
            for decision in outcome_record.decisions
            if decision.outcome == "confirm_single_candidate"
        ),
        unknown_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "unknown"
        ),
        request_more_info_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "request_more_info"
        ),
        declined_or_referred_decision_count=sum(
            1 for decision in outcome_record.decisions if decision.outcome == "declined_or_referred"
        ),
        reviewed_cluster_count=len(selected_cluster_ids),
        unreviewed_cluster_count=len(unreviewed_cluster_ids),
        unknown_cluster_count=len(unknown_cluster_ids),
        reviewed_cluster_ids=selected_cluster_ids,
        unreviewed_cluster_ids=unreviewed_cluster_ids,
        unknown_cluster_ids=unknown_cluster_ids,
        required_followups=required_followups,
        candidate_lake_event_labels=candidate_lake_event_labels,
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=_required_next_gates(
            decisions=outcome_record.decisions,
            required_followups=required_followups,
        ),
        generated_at=generated_at or now_iso(),
    )


def render_matter_linking_review_outcome_report(
    report: MatterLinkingReviewOutcomeReport,
) -> str:
    lines = [
        "# Matter-Linking Review Outcome Report",
        "",
        f"**Report ID:** `{report.matter_linking_review_outcome_report_id}`",
        f"**Status:** `{report.status}`",
        f"**Source preflight:** `{report.matter_linking_preflight_report_id}`",
        f"**Outcome record:** `{report.matter_linking_review_outcome_record_id}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Human Decision",
        "",
        f"- Overall outcome: {report.overall_outcome}",
        f"- Decision reason: {report.decision_reason}",
        f"- Reviewer: {report.reviewer_id}",
        f"- Reviewed at: {report.reviewed_at}",
        "",
        "## Cluster Coverage",
        "",
        f"- Source clusters: {report.source_cluster_count}",
        f"- Reviewed clusters: {report.reviewed_cluster_count}",
        f"- Unreviewed clusters: {report.unreviewed_cluster_count}",
        f"- Unknown cluster refs: {report.unknown_cluster_count}",
        "",
        "## Candidate Lake Labels",
        "",
        *(f"- {label}" for label in report.candidate_lake_event_labels),
        "",
        "## Required Followups",
        "",
    ]
    if not report.required_followups:
        lines.append("- No required followups recorded.")
    for followup in report.required_followups:
        lines.append(f"- {followup}")
    lines.extend(["", "## Checks", ""])
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
            f"- Candidate only: {report.candidate_only}",
            f"- Synthetic only: {report.synthetic_only}",
            f"- Local JSON only: {report.local_json_only}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Budget amount output authorized: {report.budget_amount_output_authorized}",
            f"- Matter opening authorized: {report.matter_opening_authorized}",
            f"- Conflict conclusion emitted: {report.conflict_conclusion_emitted}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report records local append-only matter-linking review evidence only. It does not call Upfront, create a screen, clear conflicts, output or submit a budget, open a matter, admit Lake/SQLite records, write sibling repos, promote canon, or learn from reviewer corrections.",
            "",
        ]
    )
    return "\n".join(lines)


def run_matter_linking_review_outcome_record(
    *,
    matter_linking_preflight_report_path: str | Path,
    outcome_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkingReviewOutcomeReport, Path]:
    preflight_path = Path(matter_linking_preflight_report_path)
    outcome_record_path = Path(outcome_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    preflight_report = MatterLinkingPreflightReport.model_validate(load_json(preflight_path))
    outcome_record = MatterLinkingReviewOutcomeRecord.model_validate(load_json(outcome_record_path))
    history_path = run_dir / MATTER_LINKING_REVIEW_OUTCOME_HISTORY_FILENAME
    report = build_matter_linking_review_outcome_report(
        matter_linking_preflight_report=preflight_report,
        matter_linking_preflight_report_ref=str(preflight_path),
        outcome_record=outcome_record,
        history_ref=str(history_path),
        generated_at=generated_at,
    )
    write_json(
        run_dir / MATTER_LINKING_REVIEW_OUTCOME_RECORD_FILENAME,
        outcome_record.model_dump(mode="json"),
    )
    append_jsonl(history_path, outcome_record.model_dump(mode="json"))
    write_json(
        run_dir / MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / MATTER_LINKING_REVIEW_OUTCOME_NOTES_FILENAME).write_text(
        render_matter_linking_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir
