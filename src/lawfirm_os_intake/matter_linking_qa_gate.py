from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .matter_linking_preflight import (
    MATTER_LINKING_PREFLIGHT_REPORT_FILENAME,
    run_matter_linking_preflight,
)
from .models import (
    MatterLinkingPreflightReport,
    MatterLinkingQAGateCase,
    MatterLinkingQAGateCheck,
    MatterLinkingQAGateReport,
)
from .util import digest_json, now_iso, write_json


MATTER_LINKING_QA_GATE_REPORT_FILENAME = "matter_linking_qa_gate_report.json"
MATTER_LINKING_QA_GATE_NOTES_FILENAME = "matter_linking_qa_gate_report.md"

REQUIRED_COVERAGE_TAGS = {
    "ambiguous_same_sender_multi_case",
    "resolved_followup_split_candidate",
    "weak_only_followup_blocked",
    "resolved_single_candidate",
    "conflicting_identifier_blocked",
    "no_official_matter_number_explicit",
    "human_review_required",
    "negative_split_evidence",
    "weak_sender_carrier_not_merge_authority",
    "no_write_boundary",
}

REQUIRED_NEXT_GATES = [
    "human_matter_linking_review",
    "sender_followup_before_budget_when_required",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_matter_linking_qa_gate",
    "exception_lake_owner_review_before_admission",
]


@dataclass(frozen=True)
class MatterLinkingQACaseSpec:
    case_id: str
    fixture_ref: str
    expected_status: str
    expected_overall_link_state: str
    expected_cluster_count: int
    expected_high_evidence_candidate_count: int
    expected_weak_only_candidate_count: int
    expected_negative_split_evidence_required: bool
    expected_sender_followup_required: bool
    expected_failed_check_ids: tuple[str, ...]
    required_coverage_tags: tuple[str, ...]


DEFAULT_CASE_SPECS = [
    MatterLinkingQACaseSpec(
        case_id="ambiguous_same_sender_multi_case",
        fixture_ref="examples/synthetic/upfront/upfront-like-intake-output.example.json",
        expected_status="matter_linking_preflight_requires_review",
        expected_overall_link_state="ambiguous_multiple_candidates",
        expected_cluster_count=2,
        expected_high_evidence_candidate_count=2,
        expected_weak_only_candidate_count=0,
        expected_negative_split_evidence_required=True,
        expected_sender_followup_required=True,
        expected_failed_check_ids=(),
        required_coverage_tags=(
            "ambiguous_same_sender_multi_case",
            "no_official_matter_number_explicit",
            "human_review_required",
            "negative_split_evidence",
            "weak_sender_carrier_not_merge_authority",
            "no_write_boundary",
        ),
    ),
    MatterLinkingQACaseSpec(
        case_id="resolved_followup_split_candidate",
        fixture_ref=(
            "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
        ),
        expected_status="matter_linking_preflight_resolved_candidate_requires_review",
        expected_overall_link_state="resolved_split_candidates_pending_human_confirmation",
        expected_cluster_count=2,
        expected_high_evidence_candidate_count=2,
        expected_weak_only_candidate_count=0,
        expected_negative_split_evidence_required=True,
        expected_sender_followup_required=False,
        expected_failed_check_ids=(),
        required_coverage_tags=(
            "resolved_followup_split_candidate",
            "no_official_matter_number_explicit",
            "human_review_required",
            "negative_split_evidence",
            "weak_sender_carrier_not_merge_authority",
            "no_write_boundary",
        ),
    ),
    MatterLinkingQACaseSpec(
        case_id="weak_only_followup_blocked",
        fixture_ref=(
            "examples/synthetic/upfront/"
            "upfront-like-intake-output.weak-single-candidate.example.json"
        ),
        expected_status="blocked_matter_linking_preflight",
        expected_overall_link_state="weak_single_candidate_requires_followup",
        expected_cluster_count=1,
        expected_high_evidence_candidate_count=0,
        expected_weak_only_candidate_count=1,
        expected_negative_split_evidence_required=False,
        expected_sender_followup_required=True,
        expected_failed_check_ids=(
            "weak_only_candidates_block_matter_linking",
            "clusters_have_source_bound_strong_support",
        ),
        required_coverage_tags=(
            "weak_only_followup_blocked",
            "no_official_matter_number_explicit",
            "human_review_required",
            "weak_sender_carrier_not_merge_authority",
            "no_write_boundary",
        ),
    ),
    MatterLinkingQACaseSpec(
        case_id="resolved_single_candidate",
        fixture_ref=(
            "examples/synthetic/upfront/"
            "upfront-like-intake-output.resolved-single-candidate.example.json"
        ),
        expected_status="matter_linking_preflight_resolved_candidate_requires_review",
        expected_overall_link_state="resolved_single_candidate_pending_human_confirmation",
        expected_cluster_count=1,
        expected_high_evidence_candidate_count=1,
        expected_weak_only_candidate_count=0,
        expected_negative_split_evidence_required=False,
        expected_sender_followup_required=False,
        expected_failed_check_ids=(),
        required_coverage_tags=(
            "resolved_single_candidate",
            "no_official_matter_number_explicit",
            "human_review_required",
            "weak_sender_carrier_not_merge_authority",
            "no_write_boundary",
        ),
    ),
    MatterLinkingQACaseSpec(
        case_id="conflicting_identifier_blocked",
        fixture_ref=(
            "examples/synthetic/upfront/"
            "upfront-like-intake-output.conflicting-identifiers.example.json"
        ),
        expected_status="blocked_matter_linking_preflight",
        expected_overall_link_state="conflicting_identifiers",
        expected_cluster_count=1,
        expected_high_evidence_candidate_count=0,
        expected_weak_only_candidate_count=0,
        expected_negative_split_evidence_required=False,
        expected_sender_followup_required=True,
        expected_failed_check_ids=(
            "multiple_candidate_clusters_require_review",
            "conflicting_identifiers_block_linking",
        ),
        required_coverage_tags=(
            "conflicting_identifier_blocked",
            "no_official_matter_number_explicit",
            "human_review_required",
            "weak_sender_carrier_not_merge_authority",
            "no_write_boundary",
        ),
    ),
]


