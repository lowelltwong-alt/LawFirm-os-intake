from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import (
    LaborEmploymentBudgetDriverDimension,
    LaborEmploymentExecutableDriverBindingCase,
    LaborEmploymentExecutableDriverBindingItem,
    LaborEmploymentExecutableDriverBindingReport,
    LaborEmploymentExecutableDriverImpactAction,
    LaborEmploymentExecutableDriverImpactCase,
    LaborEmploymentExecutableDriverImpactCheck,
    LaborEmploymentExecutableDriverImpactItem,
    LaborEmploymentExecutableDriverImpactReport,
    LaborEmploymentExecutableDriverPricingEffect,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME = (
    "labor_employment_executable_driver_impact_report.json"
)
LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_NOTES_FILENAME = (
    "labor_employment_executable_driver_impact_report.md"
)


@dataclass(frozen=True)
class DriverImpactPolicy:
    actions: tuple[LaborEmploymentExecutableDriverImpactAction, ...]
    pricing_effect: LaborEmploymentExecutableDriverPricingEffect
    range_widening_factor: float
    scenario_fork_required: bool
    rate_guideline_review_required: bool
    reason: str


DRIVER_IMPACT_POLICY: dict[LaborEmploymentBudgetDriverDimension, DriverImpactPolicy] = {
    "party_topology": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=1.6,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Party count, affiliate structure, and individual defendants drive pleadings, discovery, and deposition load.",
    ),
    "representation_posture": DriverImpactPolicy(
        actions=("require_rate_guideline_review", "hold_for_human_driver_review"),
        pricing_effect="hours_or_rate_review_required",
        range_widening_factor=1.0,
        scenario_fork_required=False,
        rate_guideline_review_required=True,
        reason="Client, payer, insured, and carrier posture governs rate/guideline review without becoming a conflict conclusion.",
    ),
    "claim_family": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=1.4,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Different L&E claim families need different phase and task assumptions.",
    ),
    "administrative_exhaustion": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=1.25,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Agency charge, right-to-sue, and exhaustion posture change motion and early-resolution paths.",
    ),
    "class_collective_scope": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=2.5,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Class, collective, PAGA, or group scope can dominate staffing, discovery, notice, and expert assumptions.",
    ),
    "forum_arbitration": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=1.3,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Forum, removal, and arbitration posture change procedure, motion practice, and hearing/trial path.",
    ),
    "employment_timeline": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=1.4,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Employment dates, protected activity dates, and termination dates shape limitations, damages, and witness work.",
    ),
    "damages_exposure": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=2.0,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Back pay, front pay, emotional distress, penalties, fees, and punitive exposure determine intensity and reserves.",
    ),
    "wage_hour_volume": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=2.2,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Employee count, pay periods, time records, and alleged violation volume drive discovery, experts, and settlement analysis.",
    ),
    "esi_discovery": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=1.8,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Custodians, systems, chat/email sources, and forensic needs drive collection, review, and vendor scope.",
    ),
    "deposition_plan": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=1.7,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Claimants, supervisors, HR witnesses, PMK topics, and third parties drive deposition hours and transcript costs.",
    ),
    "expert_vendor_needs": DriverImpactPolicy(
        actions=("widen_budget_range", "add_scenario_fork", "hold_for_human_driver_review"),
        pricing_effect="scenario_set_required",
        range_widening_factor=2.0,
        scenario_fork_required=True,
        rate_guideline_review_required=False,
        reason="Economic, statistical, forensic, e-discovery, and mediator/vendor needs require separate assumption paths.",
    ),
    "policy_contract_documents": DriverImpactPolicy(
        actions=("widen_budget_range", "hold_for_human_driver_review"),
        pricing_effect="range_width_required",
        range_widening_factor=1.25,
        scenario_fork_required=False,
        rate_guideline_review_required=False,
        reason="Handbooks, arbitration agreements, restrictive covenants, policies, and personnel files drive pleading and motion posture.",
    ),
    "carrier_guideline_rate_context": DriverImpactPolicy(
        actions=("require_rate_guideline_review", "hold_for_human_driver_review"),
        pricing_effect="hours_or_rate_review_required",
        range_widening_factor=1.0,
        scenario_fork_required=False,
        rate_guideline_review_required=True,
        reason="Carrier guidelines and approved rates must be reviewed before any compliant projection or submission path.",
    ),
}


REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "convert_reviewed_driver_impacts_to_budget_range_policy",
    "budget_generator_must_consume_reviewed_impacts_before_priced_labor_employment_output",
    "no_amount_budget_from_driver_impact_report",
    "no_lake_or_sqlite_write_from_driver_impact_report",
]


def run_labor_employment_executable_driver_impact_audit(
    *,
    executable_driver_binding_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentExecutableDriverImpactReport, Path]:
    binding_report = LaborEmploymentExecutableDriverBindingReport.model_validate(
        load_json(executable_driver_binding_report_path)
    )
    cases = [_case_from_driver_binding(case) for case in binding_report.cases]
    missing_policy_dimensions = _missing_policy_dimensions(binding_report)
    checks = _checks(
        binding_report=binding_report,
        cases=cases,
        missing_policy_dimensions=missing_policy_dimensions,
    )
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report_core = {
        "binding_report": binding_report.executable_driver_binding_report_id,
        "failed_cases": [case.executable_fixture_id for case in failed_cases],
        "failed_checks": [check.check_id for check in failed_checks],
        "missing_policy_dimensions": missing_policy_dimensions,
        "impact_counts": [
            {
                "case": case.executable_fixture_id,
                "items": case.impact_item_count,
                "blocks": case.block_amount_budget_impact_count,
                "review_only": case.critical_review_only_impact_count,
                "ranges": case.range_widening_impact_count,
                "scenarios": case.scenario_fork_impact_count,
            }
            for case in cases
        ],
    }
    report = LaborEmploymentExecutableDriverImpactReport(
        executable_driver_impact_report_id="leexecdriverimpact_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status=(
            "blocked_by_labor_employment_executable_driver_impacts"
            if failed_cases or failed_checks or missing_policy_dimensions
            else "labor_employment_executable_driver_impacts_ready_for_review"
        ),
        executable_driver_binding_report_ref=str(executable_driver_binding_report_path),
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        impact_item_count=sum(case.impact_item_count for case in cases),
        source_bound_impact_count=sum(case.source_bound_impact_count for case in cases),
        block_amount_budget_impact_count=sum(
            case.block_amount_budget_impact_count for case in cases
        ),
        critical_review_only_impact_count=sum(
            case.critical_review_only_impact_count for case in cases
        ),
        range_widening_impact_count=sum(case.range_widening_impact_count for case in cases),
        scenario_fork_impact_count=sum(case.scenario_fork_impact_count for case in cases),
        rate_guideline_review_impact_count=sum(
            case.rate_guideline_review_impact_count for case in cases
        ),
        human_review_impact_count=sum(case.human_review_impact_count for case in cases),
        max_range_widening_factor=max(
            [case.max_range_widening_factor for case in cases],
            default=1.0,
        ),
        impact_policy_dimensions=list(DRIVER_IMPACT_POLICY),
        missing_impact_policy_dimensions=missing_policy_dimensions,
        cases=cases,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_NOTES_FILENAME).write_text(
        render_labor_employment_executable_driver_impact_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_executable_driver_impact_report(
    report: LaborEmploymentExecutableDriverImpactReport,
) -> str:
    lines = [
        "# Labor/Employment Executable Driver Impact Report",
        "",
        f"**Report ID:** {report.executable_driver_impact_report_id}",
        f"**Status:** {report.status}",
        f"**Driver binding report:** `{report.executable_driver_binding_report_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Impact items: {report.impact_item_count}",
        f"- Source-bound impact candidates: {report.source_bound_impact_count}",
        f"- Amount-budget block impacts: {report.block_amount_budget_impact_count}",
        f"- Critical review-only impacts: {report.critical_review_only_impact_count}",
        f"- Range-widening impacts: {report.range_widening_impact_count}",
        f"- Scenario-fork impacts: {report.scenario_fork_impact_count}",
        f"- Rate/guideline review impacts: {report.rate_guideline_review_impact_count}",
        f"- Max range-widening factor: {report.max_range_widening_factor}",
        "- Missing impact policies: "
        + (
            ", ".join(f"`{dimension}`" for dimension in report.missing_impact_policy_dimensions)
            or "none"
        ),
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
                f"- Expected treatment: {case.expected_budget_treatment}",
                f"- Allowed budget output: {case.allowed_budget_output}",
                f"- Impact items: {case.impact_item_count}",
                f"- Block impacts: {case.block_amount_budget_impact_count}",
                f"- Critical review-only impacts: {case.critical_review_only_impact_count}",
                f"- Range impacts: {case.range_widening_impact_count}",
                f"- Scenario forks: {case.scenario_fork_impact_count}",
                f"- Rate/guideline reviews: {case.rate_guideline_review_impact_count}",
            ]
        )
        for item in case.impact_items:
            lines.append(
                f"- `{item.driver_dimension}`: {item.impact_state}; "
                f"actions={', '.join(item.impact_actions)}; "
                f"effect={item.pricing_effect}; "
                f"critical_review_only={item.critical_driver_review_only}; "
                f"range_factor={item.range_widening_factor}; "
                f"facts={', '.join(item.matched_fact_ids) or 'none'}"
            )
        if case.failed_expectation_ids:
            lines.append(
                "- Failed expectations: "
                + ", ".join(f"`{item}`" for item in case.failed_expectation_ids)
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
            "This report maps source-bound executable L&E driver candidates to "
            "deterministic budget-impact policy. It does not compute dollar amounts, "
            "submit budgets, write Lake/SQLite records, open matters, or authorize "
            "calibration. Impact policy remains candidate-only until reviewed.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_from_driver_binding(
    binding_case: LaborEmploymentExecutableDriverBindingCase,
) -> LaborEmploymentExecutableDriverImpactCase:
    items = [_impact_item(item) for item in binding_case.driver_bindings]
    failed_expectation_ids = _case_failures(binding_case, items)
    return LaborEmploymentExecutableDriverImpactCase(
        executable_fixture_id=binding_case.executable_fixture_id,
        linked_pack_case_ids=binding_case.linked_pack_case_ids,
        family=binding_case.family,
        variant=binding_case.variant,
        status="failed" if failed_expectation_ids else "passed",
        expected_budget_readiness_state=binding_case.expected_budget_readiness_state,
        expected_budget_treatment=binding_case.expected_budget_treatment,
        allowed_budget_output=_allowed_budget_output(binding_case.expected_budget_treatment),
        impact_item_count=len(items),
        source_bound_impact_count=sum(
            1 for item in items if item.impact_state == "source_bound_impact_candidate"
        ),
        block_amount_budget_impact_count=sum(
            1 for item in items if "block_amount_budget" in item.impact_actions
        ),
        critical_review_only_impact_count=sum(
            1 for item in items if item.critical_driver_review_only
        ),
        range_widening_impact_count=sum(
            1 for item in items if "widen_budget_range" in item.impact_actions
        ),
        scenario_fork_impact_count=sum(1 for item in items if item.scenario_fork_required),
        rate_guideline_review_impact_count=sum(
            1 for item in items if item.rate_guideline_review_required
        ),
        human_review_impact_count=sum(1 for item in items if item.human_review_required),
        max_range_widening_factor=max(
            [item.range_widening_factor for item in items],
            default=1.0,
        ),
        impact_items=items,
        failed_expectation_ids=failed_expectation_ids,
    )


