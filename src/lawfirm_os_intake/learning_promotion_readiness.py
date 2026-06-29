from __future__ import annotations

from pathlib import Path

from .models import (
    LearningPromotionReadinessCheck,
    LearningPromotionReadinessReport,
    LearningShadowEvalCase,
    LearningShadowEvalPlan,
    ReviewedLearningGateCandidate,
    ReviewedLearningGateReport,
)
from .util import digest_text, load_json, new_id, now_iso, write_json


LEARNING_SHADOW_EVAL_PLAN_FILENAME = "learning_shadow_eval_plan.json"
LEARNING_SHADOW_EVAL_PLAN_NOTES_FILENAME = "learning_shadow_eval_plan.md"
LEARNING_PROMOTION_READINESS_REPORT_FILENAME = "learning_promotion_readiness_report.json"
LEARNING_PROMOTION_READINESS_NOTES_FILENAME = "learning_promotion_readiness_report.md"

REQUIRED_PROMOTION_GATES = [
    "human_reviewed_outcome_evidence",
    "append_only_evidence_record",
    "proposed_change_artifact",
    "synthetic_fixture_update",
    "shadow_eval_result",
    "regression_check",
    "owning_repo_review",
]

REGRESSION_GUARDRAILS = [
    "no conflict conclusion",
    "no budget submission",
    "no matter opening",
    "no external writes",
    "no silent learning",
    "source evidence remains stable",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _fixture_requirements(candidate: ReviewedLearningGateCandidate) -> list[str]:
    return [
        f"Add or update synthetic fixture coverage for {candidate.target_learning_loop}.",
        f"Bind fixture expectations to source artifact {candidate.source_artifact_ref}.",
        "Include before/after candidate behavior and no-mutation boundary checks.",
    ]


def _eval_suites(candidate: ReviewedLearningGateCandidate) -> list[str]:
    suites = list(dict.fromkeys(candidate.required_evaluation))
    if "fixture-gold replay" not in suites:
        suites.append("fixture-gold replay")
    if "starter boundary regression" not in suites:
        suites.append("starter boundary regression")
    return suites


def _case_for_candidate(
    candidate: ReviewedLearningGateCandidate,
) -> LearningShadowEvalCase:
    return LearningShadowEvalCase(
        shadow_eval_case_id=_stable_id("shadoweval", candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        source_kind=candidate.source_kind,
        target_learning_loop=candidate.target_learning_loop,
        target_owner=candidate.target_owner,
        source_artifact_ref=candidate.source_artifact_ref,
        source_record_id=candidate.source_record_id,
        support_refs=candidate.support_refs,
        required_fixture_updates=_fixture_requirements(candidate),
        required_eval_suites=_eval_suites(candidate),
        regression_guardrails=REGRESSION_GUARDRAILS,
        status="blocked_missing_proposed_change",
    )


def build_learning_shadow_eval_plan(
    *,
    gate_report: ReviewedLearningGateReport,
    gate_report_ref: str,
) -> LearningShadowEvalPlan:
    cases = [_case_for_candidate(candidate) for candidate in gate_report.candidates]
    if gate_report.status == "failed":
        status = "failed"
    elif cases:
        status = "shadow_eval_required"
    else:
        status = "no_learning_candidates"
    return LearningShadowEvalPlan(
        shadow_eval_plan_id=new_id("shadowevalplan"),
        reviewed_learning_gate_report_id=gate_report.reviewed_learning_gate_report_id,
        status=status,  # type: ignore[arg-type]
        source_gate_report_ref=gate_report_ref,
        case_count=len(cases),
        cases=cases,
        required_next_gates=REQUIRED_PROMOTION_GATES,
        generated_at=now_iso(),
    )


def _check(
    check_id: str,
    status: str,
    message: str,
    candidate_ids: list[str] | None = None,
) -> LearningPromotionReadinessCheck:
    return LearningPromotionReadinessCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        candidate_ids=candidate_ids or [],
    )


def build_learning_promotion_readiness_report(
    *,
    gate_report: ReviewedLearningGateReport,
    gate_report_ref: str,
    shadow_eval_plan: LearningShadowEvalPlan,
    shadow_eval_plan_ref: str,
) -> LearningPromotionReadinessReport:
    candidate_ids = [candidate.candidate_id for candidate in gate_report.candidates]
    blocked_cases = [
        case
        for case in shadow_eval_plan.cases
        if case.status
        in {
            "blocked_missing_proposed_change",
            "blocked_missing_fixture_update",
            "blocked_missing_shadow_eval_result",
        }
    ]
    failed_gate = gate_report.status == "failed" or shadow_eval_plan.status == "failed"
    all_gate_candidates_blocked = all(
        candidate.status == "blocked_until_reviewed_learning_gate"
        for candidate in gate_report.candidates
    )
    no_mutations = (
        gate_report.profile_mutation_performed is False
        and gate_report.template_mutation_performed is False
        and gate_report.connector_mutation_performed is False
        and gate_report.budget_mutation_performed is False
        and gate_report.carrier_guideline_mutation_performed is False
        and gate_report.lake_write_performed is False
        and gate_report.external_writes_performed is False
        and gate_report.silent_learning_performed is False
        and shadow_eval_plan.proposed_changes_applied is False
        and shadow_eval_plan.baseline_mutated is False
        and shadow_eval_plan.external_writes_performed is False
        and shadow_eval_plan.silent_learning_performed is False
    )
    eval_cases_created = len(shadow_eval_plan.cases) == len(gate_report.candidates)
    checks = [
        _check(
            "reviewed_learning_gate_not_failed",
            "failed" if gate_report.status == "failed" else "passed",
            "Reviewed learning gate report must not be failed.",
            candidate_ids,
        ),
        _check(
            "gate_candidates_blocked",
            "passed" if all_gate_candidates_blocked else "failed",
            "All learning candidates remain blocked before promotion readiness.",
            candidate_ids,
        ),
        _check(
            "shadow_eval_cases_created",
            "passed" if eval_cases_created else "failed",
            "Every learning candidate has a shadow-eval case.",
            candidate_ids,
        ),
        _check(
            "no_mutations_or_external_writes",
            "passed" if no_mutations else "failed",
            "Readiness audit performs no mutation, Lake write, or external write.",
            candidate_ids,
        ),
        _check(
            "proposed_change_artifacts_present",
            "blocked" if blocked_cases else "passed",
            "Promotion remains blocked until proposed change artifacts exist.",
            [case.candidate_id for case in blocked_cases],
        ),
        _check(
            "shadow_eval_results_present",
            "blocked" if blocked_cases else "passed",
            "Promotion remains blocked until shadow eval results exist.",
            [case.candidate_id for case in blocked_cases],
        ),
        _check(
            "owning_repo_review_required",
            "blocked" if gate_report.candidates else "passed",
            "Owning repo review is required before any promotion can be considered.",
            candidate_ids,
        ),
    ]
    if failed_gate or any(check.status == "failed" for check in checks):
        status = "failed"
    elif not gate_report.candidates:
        status = "no_learning_candidates"
    else:
        status = "promotion_blocked_shadow_eval_required"

    return LearningPromotionReadinessReport(
        promotion_readiness_report_id=new_id("learningpromotion"),
        reviewed_learning_gate_report_id=gate_report.reviewed_learning_gate_report_id,
        shadow_eval_plan_id=shadow_eval_plan.shadow_eval_plan_id,
        status=status,  # type: ignore[arg-type]
        source_gate_report_ref=gate_report_ref,
        shadow_eval_plan_ref=shadow_eval_plan_ref,
        candidate_count=len(gate_report.candidates),
        blocked_candidate_count=len(blocked_cases),
        ready_candidate_count=0,
        target_learning_loops=gate_report.target_learning_loops,
        target_owners=gate_report.target_owners,
        checks=checks,
        required_next_gates=REQUIRED_PROMOTION_GATES,
        generated_at=now_iso(),
    )


def render_learning_shadow_eval_plan(plan: LearningShadowEvalPlan) -> str:
    lines = [
        "# Learning Shadow Eval Plan",
        "",
        f"**Plan ID:** {plan.shadow_eval_plan_id}",
        f"**Status:** {plan.status}",
        f"**Case count:** {plan.case_count}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {item}" for item in plan.required_next_gates),
        "",
        "## Cases",
        "",
    ]
    if not plan.cases:
        lines.append("- none")
    for case in plan.cases:
        lines.extend(
            [
                f"- `{case.shadow_eval_case_id}`: candidate={case.candidate_id}; "
                f"loop={case.target_learning_loop}; owner={case.target_owner}; "
                f"status={case.status}",
                "  Fixture updates:",
                *(f"  - {item}" for item in case.required_fixture_updates),
                "  Eval suites:",
                *(f"  - {item}" for item in case.required_eval_suites),
                "  Regression guardrails:",
                *(f"  - {item}" for item in case.regression_guardrails),
            ]
        )
    lines.extend(
        [
            "",
            "This plan does not apply proposed changes or mutate baselines. It is local eval evidence only.",
            "",
        ]
    )
    return "\n".join(lines)


