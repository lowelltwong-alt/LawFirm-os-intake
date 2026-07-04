from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentDriverImpactReviewCaseResult,
    LaborEmploymentDriverImpactReviewCaseSpec,
    LaborEmploymentDriverImpactReviewReport,
    LaborEmploymentDriverImpactReviewSpec,
    LaborEmploymentExecutableDriverImpactCase,
    LaborEmploymentExecutableDriverImpactCheck,
    LaborEmploymentExecutableDriverImpactReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME = (
    "labor_employment_driver_impact_review_report.json"
)
LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_NOTES_FILENAME = (
    "labor_employment_driver_impact_review_report.md"
)
LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME = (
    "labor_employment_driver_impact_reviewed_slice_report.json"
)

DEFAULT_LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_SPEC = (
    "examples/synthetic/gold/labor-employment-driver-impact-review.json"
)

REVIEW_REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "budget_generator_may_consume_only_reviewed_nonblocking_slice",
    "range_or_hours_only_budget_output_pending_review",
    "no_amount_budget_from_blocked_driver_impact_cases",
    "no_lake_or_sqlite_write_from_driver_impact_review",
]


def run_labor_employment_driver_impact_review(
    *,
    review_spec_path: str | Path = DEFAULT_LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_SPEC,
    driver_impact_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentDriverImpactReviewReport, Path]:
    spec_path = Path(review_spec_path)
    impact_path = Path(driver_impact_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    spec = LaborEmploymentDriverImpactReviewSpec.model_validate(load_json(spec_path))
    source_report = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(impact_path)
    )
    cases_by_id = {case.executable_fixture_id: case for case in source_report.cases}
    case_results = [
        _case_result(case_spec, cases_by_id.get(case_spec.executable_fixture_id))
        for case_spec in spec.cases
    ]
    checks = _checks(spec=spec, source_report=source_report, case_results=case_results)
    selected_cases = [
        cases_by_id[result.executable_fixture_id]
        for result in case_results
        if result.selected_for_reviewed_slice
    ]
    failed_cases = [result for result in case_results if result.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    status = (
        "blocked_by_labor_employment_driver_impact_review"
        if failed_cases or failed_checks
        else "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
    )
    slice_path: Path | None = None
    if status == "labor_employment_driver_impact_review_ready_for_budget_gate_replay":
        slice_report = _reviewed_slice_report(
            source_report=source_report,
            selected_cases=selected_cases,
            review_spec_ref=str(spec_path),
        )
        slice_path = output_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEWED_SLICE_REPORT_FILENAME
        write_json(slice_path, slice_report.model_dump(mode="json"))

    report = _review_report(
        spec=spec,
        source_report=source_report,
        spec_path=spec_path,
        impact_path=impact_path,
        slice_path=slice_path,
        status=status,
        case_results=case_results,
        checks=checks,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_NOTES_FILENAME).write_text(
        render_labor_employment_driver_impact_review_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_driver_impact_review_report(
    report: LaborEmploymentDriverImpactReviewReport,
) -> str:
    lines = [
        "# Labor/Employment Driver Impact Review Report",
        "",
        f"**Report ID:** {report.driver_impact_review_report_id}",
        f"**Status:** {report.status}",
        f"**Review spec:** `{report.review_spec_ref}`",
        f"**Source driver impact report:** `{report.source_driver_impact_report_ref}`",
        f"**Reviewed slice:** `{report.reviewed_slice_report_ref or 'not emitted'}`",
        "",
        "## Summary",
        "",
        f"- Review cases: {report.case_count}",
        f"- Selected cases: {report.selected_case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Selected block impacts: {report.block_amount_budget_impact_count}",
        f"- Selected range impacts: {report.range_widening_impact_count}",
        f"- Selected scenario forks: {report.scenario_fork_impact_count}",
        f"- Selected rate/guideline reviews: {report.rate_guideline_review_impact_count}",
        f"- Max range-widening factor: {report.max_range_widening_factor}",
        "",
        "## Cases",
        "",
    ]
    for result in report.case_results:
        lines.extend(
            [
                f"### {result.executable_fixture_id}",
                "",
                f"- Status: {result.status}",
                f"- Selected for reviewed slice: {result.selected_for_reviewed_slice}",
                f"- Allowed budget output: {result.allowed_budget_output or 'missing'}",
                f"- Block impacts: {result.block_amount_budget_impact_count}",
                f"- Range impacts: {result.range_widening_impact_count}",
                f"- Scenario forks: {result.scenario_fork_impact_count}",
                f"- Rate/guideline reviews: {result.rate_guideline_review_impact_count}",
                "- Failures: " + (", ".join(f"`{item}`" for item in result.failure_ids) or "none"),
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
            "This review is candidate-only synthetic evidence. It may materialize a "
            "nonblocking driver-impact slice for local budget-gate replay, but it does "
            "not compute dollar amounts, approve calibration, submit budgets, open "
            "matters, or write Lake/SQLite records.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_result(
    case_spec: LaborEmploymentDriverImpactReviewCaseSpec,
    source_case: LaborEmploymentExecutableDriverImpactCase | None,
) -> LaborEmploymentDriverImpactReviewCaseResult:
    failures: list[str] = []
    if source_case is None:
        failures.append("source_driver_impact_case_missing")
        return LaborEmploymentDriverImpactReviewCaseResult(
            executable_fixture_id=case_spec.executable_fixture_id,
            status="failed",
            review_outcome=case_spec.review_outcome,
            selected_for_reviewed_slice=False,
            block_amount_budget_impact_count=0,
            range_widening_impact_count=0,
            scenario_fork_impact_count=0,
            rate_guideline_review_impact_count=0,
            failure_ids=failures,
            evidence_refs=case_spec.evidence_refs,
        )
    if source_case.status != "passed":
        failures.append("source_driver_impact_case_not_passed")
    if source_case.allowed_budget_output != case_spec.expected_allowed_budget_output:
        failures.append("allowed_budget_output_mismatch")
    if (
        source_case.block_amount_budget_impact_count
        != case_spec.expected_block_amount_budget_impact_count
    ):
        failures.append("block_amount_budget_impact_count_mismatch")
    if source_case.block_amount_budget_impact_count > 0:
        failures.append("amount_budget_block_present")
    if source_case.range_widening_impact_count < case_spec.minimum_range_widening_impact_count:
        failures.append("missing_expected_range_widening_impact")
    if source_case.scenario_fork_impact_count < case_spec.minimum_scenario_fork_impact_count:
        failures.append("missing_expected_scenario_fork")
    if (
        source_case.rate_guideline_review_impact_count
        < case_spec.minimum_rate_guideline_review_impact_count
    ):
        failures.append("missing_expected_rate_guideline_review")
    return LaborEmploymentDriverImpactReviewCaseResult(
        executable_fixture_id=case_spec.executable_fixture_id,
        status="failed" if failures else "passed",
        review_outcome=case_spec.review_outcome,
        selected_for_reviewed_slice=not failures,
        allowed_budget_output=source_case.allowed_budget_output,
        block_amount_budget_impact_count=source_case.block_amount_budget_impact_count,
        range_widening_impact_count=source_case.range_widening_impact_count,
        scenario_fork_impact_count=source_case.scenario_fork_impact_count,
        rate_guideline_review_impact_count=source_case.rate_guideline_review_impact_count,
        failure_ids=sorted(set(failures)),
        evidence_refs=case_spec.evidence_refs,
    )


def _checks(
    *,
    spec: LaborEmploymentDriverImpactReviewSpec,
    source_report: LaborEmploymentExecutableDriverImpactReport,
    case_results: list[LaborEmploymentDriverImpactReviewCaseResult],
) -> list[LaborEmploymentExecutableDriverImpactCheck]:
    failed_results = [
        result.executable_fixture_id for result in case_results if result.status == "failed"
    ]
    selected_results = [result for result in case_results if result.selected_for_reviewed_slice]
    selected_ids = sorted(result.executable_fixture_id for result in selected_results)
    nonblocking_source_ids = _nonblocking_source_case_ids(source_report)
    missing_nonblocking_review_ids = [
        case_id for case_id in nonblocking_source_ids if case_id not in selected_ids
    ]
    unexpected_selected_ids = [
        case_id for case_id in selected_ids if case_id not in nonblocking_source_ids
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
        if getattr(source_report, flag, False) is not False
    ]
    return [
        _check(
            "source_driver_impact_report_ready",
            source_report.status == spec.source_driver_impact_report_expected_status,
            "Source driver-impact report is ready before reviewed slice selection.",
            evidence_refs=[source_report.executable_driver_impact_report_id],
            blocking_refs=[]
            if source_report.status == spec.source_driver_impact_report_expected_status
            else [source_report.status],
        ),
        _check(
            "reviewed_cases_match_expected_nonblocking_impacts",
            not failed_results,
            "Every reviewed case matches expected nonblocking driver-impact counts.",
            evidence_refs=[result.executable_fixture_id for result in case_results],
            blocking_refs=failed_results,
        ),
        _check(
            "reviewed_slice_has_required_case_count",
            len(selected_results) == spec.required_selected_case_count,
            "Reviewed slice selected exactly the spec-approved nonblocking cases.",
            evidence_refs=[result.executable_fixture_id for result in selected_results],
            blocking_refs=[]
            if len(selected_results) == spec.required_selected_case_count
            else [str(len(selected_results)), str(spec.required_selected_case_count)],
        ),
        _check(
            "reviewed_slice_has_no_amount_budget_blocks",
            sum(result.block_amount_budget_impact_count for result in selected_results) == 0,
            "Reviewed slice excludes amount-budget blockers.",
            evidence_refs=[result.executable_fixture_id for result in selected_results],
            blocking_refs=[
                result.executable_fixture_id
                for result in selected_results
                if result.block_amount_budget_impact_count > 0
            ],
        ),
        _check(
            "reviewed_slice_covers_all_nonblocking_source_cases",
            not missing_nonblocking_review_ids and not unexpected_selected_ids,
            "Reviewed slice covers every source case eligible for nonblocking budget-gate replay.",
            evidence_refs=nonblocking_source_ids,
            blocking_refs=missing_nonblocking_review_ids + unexpected_selected_ids,
        ),
        _check(
            "review_side_effect_boundaries_hold",
            not side_effects,
            "Review did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[source_report.executable_driver_impact_report_id],
            blocking_refs=side_effects,
        ),
    ]


def _nonblocking_source_case_ids(
    source_report: LaborEmploymentExecutableDriverImpactReport,
) -> list[str]:
    return sorted(
        case.executable_fixture_id
        for case in source_report.cases
        if case.allowed_budget_output != "blocked_amount_budget"
        and case.block_amount_budget_impact_count == 0
    )


def _reviewed_slice_report(
    *,
    source_report: LaborEmploymentExecutableDriverImpactReport,
    selected_cases: list[LaborEmploymentExecutableDriverImpactCase],
    review_spec_ref: str,
) -> LaborEmploymentExecutableDriverImpactReport:
    checks = [
        _check(
            "reviewed_slice_source_report_ready",
            True,
            "Reviewed slice was materialized from a ready source impact report.",
            evidence_refs=[source_report.executable_driver_impact_report_id],
        ),
        _check(
            "reviewed_slice_has_only_nonblocking_cases",
            True,
            "Reviewed slice contains only cases with zero amount-budget block impacts.",
            evidence_refs=[case.executable_fixture_id for case in selected_cases],
        ),
        _check(
            "reviewed_slice_spec_bound",
            True,
            "Reviewed slice remains bound to its synthetic review spec.",
            evidence_refs=[review_spec_ref],
        ),
    ]
    report_core = {
        "source_report_id": source_report.executable_driver_impact_report_id,
        "review_spec_ref": review_spec_ref,
        "selected_cases": [case.executable_fixture_id for case in selected_cases],
    }
    return LaborEmploymentExecutableDriverImpactReport(
        executable_driver_impact_report_id="leexecdriverimpactreviewedslice_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status="labor_employment_executable_driver_impacts_ready_for_review",
        executable_driver_binding_report_ref=source_report.executable_driver_binding_report_ref,
        case_count=len(selected_cases),
        failed_case_count=0,
        impact_item_count=sum(case.impact_item_count for case in selected_cases),
        source_bound_impact_count=sum(case.source_bound_impact_count for case in selected_cases),
        block_amount_budget_impact_count=sum(
            case.block_amount_budget_impact_count for case in selected_cases
        ),
        critical_review_only_impact_count=sum(
            case.critical_review_only_impact_count for case in selected_cases
        ),
        range_widening_impact_count=sum(
            case.range_widening_impact_count for case in selected_cases
        ),
        scenario_fork_impact_count=sum(case.scenario_fork_impact_count for case in selected_cases),
        rate_guideline_review_impact_count=sum(
            case.rate_guideline_review_impact_count for case in selected_cases
        ),
        human_review_impact_count=sum(case.human_review_impact_count for case in selected_cases),
        max_range_widening_factor=max(
            [case.max_range_widening_factor for case in selected_cases],
            default=1.0,
        ),
        impact_policy_dimensions=source_report.impact_policy_dimensions,
        missing_impact_policy_dimensions=[],
        cases=selected_cases,
        checks=checks,
        required_next_gates=REVIEW_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def _review_report(
    *,
    spec: LaborEmploymentDriverImpactReviewSpec,
    source_report: LaborEmploymentExecutableDriverImpactReport,
    spec_path: Path,
    impact_path: Path,
    slice_path: Path | None,
    status: str,
    case_results: list[LaborEmploymentDriverImpactReviewCaseResult],
    checks: list[LaborEmploymentExecutableDriverImpactCheck],
) -> LaborEmploymentDriverImpactReviewReport:
    selected_results = [result for result in case_results if result.selected_for_reviewed_slice]
    report_core = {
        "review_spec_id": spec.review_spec_id,
        "source_report_id": source_report.executable_driver_impact_report_id,
        "case_results": [
            {
                "executable_fixture_id": result.executable_fixture_id,
                "status": result.status,
                "failures": result.failure_ids,
            }
            for result in case_results
        ],
        "slice_path": str(slice_path) if slice_path else None,
    }
    return LaborEmploymentDriverImpactReviewReport(
        driver_impact_review_report_id="ledriverimpactreview_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,  # type: ignore[arg-type]
        review_spec_ref=str(spec_path),
        source_driver_impact_report_ref=str(impact_path),
        source_driver_impact_report_id=source_report.executable_driver_impact_report_id,
        reviewed_slice_report_ref=str(slice_path) if slice_path else None,
        case_count=len(case_results),
        selected_case_count=len(selected_results),
        failed_case_count=sum(1 for result in case_results if result.status == "failed"),
        block_amount_budget_impact_count=sum(
            result.block_amount_budget_impact_count for result in selected_results
        ),
        range_widening_impact_count=sum(
            result.range_widening_impact_count for result in selected_results
        ),
        scenario_fork_impact_count=sum(
            result.scenario_fork_impact_count for result in selected_results
        ),
        rate_guideline_review_impact_count=sum(
            result.rate_guideline_review_impact_count for result in selected_results
        ),
        max_range_widening_factor=max(
            [
                case.max_range_widening_factor
                for case in source_report.cases
                if case.executable_fixture_id
                in {result.executable_fixture_id for result in selected_results}
            ],
            default=1.0,
        ),
        case_results=case_results,
        checks=checks,
        required_next_gates=REVIEW_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


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