def _impact_item(
    binding_item: LaborEmploymentExecutableDriverBindingItem,
) -> LaborEmploymentExecutableDriverImpactItem:
    policy = DRIVER_IMPACT_POLICY.get(binding_item.driver_dimension)
    source_bound = binding_item.binding_state == "source_bound_driver_candidate"
    critical_block = binding_item.critical_driver_block
    critical_review_only = binding_item.critical_driver_review_only
    if policy is None:
        actions: list[LaborEmploymentExecutableDriverImpactAction] = [
            "hold_for_human_driver_review"
        ]
        pricing_effect: LaborEmploymentExecutableDriverPricingEffect = "human_review_required"
        if critical_block:
            actions.insert(0, "block_amount_budget")
            pricing_effect = "amount_budget_blocked"
        return LaborEmploymentExecutableDriverImpactItem(
            driver_dimension=binding_item.driver_dimension,
            impact_state="blocked_missing_impact_policy",
            source_binding_state=binding_item.binding_state,
            source_bound=False,
            critical_driver_block=critical_block,
            critical_driver_review_only=critical_review_only,
            impact_actions=actions,
            pricing_effect=pricing_effect,
            range_widening_factor=1.0,
            scenario_fork_required=False,
            rate_guideline_review_required=False,
            matched_fact_ids=binding_item.matched_fact_ids,
            evidence_ref_count=binding_item.evidence_ref_count,
            exception_label_count=binding_item.exception_label_count,
            source_inventory_ref_count=binding_item.source_inventory_ref_count,
            policy_reason="No candidate impact policy is declared for this driver dimension.",
            notes=["Impact policy is missing; do not use this driver for budget math."],
        )
    if not source_bound:
        return LaborEmploymentExecutableDriverImpactItem(
            driver_dimension=binding_item.driver_dimension,
            impact_state="blocked_unbound_driver_candidate",
            source_binding_state=binding_item.binding_state,
            source_bound=False,
            critical_driver_block=critical_block,
            critical_driver_review_only=critical_review_only,
            impact_actions=["hold_for_human_driver_review"],
            pricing_effect="human_review_required",
            range_widening_factor=1.0,
            scenario_fork_required=False,
            rate_guideline_review_required=False,
            matched_fact_ids=binding_item.matched_fact_ids,
            evidence_ref_count=binding_item.evidence_ref_count,
            exception_label_count=binding_item.exception_label_count,
            source_inventory_ref_count=binding_item.source_inventory_ref_count,
            policy_reason=policy.reason,
            notes=["Driver binding is not source-bound; impact is blocked."],
        )
    return _source_bound_impact_item(
        binding_item,
        policy,
        critical_block=critical_block,
        critical_review_only=critical_review_only,
    )


