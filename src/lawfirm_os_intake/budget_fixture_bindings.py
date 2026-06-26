from __future__ import annotations

import json
from pathlib import Path

from .models import (
    BudgetCalibrationArtifactKind,
    BudgetCorpusReplayReviewOutcomeReport,
    BudgetCorpusReplayReviewPacket,
    BudgetCorpusReplayReviewRecommendation,
    BudgetFixtureBindingCandidate,
    BudgetFixtureBindingCandidateReport,
    BudgetFixtureBindingCheck,
)
from .util import digest_text, load_json, now_iso, write_json


BUDGET_FIXTURE_BINDING_REPORT_FILENAME = "budget_fixture_binding_candidate_report.json"
BUDGET_FIXTURE_BINDING_CANDIDATES_FILENAME = "budget_fixture_binding_candidates.jsonl"
BUDGET_FIXTURE_BINDING_NOTES_FILENAME = "budget_fixture_binding_candidate_report.md"

BUDGET_FIXTURE_BINDING_REQUIRED_NEXT_GATES = [
    "human_fixture_update_review",
    "append_only_fixture_update_record",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


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
    candidate_ids: list[str] | None = None,
    replay_case_ids: list[str] | None = None,
) -> BudgetFixtureBindingCheck:
    return BudgetFixtureBindingCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        candidate_ids=candidate_ids or [],
        replay_case_ids=replay_case_ids or [],
    )


def _binding_action_for_kind(kind: BudgetCalibrationArtifactKind) -> str:
    if kind == "reviewed_gold_fixture":
        return "bind_replay_outputs_to_reviewed_gold"
    if kind in {
        "intake_source_fixture",
        "human_confirmation_fixture",
        "budget_review_fixture",
        "actuals_fixture",
        "carrier_rejection_fixture",
        "learning_gate_fixture",
        "learning_shadow_eval_fixture",
    }:
        return "bind_replay_outputs_to_synthetic_fixture"
    return "hold_for_manual_fixture_design"


def _candidate_status(outcome_report: BudgetCorpusReplayReviewOutcomeReport) -> str:
    if not (
        outcome_report.outcome == "approve_fixture_binding"
        and outcome_report.fixture_binding_approved
    ):
        return "blocked_pending_approved_outcome"
    if not outcome_report.approved_output_refs:
        return "blocked_missing_approved_outputs"
    return "candidate_ready_for_fixture_update_review"


def _why(
    *,
    outcome_report: BudgetCorpusReplayReviewOutcomeReport,
    recommendation: BudgetCorpusReplayReviewRecommendation,
    status: str,
) -> list[str]:
    lines = [
        f"Replay case `{outcome_report.replay_case_id}` has review outcome `{outcome_report.outcome}`.",
        f"The review packet recommended `{recommendation.recommended_action}` for `{recommendation.source_artifact_ref}`.",
    ]
    if status == "candidate_ready_for_fixture_update_review":
        lines.append(
            "The append-only review outcome approved fixture binding and named approved replay output refs."
        )
        lines.append(
            "This report proposes a fixture binding target but does not update fixture files or apply learning."
        )
    elif status == "blocked_missing_approved_outputs":
        lines.append(
            "The outcome indicates fixture binding approval but carries no approved output refs, so binding fails closed."
        )
    else:
        lines.append(
            "The human outcome has not approved fixture binding, so no fixture update may be proposed as ready."
        )
    lines.append(
        "Any fixture or reviewed-gold update still requires a separate human-reviewed change and regression run."
    )
    return lines


def _required_human_steps(status: str) -> list[str]:
    if status == "candidate_ready_for_fixture_update_review":
        return [
            "inspect approved replay output artifacts and hashes",
            "decide whether the target fixture or reviewed gold should be updated",
            "record the fixture update decision as append-only reviewed evidence",
            "run reviewed learning gate and shadow eval before any candidate learning use",
        ]
    if status == "blocked_missing_approved_outputs":
        return [
            "record a superseding review outcome with explicit approved output refs",
            "rerun fixture-binding proposal after approved output refs are bound",
        ]
    return [
        "obtain an append-only approve_fixture_binding review outcome before fixture binding",
        "keep learning, profile, template, budget, and guideline mutation blocked",
    ]


