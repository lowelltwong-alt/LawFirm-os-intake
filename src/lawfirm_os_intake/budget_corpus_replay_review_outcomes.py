from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetCorpusReplayReviewDecisionTemplate,
    BudgetCorpusReplayReviewOutcomeCheck,
    BudgetCorpusReplayReviewOutcomeRecord,
    BudgetCorpusReplayReviewOutcomeReport,
    BudgetCorpusReplayReviewPacket,
    BudgetCorpusReplayReviewRecommendation,
)
from .util import append_jsonl, load_json, new_id, now_iso, write_json


REPLAY_REVIEW_OUTCOME_RECORD_FILENAME = "budget_corpus_replay_review_outcome_record.json"
REPLAY_REVIEW_OUTCOME_HISTORY_FILENAME = "budget_corpus_replay_review_outcome_history.jsonl"
REPLAY_REVIEW_OUTCOME_REPORT_FILENAME = "budget_corpus_replay_review_outcome_report.json"
REPLAY_REVIEW_OUTCOME_NOTES_FILENAME = "budget_corpus_replay_review_outcome_report.md"

REPLAY_REVIEW_OUTCOME_REQUIRED_NEXT_GATES = [
    "inspect_append_only_review_outcome",
    "fixture_result_binding_review",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]


def _template_map(
    packet: BudgetCorpusReplayReviewPacket,
) -> dict[str, BudgetCorpusReplayReviewDecisionTemplate]:
    return {template.replay_case_id: template for template in packet.decision_templates}


def _recommendation_map(
    packet: BudgetCorpusReplayReviewPacket,
) -> dict[str, BudgetCorpusReplayReviewRecommendation]:
    return {
        recommendation.replay_case_id: recommendation for recommendation in packet.recommendations
    }


def _check(
    check_id: str,
    status: str,
    message: str,
    replay_case_ids: list[str] | None = None,
) -> BudgetCorpusReplayReviewOutcomeCheck:
    return BudgetCorpusReplayReviewOutcomeCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        replay_case_ids=replay_case_ids or [],
    )


def _bind_record_to_packet(
    *,
    record: BudgetCorpusReplayReviewOutcomeRecord,
    packet: BudgetCorpusReplayReviewPacket,
    packet_ref: str,
) -> BudgetCorpusReplayReviewOutcomeRecord:
    if record.review_packet_id != packet.review_packet_id:
        raise ValueError(
            "replay review outcome review_packet_id does not match packet: "
            f"{record.review_packet_id} != {packet.review_packet_id}"
        )
    templates = _template_map(packet)
    recommendations = _recommendation_map(packet)
    template = templates.get(record.replay_case_id)
    if template is None:
        raise ValueError(f"replay review outcome targets unknown case: {record.replay_case_id}")
    if record.outcome not in template.allowed_outcomes:
        raise ValueError(
            "replay review outcome is not allowed for case "
            f"{record.replay_case_id}: {record.outcome}"
        )
    recommendation = recommendations.get(record.replay_case_id)
    known_outputs = set(recommendation.output_refs if recommendation is not None else [])
    unbound_outputs = sorted(set(record.approved_output_refs) - known_outputs)
    if record.outcome == "approve_fixture_binding" and unbound_outputs:
        raise ValueError(
            "approved replay output refs are not present in the review packet: "
            + ", ".join(unbound_outputs)
        )
    return record.model_copy(
        update={
            "replay_execution_report_id": packet.replay_execution_report_id,
            "source_review_packet_ref": packet_ref,
            "fixture_binding_approved": record.outcome == "approve_fixture_binding",
        }
    )


def _status_for_outcome(outcome: str) -> str:
    if outcome == "approve_fixture_binding":
        return "review_outcome_recorded_learning_still_blocked"
    if outcome in {
        "reject_fixture_binding",
        "needs_replay_repair",
        "exclude_from_learning",
    }:
        return "review_outcome_rejected_or_needs_repair"
    return "review_outcome_recorded"


