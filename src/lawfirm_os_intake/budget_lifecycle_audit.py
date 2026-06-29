from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetActualVarianceLedgerReport,
    BudgetChangeLedgerReport,
    BudgetLakeAdmissionBundleReport,
    BudgetLifecycleAuditCheck,
    BudgetLifecycleAuditReport,
    BudgetLifecycleFinancialSummary,
    CarrierRejectionDecisionLedgerReport,
)
from .util import digest_text, load_json, now_iso, write_json


BUDGET_LIFECYCLE_AUDIT_REPORT_FILENAME = "budget_lifecycle_audit_report.json"
BUDGET_LIFECYCLE_AUDIT_NOTES_FILENAME = "budget_lifecycle_audit_report.md"

BUDGET_LIFECYCLE_AUDIT_REQUIRED_NEXT_GATES = [
    "human_budget_lifecycle_review",
    "orchestrator_evidence_packet_assembly",
    "exception_lake_runtime_admission_validation",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_budget_or_guideline_mutation",
]

PROHIBITED_FALSE_FLAGS = {
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
    "billing_connector_read_performed",
    "billing_connector_write_performed",
    "carrier_portal_write_performed",
    "email_send_performed",
    "appeal_submission_performed",
    "budget_submission_authorized",
    "carrier_submission_authorized",
    "budget_submission_performed",
    "budget_mutation_performed",
    "profile_mutation_performed",
    "template_mutation_performed",
    "carrier_guideline_mutation_performed",
    "silent_learning_performed",
    "raw_payload_included",
}

REQUIRED_TRUE_FLAGS = {
    "candidate_only",
    "non_authoritative",
    "synthetic_only",
    "append_only",
}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _check(
    check_id: str,
    passed: bool,
    message: str,
    artifact_refs: list[str] | None = None,
) -> BudgetLifecycleAuditCheck:
    return BudgetLifecycleAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
    )


def _warning(
    check_id: str,
    message: str,
    artifact_refs: list[str] | None = None,
) -> BudgetLifecycleAuditCheck:
    return BudgetLifecycleAuditCheck(
        check_id=check_id,
        status="warning",
        message=message,
        artifact_refs=artifact_refs or [],
    )


def _load_report(
    *,
    path: str | Path,
    model: type,
    missing_refs: list[str],
) -> tuple[Any | None, dict[str, Any] | None, Path]:
    report_path = Path(path)
    if not report_path.exists():
        missing_refs.append(str(report_path))
        return None, None, report_path
    payload = load_json(report_path)
    return model.model_validate(payload), payload, report_path


def _sorted_unique(values: list[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def _flag_violations(payload: dict[str, Any], *, ref: str) -> list[str]:
    violations: list[str] = []
    to_scan = [payload, *payload.get("events", [])]
    for item in to_scan:
        for field in PROHIBITED_FALSE_FLAGS:
            if field in item and item[field] is not False:
                violations.append(f"{ref}:{field}={item[field]}")
        for field in REQUIRED_TRUE_FLAGS:
            if field in item and item[field] is not True:
                violations.append(f"{ref}:{field}={item[field]}")
    return sorted(set(violations))


def _financial_summary(
    *,
    budget_change: BudgetChangeLedgerReport | None,
    actuals: BudgetActualVarianceLedgerReport | None,
    carrier: CarrierRejectionDecisionLedgerReport | None,
) -> BudgetLifecycleFinancialSummary:
    first_budget_event = budget_change.events[0] if budget_change and budget_change.events else None
    last_budget_event = budget_change.events[-1] if budget_change and budget_change.events else None
    return BudgetLifecycleFinancialSummary(
        original_budget_total=(
            _money(first_budget_event.budget_total_before_event) if first_budget_event else None
        ),
        human_revision_total_delta=_money(budget_change.total_delta) if budget_change else None,
        human_revised_candidate_total=(
            _money(last_budget_event.budget_total_after_event) if last_budget_event else None
        ),
        actual_comparison_budgeted_total=_money(actuals.total_budgeted) if actuals else None,
        actual_total=_money(actuals.total_actual) if actuals else None,
        actual_variance_amount=_money(actuals.total_variance_amount) if actuals else None,
        carrier_disputed_amount=_money(carrier.total_disputed_amount) if carrier else 0,
        carrier_recovered_amount=_money(carrier.total_recovered_amount) if carrier else 0,
        carrier_write_down_amount=_money(carrier.total_write_down_amount) if carrier else 0,
    )


def _required_human_decisions(
    *,
    actuals: BudgetActualVarianceLedgerReport | None,
    carrier: CarrierRejectionDecisionLedgerReport | None,
) -> list[str]:
    decisions: list[str] = []
    if actuals:
        for event in actuals.events:
            if event.requires_human_review:
                decisions.extend(event.required_human_decisions)
    if carrier:
        for event in carrier.events:
            decisions.extend(event.required_human_decisions)
    return sorted(set(decisions))


def _proposed_next_actions(
    *,
    budget_change: BudgetChangeLedgerReport | None,
    actuals: BudgetActualVarianceLedgerReport | None,
    carrier: CarrierRejectionDecisionLedgerReport | None,
) -> list[str]:
    actions: list[str] = []
    if budget_change and budget_change.entry_count:
        actions.append("review_append_only_human_budget_change_events")
    if actuals:
        for event in actuals.events:
            actions.extend(event.proposed_next_actions)
    if carrier:
        for event in carrier.events:
            actions.extend(event.proposed_next_actions)
    return sorted(set(actions))


def build_budget_lifecycle_audit_report(
    *,
    budget_change_ledger_report_path: str | Path,
    budget_actual_variance_ledger_report_path: str | Path,
    carrier_rejection_decision_ledger_report_path: str | Path,
    budget_event_lake_bundle_report_path: str | Path,
) -> BudgetLifecycleAuditReport:
    missing_refs: list[str] = []
    flag_violations: list[str] = []
    budget_change, budget_change_payload, budget_change_path = _load_report(
        path=budget_change_ledger_report_path,
        model=BudgetChangeLedgerReport,
        missing_refs=missing_refs,
    )
    actuals, actuals_payload, actuals_path = _load_report(
        path=budget_actual_variance_ledger_report_path,
        model=BudgetActualVarianceLedgerReport,
        missing_refs=missing_refs,
    )
    carrier, carrier_payload, carrier_path = _load_report(
        path=carrier_rejection_decision_ledger_report_path,
        model=CarrierRejectionDecisionLedgerReport,
        missing_refs=missing_refs,
    )
    lake_bundle, lake_payload, lake_path = _load_report(
        path=budget_event_lake_bundle_report_path,
        model=BudgetLakeAdmissionBundleReport,
        missing_refs=missing_refs,
    )

    for payload, path in [
        (budget_change_payload, budget_change_path),
        (actuals_payload, actuals_path),
        (carrier_payload, carrier_path),
        (lake_payload, lake_path),
    ]:
        if payload is not None:
            flag_violations.extend(_flag_violations(payload, ref=str(path)))

    budget_ids = _sorted_unique(
        [
            budget_change.budget_proposal_id if budget_change else None,
            actuals.budget_proposal_id if actuals else None,
            carrier.budget_proposal_id if carrier else None,
            *(lake_bundle.budget_proposal_ids if lake_bundle else []),
        ]
    )
    preflight_ids = _sorted_unique(
        [
            budget_change.preflight_packet_id if budget_change else None,
            actuals.preflight_packet_id if actuals else None,
            carrier.preflight_packet_id if carrier else None,
            *(lake_bundle.preflight_packet_ids if lake_bundle else []),
        ]
    )
    run_ids = _sorted_unique(
        [
            budget_change.run_id if budget_change else None,
            actuals.run_id if actuals else None,
            carrier.run_id if carrier else None,
            *(lake_bundle.run_ids if lake_bundle else []),
        ]
    )
    candidate_families = sorted(set(lake_bundle.candidate_record_families if lake_bundle else []))
    local_labels = sorted(set(lake_bundle.local_event_labels if lake_bundle else []))
    required_family_groups = [
        {"budget_human_change_record"},
        {"budget_actual_variance_record", "budget_actual_missing_source_record"},
        {
            "carrier_rejection_decision_record",
            "carrier_appeal_result_record",
            "carrier_financial_outcome_record",
        },
    ]
    lake_covers_required_family_groups = all(
        bool(set(candidate_families) & group) for group in required_family_groups
    )
    stream_events_present = (
        bool(budget_change and budget_change.entry_count)
        and bool(actuals and actuals.entry_count)
        and bool(carrier and carrier.entry_count)
    )
    lake_ready = bool(lake_bundle and lake_bundle.status == "ready_for_exception_lake_review")
    checks = [
        _check(
            "lifecycle_artifacts_exist",
            not missing_refs,
            "All declared budget lifecycle ledger and Lake-bundle artifacts exist.",
            missing_refs,
        ),
        _check(
            "all_lifecycle_streams_have_events",
            stream_events_present,
            "Budget change, actual variance, and carrier rejection streams each have append-only events.",
            [
                str(budget_change_path),
                str(actuals_path),
                str(carrier_path),
            ],
        ),
        _check(
            "budget_proposal_id_consistent",
            len(budget_ids) == 1,
            "All lifecycle streams refer to the same budget proposal.",
            budget_ids,
        ),
        _check(
            "preflight_packet_id_consistent",
            len(preflight_ids) == 1,
            "All lifecycle streams refer to the same preflight packet.",
            preflight_ids,
        ),
        _check(
            "budget_event_lake_bundle_ready",
            lake_ready,
            "Budget-event Lake bundle is ready for Exception Lake owner review only.",
            [str(lake_path)],
        ),
        _check(
            "budget_event_lake_bundle_covers_lifecycle_families",
            lake_covers_required_family_groups,
            "Lake bundle includes candidate record families for human changes, actual variance, and carrier decisions.",
            candidate_families,
        ),
        _check(
            "no_prohibited_writes_or_silent_learning",
            not flag_violations,
            "Lifecycle artifacts preserve no-write, no-submission, no-mutation, and no-silent-learning boundaries.",
            flag_violations,
        ),
    ]
    required_decisions = _required_human_decisions(actuals=actuals, carrier=carrier)
    if required_decisions:
        checks.append(
            _warning(
                "pending_human_decisions_captured",
                "Lifecycle audit captured pending human decisions for review; this does not block local evidence readiness.",
                required_decisions,
            )
        )
    failed_count = sum(1 for check in checks if check.status == "failed")
    if missing_refs:
        status = "blocked_missing_lifecycle_artifacts"
    elif failed_count:
        status = "blocked_inconsistent_lifecycle_evidence"
    else:
        status = "ready_for_budget_lifecycle_review"
    return BudgetLifecycleAuditReport(
        lifecycle_audit_report_id=_stable_id(
            "budgetlifecycleaudit",
            "|".join(
                [
                    str(budget_change_path),
                    str(actuals_path),
                    str(carrier_path),
                    str(lake_path),
                    "|".join(budget_ids),
                    "|".join(preflight_ids),
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        budget_proposal_id=budget_ids[0] if len(budget_ids) == 1 else None,
        preflight_packet_id=preflight_ids[0] if len(preflight_ids) == 1 else None,
        run_ids=run_ids,
        source_budget_change_ledger_report_ref=str(budget_change_path),
        source_budget_actual_variance_ledger_report_ref=str(actuals_path),
        source_carrier_rejection_decision_ledger_report_ref=str(carrier_path),
        source_budget_event_lake_bundle_report_ref=str(lake_path),
        budget_change_ledger_report_id=(
            budget_change.budget_change_ledger_report_id if budget_change else None
        ),
        budget_actual_variance_ledger_report_id=(
            actuals.budget_actual_variance_ledger_report_id if actuals else None
        ),
        carrier_rejection_decision_ledger_report_id=(
            carrier.decision_ledger_report_id if carrier else None
        ),
        budget_event_lake_bundle_report_id=lake_bundle.bundle_report_id if lake_bundle else None,
        budget_change_event_count=budget_change.entry_count if budget_change else 0,
        actual_variance_event_count=actuals.entry_count if actuals else 0,
        carrier_rejection_event_count=carrier.entry_count if carrier else 0,
        total_lifecycle_event_count=(
            (budget_change.entry_count if budget_change else 0)
            + (actuals.entry_count if actuals else 0)
            + (carrier.entry_count if carrier else 0)
        ),
        human_budget_change_event_count=(
            budget_change.event_kind_counts.get("human_budget_change_recorded", 0)
            if budget_change
            else 0
        ),
        actual_variance_review_event_count=actuals.variance_review_event_count if actuals else 0,
        carrier_pending_decision_event_count=carrier.pending_decision_event_count if carrier else 0,
        carrier_appeal_result_event_count=carrier.appeal_result_event_count if carrier else 0,
        carrier_financial_outcome_event_count=carrier.financial_outcome_event_count
        if carrier
        else 0,
        pending_human_decision_count=len(required_decisions),
        required_human_decisions=required_decisions,
        proposed_next_actions=_proposed_next_actions(
            budget_change=budget_change,
            actuals=actuals,
            carrier=carrier,
        ),
        candidate_record_families=candidate_families,
        local_event_labels=local_labels,
        financial_summary=_financial_summary(
            budget_change=budget_change,
            actuals=actuals,
            carrier=carrier,
        ),
        checks=checks,
        required_next_gates=BUDGET_LIFECYCLE_AUDIT_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_lifecycle_audit_report(report: BudgetLifecycleAuditReport) -> str:
    summary = report.financial_summary
    lines = [
        "# Budget Lifecycle Audit Report",
        "",
        f"**Report ID:** {report.lifecycle_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Budget proposal:** {report.budget_proposal_id or 'inconsistent-or-missing'}",
        f"**Preflight packet:** {report.preflight_packet_id or 'inconsistent-or-missing'}",
        "",
        "## Source Artifacts",
        "",
        f"- Budget change ledger: `{report.source_budget_change_ledger_report_ref}`",
        f"- Actual variance ledger: `{report.source_budget_actual_variance_ledger_report_ref}`",
        f"- Carrier rejection decision ledger: `{report.source_carrier_rejection_decision_ledger_report_ref}`",
        f"- Budget-event Lake bundle: `{report.source_budget_event_lake_bundle_report_ref}`",
        "",
        "## Financial Summary",
        "",
        f"- Original budget total: {summary.original_budget_total}",
        f"- Human revision total delta: {summary.human_revision_total_delta}",
        f"- Human-revised candidate total: {summary.human_revised_candidate_total}",
        f"- Actual comparison budgeted total: {summary.actual_comparison_budgeted_total}",
        f"- Actual total: {summary.actual_total}",
        f"- Actual variance amount: {summary.actual_variance_amount}",
        f"- Carrier disputed amount: {summary.carrier_disputed_amount}",
        f"- Carrier recovered amount: {summary.carrier_recovered_amount}",
        f"- Carrier write-down amount: {summary.carrier_write_down_amount}",
        "",
        "## Event Counts",
        "",
        f"- Budget change events: {report.budget_change_event_count}",
        f"- Actual variance events: {report.actual_variance_event_count}",
        f"- Carrier rejection events: {report.carrier_rejection_event_count}",
        f"- Total lifecycle events: {report.total_lifecycle_event_count}",
        f"- Pending human decisions: {report.pending_human_decision_count}",
        "",
        "## Pending Human Decisions",
        "",
    ]
    if report.required_human_decisions:
        lines.extend(f"- {decision}" for decision in report.required_human_decisions)
    else:
        lines.append("- none")
    lines.extend(["", "## Proposed Next Actions", ""])
    if report.proposed_next_actions:
        lines.extend(f"- {action}" for action in report.proposed_next_actions)
    else:
        lines.append("- none")
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
        if check.artifact_refs:
            lines.append(f"  - refs: {', '.join(check.artifact_refs)}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This audit is local candidate review evidence only. It does not admit Exception Lake records, write SQLite, submit appeals or budgets, read or write billing systems, mutate budgets or guidelines, write sibling repos, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_lifecycle_audit(
    *,
    budget_change_ledger_report_path: str | Path,
    budget_actual_variance_ledger_report_path: str | Path,
    carrier_rejection_decision_ledger_report_path: str | Path,
    budget_event_lake_bundle_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetLifecycleAuditReport, Path]:
    report = build_budget_lifecycle_audit_report(
        budget_change_ledger_report_path=budget_change_ledger_report_path,
        budget_actual_variance_ledger_report_path=budget_actual_variance_ledger_report_path,
        carrier_rejection_decision_ledger_report_path=(
            carrier_rejection_decision_ledger_report_path
        ),
        budget_event_lake_bundle_report_path=budget_event_lake_bundle_report_path,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / BUDGET_LIFECYCLE_AUDIT_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_LIFECYCLE_AUDIT_NOTES_FILENAME).write_text(
        render_budget_lifecycle_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir
