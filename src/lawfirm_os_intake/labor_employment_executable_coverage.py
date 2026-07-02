from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentExecutableCoverageCase,
    LaborEmploymentExecutableCoverageCheck,
    LaborEmploymentExecutableCoverageFamily,
    LaborEmploymentExecutableCoverageReport,
    LaborEmploymentExecutableFixtureManifest,
    LaborEmploymentExecutableFixtureSpec,
    LaborEmploymentSyntheticFixtureCase,
    LaborEmploymentSyntheticFixtureFamilyPack,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME = (
    "labor_employment_executable_coverage_report.json"
)
LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_NOTES_FILENAME = (
    "labor_employment_executable_coverage_report.md"
)

REQUIRED_NEXT_GATES = [
    "expand_labor_employment_executable_fixture_families",
    "review_missing_executable_family_variant_cases",
    "no_fixture_generation_without_review",
    "no_amount_budget_from_coverage_report",
    "no_lake_or_sqlite_write_from_coverage_report",
]


def run_labor_employment_executable_coverage_audit(
    *,
    manifest_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    pack_path: str | Path | None = None,
) -> tuple[LaborEmploymentExecutableCoverageReport, Path]:
    root = Path(repo_root).resolve()
    manifest = LaborEmploymentExecutableFixtureManifest.model_validate(load_json(manifest_path))
    resolved_pack_path = (
        _resolve_repo_ref(root, pack_path)
        if pack_path
        else _resolve_repo_ref(root, manifest.pack_ref)
    )
    pack = LaborEmploymentSyntheticFixtureFamilyPack.model_validate(load_json(resolved_pack_path))
    pack_cases = {case.case_id: case for case in pack.cases}
    links_by_case = _links_by_pack_case(manifest)
    case_coverage = _case_coverage(pack.cases, links_by_case)
    family_coverage = _family_coverage(pack, case_coverage)
    checks = _checks(manifest=manifest, pack=pack, pack_cases=pack_cases)
    failed_checks = [check for check in checks if check.status == "failed"]
    missing_cases = [case for case in case_coverage if case.coverage_state == "missing_executable"]
    covered_cases = [case for case in case_coverage if case.coverage_state == "covered_executable"]
    coverage_state = (
        "partial_executable_coverage" if missing_cases else "complete_executable_coverage"
    )
    report_core = {
        "pack_id": pack.pack_id,
        "manifest_id": manifest.manifest_id,
        "covered": [case.pack_case_id for case in covered_cases],
        "missing": [case.pack_case_id for case in missing_cases],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentExecutableCoverageReport(
        executable_coverage_report_id="leexeccoverage_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status=(
            "blocked_labor_employment_executable_coverage"
            if failed_checks
            else "labor_employment_executable_coverage_ready_for_review"
        ),
        coverage_state=coverage_state,
        pack_id=pack.pack_id,
        pack_ref=str(resolved_pack_path),
        executable_manifest_id=manifest.manifest_id,
        executable_manifest_ref=str(manifest_path),
        pack_case_count=len(pack.cases),
        executable_fixture_count=len(manifest.fixtures),
        executable_pack_case_link_count=sum(
            len(fixture.linked_pack_case_ids) for fixture in manifest.fixtures
        ),
        covered_pack_case_count=len(covered_cases),
        missing_executable_pack_case_count=len(missing_cases),
        covered_family_count=sum(1 for family in family_coverage if family.covered_case_count),
        missing_family_count=sum(1 for family in family_coverage if not family.covered_case_count),
        covered_family_variant_count=len(covered_cases),
        missing_family_variant_count=len(missing_cases),
        covered_pack_case_ids=[case.pack_case_id for case in covered_cases],
        missing_executable_pack_case_ids=[case.pack_case_id for case in missing_cases],
        missing_family_variant_refs=[f"{case.family}:{case.variant}" for case in missing_cases],
        family_coverage=family_coverage,
        case_coverage=case_coverage,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_NOTES_FILENAME).write_text(
        render_labor_employment_executable_coverage_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_executable_coverage_report(
    report: LaborEmploymentExecutableCoverageReport,
) -> str:
    lines = [
        "# Labor/Employment Executable Coverage Report",
        "",
        f"**Report ID:** {report.executable_coverage_report_id}",
        f"**Status:** {report.status}",
        f"**Coverage state:** {report.coverage_state}",
        f"**Pack:** `{report.pack_ref}`",
        f"**Executable manifest:** `{report.executable_manifest_ref}`",
        "",
        "## Summary",
        "",
        f"- Pack cases: {report.pack_case_count}",
        f"- Executable fixtures: {report.executable_fixture_count}",
        f"- Executable pack-case links: {report.executable_pack_case_link_count}",
        f"- Covered pack cases: {report.covered_pack_case_count}",
        f"- Missing executable pack cases: {report.missing_executable_pack_case_count}",
        f"- Covered family/variant pairs: {report.covered_family_variant_count}",
        f"- Missing family/variant pairs: {report.missing_family_variant_count}",
        "",
        "## Family Coverage",
        "",
    ]
    for family in report.family_coverage:
        lines.append(
            f"- `{family.family}`: {family.covered_case_count}/{family.pack_case_count} "
            f"covered; missing={', '.join(family.missing_variants) or 'none'}"
        )
    lines.extend(["", "## Missing Executable Cases", ""])
    lines.extend(f"- `{case_id}`" for case_id in report.missing_executable_pack_case_ids)
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
            "This report is a synthetic QA coverage surface. It does not generate "
            "fixtures, approve calibration, produce budget amounts, submit budgets, "
            "write Lake/SQLite records, open matters, or learn from review outcomes.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_coverage(
    pack_cases: list[LaborEmploymentSyntheticFixtureCase],
    links_by_case: dict[str, list[str]],
) -> list[LaborEmploymentExecutableCoverageCase]:
    cases: list[LaborEmploymentExecutableCoverageCase] = []
    for pack_case in pack_cases:
        fixture_ids = sorted(links_by_case.get(pack_case.case_id, []))
        cases.append(
            LaborEmploymentExecutableCoverageCase(
                pack_case_id=pack_case.case_id,
                family=pack_case.family,
                variant=pack_case.variant,
                coverage_state=("covered_executable" if fixture_ids else "missing_executable"),
                executable_fixture_ids=fixture_ids,
                expected_budget_readiness_state=pack_case.expected_budget_readiness_state,
                expected_budget_treatment=pack_case.expected_budget_treatment,
                missing_critical_fact_ids=pack_case.missing_critical_fact_ids,
                missing_important_fact_ids=pack_case.missing_important_fact_ids,
            )
        )
    return cases


def _family_coverage(
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
    case_coverage: list[LaborEmploymentExecutableCoverageCase],
) -> list[LaborEmploymentExecutableCoverageFamily]:
    coverage: list[LaborEmploymentExecutableCoverageFamily] = []
    for family in pack.required_families:
        cases = [case for case in case_coverage if case.family == family]
        covered = [case for case in cases if case.coverage_state == "covered_executable"]
        missing = [case for case in cases if case.coverage_state == "missing_executable"]
        coverage.append(
            LaborEmploymentExecutableCoverageFamily(
                family=family,
                pack_case_count=len(cases),
                covered_case_count=len(covered),
                missing_case_count=len(missing),
                covered_variants=[case.variant for case in covered],
                missing_variants=[case.variant for case in missing],
                executable_fixture_ids=sorted(
                    {fixture_id for case in covered for fixture_id in case.executable_fixture_ids}
                ),
            )
        )
    return coverage


def _links_by_pack_case(
    manifest: LaborEmploymentExecutableFixtureManifest,
) -> dict[str, list[str]]:
    links: dict[str, list[str]] = {}
    for fixture in manifest.fixtures:
        for case_id in fixture.linked_pack_case_ids:
            links.setdefault(case_id, []).append(fixture.executable_fixture_id)
    return links


def _checks(
    *,
    manifest: LaborEmploymentExecutableFixtureManifest,
    pack: LaborEmploymentSyntheticFixtureFamilyPack,
    pack_cases: dict[str, LaborEmploymentSyntheticFixtureCase],
) -> list[LaborEmploymentExecutableCoverageCheck]:
    missing_links = sorted(
        {
            case_id
            for fixture in manifest.fixtures
            for case_id in fixture.linked_pack_case_ids
            if case_id not in pack_cases
        }
    )
    mismatches = sorted(
        {
            fixture.executable_fixture_id
            for fixture in manifest.fixtures
            for case_id in fixture.linked_pack_case_ids
            if case_id in pack_cases and _fixture_has_no_family_variant_anchor(fixture, pack_cases)
        }
    )
    side_effects = [
        flag
        for flag in [
            "fixture_generation_authorized",
            "calibration_approved",
            "lake_write_performed",
            "sqlite_write_performed",
            "external_writes_performed",
            "silent_learning_performed",
        ]
        if getattr(manifest, flag) is not False or getattr(pack, flag) is not False
    ]
    return [
        _check(
            "coverage_inputs_are_synthetic_candidate_only",
            manifest.synthetic_only
            and pack.synthetic_only
            and manifest.candidate_only
            and pack.candidate_only,
            "Executable manifest and fixture family pack remain synthetic/candidate-only.",
            evidence_refs=[manifest.manifest_id, pack.pack_id],
        ),
        _check(
            "executable_pack_links_exist",
            not missing_links,
            "Every executable fixture pack-case link exists in the fixture family pack.",
            evidence_refs=[manifest.manifest_id],
            blocking_refs=missing_links,
        ),
        _check(
            "executable_pack_links_match_family_variant",
            not mismatches,
            "Every executable fixture link matches the linked pack case family and variant.",
            evidence_refs=[manifest.manifest_id],
            blocking_refs=mismatches,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Coverage audit did not authorize generation, calibration, Lake/SQLite writes, external writes, or silent learning.",
            evidence_refs=[manifest.manifest_id, pack.pack_id],
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
) -> LaborEmploymentExecutableCoverageCheck:
    return LaborEmploymentExecutableCoverageCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )


def _resolve_repo_ref(root: Path, ref: str | Path) -> Path:
    path = Path(ref)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"repository reference escapes repo root: {ref}")
    return resolved


def _fixture_has_no_family_variant_anchor(
    fixture: LaborEmploymentExecutableFixtureSpec,
    pack_cases: dict[str, LaborEmploymentSyntheticFixtureCase],
) -> bool:
    linked_cases = [
        pack_cases[case_id] for case_id in fixture.linked_pack_case_ids if case_id in pack_cases
    ]
    return bool(linked_cases) and not any(
        case.family == fixture.family and case.variant == fixture.variant for case in linked_cases
    )