def build_budget_corpus_replay_review_outcome_report(
    *,
    packet: BudgetCorpusReplayReviewPacket,
    record: BudgetCorpusReplayReviewOutcomeRecord,
    packet_ref: str,
    history_ref: str,
) -> BudgetCorpusReplayReviewOutcomeReport:
    templates = _template_map(packet)
    recommendations = _recommendation_map(packet)
    template = templates[record.replay_case_id]
    recommendation = recommendations.get(record.replay_case_id)
    approved_outputs_bound = sorted(set(record.approved_output_refs)) == sorted(
        set(record.approved_output_refs) & set(recommendation.output_refs if recommendation else [])
    )
    checks = [
        _check(
            "review_packet_id_matches",
            "passed",
            "Outcome record is bound to the supplied replay review packet.",
            [record.replay_case_id],
        ),
        _check(
            "decision_template_present",
            "passed",
            "Replay case has a decision template in the review packet.",
            [record.replay_case_id],
        ),
        _check(
            "outcome_allowed_by_template",
            "passed",
            "Outcome is one of the template's allowed outcomes.",
            [record.replay_case_id],
        ),
        _check(
            "approved_outputs_bound",
            "passed" if approved_outputs_bound else "failed",
            "Approved output refs are present in the packet recommendation.",
            [record.replay_case_id],
        ),
        _check(
            "learning_still_blocked",
            "passed",
            "Recording this outcome does not authorize learning, mutation, Lake writes, or external action.",
            [record.replay_case_id],
        ),
    ]
    return BudgetCorpusReplayReviewOutcomeReport(
        review_outcome_report_id=new_id("budgetcorpusreplayoutcomereport"),
        review_packet_id=packet.review_packet_id,
        replay_execution_report_id=packet.replay_execution_report_id,
        source_review_packet_ref=packet_ref,
        review_outcome_record_id=record.review_outcome_id,
        status=_status_for_outcome(record.outcome),  # type: ignore[arg-type]
        replay_case_id=record.replay_case_id,
        outcome=record.outcome,
        decision_action=template.recommended_action,
        decision_reason=record.decision_reason,
        append_only_history_ref=history_ref,
        approved_output_refs=record.approved_output_refs,
        rejected_output_refs=record.rejected_output_refs,
        required_followups=record.required_followups,
        checks=checks,
        required_next_gates=REPLAY_REVIEW_OUTCOME_REQUIRED_NEXT_GATES,
        fixture_binding_approved=record.outcome == "approve_fixture_binding",
        generated_at=now_iso(),
    )


def render_budget_corpus_replay_review_outcome_report(
    report: BudgetCorpusReplayReviewOutcomeReport,
) -> str:
    lines = [
        "# Budget Corpus Replay Review Outcome Report",
        "",
        f"**Report ID:** {report.review_outcome_report_id}",
        f"**Status:** {report.status}",
        f"**Review packet:** {report.review_packet_id}",
        f"**Replay case:** {report.replay_case_id}",
        f"**Outcome:** {report.outcome}",
        f"**Decision action:** {report.decision_action}",
        "",
        "## Boundary",
        "",
        f"- Append-only: {report.append_only}",
        f"- Source packet mutated: {report.source_packet_mutated}",
        f"- Fixture binding approved: {report.fixture_binding_approved}",
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
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report records append-only local review evidence. It does not mutate the review packet, apply learning, write Lake/SQLite records, or authorize external action.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_corpus_replay_review_outcome_record(
    *,
    review_packet_path: str | Path,
    outcome_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetCorpusReplayReviewOutcomeReport, Path]:
    packet_path = Path(review_packet_path)
    outcome_path = Path(outcome_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = BudgetCorpusReplayReviewPacket.model_validate(load_json(packet_path))
    raw_record = BudgetCorpusReplayReviewOutcomeRecord.model_validate(load_json(outcome_path))
    record = _bind_record_to_packet(
        record=raw_record,
        packet=packet,
        packet_ref=str(packet_path),
    )
    history_path = run_dir / REPLAY_REVIEW_OUTCOME_HISTORY_FILENAME
    report = build_budget_corpus_replay_review_outcome_report(
        packet=packet,
        record=record,
        packet_ref=str(packet_path),
        history_ref=str(history_path),
    )
    record_path = run_dir / REPLAY_REVIEW_OUTCOME_RECORD_FILENAME
    report_path = run_dir / REPLAY_REVIEW_OUTCOME_REPORT_FILENAME
    notes_path = run_dir / REPLAY_REVIEW_OUTCOME_NOTES_FILENAME
    write_json(record_path, record.model_dump(mode="json"))
    append_jsonl(history_path, record.model_dump(mode="json"))
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(
        render_budget_corpus_replay_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir
