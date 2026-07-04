from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBlockedDriverImpactReviewReport,
    LaborEmploymentBudgetOutputExpectationReport,
    LaborEmploymentBudgetQAGateBucket,
    LaborEmploymentBudgetQAGateCheck,
    LaborEmploymentBudgetQAGateReport,
    LaborEmploymentExecutableCoverageReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME = "labor_employment_budget_qa_gate_report.json"
LABOR_EMPLOYMENT_BUDGET_QA_GATE_NOTES_FILENAME = "labor_employment_budget_qa_gate_report.md"

REQUIRED_FAMILIES = [
    "administrative_exhaustion_agency_record",
    "ada_fmla_accommodation_leave",
    "class_collective_paga_representative",
    "discrimination_harassment",
    "epli_carrier_assignment",
    "restrictive_covenant_trade_secret",
    "retaliation_wrongful_termination",
    "wage_hour_flsa_state",
]

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "budget_generator_may_consume_only_budget_output_expectations",
    "block_amount_budget_when_expectation_state_is_blocked",
    "range_or_hours_only_budget_output_requires_review_context",
    "no_budget_submission_from_labor_employment_budget_qa_gate",
    "no_lake_or_sqlite_write_from_labor_employment_budget_qa_gate",
]


def run_labor_employment_budget_qa_gate(
    *,
    budget_output_expectations_report_path: str | Path,
    blocked_driver_impact_review_report_path: str | Path,
    executable_coverage_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetQAGateReport, Path]:
    output_path = Path(budget_output_expectations_report_path)
    blocked_path = Path(blocked_driver_impact_review_report_path)
    coverage_path = Path(executable_coverage_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_report = LaborEmploymentBudgetOutputExpectationReport.model_validate(
        load_json(output_path)
    )
    blocked_report = LaborEmploymentBlockedDriverImpactReviewReport.model_validate(
        load_json(blocked_path)
    )
    coverage_report = LaborEmploymentExecutableCoverageReport.model_validate(
        load_json(coverage_path)
    )

    buckets = _buckets(output_report)
    blocked_case_ids = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.final_allowed_budget_output == "blocked_amount_budget"
    ]
    range_case_ids = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.final_allowed_budget_output == "range_or_hours_only_pending_review"
    ]
    candidate_range_case_ids = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.final_allowed_budget_output == "candidate_range_after_review_pending_human_review"
    ]
    reviewed_nonblocking_case_ids = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.selected_for_reviewed_nonblocking_slice
    ]
    missing_blocked_reviews = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.final_allowed_budget_output == "blocked_amount_budget"
        and not case.blocked_case_review_present
    ]
    missing_nonblocking_reviews = [
        case.executable_fixture_id
        for case in output_report.cases
        if case.final_allowed_budget_output != "blocked_amount_budget"
        and not case.selected_for_reviewed_nonblocking_slice
    ]
    families_present = sorted({case.family for case in output_report.cases})
    required_missing = sorted(set(REQUIRED_FAMILIES) - set(families_present))
    output_fixture_ids = [case.executable_fixture_id for case in output_report.cases]
    coverage_fixture_ids = sorted(
        {
            fixture_id
            for case in coverage_report.case_coverage
            for fixture_id in case.executable_fixture_ids
        }
    )
    checks = _checks(
        output_report=output_report,
        blocked_report=blocked_report,
        coverage_report=coverage_report,
        blocked_case_ids=blocked_case_ids,
        range_case_ids=range_case_ids,
        candidate_range_case_ids=candidate_range_case_ids,
        missing_blocked_reviews=missing_blocked_reviews,
        missing_nonblocking_reviews=missing_nonblocking_reviews,
        required_missing=required_missing,
        output_fixture_ids=output_fixture_ids,
        coverage_fixture_ids=coverage_fixture_ids,
    )
    failed_checks = [check for check in checks if check.status == "failed"]
    labels = sorted(
        {
            "labor_employment_budget_qa_gate_candidate",
            "labor_employment_budget_output_distribution_candidate",
            *output_report.candidate_exception_lake_labels,
            *blocked_report.candidate_exception_lake_labels,
        }
    )
    generated = generated_at or now_iso()
    report_core = {
        "generated_at": generated,
        "output_report_id": output_report.budget_output_expectation_report_id,
        "blocked_report_id": blocked_report.blocked_driver_impact_review_report_id,
        "coverage_report_id": coverage_report.executable_coverage_report_id,
        "checks": [(check.check_id, check.status) for check in checks],
        "buckets": [(bucket.output_state, bucket.case_count) for bucket in buckets],
    }
    report = LaborEmploymentBudgetQAGateReport(
        budget_qa_gate_report_id="lebudgetqagate_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_qa_gate"
            if failed_checks
            else "labor_employment_budget_qa_gate_ready_for_review"
        ),
        source_budget_output_expectations_report_ref=str(output_path),
        source_budget_output_expectations_report_id=(
            output_report.budget_output_expectation_report_id
        ),
        source_budget_output_expectations_report_status=output_report.status,
        source_blocked_driver_impact_review_report_ref=str(blocked_path),
        source_blocked_driver_impact_review_report_id=(
            blocked_report.blocked_driver_impact_review_report_id
        ),
        source_blocked_driver_impact_review_report_status=blocked_report.status,
        source_executable_coverage_report_ref=str(coverage_path),
        source_executable_coverage_report_id=coverage_report.executable_coverage_report_id,
        source_executable_coverage_report_status=coverage_report.status,
        source_executable_coverage_state=coverage_report.coverage_state,
        case_count=output_report.case_count,
        executable_fixture_count=coverage_report.executable_fixture_count,
        covered_pack_case_count=coverage_report.covered_pack_case_count,
        missing_executable_pack_case_count=coverage_report.missing_executable_pack_case_count,
        blocked_amount_budget_case_count=output_report.blocked_amount_budget_case_count,
        range_or_hours_only_case_count=output_report.range_or_hours_only_case_count,
        candidate_range_after_review_case_count=(
            output_report.candidate_range_after_review_case_count
        ),
        reviewed_nonblocking_case_count=output_report.reviewed_nonblocking_case_count,
        blocked_review_case_count=output_report.blocked_review_case_count,
        required_family_count=len(REQUIRED_FAMILIES),
        covered_required_family_count=len(families_present),
        blocked_case_ids=blocked_case_ids,
        range_or_hours_only_case_ids=range_case_ids,
        candidate_range_after_review_case_ids=candidate_range_case_ids,
        reviewed_nonblocking_case_ids=reviewed_nonblocking_case_ids,
        missing_blocked_review_case_ids=missing_blocked_reviews,
        missing_nonblocking_review_case_ids=missing_nonblocking_reviews,
        required_families_present=families_present,
        required_families_missing=required_missing,
        output_state_buckets=buckets,
        checks=checks,
        candidate_exception_lake_labels=labels,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_NOTES_FILENAME).write_text(
        render_labor_employment_budget_qa_gate_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_budget_qa_gate_report(
    report: LaborEmploymentBudgetQAGateReport,
) -> str:
    lines = [
        "# Labor/Employment Budget QA Gate",
        "",
        f"**Report ID:** {report.budget_qa_gate_report_id}",
        f"**Status:** {report.status}",
        f"**Budget output expectations:** `{report.source_budget_output_expectations_report_ref}`",
        f"**Blocked driver review:** `{report.source_blocked_driver_impact_review_report_ref}`",
        f"**Executable coverage:** `{report.source_executable_coverage_report_ref}`",
        "",
        "## Distribution",
        "",
        f"- Cases: {report.case_count}",
        f"- Blocked amount-budget cases: {report.blocked_amount_budget_case_count}",
        f"- Range/hours-only cases: {report.range_or_hours_only_case_count}",
        f"- Candidate range-after-review cases: {report.candidate_range_after_review_case_count}",
        f"- Reviewed nonblocking cases: {report.reviewed_nonblocking_case_count}",
        f"- Required families covered: {report.covered_required_family_count}/{report.required_family_count}",
        f"- Missing executable pack cases: {report.missing_executable_pack_case_count}",
        "",
        "## Output Buckets",
        "",
    ]
    for bucket in report.output_state_buckets:
        lines.extend(
            [
                f"### {bucket.output_state}",
                "",
                f"- Cases: {bucket.case_count}",
                "- Fixture IDs: "
                + (
                    ", ".join(f"`{fixture}`" for fixture in bucket.executable_fixture_ids) or "none"
                ),
                "",
            ]
        )
    lines.extend(["## Checks", ""])
    for check in report.checks:
        lines.append(
            f"- {check.check_id}: {check.status}; {check.message}"
            + (
                "; blocking refs=" + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
                if check.blocking_refs
                else ""
            )
        )
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report is candidate-only synthetic QA evidence. It aggregates "
            "existing L&E budget-output evidence for review and UI display, but "
            "it does not compute dollar amounts, submit budgets, open matters, "
            "write Lake/SQLite records, mutate fixtures, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _buckets(
    output_report: LaborEmploymentBudgetOutputExpectationReport,
) -> list[LaborEmploymentBudgetQAGateBucket]:
    states = [
        "blocked_amount_budget",
        "range_or_hours_only_pending_review",
        "candidate_range_after_review_pending_human_review",
    ]
    buckets = []
    for state in states:
        fixture_ids = [
            case.executable_fixture_id
            for case in output_report.cases
            if case.final_allowed_budget_output == state
        ]
        buckets.append(
            LaborEmploymentBudgetQAGateBucket(
                output_state=state,
                case_count=len(fixture_ids),
                executable_fixture_ids=fixture_ids,
            )
        )
    return buckets


