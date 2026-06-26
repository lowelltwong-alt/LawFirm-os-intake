from __future__ import annotations

from pathlib import Path

from .models import (
    LearningLoopId,
    LearningPromotionReadinessReport,
    LearningProposedChangeArtifact,
    LearningProposedChangeRedTeamNote,
    LearningProposedChangeSet,
    LearningProposedChangeType,
    LearningShadowEvalCase,
    LearningShadowEvalPlan,
)
from .util import append_jsonl, digest_text, load_json, new_id, now_iso, write_json


LEARNING_PROPOSED_CHANGE_SET_FILENAME = "learning_proposed_change_set.json"
LEARNING_PROPOSED_CHANGE_SET_NOTES_FILENAME = "learning_proposed_change_set.md"
LEARNING_PROPOSED_CHANGES_FILENAME = "learning_proposed_changes.jsonl"

REQUIRED_NEXT_GATES = [
    "human_reviewed_outcome_evidence",
    "append_only_evidence_record",
    "proposed_change_artifact",
    "synthetic_fixture_update",
    "shadow_eval_result",
    "regression_check",
    "owning_repo_review",
]

CHANGE_TYPE_BY_LOOP: dict[LearningLoopId, LearningProposedChangeType] = {
    "guideline_drift": "guideline_profile_candidate",
    "budget_model": "budget_driver_adjustment_candidate",
    "template_mapping": "template_mapping_candidate",
    "narrative_rule": "narrative_rule_candidate",
    "preapproval_gate": "preapproval_gate_candidate",
    "appeal_success_or_failure": "appeal_outcome_pattern_candidate",
    "capture_completeness": "capture_reconciliation_rule_candidate",
    "parser_rule": "parser_rule_candidate",
    "eval_fixture": "eval_fixture_candidate",
    "staffing_leverage": "staffing_leverage_candidate",
    "timekeeper_rate": "timekeeper_rate_candidate",
    "validation_rule": "validation_rule_candidate",
}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _proposal_title(case: LearningShadowEvalCase) -> str:
    label = case.target_learning_loop.replace("_", " ")
    return f"Draft {label} change for {case.source_kind}"


def _recommendation(case: LearningShadowEvalCase) -> str:
    if case.target_owner != "LawFirm-os-intake":
        return "hold_for_owning_repo"
    if len(case.support_refs) < 2:
        return "needs_more_evidence"
    return "draft_for_human_review"


def _rationale(case: LearningShadowEvalCase) -> list[str]:
    rationale = [
        "The upstream reviewed-learning gate supplied source-bound support refs.",
        "The shadow-eval case declares fixture updates, eval suites, and regression guardrails.",
        "The artifact is useful review input only; it does not apply or promote a change.",
    ]
    if case.target_owner != "LawFirm-os-intake":
        rationale.append(
            f"Target owner {case.target_owner} must review before any implementation or promotion."
        )
    return rationale


def _red_team_notes(case: LearningShadowEvalCase) -> list[LearningProposedChangeRedTeamNote]:
    notes = [
        LearningProposedChangeRedTeamNote(
            note_id=_stable_id("redteam", f"{case.shadow_eval_case_id}|evidence"),
            severity="high",
            risk_area="evidence",
            objection=(
                "The source signal may reflect a single correction, rejection, or variance rather "
                "than a durable rule."
            ),
            required_check=(
                "Require reviewed outcome evidence and at least one synthetic counterfactual before "
                "promotion."
            ),
        ),
        LearningProposedChangeRedTeamNote(
            note_id=_stable_id("redteam", f"{case.shadow_eval_case_id}|authority"),
            severity="high",
            risk_area="authority",
            objection=(
                "This repo is a vertical candidate surface and cannot authorize canon, runtime, "
                "Lake, guideline, or connector changes."
            ),
            required_check="Route owning-repo review and promotion through the authority map.",
        ),
    ]
    if case.target_learning_loop in {
        "budget_model",
        "staffing_leverage",
        "timekeeper_rate",
        "preapproval_gate",
    }:
        notes.append(
            LearningProposedChangeRedTeamNote(
                note_id=_stable_id("redteam", f"{case.shadow_eval_case_id}|math"),
                severity="high",
                risk_area="math",
                objection=(
                    "Budget math may overfit a human edit or actual-cost outlier if uncertainty, "
                    "resolution path, staffing leverage, and carrier caps are not replayed."
                ),
                required_check=(
                    "Run baseline-versus-proposed math replay with no invented rates and no "
                    "submission authorization."
                ),
            )
        )
    if case.target_learning_loop in {
        "guideline_drift",
        "appeal_success_or_failure",
        "preapproval_gate",
    }:
        notes.append(
            LearningProposedChangeRedTeamNote(
                note_id=_stable_id("redteam", f"{case.shadow_eval_case_id}|carrier"),
                severity="medium",
                risk_area="carrier_guideline",
                objection=(
                    "Carrier-specific behavior may be negotiated, matter-specific, stale, or "
                    "appeal-dependent."
                ),
                required_check=(
                    "Keep proposed firm math separate from carrier-compliant projection and explain "
                    "the delta."
                ),
            )
        )
    if case.target_learning_loop in {
        "template_mapping",
        "parser_rule",
        "capture_completeness",
        "narrative_rule",
    }:
        notes.append(
            LearningProposedChangeRedTeamNote(
                note_id=_stable_id("redteam", f"{case.shadow_eval_case_id}|workflow"),
                severity="medium",
                risk_area="workflow",
                objection=(
                    "A parsing or mapping change could make source noise look like observed fact or "
                    "hide missing source coverage."
                ),
                required_check=(
                    "Replay source refs, offsets, hashes, duplicate handling, and prompt-injection "
                    "as data."
                ),
            )
        )
    return notes