def run_matter_linking_qa_gate(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkingQAGateReport, Path]:
    root = Path(repo_root).resolve()
    output_dir = Path(out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    case_reports = [
        _run_case(root=root, output_dir=output_dir, spec=spec, generated_at=generated_at)
        for spec in DEFAULT_CASE_SPECS
    ]
    report = _build_report(
        root=root,
        output_dir=output_dir,
        cases=case_reports,
        generated_at=generated_at,
    )
    write_json(output_dir / MATTER_LINKING_QA_GATE_REPORT_FILENAME, report.model_dump(mode="json"))
    (output_dir / MATTER_LINKING_QA_GATE_NOTES_FILENAME).write_text(
        render_matter_linking_qa_gate_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_matter_linking_qa_gate_report(report: MatterLinkingQAGateReport) -> str:
    lines = [
        "# Matter-Linking QA Gate Report",
        "",
        f"**Report ID:** `{report.matter_linking_qa_gate_report_id}`",
        f"**Status:** `{report.status}`",
        f"**Cases:** {report.case_count}",
        f"**Failed cases:** {report.failed_case_count}",
        "",
        "## Coverage",
        "",
        f"- Required coverage tags: {report.required_coverage_tag_count}",
        f"- Observed coverage tags: {report.observed_coverage_tag_count}",
        f"- Missing coverage tags: {', '.join(report.missing_coverage_tags) or 'none'}",
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
                f"- Fixture: `{case.fixture_ref}`",
                f"- Generated report: `{case.generated_report_ref}`",
                f"- Expected preflight status: `{case.expected_status}`",
                f"- Observed preflight status: `{case.observed_status}`",
                f"- Expected link state: `{case.expected_overall_link_state}`",
                f"- Observed link state: `{case.observed_overall_link_state}`",
                f"- Coverage: {', '.join(case.required_coverage_tags)}",
                f"- Notes: {' '.join(case.notes)}",
                "",
            ]
        )
    lines.extend(["## Checks", ""])
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- `{check.check_id}`: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- Synthetic only: {report.synthetic_only}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Budget amount output authorized: {report.budget_amount_output_authorized}",
            f"- Matter opening authorized: {report.matter_opening_authorized}",
            "",
            "This QA gate is local candidate-only evidence. It does not call Upfront, "
            "create screens, clear conflicts, output or submit budgets, open matters, "
            "write Lake/SQLite records, mutate sibling repos, promote canon, or learn.",
            "",
        ]
    )
    return "\n".join(lines)


def _run_case(
    *,
    root: Path,
    output_dir: Path,
    spec: MatterLinkingQACaseSpec,
    generated_at: str | None,
) -> MatterLinkingQAGateCase:
    case_dir = output_dir / "cases" / spec.case_id
    report, run_dir = run_matter_linking_preflight(
        input_path=root / spec.fixture_ref,
        out_dir=case_dir,
        generated_at=generated_at,
    )
    report_ref = run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME
    return _case_from_report(
        spec=spec,
        report=report,
        report_ref=report_ref,
    )


def _case_from_report(
    *,
    spec: MatterLinkingQACaseSpec,
    report: MatterLinkingPreflightReport,
    report_ref: Path,
) -> MatterLinkingQAGateCase:
    observed_failed = sorted(check.check_id for check in report.checks if check.status == "failed")
    case_passed = (
        report.status == spec.expected_status
        and report.overall_link_state == spec.expected_overall_link_state
        and report.cluster_count == spec.expected_cluster_count
        and report.high_evidence_candidate_count == spec.expected_high_evidence_candidate_count
        and report.weak_only_candidate_count == spec.expected_weak_only_candidate_count
        and report.negative_split_evidence_required
        == spec.expected_negative_split_evidence_required
        and report.sender_followup_required == spec.expected_sender_followup_required
        and set(spec.expected_failed_check_ids).issubset(set(observed_failed))
        and _boundary_clear(report)
    )
    notes = [
        "Expected matter-linking status matched."
        if case_passed
        else "Expected matter-linking status or boundary did not match.",
        "Official firm matter number remains unavailable and explicit."
        if report.official_matter_number_status == "not_available"
        else "Official firm matter number state drifted.",
    ]
    return MatterLinkingQAGateCase(
        case_id=spec.case_id,
        fixture_ref=spec.fixture_ref,
        generated_report_ref=str(report_ref),
        expected_status=spec.expected_status,
        observed_status=report.status,
        expected_overall_link_state=spec.expected_overall_link_state,
        observed_overall_link_state=report.overall_link_state,
        expected_cluster_count=spec.expected_cluster_count,
        observed_cluster_count=report.cluster_count,
        expected_high_evidence_candidate_count=spec.expected_high_evidence_candidate_count,
        observed_high_evidence_candidate_count=report.high_evidence_candidate_count,
        expected_weak_only_candidate_count=spec.expected_weak_only_candidate_count,
        observed_weak_only_candidate_count=report.weak_only_candidate_count,
        expected_negative_split_evidence_required=(spec.expected_negative_split_evidence_required),
        observed_negative_split_evidence_required=report.negative_split_evidence_required,
        expected_sender_followup_required=spec.expected_sender_followup_required,
        observed_sender_followup_required=report.sender_followup_required,
        expected_failed_check_ids=list(spec.expected_failed_check_ids),
        observed_failed_check_ids=observed_failed,
        required_coverage_tags=sorted(spec.required_coverage_tags),
        candidate_exception_lake_labels=report.candidate_exception_lake_labels,
        status="passed" if case_passed else "failed",
        notes=notes,
    )