def render_learning_promotion_readiness_report(
    report: LearningPromotionReadinessReport,
) -> str:
    lines = [
        "# Learning Promotion Readiness Report",
        "",
        f"**Report ID:** {report.promotion_readiness_report_id}",
        f"**Status:** {report.status}",
        f"**Candidate count:** {report.candidate_count}",
        f"**Blocked candidate count:** {report.blocked_candidate_count}",
        f"**Ready candidate count:** {report.ready_candidate_count}",
        "",
        "## Boundary",
        "",
        f"- Promotion authorized: {report.promotion_authorized}",
        f"- Owning repo review required: {report.owning_repo_review_required}",
        f"- Semantic Substrate promotion required for canon: {report.semantic_substrate_promotion_required_for_canon}",
        f"- Orchestrator runtime review required: {report.orchestrator_runtime_review_required}",
        f"- Exception Lake admission required: {report.exception_lake_admission_required}",
        f"- Proposed changes applied: {report.proposed_changes_applied}",
        f"- Profile mutation performed: {report.profile_mutation_performed}",
        f"- Template mutation performed: {report.template_mutation_performed}",
        f"- Connector mutation performed: {report.connector_mutation_performed}",
        f"- Budget mutation performed: {report.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(
        [
            "",
            "This report is a readiness audit, not a promotion. Promotion remains blocked until proposed changes, fixture updates, shadow eval results, and owning-repo review exist.",
            "",
        ]
    )
    return "\n".join(lines)