def _checks(
    *,
    output_report: LaborEmploymentBudgetOutputExpectationReport,
    blocked_report: LaborEmploymentBlockedDriverImpactReviewReport,
    coverage_report: LaborEmploymentExecutableCoverageReport,
    blocked_case_ids: list[str],
    range_case_ids: list[str],
    candidate_range_case_ids: list[str],
    missing_blocked_reviews: list[str],
    missing_nonblocking_reviews: list[str],
    required_missing: list[str],
    output_fixture_ids: list[str],
    coverage_fixture_ids: list[str],
) -> list[LaborEmploymentBudgetQAGateCheck]:
    output_fixture_id_set = set(output_fixture_ids)
    coverage_fixture_id_set = set(coverage_fixture_ids)
    missing_coverage_fixture_ids = sorted(output_fixture_id_set - coverage_fixture_id_set)
    extra_coverage_fixture_ids = sorted(coverage_fixture_id_set - output_fixture_id_set)
    return [
        _check(
            "source_reports_ready",
            output_report.status == "labor_employment_budget_output_expectations_ready_for_review"
            and blocked_report.status == "labor_employment_blocked_driver_impacts_ready_for_review"
            and coverage_report.status == "labor_employment_executable_coverage_ready_for_review",
            "Source L&E budget QA reports are ready for review.",
            evidence_refs=[
                output_report.budget_output_expectation_report_id,
                blocked_report.blocked_driver_impact_review_report_id,
                coverage_report.executable_coverage_report_id,
            ],
            blocking_refs=[
                status
                for status in [
                    output_report.status,
                    blocked_report.status,
                    coverage_report.status,
                ]
                if status
                not in {
                    "labor_employment_budget_output_expectations_ready_for_review",
                    "labor_employment_blocked_driver_impacts_ready_for_review",
                    "labor_employment_executable_coverage_ready_for_review",
                }
            ],
        ),
        _check(
            "source_report_lineage_matches",
            output_report.source_blocked_driver_impact_review_report_id
            == blocked_report.blocked_driver_impact_review_report_id
            and output_report.source_driver_impact_report_id
            == blocked_report.source_driver_impact_report_id,
            "Source reports belong to the same L&E driver-impact and blocked-review lineage.",
            evidence_refs=[
                output_report.source_driver_impact_report_id,
                output_report.source_blocked_driver_impact_review_report_id,
                blocked_report.source_driver_impact_report_id,
                blocked_report.blocked_driver_impact_review_report_id,
            ],
            blocking_refs=[
                ref
                for ref, matched in [
                    (
                        "source_blocked_driver_impact_review_report_id_mismatch",
                        output_report.source_blocked_driver_impact_review_report_id
                        == blocked_report.blocked_driver_impact_review_report_id,
                    ),
                    (
                        "source_driver_impact_report_id_mismatch",
                        output_report.source_driver_impact_report_id
                        == blocked_report.source_driver_impact_report_id,
                    ),
                ]
                if not matched
            ],
        ),
        _check(
            "coverage_fixture_ids_match_budget_output_cases",
            not missing_coverage_fixture_ids and not extra_coverage_fixture_ids,
            "Executable coverage fixture IDs match the budget-output expectation case IDs.",
            evidence_refs=sorted(output_fixture_id_set | coverage_fixture_id_set),
            blocking_refs=[
                *(
                    f"missing_from_coverage:{fixture_id}"
                    for fixture_id in missing_coverage_fixture_ids
                ),
                *(f"extra_in_coverage:{fixture_id}" for fixture_id in extra_coverage_fixture_ids),
            ],
        ),
        _check(
            "output_distribution_has_all_gate_states",
            bool(blocked_case_ids and range_case_ids and candidate_range_case_ids),
            "Synthetic L&E budget cases include blocked, range/hours-only, and candidate-range outputs.",
            evidence_refs=[case.executable_fixture_id for case in output_report.cases],
            blocking_refs=[
                state
                for state, ids in [
                    ("blocked_amount_budget", blocked_case_ids),
                    ("range_or_hours_only_pending_review", range_case_ids),
                    (
                        "candidate_range_after_review_pending_human_review",
                        candidate_range_case_ids,
                    ),
                ]
                if not ids
            ],
        ),
        _check(
            "blocked_cases_have_blocked_reviews",
            not missing_blocked_reviews,
            "Every blocked amount-budget case has blocked-driver review evidence.",
            evidence_refs=blocked_case_ids,
            blocking_refs=missing_blocked_reviews,
        ),
        _check(
            "nonblocking_cases_are_reviewed_for_replay",
            not missing_nonblocking_reviews,
            "Every nonblocking L&E budget-output case is selected by the reviewed replay slice.",
            evidence_refs=range_case_ids + candidate_range_case_ids,
            blocking_refs=missing_nonblocking_reviews,
        ),
        _check(
            "required_labor_employment_families_covered",
            not required_missing,
            "Executable budget-output cases cover the required L&E fixture families.",
            evidence_refs=REQUIRED_FAMILIES,
            blocking_refs=required_missing,
        ),
        _check(
            "no_write_boundary_preserved",
            output_report.external_writes_performed is False
            and output_report.lake_write_performed is False
            and output_report.sqlite_write_performed is False
            and blocked_report.external_writes_performed is False
            and blocked_report.lake_write_performed is False
            and blocked_report.sqlite_write_performed is False
            and coverage_report.external_writes_performed is False
            and coverage_report.lake_write_performed is False
            and coverage_report.sqlite_write_performed is False,
            "No source report performed external, Lake, or SQLite writes.",
            evidence_refs=[
                output_report.budget_output_expectation_report_id,
                blocked_report.blocked_driver_impact_review_report_id,
                coverage_report.executable_coverage_report_id,
            ],
            blocking_refs=[],
        ),
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str],
    blocking_refs: list[str],
) -> LaborEmploymentBudgetQAGateCheck:
    return LaborEmploymentBudgetQAGateCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs,
        blocking_refs=blocking_refs,
    )
