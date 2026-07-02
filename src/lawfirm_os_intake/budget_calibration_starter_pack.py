from __future__ import annotations

from pathlib import Path

from .budget_calibration_corpus import run_budget_calibration_corpus_audit
from .budget_calibration_readiness import run_budget_calibration_readiness_audit
from .budget_corpus_replay import run_budget_corpus_replay_plan
from .budget_corpus_replay_execution import run_budget_corpus_replay_execution
from .budget_corpus_replay_review import run_budget_corpus_replay_review
from .budget_corpus_replay_review_outcomes import (
    run_budget_corpus_replay_review_outcome_record,
)
from .budget_fixture_binding_handoff import run_budget_fixture_binding_handoff
from .budget_fixture_bindings import run_budget_fixture_binding_candidates
from .models import (
    BudgetCalibrationArtifactKind,
    BudgetCalibrationStarterPackReport,
    BudgetCalibrationStarterPackStep,
    BudgetCorpusReplayPlan,
    BudgetCorpusReplayReviewPacket,
    BudgetCorpusReplayReviewRecommendation,
)
from .util import digest_text, now_iso, write_json


BUDGET_CALIBRATION_STARTER_PACK_REPORT_FILENAME = "budget_calibration_starter_pack_report.json"
BUDGET_CALIBRATION_STARTER_PACK_NOTES_FILENAME = "budget_calibration_starter_pack_report.md"

STARTER_PACK_REQUIRED_NEXT_GATES = [
    "inspect_synthetic_qa_review_outcome",
    "manual_fixture_update_review",
    "no_learning_without_reviewed_gate_and_shadow_eval",
    "no_fixture_mutation_from_starter_pack",
]


