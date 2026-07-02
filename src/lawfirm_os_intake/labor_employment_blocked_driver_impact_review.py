from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBlockedDriverImpactCaseReview,
    LaborEmploymentBlockedDriverImpactFactReview,
    LaborEmploymentBlockedDriverImpactReviewReport,
    LaborEmploymentBudgetDriverDimension,
    LaborEmploymentExecutableBudgetFactBindingCase,
    LaborEmploymentExecutableBudgetFactBindingItem,
    LaborEmploymentExecutableBudgetFactBindingReport,
    LaborEmploymentExecutableDriverBindingCase,
    LaborEmploymentExecutableDriverBindingReport,
    LaborEmploymentExecutableDriverImpactCase,
    LaborEmploymentExecutableDriverImpactCheck,
    LaborEmploymentExecutableDriverImpactReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME = (
    "labor_employment_blocked_driver_impact_review_report.json"
)
LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_NOTES_FILENAME = (
    "labor_employment_blocked_driver_impact_review_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "collect_or_confirm_missing_labor_employment_budget_driver_sources",
    "rerun_driver_fact_binding_after_append_only_correction",
    "no_amount_budget_until_blocker_facts_are_resolved",
    "no_lake_or_sqlite_write_from_blocked_driver_impact_review",
]

BASE_CANDIDATE_LAKE_LABELS = {
    "labor_employment_driver_impacts_blocked",
    "budget_amount_blocked_pending_labor_employment_driver_review",
}


