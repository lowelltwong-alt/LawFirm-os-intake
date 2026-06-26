from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetCorpusReplayCaseResult,
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayReviewDecisionTemplate,
    BudgetCorpusReplayReviewPacket,
    BudgetCorpusReplayReviewRecommendation,
    BudgetCorpusReplayReviewRedTeamNote,
)
from .util import digest_text, load_json, new_id, now_iso, write_json


REPLAY_REVIEW_PACKET_FILENAME = "budget_corpus_replay_review_packet.json"
REPLAY_REVIEW_NOTES_FILENAME = "budget_corpus_replay_review_packet.md"
REPLAY_REVIEW_DECISION_TEMPLATE_FILENAME = "budget_corpus_replay_review_decision_template.json"

REPLAY_REVIEW_REQUIRED_NEXT_GATES = [
    "human_replay_packet_review",
    "append_only_replay_review_outcome",
    "fixture_result_binding_review",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _command_statuses(case: BudgetCorpusReplayCaseResult) -> dict[str, str]:
    return {command.command_id: command.status for command in case.command_results}


def _output_refs(case: BudgetCorpusReplayCaseResult) -> list[str]:
    return sorted(
        dict.fromkeys(check.resolved_output_path for check in case.output_checks if check.exists)
    )


def _missing_output_refs(case: BudgetCorpusReplayCaseResult) -> list[str]:
    return sorted(
        dict.fromkeys(check.output_ref for check in case.output_checks if not check.exists)
    )


def _recommended_action(case: BudgetCorpusReplayCaseResult) -> str:
    if case.status == "executed_passed":
        return "review_fixture_binding"
    if case.status == "dry_run_ready":
        return "execute_before_learning_review"
    if case.status == "executed_failed":
        if any(
            "required_learning_proposed_change_set" in reason for reason in case.blocking_reasons
        ):
            return "provide_shadow_eval_input_or_hold"
        return "repair_replay_before_learning"
    if case.status == "blocked":
        return "resolve_blocker_or_exclude"
    if case.status == "skipped_not_selected":
        return "run_selected_case_before_review"
    return "acknowledge_supporting_context"


def _priority(case: BudgetCorpusReplayCaseResult, action: str) -> str:
    if action in {"repair_replay_before_learning", "provide_shadow_eval_input_or_hold"}:
        return "critical"
    if action in {"review_fixture_binding", "resolve_blocker_or_exclude"}:
        return "high"
    if action in {"execute_before_learning_review", "run_selected_case_before_review"}:
        return "medium"
    if case.artifact_kind == "learning_support_fixture":
        return "low"
    return "medium"


def _why(case: BudgetCorpusReplayCaseResult, action: str) -> list[str]:
    lines = [
        f"Replay case `{case.replay_case_id}` has status `{case.status}`.",
        f"The source artifact is `{case.source_artifact_ref}` with kind `{case.artifact_kind}`.",
    ]
    if case.status == "executed_passed":
        lines.append(
            "All commands in the selected replay chain executed and expected outputs were found."
        )
        lines.append(
            "A human must still inspect the regenerated artifacts before fixture binding or learning use."
        )
    elif case.status == "dry_run_ready":
        lines.append(
            "The replay chain is planned but has not been executed, so it cannot support fixture binding yet."
        )
    elif case.status == "executed_failed":
        lines.append(
            "Replay execution failed or an expected output was missing; learning must remain blocked."
        )
    elif case.status == "blocked":
        lines.append(
            "The source plan or execution gate blocked this case; a reviewer must resolve or exclude it."
        )
    elif case.status == "skipped_not_selected":
        lines.append("This case was not selected for execution in the current replay run.")
    elif case.status == "skipped_supporting_context":
        lines.append(
            "This artifact is supporting context and should not be promoted as replay evidence by itself."
        )
    if case.blocking_reasons:
        lines.append("Blocking reasons: " + ", ".join(case.blocking_reasons))
    if _missing_output_refs(case):
        lines.append("Missing expected outputs: " + ", ".join(_missing_output_refs(case)))
    if action == "provide_shadow_eval_input_or_hold":
        lines.append(
            "Shadow-eval replay requires a reviewed proposed-change set before it can execute."
        )
    return lines


def _required_human_decisions(action: str) -> list[str]:
    if action == "review_fixture_binding":
        return [
            "inspect regenerated output hashes and contents",
            "approve or reject fixture-result binding",
            "decide whether the case may proceed to reviewed learning gate evidence",
        ]
    if action == "execute_before_learning_review":
        return [
            "decide whether to execute the planned replay case",
            "confirm no learning use until execution output is reviewed",
        ]
    if action == "provide_shadow_eval_input_or_hold":
        return [
            "provide reviewed proposed-change set or hold the shadow-eval case",
            "confirm no shadow-eval pass is inferred from missing input",
        ]
    if action == "repair_replay_before_learning":
        return [
            "repair the failed replay input, command, or expected-output mapping",
            "rerun replay before any learning gate use",
        ]
    if action == "resolve_blocker_or_exclude":
        return [
            "resolve the plan or corpus blocker",
            "exclude the case from learning if the blocker cannot be resolved",
        ]
    if action == "run_selected_case_before_review":
        return [
            "select and execute this case before fixture binding review",
        ]
    return [
        "acknowledge supporting context status",
        "confirm it is not used as standalone learning evidence",
    ]


def _recommendation(
    report: BudgetCorpusReplayExecutionReport,
    case: BudgetCorpusReplayCaseResult,
) -> BudgetCorpusReplayReviewRecommendation:
    action = _recommended_action(case)
    return BudgetCorpusReplayReviewRecommendation(
        recommendation_id=_stable_id(
            "replayreviewrec", f"{report.replay_execution_report_id}|{case.replay_case_id}"
        ),
        replay_case_id=case.replay_case_id,
        source_artifact_ref=case.source_artifact_ref,
        artifact_kind=case.artifact_kind,
        replay_case_status=case.status,
        recommended_action=action,  # type: ignore[arg-type]
        priority=_priority(case, action),  # type: ignore[arg-type]
        why=_why(case, action),
        command_result_statuses=_command_statuses(case),
        output_refs=_output_refs(case),
        missing_output_refs=_missing_output_refs(case),
        blocking_reasons=case.blocking_reasons,
        required_human_decisions=_required_human_decisions(action),
        downstream_learning_gate_candidate=(case.status == "executed_passed"),
    )


def _allowed_outcomes(action: str) -> list[str]:
    if action == "review_fixture_binding":
        return [
            "approve_fixture_binding",
            "reject_fixture_binding",
            "needs_more_information",
            "human_only_hold",
            "exclude_from_learning",
        ]
    if action == "execute_before_learning_review":
        return ["needs_replay_repair", "needs_more_information", "human_only_hold"]
    if action == "provide_shadow_eval_input_or_hold":
        return ["provide_shadow_eval_input", "human_only_hold", "exclude_from_learning"]
    if action == "acknowledge_supporting_context":
        return ["acknowledge_supporting_context", "exclude_from_learning"]
    return [
        "needs_replay_repair",
        "needs_more_information",
        "human_only_hold",
        "exclude_from_learning",
    ]


def _recommended_outcome(action: str) -> str:
    if action == "review_fixture_binding":
        return "needs_more_information"
    if action == "provide_shadow_eval_input_or_hold":
        return "provide_shadow_eval_input"
    if action == "acknowledge_supporting_context":
        return "acknowledge_supporting_context"
    if action in {"execute_before_learning_review", "run_selected_case_before_review"}:
        return "needs_replay_repair"
    return "needs_replay_repair"


def _decision_template(
    report: BudgetCorpusReplayExecutionReport,
    recommendation: BudgetCorpusReplayReviewRecommendation,
) -> BudgetCorpusReplayReviewDecisionTemplate:
    return BudgetCorpusReplayReviewDecisionTemplate(
        decision_template_id=_stable_id(
            "replayreviewdecision",
            f"{report.replay_execution_report_id}|{recommendation.replay_case_id}",
        ),
        replay_case_id=recommendation.replay_case_id,
        source_artifact_ref=recommendation.source_artifact_ref,
        recommended_action=recommendation.recommended_action,
        allowed_outcomes=_allowed_outcomes(recommendation.recommended_action),  # type: ignore[arg-type]
        recommended_outcome=_recommended_outcome(recommendation.recommended_action),  # type: ignore[arg-type]
        required_fields=[
            "review_outcome_id",
            "replay_case_id",
            "reviewer_id",
            "reviewed_at",
            "outcome",
            "decision_reason",
            "approved_output_refs",
            "rejected_output_refs",
            "supersedes_review_outcome_id",
        ],
        required_evidence_refs=[
            report.replay_execution_report_id,
            recommendation.replay_case_id,
            *recommendation.output_refs,
        ],
    )


def _red_team_notes(
    report: BudgetCorpusReplayExecutionReport,
    recommendations: list[BudgetCorpusReplayReviewRecommendation],
) -> list[BudgetCorpusReplayReviewRedTeamNote]:
    notes = [
        BudgetCorpusReplayReviewRedTeamNote(
            note_id=_stable_id("replayreviewrt", f"{report.replay_execution_report_id}|boundary"),
            severity="critical",
            scope="boundary",
            message=(
                "This review packet is not approval to calibrate, mutate profiles/templates/guidelines, "
                "submit budgets, write Lake or SQLite records, or use real data."
            ),
            recommended_check=(
                "Confirm calibration_applied=false, external_writes_performed=false, "
                "lake_write_performed=false, and silent_learning_performed=false."
            ),
        ),
        BudgetCorpusReplayReviewRedTeamNote(
            note_id=_stable_id(
                "replayreviewrt", f"{report.replay_execution_report_id}|human-approval"
            ),
            severity="high",
            scope="learning_loop",
            message=(
                "A passed replay only proves command execution and output presence; it is not human approval "
                "of fixture binding or a learning change."
            ),
            recommended_check=(
                "Require an append-only human review outcome before any case is used as reviewed learning evidence."
            ),
        ),
    ]
    failed_ids = [
        rec.replay_case_id
        for rec in recommendations
        if rec.recommended_action in {"repair_replay_before_learning", "resolve_blocker_or_exclude"}
    ]
    if failed_ids:
        notes.append(
            BudgetCorpusReplayReviewRedTeamNote(
                note_id=_stable_id(
                    "replayreviewrt", f"{report.replay_execution_report_id}|failed-replay"
                ),
                severity="critical",
                scope="output_integrity",
                message="Failed, blocked, or missing-output replay cases cannot support learning.",
                recommended_check="Repair and rerun the replay case or exclude it from learning evidence.",
                replay_case_ids=failed_ids,
            )
        )
    dry_run_ids = [
        rec.replay_case_id
        for rec in recommendations
        if rec.recommended_action == "execute_before_learning_review"
    ]
    if dry_run_ids:
        notes.append(
            BudgetCorpusReplayReviewRedTeamNote(
                note_id=_stable_id(
                    "replayreviewrt", f"{report.replay_execution_report_id}|dry-run"
                ),
                severity="high",
                scope="execution_scope",
                message="Dry-run replay plans have not regenerated output artifacts.",
                recommended_check="Execute selected cases and review hashes before fixture binding.",
                replay_case_ids=dry_run_ids,
            )
        )
    shadow_ids = [
        rec.replay_case_id
        for rec in recommendations
        if rec.recommended_action == "provide_shadow_eval_input_or_hold"
    ]
    if shadow_ids:
        notes.append(
            BudgetCorpusReplayReviewRedTeamNote(
                note_id=_stable_id(
                    "replayreviewrt", f"{report.replay_execution_report_id}|shadow-input"
                ),
                severity="high",
                scope="shadow_eval",
                message="Shadow-eval replay was blocked because the proposed-change set was missing.",
                recommended_check="Provide a reviewed proposed-change set or hold the case.",
                replay_case_ids=shadow_ids,
            )
        )
    support_ids = [
        rec.replay_case_id
        for rec in recommendations
        if rec.recommended_action == "acknowledge_supporting_context"
    ]
    if support_ids:
        notes.append(
            BudgetCorpusReplayReviewRedTeamNote(
                note_id=_stable_id(
                    "replayreviewrt", f"{report.replay_execution_report_id}|supporting"
                ),
                severity="medium",
                scope="supporting_context",
                message="Supporting-context fixtures are visible in review but are not executable replay evidence.",
                recommended_check="Do not use support-only artifacts as standalone learning evidence.",
                replay_case_ids=support_ids,
            )
        )
    return notes


def _packet_status(report: BudgetCorpusReplayExecutionReport) -> str:
    if report.status == "execution_passed_for_review":
        return "ready_for_human_replay_review"
    if report.status == "dry_run_ready_for_review":
        return "blocked_pending_replay_execution"
    if report.status in {"execution_failed", "blocked_by_plan"}:
        return "replay_repair_required"
    return "no_reviewable_cases"


def build_budget_corpus_replay_review_packet(
    report: BudgetCorpusReplayExecutionReport,
    *,
    replay_execution_report_ref: str,
) -> BudgetCorpusReplayReviewPacket:
    recommendations = [_recommendation(report, case) for case in report.cases]
    decision_templates = [
        _decision_template(report, recommendation) for recommendation in recommendations
    ]
    return BudgetCorpusReplayReviewPacket(
        review_packet_id=new_id("budgetcorpusreplayreview"),
        replay_execution_report_id=report.replay_execution_report_id,
        replay_execution_report_ref=replay_execution_report_ref,
        replay_execution_status=report.status,
        replay_execution_mode=report.execution_mode,
        status=_packet_status(report),  # type: ignore[arg-type]
        recommendation_count=len(recommendations),
        decision_template_count=len(decision_templates),
        executed_passed_case_count=report.executed_case_count,
        dry_run_case_count=report.dry_run_case_count,
        failed_case_count=report.failed_case_count,
        blocked_case_count=report.blocked_case_count,
        supporting_context_case_count=sum(
            1 for case in report.cases if case.status == "skipped_supporting_context"
        ),
        recommendations=recommendations,
        red_team_notes=_red_team_notes(report, recommendations),
        decision_templates=decision_templates,
        required_next_gates=REPLAY_REVIEW_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_corpus_replay_review_packet(packet: BudgetCorpusReplayReviewPacket) -> str:
    lines = [
        "# Budget Corpus Replay Review Packet",
        "",
        f"**Review packet ID:** {packet.review_packet_id}",
        f"**Status:** {packet.status}",
        f"**Execution report:** {packet.replay_execution_report_ref}",
        f"**Execution status:** {packet.replay_execution_status}",
        f"**Execution mode:** {packet.replay_execution_mode}",
        f"**Recommendations:** {packet.recommendation_count}",
        f"**Decision templates:** {packet.decision_template_count}",
        "",
        "## Boundary",
        "",
        f"- Human review required: {packet.human_review_required}",
        f"- Append-only review outcome required: {packet.append_only_review_outcome_required}",
        f"- Downstream learning without review: {packet.downstream_learning_gate_allowed_without_review}",
        f"- Calibration applied: {packet.calibration_applied}",
        f"- Profile mutation performed: {packet.profile_mutation_performed}",
        f"- Template mutation performed: {packet.template_mutation_performed}",
        f"- Budget mutation performed: {packet.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {packet.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {packet.lake_write_performed}",
        f"- SQLite write performed: {packet.sqlite_write_performed}",
        f"- External writes performed: {packet.external_writes_performed}",
        f"- Silent learning performed: {packet.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in packet.required_next_gates),
        "",
        "## Recommendations",
        "",
    ]
    for rec in packet.recommendations:
        lines.append(
            f"- `{rec.replay_case_id}`: {rec.recommended_action}; priority={rec.priority}; "
            f"status={rec.replay_case_status}"
        )
        for item in rec.why:
            lines.append(f"  - {item}")
    lines.extend(["", "## Red-Team Notes", ""])
    for note in packet.red_team_notes:
        lines.append(f"- {note.severity}/{note.scope}: {note.message}")
        lines.append(f"  - check: {note.recommended_check}")
    lines.extend(["", "## Decision Templates", ""])
    for template in packet.decision_templates:
        lines.append(
            f"- `{template.replay_case_id}`: recommended={template.recommended_outcome}; "
            f"allowed={', '.join(template.allowed_outcomes)}"
        )
    lines.extend(
        [
            "",
            "This packet is for human review only. It does not approve fixture binding, apply learning, mutate budgets, write Lake/SQLite records, or authorize external submissions.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_corpus_replay_review(
    *,
    replay_execution_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetCorpusReplayReviewPacket, Path]:
    report_path = Path(replay_execution_report_path)
    report = BudgetCorpusReplayExecutionReport.model_validate(load_json(report_path))
    packet = build_budget_corpus_replay_review_packet(
        report,
        replay_execution_report_ref=str(report_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / REPLAY_REVIEW_PACKET_FILENAME, packet.model_dump(mode="json"))
    write_json(
        run_dir / REPLAY_REVIEW_DECISION_TEMPLATE_FILENAME,
        [item.model_dump(mode="json") for item in packet.decision_templates],
    )
    (run_dir / REPLAY_REVIEW_NOTES_FILENAME).write_text(
        render_budget_corpus_replay_review_packet(packet),
        encoding="utf-8",
    )
    return packet, run_dir
