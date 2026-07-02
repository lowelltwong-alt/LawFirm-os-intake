from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBlockedDriverImpactCaseReview,
    LaborEmploymentBlockedDriverImpactReviewReport,
    LaborEmploymentBudgetOutputExpectationCase,
    LaborEmploymentBudgetOutputExpectationReport,
    LaborEmploymentDriverImpactReviewCaseResult,
    LaborEmploymentDriverImpactReviewReport,
    LaborEmploymentExecutableDriverImpactCase,
    LaborEmploymentExecutableDriverImpactCheck,
    LaborEmploymentExecutableDriverImpactReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME = (
    "labor_employment_budget_output_expectations_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_NOTES_FILENAME = (
    "labor_employment_budget_output_expectations_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "budget_generator_may_consume_only_budget_output_expectations",
    "block_amount_budget_when_expectation_state_is_blocked",
    "range_or_hours_only_budget_output_requires_review_context",
    "no_budget_submission_from_budget_output_expectations_report",
    "no_lake_or_sqlite_write_from_budget_output_expectations",
]

BASE_CASE_LABELS = {
    "labor_employment_budget_output_expectation",
    "candidate_only_budget_review_required",
}


def run_labor_employment_budget_output_expectations_audit(
    *,
    driver_impact_report_path: str | Path,
    driver_impact_review_report_path: str | Path,
    blocked_driver_impact_review_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentBudgetOutputExpectationReport, Path]:
    impact_path = Path(driver_impact_report_path)
    review_path = Path(driver_impact_review_report_path)
    blocked_review_path = Path(blocked_driver_impact_review_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    impact_report = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(impact_path)
    )
    review_report = LaborEmploymentDriverImpactReviewReport.model_validate(load_json(review_path))
    blocked_review_report = LaborEmploymentBlockedDriverImpactReviewReport.model_validate(
        load_json(blocked_review_path)
    )

    review_results = {result.executable_fixture_id: result for result in review_report.case_results}
    blocked_reviews = {
        review.executable_fixture_id: review for review in blocked_review_report.case_reviews
    }
    cases = [
        _case(
            impact_case=impact_case,
            review_result=review_results.get(impact_case.executable_fixture_id),
            blocked_review=blocked_reviews.get(impact_case.executable_fixture_id),
            impact_report=impact_report,
            review_report=review_report,
            blocked_review_report=blocked_review_report,
        )
        for impact_case in impact_report.cases
    ]
    checks = _checks(
        impact_report=impact_report,
        review_report=review_report,
        blocked_review_report=blocked_review_report,
        cases=cases,
    )
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report_core = {
        "impact_report_id": impact_report.executable_driver_impact_report_id,
        "review_report_id": review_report.driver_impact_review_report_id,
        "blocked_review_report_id": blocked_review_report.blocked_driver_impact_review_report_id,
        "cases": [
            {
                "case": case.executable_fixture_id,
                "status": case.status,
                "final": case.final_allowed_budget_output,
                "failures": case.failure_ids,
            }
            for case in cases
        ],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentBudgetOutputExpectationReport(
        budget_output_expectation_report_id="lebudgetoutputexpect_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_output_expectations"
            if failed_cases or failed_checks
            else "labor_employment_budget_output_expectations_ready_for_review"
        ),
        source_driver_impact_report_ref=str(impact_path),
        source_driver_impact_report_id=impact_report.executable_driver_impact_report_id,
        source_driver_impact_review_report_ref=str(review_path),
        source_driver_impact_review_report_id=review_report.driver_impact_review_report_id,
        source_blocked_driver_impact_review_report_ref=str(blocked_review_path),
        source_blocked_driver_impact_review_report_id=(
            blocked_review_report.blocked_driver_impact_review_report_id
        ),
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        blocked_amount_budget_case_count=sum(
            1 for case in cases if case.final_allowed_budget_output == "blocked_amount_budget"
        ),
        range_or_hours_only_case_count=sum(
            1
            for case in cases
            if case.final_allowed_budget_output == "range_or_hours_only_pending_review"
        ),
        candidate_range_after_review_case_count=sum(
            1
            for case in cases
            if case.final_allowed_budget_output
            == "candidate_range_after_review_pending_human_review"
        ),
        reviewed_nonblocking_case_count=sum(
            1 for case in cases if case.selected_for_reviewed_nonblocking_slice
        ),
        blocked_review_case_count=sum(1 for case in cases if case.blocked_case_review_present),
        candidate_exception_lake_labels=_report_labels(cases),
        cases=cases,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_NOTES_FILENAME).write_text(
        render_labor_employment_budget_output_expectations_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_budget_output_expectations_report(
    report: LaborEmploymentBudgetOutputExpectationReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Output Expectations Report",
        "",
        f"**Report ID:** {report.budget_output_expectation_report_id}",
        f"**Status:** {report.status}",
        f"**Driver impact report:** `{report.source_driver_impact_report_ref}`",
        f"**Driver impact review:** `{report.source_driver_impact_review_report_ref}`",
        f"**Blocked driver review:** `{report.source_blocked_driver_impact_review_report_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Blocked amount-budget cases: {report.blocked_amount_budget_case_count}",
        f"- Range or hours-only cases: {report.range_or_hours_only_case_count}",
        f"- Candidate range-after-review cases: {report.candidate_range_after_review_case_count}",
        f"- Reviewed nonblocking cases: {report.reviewed_nonblocking_case_count}",
        f"- Blocked-review cases: {report.blocked_review_case_count}",
        "- Candidate Lake labels: "
        + ", ".join(f"`{label}`" for label in report.candidate_exception_lake_labels),
        "",
        "## Cases",
        "",
    ]
    for case in report.cases:
        lines.extend(
            [
                f"### {case.executable_fixture_id}",
                "",
                f"- Status: {case.status}",
                f"- Family/variant: {case.family}/{case.variant}",
                f"- Final allowed output: {case.final_allowed_budget_output}",
                f"- Expectation state: {case.expectation_state}",
                f"- Selected for nonblocking replay: {case.selected_for_reviewed_nonblocking_slice}",
                f"- Blocked review present: {case.blocked_case_review_present}",
                "- Candidate Lake labels: "
                + ", ".join(f"`{label}`" for label in case.candidate_exception_lake_labels),
                "- Required next gates: "
                + ", ".join(f"`{gate}`" for gate in case.required_next_gates),
                "- Failures: "
                + (", ".join(f"`{failure}`" for failure in case.failure_ids) or "none"),
                "",
            ]
        )
    lines.extend(["## Checks", ""])
    for check in report.checks:
        blocking = (
            "; blocking refs=" + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
            if check.blocking_refs
            else ""
        )
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{blocking}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report is candidate-only synthetic QA evidence. It classifies "
            "allowed L&E budget output states for downstream test/UI review, but it "
            "does not compute dollar amounts, submit budgets, open matters, write "
            "Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _case(
    *,
    impact_case: LaborEmploymentExecutableDriverImpactCase,
    review_result: LaborEmploymentDriverImpactReviewCaseResult | None,
    blocked_review: LaborEmploymentBlockedDriverImpactCaseReview | None,
    impact_report: LaborEmploymentExecutableDriverImpactReport,
    review_report: LaborEmploymentDriverImpactReviewReport,
    blocked_review_report: LaborEmploymentBlockedDriverImpactReviewReport,
) -> LaborEmploymentBudgetOutputExpectationCase:
    if impact_case.allowed_budget_output == "blocked_amount_budget":
        return _blocked_case(
            impact_case=impact_case,
            review_result=review_result,
            blocked_review=blocked_review,
            impact_report=impact_report,
            blocked_review_report=blocked_review_report,
        )
    return _nonblocking_case(
        impact_case=impact_case,
        review_result=review_result,
        blocked_review=blocked_review,
        impact_report=impact_report,
        review_report=review_report,
    )


def _blocked_case(
    *,
    impact_case: LaborEmploymentExecutableDriverImpactCase,
    review_result: LaborEmploymentDriverImpactReviewCaseResult | None,
    blocked_review: LaborEmploymentBlockedDriverImpactCaseReview | None,
    impact_report: LaborEmploymentExecutableDriverImpactReport,
    blocked_review_report: LaborEmploymentBlockedDriverImpactReviewReport,
) -> LaborEmploymentBudgetOutputExpectationCase:
    failures = []
    if impact_case.status != "passed":
        failures.append("source_driver_impact_case_not_passed")
    if blocked_review is None:
        failures.append("blocked_case_review_missing")
    if review_result is not None and review_result.selected_for_reviewed_slice:
        failures.append("blocked_case_selected_for_nonblocking_replay")
    labels = set(BASE_CASE_LABELS)
    labels.add("budget_amount_blocked_pending_labor_employment_driver_review")
    labels.add("labor_employment_blocked_budget_output_expectation")
    gates = {
        "human_labor_employment_budget_driver_review",
        "no_amount_budget_until_blocker_facts_are_resolved",
        "no_budget_submission_from_budget_output_expectations_report",
    }
    evidence_refs = [
        impact_report.executable_driver_impact_report_id,
        blocked_review_report.blocked_driver_impact_review_report_id,
        impact_case.executable_fixture_id,
    ]
    if blocked_review is not None:
        labels.update(blocked_review.candidate_exception_lake_labels)
        gates.update(blocked_review.next_review_gates)
        evidence_refs.extend(
            [
                f"{blocked_review.executable_fixture_id}:blocked-review",
                *[fact.fact_id for fact in blocked_review.blocker_facts],
            ]
        )
    return LaborEmploymentBudgetOutputExpectationCase(
        executable_fixture_id=impact_case.executable_fixture_id,
        family=impact_case.family,
        variant=impact_case.variant,
        status="failed" if failures else "passed",
        expected_budget_readiness_state=impact_case.expected_budget_readiness_state,
        expected_budget_treatment=impact_case.expected_budget_treatment,
        source_allowed_budget_output=impact_case.allowed_budget_output,
        final_allowed_budget_output=impact_case.allowed_budget_output,
        expectation_state="blocked_amount_budget_pending_driver_review",
        selected_for_reviewed_nonblocking_slice=False,
        blocked_case_review_present=blocked_review is not None,
        amount_budget_blocked=True,
        block_amount_budget_impact_count=impact_case.block_amount_budget_impact_count,
        range_widening_impact_count=impact_case.range_widening_impact_count,
        scenario_fork_impact_count=impact_case.scenario_fork_impact_count,
        rate_guideline_review_impact_count=impact_case.rate_guideline_review_impact_count,
        candidate_exception_lake_labels=sorted(labels),
        required_next_gates=sorted(gates),
        evidence_refs=sorted(set(evidence_refs)),
        failure_ids=sorted(set(failures)),
    )


def _nonblocking_case(
    *,
    impact_case: LaborEmploymentExecutableDriverImpactCase,
    review_result: LaborEmploymentDriverImpactReviewCaseResult | None,
    blocked_review: LaborEmploymentBlockedDriverImpactCaseReview | None,
    impact_report: LaborEmploymentExecutableDriverImpactReport,
    review_report: LaborEmploymentDriverImpactReviewReport,
) -> LaborEmploymentBudgetOutputExpectationCase:
    failures = []
    if impact_case.status != "passed":
        failures.append("source_driver_impact_case_not_passed")
    if impact_case.block_amount_budget_impact_count != 0:
        failures.append("nonblocking_case_has_amount_budget_block")
    if blocked_review is not None:
        failures.append("nonblocking_case_has_blocked_review")
    if review_result is None:
        failures.append("review_result_missing")
    elif not review_result.selected_for_reviewed_slice or review_result.status != "passed":
        failures.append("review_result_not_selected_for_nonblocking_replay")
    labels = set(BASE_CASE_LABELS)
    labels.add("labor_employment_reviewed_nonblocking_budget_gate_replay")
    labels.add("budget_output_pending_human_review")
    if impact_case.allowed_budget_output == "range_or_hours_only_pending_review":
        expectation_state = "range_or_hours_only_pending_human_review"
        labels.add("labor_employment_budget_output_range_or_hours_only")
    else:
        expectation_state = "candidate_range_after_review_pending_human_review"
        labels.add("labor_employment_budget_output_candidate_range_after_review")
    gates = {
        "human_labor_employment_budget_driver_review",
        "budget_generator_may_consume_only_reviewed_nonblocking_slice",
        "preserve_candidate_only_budget_output_context",
        "no_budget_submission_from_budget_output_expectations_report",
    }
    evidence_refs = [
        impact_report.executable_driver_impact_report_id,
        review_report.driver_impact_review_report_id,
        impact_case.executable_fixture_id,
    ]
    if review_result is not None:
        evidence_refs.extend(review_result.evidence_refs)
    return LaborEmploymentBudgetOutputExpectationCase(
        executable_fixture_id=impact_case.executable_fixture_id,
        family=impact_case.family,
        variant=impact_case.variant,
        status="failed" if failures else "passed",
        expected_budget_readiness_state=impact_case.expected_budget_readiness_state,
        expected_budget_treatment=impact_case.expected_budget_treatment,
        source_allowed_budget_output=impact_case.allowed_budget_output,
        final_allowed_budget_output=impact_case.allowed_budget_output,
        expectation_state=expectation_state,
        selected_for_reviewed_nonblocking_slice=(
            review_result is not None and review_result.selected_for_reviewed_slice
        ),
        blocked_case_review_present=False,
        amount_budget_blocked=False,
        block_amount_budget_impact_count=impact_case.block_amount_budget_impact_count,
        range_widening_impact_count=impact_case.range_widening_impact_count,
        scenario_fork_impact_count=impact_case.scenario_fork_impact_count,
        rate_guideline_review_impact_count=impact_case.rate_guideline_review_impact_count,
        candidate_exception_lake_labels=sorted(labels),
        required_next_gates=sorted(gates),
        evidence_refs=sorted(set(evidence_refs)),
        failure_ids=sorted(set(failures)),
    )


