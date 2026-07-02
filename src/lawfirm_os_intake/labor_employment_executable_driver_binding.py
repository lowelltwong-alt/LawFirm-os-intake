from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBudgetDriverDimension,
    LaborEmploymentExecutableBudgetFactBindingCase,
    LaborEmploymentExecutableBudgetFactBindingReport,
    LaborEmploymentExecutableDriverBindingCase,
    LaborEmploymentExecutableDriverBindingCheck,
    LaborEmploymentExecutableDriverBindingItem,
    LaborEmploymentExecutableDriverBindingReport,
    LaborEmploymentExecutableFixtureAuditCase,
    LaborEmploymentExecutableFixtureAuditReport,
    LaborEmploymentSyntheticFixtureFamilyPack,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME = (
    "labor_employment_executable_driver_binding_report.json"
)
LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_NOTES_FILENAME = (
    "labor_employment_executable_driver_binding_report.md"
)

REQUIRED_DRIVER_DIMENSIONS: list[LaborEmploymentBudgetDriverDimension] = [
    "party_topology",
    "representation_posture",
    "administrative_exhaustion",
    "class_collective_scope",
    "forum_arbitration",
    "employment_timeline",
    "wage_hour_volume",
    "esi_discovery",
    "deposition_plan",
    "expert_vendor_needs",
    "policy_contract_documents",
    "carrier_guideline_rate_context",
]

DRIVER_FACT_IDS: dict[LaborEmploymentBudgetDriverDimension, set[str]] = {
    "party_topology": {
        "employee_claimant_identity",
        "employer_or_defendant_identity",
        "prospective_client_payer_carrier_posture",
        "individual_supervisor_or_manager_defendants",
        "joint_employer_or_affiliate_structure",
        "class_collective_or_group_scope",
    },
    "representation_posture": {"prospective_client_payer_carrier_posture"},
    "claim_family": {"claims_and_causes_of_action"},
    "administrative_exhaustion": {"administrative_exhaustion_and_agency_record"},
    "class_collective_scope": {"class_collective_or_group_scope"},
    "forum_arbitration": {"forum_removed_and_arbitration_posture"},
    "employment_timeline": {
        "relevant_employment_timeline",
        "administrative_exhaustion_and_agency_record",
    },
    "damages_exposure": {
        "damages_categories_and_exposure",
        "wage_hour_pay_period_and_employee_volume",
    },
    "wage_hour_volume": {"wage_hour_pay_period_and_employee_volume"},
    "esi_discovery": {
        "esi_custodians_and_sources",
        "policy_handbook_contract_documents",
    },
    "deposition_plan": {
        "anticipated_depositions",
        "individual_supervisor_or_manager_defendants",
        "joint_employer_or_affiliate_structure",
    },
    "expert_vendor_needs": {
        "expert_and_vendor_needs",
        "wage_hour_pay_period_and_employee_volume",
    },
    "policy_contract_documents": {"policy_handbook_contract_documents"},
    "carrier_guideline_rate_context": {
        "carrier_guideline_and_rate_source",
        "prospective_client_payer_carrier_posture",
    },
}

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_driver_review",
    "expand_driver_bindings_for_claim_family_and_damages",
    "budget_driver_values_remain_candidate_only",
    "no_amount_budget_from_driver_binding_report",
    "no_lake_or_sqlite_write_from_driver_binding_report",
]


def run_labor_employment_executable_driver_binding_audit(
    *,
    executable_fixture_report_path: str | Path,
    executable_fact_binding_report_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    pack_path: str | Path | None = None,
) -> tuple[LaborEmploymentExecutableDriverBindingReport, Path]:
    root = Path(repo_root).resolve()
    fixture_report = LaborEmploymentExecutableFixtureAuditReport.model_validate(
        load_json(executable_fixture_report_path)
    )
    fact_report = LaborEmploymentExecutableBudgetFactBindingReport.model_validate(
        load_json(executable_fact_binding_report_path)
    )
    resolved_pack_path = _resolve_repo_ref(
        root,
        pack_path or _pack_ref_from_fixture_report(fixture_report),
    )
    pack = LaborEmploymentSyntheticFixtureFamilyPack.model_validate(load_json(resolved_pack_path))
    fixture_cases = {case.executable_fixture_id: case for case in fixture_report.cases}
    pack_cases = {case.case_id: case for case in pack.cases}

    cases = [
        _case_from_fact_binding(
            binding_case=binding_case,
            fixture_case=fixture_cases.get(binding_case.executable_fixture_id),
            pack_cases=pack_cases,
        )
        for binding_case in fact_report.cases
    ]
    covered_dimensions = _covered_dimensions(cases)
    missing_dimensions = [
        dimension for dimension in REQUIRED_DRIVER_DIMENSIONS if dimension not in covered_dimensions
    ]
    checks = _checks(
        fixture_report=fixture_report,
        fact_report=fact_report,
        pack=pack,
        cases=cases,
        missing_dimensions=missing_dimensions,
    )
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report_core = {
        "fixture_report": fixture_report.executable_fixture_audit_report_id,
        "fact_report": fact_report.executable_budget_fact_binding_report_id,
        "covered_dimensions": covered_dimensions,
        "missing_dimensions": missing_dimensions,
        "failed_cases": [case.executable_fixture_id for case in failed_cases],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentExecutableDriverBindingReport(
        executable_driver_binding_report_id="leexecdriverbinding_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status=(
            "blocked_by_labor_employment_executable_driver_bindings"
            if failed_cases or failed_checks or missing_dimensions
            else "labor_employment_executable_driver_bindings_ready_for_review"
        ),
        executable_fixture_report_ref=str(executable_fixture_report_path),
        executable_fact_binding_report_ref=str(executable_fact_binding_report_path),
        pack_ref=str(resolved_pack_path),
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        driver_binding_count=sum(case.driver_binding_count for case in cases),
        source_bound_driver_count=sum(case.source_bound_driver_count for case in cases),
        unbound_driver_count=sum(case.unbound_driver_count for case in cases),
        critical_driver_block_count=sum(case.critical_driver_block_count for case in cases),
        required_driver_dimensions=REQUIRED_DRIVER_DIMENSIONS,
        covered_driver_dimensions=covered_dimensions,
        missing_driver_dimensions=missing_dimensions,
        cases=cases,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_NOTES_FILENAME).write_text(
        render_labor_employment_executable_driver_binding_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_executable_driver_binding_report(
    report: LaborEmploymentExecutableDriverBindingReport,
) -> str:
    lines = [
        "# Labor/Employment Executable Driver Binding Report",
        "",
        f"**Report ID:** {report.executable_driver_binding_report_id}",
        f"**Status:** {report.status}",
        f"**Executable fixture report:** `{report.executable_fixture_report_ref}`",
        f"**Executable fact binding report:** `{report.executable_fact_binding_report_ref}`",
        f"**Pack:** `{report.pack_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Driver bindings: {report.driver_binding_count}",
        f"- Source-bound drivers: {report.source_bound_driver_count}",
        f"- Unbound drivers: {report.unbound_driver_count}",
        f"- Critical driver blocks: {report.critical_driver_block_count}",
        "- Covered focus dimensions: "
        + ", ".join(f"`{dimension}`" for dimension in report.covered_driver_dimensions),
        "- Missing focus dimensions: "
        + (", ".join(f"`{dimension}`" for dimension in report.missing_driver_dimensions) or "none"),
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
                f"- Expected readiness: {case.expected_budget_readiness_state}",
                f"- Expected treatment: {case.expected_budget_treatment}",
                f"- Driver bindings: {case.driver_binding_count}",
                f"- Source-bound drivers: {case.source_bound_driver_count}",
                f"- Critical driver blocks: {case.critical_driver_block_count}",
            ]
        )
        for binding in case.driver_bindings:
            lines.append(
                f"- `{binding.driver_dimension}`: {binding.binding_state}; "
                f"facts={', '.join(binding.matched_fact_ids) or 'none'}; "
                f"evidence_refs={binding.evidence_ref_count}; "
                f"exception_labels={binding.exception_label_count}"
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
            "This report binds executable synthetic L&E fact-gap evidence to "
            "budget-driver focus dimensions. It does not resolve driver values, "
            "produce budget amounts, write Lake/SQLite records, submit budgets, "
            "open matters, or authorize calibration.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_from_fact_binding(
    *,
    binding_case: LaborEmploymentExecutableBudgetFactBindingCase,
    fixture_case: LaborEmploymentExecutableFixtureAuditCase | None,
    pack_cases: dict[str, object],
) -> LaborEmploymentExecutableDriverBindingCase:
    failed_expectation_ids: list[str] = []
    if fixture_case is None:
        failed_expectation_ids.append("executable_fixture_case_missing")
        linked_pack_case_ids: list[str] = []
        family = "wage_hour_flsa_state"
        variant = "clean"
    else:
        linked_pack_case_ids = fixture_case.linked_pack_case_ids
        family = fixture_case.family
        variant = fixture_case.variant
        missing_links = [case_id for case_id in linked_pack_case_ids if case_id not in pack_cases]
        if missing_links:
            failed_expectation_ids.append("linked_pack_case_missing")
    driver_bindings = _driver_bindings_from_facts(binding_case)
    unbound = [item for item in driver_bindings if item.binding_state == "unbound_driver_candidate"]
    status = "failed" if failed_expectation_ids or unbound else "passed"
    return LaborEmploymentExecutableDriverBindingCase(
        executable_fixture_id=binding_case.executable_fixture_id,
        linked_pack_case_ids=linked_pack_case_ids,
        family=family,  # type: ignore[arg-type]
        variant=variant,  # type: ignore[arg-type]
        status=status,
        expected_budget_readiness_state=binding_case.expected_budget_readiness_state,
        expected_budget_treatment=binding_case.expected_budget_treatment,
        driver_binding_count=len(driver_bindings),
        source_bound_driver_count=sum(
            1 for item in driver_bindings if item.binding_state == "source_bound_driver_candidate"
        ),
        unbound_driver_count=len(unbound),
        critical_driver_block_count=sum(
            1 for item in driver_bindings if _driver_has_critical_block(item, binding_case)
        ),
        budget_driver_dimensions=[item.driver_dimension for item in driver_bindings],
        driver_bindings=driver_bindings,
        failed_expectation_ids=sorted(set(failed_expectation_ids)),
    )


def _driver_bindings_from_facts(
    binding_case: LaborEmploymentExecutableBudgetFactBindingCase,
) -> list[LaborEmploymentExecutableDriverBindingItem]:
    items: list[LaborEmploymentExecutableDriverBindingItem] = []
    for dimension, fact_ids in DRIVER_FACT_IDS.items():
        matching = [
            binding
            for binding in binding_case.fact_bindings
            if binding.fact_id in fact_ids and binding.binding_state != "unbound_gap_candidate"
        ]
        if not matching:
            continue
        matched_fact_ids = sorted({binding.fact_id for binding in matching})
        items.append(
            LaborEmploymentExecutableDriverBindingItem(
                driver_dimension=dimension,
                binding_state="source_bound_driver_candidate",
                fact_ids=sorted(fact_ids.intersection(matched_fact_ids)),
                evidence_ref_count=sum(len(binding.evidence_refs) for binding in matching),
                exception_label_count=sum(
                    len(binding.matched_exception_labels) for binding in matching
                ),
                source_inventory_ref_count=sum(
                    len(binding.source_inventory_refs) for binding in matching
                ),
                critical_driver_block=any(binding.blocks_precise_budget for binding in matching),
                matched_fact_ids=matched_fact_ids,
                missing_fact_ids=[],
                notes=[
                    "Driver dimension is candidate-only and sourced through executable fact bindings."
                ],
            )
        )
    return items


def _driver_has_critical_block(
    item: LaborEmploymentExecutableDriverBindingItem,
    binding_case: LaborEmploymentExecutableBudgetFactBindingCase,
) -> bool:
    critical_fact_ids = {
        binding.fact_id for binding in binding_case.fact_bindings if binding.blocks_precise_budget
    }
    return bool(critical_fact_ids.intersection(item.matched_fact_ids))


def _covered_dimensions(
    cases: list[LaborEmploymentExecutableDriverBindingCase],
) -> list[LaborEmploymentBudgetDriverDimension]:
    covered = {item.driver_dimension for case in cases for item in case.driver_bindings}
    return [dimension for dimension in REQUIRED_DRIVER_DIMENSIONS if dimension in covered]


def _checks(
    *,
    fixture_report: LaborEmploymentExecutableFixtureAuditReport,
    fact_report: LaborEmploymentExecutableBudgetFactBindingReport,
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
    cases: list[LaborEmploymentExecutableDriverBindingCase],
    missing_dimensions: list[LaborEmploymentBudgetDriverDimension],
) -> list[LaborEmploymentExecutableDriverBindingCheck]:
    failed_cases = [case.executable_fixture_id for case in cases if case.status == "failed"]
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
        if getattr(fixture_report, flag, False) is not False
        or getattr(fact_report, flag, False) is not False
        or getattr(pack, flag, False) is not False
    ]
    return [
        _check(
            "source_reports_ready",
            fixture_report.status == "labor_employment_executable_fixtures_ready_for_review"
            and fact_report.status
            == "labor_employment_executable_budget_fact_bindings_ready_for_review",
            "Executable fixture and fact-binding reports are ready before driver binding.",
            evidence_refs=[
                fixture_report.executable_fixture_audit_report_id,
                fact_report.executable_budget_fact_binding_report_id,
            ],
        ),
        _check(
            "required_driver_focus_dimensions_covered",
            not missing_dimensions,
            "Required L&E budget-driver focus dimensions are covered by executable fact bindings.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=missing_dimensions,
        ),
        _check(
            "case_statuses_pass",
            not failed_cases,
            "Every executable driver binding case is source-bound and matched.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=failed_cases,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Driver binding audit did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[
                fixture_report.executable_fixture_audit_report_id,
                fact_report.executable_budget_fact_binding_report_id,
                pack.pack_id,
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
) -> LaborEmploymentExecutableDriverBindingCheck:
    return LaborEmploymentExecutableDriverBindingCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )


def _pack_ref_from_fixture_report(report: LaborEmploymentExecutableFixtureAuditReport) -> str:
    return report.pack_ref


def _resolve_repo_ref(root: Path, ref: str | Path) -> Path:
    path = Path(ref)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"repository reference escapes repo root: {ref}")
    return resolved
