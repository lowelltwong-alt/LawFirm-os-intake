from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetCalibrationReadinessReport,
    BudgetFixtureUpdateReviewCheck,
    BudgetFixtureUpdateReviewRecord,
    BudgetFixtureUpdateReviewReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_FIXTURE_UPDATE_REVIEW_RECORD_FILENAME = "budget_fixture_update_review_record.json"
BUDGET_FIXTURE_UPDATE_REVIEW_HISTORY_FILENAME = "budget_fixture_update_review_history.jsonl"
BUDGET_FIXTURE_UPDATE_REVIEW_REPORT_FILENAME = "budget_fixture_update_review_report.json"
BUDGET_FIXTURE_UPDATE_REVIEW_NOTES_FILENAME = "budget_fixture_update_review_report.md"

ACCEPT_FIXTURE_UPDATE_DECISIONS = {
    "accept_for_separate_fixture_update_pr",
    "accept_with_corrections_for_separate_fixture_update_pr",
}

BUDGET_FIXTURE_UPDATE_REVIEW_REQUIRED_NEXT_GATES = [
    "append_only_fixture_update_review_record",
    "separate_fixture_update_pr_if_accepted",
    "fixture_update_pr_review_if_created",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
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
) -> BudgetFixtureUpdateReviewCheck:
    return BudgetFixtureUpdateReviewCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _record_boundary_clear(record: BudgetFixtureUpdateReviewRecord) -> bool:
    return (
        record.source_readiness_report_mutated is False
        and record.fixture_update_pr_created is False
        and record.fixture_files_mutated is False
        and record.fixture_binding_applied is False
        and record.downstream_learning_gate_allowed is False
        and record.calibration_applied is False
        and record.profile_mutation_performed is False
        and record.template_mutation_performed is False
        and record.budget_mutation_performed is False
        and record.carrier_guideline_mutation_performed is False
        and record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.silent_learning_performed is False
    )


