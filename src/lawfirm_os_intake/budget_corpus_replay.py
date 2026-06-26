from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import (
    BudgetCalibrationCorpusArtifact,
    BudgetCalibrationCorpusReport,
    BudgetCorpusReplayCase,
    BudgetCorpusReplayCheck,
    BudgetCorpusReplayCommand,
    BudgetCorpusReplayPlan,
)
from .util import digest_text, load_json, new_id, now_iso, write_json


BUDGET_CORPUS_REPLAY_PLAN_FILENAME = "budget_corpus_replay_plan.json"
BUDGET_CORPUS_REPLAY_NOTES_FILENAME = "budget_corpus_replay_plan.md"

REPLAY_REQUIRED_NEXT_GATES = [
    "human_corpus_replay_review",
    "fixture_result_binding",
    "deterministic_baseline_regeneration",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]


@dataclass(frozen=True)
class BaselineReplaySpec:
    input_ref: str
    practice_profile_ref: str
    confirmation_ref: str


DEFAULT_BASELINE = BaselineReplaySpec(
    input_ref="examples/synthetic/inbound/carrier-assignment-medmal.json",
    practice_profile_ref="context/synthetic-profiles/insurance-defense-hours-only.yaml",
    confirmation_ref="examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json",
)

BASELINE_BY_HINT = {
    "auto-bi": BaselineReplaySpec(
        input_ref="examples/synthetic/inbound/carrier-assignment-auto-bi.json",
        practice_profile_ref="context/synthetic-profiles/insurance-defense.yaml",
        confirmation_ref="examples/synthetic/confirmations/carrier-assignment-auto-bi.confirmation-template.json",
    ),
    "north-star": BaselineReplaySpec(
        input_ref="examples/synthetic/inbound/north-star-messy-intake.json",
        practice_profile_ref="context/synthetic-profiles/insurance-defense.yaml",
        confirmation_ref="examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json",
    ),
}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _case_run_dir(case_id: str) -> str:
    return f"{{replay_run_dir}}/cases/{case_id}"


def _baseline_for_artifact(artifact: BudgetCalibrationCorpusArtifact) -> BaselineReplaySpec:
    searchable = " ".join([artifact.artifact_ref, *artifact.support_refs]).lower()
    for hint, baseline in BASELINE_BY_HINT.items():
        if hint in searchable:
            return baseline
    return DEFAULT_BASELINE


def _command(
    *,
    case_id: str,
    index: int,
    slug: str,
    command: str,
    purpose: str,
    input_artifact_refs: list[str],
    expected_output_refs: list[str],
    requires_prior_command_ids: list[str] | None = None,
) -> BudgetCorpusReplayCommand:
    return BudgetCorpusReplayCommand(
        command_id=f"{case_id}_cmd_{index:02d}_{slug}",
        command=command,
        purpose=purpose,
        input_artifact_refs=input_artifact_refs,
        expected_output_refs=expected_output_refs,
        requires_prior_command_ids=requires_prior_command_ids or [],
    )


def _baseline_command(
    *,
    case_id: str,
    baseline: BaselineReplaySpec,
    fixture_gold_ref: str | None = None,
) -> BudgetCorpusReplayCommand:
    case_dir = _case_run_dir(case_id)
    fixture_arg = f" --fixture-gold {fixture_gold_ref}" if fixture_gold_ref else ""
    command = (
        "lawfirm-os-intake demo "
        f"--input {baseline.input_ref} "
        f"--practice-profile {baseline.practice_profile_ref} "
        f"--confirmation-template {baseline.confirmation_ref} "
        f"--out-dir {case_dir}/baseline "
        "--adapter deterministic "
        f"--strict-evidence{fixture_arg}"
    )
    return _command(
        case_id=case_id,
        index=1,
        slug="baseline_demo",
        command=command,
        purpose=(
            "Regenerate the deterministic synthetic preflight and legal budget proposal "
            "used by this replay case."
        ),
        input_artifact_refs=[
            baseline.input_ref,
            baseline.practice_profile_ref,
            baseline.confirmation_ref,
            *([fixture_gold_ref] if fixture_gold_ref else []),
        ],
        expected_output_refs=[
            f"{case_dir}/baseline/preflight/*/intake_preflight_packet.json",
            f"{case_dir}/baseline/human_confirmation.json",
            f"{case_dir}/baseline/budget/legal_budget_proposal.json",
        ],
    )