def run_budget_calibration_starter_pack(
    *,
    corpus_root: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    artifact_kind: BudgetCalibrationArtifactKind = "budget_review_fixture",
    reviewed_at: str | None = None,
) -> tuple[BudgetCalibrationStarterPackReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    corpus_report, corpus_dir = run_budget_calibration_corpus_audit(
        corpus_root=corpus_root,
        repo_root=repo_root,
        out_dir=run_dir / "budget-corpus",
    )
    replay_plan, replay_plan_dir = run_budget_corpus_replay_plan(
        corpus_report_path=corpus_dir / "budget_calibration_corpus_report.json",
        out_dir=run_dir / "budget-replay-plan",
    )
    replay_case_id = _select_case_id(replay_plan, artifact_kind)
    replay_execution, replay_execution_dir = run_budget_corpus_replay_execution(
        replay_plan_path=replay_plan_dir / "budget_corpus_replay_plan.json",
        out_dir=run_dir / "budget-replay-execution",
        repo_root=repo_root,
        execute=True,
        case_ids=[replay_case_id],
    )
    review_packet, review_packet_dir = run_budget_corpus_replay_review(
        replay_execution_report_path=(
            replay_execution_dir / "budget_corpus_replay_execution_report.json"
        ),
        out_dir=run_dir / "budget-replay-review",
    )
    recommendation = _recommendation_for_case(review_packet, replay_case_id)
    outcome_input_path = write_json(
        run_dir / "synthetic-replay-review-outcome-input.json",
        _outcome_payload(
            packet=review_packet,
            recommendation=recommendation,
            reviewed_at=reviewed_at or now_iso(),
        ),
    )
    replay_outcome, replay_outcome_dir = run_budget_corpus_replay_review_outcome_record(
        review_packet_path=review_packet_dir / "budget_corpus_replay_review_packet.json",
        outcome_path=outcome_input_path,
        out_dir=run_dir / "budget-replay-review-outcome",
    )
    fixture_binding, fixture_binding_dir = run_budget_fixture_binding_candidates(
        review_packet_path=review_packet_dir / "budget_corpus_replay_review_packet.json",
        review_outcome_report_path=(
            replay_outcome_dir / "budget_corpus_replay_review_outcome_report.json"
        ),
        out_dir=run_dir / "budget-fixture-bindings",
    )
    handoff, handoff_dir = run_budget_fixture_binding_handoff(
        fixture_binding_candidate_report_path=(
            fixture_binding_dir / "budget_fixture_binding_candidate_report.json"
        ),
        out_dir=run_dir / "budget-fixture-binding-handoff",
    )
    readiness, readiness_dir = run_budget_calibration_readiness_audit(
        corpus_report_path=corpus_dir / "budget_calibration_corpus_report.json",
        replay_plan_path=replay_plan_dir / "budget_corpus_replay_plan.json",
        replay_execution_report_path=(
            replay_execution_dir / "budget_corpus_replay_execution_report.json"
        ),
        replay_review_packet_path=(review_packet_dir / "budget_corpus_replay_review_packet.json"),
        replay_review_outcome_report_path=(
            replay_outcome_dir / "budget_corpus_replay_review_outcome_report.json"
        ),
        fixture_binding_candidate_report_path=(
            fixture_binding_dir / "budget_fixture_binding_candidate_report.json"
        ),
        fixture_binding_handoff_report_path=(
            handoff_dir / "budget_fixture_binding_handoff_report.json"
        ),
        out_dir=run_dir / "budget-calibration-readiness",
    )
    report = _report(
        selected_replay_case_id=replay_case_id,
        selected_artifact_kind=artifact_kind,
        corpus_report_ref=str(corpus_dir / "budget_calibration_corpus_report.json"),
        replay_plan_ref=str(replay_plan_dir / "budget_corpus_replay_plan.json"),
        replay_execution_report_ref=str(
            replay_execution_dir / "budget_corpus_replay_execution_report.json"
        ),
        replay_review_packet_ref=str(review_packet_dir / "budget_corpus_replay_review_packet.json"),
        synthetic_review_outcome_input_ref=str(outcome_input_path),
        replay_review_outcome_report_ref=str(
            replay_outcome_dir / "budget_corpus_replay_review_outcome_report.json"
        ),
        fixture_binding_candidate_report_ref=str(
            fixture_binding_dir / "budget_fixture_binding_candidate_report.json"
        ),
        fixture_binding_handoff_report_ref=str(
            handoff_dir / "budget_fixture_binding_handoff_report.json"
        ),
        budget_calibration_readiness_report_ref=str(
            readiness_dir / "budget_calibration_readiness_report.json"
        ),
        budget_calibration_readiness_status=readiness.status,
        step_statuses=[
            ("corpus", corpus_report.status == "synthetic_corpus_ready_for_review"),
            ("replay_plan", replay_plan.status == "replay_plan_ready_for_review"),
            (
                "replay_execution",
                replay_execution.status == "execution_passed_for_review",
            ),
            (
                "replay_review_packet",
                review_packet.status == "ready_for_human_replay_review",
            ),
            (
                "synthetic_review_outcome",
                replay_outcome.status == "review_outcome_recorded_learning_still_blocked",
            ),
            (
                "fixture_binding_candidates",
                fixture_binding.status == "fixture_binding_candidates_ready_for_review",
            ),
            (
                "fixture_binding_handoff",
                handoff.status == "fixture_binding_handoff_ready_for_human_review",
            ),
            (
                "calibration_readiness",
                readiness.status == "ready_for_manual_fixture_update_review",
            ),
        ],
    )
    write_json(
        run_dir / BUDGET_CALIBRATION_STARTER_PACK_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_CALIBRATION_STARTER_PACK_NOTES_FILENAME).write_text(
        render_budget_calibration_starter_pack_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_budget_calibration_starter_pack_report(
    report: BudgetCalibrationStarterPackReport,
) -> str:
    lines = [
        "# Budget Calibration Starter Pack Report",
        "",
        f"**Report ID:** {report.starter_pack_report_id}",
        f"**Status:** {report.status}",
        f"**Replay case:** `{report.selected_replay_case_id}`",
        f"**Artifact kind:** {report.selected_artifact_kind}",
        f"**Calibration readiness:** {report.budget_calibration_readiness_status}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Synthetic only: {report.synthetic_only}",
        f"- QA fixture review only: {report.qa_fixture_review_only}",
        f"- Fixture files mutated: {report.fixture_files_mutated}",
        f"- Fixture binding applied: {report.fixture_binding_applied}",
        f"- Calibration applied: {report.calibration_applied}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Steps",
        "",
    ]
    for step in report.steps:
        lines.append(f"- {step.step_id}: {step.status}; `{step.artifact_ref}`")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This starter pack creates local synthetic QA evidence only. It does not replace real human review, update fixtures, apply calibration, write Lake/SQLite records, submit budgets, open matters, or authorize learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _select_case_id(plan: BudgetCorpusReplayPlan, artifact_kind: str) -> str:
    for case in plan.cases:
        if case.artifact_kind == artifact_kind and case.status == "planned_for_replay":
            return case.replay_case_id
    raise ValueError(f"no planned replay case found for artifact kind: {artifact_kind}")


def _recommendation_for_case(
    packet: BudgetCorpusReplayReviewPacket,
    replay_case_id: str,
) -> BudgetCorpusReplayReviewRecommendation:
    for recommendation in packet.recommendations:
        if recommendation.replay_case_id == replay_case_id:
            return recommendation
    raise ValueError(f"review packet has no recommendation for replay case: {replay_case_id}")


def _outcome_payload(
    *,
    packet: BudgetCorpusReplayReviewPacket,
    recommendation: BudgetCorpusReplayReviewRecommendation,
    reviewed_at: str,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "review_outcome_id": "synthetic-qa-review-"
        + digest_text(f"{packet.review_packet_id}|{recommendation.replay_case_id}").split(
            ":", maxsplit=1
        )[1][:16],
        "review_packet_id": packet.review_packet_id,
        "replay_case_id": recommendation.replay_case_id,
        "reviewer_id": "synthetic-qa-starter-reviewer",
        "reviewer_role": "synthetic_qa_fixture_reviewer",
        "reviewed_at": reviewed_at,
        "outcome": "approve_fixture_binding",
        "decision_reason": (
            "Synthetic QA starter pack approval used only to exercise the calibration "
            "readiness chain; it is not production human approval."
        ),
        "approved_output_refs": recommendation.output_refs,
        "rejected_output_refs": [],
        "evidence_refs": [
            packet.review_packet_id,
            recommendation.replay_case_id,
            *recommendation.output_refs,
        ],
        "required_followups": [
            "manual fixture-update review before any fixture edit",
            "reviewed learning gate and shadow eval before learning use",
        ],
    }


def _report(
    *,
    selected_replay_case_id: str,
    selected_artifact_kind: BudgetCalibrationArtifactKind,
    corpus_report_ref: str,
    replay_plan_ref: str,
    replay_execution_report_ref: str,
    replay_review_packet_ref: str,
    synthetic_review_outcome_input_ref: str,
    replay_review_outcome_report_ref: str,
    fixture_binding_candidate_report_ref: str,
    fixture_binding_handoff_report_ref: str,
    budget_calibration_readiness_report_ref: str,
    budget_calibration_readiness_status: str,
    step_statuses: list[tuple[str, bool]],
) -> BudgetCalibrationStarterPackReport:
    artifact_by_step = {
        "corpus": corpus_report_ref,
        "replay_plan": replay_plan_ref,
        "replay_execution": replay_execution_report_ref,
        "replay_review_packet": replay_review_packet_ref,
        "synthetic_review_outcome": replay_review_outcome_report_ref,
        "fixture_binding_candidates": fixture_binding_candidate_report_ref,
        "fixture_binding_handoff": fixture_binding_handoff_report_ref,
        "calibration_readiness": budget_calibration_readiness_report_ref,
    }
    steps = [
        BudgetCalibrationStarterPackStep(
            step_id=step_id,
            status="passed" if passed else "failed",
            artifact_ref=artifact_by_step[step_id],
            notes=[
                "Synthetic QA starter-pack step."
                if step_id != "synthetic_review_outcome"
                else "Synthetic QA review outcome; not production human approval."
            ],
        )
        for step_id, passed in step_statuses
    ]
    failed_steps = [step for step in steps if step.status == "failed"]
    status = (
        "starter_pack_ready_for_manual_fixture_update_review"
        if not failed_steps
        and budget_calibration_readiness_status == "ready_for_manual_fixture_update_review"
        else "blocked_by_starter_pack"
    )
    return BudgetCalibrationStarterPackReport(
        starter_pack_report_id="budgetcalibrationstarter_"
        + digest_text(
            "|".join(
                [
                    selected_replay_case_id,
                    selected_artifact_kind,
                    budget_calibration_readiness_report_ref,
                    budget_calibration_readiness_status,
                ]
            )
        ).split(":", maxsplit=1)[1][:20],
        status=status,  # type: ignore[arg-type]
        selected_replay_case_id=selected_replay_case_id,
        selected_artifact_kind=selected_artifact_kind,
        corpus_report_ref=corpus_report_ref,
        replay_plan_ref=replay_plan_ref,
        replay_execution_report_ref=replay_execution_report_ref,
        replay_review_packet_ref=replay_review_packet_ref,
        synthetic_review_outcome_input_ref=synthetic_review_outcome_input_ref,
        replay_review_outcome_report_ref=replay_review_outcome_report_ref,
        fixture_binding_candidate_report_ref=fixture_binding_candidate_report_ref,
        fixture_binding_handoff_report_ref=fixture_binding_handoff_report_ref,
        budget_calibration_readiness_report_ref=budget_calibration_readiness_report_ref,
        budget_calibration_readiness_status=budget_calibration_readiness_status,  # type: ignore[arg-type]
        step_count=len(steps),
        failed_step_count=len(failed_steps),
        steps=steps,
        required_next_gates=STARTER_PACK_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
