from __future__ import annotations

from pathlib import Path

from .labor_employment_budget_qa_gate import REQUIRED_FAMILIES
from .models import (
    LaborEmploymentBudgetLearningFixtureCase,
    LaborEmploymentBudgetLearningFixtureCheck,
    LaborEmploymentBudgetLearningFixtureManifest,
    LaborEmploymentBudgetLearningFixtureReport,
    LaborEmploymentBudgetLearningLoopType,
    LaborEmploymentBudgetQAGateReport,
    LaborEmploymentExecutableDriverAllowedBudgetOutput,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME = (
    "labor_employment_budget_learning_fixtures_report.json"
)
LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_NOTES_FILENAME = (
    "labor_employment_budget_learning_fixtures_report.md"
)

REQUIRED_LEARNING_LOOP_TYPES: list[LaborEmploymentBudgetLearningLoopType] = [
    "actuals_variance",
    "carrier_rejection_capture",
    "appeal_outcome",
    "reviewed_learning_gate",
    "blocked_budget_guard",
]

REQUIRED_BUDGET_OUTPUT_STATES: list[LaborEmploymentExecutableDriverAllowedBudgetOutput] = [
    "blocked_amount_budget",
    "range_or_hours_only_pending_review",
    "candidate_range_after_review_pending_human_review",
]

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_learning_fixture_review",
    "generate_labor_employment_actuals_and_carrier_rejection_payloads_before_calibration",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "no_budget_submission_from_labor_employment_budget_learning_fixtures",
    "no_lake_or_sqlite_write_from_labor_employment_budget_learning_fixtures",
]