def _budget_review_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
    baseline: BaselineReplaySpec,
) -> list[BudgetCorpusReplayCommand]:
    case_dir = _case_run_dir(case_id)
    baseline_command = _baseline_command(case_id=case_id, baseline=baseline)
    review_command = _command(
        case_id=case_id,
        index=2,
        slug="record_budget_review",
        command=(
            "lawfirm-os-intake record-budget-review "
            f"--budget {case_dir}/baseline/budget/legal_budget_proposal.json "
            f"--review {artifact.artifact_ref} "
            f"--out-dir {case_dir}/budget-review"
        ),
        purpose="Record human budget changes as append-only review evidence.",
        input_artifact_refs=[
            artifact.artifact_ref,
            f"{case_dir}/baseline/budget/legal_budget_proposal.json",
        ],
        expected_output_refs=[
            f"{case_dir}/budget-review/budget_revision_report.json",
            f"{case_dir}/budget-review/budget_revision_history.jsonl",
        ],
        requires_prior_command_ids=[baseline_command.command_id],
    )
    gate_command = _command(
        case_id=case_id,
        index=3,
        slug="review_learning_gate",
        command=(
            "lawfirm-os-intake review-learning-gate "
            f"--budget-revision-report {case_dir}/budget-review/budget_revision_report.json "
            f"--out-dir {case_dir}/learning-gate"
        ),
        purpose="Route the human-review delta through the reviewed learning gate.",
        input_artifact_refs=[f"{case_dir}/budget-review/budget_revision_report.json"],
        expected_output_refs=[
            f"{case_dir}/learning-gate/reviewed_learning_gate_report.json",
            f"{case_dir}/learning-gate/reviewed_learning_gate_candidates.jsonl",
        ],
        requires_prior_command_ids=[review_command.command_id],
    )
    return [baseline_command, review_command, gate_command]


def _actuals_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
    baseline: BaselineReplaySpec,
) -> list[BudgetCorpusReplayCommand]:
    case_dir = _case_run_dir(case_id)
    baseline_command = _baseline_command(case_id=case_id, baseline=baseline)
    actuals_command = _command(
        case_id=case_id,
        index=2,
        slug="compare_actuals",
        command=(
            "lawfirm-os-intake compare-budget-actuals "
            f"--budget {case_dir}/baseline/budget/legal_budget_proposal.json "
            f"--actuals {artifact.artifact_ref} "
            f"--out-dir {case_dir}/actuals"
        ),
        purpose="Compare synthetic actual costs to the regenerated budget proposal.",
        input_artifact_refs=[
            artifact.artifact_ref,
            f"{case_dir}/baseline/budget/legal_budget_proposal.json",
        ],
        expected_output_refs=[
            f"{case_dir}/actuals/budget_actual_comparison_report.json",
            f"{case_dir}/actuals/budget_actual_variance_candidates.jsonl",
        ],
        requires_prior_command_ids=[baseline_command.command_id],
    )
    gate_command = _command(
        case_id=case_id,
        index=3,
        slug="review_learning_gate",
        command=(
            "lawfirm-os-intake review-learning-gate "
            f"--budget-actual-comparison-report {case_dir}/actuals/budget_actual_comparison_report.json "
            f"--out-dir {case_dir}/learning-gate"
        ),
        purpose="Route actual-cost variance candidates through the reviewed learning gate.",
        input_artifact_refs=[f"{case_dir}/actuals/budget_actual_comparison_report.json"],
        expected_output_refs=[
            f"{case_dir}/learning-gate/reviewed_learning_gate_report.json",
            f"{case_dir}/learning-gate/reviewed_learning_gate_candidates.jsonl",
        ],
        requires_prior_command_ids=[actuals_command.command_id],
    )
    return [baseline_command, actuals_command, gate_command]