def run_learning_promotion_readiness(
    *,
    reviewed_learning_gate_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LearningShadowEvalPlan, LearningPromotionReadinessReport, Path]:
    gate_path = Path(reviewed_learning_gate_report_path)
    gate_report = ReviewedLearningGateReport.model_validate(load_json(gate_path))
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    plan = build_learning_shadow_eval_plan(
        gate_report=gate_report,
        gate_report_ref=str(gate_path),
    )
    plan_path = run_dir / LEARNING_SHADOW_EVAL_PLAN_FILENAME
    plan_notes_path = run_dir / LEARNING_SHADOW_EVAL_PLAN_NOTES_FILENAME
    write_json(plan_path, plan.model_dump(mode="json"))
    plan_notes_path.write_text(render_learning_shadow_eval_plan(plan), encoding="utf-8")

    report = build_learning_promotion_readiness_report(
        gate_report=gate_report,
        gate_report_ref=str(gate_path),
        shadow_eval_plan=plan,
        shadow_eval_plan_ref=str(plan_path),
    )
    report_path = run_dir / LEARNING_PROMOTION_READINESS_REPORT_FILENAME
    notes_path = run_dir / LEARNING_PROMOTION_READINESS_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_learning_promotion_readiness_report(report), encoding="utf-8")
    return plan, report, run_dir
