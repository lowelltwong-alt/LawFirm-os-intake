from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetCodeBudgetSnapshot,
    BudgetLine,
    BudgetPhaseBudgetSnapshot,
    BudgetProposal,
    BudgetReviewChange,
    BudgetReviewChangeRecord,
    BudgetRevisionDelta,
    BudgetRevisionReport,
    ExceptionLakeCandidate,
)
from .util import append_jsonl, load_json, new_id, now_iso, write_json


BUDGET_REVIEW_CHANGE_RECORD_FILENAME = "budget_review_change_record.json"
BUDGET_REVISION_REPORT_FILENAME = "budget_revision_report.json"
BUDGET_REVISION_HISTORY_FILENAME = "budget_revision_history.jsonl"
BUDGET_REVISION_EXCEPTION_CANDIDATES_FILENAME = "budget_revision_exception_lake_candidates.jsonl"
BUDGET_REVISION_NOTES_FILENAME = "budget_revision_report.md"


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _line_total(line: BudgetLine) -> float:
    return round(float(line.estimated_fees or 0.0) + float(line.estimated_expenses or 0.0), 2)


def _phase_snapshots_from_lines(lines: list[BudgetLine]) -> list[BudgetPhaseBudgetSnapshot]:
    rows: dict[str, dict[str, Any]] = {}
    for line in lines:
        row = rows.setdefault(line.phase_id, {"fees": 0.0, "expenses": 0.0, "codes": set()})
        row["fees"] += float(line.estimated_fees or 0.0)
        row["expenses"] += float(line.estimated_expenses or 0.0)
        if line.external_code_candidate:
            row["codes"].add(line.external_code_candidate)
        if line.expense_code:
            row["codes"].add(line.expense_code)
    return [
        BudgetPhaseBudgetSnapshot(
            phase_id=phase_id,
            budgeted_fees=_money(row["fees"]),
            budgeted_expenses=round(row["expenses"], 2),
            budgeted_total=round(row["fees"] + row["expenses"], 2),
            external_code_candidates=sorted(row["codes"]),
        )
        for phase_id, row in sorted(rows.items())
    ]


def _code_snapshots_from_lines(lines: list[BudgetLine]) -> list[BudgetCodeBudgetSnapshot]:
    rows: dict[str, dict[str, Any]] = {}
    for line in lines:
        if line.external_code_candidate:
            fee_row = rows.setdefault(
                line.external_code_candidate,
                {"fees": 0.0, "expenses": 0.0, "phase_ids": set()},
            )
            fee_row["fees"] += float(line.estimated_fees or 0.0)
            fee_row["phase_ids"].add(line.phase_id)
        expense_code = line.expense_code or line.external_code_candidate
        if expense_code:
            expense_row = rows.setdefault(
                expense_code,
                {"fees": 0.0, "expenses": 0.0, "phase_ids": set()},
            )
            expense_row["expenses"] += float(line.estimated_expenses or 0.0)
            expense_row["phase_ids"].add(line.phase_id)
    snapshots = []
    for code, row in sorted(rows.items()):
        phase_ids = sorted(row["phase_ids"])
        phase_id = phase_ids[0] if len(phase_ids) == 1 else None
        snapshots.append(
            BudgetCodeBudgetSnapshot(
                code=code,
                phase_id=phase_id,
                budgeted_fees=round(row["fees"], 2),
                budgeted_expenses=round(row["expenses"], 2),
                budgeted_total=round(row["fees"] + row["expenses"], 2),
            )
        )
    return snapshots


def _snapshot_map(
    snapshots: list[BudgetPhaseBudgetSnapshot],
) -> dict[str, BudgetPhaseBudgetSnapshot]:
    return {snapshot.phase_id: snapshot for snapshot in snapshots}


def _code_snapshot_map(
    snapshots: list[BudgetCodeBudgetSnapshot],
) -> dict[str, BudgetCodeBudgetSnapshot]:
    return {snapshot.code: snapshot for snapshot in snapshots}


def _line_matches(line: BudgetLine, change: BudgetReviewChange) -> bool:
    if line.phase_id != change.phase_id or line.task_id != change.task_id:
        return False
    if change.staffing_role and line.staffing_role != change.staffing_role:
        return False
    if (
        change.external_code_candidate
        and line.external_code_candidate != change.external_code_candidate
    ):
        return False
    return not (change.expense_code and line.expense_code != change.expense_code)


def _target_line(budget: BudgetProposal, change: BudgetReviewChange) -> BudgetLine:
    matches = [line for line in budget.lines if _line_matches(line, change)]
    if not matches:
        raise ValueError(
            "budget review change targets no budget line: "
            f"{change.phase_id}/{change.task_id}/{change.staffing_role or '*'}"
        )
    if len(matches) > 1:
        raise ValueError(
            "budget review change ambiguously targets multiple budget lines: "
            f"{change.phase_id}/{change.task_id}/{change.staffing_role or '*'}"
        )
    return matches[0]


def _numeric(value: float | str | None, *, field: str) -> float:
    if value is None:
        raise ValueError(f"{field} change requires a numeric new_value")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} change requires a numeric new_value") from exc


def _delta_for_change(
    *,
    budget: BudgetProposal,
    change: BudgetReviewChange,
) -> BudgetRevisionDelta:
    fee_delta = 0.0
    expense_delta = 0.0
    hours_delta = 0.0
    previous_value: float | str | None = None
    target_line: BudgetLine | None = None

    if change.target_type == "budget_line":
        target_line = _target_line(budget, change)
        if change.field == "estimated_hours":
            previous_value = target_line.estimated_hours
            new_value = _numeric(change.new_value, field=change.field)
            hours_delta = round(new_value - target_line.estimated_hours, 2)
            if target_line.hourly_rate is not None:
                fee_delta = round(hours_delta * target_line.hourly_rate, 2)
        elif change.field == "hourly_rate":
            previous_value = target_line.hourly_rate
            new_value = _numeric(change.new_value, field=change.field)
            old_rate = float(target_line.hourly_rate or 0.0)
            fee_delta = round((new_value - old_rate) * target_line.estimated_hours, 2)
        elif change.field == "estimated_expenses":
            previous_value = target_line.estimated_expenses
            new_value = _numeric(change.new_value, field=change.field)
            expense_delta = round(new_value - target_line.estimated_expenses, 2)
        else:
            previous_value = None
    elif change.field in {"assumption", "exclusion", "unknown", "scenario_id"}:
        previous_value = None

    return BudgetRevisionDelta(
        delta_id=new_id("budgetrevdelta"),
        change_id=change.change_id,
        target_type=change.target_type,
        phase_id=change.phase_id,
        task_id=change.task_id,
        external_code_candidate=(
            change.external_code_candidate
            or (target_line.external_code_candidate if target_line is not None else None)
        ),
        expense_code=change.expense_code or (target_line.expense_code if target_line else None),
        staffing_role=change.staffing_role or (target_line.staffing_role if target_line else None),
        field=change.field,
        previous_value=previous_value,
        new_value=change.new_value,
        hours_delta=hours_delta,
        fee_delta=fee_delta,
        expense_delta=expense_delta,
        total_delta=round(fee_delta + expense_delta, 2),
        reason=change.reason,
        evidence_refs=change.evidence_refs,
        structured_refs=change.structured_refs,
    )


def _apply_delta_to_phase(
    rows: dict[str, BudgetPhaseBudgetSnapshot],
    delta: BudgetRevisionDelta,
) -> None:
    if not delta.phase_id or delta.phase_id not in rows:
        return
    row = rows[delta.phase_id]
    fees = round(float(row.budgeted_fees or 0.0) + delta.fee_delta, 2)
    expenses = round(row.budgeted_expenses + delta.expense_delta, 2)
    rows[delta.phase_id] = row.model_copy(
        update={
            "budgeted_fees": fees,
            "budgeted_expenses": expenses,
            "budgeted_total": round(fees + expenses, 2),
        }
    )