def _checks(
    *,
    impact_report: LaborEmploymentExecutableDriverImpactReport,
    review_report: LaborEmploymentDriverImpactReviewReport,
    blocked_review_report: LaborEmploymentBlockedDriverImpactReviewReport,
    cases: list[LaborEmploymentBudgetOutputExpectationCase],
) -> list[LaborEmploymentExecutableDriverImpactCheck]:
    source_ids = {case.executable_fixture_id for case in impact_report.cases}
    output_ids = [case.executable_fixture_id for case in cases]
    duplicated_ids = sorted({case_id for case_id in output_ids if output_ids.count(case_id) > 1})
    missing_ids = sorted(source_ids - set(output_ids))
    failed_cases = [case.executable_fixture_id for case in cases if case.status == "failed"]
    blocked_missing_review = [
        case.executable_fixture_id
        for case in cases
        if case.final_allowed_budget_output == "blocked_amount_budget"
        and not case.blocked_case_review_present
    ]
    nonblocking_missing_review = [
        case.executable_fixture_id
        for case in cases
        if case.final_allowed_budget_output != "blocked_amount_budget"
        and not case.selected_for_reviewed_nonblocking_slice
    ]
    unlabeled = [
        case.executable_fixture_id
        for case in cases
        if not case.candidate_exception_lake_labels or not case.required_next_gates
    ]
    side_effects = [
        flag
        for flag in [
            "budget_amount_output_authorized",
            "budget_submission_authorized",
            "conflict_conclusion_emitted",
            "matter_opening_authorized",
            "training_pipeline_created",
            "lake_write_performed",
            "sqlite_write_performed",
            "external_writes_performed",
            "silent_learning_performed",
        ]
        if getattr(impact_report, flag, False) is not False
        or getattr(review_report, flag, False) is not False
        or getattr(blocked_review_report, flag, False) is not False
    ]
    return [
        _check(
            "source_reports_ready",
            impact_report.status == "labor_employment_executable_driver_impacts_ready_for_review"
            and review_report.status
            == "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
            and blocked_review_report.status
            == "labor_employment_blocked_driver_impacts_ready_for_review",
            "Driver impact, reviewed nonblocking slice, and blocked-driver review reports are ready.",
            evidence_refs=[
                impact_report.executable_driver_impact_report_id,
                review_report.driver_impact_review_report_id,
                blocked_review_report.blocked_driver_impact_review_report_id,
            ],
            blocking_refs=[
                status
                for status in [
                    impact_report.status,
                    review_report.status,
                    blocked_review_report.status,
                ]
                if not status.endswith("ready_for_review")
                and not status.endswith("ready_for_budget_gate_replay")
            ],
        ),
        _check(
            "every_source_case_has_one_output_expectation",
            not duplicated_ids and not missing_ids and len(output_ids) == impact_report.case_count,
            "Every source driver-impact case has exactly one budget-output expectation.",
            evidence_refs=sorted(source_ids),
            blocking_refs=duplicated_ids + missing_ids,
        ),
        _check(
            "blocked_cases_have_blocked_reviews",
            not blocked_missing_review,
            "Every blocked amount-budget case has blocked-driver review evidence.",
            evidence_refs=[
                case.executable_fixture_id
                for case in cases
                if case.final_allowed_budget_output == "blocked_amount_budget"
            ],
            blocking_refs=blocked_missing_review,
        ),
        _check(
            "nonblocking_cases_are_reviewed_for_replay",
            not nonblocking_missing_review,
            "Every nonblocking case is selected by the reviewed budget-gate replay slice.",
            evidence_refs=[
                case.executable_fixture_id
                for case in cases
                if case.final_allowed_budget_output != "blocked_amount_budget"
            ],
            blocking_refs=nonblocking_missing_review,
        ),
        _check(
            "case_output_expectations_pass",
            not failed_cases,
            "Every case-level budget-output expectation is internally coherent.",
            evidence_refs=output_ids,
            blocking_refs=failed_cases,
        ),
        _check(
            "case_labels_and_next_gates_present",
            not unlabeled,
            "Every output expectation has candidate labels and deterministic next gates.",
            evidence_refs=output_ids,
            blocking_refs=unlabeled,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Budget-output expectation audit did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[
                impact_report.executable_driver_impact_report_id,
                review_report.driver_impact_review_report_id,
                blocked_review_report.blocked_driver_impact_review_report_id,
            ],
            blocking_refs=side_effects,
        ),
    ]


def _report_labels(cases: list[LaborEmploymentBudgetOutputExpectationCase]) -> list[str]:
    return sorted({label for case in cases for label in case.candidate_exception_lake_labels})


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> LaborEmploymentExecutableDriverImpactCheck:
    return LaborEmploymentExecutableDriverImpactCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )
