from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetActualComparisonReport,
    BudgetActualVarianceLedgerReport,
    BudgetLearningLoopActualsSummary,
    BudgetLearningLoopCarrierRejectionSummary,
    BudgetLearningLoopLane,
    BudgetLearningLoopReport,
    BudgetLearningLoopReviewedGateSummary,
    CarrierRejectionDecisionLedgerReport,
    CarrierRejectionLearningReport,
    CarrierRejectionReviewPacket,
    CarrierResponseReconciliationReport,
    ReviewedLearningGateReport,
)
from .util import digest_json, load_json, now_iso, write_json


BUDGET_LEARNING_LOOP_REPORT_FILENAME = "budget_learning_loop_report.json"
BUDGET_LEARNING_LOOP_NOTES_FILENAME = "budget_learning_loop_report.md"


def _money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:,.0f}"


def _amount(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _load(path: str | Path, model: type):
    return model.model_validate(load_json(path))


def _stable_report_id(*, prefix: str, payload: dict[str, object]) -> str:
    digest = digest_json(payload).split(":", maxsplit=1)[1]
    return f"{prefix}_{digest[:20]}"


def _single(values: set[str], label: str) -> str:
    clean = {value for value in values if value}
    if len(clean) != 1:
        raise ValueError(f"budget learning loop requires one {label}; found {sorted(clean)}")
    return next(iter(clean))


def _validate_chain(
    *,
    actuals: BudgetActualComparisonReport,
    actual_ledger: BudgetActualVarianceLedgerReport,
    reconciliation: CarrierResponseReconciliationReport,
    carrier_ledger: CarrierRejectionDecisionLedgerReport,
    review_packet: CarrierRejectionReviewPacket,
    learning: CarrierRejectionLearningReport,
) -> tuple[str, str, str]:
    budget_id = _single(
        {
            actuals.budget_proposal_id,
            actual_ledger.budget_proposal_id,
            reconciliation.budget_proposal_id,
            carrier_ledger.budget_proposal_id,
            review_packet.budget_proposal_id,
            learning.budget_proposal_id,
        },
        "budget_proposal_id",
    )
    preflight_id = _single(
        {
            actuals.preflight_packet_id,
            actual_ledger.preflight_packet_id,
            reconciliation.preflight_packet_id,
            carrier_ledger.preflight_packet_id,
            review_packet.preflight_packet_id,
            learning.preflight_packet_id,
        },
        "preflight_packet_id",
    )
    if (
        actuals.budget_actual_comparison_report_id
        != actual_ledger.budget_actual_comparison_report_id
    ):
        raise ValueError("budget learning loop actual comparison and ledger IDs do not match")
    if actuals.run_id != actual_ledger.run_id:
        raise ValueError("budget learning loop actual comparison and ledger run IDs do not match")
    if reconciliation.reconciliation_report_id != carrier_ledger.reconciliation_report_id:
        raise ValueError("budget learning loop carrier reconciliation and ledger IDs do not match")
    if reconciliation.reconciliation_report_id != review_packet.reconciliation_report_id:
        raise ValueError("budget learning loop review packet is not bound to reconciliation report")
    if review_packet.review_packet_id != learning.review_packet_id:
        raise ValueError("budget learning loop learning report is not bound to review packet")
    carrier_run_ids = {
        reconciliation.run_id,
        carrier_ledger.run_id,
        review_packet.run_id,
        learning.run_id,
    }
    if len(carrier_run_ids) != 1:
        raise ValueError(
            "budget learning loop carrier rejection run IDs do not match: "
            f"{sorted(carrier_run_ids)}"
        )
    run_id = _stable_report_id(
        prefix="budgetlearninglooprun",
        payload={
            "budget_proposal_id": budget_id,
            "preflight_packet_id": preflight_id,
            "source_run_ids": sorted({actuals.run_id, *carrier_run_ids}),
        },
    )
    return run_id, preflight_id, budget_id


def _actuals_summary(
    *,
    actuals: BudgetActualComparisonReport,
    actual_ledger: BudgetActualVarianceLedgerReport,
) -> BudgetLearningLoopActualsSummary:
    return BudgetLearningLoopActualsSummary(
        status=actuals.status,
        comparison_scope=actual_ledger.comparison_scope,
        total_budgeted=_amount(actual_ledger.total_budgeted),
        total_actual=_amount(actual_ledger.total_actual),
        total_variance_amount=_amount(actual_ledger.total_variance_amount),
        total_variance_percent=_amount(actual_ledger.total_variance_percent),
        phase_event_count=actual_ledger.phase_event_count,
        code_event_count=actual_ledger.code_event_count,
        revision_context_event_count=actual_ledger.revision_context_event_count,
        variance_review_event_count=actual_ledger.variance_review_event_count,
        actuals_without_budget_event_count=actual_ledger.actuals_without_budget_event_count,
        missing_actuals_event_count=actual_ledger.missing_actuals_event_count,
        ledger_entry_count=actual_ledger.entry_count,
        learning_disposition_candidates=sorted(set(actuals.learning_disposition_candidates)),
    )


def _carrier_summary(
    *,
    reconciliation: CarrierResponseReconciliationReport,
    carrier_ledger: CarrierRejectionDecisionLedgerReport,
) -> BudgetLearningLoopCarrierRejectionSummary:
    return BudgetLearningLoopCarrierRejectionSummary(
        reconciliation_status=reconciliation.status,
        decision_ledger_status=carrier_ledger.status,
        expected_response_count=reconciliation.expected_response_count,
        reconciled_response_count=reconciliation.reconciled_response_count,
        missing_response_count=reconciliation.missing_response_count,
        unlinked_notice_count=reconciliation.unlinked_notice_count,
        duplicate_notice_count=reconciliation.duplicate_notice_count,
        parser_failure_count=reconciliation.parser_failure_count,
        appeal_result_count=reconciliation.appeal_result_count,
        remediation_case_count=len(reconciliation.remediation_cases),
        decision_ledger_entry_count=carrier_ledger.entry_count,
        pending_decision_event_count=carrier_ledger.pending_decision_event_count,
        total_disputed_amount=_amount(carrier_ledger.total_disputed_amount) or 0,
        total_recovered_amount=_amount(carrier_ledger.total_recovered_amount) or 0,
        total_write_down_amount=_amount(carrier_ledger.total_write_down_amount) or 0,
        candidate_event_labels=sorted(
            {case.local_event_label for case in reconciliation.remediation_cases}
        ),
    )


def _learning_summary(
    gate: ReviewedLearningGateReport,
) -> BudgetLearningLoopReviewedGateSummary:
    return BudgetLearningLoopReviewedGateSummary(
        status=gate.status,
        candidate_count=gate.candidate_count,
        carrier_learning_candidate_count=gate.carrier_learning_candidate_count,
        budget_revision_candidate_count=gate.budget_revision_candidate_count,
        budget_actual_variance_candidate_count=gate.budget_actual_variance_candidate_count,
        target_learning_loops=gate.target_learning_loops,
        target_owners=gate.target_owners,
        reviewed_outcome_required=gate.reviewed_outcome_required,
        shadow_eval_required=gate.shadow_eval_required,
    )


def _actuals_lane(actuals: BudgetLearningLoopActualsSummary) -> BudgetLearningLoopLane:
    state = "pending" if actuals.variance_review_event_count else "passed"
    labels = ["budget_actual_cost_variance_requires_review"]
    if actuals.actuals_without_budget_event_count:
        labels.append("budget_actual_without_budget_recorded")
    if actuals.missing_actuals_event_count:
        labels.append("budget_actual_missing_actuals_recorded")
    return BudgetLearningLoopLane(
        lane_id="actuals_variance_review",
        label="Actuals Variance",
        state=state,  # type: ignore[arg-type]
        metric=f"{actuals.variance_review_event_count} review events",
        why=(
            "Synthetic actuals are compared against the selected candidate budget state; "
            "overall variance does not suppress code-level or missing-actual review signals."
        ),
        next_action=(
            "Review budget-driver and template-mapping candidates before calibration, "
            "fixture update, or budget-model changes."
        ),
        evidence_refs=[
            "budget_actual_comparison_report.json",
            "budget_actual_variance_ledger_report.json",
        ],
        candidate_exception_lake_labels=labels,
    )


def _carrier_lane(carrier: BudgetLearningLoopCarrierRejectionSummary) -> BudgetLearningLoopLane:
    state = "pending" if carrier.remediation_case_count else "passed"
    labels = carrier.candidate_event_labels or ["carrier_rejection_no_cases_to_review"]
    return BudgetLearningLoopLane(
        lane_id="carrier_rejection_capture",
        label="Carrier Rejections",
        state=state,  # type: ignore[arg-type]
        metric=f"{_money(carrier.total_disputed_amount)} disputed",
        why=(
            "Carrier response evidence is reconciled for duplicates, missing responses, "
            "unlinked notices, parser failures, and appeal results without submitting anything."
        ),
        next_action=(
            "Use the review packet to decide fix versus appeal steps and keep all outcomes "
            "append-only."
        ),
        evidence_refs=[
            "carrier_rejection_reconciliation_report.json",
            "carrier_rejection_decision_ledger_report.json",
        ],
        candidate_exception_lake_labels=labels,
    )


def _appeal_lane(carrier: BudgetLearningLoopCarrierRejectionSummary) -> BudgetLearningLoopLane:
    state = "pending" if carrier.appeal_result_count else "passed"
    return BudgetLearningLoopLane(
        lane_id="appeal_financial_outcome",
        label="Appeal Outcome",
        state=state,  # type: ignore[arg-type]
        metric=f"{_money(carrier.total_recovered_amount)} recovered",
        why=(
            "Appeal result evidence is captured as financial outcome telemetry, not as a "
            "silent guideline, template, or rate update."
        ),
        next_action=(
            "Require reviewed outcome evidence and shadow eval before using recovered or "
            "write-down signals to change assumptions."
        ),
        evidence_refs=[
            "carrier_rejection_decision_ledger_report.json",
            "carrier_rejection_learning_report.json",
        ],
        candidate_exception_lake_labels=[
            "carrier_appeal_result_received"
            if carrier.appeal_result_count
            else "carrier_appeal_result_not_present",
            "carrier_rejection_learning_candidate",
        ],
    )


def _learning_lane(gate: BudgetLearningLoopReviewedGateSummary) -> BudgetLearningLoopLane:
    state = "pending" if gate.candidate_count else "passed"
    return BudgetLearningLoopLane(
        lane_id="reviewed_learning_gate",
        label="Reviewed Learning Gate",
        state=state,  # type: ignore[arg-type]
        metric=f"{gate.candidate_count} candidates",
        why=(
            "Budget revisions, actual variance, and carrier rejection learning pressure are "
            "aggregated but blocked from profile, template, guideline, or connector mutation."
        ),
        next_action=(
            "Send only reviewed, shadow-evaluated proposed changes to owner repos; do not "
            "silently learn from this run."
        ),
        evidence_refs=["reviewed_learning_gate_report.json"],
        candidate_exception_lake_labels=[
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_required",
        ],
    )


def build_budget_learning_loop_report(
    *,
    budget_actual_comparison_report_path: str | Path,
    budget_actual_variance_ledger_report_path: str | Path,
    carrier_rejection_reconciliation_report_path: str | Path,
    carrier_rejection_decision_ledger_report_path: str | Path,
    carrier_rejection_review_packet_path: str | Path,
    carrier_rejection_learning_report_path: str | Path,
    reviewed_learning_gate_report_path: str | Path,
    generated_at: str | None = None,
) -> BudgetLearningLoopReport:
    actuals = _load(budget_actual_comparison_report_path, BudgetActualComparisonReport)
    actual_ledger = _load(
        budget_actual_variance_ledger_report_path,
        BudgetActualVarianceLedgerReport,
    )
    reconciliation = _load(
        carrier_rejection_reconciliation_report_path,
        CarrierResponseReconciliationReport,
    )
    carrier_ledger = _load(
        carrier_rejection_decision_ledger_report_path,
        CarrierRejectionDecisionLedgerReport,
    )
    review_packet = _load(carrier_rejection_review_packet_path, CarrierRejectionReviewPacket)
    learning = _load(carrier_rejection_learning_report_path, CarrierRejectionLearningReport)
    learning_gate = _load(reviewed_learning_gate_report_path, ReviewedLearningGateReport)

    run_id, preflight_id, budget_id = _validate_chain(
        actuals=actuals,
        actual_ledger=actual_ledger,
        reconciliation=reconciliation,
        carrier_ledger=carrier_ledger,
        review_packet=review_packet,
        learning=learning,
    )
    actuals_summary = _actuals_summary(actuals=actuals, actual_ledger=actual_ledger)
    carrier_summary = _carrier_summary(
        reconciliation=reconciliation,
        carrier_ledger=carrier_ledger,
    )
    learning_summary = _learning_summary(learning_gate)
    lanes = [
        _actuals_lane(actuals_summary),
        _carrier_lane(carrier_summary),
        _appeal_lane(carrier_summary),
        _learning_lane(learning_summary),
    ]
    source_refs = {
        "source_budget_actual_comparison_report_ref": str(budget_actual_comparison_report_path),
        "source_budget_actual_variance_ledger_report_ref": str(
            budget_actual_variance_ledger_report_path
        ),
        "source_carrier_rejection_reconciliation_report_ref": str(
            carrier_rejection_reconciliation_report_path
        ),
        "source_carrier_rejection_decision_ledger_report_ref": str(
            carrier_rejection_decision_ledger_report_path
        ),
        "source_carrier_rejection_review_packet_ref": str(carrier_rejection_review_packet_path),
        "source_carrier_rejection_learning_report_ref": str(carrier_rejection_learning_report_path),
        "source_reviewed_learning_gate_report_ref": str(reviewed_learning_gate_report_path),
    }
    identity = {
        "run_id": run_id,
        "preflight_packet_id": preflight_id,
        "budget_proposal_id": budget_id,
        **source_refs,
        "actuals_status": actuals_summary.status,
        "carrier_status": carrier_summary.reconciliation_status,
        "learning_status": learning_summary.status,
    }
    return BudgetLearningLoopReport(
        budget_learning_loop_report_id=_stable_report_id(
            prefix="budgetlearningloop",
            payload=identity,
        ),
        status=(
            "budget_learning_loop_ready_for_review"
            if learning_summary.status != "failed"
            else "blocked_by_budget_learning_loop"
        ),
        run_id=run_id,
        preflight_packet_id=preflight_id,
        budget_proposal_id=budget_id,
        comparison_budget_state=actuals.comparison_budget_state,
        actuals=actuals_summary,
        carrier_rejections=carrier_summary,
        reviewed_learning_gate=learning_summary,
        lifecycle_lanes=lanes,
        red_team_notes=[
            "This report is a compact projection of generated synthetic artifacts; it is not a ledger, Lake write, billing connector, appeal submission, or production learning signal.",
            "Negative total variance does not mean the budget model is accepted; code-level over-threshold and actuals-without-budget events still require review.",
            "Recovered appeal amounts are outcome evidence only and cannot update rates, guidelines, templates, or profiles without reviewed outcome evidence and shadow evaluation.",
        ],
        required_next_actions=[
            "Add L&E-specific actuals and carrier rejection fixtures after this medmal synthetic loop is visible.",
            "Add state/rate benchmark replay only from pinned candidate benchmark cells.",
            "Keep all learning candidates blocked until reviewed-learning and owner-adoption gates are satisfied.",
        ],
        generated_at=generated_at or now_iso(),
        **source_refs,
    )


def render_budget_learning_loop_report(report: BudgetLearningLoopReport) -> str:
    lane_lines = [
        f"- {lane.label}: {lane.metric}; state={lane.state}; next={lane.next_action}"
        for lane in report.lifecycle_lanes
    ]
    return "\n".join(
        [
            "# Budget Learning Loop Report",
            "",
            f"**Report ID:** {report.budget_learning_loop_report_id}",
            f"**Status:** {report.status}",
            f"**Budget proposal:** {report.budget_proposal_id}",
            f"**Comparison state:** {report.comparison_budget_state}",
            "",
            "## Actuals",
            "",
            f"- Budgeted: {_money(report.actuals.total_budgeted)}",
            f"- Actual: {_money(report.actuals.total_actual)}",
            f"- Variance: {_money(report.actuals.total_variance_amount)} ({report.actuals.total_variance_percent}%)",
            f"- Review events: {report.actuals.variance_review_event_count}",
            "",
            "## Carrier Rejections",
            "",
            f"- Disputed: {_money(report.carrier_rejections.total_disputed_amount)}",
            f"- Recovered: {_money(report.carrier_rejections.total_recovered_amount)}",
            f"- Write-down: {_money(report.carrier_rejections.total_write_down_amount)}",
            f"- Pending decision events: {report.carrier_rejections.pending_decision_event_count}",
            "",
            "## Learning Gate",
            "",
            f"- Candidates: {report.reviewed_learning_gate.candidate_count}",
            f"- Target loops: {', '.join(report.reviewed_learning_gate.target_learning_loops)}",
            "- Reviewed outcome required: True",
            "- Shadow eval required: True",
            "",
            "## Lanes",
            "",
            *lane_lines,
            "",
            "## Red Team Notes",
            "",
            *[f"- {note}" for note in report.red_team_notes],
            "",
            "## Boundaries",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- Synthetic only: {report.synthetic_only}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- Appeal submission performed: {report.appeal_submission_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
        ]
    )


def run_budget_learning_loop_report(
    *,
    budget_actual_comparison_report_path: str | Path,
    budget_actual_variance_ledger_report_path: str | Path,
    carrier_rejection_reconciliation_report_path: str | Path,
    carrier_rejection_decision_ledger_report_path: str | Path,
    carrier_rejection_review_packet_path: str | Path,
    carrier_rejection_learning_report_path: str | Path,
    reviewed_learning_gate_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[BudgetLearningLoopReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_budget_learning_loop_report(
        budget_actual_comparison_report_path=budget_actual_comparison_report_path,
        budget_actual_variance_ledger_report_path=budget_actual_variance_ledger_report_path,
        carrier_rejection_reconciliation_report_path=carrier_rejection_reconciliation_report_path,
        carrier_rejection_decision_ledger_report_path=carrier_rejection_decision_ledger_report_path,
        carrier_rejection_review_packet_path=carrier_rejection_review_packet_path,
        carrier_rejection_learning_report_path=carrier_rejection_learning_report_path,
        reviewed_learning_gate_report_path=reviewed_learning_gate_report_path,
        generated_at=generated_at,
    )
    write_json(run_dir / BUDGET_LEARNING_LOOP_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / BUDGET_LEARNING_LOOP_NOTES_FILENAME).write_text(
        render_budget_learning_loop_report(report),
        encoding="utf-8",
    )
    return report, run_dir
