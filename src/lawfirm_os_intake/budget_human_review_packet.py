from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetActualComparisonReport,
    BudgetHumanReviewDecisionTemplate,
    BudgetHumanReviewPacket,
    BudgetHumanReviewPacketCheck,
    BudgetHumanReviewRecommendation,
    BudgetHumanReviewRedTeamNote,
    BudgetLifecycleAuditReport,
    BudgetRevisionReport,
    CarrierRejectionLearningReport,
    CarrierRejectionReviewPacket,
)
from .util import digest_text, load_json, now_iso, write_json


BUDGET_HUMAN_REVIEW_PACKET_FILENAME = "budget_human_review_packet.json"
BUDGET_HUMAN_REVIEW_NOTES_FILENAME = "budget_human_review_packet.md"
BUDGET_HUMAN_REVIEW_DECISION_TEMPLATES_FILENAME = "budget_human_review_decision_templates.json"

BUDGET_HUMAN_REVIEW_REQUIRED_NEXT_GATES = [
    "append_only_human_budget_decision",
    "orchestrator_human_pause_before_external_action",
    "exception_lake_owner_review_before_admission",
    "reviewed_learning_gate_before_mutation",
    "no_budget_or_appeal_submission_from_intake",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> BudgetHumanReviewPacketCheck:
    return BudgetHumanReviewPacketCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _optional_check(
    *,
    check_id: str,
    path: str | Path | None,
    loaded: object | None,
    message: str,
) -> BudgetHumanReviewPacketCheck:
    if path is None:
        return BudgetHumanReviewPacketCheck(
            check_id=check_id,
            status="warning",
            message=f"{message} Optional source was not supplied.",
            artifact_refs=[],
            blocking_refs=[],
        )
    return _check(
        check_id,
        loaded is not None,
        message,
        artifact_refs=[str(path)],
    )


def _load_optional(path: str | Path | None, model: type) -> object | None:
    if path is None:
        return None
    report_path = Path(path)
    if not report_path.exists():
        return None
    return model.model_validate(load_json(report_path))


def _lifecycle_boundary_clear(report: BudgetLifecycleAuditReport) -> bool:
    return (
        report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.billing_connector_read_performed is False
        and report.billing_connector_write_performed is False
        and report.carrier_portal_write_performed is False
        and report.email_send_performed is False
        and report.appeal_submission_performed is False
        and report.budget_submission_performed is False
        and report.budget_mutation_performed is False
        and report.profile_mutation_performed is False
        and report.template_mutation_performed is False
        and report.carrier_guideline_mutation_performed is False
        and report.silent_learning_performed is False
    )


def _optional_refs(
    *,
    lifecycle_ref: str,
    budget_revision_report_path: str | Path | None,
    budget_actual_comparison_report_path: str | Path | None,
    carrier_rejection_review_packet_path: str | Path | None,
    carrier_rejection_learning_report_path: str | Path | None,
) -> dict[str, list[str]]:
    refs = {
        "overall": [lifecycle_ref],
        "budget_revision": [lifecycle_ref],
        "actual_variance": [lifecycle_ref],
        "carrier_rejection": [lifecycle_ref],
        "appeal_result": [lifecycle_ref],
        "lake_handoff": [lifecycle_ref],
        "learning_loop": [lifecycle_ref],
        "authority_boundary": [lifecycle_ref],
    }
    if budget_revision_report_path is not None:
        refs["budget_revision"].append(str(budget_revision_report_path))
    if budget_actual_comparison_report_path is not None:
        refs["actual_variance"].append(str(budget_actual_comparison_report_path))
    if carrier_rejection_review_packet_path is not None:
        refs["carrier_rejection"].append(str(carrier_rejection_review_packet_path))
        refs["appeal_result"].append(str(carrier_rejection_review_packet_path))
    if carrier_rejection_learning_report_path is not None:
        refs["learning_loop"].append(str(carrier_rejection_learning_report_path))
    return refs


def _recommendation(
    *,
    lifecycle: BudgetLifecycleAuditReport,
    area: str,
    action: str,
    priority: str,
    why: list[str],
    source_refs: list[str],
    financial_impact: float | None = None,
    candidate_record_families: list[str] | None = None,
) -> BudgetHumanReviewRecommendation:
    return BudgetHumanReviewRecommendation(
        recommendation_id=_stable_id(
            "budgethumanreviewrec",
            "|".join([lifecycle.lifecycle_audit_report_id, area, action, *why]),
        ),
        review_area=area,  # type: ignore[arg-type]
        recommended_action=action,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        why=why,
        source_artifact_refs=source_refs,
        required_human_decisions=lifecycle.required_human_decisions,
        proposed_next_actions=lifecycle.proposed_next_actions,
        financial_impact=_money(financial_impact),
        candidate_record_families=candidate_record_families or [],
    )


def _build_recommendations(
    *,
    lifecycle: BudgetLifecycleAuditReport,
    refs: dict[str, list[str]],
) -> list[BudgetHumanReviewRecommendation]:
    if lifecycle.status != "ready_for_budget_lifecycle_review":
        return []
    financial = lifecycle.financial_summary
    recommendations = [
        _recommendation(
            lifecycle=lifecycle,
            area="authority_boundary",
            action="block_submission",
            priority="critical",
            why=[
                "Budget lifecycle evidence is review-ready, but intake has no authority to submit a budget, submit an appeal, write billing, or admit Lake records.",
                "The next action is a human review decision plus Orchestrator/Lake owner review before any external action.",
            ],
            source_refs=refs["authority_boundary"],
        )
    ]
    if lifecycle.human_budget_change_event_count:
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="budget_revision",
                action="correct_budget"
                if (financial.human_revision_total_delta or 0) != 0
                else "confirm_no_change",
                priority="high",
                why=[
                    f"{lifecycle.human_budget_change_event_count} append-only human budget change event(s) are present.",
                    "A reviewer should confirm whether the revised candidate remains the intended comparison point before any later actuals or carrier-facing review.",
                ],
                source_refs=refs["budget_revision"],
                financial_impact=financial.human_revision_total_delta,
                candidate_record_families=["budget_human_change_record"],
            )
        )
    if lifecycle.actual_variance_review_event_count:
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="actual_variance",
                action="request_more_information",
                priority="high",
                why=[
                    f"{lifecycle.actual_variance_review_event_count} actual-variance event(s) require review.",
                    "A reviewer should confirm the scenario, actuals coverage, and variance driver before using the variance as learning pressure.",
                ],
                source_refs=refs["actual_variance"],
                financial_impact=financial.actual_variance_amount,
                candidate_record_families=["budget_actual_variance_record"],
            )
        )
    if lifecycle.carrier_pending_decision_event_count:
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="carrier_rejection",
                action="appeal"
                if financial.carrier_disputed_amount > 0
                else "request_more_information",
                priority="high",
                why=[
                    f"{lifecycle.carrier_pending_decision_event_count} carrier rejection/fix/appeal decision event(s) remain pending.",
                    "A human should decide whether to appeal, correct and resubmit, accept a write-down, or request more information.",
                ],
                source_refs=refs["carrier_rejection"],
                financial_impact=financial.carrier_disputed_amount,
                candidate_record_families=["carrier_rejection_decision_record"],
            )
        )
    if (
        lifecycle.carrier_appeal_result_event_count
        or lifecycle.carrier_financial_outcome_event_count
    ):
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="appeal_result",
                action="accept_write_down"
                if financial.carrier_write_down_amount > 0
                else "confirm_no_change",
                priority="medium",
                why=[
                    "Carrier appeal result or financial outcome evidence is present.",
                    "Recovered and write-down amounts should be reviewed before the result becomes Lake evidence or learning pressure.",
                ],
                source_refs=refs["appeal_result"],
                financial_impact=financial.carrier_write_down_amount,
                candidate_record_families=["carrier_financial_outcome_record"],
            )
        )
    if lifecycle.candidate_record_families:
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="lake_handoff",
                action="route_to_owner_review",
                priority="high",
                why=[
                    "Candidate Exception Lake record families are present, but intake cannot admit them.",
                    "Exception Lake owner review must validate idempotency, append-only storage, record hashes, and supersession behavior.",
                ],
                source_refs=refs["lake_handoff"],
                candidate_record_families=lifecycle.candidate_record_families,
            )
        )
    if lifecycle.local_event_labels:
        recommendations.append(
            _recommendation(
                lifecycle=lifecycle,
                area="learning_loop",
                action="no_learning_change",
                priority="high",
                why=[
                    "Local event labels and lifecycle pressure may inform future learning candidates.",
                    "No profile, template, budget, carrier guideline, or validation rule may change without reviewed outcome evidence, shadow eval, and owning-repo review.",
                ],
                source_refs=refs["learning_loop"],
                candidate_record_families=lifecycle.candidate_record_families,
            )
        )
    return recommendations