def _apply_delta_to_code(
    rows: dict[str, BudgetCodeBudgetSnapshot],
    delta: BudgetRevisionDelta,
) -> None:
    if delta.external_code_candidate and delta.fee_delta:
        row = rows.get(delta.external_code_candidate)
        if row:
            fees = round(row.budgeted_fees + delta.fee_delta, 2)
            rows[delta.external_code_candidate] = row.model_copy(
                update={
                    "budgeted_fees": fees,
                    "budgeted_total": round(fees + row.budgeted_expenses, 2),
                }
            )
    expense_code = delta.expense_code or delta.external_code_candidate
    if expense_code and delta.expense_delta:
        row = rows.get(expense_code)
        if row:
            expenses = round(row.budgeted_expenses + delta.expense_delta, 2)
            rows[expense_code] = row.model_copy(
                update={
                    "budgeted_expenses": expenses,
                    "budgeted_total": round(row.budgeted_fees + expenses, 2),
                }
            )


def _status_for_outcome(outcome: str) -> str:
    return {
        "corrected": "revision_recorded",
        "confirmed_no_change": "confirmed_no_change",
        "needs_more_information": "blocked_needs_more_information",
        "human_only": "human_only",
        "declined_referred": "declined_referred",
    }[outcome]


def _bind_record_to_budget(
    record: BudgetReviewChangeRecord,
    budget: BudgetProposal,
    budget_ref: str,
) -> BudgetReviewChangeRecord:
    budget_proposal_id = (
        budget.budget_proposal_id
        if record.budget_proposal_id == "__BUDGET_PROPOSAL_ID__"
        else record.budget_proposal_id
    )
    if budget_proposal_id != budget.budget_proposal_id:
        raise ValueError(
            "budget review record budget_proposal_id does not match proposal: "
            f"{budget_proposal_id} != {budget.budget_proposal_id}"
        )
    return record.model_copy(
        update={
            "budget_proposal_id": budget.budget_proposal_id,
            "source_budget_proposal_ref": budget_ref,
        }
    )


def build_budget_revision_report(
    *,
    budget: BudgetProposal,
    record: BudgetReviewChangeRecord,
    budget_ref: str,
    history_ref: str | None = None,
) -> BudgetRevisionReport:
    original_phase_totals = _phase_snapshots_from_lines(budget.lines)
    original_code_totals = _code_snapshots_from_lines(budget.lines)
    phase_rows = _snapshot_map(original_phase_totals)
    code_rows = _code_snapshot_map(original_code_totals)
    deltas = [_delta_for_change(budget=budget, change=change) for change in record.changes]
    for delta in deltas:
        _apply_delta_to_phase(phase_rows, delta)
        _apply_delta_to_code(code_rows, delta)
    original_total = _money(budget.total_proposed_budget)
    total_delta = round(sum(delta.total_delta for delta in deltas), 2)
    revised_total = round(original_total + total_delta, 2) if original_total is not None else None
    return BudgetRevisionReport(
        budget_revision_report_id=new_id("budgetrevision"),
        run_id=new_id("budgetreviewrun"),
        preflight_packet_id=budget.preflight_packet_id,
        budget_proposal_id=budget.budget_proposal_id,
        budget_review_change_record_id=record.budget_review_change_record_id,
        source_budget_proposal_ref=budget_ref,
        status=_status_for_outcome(record.outcome),  # type: ignore[arg-type]
        review_outcome=record.outcome,
        change_count=len(record.changes),
        numeric_change_count=sum(
            1 for delta in deltas if delta.fee_delta or delta.expense_delta or delta.hours_delta
        ),
        original_phase_totals=original_phase_totals,
        revised_phase_totals=list(phase_rows.values()),
        original_code_totals=original_code_totals,
        revised_code_totals=list(code_rows.values()),
        original_total=original_total,
        revised_total=revised_total,
        total_delta=total_delta,
        deltas=deltas,
        append_only_history_ref=history_ref,
        generated_at=now_iso(),
    )


