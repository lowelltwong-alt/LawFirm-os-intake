from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .labor_employment_budget_facts import run_labor_employment_budget_fact_audit
from .models import (
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentQAMatrixBudgetGateEffect,
    LaborEmploymentQAMatrixCase,
    LaborEmploymentQAMatrixReport,
)
from .util import digest_text, now_iso, write_json


LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME = "labor_employment_qa_matrix_report.json"
LABOR_EMPLOYMENT_QA_MATRIX_NOTES_FILENAME = "labor_employment_qa_matrix_report.md"

LABOR_EMPLOYMENT_QA_MATRIX_REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_fact_review",
    "no_amount_budget_when_critical_facts_missing",
    "range_or_hours_only_until_review",
    "no_role_taxonomy_promotion_from_matrix",
]


@dataclass(frozen=True)
class LaborEmploymentQAMatrixCaseSpec:
    case_id: str
    label: str
    manifest_ref: str
    expected_budget_readiness_state: str
    expected_budget_gate_effect: LaborEmploymentQAMatrixBudgetGateEffect


DEFAULT_CASES = [
    LaborEmploymentQAMatrixCaseSpec(
        case_id="critical_fact_gaps_block_amount_budget",
        label="Critical L&E Fact Gaps Block Amount Budget",
        manifest_ref="examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json",
        expected_budget_readiness_state="blocked_missing_critical_facts",
        expected_budget_gate_effect="block_amount_budget_before_proposal",
    ),
    LaborEmploymentQAMatrixCaseSpec(
        case_id="ready_critical_facts_still_range_only",
        label="Ready Critical L&E Facts Still Require Range Review",
        manifest_ref="examples/synthetic/courtlistener-derived/labor-employment-ready-critical-facts-manifest.json",
        expected_budget_readiness_state="range_only_pending_human_review",
        expected_budget_gate_effect="allow_range_or_hours_only_pending_review",
    ),
]