def _red_team_notes(
    *,
    lifecycle: BudgetLifecycleAuditReport,
    refs: dict[str, list[str]],
    carrier_review: CarrierRejectionReviewPacket | None,
) -> list[BudgetHumanReviewRedTeamNote]:
    notes = [
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|authority"
            ),
            severity="critical",
            scope="authority_boundary",
            message="A consolidated human packet can look like approval if the no-action boundary is not checked.",
            recommended_check="Confirm no budget submission, appeal submission, Lake/SQLite write, billing write, profile mutation, template mutation, or silent learning occurred.",
            artifact_refs=refs["authority_boundary"],
        ),
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|proposed-compliant"
            ),
            severity="high",
            scope="proposed_vs_compliant_collapse",
            message="Carrier-compliant projection deltas must not overwrite the proposed firm budget.",
            recommended_check="Verify proposed-vs-compliant totals and deltas remain visible and any guideline effects have reasons.",
            artifact_refs=refs["overall"],
        ),
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|scenario"
            ),
            severity="high",
            scope="scenario_variance_mismatch",
            message="Actual variance can be misleading when compared against the wrong resolution path or scenario.",
            recommended_check="Confirm actual_resolution_scenario_id or explain why the standard scenario remains the correct comparator.",
            artifact_refs=refs["actual_variance"],
        ),
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|math"
            ),
            severity="high",
            scope="financial_math",
            message="Human revisions, actual variance, disputed amounts, recovered amounts, and write-downs must reconcile before any Lake or learning handoff.",
            recommended_check="Review financial_summary totals against the source ledgers and any optional source reports.",
            artifact_refs=refs["overall"],
        ),
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|learning"
            ),
            severity="high",
            scope="learning_loop_mutation",
            message="Budget, rejection, appeal, and actuals outcomes can create useful learning pressure but must not silently mutate rules or profiles.",
            recommended_check="Require append-only reviewed outcome evidence, proposed changes, fixture updates, shadow eval, and owning-repo approval.",
            artifact_refs=refs["learning_loop"],
        ),
        BudgetHumanReviewRedTeamNote(
            note_id=_stable_id(
                "budgethumanreviewrt", f"{lifecycle.lifecycle_audit_report_id}|source"
            ),
            severity="medium",
            scope="source_coverage",
            message="A lifecycle packet is only as good as the source coverage in each underlying ledger.",
            recommended_check="Check missing actuals, unlinked notices, parser failures, and source artifact hashes before relying on recommendations.",
            artifact_refs=refs["overall"],
        ),
    ]
    if carrier_review and carrier_review.duplicate_notice_count:
        notes.append(
            BudgetHumanReviewRedTeamNote(
                note_id=_stable_id(
                    "budgethumanreviewrt",
                    f"{lifecycle.lifecycle_audit_report_id}|duplicate-rejections",
                ),
                severity="high",
                scope="duplicate_rejection",
                message="Duplicate carrier notices can double-count rejected dollars, deadlines, or appeal obligations.",
                recommended_check="Verify duplicate notices collapse to one logical rejection with multiple evidence refs.",
                artifact_refs=refs["carrier_rejection"],
            )
        )
    return notes


