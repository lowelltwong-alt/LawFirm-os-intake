from __future__ import annotations

from pathlib import Path

from .labor_employment_budget_facts import (
    LABOR_EMPLOYMENT_BUDGET_FACT_NOTES_FILENAME,
    LABOR_EMPLOYMENT_BUDGET_FACT_REPORT_FILENAME,
    build_labor_employment_budget_fact_audit_report,
    render_labor_employment_budget_fact_audit_report,
)
from .models import (
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentBudgetFactGoldCaseResult,
    LaborEmploymentBudgetFactGoldCaseSpec,
    LaborEmploymentBudgetFactGoldCheck,
    LaborEmploymentBudgetFactGoldReport,
    LaborEmploymentBudgetFactGoldSpec,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME = "labor_employment_budget_fact_gold_report.json"
LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_NOTES_FILENAME = "labor_employment_budget_fact_gold_report.md"


def run_labor_employment_budget_fact_gold_validation(
    *,
    gold_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    policy_path: str | Path | None = None,
) -> tuple[LaborEmploymentBudgetFactGoldReport, Path]:
    root = Path(repo_root)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    gold = LaborEmploymentBudgetFactGoldSpec.model_validate(load_json(gold_path))
    policy_ref = str(policy_path or gold.policy_ref)

    cases: list[LaborEmploymentBudgetFactGoldCaseResult] = []
    checks: list[LaborEmploymentBudgetFactGoldCheck] = [
        _check(
            "gold_is_reviewed_synthetic_candidate",
            gold.reviewed
            and gold.data_scope == "synthetic"
            and gold.candidate_only
            and gold.non_authoritative,
            "Gold spec is reviewed, synthetic-only, candidate-only, and non-authoritative.",
        ),
        _check(
            "gold_has_no_side_effect_authority",
            _no_gold_side_effects(gold),
            "Gold spec does not authorize budgets, submissions, Lake/SQLite writes, training, or silent learning.",
        ),
    ]
    for case_spec in gold.cases:
        case_result, case_checks = _evaluate_case(
            case_spec=case_spec,
            root=root,
            run_dir=run_dir,
            policy_ref=policy_ref,
        )
        cases.append(case_result)
        checks.extend(case_checks)

    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report_core = {
        "gold_id": gold.gold_id,
        "gold_ref": str(gold_path),
        "policy_ref": policy_ref,
        "cases": [
            {
                "case_id": case.case_id,
                "status": case.status,
                "failures": case.failed_expectation_ids,
            }
            for case in cases
        ],
        "checks": [
            {
                "check_id": check.check_id,
                "status": check.status,
                "case_id": check.case_id,
            }
            for check in checks
        ],
    }
    report = LaborEmploymentBudgetFactGoldReport(
        labor_employment_budget_fact_gold_report_id="lebudgetfactgold_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status="failed" if failed_cases or failed_checks else "passed",
        gold_id=gold.gold_id,
        gold_ref=str(gold_path),
        reviewed_gold=gold.reviewed,
        data_scope=gold.data_scope,
        policy_ref=policy_ref,
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        check_count=len(checks),
        failed_check_count=len(failed_checks),
        cases=cases,
        checks=checks,
        required_next_gates=gold.required_next_gates,
        generated_at=now_iso(),
    )
    write_json(
        run_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME, report.model_dump(mode="json")
    )
    (run_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_NOTES_FILENAME).write_text(
        render_labor_employment_budget_fact_gold_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_budget_fact_gold_report(
    report: LaborEmploymentBudgetFactGoldReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Fact Gold Report",
        "",
        f"**Report ID:** {report.labor_employment_budget_fact_gold_report_id}",
        f"**Status:** {report.status}",
        f"**Gold:** `{report.gold_ref}`",
        f"**Policy:** `{report.policy_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Checks: {report.check_count}",
        f"- Failed checks: {report.failed_check_count}",
        "",
        "## Cases",
        "",
    ]
    for case in report.cases:
        lines.extend(
            [
                f"### {case.case_id}",
                "",
                f"- Status: {case.status}",
                f"- Manifest: `{case.manifest_ref}`",
                f"- Audit report: `{case.report_ref or 'missing'}`",
                f"- Audit status: {case.audit_report_status or 'missing'}",
                f"- Audit readiness: {case.audit_budget_readiness_state or 'missing'}",
            ]
        )
        if case.failed_expectation_ids:
            lines.append(
                "- Failed expectations: "
                + ", ".join(f"`{failure}`" for failure in case.failed_expectation_ids)
            )
        lines.append("")
    lines.extend(["## Checks", ""])
    for check in report.checks:
        case_prefix = f"{check.case_id}: " if check.case_id else ""
        lines.append(f"- {case_prefix}{check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This reviewed synthetic-gold report validates deterministic L&E budget "
            "fact audit behavior only. It does not resolve facts, authorize budget "
            "amounts, write Lake/SQLite records, train models, or promote canonical "
            "roles or taxonomies.",
            "",
        ]
    )
    return "\n".join(lines)


def _evaluate_case(
    *,
    case_spec: LaborEmploymentBudgetFactGoldCaseSpec,
    root: Path,
    run_dir: Path,
    policy_ref: str,
) -> tuple[LaborEmploymentBudgetFactGoldCaseResult, list[LaborEmploymentBudgetFactGoldCheck]]:
    case_dir = run_dir / "cases" / case_spec.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    checks: list[LaborEmploymentBudgetFactGoldCheck] = []
    failed: list[str] = []
    report: LaborEmploymentBudgetFactAuditReport | None = None
    report_ref: str | None = None
    try:
        report = build_labor_employment_budget_fact_audit_report(
            repo_root=root,
            manifest_path=case_spec.manifest_ref,
            policy_path=policy_ref,
        )
        report_ref = str(case_dir / LABOR_EMPLOYMENT_BUDGET_FACT_REPORT_FILENAME)
        write_json(report_ref, report.model_dump(mode="json"))
        (case_dir / LABOR_EMPLOYMENT_BUDGET_FACT_NOTES_FILENAME).write_text(
            render_labor_employment_budget_fact_audit_report(report),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 - fail closed into the gold report.
        failed.append("audit_report_build_failed")
        checks.append(
            _check(
                "audit_report_builds",
                False,
                "Budget fact audit report must build for gold case.",
                case_id=case_spec.case_id,
                details={"error": str(exc)},
            )
        )

    if report is not None:
        checks.extend(_report_checks(case_spec, report))
        failed.extend(
            check.check_id
            for check in checks
            if check.case_id == case_spec.case_id and check.status == "failed"
        )

    case_result = LaborEmploymentBudgetFactGoldCaseResult(
        case_id=case_spec.case_id,
        label=case_spec.label,
        manifest_ref=case_spec.manifest_ref,
        manifest_id=report.manifest_id if report else None,
        status="failed" if failed else "passed",
        audit_report_status=report.status if report else None,
        audit_budget_readiness_state=report.budget_readiness_state if report else None,
        failed_expectation_ids=sorted(set(failed)),
        report_ref=report_ref,
    )
    return case_result, checks


def _report_checks(
    case_spec: LaborEmploymentBudgetFactGoldCaseSpec,
    report: LaborEmploymentBudgetFactAuditReport,
) -> list[LaborEmploymentBudgetFactGoldCheck]:
    critical_gap_ids = [gap.fact_id for gap in report.gaps if gap.severity == "critical"]
    warning_gap_ids = [gap.fact_id for gap in report.gaps if gap.severity == "warning"]
    by_fact = {finding.fact_id: finding for finding in report.findings}
    checks = [
        _case_check(
            case_spec,
            "manifest_id_matches_gold",
            report.manifest_id == case_spec.expected_manifest_id,
            "Manifest ID matches reviewed gold.",
            {"actual": report.manifest_id, "expected": case_spec.expected_manifest_id},
        ),
        _case_check(
            case_spec,
            "status_matches_gold",
            report.status == case_spec.expected_status,
            "Audit report status matches reviewed gold.",
            {"actual": report.status, "expected": case_spec.expected_status},
        ),
        _case_check(
            case_spec,
            "budget_readiness_matches_gold",
            report.budget_readiness_state == case_spec.expected_budget_readiness_state,
            "Budget readiness state matches reviewed gold.",
            {
                "actual": report.budget_readiness_state,
                "expected": case_spec.expected_budget_readiness_state,
            },
        ),
        _case_check(
            case_spec,
            "counts_match_gold",
            (
                report.finding_count == case_spec.expected_finding_count
                and report.source_bound_finding_count
                == case_spec.expected_source_bound_finding_count
                and report.needs_review_finding_count
                == case_spec.expected_needs_review_finding_count
                and report.unknown_finding_count == case_spec.expected_unknown_finding_count
                and report.gap_count == case_spec.expected_gap_count
                and report.critical_gap_count == case_spec.expected_critical_gap_count
            ),
            "Fact/gap counts match reviewed gold.",
            {
                "actual": {
                    "finding_count": report.finding_count,
                    "source_bound_finding_count": report.source_bound_finding_count,
                    "needs_review_finding_count": report.needs_review_finding_count,
                    "unknown_finding_count": report.unknown_finding_count,
                    "gap_count": report.gap_count,
                    "critical_gap_count": report.critical_gap_count,
                },
                "expected": {
                    "finding_count": case_spec.expected_finding_count,
                    "source_bound_finding_count": case_spec.expected_source_bound_finding_count,
                    "needs_review_finding_count": case_spec.expected_needs_review_finding_count,
                    "unknown_finding_count": case_spec.expected_unknown_finding_count,
                    "gap_count": case_spec.expected_gap_count,
                    "critical_gap_count": case_spec.expected_critical_gap_count,
                },
            },
        ),
        _case_check(
            case_spec,
            "critical_gap_ids_match_gold",
            critical_gap_ids == case_spec.expected_critical_gap_ids,
            "Critical gap IDs match reviewed gold.",
            {"actual": critical_gap_ids, "expected": case_spec.expected_critical_gap_ids},
        ),
        _case_check(
            case_spec,
            "warning_gap_ids_match_gold",
            warning_gap_ids == case_spec.expected_warning_gap_ids,
            "Warning gap IDs match reviewed gold.",
            {"actual": warning_gap_ids, "expected": case_spec.expected_warning_gap_ids},
        ),
        _case_check(
            case_spec,
            "relationship_topology_matches_gold",
            (
                report.relationship_topology.budget_treatment
                == case_spec.expected_relationship_budget_treatment
                and report.relationship_topology.unresolved_relationship_fact_ids
                == case_spec.expected_relationship_unresolved_fact_ids
                and report.relationship_topology.person_candidate_count
                == case_spec.expected_person_candidate_count
                and report.relationship_topology.organization_candidate_count
                == case_spec.expected_organization_candidate_count
                and report.relationship_topology.source_bound_relationship_count
                == case_spec.expected_source_bound_relationship_count
                and report.relationship_topology.critical_relationship_gap_count
                == case_spec.expected_critical_relationship_gap_count
            ),
            "Relationship topology summary matches reviewed gold.",
            {
                "actual": {
                    "budget_treatment": report.relationship_topology.budget_treatment,
                    "unresolved": report.relationship_topology.unresolved_relationship_fact_ids,
                    "person_candidate_count": report.relationship_topology.person_candidate_count,
                    "organization_candidate_count": (
                        report.relationship_topology.organization_candidate_count
                    ),
                    "source_bound_relationship_count": (
                        report.relationship_topology.source_bound_relationship_count
                    ),
                    "critical_relationship_gap_count": (
                        report.relationship_topology.critical_relationship_gap_count
                    ),
                }
            },
        ),
        _case_check(
            case_spec,
            "source_refs_are_complete",
            _source_refs_complete(report),
            "Every non-unknown source-bound fact keeps source refs, offsets, and hashes.",
            {},
        ),
        _case_check(
            case_spec,
            "no_side_effect_boundaries_crossed",
            _no_report_side_effects(report),
            "Gold replay report does not authorize or perform budget, matter, Lake, SQLite, external, or learning actions.",
            {},
        ),
    ]
    for expected in case_spec.expected_findings:
        finding = by_fact.get(expected.fact_id)
        passed = finding is not None and finding.current_state == expected.expected_state
        if expected.expected_source_bound is not None:
            passed = (
                passed
                and finding is not None
                and finding.source_bound == expected.expected_source_bound
            )
        if expected.expected_source_label_ids:
            passed = (
                passed
                and finding is not None
                and [source.label_id for source in finding.sources]
                == expected.expected_source_label_ids
            )
        checks.append(
            _case_check(
                case_spec,
                f"finding_matches_gold:{expected.fact_id}",
                passed,
                f"Finding `{expected.fact_id}` state and source support match reviewed gold.",
                {
                    "actual": (
                        None
                        if finding is None
                        else {
                            "state": finding.current_state,
                            "source_bound": finding.source_bound,
                            "source_label_ids": [source.label_id for source in finding.sources],
                        }
                    ),
                    "expected": expected.model_dump(mode="json"),
                },
            )
        )
    return checks


def _case_check(
    case_spec: LaborEmploymentBudgetFactGoldCaseSpec,
    check_id: str,
    passed: bool,
    message: str,
    details: dict[str, object],
) -> LaborEmploymentBudgetFactGoldCheck:
    return _check(
        check_id=check_id,
        passed=passed,
        message=message,
        case_id=case_spec.case_id,
        details=details,
    )


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    case_id: str | None = None,
    details: dict[str, object] | None = None,
) -> LaborEmploymentBudgetFactGoldCheck:
    return LaborEmploymentBudgetFactGoldCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        case_id=case_id,
        details=details or {},
    )


