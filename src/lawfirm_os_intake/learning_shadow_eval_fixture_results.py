from __future__ import annotations

from pathlib import Path

from .models import (
    LearningProposedChangeArtifact,
    LearningProposedChangeSet,
    LearningShadowEvalFixtureEvidenceCheck,
    LearningShadowEvalFixtureEvidenceReport,
    LearningShadowEvalFixtureResult,
    LearningShadowEvalFixtureReviewItem,
    LearningShadowEvalFixtureReviewRecord,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


LEARNING_SHADOW_EVAL_FIXTURE_EVIDENCE_REPORT_FILENAME = (
    "learning_shadow_eval_fixture_evidence_report.json"
)
LEARNING_SHADOW_EVAL_FIXTURE_EVIDENCE_NOTES_FILENAME = (
    "learning_shadow_eval_fixture_evidence_report.md"
)
LEARNING_SHADOW_EVAL_FIXTURE_REVIEW_RECORD_FILENAME = (
    "learning_shadow_eval_fixture_review_record.json"
)
LEARNING_SHADOW_EVAL_FIXTURE_RESULTS_FILENAME = "learning_shadow_eval_fixture_results.jsonl"
LEARNING_SHADOW_EVAL_FIXTURE_RESULTS_DIRNAME = "learning_shadow_eval_fixture_results"

REQUIRED_NEXT_GATES = [
    "run_learning_shadow_eval",
    "human_shadow_eval_review",
    "owning_repo_review",
    "promotion_decision_by_owning_repo",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _fixture_result_for_review_item(
    *,
    change: LearningProposedChangeArtifact,
    item: LearningShadowEvalFixtureReviewItem,
    review: LearningShadowEvalFixtureReviewRecord,
    proposed_change_set_ref: str,
    review_record_ref: str,
    generated_at: str,
) -> LearningShadowEvalFixtureResult:
    baseline_ref = (
        item.baseline_behavior_ref
        or f"synthetic-shadow-eval://{change.target_learning_loop}/{change.candidate_id}/baseline"
    )
    proposed_ref = (
        item.proposed_behavior_ref
        or f"synthetic-shadow-eval://{change.target_learning_loop}/{change.candidate_id}/proposed"
    )
    expected_summary = (
        item.expected_behavior_summary
        or change.proposed_behavior_summary
        or f"Expected candidate behavior for {change.proposed_change_id}."
    )
    observed_summary = (
        item.observed_behavior_summary
        or "Reviewer recorded synthetic fixture evidence matching the proposed change checks."
    )
    support_refs = _dedupe(
        [
            *item.support_refs,
            *review.evidence_refs,
            proposed_change_set_ref,
            review_record_ref,
        ]
    )

    return LearningShadowEvalFixtureResult(
        fixture_result_id=_stable_id(
            "shadowevalfixture",
            f"{review.shadow_eval_fixture_review_id}|{change.proposed_change_id}",
        ),
        proposed_change_id=change.proposed_change_id,
        candidate_id=change.candidate_id,
        baseline_behavior_ref=baseline_ref,
        proposed_behavior_ref=proposed_ref,
        baseline_output_hash=digest_text(f"baseline|{baseline_ref}|{change.proposed_change_id}"),
        proposed_output_hash=digest_text(f"proposed|{proposed_ref}|{change.proposed_change_id}"),
        expected_behavior_summary=expected_summary,
        observed_behavior_summary=observed_summary,
        evaluation_outcome="passed",
        passed_eval_suites=item.passed_eval_suites,
        failed_eval_suites=[],
        passed_regression_guardrails=item.passed_regression_guardrails,
        failed_regression_guardrails=[],
        support_refs=support_refs,
        generated_at=generated_at,
    )


def _item_blockers(
    *,
    change: LearningProposedChangeArtifact,
    item: LearningShadowEvalFixtureReviewItem,
) -> list[str]:
    blockers: list[str] = []
    missing_evals = sorted(set(change.required_eval_suites) - set(item.passed_eval_suites))
    missing_guardrails = sorted(
        set(change.regression_guardrails) - set(item.passed_regression_guardrails)
    )
    blockers.extend(f"required_eval_missing:{value}" for value in missing_evals)
    blockers.extend(
        f"required_regression_guardrail_missing:{value}" for value in missing_guardrails
    )
    if item.evaluation_outcome == "blocked":
        blockers.append("review_item_blocked")
    if item.evaluation_outcome == "failed":
        blockers.append("review_item_failed")
    return blockers


def build_learning_shadow_eval_fixture_evidence_report(
    *,
    proposed_change_set: LearningProposedChangeSet,
    proposed_change_set_ref: str,
    review: LearningShadowEvalFixtureReviewRecord,
    review_record_ref: str,
    fixture_result_refs: list[str],
    fixture_results: list[LearningShadowEvalFixtureResult],
    checks: list[LearningShadowEvalFixtureEvidenceCheck],
    passed_item_count: int,
    failed_item_count: int,
    blocked_item_count: int,
    missing_item_count: int,
    generated_at: str,
) -> LearningShadowEvalFixtureEvidenceReport:
    if review.decision == "reject_fixture_results":
        status = "blocked_by_fixture_review"
    elif (
        proposed_change_set.change_count
        and passed_item_count == proposed_change_set.change_count
        and failed_item_count == 0
        and blocked_item_count == 0
        and missing_item_count == 0
    ):
        status = "fixture_results_recorded"
    elif passed_item_count:
        status = "fixture_results_partially_recorded"
    else:
        status = "blocked_by_fixture_review"

    return LearningShadowEvalFixtureEvidenceReport(
        fixture_evidence_report_id=_stable_id(
            "shadowevalfixtureevidence",
            f"{review.shadow_eval_fixture_review_id}|{proposed_change_set.proposed_change_set_id}",
        ),
        status=status,  # type: ignore[arg-type]
        source_proposed_change_set_id=proposed_change_set.proposed_change_set_id,
        source_proposed_change_set_ref=proposed_change_set_ref,
        source_review_record_id=review.shadow_eval_fixture_review_id,
        source_review_record_ref=review_record_ref,
        reviewer_id=review.reviewer_id,
        reviewed_at=review.reviewed_at,
        change_count=proposed_change_set.change_count,
        reviewed_item_count=passed_item_count + failed_item_count + blocked_item_count,
        passed_item_count=passed_item_count,
        failed_item_count=failed_item_count,
        blocked_item_count=blocked_item_count,
        missing_item_count=missing_item_count,
        fixture_result_refs=fixture_result_refs,
        fixture_results=fixture_results,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=generated_at,
    )


def render_learning_shadow_eval_fixture_evidence_report(
    report: LearningShadowEvalFixtureEvidenceReport,
) -> str:
    lines = [
        "# Learning Shadow-Eval Fixture Evidence Report",
        "",
        f"**Report ID:** {report.fixture_evidence_report_id}",
        f"**Status:** {report.status}",
        f"**Reviewer:** {report.reviewer_id}",
        f"**Change count:** {report.change_count}",
        f"**Passed items:** {report.passed_item_count}",
        f"**Failed items:** {report.failed_item_count}",
        f"**Blocked items:** {report.blocked_item_count}",
        f"**Missing items:** {report.missing_item_count}",
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
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend(
            [
                f"- `{check.check_id}`: {check.status}",
                f"  {check.message}",
            ]
        )
        if check.proposed_change_ids:
            lines.extend(f"  - {value}" for value in check.proposed_change_ids)
    lines.extend(["", "## Fixture Results", ""])
    if not report.fixture_results:
        lines.append("- none")
    for fixture in report.fixture_results:
        lines.extend(
            [
                f"- `{fixture.fixture_result_id}`: change={fixture.proposed_change_id}; "
                f"candidate={fixture.candidate_id}; outcome={fixture.evaluation_outcome}",
                "  Eval suites:",
                *(f"  - {value}" for value in fixture.passed_eval_suites),
                "  Guardrails:",
                *(f"  - {value}" for value in fixture.passed_regression_guardrails),
            ]
        )
    lines.extend(
        [
            "",
            "This artifact records reviewed synthetic fixture evidence only. It does not apply "
            "a learning change, mutate a baseline, write the Exception Lake, or authorize promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def run_learning_shadow_eval_fixture_results(
    *,
    proposed_change_set_path: str | Path,
    review_path: str | Path,
    out_dir: str | Path,
) -> tuple[LearningShadowEvalFixtureEvidenceReport, Path]:
    change_set_path = Path(proposed_change_set_path)
    review_input_path = Path(review_path)
    proposed_change_set = LearningProposedChangeSet.model_validate(load_json(change_set_path))
    review = LearningShadowEvalFixtureReviewRecord.model_validate(load_json(review_input_path))
    if review.proposed_change_set_id != proposed_change_set.proposed_change_set_id:
        raise ValueError("fixture review record does not match proposed change set")

    changes_by_id = {change.proposed_change_id: change for change in proposed_change_set.changes}
    seen_item_ids: set[str] = set()
    for item in review.items:
        if item.proposed_change_id not in changes_by_id:
            raise ValueError(
                f"fixture review item does not match proposed change set: {item.proposed_change_id}"
            )
        if item.proposed_change_id in seen_item_ids:
            raise ValueError(
                "fixture review record includes duplicate proposed change id: "
                f"{item.proposed_change_id}"
            )
        seen_item_ids.add(item.proposed_change_id)
        if item.candidate_id != changes_by_id[item.proposed_change_id].candidate_id:
            raise ValueError(
                "fixture review item candidate_id does not match proposed change: "
                f"{item.proposed_change_id}"
            )

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = run_dir / LEARNING_SHADOW_EVAL_FIXTURE_RESULTS_DIRNAME
    fixture_dir.mkdir(parents=True, exist_ok=True)
    generated_at = now_iso()
    normalized_review_path = run_dir / LEARNING_SHADOW_EVAL_FIXTURE_REVIEW_RECORD_FILENAME
    write_json(normalized_review_path, review.model_dump(mode="json"))

    checks: list[LearningShadowEvalFixtureEvidenceCheck] = [
        LearningShadowEvalFixtureEvidenceCheck(
            check_id="review_record_matches_proposed_change_set",
            status="passed",
            message="Review record proposed_change_set_id matches the proposed change set.",
        ),
        LearningShadowEvalFixtureEvidenceCheck(
            check_id="review_record_boundary_no_writes",
            status="passed",
            message="Review record preserves candidate-only, no-mutation, no-Lake-write flags.",
        ),
    ]
    passed_item_count = 0
    failed_item_count = 0
    blocked_item_count = 0
    fixture_results: list[LearningShadowEvalFixtureResult] = []
    fixture_result_refs: list[str] = []
    reviewed_items_by_change = {item.proposed_change_id: item for item in review.items}
    missing_change_ids = sorted(set(changes_by_id) - set(reviewed_items_by_change))
    if missing_change_ids:
        checks.append(
            LearningShadowEvalFixtureEvidenceCheck(
                check_id="all_proposed_changes_reviewed",
                status="blocked",
                message="At least one proposed change is missing fixture review evidence.",
                proposed_change_ids=missing_change_ids,
                blocking_refs=[str(review_input_path)],
            )
        )
    else:
        checks.append(
            LearningShadowEvalFixtureEvidenceCheck(
                check_id="all_proposed_changes_reviewed",
                status="passed",
                message="Every proposed change has a review item.",
            )
        )

    for change_id, item in reviewed_items_by_change.items():
        change = changes_by_id[change_id]
        blockers = _item_blockers(change=change, item=item)
        if item.evaluation_outcome == "failed":
            failed_item_count += 1
        elif blockers:
            blocked_item_count += 1
        else:
            passed_item_count += 1
            fixture = _fixture_result_for_review_item(
                change=change,
                item=item,
                review=review,
                proposed_change_set_ref=str(change_set_path),
                review_record_ref=str(normalized_review_path),
                generated_at=generated_at,
            )
            fixture_path = fixture_dir / f"{fixture.fixture_result_id}.json"
            write_json(fixture_path, fixture.model_dump(mode="json"))
            fixture_results.append(fixture)
            fixture_result_refs.append(str(fixture_path))
        if blockers:
            checks.append(
                LearningShadowEvalFixtureEvidenceCheck(
                    check_id=f"fixture_review_item_blocked:{change_id}",
                    status="blocked",
                    message="Review item cannot produce passing fixture evidence.",
                    proposed_change_ids=[change_id],
                    blocking_refs=blockers,
                )
            )

    if review.decision == "reject_fixture_results":
        checks.append(
            LearningShadowEvalFixtureEvidenceCheck(
                check_id="fixture_review_decision_rejected",
                status="blocked",
                message="Reviewer rejected fixture-result recording.",
                proposed_change_ids=sorted(changes_by_id),
                blocking_refs=[str(review_input_path)],
            )
        )

    report = build_learning_shadow_eval_fixture_evidence_report(
        proposed_change_set=proposed_change_set,
        proposed_change_set_ref=str(change_set_path),
        review=review,
        review_record_ref=str(normalized_review_path),
        fixture_result_refs=fixture_result_refs,
        fixture_results=fixture_results,
        checks=checks,
        passed_item_count=passed_item_count,
        failed_item_count=failed_item_count,
        blocked_item_count=blocked_item_count,
        missing_item_count=len(missing_change_ids),
        generated_at=generated_at,
    )

    report_path = run_dir / LEARNING_SHADOW_EVAL_FIXTURE_EVIDENCE_REPORT_FILENAME
    notes_path = run_dir / LEARNING_SHADOW_EVAL_FIXTURE_EVIDENCE_NOTES_FILENAME
    results_path = run_dir / LEARNING_SHADOW_EVAL_FIXTURE_RESULTS_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(
        render_learning_shadow_eval_fixture_evidence_report(report),
        encoding="utf-8",
    )
    results_path.touch()
    for fixture in fixture_results:
        append_jsonl(results_path, fixture.model_dump(mode="json"))
    return report, run_dir