def run_labor_employment_budget_learning_fixture_audit(
    *,
    manifest_path: str | Path,
    budget_qa_gate_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetLearningFixtureReport, Path]:
    manifest_ref = Path(manifest_path)
    qa_gate_ref = Path(budget_qa_gate_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = LaborEmploymentBudgetLearningFixtureManifest.model_validate(load_json(manifest_ref))
    qa_gate = LaborEmploymentBudgetQAGateReport.model_validate(load_json(qa_gate_ref))
    cases = _cases(manifest=manifest, qa_gate=qa_gate)
    checks = _checks(manifest=manifest, qa_gate=qa_gate, cases=cases)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    covered_families = sorted({case.family for case in cases})
    missing_families = sorted(set(REQUIRED_FAMILIES) - set(covered_families))
    covered_states = _ordered_present(
        REQUIRED_BUDGET_OUTPUT_STATES,
        {case.expected_budget_output_state for case in cases},
    )
    missing_states = [
        state for state in REQUIRED_BUDGET_OUTPUT_STATES if state not in covered_states
    ]
    covered_loops = _ordered_present(
        REQUIRED_LEARNING_LOOP_TYPES,
        {loop for case in cases for loop in case.learning_loop_types},
    )
    missing_loops = [loop for loop in REQUIRED_LEARNING_LOOP_TYPES if loop not in covered_loops]
    labels = sorted(
        {
            "labor_employment_budget_learning_fixture_candidate",
            *[label for case in cases for label in case.expected_candidate_exception_lake_labels],
        }
    )
    generated = generated_at or now_iso()
    report_core = {
        "manifest_id": manifest.manifest_id,
        "qa_gate_report_id": qa_gate.budget_qa_gate_report_id,
        "cases": [
            {
                "learning_fixture_id": case.learning_fixture_id,
                "status": case.status,
                "failures": case.failure_ids,
            }
            for case in cases
        ],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentBudgetLearningFixtureReport(
        budget_learning_fixture_report_id="lebudgetlearningfixtures_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_learning_fixtures"
            if failed_cases or failed_checks
            else "labor_employment_budget_learning_fixtures_ready_for_review"
        ),
        source_manifest_ref=str(manifest_ref),
        source_manifest_id=manifest.manifest_id,
        source_budget_qa_gate_report_ref=str(qa_gate_ref),
        source_budget_qa_gate_report_id=qa_gate.budget_qa_gate_report_id,
        source_budget_qa_gate_report_status=qa_gate.status,
        fixture_count=len(cases),
        failed_case_count=len(failed_cases),
        required_family_count=len(REQUIRED_FAMILIES),
        covered_required_family_count=len(covered_families),
        missing_required_families=missing_families,
        covered_budget_output_states=covered_states,
        missing_budget_output_states=missing_states,
        covered_learning_loop_types=covered_loops,
        missing_learning_loop_types=missing_loops,
        blocked_budget_guard_fixture_count=_loop_count(cases, "blocked_budget_guard"),
        actuals_variance_fixture_count=_loop_count(cases, "actuals_variance"),
        carrier_rejection_fixture_count=_loop_count(cases, "carrier_rejection_capture"),
        appeal_outcome_fixture_count=_loop_count(cases, "appeal_outcome"),
        reviewed_learning_gate_fixture_count=_loop_count(cases, "reviewed_learning_gate"),
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=labels,
        required_next_gates=REQUIRED_NEXT_GATES,
        red_team_notes=[
            "This report proves L&E learning-loop fixture coverage intent, not budget accuracy.",
            "Fixture specs must still be converted into executable actuals, rejection, and appeal payloads before calibration.",
            "Blocked amount-budget cases can only exercise guard and exception-classification loops, never submitted-budget rejection loops.",
        ],
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_NOTES_FILENAME).write_text(
        render_labor_employment_budget_learning_fixture_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_budget_learning_fixture_report(
    report: LaborEmploymentBudgetLearningFixtureReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Learning Fixture Report",
        "",
        f"**Report ID:** {report.budget_learning_fixture_report_id}",
        f"**Status:** {report.status}",
        f"**Manifest:** `{report.source_manifest_ref}`",
        f"**Budget QA gate:** `{report.source_budget_qa_gate_report_ref}`",
        "",
        "## Coverage",
        "",
        f"- Fixtures: {report.fixture_count}",
        f"- Families covered: {report.covered_required_family_count}/{report.required_family_count}",
        "- Missing families: "
        + (", ".join(f"`{family}`" for family in report.missing_required_families) or "none"),
        "- Covered budget states: "
        + ", ".join(f"`{state}`" for state in report.covered_budget_output_states),
        "- Missing budget states: "
        + (", ".join(f"`{state}`" for state in report.missing_budget_output_states) or "none"),
        "- Covered learning loops: "
        + ", ".join(f"`{loop}`" for loop in report.covered_learning_loop_types),
        "- Missing learning loops: "
        + (", ".join(f"`{loop}`" for loop in report.missing_learning_loop_types) or "none"),
        "",
        "## Cases",
        "",
    ]
    for case in report.cases:
        lines.extend(
            [
                f"### {case.learning_fixture_id}",
                "",
                f"- Status: {case.status}",
                f"- Executable fixture: `{case.executable_fixture_id}`",
                f"- Family/variant: {case.family}/{case.variant}",
                f"- Expected output: {case.expected_budget_output_state}",
                f"- Observed output: {case.observed_budget_output_state or 'missing'}",
                "- Learning loops: " + ", ".join(f"`{loop}`" for loop in case.learning_loop_types),
                "- Candidate Lake labels: "
                + ", ".join(
                    f"`{label}`" for label in case.expected_candidate_exception_lake_labels
                ),
                "- Failures: "
                + (", ".join(f"`{failure}`" for failure in case.failure_ids) or "none"),
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
    lines.extend(["", "## Red Team Notes", ""])
    lines.extend(f"- {note}" for note in report.red_team_notes)
    lines.extend(
        [
            "",
            "This report is candidate-only synthetic QA evidence. It does not create "
            "actuals, submit budgets, submit appeals, write Lake/SQLite records, mutate "
            "templates, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _cases(
    *,
    manifest: LaborEmploymentBudgetLearningFixtureManifest,
    qa_gate: LaborEmploymentBudgetQAGateReport,
) -> list[LaborEmploymentBudgetLearningFixtureCase]:
    output_by_fixture = _output_state_by_fixture(qa_gate)
    return [
        _case(spec=spec, output_by_fixture=output_by_fixture, manifest=manifest, qa_gate=qa_gate)
        for spec in manifest.fixtures
    ]


def _case(
    *,
    spec,
    output_by_fixture: dict[str, LaborEmploymentExecutableDriverAllowedBudgetOutput],
    manifest: LaborEmploymentBudgetLearningFixtureManifest,
    qa_gate: LaborEmploymentBudgetQAGateReport,
) -> LaborEmploymentBudgetLearningFixtureCase:
    observed = output_by_fixture.get(spec.executable_fixture_id)
    failures = []
    if observed is None:
        failures.append("executable_fixture_missing_from_budget_qa_gate")
    elif observed != spec.expected_budget_output_state:
        failures.append("budget_output_state_mismatch")
    if spec.family not in qa_gate.required_families_present:
        failures.append("family_missing_from_budget_qa_gate")
    if (
        spec.expected_budget_output_state == "blocked_amount_budget"
        and spec.learning_loop_types != ["blocked_budget_guard"]
    ):
        failures.append("blocked_fixture_claims_non_guard_learning_loop")
    evidence_refs = [
        spec.executable_fixture_id,
        manifest.manifest_id,
        qa_gate.budget_qa_gate_report_id,
        *spec.source_fixture_refs,
    ]
    return LaborEmploymentBudgetLearningFixtureCase(
        learning_fixture_id=spec.learning_fixture_id,
        executable_fixture_id=spec.executable_fixture_id,
        family=spec.family,
        variant=spec.variant,
        status="failed" if failures else "passed",
        expected_budget_output_state=spec.expected_budget_output_state,
        observed_budget_output_state=observed,
        learning_loop_types=spec.learning_loop_types,
        expected_candidate_exception_lake_labels=spec.expected_candidate_exception_lake_labels,
        expected_learning_targets=spec.expected_learning_targets,
        evidence_refs=sorted(set(evidence_refs)),
        failure_ids=sorted(set(failures)),
    )


def _checks(
    *,
    manifest: LaborEmploymentBudgetLearningFixtureManifest,
    qa_gate: LaborEmploymentBudgetQAGateReport,
    cases: list[LaborEmploymentBudgetLearningFixtureCase],
) -> list[LaborEmploymentBudgetLearningFixtureCheck]:
    failed_cases = [case.learning_fixture_id for case in cases if case.status == "failed"]
    families = {case.family for case in cases}
    missing_families = sorted(set(REQUIRED_FAMILIES) - families)
    states = {case.expected_budget_output_state for case in cases}
    missing_states = [state for state in REQUIRED_BUDGET_OUTPUT_STATES if state not in states]
    loops = {loop for case in cases for loop in case.learning_loop_types}
    missing_loops = [loop for loop in REQUIRED_LEARNING_LOOP_TYPES if loop not in loops]
    qa_gate_unready = qa_gate.status != "labor_employment_budget_qa_gate_ready_for_review"
    side_effects = [
        flag
        for flag in [
            "budget_submission_authorized",
            "matter_opening_authorized",
            "training_pipeline_created",
            "lake_write_performed",
            "sqlite_write_performed",
            "external_writes_performed",
            "silent_learning_performed",
        ]
        if getattr(manifest, flag, False) is not False or getattr(qa_gate, flag, False) is not False
    ]
    blocked_bad = [
        case.learning_fixture_id
        for case in cases
        if case.expected_budget_output_state == "blocked_amount_budget"
        and set(case.learning_loop_types) != {"blocked_budget_guard"}
    ]
    nonblocking_missing_gate = [
        case.learning_fixture_id
        for case in cases
        if case.expected_budget_output_state != "blocked_amount_budget"
        and "reviewed_learning_gate" not in case.learning_loop_types
    ]
    return [
        _check(
            "source_budget_qa_gate_ready",
            not qa_gate_unready,
            "Source L&E budget QA gate is ready for review.",
            evidence_refs=[qa_gate.budget_qa_gate_report_id],
            blocking_refs=[qa_gate.status] if qa_gate_unready else [],
        ),
        _check(
            "all_fixture_cases_pass",
            not failed_cases,
            "Every L&E budget-learning fixture maps to the expected budget QA state.",
            evidence_refs=[case.learning_fixture_id for case in cases],
            blocking_refs=failed_cases,
        ),
        _check(
            "required_families_have_learning_fixtures",
            not missing_families,
            "Every required L&E family has at least one learning fixture.",
            evidence_refs=REQUIRED_FAMILIES,
            blocking_refs=missing_families,
        ),
        _check(
            "required_budget_output_states_have_learning_fixtures",
            not missing_states,
            "Blocked, range/hours-only, and candidate-range output states are covered.",
            evidence_refs=REQUIRED_BUDGET_OUTPUT_STATES,
            blocking_refs=missing_states,
        ),
        _check(
            "required_learning_loop_types_covered",
            not missing_loops,
            "Actuals, carrier rejection, appeal, reviewed-learning, and blocked guard loops are covered.",
            evidence_refs=REQUIRED_LEARNING_LOOP_TYPES,
            blocking_refs=missing_loops,
        ),
        _check(
            "blocked_cases_do_not_claim_submitted_budget_loops",
            not blocked_bad,
            "Blocked amount-budget fixtures only exercise blocked-budget guard loops.",
            evidence_refs=[
                case.learning_fixture_id
                for case in cases
                if case.expected_budget_output_state == "blocked_amount_budget"
            ],
            blocking_refs=blocked_bad,
        ),
        _check(
            "nonblocking_cases_have_reviewed_learning_gate",
            not nonblocking_missing_gate,
            "Nonblocking L&E learning fixtures remain tied to reviewed-learning gates.",
            evidence_refs=[
                case.learning_fixture_id
                for case in cases
                if case.expected_budget_output_state != "blocked_amount_budget"
            ],
            blocking_refs=nonblocking_missing_gate,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Manifest and QA gate did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[manifest.manifest_id, qa_gate.budget_qa_gate_report_id],
            blocking_refs=side_effects,
        ),
    ]


def _output_state_by_fixture(
    qa_gate: LaborEmploymentBudgetQAGateReport,
) -> dict[str, LaborEmploymentExecutableDriverAllowedBudgetOutput]:
    output: dict[str, LaborEmploymentExecutableDriverAllowedBudgetOutput] = {}
    for bucket in qa_gate.output_state_buckets:
        for fixture_id in bucket.executable_fixture_ids:
            output[fixture_id] = bucket.output_state
    return output


def _loop_count(
    cases: list[LaborEmploymentBudgetLearningFixtureCase],
    loop_type: LaborEmploymentBudgetLearningLoopType,
) -> int:
    return sum(1 for case in cases if loop_type in case.learning_loop_types)


def _ordered_present(values: list, present: set) -> list:
    return [value for value in values if value in present]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str],
    blocking_refs: list[str],
) -> LaborEmploymentBudgetLearningFixtureCheck:
    return LaborEmploymentBudgetLearningFixtureCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs,
        blocking_refs=blocking_refs,
    )
