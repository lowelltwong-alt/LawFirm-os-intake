from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    LaborEmploymentSyntheticFixtureFamilyCoverage,
    LaborEmploymentSyntheticFixtureFamilyPack,
    LaborEmploymentSyntheticFixtureFamilyPackCheck,
    LaborEmploymentSyntheticFixtureFamilyPackReport,
)
from .util import digest_text, load_json, now_iso, write_json


LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME = (
    "labor_employment_fixture_family_pack_report.json"
)
LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_NOTES_FILENAME = (
    "labor_employment_fixture_family_pack_report.md"
)

REQUIRED_NEXT_GATES = [
    "synthetic_fixture_generation_review",
    "reviewed_gold_before_calibration",
    "no_real_public_payload_or_identity_reconstruction",
    "range_or_block_until_human_fact_review",
    "no_lake_or_sqlite_write_from_fixture_pack",
]


def run_labor_employment_fixture_family_pack_audit(
    *,
    pack_path: str | Path,
    fact_needs_path: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentSyntheticFixtureFamilyPackReport, Path]:
    pack_ref = str(pack_path)
    pack = LaborEmploymentSyntheticFixtureFamilyPack.model_validate(load_json(pack_path))
    fact_needs = _load_fact_needs(Path(fact_needs_path))
    critical_fact_need_ids = sorted(
        fact_id for fact_id, level in fact_needs.items() if level == "critical"
    )
    report = build_labor_employment_fixture_family_pack_report(
        pack=pack,
        pack_ref=pack_ref,
        fact_needs=fact_needs,
        critical_fact_need_ids=critical_fact_need_ids,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_NOTES_FILENAME).write_text(
        render_labor_employment_fixture_family_pack_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def build_labor_employment_fixture_family_pack_report(
    *,
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
    pack_ref: str,
    fact_needs: dict[str, str],
    critical_fact_need_ids: list[str],
) -> LaborEmploymentSyntheticFixtureFamilyPackReport:
    family_coverage = _family_coverage(pack)
    missing_family_variant_count = sum(
        len(coverage.missing_variants) for coverage in family_coverage
    )
    covered_fact_needs = {
        fact_need_id for case in pack.cases for fact_need_id in case.fact_need_ids
    }
    missing_fact_need_ids = sorted(set(fact_needs) - covered_fact_needs)
    missing_critical_fact_need_ids = sorted(set(critical_fact_need_ids) - covered_fact_needs)
    covered_dimensions = {
        dimension for case in pack.cases for dimension in case.budget_driver_dimensions
    }
    missing_budget_driver_dimensions = sorted(
        set(pack.required_budget_driver_dimensions) - covered_dimensions
    )
    checks = _checks(
        pack=pack,
        pack_ref=pack_ref,
        family_coverage=family_coverage,
        missing_family_variant_count=missing_family_variant_count,
        missing_fact_need_ids=missing_fact_need_ids,
        missing_critical_fact_need_ids=missing_critical_fact_need_ids,
        missing_budget_driver_dimensions=missing_budget_driver_dimensions,
    )
    failed = [check for check in checks if check.status == "failed"]
    status = (
        "blocked_by_labor_employment_fixture_family_pack"
        if failed
        else "labor_employment_fixture_family_pack_ready_for_review"
    )
    return LaborEmploymentSyntheticFixtureFamilyPackReport(
        fixture_family_pack_report_id=_stable_id(
            "lefixturefamilypack",
            "|".join(
                [
                    pack.pack_id,
                    ",".join(sorted(case.case_id for case in pack.cases)),
                ]
            ),
        ),
        status=status,
        pack_id=pack.pack_id,
        pack_ref=pack_ref,
        case_count=len(pack.cases),
        required_family_count=len(pack.required_families),
        required_variant_count=len(pack.required_variants),
        complete_family_variant_count=sum(
            1 for coverage in family_coverage for _variant in coverage.covered_variants
        ),
        missing_family_variant_count=missing_family_variant_count,
        blocked_case_count=sum(
            1
            for case in pack.cases
            if case.expected_budget_readiness_state == "blocked_missing_critical_facts"
        ),
        range_only_case_count=sum(
            1
            for case in pack.cases
            if case.expected_budget_readiness_state == "range_only_pending_human_review"
        ),
        ready_case_count=sum(
            1
            for case in pack.cases
            if case.expected_budget_readiness_state == "candidate_ready_for_budget_review"
        ),
        missing_fact_need_ids=missing_fact_need_ids,
        missing_critical_fact_need_ids=missing_critical_fact_need_ids,
        missing_budget_driver_dimensions=missing_budget_driver_dimensions,
        family_coverage=family_coverage,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_labor_employment_fixture_family_pack_report(
    report: LaborEmploymentSyntheticFixtureFamilyPackReport,
) -> str:
    lines = [
        "# Labor/Employment Fixture Family Pack Report",
        "",
        f"**Report ID:** {report.fixture_family_pack_report_id}",
        f"**Status:** {report.status}",
        f"**Pack:** `{report.pack_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Required families: {report.required_family_count}",
        f"- Required variants: {report.required_variant_count}",
        f"- Complete family/variant cells: {report.complete_family_variant_count}",
        f"- Missing family/variant cells: {report.missing_family_variant_count}",
        f"- Blocked cases: {report.blocked_case_count}",
        f"- Range-only cases: {report.range_only_case_count}",
        f"- Ready cases: {report.ready_case_count}",
        "",
        "## Family Coverage",
        "",
    ]
    for coverage in report.family_coverage:
        lines.append(
            f"- {coverage.family}: cases={coverage.case_count}; "
            f"covered={', '.join(coverage.covered_variants)}; "
            f"missing={', '.join(coverage.missing_variants) if coverage.missing_variants else 'none'}"
        )
    lines.extend(["", "## Checks", ""])
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
            "This report is local synthetic QA evidence only. It does not create "
            "fixtures, approve calibration, mutate source files, write Lake/SQLite "
            "records, open matters, submit budgets, or authorize learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _load_fact_needs(path: Path) -> dict[str, str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"L&E fact-needs policy is not a mapping: {path}")
    fact_needs = payload.get("fact_needs")
    if not isinstance(fact_needs, list):
        raise ValueError(f"L&E fact-needs policy is missing fact_needs: {path}")
    result: dict[str, str] = {}
    for item in fact_needs:
        if not isinstance(item, dict):
            continue
        fact_id = item.get("fact_id")
        level = item.get("required_level")
        if isinstance(fact_id, str) and isinstance(level, str):
            result[fact_id] = level
    return result


def _family_coverage(
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
) -> list[LaborEmploymentSyntheticFixtureFamilyCoverage]:
    coverage: list[LaborEmploymentSyntheticFixtureFamilyCoverage] = []
    for family in pack.required_families:
        covered = sorted(
            {case.variant for case in pack.cases if case.family == family},
            key=pack.required_variants.index,
        )
        missing = [variant for variant in pack.required_variants if variant not in set(covered)]
        coverage.append(
            LaborEmploymentSyntheticFixtureFamilyCoverage(
                family=family,
                case_count=sum(1 for case in pack.cases if case.family == family),
                covered_variants=covered,
                missing_variants=missing,
            )
        )
    return coverage


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> LaborEmploymentSyntheticFixtureFamilyPackCheck:
    return LaborEmploymentSyntheticFixtureFamilyPackCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )


def _checks(
    *,
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
    pack_ref: str,
    family_coverage: list[LaborEmploymentSyntheticFixtureFamilyCoverage],
    missing_family_variant_count: int,
    missing_fact_need_ids: list[str],
    missing_critical_fact_need_ids: list[str],
    missing_budget_driver_dimensions: list[str],
) -> list[LaborEmploymentSyntheticFixtureFamilyPackCheck]:
    no_write_boundary = (
        pack.fixture_generation_authorized is False
        and pack.calibration_approved is False
        and pack.fixture_files_mutated is False
        and pack.lake_write_performed is False
        and pack.sqlite_write_performed is False
        and pack.external_writes_performed is False
        and pack.silent_learning_performed is False
        and all(
            case.calibration_approved is False
            and case.fixture_files_mutated is False
            and case.lake_write_performed is False
            and case.sqlite_write_performed is False
            and case.external_writes_performed is False
            and case.silent_learning_performed is False
            for case in pack.cases
        )
    )
    blocked_cases = [
        case
        for case in pack.cases
        if case.expected_budget_readiness_state == "blocked_missing_critical_facts"
    ]
    range_cases = [
        case
        for case in pack.cases
        if case.expected_budget_readiness_state == "range_only_pending_human_review"
    ]
    adversarial_cases = [case for case in pack.cases if case.variant == "adversarial"]
    return [
        _check(
            "family_variant_matrix_complete",
            missing_family_variant_count == 0,
            "Every required L&E family has clean, messy-thread, missing-attachment, and adversarial cases.",
            evidence_refs=[pack_ref],
            blocking_refs=[
                f"{coverage.family}:{variant}"
                for coverage in family_coverage
                for variant in coverage.missing_variants
            ],
        ),
        _check(
            "fact_need_policy_covered",
            not missing_fact_need_ids,
            "The pack covers every configured L&E budget fact need at least once.",
            evidence_refs=["config/labor-employment-budget-fact-needs.yaml", pack_ref],
            blocking_refs=missing_fact_need_ids,
        ),
        _check(
            "critical_fact_need_policy_covered",
            not missing_critical_fact_need_ids,
            "The pack covers every critical L&E budget fact need.",
            evidence_refs=["config/labor-employment-budget-fact-needs.yaml", pack_ref],
            blocking_refs=missing_critical_fact_need_ids,
        ),
        _check(
            "budget_driver_dimensions_covered",
            not missing_budget_driver_dimensions,
            "The pack covers required budget-driver dimensions for L&E budget QA.",
            evidence_refs=[pack_ref],
            blocking_refs=missing_budget_driver_dimensions,
        ),
        _check(
            "blocked_and_range_only_cases_present",
            bool(blocked_cases) and bool(range_cases),
            "The pack includes both critical-fact blockers and range-only pending-review cases.",
            evidence_refs=[case.case_id for case in [*blocked_cases, *range_cases]],
        ),
        _check(
            "adversarial_cases_stay_out_of_prompt_assembly",
            adversarial_cases
            and all(case.holdout_excluded_from_prompt_assembly for case in adversarial_cases),
            "Adversarial L&E cases are holdouts and stay excluded from model-visible prompt assembly.",
            evidence_refs=[case.case_id for case in adversarial_cases],
        ),
        _check(
            "no_write_and_no_calibration_boundary",
            no_write_boundary,
            "The fixture family pack authorizes no fixture generation, calibration, Lake/SQLite write, external write, or learning.",
            evidence_refs=[pack_ref],
        ),
    ]