def _source_bound_impact_item(
    binding_item: LaborEmploymentExecutableDriverBindingItem,
    policy: DriverImpactPolicy,
    *,
    critical_block: bool,
    critical_review_only: bool,
) -> LaborEmploymentExecutableDriverImpactItem:
    actions = list(policy.actions)
    pricing_effect = policy.pricing_effect
    if critical_block and "block_amount_budget" not in actions:
        actions.insert(0, "block_amount_budget")
        pricing_effect = "amount_budget_blocked"
    return LaborEmploymentExecutableDriverImpactItem(
        driver_dimension=binding_item.driver_dimension,
        impact_state="source_bound_impact_candidate",
        source_binding_state=binding_item.binding_state,
        source_bound=True,
        critical_driver_block=critical_block,
        critical_driver_review_only=critical_review_only,
        impact_actions=actions,
        pricing_effect=pricing_effect,
        range_widening_factor=policy.range_widening_factor,
        scenario_fork_required=policy.scenario_fork_required,
        rate_guideline_review_required=policy.rate_guideline_review_required,
        matched_fact_ids=binding_item.matched_fact_ids,
        evidence_ref_count=binding_item.evidence_ref_count,
        exception_label_count=binding_item.exception_label_count,
        source_inventory_ref_count=binding_item.source_inventory_ref_count,
        policy_reason=policy.reason,
        notes=[
            "Impact is candidate-only and traceable to source-bound executable driver binding.",
        ],
    )