def _carrier_rejection_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
    baseline: BaselineReplaySpec,
) -> list[BudgetCorpusReplayCommand]:
    case_dir = _case_run_dir(case_id)
    baseline_command = _baseline_command(case_id=case_id, baseline=baseline)
    capture_command = _command(
        case_id=case_id,
        index=2,
        slug="capture_rejections",
        command=(
            "lawfirm-os-intake capture-carrier-rejections "
            f"--budget {case_dir}/baseline/budget/legal_budget_proposal.json "
            f"--source-bundle {artifact.artifact_ref} "
            f"--out-dir {case_dir}/carrier-rejections"
        ),
        purpose="Capture and reconcile synthetic carrier rejection, appeal, and missing-response evidence.",
        input_artifact_refs=[
            artifact.artifact_ref,
            f"{case_dir}/baseline/budget/legal_budget_proposal.json",
        ],
        expected_output_refs=[
            f"{case_dir}/carrier-rejections/carrier_rejection_reconciliation_report.json",
            f"{case_dir}/carrier-rejections/carrier_rejection_exception_lake_candidates.jsonl",
        ],
        requires_prior_command_ids=[baseline_command.command_id],
    )
    review_command = _command(
        case_id=case_id,
        index=3,
        slug="review_rejections",
        command=(
            "lawfirm-os-intake review-carrier-rejections "
            f"--reconciliation-report {case_dir}/carrier-rejections/carrier_rejection_reconciliation_report.json "
            f"--out-dir {case_dir}/carrier-rejection-review"
        ),
        purpose="Build the human review packet for rejection remediation and appeal follow-up.",
        input_artifact_refs=[
            f"{case_dir}/carrier-rejections/carrier_rejection_reconciliation_report.json"
        ],
        expected_output_refs=[
            f"{case_dir}/carrier-rejection-review/carrier_rejection_review_packet.json",
            f"{case_dir}/carrier-rejection-review/carrier_rejection_review_decision_template.json",
        ],
        requires_prior_command_ids=[capture_command.command_id],
    )
    learning_command = _command(
        case_id=case_id,
        index=4,
        slug="propose_rejection_learning",
        command=(
            "lawfirm-os-intake propose-carrier-rejection-learning "
            f"--review-packet {case_dir}/carrier-rejection-review/carrier_rejection_review_packet.json "
            f"--out-dir {case_dir}/carrier-rejection-learning"
        ),
        purpose="Draft candidate-only learning proposals from reviewed rejection pressure.",
        input_artifact_refs=[
            f"{case_dir}/carrier-rejection-review/carrier_rejection_review_packet.json"
        ],
        expected_output_refs=[
            f"{case_dir}/carrier-rejection-learning/carrier_rejection_learning_report.json"
        ],
        requires_prior_command_ids=[review_command.command_id],
    )
    gate_command = _command(
        case_id=case_id,
        index=5,
        slug="review_learning_gate",
        command=(
            "lawfirm-os-intake review-learning-gate "
            f"--carrier-learning-report {case_dir}/carrier-rejection-learning/carrier_rejection_learning_report.json "
            f"--out-dir {case_dir}/learning-gate"
        ),
        purpose="Route carrier rejection learning pressure through the reviewed learning gate.",
        input_artifact_refs=[
            f"{case_dir}/carrier-rejection-learning/carrier_rejection_learning_report.json"
        ],
        expected_output_refs=[
            f"{case_dir}/learning-gate/reviewed_learning_gate_report.json",
            f"{case_dir}/learning-gate/reviewed_learning_gate_candidates.jsonl",
        ],
        requires_prior_command_ids=[learning_command.command_id],
    )
    return [baseline_command, capture_command, review_command, learning_command, gate_command]


def _gold_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
    baseline: BaselineReplaySpec,
) -> list[BudgetCorpusReplayCommand]:
    baseline_command = _baseline_command(
        case_id=case_id,
        baseline=baseline,
        fixture_gold_ref=artifact.artifact_ref,
    )
    return [baseline_command]


def _learning_gate_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
) -> list[BudgetCorpusReplayCommand]:
    case_dir = _case_run_dir(case_id)
    readiness_command = _command(
        case_id=case_id,
        index=1,
        slug="promotion_readiness",
        command=(
            "lawfirm-os-intake audit-learning-promotion-readiness "
            f"--reviewed-learning-gate-report {artifact.artifact_ref} "
            f"--out-dir {case_dir}/promotion-readiness"
        ),
        purpose="Build promotion-readiness and shadow-eval planning artifacts from a reviewed learning gate.",
        input_artifact_refs=[artifact.artifact_ref],
        expected_output_refs=[
            f"{case_dir}/promotion-readiness/learning_shadow_eval_plan.json",
            f"{case_dir}/promotion-readiness/learning_promotion_readiness_report.json",
        ],
    )
    proposed_command = _command(
        case_id=case_id,
        index=2,
        slug="draft_proposed_changes",
        command=(
            "lawfirm-os-intake draft-learning-proposed-changes "
            f"--shadow-eval-plan {case_dir}/promotion-readiness/learning_shadow_eval_plan.json "
            f"--promotion-readiness-report {case_dir}/promotion-readiness/learning_promotion_readiness_report.json "
            f"--out-dir {case_dir}/proposed-changes"
        ),
        purpose="Draft candidate learning changes with why-notes and red-team objections.",
        input_artifact_refs=[
            f"{case_dir}/promotion-readiness/learning_shadow_eval_plan.json",
            f"{case_dir}/promotion-readiness/learning_promotion_readiness_report.json",
        ],
        expected_output_refs=[
            f"{case_dir}/proposed-changes/learning_proposed_change_set.json",
            f"{case_dir}/proposed-changes/learning_proposed_changes.jsonl",
        ],
        requires_prior_command_ids=[readiness_command.command_id],
    )
    return [readiness_command, proposed_command]


def _shadow_eval_commands(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
) -> list[BudgetCorpusReplayCommand]:
    case_dir = _case_run_dir(case_id)
    return [
        _command(
            case_id=case_id,
            index=1,
            slug="run_shadow_eval",
            command=(
                "lawfirm-os-intake run-learning-shadow-eval "
                "--proposed-change-set {required_learning_proposed_change_set_json} "
                f"--fixture-result {artifact.artifact_ref} "
                f"--out-dir {case_dir}/shadow-eval"
            ),
            purpose=(
                "Replay a synthetic shadow-eval result against a human-reviewed proposed "
                "change set from the prior learning-gate chain."
            ),
            input_artifact_refs=[
                "{required_learning_proposed_change_set_json}",
                artifact.artifact_ref,
            ],
            expected_output_refs=[
                f"{case_dir}/shadow-eval/learning_shadow_eval_result_report.json",
                f"{case_dir}/shadow-eval/learning_shadow_eval_results.jsonl",
            ],
        )
    ]


def _commands_for_artifact(
    case_id: str,
    artifact: BudgetCalibrationCorpusArtifact,
) -> list[BudgetCorpusReplayCommand]:
    baseline = _baseline_for_artifact(artifact)
    if artifact.artifact_kind == "budget_review_fixture":
        return _budget_review_commands(case_id, artifact, baseline)
    if artifact.artifact_kind == "actuals_fixture":
        return _actuals_commands(case_id, artifact, baseline)
    if artifact.artifact_kind == "carrier_rejection_fixture":
        return _carrier_rejection_commands(case_id, artifact, baseline)
    if artifact.artifact_kind == "reviewed_gold_fixture":
        return _gold_commands(case_id, artifact, baseline)
    if artifact.artifact_kind == "learning_gate_fixture":
        return _learning_gate_commands(case_id, artifact)
    if artifact.artifact_kind == "learning_shadow_eval_fixture":
        return _shadow_eval_commands(case_id, artifact)
    return []