def run_labor_employment_qa_matrix(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
) -> tuple[LaborEmploymentQAMatrixReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        _case_from_spec(repo_root=repo_root, run_dir=run_dir, spec=spec) for spec in DEFAULT_CASES
    ]
    failed_cases = [case for case in cases if case.status == "failed"]
    report = LaborEmploymentQAMatrixReport(
        labor_employment_qa_matrix_report_id="leqamat_"
        + digest_text(
            "|".join(
                [
                    case.case_id
                    + ":"
                    + case.actual_budget_readiness_state
                    + ":"
                    + case.actual_budget_gate_effect
                    for case in cases
                ]
            )
        ).split(":", maxsplit=1)[1][:20],
        status=(
            "blocked_by_labor_employment_qa_matrix"
            if failed_cases
            else "labor_employment_qa_matrix_ready_for_review"
        ),
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        cases=cases,
        required_next_gates=LABOR_EMPLOYMENT_QA_MATRIX_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    write_json(run_dir / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / LABOR_EMPLOYMENT_QA_MATRIX_NOTES_FILENAME).write_text(
        render_labor_employment_qa_matrix_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_qa_matrix_report(report: LaborEmploymentQAMatrixReport) -> str:
    lines = [
        "# Labor/Employment QA Matrix Report",
        "",
        f"**Report ID:** {report.labor_employment_qa_matrix_report_id}",
        f"**Status:** {report.status}",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        "",
        "## Cases",
        "",
    ]
    for case in report.cases:
        lines.extend(
            [
                f"### {case.label}",
                "",
                f"- Case ID: `{case.case_id}`",
                f"- Status: {case.status}",
                f"- Manifest: `{case.manifest_ref}`",
                f"- Fact report: `{case.fact_report_ref}`",
                f"- Expected readiness: {case.expected_budget_readiness_state}",
                f"- Actual readiness: {case.actual_budget_readiness_state}",
                f"- Expected budget gate: {case.expected_budget_gate_effect}",
                f"- Actual budget gate: {case.actual_budget_gate_effect}",
                f"- Critical gaps: {case.critical_gap_count}",
                f"- Relationship treatment: {case.relationship_budget_treatment}",
                "- Notes:",
                *(f"  - {note}" for note in case.notes),
                "",
            ]
        )
    lines.extend(["## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This matrix is local synthetic QA evidence only. It does not approve a budget, promote role taxonomies, write Lake/SQLite records, open matters, submit budgets, or authorize learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_from_spec(
    *,
    repo_root: str | Path,
    run_dir: Path,
    spec: LaborEmploymentQAMatrixCaseSpec,
) -> LaborEmploymentQAMatrixCase:
    report, case_dir = run_labor_employment_budget_fact_audit(
        repo_root=repo_root,
        manifest_path=spec.manifest_ref,
        out_dir=run_dir / "cases" / spec.case_id,
    )
    report_ref = str(case_dir / "labor_employment_budget_fact_audit_report.json")
    actual_effect = _budget_gate_effect(report)
    no_side_effects = _no_side_effects(report)
    expected_matches = (
        report.status == "labor_employment_budget_facts_ready_for_review"
        and report.budget_readiness_state == spec.expected_budget_readiness_state
        and actual_effect == spec.expected_budget_gate_effect
        and no_side_effects
    )
    if spec.expected_budget_gate_effect == "block_amount_budget_before_proposal":
        expected_matches = expected_matches and report.critical_gap_count > 0
    if spec.expected_budget_gate_effect == "allow_range_or_hours_only_pending_review":
        expected_matches = (
            expected_matches
            and report.critical_gap_count == 0
            and report.gap_count > 0
            and report.budget_readiness_state == "range_only_pending_human_review"
        )
    return LaborEmploymentQAMatrixCase(
        case_id=spec.case_id,
        label=spec.label,
        status="passed" if expected_matches else "failed",
        manifest_ref=spec.manifest_ref,
        fact_report_ref=report_ref,
        expected_budget_readiness_state=spec.expected_budget_readiness_state,  # type: ignore[arg-type]
        actual_budget_readiness_state=report.budget_readiness_state,
        expected_budget_gate_effect=spec.expected_budget_gate_effect,
        actual_budget_gate_effect=actual_effect,
        critical_gap_count=report.critical_gap_count,
        gap_count=report.gap_count,
        source_bound_finding_count=report.source_bound_finding_count,
        unknown_finding_count=report.unknown_finding_count,
        needs_review_finding_count=report.needs_review_finding_count,
        relationship_budget_treatment=report.relationship_topology.budget_treatment,
        critical_relationship_gap_count=(
            report.relationship_topology.critical_relationship_gap_count
        ),
        required_human_question_count=len(report.required_human_questions),
        notes=_notes(report, expected_matches, no_side_effects),
    )


def _budget_gate_effect(
    report: LaborEmploymentBudgetFactAuditReport,
) -> LaborEmploymentQAMatrixBudgetGateEffect:
    if (
        report.budget_readiness_state == "blocked_missing_critical_facts"
        or report.critical_gap_count > 0
    ):
        return "block_amount_budget_before_proposal"
    if report.budget_readiness_state == "range_only_pending_human_review":
        return "allow_range_or_hours_only_pending_review"
    return "candidate_ready_for_budget_review_after_review"


def _no_side_effects(report: LaborEmploymentBudgetFactAuditReport) -> bool:
    return (
        report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.matter_opening_authorized is False
        and report.training_pipeline_created is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.candidate_only is True
        and report.non_authoritative is True
    )


def _notes(
    report: LaborEmploymentBudgetFactAuditReport,
    expected_matches: bool,
    no_side_effects: bool,
) -> list[str]:
    notes = [
        f"Fact audit status={report.status}; readiness={report.budget_readiness_state}.",
        f"Critical gaps={report.critical_gap_count}; total gaps={report.gap_count}.",
        f"Relationship topology treatment={report.relationship_topology.budget_treatment}.",
    ]
    if not no_side_effects:
        notes.append("Side-effect boundary failed; this matrix case must block.")
    if not expected_matches:
        notes.append("Observed readiness or gate effect did not match the expected QA case.")
    if report.budget_readiness_state == "blocked_missing_critical_facts":
        notes.append("Amount budget must remain blocked before proposal generation.")
    elif report.budget_readiness_state == "range_only_pending_human_review":
        notes.append("Budget may only proceed as range/hours-only pending human fact review.")
    return notes