def _artifact_for_case(
    *,
    case: LearningShadowEvalCase,
    shadow_eval_plan: LearningShadowEvalPlan,
    promotion_readiness_report: LearningPromotionReadinessReport | None,
) -> LearningProposedChangeArtifact:
    return LearningProposedChangeArtifact(
        proposed_change_id=_stable_id("proposedchange", case.shadow_eval_case_id),
        reviewed_learning_gate_report_id=shadow_eval_plan.reviewed_learning_gate_report_id,
        shadow_eval_plan_id=shadow_eval_plan.shadow_eval_plan_id,
        shadow_eval_case_id=case.shadow_eval_case_id,
        promotion_readiness_report_id=(
            promotion_readiness_report.promotion_readiness_report_id
            if promotion_readiness_report
            else None
        ),
        candidate_id=case.candidate_id,
        source_kind=case.source_kind,
        target_learning_loop=case.target_learning_loop,
        target_owner=case.target_owner,
        change_type=CHANGE_TYPE_BY_LOOP[case.target_learning_loop],
        source_artifact_ref=case.source_artifact_ref,
        source_record_id=case.source_record_id,
        support_refs=case.support_refs,
        affected_candidate_refs=[case.candidate_id],
        proposal_title=_proposal_title(case),
        proposed_behavior_summary=(
            f"Draft a candidate {case.target_learning_loop} behavior change for human review "
            f"based on {case.source_kind}; no change is applied."
        ),
        recommendation=_recommendation(case),  # type: ignore[arg-type]
        recommendation_rationale=_rationale(case),
        red_team_notes=_red_team_notes(case),
        required_fixture_updates=case.required_fixture_updates,
        required_eval_suites=case.required_eval_suites,
        regression_guardrails=case.regression_guardrails,
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def build_learning_proposed_change_set(
    *,
    shadow_eval_plan: LearningShadowEvalPlan,
    shadow_eval_plan_ref: str,
    promotion_readiness_report: LearningPromotionReadinessReport | None = None,
    promotion_readiness_report_ref: str | None = None,
) -> LearningProposedChangeSet:
    if promotion_readiness_report is not None:
        if promotion_readiness_report.shadow_eval_plan_id != shadow_eval_plan.shadow_eval_plan_id:
            raise ValueError("promotion readiness report does not match shadow eval plan")
        if (
            promotion_readiness_report.reviewed_learning_gate_report_id
            != shadow_eval_plan.reviewed_learning_gate_report_id
        ):
            raise ValueError("promotion readiness report does not match reviewed learning gate")

    changes = [
        _artifact_for_case(
            case=case,
            shadow_eval_plan=shadow_eval_plan,
            promotion_readiness_report=promotion_readiness_report,
        )
        for case in shadow_eval_plan.cases
    ]
    if shadow_eval_plan.status == "failed":
        status = "failed"
    elif changes:
        status = "draft_candidates_ready_for_human_review"
    else:
        status = "no_learning_candidates"

    return LearningProposedChangeSet(
        proposed_change_set_id=new_id("learningproposedchanges"),
        reviewed_learning_gate_report_id=shadow_eval_plan.reviewed_learning_gate_report_id,
        shadow_eval_plan_id=shadow_eval_plan.shadow_eval_plan_id,
        promotion_readiness_report_id=(
            promotion_readiness_report.promotion_readiness_report_id
            if promotion_readiness_report
            else None
        ),
        status=status,  # type: ignore[arg-type]
        source_shadow_eval_plan_ref=shadow_eval_plan_ref,
        source_promotion_readiness_report_ref=promotion_readiness_report_ref,
        change_count=len(changes),
        target_learning_loops=sorted({change.target_learning_loop for change in changes}),
        target_owners=sorted({change.target_owner for change in changes}),
        changes=changes,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_learning_proposed_change_set(change_set: LearningProposedChangeSet) -> str:
    lines = [
        "# Learning Proposed Change Set",
        "",
        f"**Change set ID:** {change_set.proposed_change_set_id}",
        f"**Status:** {change_set.status}",
        f"**Change count:** {change_set.change_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {change_set.candidate_only}",
        f"- Non-authoritative: {change_set.non_authoritative}",
        f"- Promotion authorized: {change_set.promotion_authorized}",
        f"- Proposed changes applied: {change_set.proposed_changes_applied}",
        f"- Baseline mutated: {change_set.baseline_mutated}",
        f"- Lake write performed: {change_set.lake_write_performed}",
        f"- SQLite write performed: {change_set.sqlite_write_performed}",
        f"- External writes performed: {change_set.external_writes_performed}",
        f"- Silent learning performed: {change_set.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in change_set.required_next_gates),
        "",
        "## Draft Changes",
        "",
    ]
    if not change_set.changes:
        lines.append("- none")
    for change in change_set.changes:
        lines.extend(
            [
                f"- `{change.proposed_change_id}`: {change.proposal_title}",
                f"  Recommendation: {change.recommendation}",
                "  Why:",
                *(f"  - {item}" for item in change.recommendation_rationale),
                "  Red-team objections:",
                *(
                    f"  - [{note.severity}/{note.risk_area}] {note.objection} "
                    f"Check: {note.required_check}"
                    for note in change.red_team_notes
                ),
                "  Required eval suites:",
                *(f"  - {item}" for item in change.required_eval_suites),
                "  Support refs:",
                *(f"  - {item}" for item in change.support_refs),
            ]
        )
    lines.extend(
        [
            "",
            "These draft changes are reviewer notes and eval inputs only. They do not mutate budgets, profiles, templates, carrier guidelines, Lake records, SQLite, connectors, or canon.",
            "",
        ]
    )
    return "\n".join(lines)


def run_learning_proposed_changes(
    *,
    shadow_eval_plan_path: str | Path,
    out_dir: str | Path,
    promotion_readiness_report_path: str | Path | None = None,
) -> tuple[LearningProposedChangeSet, Path]:
    plan_path = Path(shadow_eval_plan_path)
    shadow_eval_plan = LearningShadowEvalPlan.model_validate(load_json(plan_path))
    promotion_readiness_report = None
    promotion_ref = None
    if promotion_readiness_report_path is not None:
        promotion_path = Path(promotion_readiness_report_path)
        promotion_readiness_report = LearningPromotionReadinessReport.model_validate(
            load_json(promotion_path)
        )
        promotion_ref = str(promotion_path)

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    change_set = build_learning_proposed_change_set(
        shadow_eval_plan=shadow_eval_plan,
        shadow_eval_plan_ref=str(plan_path),
        promotion_readiness_report=promotion_readiness_report,
        promotion_readiness_report_ref=promotion_ref,
    )

    change_set_path = run_dir / LEARNING_PROPOSED_CHANGE_SET_FILENAME
    notes_path = run_dir / LEARNING_PROPOSED_CHANGE_SET_NOTES_FILENAME
    changes_path = run_dir / LEARNING_PROPOSED_CHANGES_FILENAME
    write_json(change_set_path, change_set.model_dump(mode="json"))
    notes_path.write_text(render_learning_proposed_change_set(change_set), encoding="utf-8")
    changes_path.touch()
    for change in change_set.changes:
        append_jsonl(changes_path, change.model_dump(mode="json"))
    return change_set, run_dir
