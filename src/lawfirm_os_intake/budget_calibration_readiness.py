from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetCalibrationCorpusReport,
    BudgetCalibrationReadinessCheck,
    BudgetCalibrationReadinessReport,
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayPlan,
    BudgetCorpusReplayReviewOutcomeReport,
    BudgetCorpusReplayReviewPacket,
    BudgetFixtureBindingCandidateReport,
    BudgetFixtureBindingHandoffReport,
)
from .util import digest_text, load_json, now_iso, write_json


BUDGET_CALIBRATION_READINESS_REPORT_FILENAME = "budget_calibration_readiness_report.json"
BUDGET_CALIBRATION_READINESS_NOTES_FILENAME = "budget_calibration_readiness_report.md"

BUDGET_CALIBRATION_READINESS_REQUIRED_NEXT_GATES = [
    "human_fixture_update_review",
    "separate_fixture_update_pr_if_accepted",
    "append_only_fixture_update_record",
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
) -> BudgetCalibrationReadinessCheck:
    return BudgetCalibrationReadinessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _boundary_clear(item: Any) -> bool:
    for field in [
        "calibration_applied",
        "profile_mutation_performed",
        "template_mutation_performed",
        "budget_mutation_performed",
        "carrier_guideline_mutation_performed",
        "lake_write_performed",
        "sqlite_write_performed",
        "external_writes_performed",
        "silent_learning_performed",
    ]:
        if getattr(item, field, False):
            return False
    return True


def _candidate_report_boundary_clear(report: BudgetFixtureBindingCandidateReport) -> bool:
    return (
        _boundary_clear(report)
        and report.fixture_files_mutated is False
        and report.fixture_binding_applied is False
        and report.downstream_learning_gate_allowed is False
    )


def _handoff_boundary_clear(report: BudgetFixtureBindingHandoffReport) -> bool:
    return (
        _boundary_clear(report)
        and report.fixture_update_authorized is False
        and report.fixture_update_pr_created is False
        and report.fixture_files_mutated is False
        and report.fixture_binding_applied is False
        and report.downstream_learning_gate_allowed is False
    )