def _case_for_artifact(
    *,
    artifact: BudgetCalibrationCorpusArtifact,
    source_corpus_ready: bool,
) -> BudgetCorpusReplayCase:
    case_id = _stable_id("budgetreplaycase", artifact.artifact_ref)
    baseline = _baseline_for_artifact(artifact)
    blocking_reasons: list[str] = []
    commands: list[BudgetCorpusReplayCommand] = []

    if not source_corpus_ready:
        status = "blocked_from_replay"
        blocking_reasons.append("source_corpus_report_not_ready_for_review")
    elif artifact.eligibility == "supporting_context_only":
        status = "supporting_context_only"
    elif artifact.eligibility != "eligible_for_synthetic_calibration_review":
        status = "blocked_from_replay"
        blocking_reasons.extend([*artifact.scope_failures, *artifact.boundary_failures])
    else:
        commands = _commands_for_artifact(case_id, artifact)
        if commands:
            status = "planned_for_replay"
        else:
            status = "supporting_context_only"
            blocking_reasons.append("no_replay_command_chain_for_artifact_kind")

    expected_outputs = [output for command in commands for output in command.expected_output_refs]
    required_inputs = [
        input_ref for command in commands for input_ref in command.input_artifact_refs
    ]
    return BudgetCorpusReplayCase(
        replay_case_id=case_id,
        source_artifact_id=artifact.artifact_id,
        source_artifact_ref=artifact.artifact_ref,
        artifact_kind=artifact.artifact_kind,
        calibration_role=artifact.calibration_role,
        eligibility=artifact.eligibility,
        status=status,  # type: ignore[arg-type]
        baseline_input_ref=baseline.input_ref if commands else None,
        baseline_practice_profile_ref=baseline.practice_profile_ref if commands else None,
        baseline_confirmation_ref=baseline.confirmation_ref if commands else None,
        command_chain=commands,
        required_inputs=sorted(dict.fromkeys(required_inputs)),
        expected_outputs=sorted(dict.fromkeys(expected_outputs)),
        support_refs=artifact.support_refs,
        blocking_reasons=blocking_reasons,
        required_next_gates=REPLAY_REQUIRED_NEXT_GATES,
    )


def _check(
    check_id: str,
    status: str,
    message: str,
    *,
    cases: list[BudgetCorpusReplayCase] | None = None,
) -> BudgetCorpusReplayCheck:
    return BudgetCorpusReplayCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        case_ids=[case.replay_case_id for case in cases or []],
        artifact_refs=[case.source_artifact_ref for case in cases or []],
    )