def _decision_templates(
    recommendations: list[BudgetHumanReviewRecommendation],
) -> list[BudgetHumanReviewDecisionTemplate]:
    templates: list[BudgetHumanReviewDecisionTemplate] = []
    for recommendation in recommendations:
        allowed = [
            "confirm",
            "correct",
            "unknown",
            "needs_more_information",
            "human_only",
            "declined_referred",
            "block",
        ]
        recommended_outcome = "confirm"
        required_fields = [
            "reviewer_id",
            "reviewed_at",
            "outcome",
            "decision_reason",
            "evidence_refs",
        ]
        if recommendation.recommended_action == "appeal":
            allowed.extend(["appeal", "write_off", "reopen"])
            recommended_outcome = "appeal"
            required_fields.extend(["followup_owner", "followup_due_at"])
        elif recommendation.recommended_action == "accept_write_down":
            allowed.extend(["write_off", "reopen"])
            recommended_outcome = "write_off"
        elif recommendation.recommended_action == "no_learning_change":
            allowed.extend(["no_learning_change", "route_to_owner_review"])
            recommended_outcome = "no_learning_change"
        elif recommendation.recommended_action == "route_to_owner_review":
            allowed.append("route_to_owner_review")
            recommended_outcome = "route_to_owner_review"
        elif recommendation.recommended_action == "request_more_information":
            recommended_outcome = "needs_more_information"
        elif recommendation.recommended_action == "block_submission":
            recommended_outcome = "block"
        elif recommendation.recommended_action == "correct_budget":
            recommended_outcome = "correct"
        elif recommendation.recommended_action == "confirm_no_change":
            allowed.append("no_change")
            recommended_outcome = "no_change"
        templates.append(
            BudgetHumanReviewDecisionTemplate(
                template_id=_stable_id(
                    "budgethumanreviewtemplate",
                    f"{recommendation.recommendation_id}|{recommendation.review_area}",
                ),
                review_area=recommendation.review_area,
                source_recommendation_ids=[recommendation.recommendation_id],
                allowed_outcomes=sorted(set(allowed)),  # type: ignore[arg-type]
                recommended_outcome=recommended_outcome,  # type: ignore[arg-type]
                required_fields=required_fields,
            )
        )
    return templates