def build_budget_calibration_readiness_report(
    *,
    corpus_report: BudgetCalibrationCorpusReport,
    corpus_report_ref: str,
    replay_plan: BudgetCorpusReplayPlan,
    replay_plan_ref: str,
    replay_execution_report: BudgetCorpusReplayExecutionReport,
    replay_execution_report_ref: str,
    replay_review_packet: BudgetCorpusReplayReviewPacket,
    replay_review_packet_ref: str,
    replay_review_outcome_report: BudgetCorpusReplayReviewOutcomeReport,
    replay_review_outcome_report_ref: str,
    fixture_binding_candidate_report: BudgetFixtureBindingCandidateReport,
    fixture_binding_candidate_report_ref: str,
    fixture_binding_handoff_report: BudgetFixtureBindingHandoffReport,
    fixture_binding_handoff_report_ref: str,
) -> BudgetCalibrationReadinessReport:
    ready_handoff_items = [
        item
        for item in fixture_binding_handoff_report.handoff_items
        if item.disposition == "ready_for_human_fixture_update_review"
    ]
    approved_output_refs = sorted(
        {ref for item in ready_handoff_items for ref in item.approved_output_refs}
    )
    target_fixture_refs = sorted(
        {ref for item in ready_handoff_items for ref in item.proposed_target_fixture_refs}
    )
    ready_candidate_ids = {
        candidate.fixture_binding_candidate_id
        for candidate in fixture_binding_candidate_report.candidates
        if candidate.status == "candidate_ready_for_fixture_update_review"
    }
    handoff_candidate_ids = {
        item.fixture_binding_candidate_id for item in fixture_binding_handoff_report.handoff_items
    }
    chain_refs = [
        corpus_report_ref,
        replay_plan_ref,
        replay_execution_report_ref,
        replay_review_packet_ref,
        replay_review_outcome_report_ref,
        fixture_binding_candidate_report_ref,
        fixture_binding_handoff_report_ref,
    ]
    checks = [
        _check(
            "corpus_ready_for_review",
            corpus_report.status == "synthetic_corpus_ready_for_review"
            and corpus_report.eligible_artifact_count > 0
            and corpus_report.blocked_artifact_count == 0
            and _boundary_clear(corpus_report),
            "Corpus audit is synthetic, eligible for review, and has no mutation/write side effects.",
            artifact_refs=[corpus_report_ref],
        ),
        _check(
            "replay_plan_ready_and_bound_to_corpus",
            replay_plan.status == "replay_plan_ready_for_review"
            and replay_plan.source_corpus_report_id == corpus_report.corpus_report_id
            and replay_plan.planned_case_count > 0
            and _boundary_clear(replay_plan),
            "Replay plan is ready and bound to the supplied corpus report.",
            artifact_refs=[replay_plan_ref, corpus_report_ref],
        ),
        _check(
            "replay_execution_passed_and_bound_to_plan",
            replay_execution_report.status == "execution_passed_for_review"
            and replay_execution_report.replay_plan_id == replay_plan.replay_plan_id
            and replay_execution_report.executed_case_count > 0
            and replay_execution_report.failed_case_count == 0
            and replay_execution_report.blocked_case_count == 0
            and _boundary_clear(replay_execution_report),
            "Replay execution passed for selected synthetic cases and is bound to the supplied plan.",
            artifact_refs=[replay_execution_report_ref, replay_plan_ref],
        ),
        _check(
            "review_packet_ready_and_bound_to_execution",
            replay_review_packet.status == "ready_for_human_replay_review"
            and replay_review_packet.replay_execution_report_id
            == replay_execution_report.replay_execution_report_id
            and replay_review_packet.recommendation_count > 0
            and _boundary_clear(replay_review_packet),
            "Replay review packet is ready and bound to the supplied execution report.",
            artifact_refs=[replay_review_packet_ref, replay_execution_report_ref],
        ),
        _check(
            "review_outcome_approves_fixture_binding",
            replay_review_outcome_report.review_packet_id == replay_review_packet.review_packet_id
            and replay_review_outcome_report.replay_execution_report_id
            == replay_execution_report.replay_execution_report_id
            and replay_review_outcome_report.outcome == "approve_fixture_binding"
            and replay_review_outcome_report.fixture_binding_approved
            and bool(replay_review_outcome_report.approved_output_refs)
            and _boundary_clear(replay_review_outcome_report)
            and replay_review_outcome_report.downstream_learning_gate_allowed is False,
            "Append-only review outcome approves fixture binding, carries approved output refs, and still blocks learning.",
            artifact_refs=[replay_review_outcome_report_ref, replay_review_packet_ref],
        ),
        _check(
            "fixture_binding_candidates_ready",
            fixture_binding_candidate_report.status == "fixture_binding_candidates_ready_for_review"
            and fixture_binding_candidate_report.review_packet_id
            == replay_review_packet.review_packet_id
            and fixture_binding_candidate_report.review_outcome_report_id
            == replay_review_outcome_report.review_outcome_report_id
            and fixture_binding_candidate_report.replay_case_id
            == replay_review_outcome_report.replay_case_id
            and fixture_binding_candidate_report.ready_candidate_count > 0
            and fixture_binding_candidate_report.blocked_candidate_count == 0
            and _candidate_report_boundary_clear(fixture_binding_candidate_report),
            "Fixture-binding candidate report is ready, bound to the review outcome, and does not mutate fixtures.",
            artifact_refs=[
                fixture_binding_candidate_report_ref,
                replay_review_outcome_report_ref,
            ],
        ),
        _check(
            "fixture_binding_handoff_ready",
            fixture_binding_handoff_report.status
            == "fixture_binding_handoff_ready_for_human_review"
            and fixture_binding_handoff_report.source_fixture_binding_candidate_report_id
            == fixture_binding_candidate_report.fixture_binding_candidate_report_id
            and fixture_binding_handoff_report.ready_item_count > 0
            and fixture_binding_handoff_report.blocked_item_count == 0
            and ready_candidate_ids == handoff_candidate_ids
            and _handoff_boundary_clear(fixture_binding_handoff_report),
            "Fixture-binding handoff is ready for manual fixture-update review and does not authorize a fixture update.",
            artifact_refs=[
                fixture_binding_handoff_report_ref,
                fixture_binding_candidate_report_ref,
            ],
        ),
        _check(
            "replay_case_ids_align",
            replay_review_outcome_report.replay_case_id
            == fixture_binding_candidate_report.replay_case_id
            and all(
                item.replay_case_id == replay_review_outcome_report.replay_case_id
                for item in fixture_binding_handoff_report.handoff_items
            ),
            "Replay case IDs align from outcome through fixture-binding handoff.",
            artifact_refs=chain_refs,
        ),
        _check(
            "required_manual_gates_preserved",
            set(BUDGET_CALIBRATION_READINESS_REQUIRED_NEXT_GATES).issubset(
                set(fixture_binding_handoff_report.required_next_gates)
            ),
            "Fixture-binding handoff preserves manual fixture update, append-only record, shadow eval, owner review, and no-silent-learning gates.",
            artifact_refs=[fixture_binding_handoff_report_ref],
        ),
        _check(
            "no_side_effects_across_chain",
            all(
                [
                    _boundary_clear(corpus_report),
                    _boundary_clear(replay_plan),
                    _boundary_clear(replay_execution_report),
                    _boundary_clear(replay_review_packet),
                    _boundary_clear(replay_review_outcome_report),
                    _candidate_report_boundary_clear(fixture_binding_candidate_report),
                    _handoff_boundary_clear(fixture_binding_handoff_report),
                ]
            ),
            "The full calibration chain performed no fixture mutation, calibration, Lake/SQLite write, external write, or silent learning.",
            artifact_refs=chain_refs,
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    status = (
        "blocked_by_calibration_chain"
        if failed_checks
        else "ready_for_manual_fixture_update_review"
    )
    return BudgetCalibrationReadinessReport(
        budget_calibration_readiness_report_id=_stable_id(
            "budgetcalibrationreadiness",
            "|".join(
                [
                    corpus_report.corpus_report_id,
                    replay_plan.replay_plan_id,
                    replay_execution_report.replay_execution_report_id,
                    replay_review_packet.review_packet_id,
                    replay_review_outcome_report.review_outcome_report_id,
                    fixture_binding_candidate_report.fixture_binding_candidate_report_id,
                    fixture_binding_handoff_report.fixture_binding_handoff_report_id,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        corpus_report_id=corpus_report.corpus_report_id,
        replay_plan_id=replay_plan.replay_plan_id,
        replay_execution_report_id=replay_execution_report.replay_execution_report_id,
        review_packet_id=replay_review_packet.review_packet_id,
        review_outcome_report_id=replay_review_outcome_report.review_outcome_report_id,
        fixture_binding_candidate_report_id=(
            fixture_binding_candidate_report.fixture_binding_candidate_report_id
        ),
        fixture_binding_handoff_report_id=(
            fixture_binding_handoff_report.fixture_binding_handoff_report_id
        ),
        replay_case_id=replay_review_outcome_report.replay_case_id,
        source_corpus_report_ref=corpus_report_ref,
        source_replay_plan_ref=replay_plan_ref,
        source_replay_execution_report_ref=replay_execution_report_ref,
        source_review_packet_ref=replay_review_packet_ref,
        source_review_outcome_report_ref=replay_review_outcome_report_ref,
        source_fixture_binding_candidate_report_ref=fixture_binding_candidate_report_ref,
        source_fixture_binding_handoff_report_ref=fixture_binding_handoff_report_ref,
        ready_fixture_binding_handoff_count=fixture_binding_handoff_report.ready_item_count,
        blocked_fixture_binding_handoff_count=fixture_binding_handoff_report.blocked_item_count,
        approved_output_refs=approved_output_refs,
        proposed_target_fixture_refs=target_fixture_refs,
        checks=checks,
        required_next_gates=BUDGET_CALIBRATION_READINESS_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_calibration_readiness_report(
    report: BudgetCalibrationReadinessReport,
) -> str:
    lines = [
        "# Budget Calibration Readiness Report",
        "",
        f"**Report ID:** {report.budget_calibration_readiness_report_id}",
        f"**Status:** {report.status}",
        f"**Replay case:** {report.replay_case_id}",
        f"**Ready fixture-binding handoffs:** {report.ready_fixture_binding_handoff_count}",
        f"**Blocked fixture-binding handoffs:** {report.blocked_fixture_binding_handoff_count}",
        "",
        "## Source Artifacts",
        "",
        f"- Corpus report: `{report.source_corpus_report_ref}`",
        f"- Replay plan: `{report.source_replay_plan_ref}`",
        f"- Replay execution report: `{report.source_replay_execution_report_ref}`",
        f"- Replay review packet: `{report.source_review_packet_ref}`",
        f"- Replay review outcome report: `{report.source_review_outcome_report_ref}`",
        "- Fixture-binding candidate report: "
        f"`{report.source_fixture_binding_candidate_report_ref}`",
        f"- Fixture-binding handoff report: `{report.source_fixture_binding_handoff_report_ref}`",
        "",
        "## Candidate Binding Surface",
        "",
        "- Approved output refs: "
        + (
            ", ".join(f"`{ref}`" for ref in report.approved_output_refs)
            if report.approved_output_refs
            else "none"
        ),
        "- Proposed target fixture refs: "
        + (
            ", ".join(f"`{ref}`" for ref in report.proposed_target_fixture_refs)
            if report.proposed_target_fixture_refs
            else "none"
        ),
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
            "## Boundary Flags",
            "",
            f"- Manual fixture update review required: {report.manual_fixture_update_review_required}",
            f"- Fixture update authorized: {report.fixture_update_authorized}",
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
            "This report proves only that the synthetic calibration chain is ready for manual fixture-update review. It does not update fixtures, create a PR, apply learning, write Lake/SQLite records, submit budgets, open matters, or authorize external action.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_calibration_readiness_audit(
    *,
    corpus_report_path: str | Path,
    replay_plan_path: str | Path,
    replay_execution_report_path: str | Path,
    replay_review_packet_path: str | Path,
    replay_review_outcome_report_path: str | Path,
    fixture_binding_candidate_report_path: str | Path,
    fixture_binding_handoff_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetCalibrationReadinessReport, Path]:
    corpus_path = Path(corpus_report_path)
    plan_path = Path(replay_plan_path)
    execution_path = Path(replay_execution_report_path)
    packet_path = Path(replay_review_packet_path)
    outcome_path = Path(replay_review_outcome_report_path)
    candidate_path = Path(fixture_binding_candidate_report_path)
    handoff_path = Path(fixture_binding_handoff_report_path)
    report = build_budget_calibration_readiness_report(
        corpus_report=BudgetCalibrationCorpusReport.model_validate(load_json(corpus_path)),
        corpus_report_ref=str(corpus_path),
        replay_plan=BudgetCorpusReplayPlan.model_validate(load_json(plan_path)),
        replay_plan_ref=str(plan_path),
        replay_execution_report=BudgetCorpusReplayExecutionReport.model_validate(
            load_json(execution_path)
        ),
        replay_execution_report_ref=str(execution_path),
        replay_review_packet=BudgetCorpusReplayReviewPacket.model_validate(load_json(packet_path)),
        replay_review_packet_ref=str(packet_path),
        replay_review_outcome_report=BudgetCorpusReplayReviewOutcomeReport.model_validate(
            load_json(outcome_path)
        ),
        replay_review_outcome_report_ref=str(outcome_path),
        fixture_binding_candidate_report=BudgetFixtureBindingCandidateReport.model_validate(
            load_json(candidate_path)
        ),
        fixture_binding_candidate_report_ref=str(candidate_path),
        fixture_binding_handoff_report=BudgetFixtureBindingHandoffReport.model_validate(
            load_json(handoff_path)
        ),
        fixture_binding_handoff_report_ref=str(handoff_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / BUDGET_CALIBRATION_READINESS_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_CALIBRATION_READINESS_NOTES_FILENAME).write_text(
        render_budget_calibration_readiness_report(report),
        encoding="utf-8",
    )
    return report, run_dir