def build_budget_corpus_replay_plan(
    corpus_report: BudgetCalibrationCorpusReport,
    *,
    source_corpus_report_ref: str,
) -> BudgetCorpusReplayPlan:
    source_corpus_ready = corpus_report.status == "synthetic_corpus_ready_for_review"
    cases = [
        _case_for_artifact(
            artifact=artifact,
            source_corpus_ready=source_corpus_ready,
        )
        for artifact in corpus_report.artifacts
    ]
    planned = [case for case in cases if case.status == "planned_for_replay"]
    supporting = [case for case in cases if case.status == "supporting_context_only"]
    blocked = [case for case in cases if case.status == "blocked_from_replay"]
    checks = [
        _check(
            "source_corpus_ready",
            "passed" if source_corpus_ready else "failed",
            (
                "Source corpus report is ready for synthetic calibration review."
                if source_corpus_ready
                else f"Source corpus report status is {corpus_report.status}."
            ),
            cases=blocked if not source_corpus_ready else [],
        ),
        _check(
            "planned_cases_present",
            "passed" if planned else "warning",
            "Replay command chains exist for eligible outcome, gold, learning, or shadow-eval artifacts.",
            cases=planned,
        ),
        _check(
            "supporting_context_not_executed",
            "passed",
            "Supporting context artifacts do not receive replay command chains.",
            cases=supporting,
        ),
        _check(
            "no_learning_or_external_writes",
            "passed",
            "Replay plan is manifest-only: no calibration, mutation, Lake, SQLite, external write, or silent learning is performed.",
        ),
    ]
    if not source_corpus_ready:
        status = "blocked_by_corpus_report"
    elif planned:
        status = "replay_plan_ready_for_review"
    else:
        status = "no_replay_candidates"
    return BudgetCorpusReplayPlan(
        replay_plan_id=new_id("budgetcorpusreplay"),
        source_corpus_report_id=corpus_report.corpus_report_id,
        source_corpus_report_ref=source_corpus_report_ref,
        source_corpus_status=corpus_report.status,
        status=status,  # type: ignore[arg-type]
        case_count=len(cases),
        planned_case_count=len(planned),
        supporting_case_count=len(supporting),
        blocked_case_count=len(blocked),
        cases=cases,
        checks=checks,
        required_next_gates=REPLAY_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_corpus_replay_plan(plan: BudgetCorpusReplayPlan) -> str:
    lines = [
        "# Budget Corpus Replay Plan",
        "",
        f"**Replay plan ID:** {plan.replay_plan_id}",
        f"**Status:** {plan.status}",
        f"**Source corpus report:** {plan.source_corpus_report_ref}",
        f"**Source corpus status:** {plan.source_corpus_status}",
        f"**Cases:** {plan.case_count}",
        f"**Planned:** {plan.planned_case_count}",
        f"**Supporting only:** {plan.supporting_case_count}",
        f"**Blocked:** {plan.blocked_case_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {plan.candidate_only}",
        f"- Synthetic only: {plan.synthetic_only}",
        f"- Calibration applied: {plan.calibration_applied}",
        f"- Profile mutation performed: {plan.profile_mutation_performed}",
        f"- Template mutation performed: {plan.template_mutation_performed}",
        f"- Budget mutation performed: {plan.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {plan.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {plan.lake_write_performed}",
        f"- SQLite write performed: {plan.sqlite_write_performed}",
        f"- External writes performed: {plan.external_writes_performed}",
        f"- Silent learning performed: {plan.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in plan.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in plan.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Replay Cases", ""])
    for case in plan.cases:
        lines.append(
            f"- `{case.source_artifact_ref}`: {case.status}; "
            f"kind={case.artifact_kind}; commands={len(case.command_chain)}"
        )
        for reason in case.blocking_reasons:
            lines.append(f"  - blocked: {reason}")
        for command in case.command_chain:
            lines.append(f"  - {command.command_id}: `{command.command}`")
    lines.extend(
        [
            "",
            "This replay plan is candidate-only planning evidence. It does not execute commands, calibrate models, mutate budgets, update profiles/templates/guidelines, write Lake or SQLite records, or authorize real-data use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_corpus_replay_plan(
    *,
    corpus_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetCorpusReplayPlan, Path]:
    report_path = Path(corpus_report_path)
    corpus_report = BudgetCalibrationCorpusReport.model_validate(load_json(report_path))
    plan = build_budget_corpus_replay_plan(
        corpus_report,
        source_corpus_report_ref=str(report_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / BUDGET_CORPUS_REPLAY_PLAN_FILENAME, plan.model_dump(mode="json"))
    (run_dir / BUDGET_CORPUS_REPLAY_NOTES_FILENAME).write_text(
        render_budget_corpus_replay_plan(plan),
        encoding="utf-8",
    )
    return plan, run_dir