def _readiness_boundary_clear(report: BudgetCalibrationReadinessReport) -> bool:
    return (
        report.fixture_update_authorized is False
        and report.fixture_update_pr_created is False
        and report.fixture_files_mutated is False
        and report.fixture_binding_applied is False
        and report.downstream_learning_gate_allowed is False
        and report.calibration_applied is False
        and report.profile_mutation_performed is False
        and report.template_mutation_performed is False
        and report.budget_mutation_performed is False
        and report.carrier_guideline_mutation_performed is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _accepted(record: BudgetFixtureUpdateReviewRecord) -> bool:
    return record.decision in ACCEPT_FIXTURE_UPDATE_DECISIONS


def _bind_record_to_readiness(
    *,
    record: BudgetFixtureUpdateReviewRecord,
    readiness: BudgetCalibrationReadinessReport,
) -> BudgetFixtureUpdateReviewRecord:
    if (
        record.budget_calibration_readiness_report_id
        != readiness.budget_calibration_readiness_report_id
    ):
        raise ValueError(
            "fixture update review budget_calibration_readiness_report_id does not match: "
            f"{record.budget_calibration_readiness_report_id} != "
            f"{readiness.budget_calibration_readiness_report_id}"
        )
    if record.fixture_binding_handoff_report_id != readiness.fixture_binding_handoff_report_id:
        raise ValueError(
            "fixture update review fixture_binding_handoff_report_id does not match: "
            f"{record.fixture_binding_handoff_report_id} != "
            f"{readiness.fixture_binding_handoff_report_id}"
        )
    if record.replay_case_id != readiness.replay_case_id:
        raise ValueError(
            "fixture update review replay_case_id does not match: "
            f"{record.replay_case_id} != {readiness.replay_case_id}"
        )
    unbound_outputs = sorted(set(record.accepted_output_refs) - set(readiness.approved_output_refs))
    if _accepted(record) and unbound_outputs:
        raise ValueError(
            "accepted fixture update output refs are not approved by readiness report: "
            + ", ".join(unbound_outputs)
        )
    unbound_targets = sorted(
        set(record.target_fixture_refs) - set(readiness.proposed_target_fixture_refs)
    )
    if _accepted(record) and unbound_targets:
        raise ValueError(
            "accepted fixture update target refs are not proposed by readiness report: "
            + ", ".join(unbound_targets)
        )
    return record


def build_budget_fixture_update_review_report(
    *,
    readiness_report: BudgetCalibrationReadinessReport,
    readiness_report_ref: str,
    review_record: BudgetFixtureUpdateReviewRecord,
    history_ref: str,
) -> BudgetFixtureUpdateReviewReport:
    failed_readiness_checks = [
        check.check_id for check in readiness_report.checks if check.status == "failed"
    ]
    accept_decision = _accepted(review_record)
    accepted_outputs_bound = sorted(set(review_record.accepted_output_refs)) == sorted(
        set(review_record.accepted_output_refs) & set(readiness_report.approved_output_refs)
    )
    target_refs_bound = sorted(set(review_record.target_fixture_refs)) == sorted(
        set(review_record.target_fixture_refs) & set(readiness_report.proposed_target_fixture_refs)
    )
    checks = [
        _check(
            "calibration_readiness_allows_manual_review",
            readiness_report.status == "ready_for_manual_fixture_update_review"
            and not failed_readiness_checks
            and readiness_report.ready_fixture_binding_handoff_count > 0
            and readiness_report.blocked_fixture_binding_handoff_count == 0
            and _readiness_boundary_clear(readiness_report),
            "Calibration readiness is ready for manual fixture-update review and still has no side effects.",
            artifact_refs=[readiness_report_ref],
            blocking_refs=failed_readiness_checks,
        ),
        _check(
            "review_record_matches_readiness",
            review_record.budget_calibration_readiness_report_id
            == readiness_report.budget_calibration_readiness_report_id
            and review_record.fixture_binding_handoff_report_id
            == readiness_report.fixture_binding_handoff_report_id
            and review_record.replay_case_id == readiness_report.replay_case_id,
            "Fixture update review record is bound to the supplied calibration readiness report.",
            artifact_refs=[readiness_report_ref],
        ),
        _check(
            "accepted_outputs_bound_to_readiness",
            (not accept_decision)
            or (bool(review_record.accepted_output_refs) and accepted_outputs_bound),
            "Accepted output refs are approved by the calibration readiness report.",
            artifact_refs=review_record.accepted_output_refs,
        ),
        _check(
            "target_fixture_refs_bound_to_readiness",
            (not accept_decision)
            or (bool(review_record.target_fixture_refs) and target_refs_bound),
            "Target fixture refs are proposed by the calibration readiness report.",
            artifact_refs=review_record.target_fixture_refs,
        ),
        _check(
            "human_decision_record_complete",
            bool(
                review_record.reviewer_id.strip()
                and review_record.reviewed_at.strip()
                and review_record.decision_reason.strip()
            ),
            "Human fixture-update review decision includes reviewer, timestamp, and reason.",
        ),
        _check(
            "no_side_effects_from_review_recording",
            _record_boundary_clear(review_record),
            "Recording the fixture-update review did not mutate fixtures, apply calibration, write Lake/SQLite records, or perform silent learning.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "blocked_by_fixture_update_review_evidence"
    elif accept_decision:
        status = "fixture_update_review_recorded_separate_pr_required"
    else:
        status = "fixture_update_review_recorded_no_fixture_pr"
    return BudgetFixtureUpdateReviewReport(
        fixture_update_review_report_id=_stable_id(
            "budgetfixtureupdatereviewreport",
            "|".join(
                [
                    readiness_report.budget_calibration_readiness_report_id,
                    review_record.fixture_update_review_id,
                    review_record.decision,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_budget_calibration_readiness_report_id=(
            readiness_report.budget_calibration_readiness_report_id
        ),
        source_budget_calibration_readiness_report_ref=readiness_report_ref,
        source_budget_calibration_readiness_status=readiness_report.status,
        fixture_binding_handoff_report_id=readiness_report.fixture_binding_handoff_report_id,
        replay_case_id=readiness_report.replay_case_id,
        fixture_update_review_id=review_record.fixture_update_review_id,
        decision=review_record.decision,
        decision_reason=review_record.decision_reason,
        accepted_output_refs=review_record.accepted_output_refs,
        rejected_output_refs=review_record.rejected_output_refs,
        target_fixture_refs=review_record.target_fixture_refs,
        reviewer_corrections=review_record.reviewer_corrections,
        required_followups=review_record.required_followups,
        reviewed_red_team_notes=review_record.reviewed_red_team_notes,
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=BUDGET_FIXTURE_UPDATE_REVIEW_REQUIRED_NEXT_GATES,
        accepted_for_fixture_update_pr=accept_decision and not failed_checks,
        separate_fixture_update_pr_required=accept_decision and not failed_checks,
        generated_at=now_iso(),
    )


def render_budget_fixture_update_review_report(
    report: BudgetFixtureUpdateReviewReport,
) -> str:
    lines = [
        "# Budget Fixture Update Review Report",
        "",
        f"**Report ID:** {report.fixture_update_review_report_id}",
        f"**Status:** {report.status}",
        f"**Decision:** {report.decision}",
        f"**Replay case:** {report.replay_case_id}",
        f"**Calibration readiness:** `{report.source_budget_calibration_readiness_report_ref}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Fixture Review Decision",
        "",
        f"- Decision reason: {report.decision_reason}",
        f"- Accepted output refs: {len(report.accepted_output_refs)}",
        f"- Rejected output refs: {len(report.rejected_output_refs)}",
        f"- Target fixture refs: {len(report.target_fixture_refs)}",
        f"- Separate fixture-update PR required: {report.separate_fixture_update_pr_required}",
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
            f"- Candidate only: {report.candidate_only}",
            f"- Non-authoritative: {report.non_authoritative}",
            f"- Synthetic only: {report.synthetic_only}",
            f"- Source readiness report mutated: {report.source_readiness_report_mutated}",
            f"- Fixture update PR created: {report.fixture_update_pr_created}",
            f"- Fixture files mutated: {report.fixture_files_mutated}",
            f"- Fixture binding applied: {report.fixture_binding_applied}",
            f"- Downstream learning gate allowed: {report.downstream_learning_gate_allowed}",
            f"- Calibration applied: {report.calibration_applied}",
            f"- Profile mutation performed: {report.profile_mutation_performed}",
            f"- Template mutation performed: {report.template_mutation_performed}",
            f"- Budget mutation performed: {report.budget_mutation_performed}",
            f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report records local append-only fixture-update review evidence only. It does not update fixtures, create a PR, apply calibration, apply learning, write Lake/SQLite records, submit budgets, open matters, or authorize external action.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_fixture_update_review_record(
    *,
    calibration_readiness_report_path: str | Path,
    review_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetFixtureUpdateReviewReport, Path]:
    readiness_path = Path(calibration_readiness_report_path)
    review_path = Path(review_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    readiness = BudgetCalibrationReadinessReport.model_validate(load_json(readiness_path))
    raw_record = BudgetFixtureUpdateReviewRecord.model_validate(load_json(review_path))
    record = _bind_record_to_readiness(record=raw_record, readiness=readiness)
    history_path = run_dir / BUDGET_FIXTURE_UPDATE_REVIEW_HISTORY_FILENAME
    report = build_budget_fixture_update_review_report(
        readiness_report=readiness,
        readiness_report_ref=str(readiness_path),
        review_record=record,
        history_ref=str(history_path),
    )
    write_json(
        run_dir / BUDGET_FIXTURE_UPDATE_REVIEW_RECORD_FILENAME,
        record.model_dump(mode="json"),
    )
    append_jsonl(history_path, record.model_dump(mode="json"))
    write_json(
        run_dir / BUDGET_FIXTURE_UPDATE_REVIEW_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_FIXTURE_UPDATE_REVIEW_NOTES_FILENAME).write_text(
        render_budget_fixture_update_review_report(report),
        encoding="utf-8",
    )
    return report, run_dir
