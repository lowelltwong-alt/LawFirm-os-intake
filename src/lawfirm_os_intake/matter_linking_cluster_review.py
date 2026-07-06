from __future__ import annotations

from pathlib import Path

from .models import (
    MatterLinkingClusterReport,
    MatterLinkingClusterReviewDecision,
    MatterLinkingClusterReviewOutcomeCheck,
    MatterLinkingClusterReviewOutcomeRecord,
    MatterLinkingClusterReviewOutcomeReport,
)
from .util import append_jsonl, digest_json, load_json, now_iso, write_json


MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_RECORD_FILENAME = (
    "matter_linking_cluster_review_outcome_record.json"
)
MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_HISTORY_FILENAME = (
    "matter_linking_cluster_review_outcome_history.jsonl"
)
MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_REPORT_FILENAME = (
    "matter_linking_cluster_review_outcome_report.json"
)
MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_NOTES_FILENAME = (
    "matter_linking_cluster_review_outcome_report.md"
)

BASE_REQUIRED_NEXT_GATES = [
    "append_only_matter_linking_cluster_review_outcome",
    "exception_lake_owner_review_before_admission",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_intake",
    "no_silent_learning_from_matter_linking_cluster_review",
]


def run_matter_linking_cluster_review_outcome_record(
    *,
    matter_linking_cluster_report_path: str | Path,
    outcome_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkingClusterReviewOutcomeReport, Path]:
    cluster_report_path = Path(matter_linking_cluster_report_path)
    outcome_record_path = Path(outcome_path)
    cluster_report = MatterLinkingClusterReport.model_validate(load_json(cluster_report_path))
    outcome_record = MatterLinkingClusterReviewOutcomeRecord.model_validate(
        load_json(outcome_record_path)
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    record_path = run_dir / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_RECORD_FILENAME
    history_path = run_dir / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_HISTORY_FILENAME
    write_json(record_path, outcome_record.model_dump(mode="json"))
    append_jsonl(history_path, outcome_record.model_dump(mode="json"))
    report = build_matter_linking_cluster_review_outcome_report(
        matter_linking_cluster_report=cluster_report,
        matter_linking_cluster_report_ref=str(cluster_report_path),
        outcome_record=outcome_record,
        history_ref=str(history_path),
        generated_at=generated_at or now_iso(),
    )
    write_json(
        run_dir / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_NOTES_FILENAME).write_text(
        render_matter_linking_cluster_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def build_matter_linking_cluster_review_outcome_report(
    *,
    matter_linking_cluster_report: MatterLinkingClusterReport,
    matter_linking_cluster_report_ref: str,
    outcome_record: MatterLinkingClusterReviewOutcomeRecord,
    history_ref: str,
    generated_at: str | None = None,
) -> MatterLinkingClusterReviewOutcomeReport:
    known_cluster_ids = {cluster.cluster_id for cluster in matter_linking_cluster_report.clusters}
    selected_cluster_ids = _selected_cluster_ids(outcome_record.decisions)
    unknown_cluster_ids = sorted(set(selected_cluster_ids) - known_cluster_ids)
    unreviewed_cluster_ids = sorted(known_cluster_ids - set(selected_cluster_ids))
    budget_scope_cluster_ids = _budget_scope_cluster_ids(outcome_record.decisions)
    required_followups = _required_followups(outcome_record.decisions)
    clusters_by_id = {
        cluster.cluster_id: cluster for cluster in matter_linking_cluster_report.clusters
    }
    budget_blocking_cluster_ids = _budget_blocking_cluster_ids(
        budget_scope_cluster_ids=budget_scope_cluster_ids,
        clusters_by_id=clusters_by_id,
        unknown_cluster_ids=unknown_cluster_ids,
    )
    checks = _checks(
        matter_linking_cluster_report=matter_linking_cluster_report,
        matter_linking_cluster_report_ref=matter_linking_cluster_report_ref,
        outcome_record=outcome_record,
        selected_cluster_ids=selected_cluster_ids,
        unknown_cluster_ids=unknown_cluster_ids,
        unreviewed_cluster_ids=unreviewed_cluster_ids,
        budget_scope_cluster_ids=budget_scope_cluster_ids,
        budget_blocking_cluster_ids=budget_blocking_cluster_ids,
    )
    failed = [check for check in checks if check.status == "failed"]
    if failed:
        status = "blocked_by_matter_linking_cluster_review"
    elif (
        len(budget_scope_cluster_ids) == 1
        and not budget_blocking_cluster_ids
        and not unreviewed_cluster_ids
        and not unknown_cluster_ids
        and not required_followups
    ):
        status = "matter_linking_cluster_review_confirmed_for_budget_scope"
    else:
        status = "matter_linking_cluster_review_recorded_pending_followup"
    report_core = {
        "matter_linking_cluster_report_id": (
            matter_linking_cluster_report.matter_linking_cluster_report_id
        ),
        "outcome_record_id": outcome_record.matter_linking_cluster_review_outcome_record_id,
        "budget_scope_cluster_ids": budget_scope_cluster_ids,
        "unknown_cluster_ids": unknown_cluster_ids,
        "unreviewed_cluster_ids": unreviewed_cluster_ids,
        "status": status,
    }
    return MatterLinkingClusterReviewOutcomeReport(
        matter_linking_cluster_review_outcome_report_id="matterlinkclusterreview_"
        + digest_json(report_core).removeprefix("sha256:")[:20],
        status=status,  # type: ignore[arg-type]
        source_matter_linking_cluster_report_ref=matter_linking_cluster_report_ref,
        matter_linking_cluster_report_id=matter_linking_cluster_report.matter_linking_cluster_report_id,
        source_matter_linking_cluster_status=matter_linking_cluster_report.status,
        matter_linking_cluster_review_outcome_record_id=(
            outcome_record.matter_linking_cluster_review_outcome_record_id
        ),
        reviewer_id=outcome_record.reviewer_id,
        reviewed_at=outcome_record.reviewed_at,
        overall_outcome=outcome_record.overall_outcome,
        decision_reason=outcome_record.decision_reason,
        source_cluster_count=len(known_cluster_ids),
        decision_count=len(outcome_record.decisions),
        budget_scope_cluster_count=len(budget_scope_cluster_ids),
        reviewed_cluster_count=len(selected_cluster_ids),
        unreviewed_cluster_count=len(unreviewed_cluster_ids),
        unknown_cluster_count=len(unknown_cluster_ids),
        budget_blocking_cluster_count=len(budget_blocking_cluster_ids),
        budget_scope_cluster_ids=budget_scope_cluster_ids,
        reviewed_cluster_ids=selected_cluster_ids,
        unreviewed_cluster_ids=unreviewed_cluster_ids,
        unknown_cluster_ids=unknown_cluster_ids,
        budget_blocking_cluster_ids=budget_blocking_cluster_ids,
        required_followups=required_followups,
        candidate_lake_event_labels=_candidate_lake_event_labels(
            cluster_report=matter_linking_cluster_report,
            decisions=outcome_record.decisions,
            budget_blocking_cluster_ids=budget_blocking_cluster_ids,
            status=status,
        ),
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=_required_next_gates(
            status=status,
            required_followups=required_followups,
            unreviewed_cluster_ids=unreviewed_cluster_ids,
        ),
        generated_at=generated_at or now_iso(),
    )


def render_matter_linking_cluster_review_outcome_report(
    report: MatterLinkingClusterReviewOutcomeReport,
) -> str:
    failed = [check for check in report.checks if check.status == "failed"]
    lines = [
        "# Matter Linking Cluster Review Outcome",
        "",
        f"- Report ID: `{report.matter_linking_cluster_review_outcome_report_id}`",
        f"- Status: `{report.status}`",
        f"- Source cluster report: `{report.matter_linking_cluster_report_id}`",
        f"- Budget-scope clusters: `{', '.join(report.budget_scope_cluster_ids) or 'none'}`",
        f"- Unreviewed clusters: `{report.unreviewed_cluster_count}`",
        f"- Budget-blocking clusters: `{report.budget_blocking_cluster_count}`",
        f"- Failed checks: `{len(failed)}`",
        "- Boundary: append-only candidate review; no budget, matter, conflict, Lake, or SQLite action.",
    ]
    return "\n".join(lines) + "\n"


def _checks(
    *,
    matter_linking_cluster_report: MatterLinkingClusterReport,
    matter_linking_cluster_report_ref: str,
    outcome_record: MatterLinkingClusterReviewOutcomeRecord,
    selected_cluster_ids: list[str],
    unknown_cluster_ids: list[str],
    unreviewed_cluster_ids: list[str],
    budget_scope_cluster_ids: list[str],
    budget_blocking_cluster_ids: list[str],
) -> list[MatterLinkingClusterReviewOutcomeCheck]:
    return [
        _check(
            "matter_linking_cluster_report_ready_without_authority",
            _cluster_report_boundary_clear(matter_linking_cluster_report),
            "Source cluster report is reviewable and has no connector, Lake, SQLite, budget, matter-opening, conflict, or learning side effects.",
            artifact_refs=[matter_linking_cluster_report_ref],
        ),
        _check(
            "outcome_record_matches_cluster_report",
            outcome_record.matter_linking_cluster_report_id
            == matter_linking_cluster_report.matter_linking_cluster_report_id,
            "Outcome record is bound to the supplied matter-linking cluster report.",
            artifact_refs=[matter_linking_cluster_report_ref],
        ),
        _check(
            "outcome_record_preserves_no_write_boundary",
            _record_boundary_clear(outcome_record),
            "Cluster review outcome did not authorize budgets, matters, conflicts, Lake/SQLite records, external writes, or learning.",
        ),
        _check(
            "review_decisions_target_known_clusters",
            not unknown_cluster_ids,
            "Every selected cluster exists in the source matter-linking cluster report.",
            cluster_ids=unknown_cluster_ids,
            blocking_refs=unknown_cluster_ids,
        ),
        _check(
            "budget_scope_exactly_one_cluster",
            len(budget_scope_cluster_ids) == 1,
            "Budget-scope review must confirm exactly one cluster.",
            cluster_ids=budget_scope_cluster_ids,
            blocking_refs=budget_scope_cluster_ids,
        ),
        _check(
            "budget_scope_cluster_is_not_held_or_conflicted",
            not budget_blocking_cluster_ids,
            "Budget-scope cluster must be a proposed_link cluster with no held/conflicted disposition.",
            cluster_ids=budget_blocking_cluster_ids,
            blocking_refs=budget_blocking_cluster_ids,
        ),
        _check(
            "all_clusters_reviewed_before_budget_scope",
            not unreviewed_cluster_ids,
            "All cluster proposals must be reviewed before this bundle can be treated as one budget scope.",
            cluster_ids=unreviewed_cluster_ids,
            blocking_refs=unreviewed_cluster_ids,
        ),
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
) -> MatterLinkingClusterReviewOutcomeCheck:
    return MatterLinkingClusterReviewOutcomeCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        decision_ids=decision_ids or [],
        cluster_ids=cluster_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _cluster_report_boundary_clear(report: MatterLinkingClusterReport) -> bool:
    return (
        report.status == "matter_linking_clusters_proposed_for_review"
        and report.candidate_only is True
        and report.synthetic_only is True
        and report.non_authoritative is True
        and report.local_json_only is True
        and report.human_review_required is True
        and report.matter_identity_asserted is False
        and report.matter_link_finalized is False
        and report.budget_generation_performed is False
        and report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.matter_opening_authorized is False
        and report.connector_called is False
        and report.external_writes_performed is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.silent_learning_performed is False
    )


def _record_boundary_clear(record: MatterLinkingClusterReviewOutcomeRecord) -> bool:
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
        and record.no_connector_implemented is True
        and record.no_lake_admission_performed is True
        and record.no_sibling_repo_writes is True
        and record.no_canonical_mutation is True
        and record.budget_amount_output_authorized is False
        and record.budget_submission_authorized is False
        and record.conflict_conclusion_emitted is False
        and record.matter_opening_authorized is False
        and record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.silent_learning_performed is False
    )


def _selected_cluster_ids(decisions: list[MatterLinkingClusterReviewDecision]) -> list[str]:
    return sorted(
        {cluster_id for decision in decisions for cluster_id in decision.selected_cluster_ids}
    )


def _budget_scope_cluster_ids(
    decisions: list[MatterLinkingClusterReviewDecision],
) -> list[str]:
    return sorted(
        {
            cluster_id
            for decision in decisions
            if decision.outcome == "confirm_budget_scope_cluster"
            for cluster_id in decision.selected_cluster_ids
        }
    )


def _required_followups(decisions: list[MatterLinkingClusterReviewDecision]) -> list[str]:
    return [
        followup
        for decision in decisions
        for followup in decision.required_followups
        if followup.strip()
    ]


def _budget_blocking_cluster_ids(
    *,
    budget_scope_cluster_ids: list[str],
    clusters_by_id: dict[str, object],
    unknown_cluster_ids: list[str],
) -> list[str]:
    blocking = set(unknown_cluster_ids)
    for cluster_id in budget_scope_cluster_ids:
        cluster = clusters_by_id.get(cluster_id)
        if cluster is None:
            blocking.add(cluster_id)
            continue
        if (
            getattr(cluster, "disposition") != "proposed_link"
            or getattr(cluster, "ambiguity_class") == "conflicted"
        ):
            blocking.add(cluster_id)
    return sorted(blocking)


def _candidate_lake_event_labels(
    *,
    cluster_report: MatterLinkingClusterReport,
    decisions: list[MatterLinkingClusterReviewDecision],
    budget_blocking_cluster_ids: list[str],
    status: str,
) -> list[str]:
    labels = {
        "matter_linking_cluster_review_outcome_candidate",
        *cluster_report.candidate_exception_lake_labels,
    }
    outcomes = {decision.outcome for decision in decisions}
    if "confirm_budget_scope_cluster" in outcomes:
        labels.add("matter_linking_cluster_confirmed_budget_scope_candidate")
    if "confirm_split" in outcomes:
        labels.add("matter_linking_cluster_confirmed_split_candidate")
    if outcomes & {"unknown", "request_more_info", "declined_or_referred"}:
        labels.add("matter_linking_cluster_followup_required_candidate")
    if budget_blocking_cluster_ids or status == "blocked_by_matter_linking_cluster_review":
        labels.add("matter_linking_confirmation_blocked")
    return sorted(labels)


def _required_next_gates(
    *,
    status: str,
    required_followups: list[str],
    unreviewed_cluster_ids: list[str],
) -> list[str]:
    gates = set(BASE_REQUIRED_NEXT_GATES)
    if status != "matter_linking_cluster_review_confirmed_for_budget_scope":
        gates.add("split_bundle_and_build_preflight_per_confirmed_cluster_before_budget")
    if required_followups or unreviewed_cluster_ids:
        gates.add("complete_matter_linking_followup_before_budget_or_opening")
    return sorted(gates)
