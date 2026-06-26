from __future__ import annotations

from pathlib import Path

from .models import (
    LearningProposedChangeArtifact,
    LearningProposedChangeSet,
    LearningShadowEvalFixtureEvidenceReport,
    LearningShadowEvalFixtureResult,
    LearningShadowEvalResult,
    LearningShadowEvalResultReport,
)
from .util import append_jsonl, digest_text, load_json, new_id, now_iso, write_json


LEARNING_SHADOW_EVAL_RESULT_REPORT_FILENAME = "learning_shadow_eval_result_report.json"
LEARNING_SHADOW_EVAL_RESULT_NOTES_FILENAME = "learning_shadow_eval_result_report.md"
LEARNING_SHADOW_EVAL_RESULTS_FILENAME = "learning_shadow_eval_results.jsonl"

REQUIRED_NEXT_GATES = [
    "human_shadow_eval_review",
    "owning_repo_review",
    "promotion_decision_by_owning_repo",
    "contract_pinning_after_owning_repo_promotion",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _result_for_missing_fixture(
    *,
    change_set: LearningProposedChangeSet,
    change: LearningProposedChangeArtifact,
) -> LearningShadowEvalResult:
    return LearningShadowEvalResult(
        shadow_eval_result_id=_stable_id("shadowevalresult", change.proposed_change_id),
        proposed_change_set_id=change_set.proposed_change_set_id,
        proposed_change_id=change.proposed_change_id,
        candidate_id=change.candidate_id,
        target_learning_loop=change.target_learning_loop,
        target_owner=change.target_owner,
        change_type=change.change_type,
        status="blocked_missing_fixture_result",
        passed_checks=[
            "proposed_change_artifact_present",
            "red_team_notes_present",
            "no_mutation_flags_false",
            "promotion_not_authorized",
        ],
        failed_checks=[],
        blocked_checks=["synthetic_shadow_eval_fixture_result_present"],
        red_team_note_count=len(change.red_team_notes),
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def _result_for_fixture(
    *,
    change_set: LearningProposedChangeSet,
    change: LearningProposedChangeArtifact,
    fixture: LearningShadowEvalFixtureResult,
    fixture_ref: str,
) -> LearningShadowEvalResult:
    passed_checks = [
        "proposed_change_artifact_present",
        "synthetic_fixture_result_present",
        "red_team_notes_present",
        "no_mutation_flags_false",
        "promotion_not_authorized",
    ]
    failed_checks: list[str] = []
    blocked_checks: list[str] = []

    if fixture.candidate_id != change.candidate_id:
        blocked_checks.append("fixture_candidate_id_matches_change")
        status = "blocked_fixture_mismatch"
    else:
        missing_evals = sorted(set(change.required_eval_suites) - set(fixture.passed_eval_suites))
        missing_guardrails = sorted(
            set(change.regression_guardrails) - set(fixture.passed_regression_guardrails)
        )
        if fixture.evaluation_outcome != "passed":
            failed_checks.append(f"fixture_evaluation_outcome:{fixture.evaluation_outcome}")
        failed_checks.extend(f"eval_suite_failed:{item}" for item in fixture.failed_eval_suites)
        failed_checks.extend(
            f"regression_guardrail_failed:{item}" for item in fixture.failed_regression_guardrails
        )
        blocked_checks.extend(f"required_eval_missing:{item}" for item in missing_evals)
        blocked_checks.extend(
            f"required_regression_guardrail_missing:{item}" for item in missing_guardrails
        )
        if failed_checks:
            status = "failed_shadow_eval"
        elif missing_evals:
            status = "blocked_missing_required_eval"
        elif missing_guardrails:
            status = "blocked_missing_regression_guardrail"
        else:
            status = "passed_for_owning_repo_review"
            passed_checks.extend(
                [
                    "required_eval_suites_passed",
                    "regression_guardrails_passed",
                    "owner_review_still_required",
                ]
            )

    return LearningShadowEvalResult(
        shadow_eval_result_id=_stable_id(
            "shadowevalresult", f"{change.proposed_change_id}|{fixture.fixture_result_id}"
        ),
        proposed_change_set_id=change_set.proposed_change_set_id,
        proposed_change_id=change.proposed_change_id,
        candidate_id=change.candidate_id,
        target_learning_loop=change.target_learning_loop,
        target_owner=change.target_owner,
        change_type=change.change_type,
        status=status,  # type: ignore[arg-type]
        fixture_result_ref=fixture_ref,
        fixture_result_id=fixture.fixture_result_id,
        baseline_behavior_ref=fixture.baseline_behavior_ref,
        proposed_behavior_ref=fixture.proposed_behavior_ref,
        baseline_output_hash=fixture.baseline_output_hash,
        proposed_output_hash=fixture.proposed_output_hash,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        blocked_checks=blocked_checks,
        red_team_note_count=len(change.red_team_notes),
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def build_learning_shadow_eval_result_report(
    *,
    proposed_change_set: LearningProposedChangeSet,
    proposed_change_set_ref: str,
    fixture_results: list[tuple[LearningShadowEvalFixtureResult, str]] | None = None,
) -> LearningShadowEvalResultReport:
    fixture_results = fixture_results or []
    fixture_by_change = {
        fixture.proposed_change_id: (fixture, fixture_ref)
        for fixture, fixture_ref in fixture_results
    }
    known_change_ids = {change.proposed_change_id for change in proposed_change_set.changes}
    unknown_fixture_ids = sorted(set(fixture_by_change) - known_change_ids)
    if unknown_fixture_ids:
        raise ValueError(
            "shadow eval fixture result does not match proposed change set: "
            + ", ".join(unknown_fixture_ids)
        )

    results = []
    for change in proposed_change_set.changes:
        fixture_pair = fixture_by_change.get(change.proposed_change_id)
        if fixture_pair is None:
            results.append(
                _result_for_missing_fixture(change_set=proposed_change_set, change=change)
            )
        else:
            fixture, fixture_ref = fixture_pair
            results.append(
                _result_for_fixture(
                    change_set=proposed_change_set,
                    change=change,
                    fixture=fixture,
                    fixture_ref=fixture_ref,
                )
            )

    passed_count = sum(1 for result in results if result.status == "passed_for_owning_repo_review")
    failed_count = sum(1 for result in results if result.status == "failed_shadow_eval")
    blocked_count = len(results) - passed_count - failed_count
    if not proposed_change_set.changes:
        status = "no_learning_candidates"
    elif failed_count:
        status = "shadow_eval_failed"
    elif blocked_count:
        status = "shadow_eval_blocked"
    else:
        status = "shadow_eval_passed_owner_review_required"

    return LearningShadowEvalResultReport(
        shadow_eval_result_report_id=new_id("shadowevalreport"),
        proposed_change_set_id=proposed_change_set.proposed_change_set_id,
        status=status,  # type: ignore[arg-type]
        source_proposed_change_set_ref=proposed_change_set_ref,
        fixture_result_refs=[fixture_ref for _, fixture_ref in fixture_results],
        change_count=proposed_change_set.change_count,
        result_count=len(results),
        passed_result_count=passed_count,
        failed_result_count=failed_count,
        blocked_result_count=blocked_count,
        target_learning_loops=proposed_change_set.target_learning_loops,
        target_owners=proposed_change_set.target_owners,
        results=results,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_learning_shadow_eval_result_report(
    report: LearningShadowEvalResultReport,
) -> str:
    lines = [
        "# Learning Shadow Eval Result Report",
        "",
        f"**Report ID:** {report.shadow_eval_result_report_id}",
        f"**Status:** {report.status}",
        f"**Change count:** {report.change_count}",
        f"**Passed:** {report.passed_result_count}",
        f"**Failed:** {report.failed_result_count}",
        f"**Blocked:** {report.blocked_result_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Non-authoritative: {report.non_authoritative}",
        f"- Promotion authorized: {report.promotion_authorized}",
        f"- Proposed changes applied: {report.proposed_changes_applied}",
        f"- Baseline mutated: {report.baseline_mutated}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Results",
        "",
    ]
    if not report.results:
        lines.append("- none")
    for result in report.results:
        lines.extend(
            [
                f"- `{result.shadow_eval_result_id}`: change={result.proposed_change_id}; "
                f"loop={result.target_learning_loop}; owner={result.target_owner}; "
                f"status={result.status}",
                "  Passed checks:",
                *(f"  - {item}" for item in result.passed_checks),
                "  Failed checks:",
                *(f"  - {item}" for item in result.failed_checks or ["none"]),
                "  Blocked checks:",
                *(f"  - {item}" for item in result.blocked_checks or ["none"]),
            ]
        )
    lines.extend(
        [
            "",
            "This report is local shadow-eval evidence only. Passing results still require human review and owning-repo promotion review; no proposed change is applied here.",
            "",
        ]
    )
    return "\n".join(lines)


def run_learning_shadow_eval_results(
    *,
    proposed_change_set_path: str | Path,
    out_dir: str | Path,
    fixture_result_paths: list[str | Path] | None = None,
    fixture_result_report_paths: list[str | Path] | None = None,
) -> tuple[LearningShadowEvalResultReport, Path]:
    change_set_path = Path(proposed_change_set_path)
    proposed_change_set = LearningProposedChangeSet.model_validate(load_json(change_set_path))
    fixture_pairs = []
    for path_value in fixture_result_paths or []:
        fixture_path = Path(path_value)
        fixture_pairs.append(
            (
                LearningShadowEvalFixtureResult.model_validate(load_json(fixture_path)),
                str(fixture_path),
            )
        )
    for path_value in fixture_result_report_paths or []:
        report_path = Path(path_value)
        fixture_evidence_report = LearningShadowEvalFixtureEvidenceReport.model_validate(
            load_json(report_path)
        )
        for fixture in fixture_evidence_report.fixture_results:
            fixture_pairs.append((fixture, str(report_path)))

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_learning_shadow_eval_result_report(
        proposed_change_set=proposed_change_set,
        proposed_change_set_ref=str(change_set_path),
        fixture_results=fixture_pairs,
    )

    report_path = run_dir / LEARNING_SHADOW_EVAL_RESULT_REPORT_FILENAME
    notes_path = run_dir / LEARNING_SHADOW_EVAL_RESULT_NOTES_FILENAME
    results_path = run_dir / LEARNING_SHADOW_EVAL_RESULTS_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_learning_shadow_eval_result_report(report), encoding="utf-8")
    results_path.touch()
    for result in report.results:
        append_jsonl(results_path, result.model_dump(mode="json"))
    return report, run_dir