def _case_failures(
    binding_case: LaborEmploymentExecutableDriverBindingCase,
    items: list[LaborEmploymentExecutableDriverImpactItem],
) -> list[str]:
    failures = []
    if binding_case.status != "passed":
        failures.append("driver_binding_case_not_passed")
    if any(item.impact_state != "source_bound_impact_candidate" for item in items):
        failures.append("driver_impact_not_source_bound")
    if (
        binding_case.expected_budget_treatment == "block_amount_budget"
        and binding_case.critical_driver_block_count == 0
    ):
        failures.append("blocked_budget_without_critical_driver")
    if binding_case.expected_budget_treatment == "block_amount_budget" and not any(
        "block_amount_budget" in item.impact_actions for item in items
    ):
        failures.append("blocked_budget_without_block_impact")
    if binding_case.expected_budget_treatment != "block_amount_budget" and not any(
        "widen_budget_range" in item.impact_actions
        or "add_scenario_fork" in item.impact_actions
        or "require_rate_guideline_review" in item.impact_actions
        for item in items
    ):
        failures.append("review_budget_without_driver_impact")
    return sorted(set(failures))


def _allowed_budget_output(
    expected_treatment: str,
) -> str:
    if expected_treatment == "block_amount_budget":
        return "blocked_amount_budget"
    if expected_treatment == "hours_only_or_broad_range":
        return "range_or_hours_only_pending_review"
    return "candidate_range_after_review_pending_human_review"


def _missing_policy_dimensions(
    binding_report: LaborEmploymentExecutableDriverBindingReport,
) -> list[LaborEmploymentBudgetDriverDimension]:
    bound_dimensions = {
        item.driver_dimension
        for case in binding_report.cases
        for item in case.driver_bindings
        if item.binding_state == "source_bound_driver_candidate"
    }
    return [
        dimension for dimension in sorted(bound_dimensions) if dimension not in DRIVER_IMPACT_POLICY
    ]


def _checks(
    *,
    binding_report: LaborEmploymentExecutableDriverBindingReport,
    cases: list[LaborEmploymentExecutableDriverImpactCase],
    missing_policy_dimensions: list[LaborEmploymentBudgetDriverDimension],
) -> list[LaborEmploymentExecutableDriverImpactCheck]:
    failed_cases = [case.executable_fixture_id for case in cases if case.status == "failed"]
    blocked_expected = [
        case.executable_fixture_id
        for case in cases
        if case.expected_budget_treatment == "block_amount_budget"
        and case.allowed_budget_output != "blocked_amount_budget"
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
        if getattr(binding_report, flag, False) is not False
    ]
    return [
        _check(
            "driver_binding_report_ready",
            binding_report.status == "labor_employment_executable_driver_bindings_ready_for_review",
            "Driver binding report is ready before impact policy can be trusted.",
            evidence_refs=[binding_report.executable_driver_binding_report_id],
            blocking_refs=[]
            if binding_report.status.endswith("ready_for_review")
            else [binding_report.status],
        ),
        _check(
            "every_source_bound_driver_has_impact_policy",
            not missing_policy_dimensions,
            "Every source-bound executable L&E driver dimension has a candidate impact policy.",
            evidence_refs=[binding_report.executable_driver_binding_report_id],
            blocking_refs=missing_policy_dimensions,
        ),
        _check(
            "critical_driver_blocks_preserve_amount_budget_block",
            not blocked_expected,
            "Cases with critical driver blockers keep amount-budget output blocked.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=blocked_expected,
        ),
        _check(
            "case_statuses_pass",
            not failed_cases,
            "Every executable driver impact case matched deterministic expectations.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=failed_cases,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Driver impact audit did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[binding_report.executable_driver_binding_report_id],
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