def _build_candidate(
    *,
    packet: BudgetCorpusReplayReviewPacket,
    outcome_report: BudgetCorpusReplayReviewOutcomeReport,
    recommendation: BudgetCorpusReplayReviewRecommendation,
) -> BudgetFixtureBindingCandidate:
    status = _candidate_status(outcome_report)
    action = (
        _binding_action_for_kind(recommendation.artifact_kind)
        if status == "candidate_ready_for_fixture_update_review"
        else "exclude_from_fixture_binding"
    )
    target_refs = (
        [recommendation.source_artifact_ref]
        if status == "candidate_ready_for_fixture_update_review"
        else []
    )
    return BudgetFixtureBindingCandidate(
        fixture_binding_candidate_id=_stable_id(
            "budgetfixturebinding",
            "|".join(
                [
                    packet.review_packet_id,
                    outcome_report.review_outcome_report_id,
                    outcome_report.replay_case_id,
                ]
            ),
        ),
        review_outcome_report_id=outcome_report.review_outcome_report_id,
        review_outcome_record_id=outcome_report.review_outcome_record_id,
        review_packet_id=packet.review_packet_id,
        replay_execution_report_id=packet.replay_execution_report_id,
        replay_case_id=outcome_report.replay_case_id,
        source_artifact_ref=recommendation.source_artifact_ref,
        artifact_kind=recommendation.artifact_kind,
        approved_output_refs=outcome_report.approved_output_refs,
        proposed_target_fixture_refs=target_refs,
        proposed_binding_action=action,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        why=_why(
            outcome_report=outcome_report,
            recommendation=recommendation,
            status=status,
        ),
        required_human_steps=_required_human_steps(status),
    )


