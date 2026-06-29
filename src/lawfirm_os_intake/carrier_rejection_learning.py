from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import (
    CarrierRejectionLearningProposal,
    CarrierRejectionLearningReport,
    CarrierRejectionReviewPacket,
    CarrierRejectionReviewRecommendation,
    RunEvent,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


LEARNING_REPORT_FILENAME = "carrier_rejection_learning_report.json"
LEARNING_NOTES_FILENAME = "carrier_rejection_learning_report.md"


PROPOSAL_POLICY: dict[str, dict[str, str]] = {
    "timekeeper_rate_candidate": {
        "loop": "timekeeper_rate",
        "owner": "LawFirm-os-intake",
        "before": "Named timekeeper or title-rate pressure is handled case by case.",
        "after": "Propose a reviewed candidate rate-resolution fixture or warning for the affected carrier/profile.",
        "eval": "rate-resolution counterfactual",
    },
    "guideline_profile_change_candidate": {
        "loop": "guideline_drift",
        "owner": "LawFirm-os-intake",
        "before": "The current synthetic guideline profile may not explain the carrier rejection.",
        "after": "Propose a reviewed candidate guideline-profile delta with before/after compliant projection behavior.",
        "eval": "carrier guideline shadow projection",
    },
    "eval_fixture_candidate": {
        "loop": "eval_fixture",
        "owner": "LawFirm-os-intake",
        "before": "The rejection pattern is not yet represented by a synthetic acceptance fixture.",
        "after": "Propose a synthetic fixture or holdout that reproduces the reviewed rejection pressure.",
        "eval": "fixture-gold replay",
    },
    "validation_rule_candidate": {
        "loop": "validation_rule",
        "owner": "LawFirm-os-intake",
        "before": "The current local validation layer did not surface this issue early enough.",
        "after": "Propose a candidate validation warning or blocker with source-bound evidence requirements.",
        "eval": "validation regression",
    },
    "preapproval_gate_candidate": {
        "loop": "preapproval_gate",
        "owner": "LawFirm-os-orchestrator",
        "before": "Preapproval pressure is detected after carrier rejection.",
        "after": "Propose an earlier human preapproval gate before budget, vendor, expert, or deposition action.",
        "eval": "preapproval threshold replay",
    },
    "staffing_rule_candidate": {
        "loop": "staffing_leverage",
        "owner": "LawFirm-os-intake",
        "before": "Staffing or leverage pressure is handled as a reviewer note.",
        "after": "Propose a candidate staffing/leverage warning and blended-rate report expectation.",
        "eval": "staffing counterfactual",
    },
    "narrative_rule_candidate": {
        "loop": "narrative_rule",
        "owner": "LawFirm-os-intake",
        "before": "Narrative deficiencies are not yet transformed into reusable review rules.",
        "after": "Propose a candidate narrative-review rule and synthetic time-entry fixture.",
        "eval": "narrative deficiency replay",
    },
    "template_mapping_candidate": {
        "loop": "template_mapping",
        "owner": "LawFirm-os-intake",
        "before": "Workbook or UTBMS mapping pressure remains local to the rejection case.",
        "after": "Propose a candidate template mapping fixture and form audit regression.",
        "eval": "budget form mapping regression",
    },
    "budget_driver_candidate": {
        "loop": "budget_model",
        "owner": "LawFirm-os-intake",
        "before": "Phase/task budget variance is reviewed as an after-the-fact rejection.",
        "after": "Propose a candidate budget-driver adjustment or warning with scenario impact.",
        "eval": "budget driver counterfactual",
    },
    "variance_threshold_candidate": {
        "loop": "budget_model",
        "owner": "LawFirm-os-intake",
        "before": "Variance thresholds do not yet affect human review pressure.",
        "after": "Propose a candidate variance threshold warning before budget overrun repeats.",
        "eval": "actual-vs-budget replay",
    },
    "guideline_version_review_candidate": {
        "loop": "guideline_drift",
        "owner": "LawFirm-os-semantic-substrate",
        "before": "Guideline version drift is captured as a rejection label only.",
        "after": "Propose a governed profile/version review path; canonical promotion remains outside intake.",
        "eval": "guideline version drift replay",
    },
    "parser_rule_candidate": {
        "loop": "parser_rule",
        "owner": "LawFirm-os-orchestrator",
        "before": "Captured source parsing failed and requires manual review.",
        "after": "Propose a parser repair candidate with source hash, parser version, and expected field gap.",
        "eval": "parser failure replay",
    },
    "reconciliation_rule_candidate": {
        "loop": "capture_completeness",
        "owner": "LawFirm-os-orchestrator",
        "before": "A captured notice could not link to an expected response state.",
        "after": "Propose a deterministic linkage rule candidate for submission, claim, invoice, appeal, or source IDs.",
        "eval": "unlinked notice replay",
    },
    "capture_sla_candidate": {
        "loop": "capture_completeness",
        "owner": "LawFirm-os-orchestrator",
        "before": "Missing expected responses are detected after the SLA has elapsed.",
        "after": "Propose an earlier follow-up threshold, owner assignment check, or response-state alert.",
        "eval": "missing response SLA replay",
    },
    "appeal_outcome_candidate": {
        "loop": "appeal_success_or_failure",
        "owner": "LawFirm-os-intake",
        "before": "Appeal outcomes are captured but not yet summarized as reusable decision pressure.",
        "after": "Propose an appeal outcome pattern candidate with recovered/write-down math and no automatic future appeal.",
        "eval": "appeal result replay",
    },
}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _proposal_types_for_recommendation(
    recommendation: CarrierRejectionReviewRecommendation,
) -> list[str]:
    proposal_types = list(recommendation.learning_disposition_candidates)
    if recommendation.recommended_action == "record_appeal_result":
        proposal_types.append("appeal_outcome_candidate")
    return sorted(set(item for item in proposal_types if item in PROPOSAL_POLICY))


def _status_for_review_packet(packet: CarrierRejectionReviewPacket, proposal_count: int) -> str:
    if not proposal_count:
        return "no_learning_candidates"
    if packet.status.startswith("blocked"):
        return "blocked_pending_human_review_packet"
    return "candidate_learning_ready_for_review"


def build_carrier_rejection_learning_report(
    packet: CarrierRejectionReviewPacket,
) -> CarrierRejectionLearningReport:
    grouped: dict[tuple[str, str], list[CarrierRejectionReviewRecommendation]] = defaultdict(list)
    for recommendation in packet.recommendations:
        for proposal_type in _proposal_types_for_recommendation(recommendation):
            grouped[(proposal_type, recommendation.local_event_label)].append(recommendation)

    proposals: list[CarrierRejectionLearningProposal] = []
    for (proposal_type, label), recommendations in sorted(grouped.items()):
        policy = PROPOSAL_POLICY[proposal_type]
        recommendation_ids = sorted(item.recommendation_id for item in recommendations)
        case_ids = sorted({item.remediation_case_id for item in recommendations})
        exception_ids = sorted(
            {
                candidate_id
                for item in recommendations
                for candidate_id in item.exception_candidate_ids
            }
        )
        structured_refs = [
            f"carrier-rejection-review-packet://{packet.review_packet_id}",
            *[f"carrier-rejection-recommendation://{item}" for item in recommendation_ids],
            *[f"carrier-rejection-case://{item}" for item in case_ids],
            *[f"exception-lake-candidate://{item}" for item in exception_ids],
            "docs/carrier-rejection-learning-loop-roadmap.md#learning-loops",
        ]
        proposal_id = _stable_id(
            "carrierrejlearn",
            f"{packet.review_packet_id}|{proposal_type}|{label}|{','.join(case_ids)}",
        )
        proposals.append(
            CarrierRejectionLearningProposal(
                proposal_id=proposal_id,
                proposal_type=proposal_type,  # type: ignore[arg-type]
                target_learning_loop=policy["loop"],  # type: ignore[arg-type]
                target_owner=policy["owner"],  # type: ignore[arg-type]
                source_review_packet_id=packet.review_packet_id,
                source_recommendation_ids=recommendation_ids,
                remediation_case_ids=case_ids,
                local_event_labels=[label],
                source_structured_refs=structured_refs,
                support_count=len(case_ids),
                before_behavior=policy["before"],
                proposed_candidate_behavior=policy["after"],
                required_evaluation=[
                    policy["eval"],
                    "synthetic fixture update",
                    "shadow eval before promotion",
                    "human-reviewed outcome evidence",
                ],
                promotion_target_note=(
                    f"{policy['owner']} may review this proposal; intake performs no direct promotion."
                ),
                status="blocked_until_reviewed_outcome",
            )
        )

    target_owners = sorted({proposal.target_owner for proposal in proposals})
    return CarrierRejectionLearningReport(
        learning_report_id=_stable_id(
            "carrierrejlearning", f"{packet.review_packet_id}|learning-report"
        ),
        review_packet_id=packet.review_packet_id,
        reconciliation_report_id=packet.reconciliation_report_id,
        run_id=packet.run_id,
        preflight_packet_id=packet.preflight_packet_id,
        budget_proposal_id=packet.budget_proposal_id,
        status=_status_for_review_packet(packet, len(proposals)),  # type: ignore[arg-type]
        input_review_status=packet.status,
        proposal_count=len(proposals),
        proposals=proposals,
        required_next_gates=[
            "human_reviewed_rejection_outcome",
            "append_only_outcome_record",
            "synthetic_fixture_update",
            "shadow_eval",
            "owning_repo_promotion_review_if_canon_changes",
        ],
        target_owners=target_owners,
        generated_at=now_iso(),
    )


def render_carrier_rejection_learning_report(report: CarrierRejectionLearningReport) -> str:
    lines = [
        "# Carrier Rejection Learning Candidate Report",
        "",
        f"**Learning report ID:** {report.learning_report_id}",
        f"**Review packet ID:** {report.review_packet_id}",
        f"**Reconciliation report ID:** {report.reconciliation_report_id}",
        f"**Status:** {report.status}",
        f"**Input review status:** {report.input_review_status}",
        "",
        "## Summary",
        "",
        f"- Proposal count: {report.proposal_count}",
        f"- Target owners: {', '.join(report.target_owners) or 'none'}",
        f"- Reviewed outcome required: {report.reviewed_outcome_required}",
        f"- Append-only outcome required: {report.append_only_outcome_required}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        f"- Profile mutation performed: {report.profile_mutation_performed}",
        f"- Template mutation performed: {report.template_mutation_performed}",
        f"- Connector mutation performed: {report.connector_mutation_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {item}" for item in report.required_next_gates),
        "",
        "## Proposals",
        "",
    ]
    if not report.proposals:
        lines.append("- none")
    for proposal in report.proposals:
        lines.extend(
            [
                f"- `{proposal.proposal_id}`: {proposal.proposal_type}; "
                f"loop={proposal.target_learning_loop}; owner={proposal.target_owner}; "
                f"status={proposal.status}; support_count={proposal.support_count}",
                f"  Before: {proposal.before_behavior}",
                f"  Candidate behavior: {proposal.proposed_candidate_behavior}",
                f"  Promotion note: {proposal.promotion_target_note}",
                "  Required evaluation:",
                *(f"  - {item}" for item in proposal.required_evaluation),
                "  Source refs:",
                *(f"  - {item}" for item in proposal.source_structured_refs),
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- Lake write authorized: {not report.not_authorized_for_lake_write}",
            f"- External submission authorized: {not report.not_authorized_for_external_submission}",
            f"- External writes performed: {report.external_writes_performed}",
            "",
            "This report proposes candidate learning work only. It does not mutate profiles, templates, connectors, Lake records, budgets, carrier submissions, or canonical contracts.",
            "",
        ]
    )
    return "\n".join(lines)


def run_carrier_rejection_learning(
    review_packet_path: str | Path,
    out_dir: str | Path,
) -> tuple[CarrierRejectionLearningReport, Path]:
    packet = CarrierRejectionReviewPacket.model_validate(load_json(review_packet_path))
    report = build_carrier_rejection_learning_report(packet)

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / LEARNING_REPORT_FILENAME
    notes_path = run_dir / LEARNING_NOTES_FILENAME
    ledger_path = run_dir / "run_ledger.jsonl"
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_carrier_rejection_learning_report(report), encoding="utf-8")
    append_jsonl(
        ledger_path,
        RunEvent(
            run_id=report.run_id,
            step_index=2,
            step_name="carrier_rejection_learning_candidates_built",
            status="completed" if report.proposal_count else "blocked",
            timestamp=now_iso(),
            input_refs=[str(review_packet_path)],
            output_refs=[str(report_path), str(notes_path)],
        ).model_dump(mode="json"),
    )
    return report, run_dir
