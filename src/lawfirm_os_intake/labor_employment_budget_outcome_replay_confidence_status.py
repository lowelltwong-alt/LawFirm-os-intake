from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
    LaborEmploymentBudgetOutcomeReplayConfidenceStage,
    LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport,
    LaborEmploymentBudgetOutcomeReplayExecutionReport,
    LaborEmploymentBudgetOutcomeReplayInputPackReport,
    LaborEmploymentBudgetOutcomeReplayReadinessReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME = (
    "labor_employment_budget_outcome_replay_confidence_status_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_NOTES_FILENAME = (
    "labor_employment_budget_outcome_replay_confidence_status_report.md"
)


def run_labor_employment_budget_outcome_replay_confidence_status(
    *,
    readiness_report_path: str | Path,
    execution_report_path: str | Path,
    builder_binding_report_path: str | Path,
    input_pack_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport, Path]:
    readiness_ref = Path(readiness_report_path)
    execution_ref = Path(execution_report_path)
    binding_ref = Path(builder_binding_report_path)
    input_pack_ref = Path(input_pack_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness = LaborEmploymentBudgetOutcomeReplayReadinessReport.model_validate(
        load_json(readiness_ref)
    )
    execution = LaborEmploymentBudgetOutcomeReplayExecutionReport.model_validate(
        load_json(execution_ref)
    )
    binding = LaborEmploymentBudgetOutcomeReplayBuilderBindingReport.model_validate(
        load_json(binding_ref)
    )
    input_pack = LaborEmploymentBudgetOutcomeReplayInputPackReport.model_validate(
        load_json(input_pack_ref)
    )

    stages = [
        _readiness_stage(readiness, readiness_ref),
        _execution_stage(execution, execution_ref),
        _binding_stage(binding, binding_ref),
        _input_pack_stage(input_pack, input_pack_ref),
    ]
    blocked_count = len([stage for stage in stages if stage.status == "blocked"])
    pending_count = len([stage for stage in stages if stage.status == "pending_inputs"])
    status = (
        "blocked_by_labor_employment_budget_outcome_replay_confidence"
        if blocked_count
        else "labor_employment_budget_outcome_replay_confidence_pending_inputs"
        if pending_count
        else "labor_employment_budget_outcome_replay_confidence_ready_for_review"
    )
    blockers = [blocker for stage in stages for blocker in stage.blockers]
    report_core = {
        "readiness": readiness.outcome_replay_readiness_report_id,
        "execution": execution.outcome_replay_execution_report_id,
        "binding": binding.builder_binding_report_id,
        "input_pack": input_pack.input_pack_report_id,
        "stage_statuses": [(stage.stage_id, stage.status) for stage in stages],
        "blockers": blockers,
    }
    report = LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport(
        replay_confidence_status_report_id="lereplayconfidence_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,
        source_readiness_report_ref=str(readiness_ref),
        source_readiness_report_id=readiness.outcome_replay_readiness_report_id,
        source_readiness_report_status=readiness.status,
        source_execution_report_ref=str(execution_ref),
        source_execution_report_id=execution.outcome_replay_execution_report_id,
        source_execution_report_status=execution.status,
        source_builder_binding_report_ref=str(binding_ref),
        source_builder_binding_report_id=binding.builder_binding_report_id,
        source_builder_binding_report_status=binding.status,
        source_input_pack_report_ref=str(input_pack_ref),
        source_input_pack_report_id=input_pack.input_pack_report_id,
        source_input_pack_report_status=input_pack.status,
        fixture_count=readiness.fixture_count,
        stage_count=len(stages),
        ready_stage_count=len([stage for stage in stages if stage.status == "ready"]),
        pending_stage_count=pending_count,
        blocked_stage_count=blocked_count,
        readiness_failed_case_count=readiness.failed_case_count,
        execution_failed_case_count=execution.failed_case_count,
        builder_replay_input_gap_count=binding.replay_input_gap_count,
        builder_missing_case_prerequisite_count=binding.missing_case_prerequisite_count,
        input_pack_missing_input_count=input_pack.missing_input_count,
        input_pack_invalid_input_count=input_pack.invalid_input_count,
        stages=stages,
        top_blockers=blockers[:6],
        display_banner={
            "status": status,
            "candidate_only": True,
            "blocked_actions": [
                "budget_submission",
                "matter_opening",
                "conflict_conclusion",
                "calibration",
                "lake_or_sqlite_write",
                "silent_learning",
            ],
            "summary": _banner_summary(status=status, pending_count=pending_count),
        },
        candidate_exception_lake_labels=sorted(
            {
                "labor_employment_budget_outcome_replay_confidence_candidate",
                *readiness.candidate_exception_lake_labels,
                *execution.candidate_exception_lake_labels,
                *binding.candidate_exception_lake_labels,
                *input_pack.candidate_exception_lake_labels,
            }
        ),
        required_next_gates=sorted(
            {
                "human_labor_employment_replay_confidence_review",
                *readiness.required_next_gates,
                *execution.required_next_gates,
                *binding.required_next_gates,
                *input_pack.required_next_gates,
            }
        ),
        red_team_notes=[
            "This report summarizes existing replay QA artifacts; it does not run builders or create replay outputs.",
            "Ready stages mean candidate review readiness, not production readiness, calibration, learning, or carrier/billing authority.",
            "Replay input gaps and missing one-of reviewed learning signals must remain visible as pending input work.",
        ],
        rust_transition_candidates=sorted(
            {
                "deterministic_replay_confidence_status_aggregator",
                *input_pack.rust_transition_candidates,
            }
        ),
        generated_at=generated_at or now_iso(),
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_NOTES_FILENAME
    ).write_text(
        render_labor_employment_budget_outcome_replay_confidence_status(report), encoding="utf-8"
    )
    return report, output_dir


def render_labor_employment_budget_outcome_replay_confidence_status(
    report: LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Outcome Replay Confidence Status",
        "",
        f"**Report ID:** {report.replay_confidence_status_report_id}",
        f"**Status:** {report.status}",
        "",
        "## Stages",
        "",
    ]
    for stage in report.stages:
        lines.extend(
            [
                f"- {stage.label}: {stage.status}; blockers={stage.blocker_count}",
                *[f"  - {blocker}" for blocker in stage.blockers],
            ]
        )
    lines.extend(["", "## Blocked Actions", ""])
    lines.extend(f"- {action}" for action in report.display_banner["blocked_actions"])
    lines.extend(
        [
            "",
            "This report is candidate-only synthetic QA evidence. It does not submit budgets, "
            "open matters, write to the Exception Lake or SQLite, call connectors, or silently learn.",
            "",
        ]
    )
    return "\n".join(lines)


def _readiness_stage(
    report: LaborEmploymentBudgetOutcomeReplayReadinessReport,
    report_ref: Path,
) -> LaborEmploymentBudgetOutcomeReplayConfidenceStage:
    blockers = []
    if report.status != "labor_employment_budget_outcome_replay_ready_for_review":
        blockers.append(f"readiness status={report.status}")
    if report.failed_case_count:
        blockers.append(f"failed replay readiness cases={report.failed_case_count}")
    if report.missing_loop_requirement_count:
        blockers.append(f"missing loop requirements={report.missing_loop_requirement_count}")
    if report.unresolved_source_ref_count:
        blockers.append(f"unresolved source refs={report.unresolved_source_ref_count}")
    return LaborEmploymentBudgetOutcomeReplayConfidenceStage(
        stage_id="readiness",
        label="Replay Readiness",
        source_report_ref=str(report_ref),
        source_report_id=report.outcome_replay_readiness_report_id,
        source_report_status=report.status,
        status="blocked" if blockers else "ready",
        counts={
            "fixture_count": report.fixture_count,
            "failed_case_count": report.failed_case_count,
            "missing_loop_requirement_count": report.missing_loop_requirement_count,
            "unresolved_source_ref_count": report.unresolved_source_ref_count,
        },
        blocker_count=len(blockers),
        blockers=blockers,
        evidence_refs=[report.outcome_replay_readiness_report_id],
    )


def _execution_stage(
    report: LaborEmploymentBudgetOutcomeReplayExecutionReport,
    report_ref: Path,
) -> LaborEmploymentBudgetOutcomeReplayConfidenceStage:
    blockers = []
    if report.status != "labor_employment_budget_outcome_replay_execution_ready_for_review":
        blockers.append(f"execution status={report.status}")
    if report.failed_case_count:
        blockers.append(f"failed replay execution cases={report.failed_case_count}")
    if report.materialized_artifact_slot_count != report.expected_artifact_slot_count:
        blockers.append(
            "materialized artifact slots="
            f"{report.materialized_artifact_slot_count}/{report.expected_artifact_slot_count}"
        )
    if report.runtime_artifact_count:
        blockers.append(f"runtime artifacts created={report.runtime_artifact_count}")
    return LaborEmploymentBudgetOutcomeReplayConfidenceStage(
        stage_id="execution",
        label="Replay Execution Slots",
        source_report_ref=str(report_ref),
        source_report_id=report.outcome_replay_execution_report_id,
        source_report_status=report.status,
        status="blocked" if blockers else "ready",
        counts={
            "fixture_count": report.fixture_count,
            "failed_case_count": report.failed_case_count,
            "expected_artifact_slot_count": report.expected_artifact_slot_count,
            "materialized_artifact_slot_count": report.materialized_artifact_slot_count,
            "runtime_artifact_count": report.runtime_artifact_count,
        },
        blocker_count=len(blockers),
        blockers=blockers,
        evidence_refs=[report.outcome_replay_execution_report_id],
    )


def _binding_stage(
    report: LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
    report_ref: Path,
) -> LaborEmploymentBudgetOutcomeReplayConfidenceStage:
    blockers = []
    if report.status != "labor_employment_budget_replay_builder_binding_ready_for_review":
        blockers.append(f"builder binding status={report.status}")
    if report.failed_case_count:
        blockers.append(f"failed builder binding cases={report.failed_case_count}")
    if report.unknown_artifact_count:
        blockers.append(f"unknown artifacts={report.unknown_artifact_count}")
    if report.blocked_slot_count:
        blockers.append(f"blocked builder slots={report.blocked_slot_count}")
    pending = []
    if report.replay_input_gap_count:
        pending.append(f"replay input gaps={report.replay_input_gap_count}")
    if report.missing_case_prerequisite_count:
        pending.append(f"missing case prerequisites={report.missing_case_prerequisite_count}")
    status = "blocked" if blockers else "pending_inputs" if pending else "ready"
    return LaborEmploymentBudgetOutcomeReplayConfidenceStage(
        stage_id="builder_binding",
        label="Builder Binding",
        source_report_ref=str(report_ref),
        source_report_id=report.builder_binding_report_id,
        source_report_status=report.status,
        status=status,
        counts={
            "slot_count": report.slot_count,
            "bound_slot_count": report.bound_slot_count,
            "unknown_artifact_count": report.unknown_artifact_count,
            "blocked_slot_count": report.blocked_slot_count,
            "replay_input_gap_count": report.replay_input_gap_count,
            "missing_case_prerequisite_count": report.missing_case_prerequisite_count,
        },
        blocker_count=len([*blockers, *pending]),
        blockers=[*blockers, *pending],
        evidence_refs=[report.builder_binding_report_id],
    )


def _input_pack_stage(
    report: LaborEmploymentBudgetOutcomeReplayInputPackReport,
    report_ref: Path,
) -> LaborEmploymentBudgetOutcomeReplayConfidenceStage:
    blockers = []
    if report.status == "blocked_by_labor_employment_budget_replay_input_pack":
        blockers.append(f"input-pack status={report.status}")
    if report.invalid_input_count:
        blockers.append(f"invalid replay inputs={report.invalid_input_count}")
    if report.blocked_case_count:
        blockers.append(f"blocked replay input cases={report.blocked_case_count}")
    pending = []
    if report.missing_input_count:
        pending.append(f"missing replay inputs={report.missing_input_count}")
    if report.one_of_signal_missing_count:
        pending.append(
            f"missing one-of reviewed learning signals={report.one_of_signal_missing_count}"
        )
    if report.partial_case_count:
        pending.append(f"partial replay input cases={report.partial_case_count}")
    status = "blocked" if blockers else "pending_inputs" if pending else "ready"
    return LaborEmploymentBudgetOutcomeReplayConfidenceStage(
        stage_id="input_pack",
        label="Replay Input Pack",
        source_report_ref=str(report_ref),
        source_report_id=report.input_pack_report_id,
        source_report_status=report.status,
        status=status,
        counts={
            "case_count": report.case_count,
            "ready_case_count": report.ready_case_count,
            "partial_case_count": report.partial_case_count,
            "blocked_case_count": report.blocked_case_count,
            "missing_input_count": report.missing_input_count,
            "invalid_input_count": report.invalid_input_count,
            "one_of_signal_missing_count": report.one_of_signal_missing_count,
        },
        blocker_count=len([*blockers, *pending]),
        blockers=[*blockers, *pending],
        evidence_refs=[report.input_pack_report_id],
    )


def _banner_summary(*, status: str, pending_count: int) -> str:
    if status == "labor_employment_budget_outcome_replay_confidence_ready_for_review":
        return "Replay QA stages are ready for candidate human review."
    if status == "labor_employment_budget_outcome_replay_confidence_pending_inputs":
        return f"Replay QA has {pending_count} pending input stage(s); no calibration or learning is authorized."
    return "Replay QA is blocked; repair failed stages before relying on the replay surface."
