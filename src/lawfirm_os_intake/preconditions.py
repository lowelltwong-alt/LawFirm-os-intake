from __future__ import annotations

from .models import (
    BudgetPreconditionCheck,
    BudgetPreconditionReport,
    EvidenceRef,
    HumanConfirmation,
    IntakePreflightPacket,
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentExecutableDriverImpactReport,
    MatterLinkingClusterReport,
    MatterLinkingClusterReviewOutcomeReport,
)
from .util import new_id, now_iso


PROHIBITED_PRECONDITION_FAILURE_OUTPUTS = [
    "conflict_search_seed_packet",
    "legal_budget_proposal",
    "legal_budget_review_form",
    "matter_opening_readiness",
    "matter_opening_review_package",
    "review_package_manifest",
    "safety_gate_report",
]


def _check(
    check_id: str,
    ok: bool,
    message: str,
    evidence_refs: list[str],
) -> BudgetPreconditionCheck:
    return BudgetPreconditionCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence_refs=evidence_refs,
    )


def build_budget_precondition_report(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    input_refs: list[str],
    human_review_outcome_ref: str | None = None,
    labor_employment_budget_fact_report: LaborEmploymentBudgetFactAuditReport | None = None,
    labor_employment_budget_fact_report_ref: str | None = None,
    labor_employment_driver_impact_report: (
        LaborEmploymentExecutableDriverImpactReport | None
    ) = None,
    labor_employment_driver_impact_report_ref: str | None = None,
    matter_linking_cluster_report: MatterLinkingClusterReport | None = None,
    matter_linking_cluster_report_ref: str | None = None,
    matter_linking_cluster_review_outcome_report: (
        MatterLinkingClusterReviewOutcomeReport | None
    ) = None,
    matter_linking_cluster_review_outcome_report_ref: str | None = None,
) -> BudgetPreconditionReport:
    confirmation_ref = f"human-confirmation://{confirmation.confirmation_id}"
    packet_ref = f"intake-preflight-packet://{packet.packet_id}"
    confirmed_status = confirmation.status == "confirmed"
    party_evidence_refs = [
        ref for party in confirmation.confirmed_parties for ref in party.evidence_refs
    ]
    all_confirmation_refs = confirmation.decision_evidence_refs + party_evidence_refs
    checks = [
        _check(
            "preflight_requires_human_review",
            packet.status == "human_intake_review_required"
            and packet.human_confirmation_required is True,
            "Preflight packet is in the human-review-required state.",
            [packet_ref],
        ),
        _check(
            "confirmation_matches_preflight_packet",
            confirmation.preflight_packet_id == packet.packet_id,
            "Human confirmation must bind to the exact preflight packet.",
            [packet_ref, confirmation_ref],
        ),
        _check(
            "confirmation_status_confirmed",
            confirmed_status,
            "Budget generation requires confirmation status to be confirmed.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_matter_family_present",
            bool(confirmation.confirmed_matter_family),
            "Budget generation requires a human-confirmed matter family.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_representation_posture_present",
            bool(confirmation.confirmed_representation_posture),
            "Budget generation requires a human-confirmed representation posture.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_principal_party_roles_present",
            bool(confirmation.confirmed_parties),
            "Budget generation requires human-confirmed principal party roles.",
            [confirmation_ref],
        ),
        _check(
            "decision_evidence_refs_present",
            bool(confirmation.decision_evidence_refs),
            "Human confirmation must include source-bound decision evidence refs.",
            [confirmation_ref],
        ),
        _check(
            "confirmed_party_evidence_refs_present",
            bool(confirmation.confirmed_parties)
            and all(party.evidence_refs for party in confirmation.confirmed_parties),
            "Every confirmed party role must include source-bound evidence refs.",
            [confirmation_ref],
        ),
        _check(
            "confirmation_evidence_refs_match_preflight_segments",
            _refs_match_packet_segments(packet, all_confirmation_refs),
            "Confirmation evidence refs must match preflight segment source IDs, offsets, and hashes.",
            [confirmation_ref, packet_ref],
        ),
    ]
    resolved_labor_employment_budget_fact_report_ref = None
    if labor_employment_budget_fact_report is not None:
        resolved_labor_employment_budget_fact_report_ref = (
            labor_employment_budget_fact_report_ref
            or (
                "labor-employment-budget-fact-report://"
                f"{labor_employment_budget_fact_report.labor_employment_budget_fact_audit_report_id}"
            )
        )
        checks.extend(
            [
                _check(
                    "labor_employment_budget_fact_report_ready",
                    labor_employment_budget_fact_report.status
                    == "labor_employment_budget_facts_ready_for_review",
                    "L&E budget fact report must be ready for human fact review.",
                    [resolved_labor_employment_budget_fact_report_ref],
                ),
                _check(
                    "labor_employment_budget_fact_no_critical_gaps",
                    labor_employment_budget_fact_report.budget_readiness_state
                    != "blocked_missing_critical_facts"
                    and labor_employment_budget_fact_report.critical_gap_count == 0,
                    "Critical L&E fact gaps must block amount budget generation.",
                    [resolved_labor_employment_budget_fact_report_ref],
                ),
                _check(
                    "labor_employment_budget_fact_report_no_side_effects",
                    _labor_employment_fact_report_has_no_side_effects(
                        labor_employment_budget_fact_report
                    ),
                    "L&E fact report must be candidate-only and must not claim Lake, SQLite, training, matter-opening, conflict, or submission side effects.",
                    [resolved_labor_employment_budget_fact_report_ref],
                ),
            ]
        )
    resolved_labor_employment_driver_impact_report_ref = None
    if labor_employment_driver_impact_report is not None:
        resolved_labor_employment_driver_impact_report_ref = (
            labor_employment_driver_impact_report_ref
            or (
                "labor-employment-driver-impact-report://"
                f"{labor_employment_driver_impact_report.executable_driver_impact_report_id}"
            )
        )
    resolved_matter_linking_cluster_report_ref = None
    resolved_matter_linking_cluster_review_outcome_report_ref = None
    if (
        matter_linking_cluster_report is not None
        or matter_linking_cluster_review_outcome_report is not None
    ):
        if matter_linking_cluster_report is not None:
            resolved_matter_linking_cluster_report_ref = matter_linking_cluster_report_ref or (
                "matter-linking-cluster-report://"
                f"{matter_linking_cluster_report.matter_linking_cluster_report_id}"
            )
        if matter_linking_cluster_review_outcome_report is not None:
            resolved_matter_linking_cluster_review_outcome_report_ref = (
                matter_linking_cluster_review_outcome_report_ref
                or (
                    "matter-linking-cluster-review-outcome-report://"
                    f"{matter_linking_cluster_review_outcome_report.matter_linking_cluster_review_outcome_report_id}"
                )
            )
        checks.extend(
            [
                _check(
                    "matter_linking_cluster_report_supplied",
                    matter_linking_cluster_report is not None,
                    "Matter-linking cluster report must be supplied when matter-linking review is part of the budget gate.",
                    [ref for ref in [resolved_matter_linking_cluster_report_ref] if ref],
                ),
                _check(
                    "matter_linking_cluster_report_ready",
                    matter_linking_cluster_report is not None
                    and matter_linking_cluster_report.status
                    == "matter_linking_clusters_proposed_for_review"
                    and matter_linking_cluster_report.matter_identity_asserted is False
                    and matter_linking_cluster_report.budget_generation_performed is False
                    and matter_linking_cluster_report.external_writes_performed is False
                    and matter_linking_cluster_report.lake_write_performed is False
                    and matter_linking_cluster_report.sqlite_write_performed is False,
                    "Matter-linking cluster report must be review-only, ready, no-write, and non-authoritative.",
                    [ref for ref in [resolved_matter_linking_cluster_report_ref] if ref],
                ),
                _check(
                    "matter_linking_cluster_review_outcome_supplied",
                    matter_linking_cluster_review_outcome_report is not None,
                    "Budget generation requires a human matter-linking cluster review outcome when clustering evidence is supplied.",
                    [
                        ref
                        for ref in [resolved_matter_linking_cluster_review_outcome_report_ref]
                        if ref
                    ],
                ),
                _check(
                    "matter_linking_cluster_review_matches_cluster_report",
                    matter_linking_cluster_report is not None
                    and matter_linking_cluster_review_outcome_report is not None
                    and matter_linking_cluster_review_outcome_report.matter_linking_cluster_report_id
                    == matter_linking_cluster_report.matter_linking_cluster_report_id,
                    "Matter-linking cluster review outcome must bind to the supplied cluster report.",
                    [
                        ref
                        for ref in [
                            resolved_matter_linking_cluster_report_ref,
                            resolved_matter_linking_cluster_review_outcome_report_ref,
                        ]
                        if ref
                    ],
                ),
                _check(
                    "matter_linking_cluster_review_confirmed_for_budget_scope",
                    matter_linking_cluster_review_outcome_report is not None
                    and matter_linking_cluster_review_outcome_report.status
                    == "matter_linking_cluster_review_confirmed_for_budget_scope"
                    and matter_linking_cluster_review_outcome_report.budget_scope_cluster_count == 1
                    and matter_linking_cluster_review_outcome_report.budget_blocking_cluster_count
                    == 0
                    and matter_linking_cluster_review_outcome_report.unreviewed_cluster_count == 0
                    and matter_linking_cluster_review_outcome_report.unknown_cluster_count == 0,
                    "Budget generation requires exactly one human-confirmed budget-scope cluster with no held, conflicted, unknown, or unreviewed cluster blockers.",
                    [
                        ref
                        for ref in [resolved_matter_linking_cluster_review_outcome_report_ref]
                        if ref
                    ],
                ),
                _check(
                    "matter_linking_cluster_review_no_side_effects",
                    matter_linking_cluster_review_outcome_report is not None
                    and matter_linking_cluster_review_outcome_report.budget_amount_output_authorized
                    is False
                    and matter_linking_cluster_review_outcome_report.budget_submission_authorized
                    is False
                    and matter_linking_cluster_review_outcome_report.conflict_conclusion_emitted
                    is False
                    and matter_linking_cluster_review_outcome_report.matter_opening_authorized
                    is False
                    and matter_linking_cluster_review_outcome_report.lake_write_performed is False
                    and matter_linking_cluster_review_outcome_report.sqlite_write_performed is False
                    and matter_linking_cluster_review_outcome_report.external_writes_performed
                    is False
                    and matter_linking_cluster_review_outcome_report.silent_learning_performed
                    is False,
                    "Matter-linking cluster review must remain append-only and must not authorize budget, matter, conflict, Lake, SQLite, external-write, or learning side effects.",
                    [
                        ref
                        for ref in [resolved_matter_linking_cluster_review_outcome_report_ref]
                        if ref
                    ],
                ),
            ]
        )
    if labor_employment_driver_impact_report is not None:
        checks.extend(
            [
                _check(
                    "labor_employment_driver_impact_report_ready",
                    labor_employment_driver_impact_report.status
                    == "labor_employment_executable_driver_impacts_ready_for_review",
                    "L&E driver impact report must be ready for candidate driver-impact review.",
                    [resolved_labor_employment_driver_impact_report_ref],
                ),
                _check(
                    "labor_employment_driver_impact_no_amount_budget_blocks",
                    labor_employment_driver_impact_report.block_amount_budget_impact_count == 0,
                    "Source-bound L&E driver impacts with amount-budget blockers must block amount budget generation.",
                    [resolved_labor_employment_driver_impact_report_ref],
                ),
                _check(
                    "labor_employment_driver_impact_report_no_side_effects",
                    _labor_employment_driver_impact_report_has_no_side_effects(
                        labor_employment_driver_impact_report
                    ),
                    "L&E driver impact report must be candidate-only and must not claim Lake, SQLite, training, matter-opening, conflict, or submission side effects.",
                    [resolved_labor_employment_driver_impact_report_ref],
                ),
            ]
        )
    failed = [check.check_id for check in checks if check.status == "failed"]
    status = "passed" if not failed else "failed"
    blocked_state = None
    if failed:
        if "labor_employment_driver_impact_no_amount_budget_blocks" in failed:
            blocked_state = "labor_employment_driver_impacts_blocked"
        elif any(check_id.startswith("matter_linking_cluster") for check_id in failed):
            blocked_state = "matter_linking_confirmation_blocked"
        elif "labor_employment_budget_fact_no_critical_gaps" in failed:
            blocked_state = "labor_employment_budget_facts_blocked"
        elif "confirmation_status_confirmed" in failed:
            blocked_state = "budget_blocked_before_human_confirmation"
        elif "confirmation_matches_preflight_packet" in failed:
            blocked_state = "budget_precondition_failed"
        elif any("evidence_refs" in check_id for check_id in failed):
            blocked_state = "budget_confirmation_evidence_missing"
        else:
            blocked_state = "budget_precondition_failed"
    return BudgetPreconditionReport(
        budget_precondition_report_id=new_id("budgetprecondition"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status=status,
        checks=checks,
        blocked_state=blocked_state,
        input_refs=input_refs,
        human_review_outcome_ref=human_review_outcome_ref,
        labor_employment_budget_fact_report_ref=resolved_labor_employment_budget_fact_report_ref,
        labor_employment_budget_readiness_state=(
            labor_employment_budget_fact_report.budget_readiness_state
            if labor_employment_budget_fact_report is not None
            else None
        ),
        labor_employment_budget_treatment=_labor_employment_budget_treatment(
            labor_employment_budget_fact_report
        ),
        labor_employment_critical_gap_count=(
            labor_employment_budget_fact_report.critical_gap_count
            if labor_employment_budget_fact_report is not None
            else 0
        ),
        labor_employment_required_human_questions=(
            labor_employment_budget_fact_report.required_human_questions
            if labor_employment_budget_fact_report is not None
            else []
        ),
        labor_employment_driver_impact_report_ref=(
            resolved_labor_employment_driver_impact_report_ref
        ),
        labor_employment_driver_impact_status=(
            labor_employment_driver_impact_report.status
            if labor_employment_driver_impact_report is not None
            else None
        ),
        labor_employment_driver_allowed_budget_output=(
            _labor_employment_driver_allowed_budget_output(labor_employment_driver_impact_report)
        ),
        labor_employment_driver_block_amount_budget_impact_count=(
            labor_employment_driver_impact_report.block_amount_budget_impact_count
            if labor_employment_driver_impact_report is not None
            else 0
        ),
        labor_employment_driver_range_widening_impact_count=(
            labor_employment_driver_impact_report.range_widening_impact_count
            if labor_employment_driver_impact_report is not None
            else 0
        ),
        labor_employment_driver_scenario_fork_impact_count=(
            labor_employment_driver_impact_report.scenario_fork_impact_count
            if labor_employment_driver_impact_report is not None
            else 0
        ),
        labor_employment_driver_rate_guideline_review_impact_count=(
            labor_employment_driver_impact_report.rate_guideline_review_impact_count
            if labor_employment_driver_impact_report is not None
            else 0
        ),
        labor_employment_driver_max_range_widening_factor=(
            labor_employment_driver_impact_report.max_range_widening_factor
            if labor_employment_driver_impact_report is not None
            else 1.0
        ),
        matter_linking_cluster_report_ref=resolved_matter_linking_cluster_report_ref,
        matter_linking_cluster_review_outcome_report_ref=(
            resolved_matter_linking_cluster_review_outcome_report_ref
        ),
        matter_linking_cluster_review_status=(
            matter_linking_cluster_review_outcome_report.status
            if matter_linking_cluster_review_outcome_report is not None
            else None
        ),
        matter_linking_budget_scope_cluster_ids=(
            matter_linking_cluster_review_outcome_report.budget_scope_cluster_ids
            if matter_linking_cluster_review_outcome_report is not None
            else []
        ),
        matter_linking_budget_blocking_cluster_count=(
            matter_linking_cluster_review_outcome_report.budget_blocking_cluster_count
            if matter_linking_cluster_review_outcome_report is not None
            else 0
        ),
        prohibited_outputs=PROHIBITED_PRECONDITION_FAILURE_OUTPUTS,
        generated_at=now_iso(),
    )


def _labor_employment_fact_report_has_no_side_effects(
    report: LaborEmploymentBudgetFactAuditReport,
) -> bool:
    return (
        report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.matter_opening_authorized is False
        and report.training_pipeline_created is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.candidate_only is True
        and report.non_authoritative is True
    )


def _labor_employment_driver_impact_report_has_no_side_effects(
    report: LaborEmploymentExecutableDriverImpactReport,
) -> bool:
    return (
        report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.matter_opening_authorized is False
        and report.training_pipeline_created is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.candidate_only is True
        and report.non_authoritative is True
    )


def _labor_employment_driver_allowed_budget_output(
    report: LaborEmploymentExecutableDriverImpactReport | None,
) -> str | None:
    if report is None:
        return None
    if report.block_amount_budget_impact_count > 0:
        return "blocked_amount_budget"
    if report.range_widening_impact_count or report.scenario_fork_impact_count:
        return "range_or_hours_only_pending_review"
    if report.rate_guideline_review_impact_count:
        return "candidate_range_after_review_pending_human_review"
    return "candidate_range_after_review_pending_human_review"


def _labor_employment_budget_treatment(
    report: LaborEmploymentBudgetFactAuditReport | None,
) -> str:
    if report is None:
        return "not_applicable"
    if (
        report.budget_readiness_state == "blocked_missing_critical_facts"
        or report.critical_gap_count > 0
    ):
        return "block_amount_budget"
    if report.budget_readiness_state == "range_only_pending_human_review":
        return "hours_only_or_broad_range"
    if any(
        finding.recommended_budget_treatment == "hours_only_or_broad_range"
        for finding in report.findings
        if finding.human_confirmation_required or not finding.source_bound
    ):
        return "hours_only_or_broad_range"
    if any(
        finding.recommended_budget_treatment == "candidate_range_budget_after_review"
        for finding in report.findings
        if finding.human_confirmation_required or not finding.source_bound
    ):
        return "candidate_range_budget_after_review"
    return "candidate_ready_for_budget_review"


def enforce_budget_preconditions(report: BudgetPreconditionReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("budget precondition gate failed: " + ", ".join(failed))


def _refs_match_packet_segments(
    packet: IntakePreflightPacket,
    refs: list[EvidenceRef],
) -> bool:
    if not refs:
        return False
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}
    for ref in refs:
        segment = segments_by_id.get(ref.segment_id)
        if segment is None:
            return False
        if ref.source_id != segment.source_id:
            return False
        if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
            return False
        if ref.sha256 != segment.sha256:
            return False
    return True