def build_budget_revision_exception_candidates(
    report: BudgetRevisionReport,
    report_ref: str,
) -> list[ExceptionLakeCandidate]:
    if report.change_count == 0:
        return []
    return [
        ExceptionLakeCandidate(
            candidate_id=new_id("exc"),
            run_id=report.run_id,
            preflight_packet_id=report.preflight_packet_id,
            local_event_label="budget_human_change_recorded",
            canonical_lake_class="workflow_escalation",
            reason=(
                f"Human budget review recorded {report.change_count} append-only change(s) "
                f"with total candidate delta {report.total_delta}."
            ),
            structured_refs=[
                report_ref,
                f"budget-proposal://{report.budget_proposal_id}",
                "docs/human-review.md#budget-review",
            ],
            blocked_state="budget_review_change_requires_lake_admission_by_owner",
        )
    ]


def render_budget_revision_report(report: BudgetRevisionReport) -> str:
    lines = [
        "# Budget Revision Report",
        "",
        f"**Report ID:** {report.budget_revision_report_id}",
        f"**Status:** {report.status}",
        f"**Budget proposal:** {report.budget_proposal_id}",
        f"**Review record:** {report.budget_review_change_record_id}",
        "",
        "## Summary",
        "",
        f"- Change count: {report.change_count}",
        f"- Numeric change count: {report.numeric_change_count}",
        f"- Original total: {report.original_total}",
        f"- Revised candidate total: {report.revised_total}",
        f"- Total delta: {report.total_delta}",
        f"- Original budget mutated: {report.original_budget_mutated}",
        f"- Superseding budget written: {report.superseding_budget_written}",
        f"- Budget submission authorized: {report.budget_submission_authorized}",
        f"- Carrier submission authorized: {report.carrier_submission_authorized}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        "",
        "## Deltas",
        "",
    ]
    if not report.deltas:
        lines.append("- none")
    for delta in report.deltas:
        lines.append(
            f"- {delta.change_id}: {delta.field} {delta.previous_value} -> "
            f"{delta.new_value}; phase={delta.phase_id}; task={delta.task_id}; "
            f"fee_delta={delta.fee_delta}; expense_delta={delta.expense_delta}; "
            f"reason={delta.reason}"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This report records candidate human budget review evidence only. It does not mutate the original budget, authorize submission, write to billing, admit Lake records, or promote canonical budget taxonomy.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_review_record(
    *,
    budget_path: str | Path,
    review_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetRevisionReport, Path]:
    budget_path = Path(budget_path)
    review_path = Path(review_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    budget = BudgetProposal.model_validate(load_json(budget_path))
    record = BudgetReviewChangeRecord.model_validate(load_json(review_path))
    record = _bind_record_to_budget(record, budget, str(budget_path))
    history_path = run_dir / BUDGET_REVISION_HISTORY_FILENAME
    report = build_budget_revision_report(
        budget=budget,
        record=record,
        budget_ref=str(budget_path),
        history_ref=str(history_path),
    )
    record_path = run_dir / BUDGET_REVIEW_CHANGE_RECORD_FILENAME
    report_path = run_dir / BUDGET_REVISION_REPORT_FILENAME
    candidates_path = run_dir / BUDGET_REVISION_EXCEPTION_CANDIDATES_FILENAME
    notes_path = run_dir / BUDGET_REVISION_NOTES_FILENAME
    write_json(record_path, record.model_dump(mode="json"))
    append_jsonl(history_path, record.model_dump(mode="json"))
    write_json(report_path, report.model_dump(mode="json"))
    candidates_path.touch()
    for candidate in build_budget_revision_exception_candidates(report, str(report_path)):
        append_jsonl(candidates_path, candidate.model_dump(mode="json"))
    notes_path.write_text(render_budget_revision_report(report), encoding="utf-8")
    return report, run_dir