def build_budget_human_review_packet(
    *,
    budget_lifecycle_audit_report_path: str | Path,
    budget_revision_report_path: str | Path | None = None,
    budget_actual_comparison_report_path: str | Path | None = None,
    carrier_rejection_review_packet_path: str | Path | None = None,
    carrier_rejection_learning_report_path: str | Path | None = None,
) -> BudgetHumanReviewPacket:
    lifecycle_path = Path(budget_lifecycle_audit_report_path)
    lifecycle = BudgetLifecycleAuditReport.model_validate(load_json(lifecycle_path))
    budget_revision = _load_optional(budget_revision_report_path, BudgetRevisionReport)
    actuals = _load_optional(budget_actual_comparison_report_path, BudgetActualComparisonReport)
    carrier_review = _load_optional(
        carrier_rejection_review_packet_path,
        CarrierRejectionReviewPacket,
    )
    learning = _load_optional(
        carrier_rejection_learning_report_path,
        CarrierRejectionLearningReport,
    )
    refs = _optional_refs(
        lifecycle_ref=str(lifecycle_path),
        budget_revision_report_path=budget_revision_report_path,
        budget_actual_comparison_report_path=budget_actual_comparison_report_path,
        carrier_rejection_review_packet_path=carrier_rejection_review_packet_path,
        carrier_rejection_learning_report_path=carrier_rejection_learning_report_path,
    )
    checks = [
        _check(
            "budget_lifecycle_audit_ready_without_writes",
            lifecycle.status == "ready_for_budget_lifecycle_review"
            and _lifecycle_boundary_clear(lifecycle),
            "Budget lifecycle audit is ready and preserves no-write/no-submission boundaries.",
            artifact_refs=[str(lifecycle_path)],
        ),
        _check(
            "budget_lifecycle_has_review_content",
            lifecycle.pending_human_decision_count > 0
            or lifecycle.total_lifecycle_event_count > 0
            or bool(lifecycle.proposed_next_actions),
            "Budget lifecycle audit has human-review content.",
            artifact_refs=[str(lifecycle_path)],
        ),
        _optional_check(
            check_id="optional_budget_revision_report_loaded",
            path=budget_revision_report_path,
            loaded=budget_revision,
            message="Optional budget revision report is schema-valid when supplied.",
        ),
        _optional_check(
            check_id="optional_budget_actual_comparison_report_loaded",
            path=budget_actual_comparison_report_path,
            loaded=actuals,
            message="Optional budget actual comparison report is schema-valid when supplied.",
        ),
        _optional_check(
            check_id="optional_carrier_rejection_review_packet_loaded",
            path=carrier_rejection_review_packet_path,
            loaded=carrier_review,
            message="Optional carrier rejection review packet is schema-valid when supplied.",
        ),
        _optional_check(
            check_id="optional_carrier_rejection_learning_report_loaded",
            path=carrier_rejection_learning_report_path,
            loaded=learning,
            message="Optional carrier rejection learning report is schema-valid when supplied.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    recommendations = _build_recommendations(lifecycle=lifecycle, refs=refs)
    red_team_notes = _red_team_notes(
        lifecycle=lifecycle,
        refs=refs,
        carrier_review=carrier_review
        if isinstance(carrier_review, CarrierRejectionReviewPacket)
        else None,
    )
    templates = _decision_templates(recommendations)
    status = (
        "blocked_by_lifecycle_audit"
        if failed_checks or lifecycle.status != "ready_for_budget_lifecycle_review"
        else "ready_for_human_budget_review"
    )
    sections = sorted(
        {recommendation.review_area for recommendation in recommendations}
        | {"overall", "authority_boundary"}
    )
    return BudgetHumanReviewPacket(
        budget_human_review_packet_id=_stable_id(
            "budgethumanreviewpacket",
            "|".join(
                [
                    lifecycle.lifecycle_audit_report_id,
                    lifecycle.status,
                    str(lifecycle.budget_proposal_id),
                    str(lifecycle.preflight_packet_id),
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_budget_lifecycle_audit_report_id=lifecycle.lifecycle_audit_report_id,
        source_budget_lifecycle_audit_report_ref=str(lifecycle_path),
        source_budget_lifecycle_audit_status=lifecycle.status,
        source_budget_revision_report_ref=(
            str(budget_revision_report_path) if budget_revision_report_path else None
        ),
        source_budget_actual_comparison_report_ref=(
            str(budget_actual_comparison_report_path)
            if budget_actual_comparison_report_path
            else None
        ),
        source_carrier_rejection_review_packet_ref=(
            str(carrier_rejection_review_packet_path)
            if carrier_rejection_review_packet_path
            else None
        ),
        source_carrier_rejection_learning_report_ref=(
            str(carrier_rejection_learning_report_path)
            if carrier_rejection_learning_report_path
            else None
        ),
        budget_proposal_id=lifecycle.budget_proposal_id,
        preflight_packet_id=lifecycle.preflight_packet_id,
        run_ids=lifecycle.run_ids,
        financial_summary=lifecycle.financial_summary,
        pending_human_decision_count=lifecycle.pending_human_decision_count,
        required_human_decisions=lifecycle.required_human_decisions,
        proposed_next_actions=lifecycle.proposed_next_actions,
        candidate_record_families=lifecycle.candidate_record_families,
        local_event_labels=lifecycle.local_event_labels,
        required_review_sections=sections,  # type: ignore[arg-type]
        recommendations=recommendations,
        red_team_notes=red_team_notes,
        decision_templates=templates,
        checks=checks,
        required_next_gates=BUDGET_HUMAN_REVIEW_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_human_review_packet(packet: BudgetHumanReviewPacket) -> str:
    financial = packet.financial_summary
    lines = [
        "# Budget Human Review Packet",
        "",
        f"**Packet ID:** {packet.budget_human_review_packet_id}",
        f"**Status:** {packet.status}",
        f"**Budget proposal:** {packet.budget_proposal_id or 'not supplied'}",
        f"**Preflight packet:** {packet.preflight_packet_id or 'not supplied'}",
        f"**Lifecycle audit:** `{packet.source_budget_lifecycle_audit_report_ref}`",
        "",
        "## Financial Summary",
        "",
        f"- Original budget total: {financial.original_budget_total}",
        f"- Human revision delta: {financial.human_revision_total_delta}",
        f"- Human revised candidate total: {financial.human_revised_candidate_total}",
        f"- Actual comparison budgeted total: {financial.actual_comparison_budgeted_total}",
        f"- Actual total: {financial.actual_total}",
        f"- Actual variance amount: {financial.actual_variance_amount}",
        f"- Carrier disputed amount: {financial.carrier_disputed_amount}",
        f"- Carrier recovered amount: {financial.carrier_recovered_amount}",
        f"- Carrier write-down amount: {financial.carrier_write_down_amount}",
        "",
        "## Recommendations",
        "",
    ]
    if not packet.recommendations:
        lines.append("- No recommendations emitted because the lifecycle audit is blocked.")
    for recommendation in packet.recommendations:
        lines.append(
            f"- {recommendation.review_area}: {recommendation.recommended_action} "
            f"({recommendation.priority})"
        )
        for why in recommendation.why:
            lines.append(f"  - Why: {why}")
        if recommendation.financial_impact is not None:
            lines.append(f"  - Financial impact: {recommendation.financial_impact}")
    lines.extend(["", "## Red-Team Notes", ""])
    for note in packet.red_team_notes:
        lines.append(f"- {note.scope}: {note.severity}; {note.message}")
        lines.append(f"  - Check: {note.recommended_check}")
    lines.extend(["", "## Decision Templates", ""])
    for template in packet.decision_templates:
        lines.append(
            f"- {template.review_area}: recommended `{template.recommended_outcome}`; "
            f"allowed {', '.join(template.allowed_outcomes)}"
        )
    lines.extend(["", "## Checks", ""])
    for check in packet.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Lake write performed: {packet.lake_write_performed}",
            f"- SQLite write performed: {packet.sqlite_write_performed}",
            f"- External writes performed: {packet.external_writes_performed}",
            f"- Budget submission performed: {packet.budget_submission_performed}",
            f"- Appeal submission performed: {packet.appeal_submission_performed}",
            f"- Budget mutation performed: {packet.budget_mutation_performed}",
            f"- Carrier guideline mutation performed: {packet.carrier_guideline_mutation_performed}",
            f"- Silent learning performed: {packet.silent_learning_performed}",
            "",
            "This packet is review evidence only. It does not submit a budget or appeal, write billing, admit Lake/SQLite records, mutate profiles/templates/budgets/guidelines, write sibling repos, promote canon, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_human_review_packet(
    *,
    budget_lifecycle_audit_report_path: str | Path,
    out_dir: str | Path,
    budget_revision_report_path: str | Path | None = None,
    budget_actual_comparison_report_path: str | Path | None = None,
    carrier_rejection_review_packet_path: str | Path | None = None,
    carrier_rejection_learning_report_path: str | Path | None = None,
) -> tuple[BudgetHumanReviewPacket, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = build_budget_human_review_packet(
        budget_lifecycle_audit_report_path=budget_lifecycle_audit_report_path,
        budget_revision_report_path=budget_revision_report_path,
        budget_actual_comparison_report_path=budget_actual_comparison_report_path,
        carrier_rejection_review_packet_path=carrier_rejection_review_packet_path,
        carrier_rejection_learning_report_path=carrier_rejection_learning_report_path,
    )
    write_json(run_dir / BUDGET_HUMAN_REVIEW_PACKET_FILENAME, packet.model_dump(mode="json"))
    write_json(
        run_dir / BUDGET_HUMAN_REVIEW_DECISION_TEMPLATES_FILENAME,
        [template.model_dump(mode="json") for template in packet.decision_templates],
    )
    (run_dir / BUDGET_HUMAN_REVIEW_NOTES_FILENAME).write_text(
        render_budget_human_review_packet(packet),
        encoding="utf-8",
    )
    return packet, run_dir