def build_budget_fixture_binding_candidate_report(
    *,
    packet: BudgetCorpusReplayReviewPacket,
    outcome_report: BudgetCorpusReplayReviewOutcomeReport,
    review_packet_ref: str,
    review_outcome_report_ref: str,
) -> BudgetFixtureBindingCandidateReport:
    if outcome_report.review_packet_id != packet.review_packet_id:
        raise ValueError(
            "fixture binding outcome report review_packet_id does not match packet: "
            f"{outcome_report.review_packet_id} != {packet.review_packet_id}"
        )
    if outcome_report.replay_execution_report_id != packet.replay_execution_report_id:
        raise ValueError(
            "fixture binding outcome report replay_execution_report_id does not match packet: "
            f"{outcome_report.replay_execution_report_id} != {packet.replay_execution_report_id}"
        )
    recommendations = _recommendation_map(packet)
    recommendation = recommendations.get(outcome_report.replay_case_id)
    if recommendation is None:
        raise ValueError(
            "fixture binding outcome report targets unknown replay case: "
            f"{outcome_report.replay_case_id}"
        )
    candidate = _build_candidate(
        packet=packet,
        outcome_report=outcome_report,
        recommendation=recommendation,
    )
    approved = (
        outcome_report.outcome == "approve_fixture_binding"
        and outcome_report.fixture_binding_approved
    )
    approved_outputs_present = bool(outcome_report.approved_output_refs)
    checks = [
        _check(
            "review_packet_matches_outcome_report",
            "passed",
            "Review packet ID and replay execution report ID match the outcome report.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
        _check(
            "recommendation_present",
            "passed",
            "Replay case has a recommendation in the supplied review packet.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
        _check(
            "approved_review_outcome_present",
            "passed" if approved else "failed",
            "Fixture binding requires an append-only approve_fixture_binding outcome.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
        _check(
            "approved_outputs_present",
            "passed" if approved_outputs_present else "failed",
            "Approved fixture binding requires approved replay output refs.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
        _check(
            "fixture_binding_not_applied",
            "passed",
            "This report proposes candidate bindings only and does not mutate fixtures.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
        _check(
            "learning_still_blocked",
            "passed",
            "Fixture-binding candidates do not authorize learning, mutation, Lake writes, or external action.",
            [candidate.fixture_binding_candidate_id],
            [candidate.replay_case_id],
        ),
    ]
    ready_count = int(candidate.status == "candidate_ready_for_fixture_update_review")
    if candidate.status == "candidate_ready_for_fixture_update_review":
        report_status = "fixture_binding_candidates_ready_for_review"
    elif candidate.status == "blocked_missing_approved_outputs":
        report_status = "blocked_missing_approved_outputs"
    else:
        report_status = "blocked_pending_approved_outcome"
    return BudgetFixtureBindingCandidateReport(
        fixture_binding_candidate_report_id=_stable_id(
            "budgetfixturebindingreport",
            "|".join(
                [
                    packet.review_packet_id,
                    outcome_report.review_outcome_report_id,
                    outcome_report.replay_case_id,
                ]
            ),
        ),
        review_packet_id=packet.review_packet_id,
        review_outcome_report_id=outcome_report.review_outcome_report_id,
        review_outcome_record_id=outcome_report.review_outcome_record_id,
        replay_execution_report_id=packet.replay_execution_report_id,
        replay_case_id=outcome_report.replay_case_id,
        source_review_packet_ref=review_packet_ref,
        source_review_outcome_report_ref=review_outcome_report_ref,
        status=report_status,  # type: ignore[arg-type]
        candidate_count=1,
        ready_candidate_count=ready_count,
        blocked_candidate_count=1 - ready_count,
        candidates=[candidate],
        checks=checks,
        required_next_gates=BUDGET_FIXTURE_BINDING_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_fixture_binding_candidate_report(
    report: BudgetFixtureBindingCandidateReport,
) -> str:
    lines = [
        "# Budget Fixture Binding Candidate Report",
        "",
        f"**Report ID:** {report.fixture_binding_candidate_report_id}",
        f"**Status:** {report.status}",
        f"**Review packet:** {report.review_packet_id}",
        f"**Review outcome report:** {report.review_outcome_report_id}",
        f"**Replay case:** {report.replay_case_id}",
        f"**Candidates:** {report.candidate_count}",
        f"**Ready candidates:** {report.ready_candidate_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Review packet mutated: {report.review_packet_mutated}",
        f"- Outcome report mutated: {report.outcome_report_mutated}",
        f"- Source fixture mutated: {report.source_fixture_mutated}",
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
        "## Candidates",
        "",
    ]
    for candidate in report.candidates:
        lines.append(
            f"- `{candidate.fixture_binding_candidate_id}`: {candidate.status}; "
            f"action={candidate.proposed_binding_action}; target={candidate.source_artifact_ref}"
        )
        for item in candidate.why:
            lines.append(f"  - {item}")
        lines.append("  - Required human steps:")
        lines.extend(f"    - {step}" for step in candidate.required_human_steps)
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report is a candidate fixture-binding proposal only. It does not update fixtures, apply learning, write Lake/SQLite records, submit budgets, open matters, or authorize external action.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_candidates_jsonl(
    path: Path,
    candidates: list[BudgetFixtureBindingCandidate],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for candidate in candidates
    )
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    return path


def run_budget_fixture_binding_candidates(
    *,
    review_packet_path: str | Path,
    review_outcome_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetFixtureBindingCandidateReport, Path]:
    packet_path = Path(review_packet_path)
    outcome_report_path = Path(review_outcome_report_path)
    packet = BudgetCorpusReplayReviewPacket.model_validate(load_json(packet_path))
    outcome_report = BudgetCorpusReplayReviewOutcomeReport.model_validate(
        load_json(outcome_report_path)
    )
    report = build_budget_fixture_binding_candidate_report(
        packet=packet,
        outcome_report=outcome_report,
        review_packet_ref=str(packet_path),
        review_outcome_report_ref=str(outcome_report_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / BUDGET_FIXTURE_BINDING_REPORT_FILENAME, report.model_dump(mode="json"))
    _write_candidates_jsonl(
        run_dir / BUDGET_FIXTURE_BINDING_CANDIDATES_FILENAME,
        report.candidates,
    )
    (run_dir / BUDGET_FIXTURE_BINDING_NOTES_FILENAME).write_text(
        render_budget_fixture_binding_candidate_report(report),
        encoding="utf-8",
    )
    return report, run_dir