def run_labor_employment_blocked_driver_impact_review(
    *,
    fact_binding_report_path: str | Path,
    driver_binding_report_path: str | Path,
    driver_impact_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentBlockedDriverImpactReviewReport, Path]:
    fact_path = Path(fact_binding_report_path)
    driver_path = Path(driver_binding_report_path)
    impact_path = Path(driver_impact_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fact_report = LaborEmploymentExecutableBudgetFactBindingReport.model_validate(
        load_json(fact_path)
    )
    driver_report = LaborEmploymentExecutableDriverBindingReport.model_validate(
        load_json(driver_path)
    )
    impact_report = LaborEmploymentExecutableDriverImpactReport.model_validate(
        load_json(impact_path)
    )
    fact_cases = {case.executable_fixture_id: case for case in fact_report.cases}
    driver_cases = {case.executable_fixture_id: case for case in driver_report.cases}
    blocked_impact_cases = [
        case
        for case in impact_report.cases
        if case.allowed_budget_output == "blocked_amount_budget"
    ]
    nonblocking_case_count = impact_report.case_count - len(blocked_impact_cases)
    case_reviews = [
        _case_review(
            impact_case=case,
            fact_case=fact_cases[case.executable_fixture_id],
            driver_case=driver_cases[case.executable_fixture_id],
        )
        for case in blocked_impact_cases
        if case.executable_fixture_id in fact_cases and case.executable_fixture_id in driver_cases
    ]
    checks = _checks(
        fact_report=fact_report,
        driver_report=driver_report,
        impact_report=impact_report,
        blocked_impact_cases=blocked_impact_cases,
        case_reviews=case_reviews,
    )
    failed_checks = [check for check in checks if check.status == "failed"]
    report_core = {
        "fact_report_id": fact_report.executable_budget_fact_binding_report_id,
        "driver_report_id": driver_report.executable_driver_binding_report_id,
        "impact_report_id": impact_report.executable_driver_impact_report_id,
        "case_reviews": [
            {
                "case": case.executable_fixture_id,
                "facts": [fact.fact_id for fact in case.blocker_facts],
                "labels": case.candidate_exception_lake_labels,
            }
            for case in case_reviews
        ],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentBlockedDriverImpactReviewReport(
        blocked_driver_impact_review_report_id="leblockeddriverimpactreview_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_blocked_driver_impact_review"
            if failed_checks
            else "labor_employment_blocked_driver_impacts_ready_for_review"
        ),
        source_fact_binding_report_ref=str(fact_path),
        source_driver_binding_report_ref=str(driver_path),
        source_driver_impact_report_ref=str(impact_path),
        source_driver_impact_report_id=impact_report.executable_driver_impact_report_id,
        case_count=impact_report.case_count,
        blocked_case_count=len(blocked_impact_cases),
        nonblocking_case_count=nonblocking_case_count,
        blocker_fact_count=sum(case.blocker_fact_count for case in case_reviews),
        block_amount_budget_impact_count=sum(
            case.block_amount_budget_impact_count for case in case_reviews
        ),
        candidate_exception_lake_labels=_report_labels(case_reviews),
        case_reviews=case_reviews,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_NOTES_FILENAME).write_text(
        render_labor_employment_blocked_driver_impact_review_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_blocked_driver_impact_review_report(
    report: LaborEmploymentBlockedDriverImpactReviewReport,
) -> str:
    lines = [
        "# Labor/Employment Blocked Driver Impact Review Report",
        "",
        f"**Report ID:** {report.blocked_driver_impact_review_report_id}",
        f"**Status:** {report.status}",
        f"**Fact binding report:** `{report.source_fact_binding_report_ref}`",
        f"**Driver binding report:** `{report.source_driver_binding_report_ref}`",
        f"**Driver impact report:** `{report.source_driver_impact_report_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Blocked cases: {report.blocked_case_count}",
        f"- Nonblocking cases: {report.nonblocking_case_count}",
        f"- Blocker facts: {report.blocker_fact_count}",
        f"- Amount-budget block impacts: {report.block_amount_budget_impact_count}",
        "- Candidate Lake labels: "
        + ", ".join(f"`{label}`" for label in report.candidate_exception_lake_labels),
        "",
        "## Blocked Cases",
        "",
    ]
    for case in report.case_reviews:
        lines.extend(
            [
                f"### {case.executable_fixture_id}",
                "",
                f"- Family/variant: {case.family}/{case.variant}",
                f"- Block reason: {case.block_reason}",
                "- Critical driver dimensions: "
                + ", ".join(f"`{dimension}`" for dimension in case.critical_driver_dimensions),
                f"- Block impacts: {case.block_amount_budget_impact_count}",
                f"- Range impacts still present: {case.range_widening_impact_count}",
                f"- Scenario forks still present: {case.scenario_fork_impact_count}",
                f"- Rate/guideline reviews still present: {case.rate_guideline_review_impact_count}",
                "- Candidate Lake labels: "
                + ", ".join(f"`{label}`" for label in case.candidate_exception_lake_labels),
                "",
            ]
        )
        for fact in case.blocker_facts:
            lines.extend(
                [
                    f"- `{fact.fact_id}`: {fact.reason}",
                    f"  - Budget effects: {', '.join(fact.budget_effects) or 'none'}",
                    "  - Matched exception labels: "
                    + (", ".join(fact.matched_exception_labels) or "none"),
                    "  - Matched source IDs: " + (", ".join(fact.matched_source_ids) or "none"),
                    "  - Unblock actions: "
                    + ", ".join(f"`{action}`" for action in fact.unblock_actions),
                ]
            )
        lines.append("")
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
            "This report is a review packet for blocked synthetic driver impacts. "
            "It explains why amount-budget output remains blocked and what human "
            "or append-only correction work could unblock rerun. It does not "
            "submit budgets, open matters, write Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_review(
    *,
    impact_case: LaborEmploymentExecutableDriverImpactCase,
    fact_case: LaborEmploymentExecutableBudgetFactBindingCase,
    driver_case: LaborEmploymentExecutableDriverBindingCase,
) -> LaborEmploymentBlockedDriverImpactCaseReview:
    blocker_facts = [
        _fact_review(binding)
        for binding in fact_case.fact_bindings
        if binding.blocks_precise_budget
    ]
    labels = _case_labels(blocker_facts)
    actions = sorted(
        {action for fact in blocker_facts for action in fact.unblock_actions}
        | {"rerun_labor_employment_driver_impact_review_after_corrections"}
    )
    critical_dimensions = _critical_dimensions(driver_case)
    return LaborEmploymentBlockedDriverImpactCaseReview(
        executable_fixture_id=impact_case.executable_fixture_id,
        family=impact_case.family,
        variant=impact_case.variant,
        allowed_budget_output="blocked_amount_budget",
        block_reason=(
            "Amount-budget output is blocked because one or more critical L&E "
            "budget facts remain unresolved or exception-bound."
        ),
        block_amount_budget_impact_count=impact_case.block_amount_budget_impact_count,
        range_widening_impact_count=impact_case.range_widening_impact_count,
        scenario_fork_impact_count=impact_case.scenario_fork_impact_count,
        rate_guideline_review_impact_count=impact_case.rate_guideline_review_impact_count,
        critical_driver_dimensions=critical_dimensions,
        blocker_fact_count=len(blocker_facts),
        blocker_facts=blocker_facts,
        candidate_exception_lake_labels=labels,
        unblock_actions=actions,
        next_review_gates=[
            "human_labor_employment_budget_driver_review",
            "append_or_supersede_missing_source_corrections",
            "rerun_budget_precondition_after_review",
        ],
    )


def _fact_review(
    binding: LaborEmploymentExecutableBudgetFactBindingItem,
) -> LaborEmploymentBlockedDriverImpactFactReview:
    labels = _fact_labels(binding)
    return LaborEmploymentBlockedDriverImpactFactReview(
        fact_id=binding.fact_id,
        required_level=binding.required_level,
        binding_state=binding.binding_state,
        blocks_precise_budget=binding.blocks_precise_budget,
        reason=binding.reason,
        budget_effects=binding.budget_effects,
        evidence_ref_count=len(binding.evidence_refs),
        source_inventory_ref_count=len(binding.source_inventory_refs),
        matched_source_signal_terms=binding.matched_source_signal_terms,
        missing_source_signal_terms=binding.missing_source_signal_terms,
        matched_exception_labels=binding.matched_exception_labels,
        missing_exception_labels=binding.missing_exception_labels,
        matched_source_ids=binding.matched_source_ids,
        missing_source_ids=binding.missing_source_ids,
        unblock_actions=_fact_unblock_actions(binding),
        candidate_exception_lake_labels=labels,
    )


def _critical_dimensions(
    driver_case: LaborEmploymentExecutableDriverBindingCase,
) -> list[LaborEmploymentBudgetDriverDimension]:
    return sorted(
        {
            binding.driver_dimension
            for binding in driver_case.driver_bindings
            if binding.critical_driver_block
        }
    )


def _fact_unblock_actions(binding: LaborEmploymentExecutableBudgetFactBindingItem) -> list[str]:
    actions = {f"human_confirm_labor_employment_budget_fact:{binding.fact_id}"}
    for source_id in binding.matched_source_ids:
        actions.add(f"collect_or_confirm_unavailable_source:{source_id}")
    for source_id in binding.missing_source_ids:
        actions.add(f"add_expected_source_inventory_ref:{source_id}")
    for label in sorted(set(binding.matched_exception_labels + binding.missing_exception_labels)):
        actions.add(f"resolve_exception_label:{label}")
    if binding.missing_source_signal_terms:
        actions.add(f"collect_source_signal_terms:{binding.fact_id}")
    if binding.evidence_refs:
        actions.add(f"human_review_source_bound_fact:{binding.fact_id}")
    return sorted(actions)


def _fact_labels(binding: LaborEmploymentExecutableBudgetFactBindingItem) -> list[str]:
    labels = set(BASE_CANDIDATE_LAKE_LABELS)
    labels.add("labor_employment_critical_budget_fact_block")
    labels.update(binding.matched_exception_labels)
    labels.update(binding.missing_exception_labels)
    if binding.matched_source_ids or binding.missing_source_ids:
        labels.add("missing_budget_driver_source_requires_follow_up")
    if binding.evidence_refs:
        labels.add("labor_employment_budget_driver_requires_human_confirmation")
    return sorted(labels)


def _case_labels(facts: list[LaborEmploymentBlockedDriverImpactFactReview]) -> list[str]:
    labels = set(BASE_CANDIDATE_LAKE_LABELS)
    for fact in facts:
        labels.update(fact.candidate_exception_lake_labels)
    return sorted(labels)


def _report_labels(cases: list[LaborEmploymentBlockedDriverImpactCaseReview]) -> list[str]:
    labels = {label for case in cases for label in case.candidate_exception_lake_labels}
    return sorted(labels)


def _checks(
    *,
    fact_report: LaborEmploymentExecutableBudgetFactBindingReport,
    driver_report: LaborEmploymentExecutableDriverBindingReport,
    impact_report: LaborEmploymentExecutableDriverImpactReport,
    blocked_impact_cases: list[LaborEmploymentExecutableDriverImpactCase],
    case_reviews: list[LaborEmploymentBlockedDriverImpactCaseReview],
) -> list[LaborEmploymentExecutableDriverImpactCheck]:
    case_review_ids = {case.executable_fixture_id for case in case_reviews}
    missing_case_reviews = [
        case.executable_fixture_id
        for case in blocked_impact_cases
        if case.executable_fixture_id not in case_review_ids
    ]
    cases_without_facts = [
        case.executable_fixture_id for case in case_reviews if case.blocker_fact_count == 0
    ]
    cases_without_dimensions = [
        case.executable_fixture_id for case in case_reviews if not case.critical_driver_dimensions
    ]
    cases_without_actions = [
        case.executable_fixture_id for case in case_reviews if not case.unblock_actions
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
        if getattr(fact_report, flag, False) is not False
        or getattr(driver_report, flag, False) is not False
        or getattr(impact_report, flag, False) is not False
    ]
    return [
        _check(
            "source_reports_ready",
            fact_report.status
            == "labor_employment_executable_budget_fact_bindings_ready_for_review"
            and driver_report.status
            == "labor_employment_executable_driver_bindings_ready_for_review"
            and impact_report.status
            == "labor_employment_executable_driver_impacts_ready_for_review",
            "Fact, driver-binding, and driver-impact reports are ready for blocked review.",
            evidence_refs=[
                fact_report.executable_budget_fact_binding_report_id,
                driver_report.executable_driver_binding_report_id,
                impact_report.executable_driver_impact_report_id,
            ],
        ),
        _check(
            "all_blocked_impact_cases_reviewed",
            not missing_case_reviews,
            "Every blocked source impact case has a blocked-case review entry.",
            evidence_refs=[case.executable_fixture_id for case in blocked_impact_cases],
            blocking_refs=missing_case_reviews,
        ),
        _check(
            "blocked_cases_have_blocker_facts",
            not cases_without_facts,
            "Every blocked case has at least one critical fact blocker.",
            evidence_refs=[case.executable_fixture_id for case in case_reviews],
            blocking_refs=cases_without_facts,
        ),
        _check(
            "blocked_cases_have_critical_driver_dimensions",
            not cases_without_dimensions,
            "Every blocked case identifies critical driver dimensions.",
            evidence_refs=[case.executable_fixture_id for case in case_reviews],
            blocking_refs=cases_without_dimensions,
        ),
        _check(
            "blocked_cases_have_unblock_actions",
            not cases_without_actions,
            "Every blocked case has deterministic human/correction follow-up actions.",
            evidence_refs=[case.executable_fixture_id for case in case_reviews],
            blocking_refs=cases_without_actions,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Blocked review did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[
                fact_report.executable_budget_fact_binding_report_id,
                driver_report.executable_driver_binding_report_id,
                impact_report.executable_driver_impact_report_id,
            ],
            blocking_refs=side_effects,
        ),
    ]


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