def _build_report(
    *,
    root: Path,
    output_dir: Path,
    cases: list[MatterLinkingQAGateCase],
    generated_at: str | None,
) -> MatterLinkingQAGateReport:
    observed_tags = sorted({tag for case in cases for tag in case.required_coverage_tags})
    missing_tags = sorted(REQUIRED_COVERAGE_TAGS.difference(observed_tags))
    labels = sorted(
        {
            "matter_linking_qa_gate_candidate",
            *[label for case in cases for label in case.candidate_exception_lake_labels],
        }
    )
    checks = _checks(cases=cases, observed_tags=observed_tags, missing_tags=missing_tags)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    status = (
        "blocked_by_matter_linking_qa_gate"
        if failed_cases or failed_checks or missing_tags
        else "matter_linking_qa_gate_ready_for_review"
    )
    report_core = {
        "status": status,
        "cases": [
            {
                "case_id": case.case_id,
                "status": case.status,
                "observed_status": case.observed_status,
            }
            for case in cases
        ],
        "coverage_tags": observed_tags,
        "missing_tags": missing_tags,
    }
    return MatterLinkingQAGateReport(
        matter_linking_qa_gate_report_id="matterlinkqagate_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,
        repo_root_ref=str(root),
        out_dir_ref=str(output_dir),
        case_count=len(cases),
        passed_case_count=sum(1 for case in cases if case.status == "passed"),
        failed_case_count=len(failed_cases),
        required_coverage_tag_count=len(REQUIRED_COVERAGE_TAGS),
        observed_coverage_tag_count=len(observed_tags),
        missing_coverage_tags=missing_tags,
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=labels,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=generated_at or now_iso(),
    )


def _checks(
    *,
    cases: list[MatterLinkingQAGateCase],
    observed_tags: list[str],
    missing_tags: list[str],
) -> list[MatterLinkingQAGateCheck]:
    failed_cases = [case.case_id for case in cases if case.status == "failed"]
    side_effect_cases = [
        case.case_id
        for case in cases
        if (
            case.budget_amount_output_authorized
            or case.budget_submission_authorized
            or case.conflict_conclusion_emitted
            or case.matter_opening_authorized
            or case.lake_write_performed
            or case.sqlite_write_performed
            or case.external_writes_performed
            or case.silent_learning_performed
        )
    ]
    return [
        _check(
            "expected_case_matrix_present",
            len(cases) == len(DEFAULT_CASE_SPECS),
            "All default matter-linking QA fixture families were replayed.",
            case_ids=[case.case_id for case in cases],
            blocking_refs=[] if len(cases) == len(DEFAULT_CASE_SPECS) else ["case_count"],
        ),
        _check(
            "case_expectations_match",
            not failed_cases,
            "Each synthetic matter-linking fixture produced its expected safe state.",
            case_ids=[case.case_id for case in cases],
            blocking_refs=failed_cases,
        ),
        _check(
            "required_coverage_tags_present",
            not missing_tags,
            "Matter-linking QA covers weak signals, resolved candidates, conflicts, split evidence, no official matter number, review gates, and no-write boundaries.",
            case_ids=[case.case_id for case in cases],
            blocking_refs=missing_tags,
        ),
        _check(
            "no_side_effect_boundary",
            not side_effect_cases,
            "The gate and replayed reports preserve no budget, matter, conflict, Lake/SQLite, external-write, or learning side effects.",
            case_ids=[case.case_id for case in cases],
            blocking_refs=side_effect_cases,
        ),
        _check(
            "coverage_tags_are_known",
            set(observed_tags).issubset(REQUIRED_COVERAGE_TAGS),
            "Observed coverage tags are part of the declared matter-linking QA coverage contract.",
            blocking_refs=sorted(set(observed_tags).difference(REQUIRED_COVERAGE_TAGS)),
        ),
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    case_ids: list[str] | None = None,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> MatterLinkingQAGateCheck:
    return MatterLinkingQAGateCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        case_ids=case_ids or [],
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else case_ids or []),
    )


def _boundary_clear(report: MatterLinkingPreflightReport) -> bool:
    return (
        report.candidate_only is True
        and report.synthetic_only is True
        and report.non_authoritative is True
        and report.local_json_only is True
        and report.human_review_required is True
        and report.upfront_connector_implemented is False
        and report.vendor_api_called is False
        and report.external_write_performed is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.matter_opening_authorized is False
        and report.budget_amount_output_authorized is False
        and report.budget_submission_authorized is False
        and report.conflict_conclusion_emitted is False
        and report.screen_created is False
        and report.silent_learning_performed is False
    )