def _source_refs_complete(report: LaborEmploymentBudgetFactAuditReport) -> bool:
    for finding in report.findings:
        if finding.current_state == "unknown_missing":
            continue
        if not finding.sources:
            return False
        for source in finding.sources:
            ref = source.source_ref
            if not ref.source_segment_id or ref.start_offset >= ref.end_offset:
                return False
            if not ref.sha256.startswith("sha256:"):
                return False
    return True


def _no_gold_side_effects(gold: LaborEmploymentBudgetFactGoldSpec) -> bool:
    return not any(
        [
            gold.budget_amount_output_authorized,
            gold.budget_submission_authorized,
            gold.conflict_conclusion_emitted,
            gold.matter_opening_authorized,
            gold.training_pipeline_created,
            gold.lake_write_performed,
            gold.sqlite_write_performed,
            gold.external_writes_performed,
            gold.silent_learning_performed,
        ]
    )


def _no_report_side_effects(report: LaborEmploymentBudgetFactAuditReport) -> bool:
    return not any(
        [
            report.budget_amount_output_authorized,
            report.budget_submission_authorized,
            report.conflict_conclusion_emitted,
            report.matter_opening_authorized,
            report.training_pipeline_created,
            report.lake_write_performed,
            report.sqlite_write_performed,
            report.external_writes_performed,
        ]
    )
