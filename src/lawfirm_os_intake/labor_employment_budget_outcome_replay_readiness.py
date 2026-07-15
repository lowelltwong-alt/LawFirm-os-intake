from __future__ import annotations

from pathlib import Path

from .labor_employment_budget_learning_fixtures import REQUIRED_LEARNING_LOOP_TYPES
from .models import (
    LaborEmploymentBudgetLearningFixtureReport,
    LaborEmploymentBudgetLearningLoopType,
    LaborEmploymentBudgetOutcomeReplayReadinessCase,
    LaborEmploymentBudgetOutcomeReplayReadinessCheck,
    LaborEmploymentBudgetOutcomeReplayReadinessReport,
    LaborEmploymentBudgetOutcomeReplaySeedManifest,
    LaborEmploymentBudgetOutcomeReplaySeedSpec,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME = (
    "labor_employment_budget_outcome_replay_readiness_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_NOTES_FILENAME = (
    "labor_employment_budget_outcome_replay_readiness_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_outcome_seed_review",
    "execute_labor_employment_actuals_and_rejection_replay_harness",
    "compare_replay_outputs_to_reviewed_gold",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "no_budget_submission_from_outcome_replay_readiness",
    "no_lake_or_sqlite_write_from_outcome_replay_readiness",
]

REQUIRED_ARTIFACTS_BY_LOOP: dict[LaborEmploymentBudgetLearningLoopType, set[str]] = {
    "actuals_variance": {
        "budget_actual_comparison_report.json",
        "budget_actual_variance_ledger_report.json",
    },
    "carrier_rejection_capture": {
        "carrier_rejection_reconciliation_report.json",
        "carrier_rejection_decision_ledger_report.json",
    },
    "appeal_outcome": {
        "carrier_rejection_decision_ledger_report.json",
        "carrier_rejection_learning_report.json",
    },
    "reviewed_learning_gate": {
        "reviewed_learning_gate_report.json",
        "budget_learning_loop_report.json",
    },
    "blocked_budget_guard": {
        "labor_employment_budget_qa_gate_report.json",
        "labor_employment_budget_learning_fixtures_report.json",
    },
}


def _required_artifacts_for_seed(
    seed: LaborEmploymentBudgetOutcomeReplaySeedSpec,
    loop_type: LaborEmploymentBudgetLearningLoopType,
) -> set[str]:
    required = set(REQUIRED_ARTIFACTS_BY_LOOP[loop_type])
    if loop_type == "reviewed_learning_gate" and seed.replay_scope == "scoped_partial":
        required.discard("budget_learning_loop_report.json")
    return required


def run_labor_employment_budget_outcome_replay_readiness_audit(
    *,
    seed_manifest_path: str | Path,
    learning_fixture_report_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetOutcomeReplayReadinessReport, Path]:
    seed_ref = Path(seed_manifest_path)
    learning_ref = Path(learning_fixture_report_path)
    root = Path(repo_root)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = LaborEmploymentBudgetOutcomeReplaySeedManifest.model_validate(load_json(seed_ref))
    learning_report = LaborEmploymentBudgetLearningFixtureReport.model_validate(
        load_json(learning_ref)
    )
    cases = _cases(
        manifest=manifest,
        learning_report=learning_report,
        repo_root=root,
        seed_manifest_ref=seed_ref,
    )
    checks = _checks(manifest=manifest, learning_report=learning_report, cases=cases)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    covered_loops = _ordered_present(
        REQUIRED_LEARNING_LOOP_TYPES,
        {loop for case in cases for loop in case.seeded_learning_loop_types},
    )
    missing_loops = [
        loop
        for loop in REQUIRED_LEARNING_LOOP_TYPES
        if not any(loop in case.seeded_learning_loop_types for case in cases)
    ]
    labels = sorted(
        {
            "labor_employment_budget_outcome_replay_seed_candidate",
            *[label for case in cases for label in case.candidate_exception_lake_labels],
        }
    )
    generated = generated_at or now_iso()
    report_core = {
        "seed_manifest_id": manifest.manifest_id,
        "learning_report_id": learning_report.budget_learning_fixture_report_id,
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
    loop_requirement_count = sum(len(case.required_learning_loop_types) for case in cases)
    missing_loop_requirement_count = sum(len(case.missing_learning_loop_types) for case in cases)
    report = LaborEmploymentBudgetOutcomeReplayReadinessReport(
        outcome_replay_readiness_report_id="lebudgetoutcomereplay_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_outcome_replay"
            if failed_cases or failed_checks
            else "labor_employment_budget_outcome_replay_ready_for_review"
        ),
        source_seed_manifest_ref=str(seed_ref),
        source_seed_manifest_id=manifest.manifest_id,
        source_learning_fixture_report_ref=str(learning_ref),
        source_learning_fixture_report_id=(learning_report.budget_learning_fixture_report_id),
        source_learning_fixture_report_status=learning_report.status,
        fixture_count=len(cases),
        seed_spec_count=len(manifest.seeds),
        failed_case_count=len(failed_cases),
        loop_requirement_count=loop_requirement_count,
        seeded_loop_requirement_count=loop_requirement_count - missing_loop_requirement_count,
        missing_loop_requirement_count=missing_loop_requirement_count,
        unresolved_source_ref_count=sum(len(case.unresolved_source_refs) for case in cases),
        expected_replay_artifact_count=len(
            {artifact for case in cases for artifact in case.expected_replay_artifacts}
        ),
        covered_learning_loop_types=covered_loops,
        missing_learning_loop_types=missing_loops,
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=labels,
        required_next_gates=REQUIRED_NEXT_GATES,
        red_team_notes=[
            "This report proves replay-seed readiness, not replay execution or budget accuracy.",
            "Seeded outcome loops must still be executed and reviewed before calibration or model comparison.",
            "Blocked amount-budget fixtures stay in guard coverage and cannot enter actuals, rejection, appeal, or submitted-budget loops.",
        ],
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_NOTES_FILENAME).write_text(
        render_labor_employment_budget_outcome_replay_readiness_report(report), encoding="utf-8"
    )
    return report, output_dir


def render_labor_employment_budget_outcome_replay_readiness_report(
    report: LaborEmploymentBudgetOutcomeReplayReadinessReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Outcome Replay Readiness Report",
        "",
        f"**Report ID:** {report.outcome_replay_readiness_report_id}",
        f"**Status:** {report.status}",
        f"**Seed manifest:** `{report.source_seed_manifest_ref}`",
        f"**Learning fixture report:** `{report.source_learning_fixture_report_ref}`",
        "",
        "## Coverage",
        "",
        f"- Fixture cases: {report.fixture_count}",
        f"- Seed specs: {report.seed_spec_count}",
        f"- Loop requirements: {report.seeded_loop_requirement_count}/{report.loop_requirement_count}",
        f"- Unresolved source refs: {report.unresolved_source_ref_count}",
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
                f"- Seed: `{case.outcome_seed_id or 'missing'}`",
                f"- Family/variant: {case.family}/{case.variant}",
                "- Required loops: "
                + ", ".join(f"`{loop}`" for loop in case.required_learning_loop_types),
                "- Seeded loops: "
                + (", ".join(f"`{loop}`" for loop in case.seeded_learning_loop_types) or "none"),
                "- Expected replay artifacts: "
                + (
                    ", ".join(f"`{artifact}`" for artifact in case.expected_replay_artifacts)
                    or "none"
                ),
                "- Candidate Lake labels: "
                + (
                    ", ".join(f"`{label}`" for label in case.candidate_exception_lake_labels)
                    or "none"
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
            "This report is candidate-only synthetic QA evidence. It does not execute "
            "replay commands, submit budgets or appeals, write Lake/SQLite records, mutate "
            "templates, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _cases(
    *,
    manifest: LaborEmploymentBudgetOutcomeReplaySeedManifest,
    learning_report: LaborEmploymentBudgetLearningFixtureReport,
    repo_root: Path,
    seed_manifest_ref: Path,
) -> list[LaborEmploymentBudgetOutcomeReplayReadinessCase]:
    seeds_by_fixture = {seed.learning_fixture_id: seed for seed in manifest.seeds}
    return [
        _case(
            learning_case=learning_case,
            seed=seeds_by_fixture.get(learning_case.learning_fixture_id),
            repo_root=repo_root,
            seed_manifest_ref=seed_manifest_ref,
        )
        for learning_case in learning_report.cases
    ]


def _case(
    *,
    learning_case,
    seed: LaborEmploymentBudgetOutcomeReplaySeedSpec | None,
    repo_root: Path,
    seed_manifest_ref: Path,
) -> LaborEmploymentBudgetOutcomeReplayReadinessCase:
    failures: list[str] = []
    required_loops = list(learning_case.learning_loop_types)
    seeded_loops = list(seed.seeded_learning_loop_types) if seed else []
    missing_loops = [loop for loop in required_loops if loop not in seeded_loops]
    extra_loops = [loop for loop in seeded_loops if loop not in required_loops]
    missing_refs: list[LaborEmploymentBudgetLearningLoopType] = []
    missing_artifacts: list[LaborEmploymentBudgetLearningLoopType] = []
    missing_labels: list[LaborEmploymentBudgetLearningLoopType] = []
    unresolved_refs: list[str] = []
    expected_artifacts: list[str] = []
    labels: list[str] = []
    evidence_refs = [
        learning_case.learning_fixture_id,
        learning_case.executable_fixture_id,
        str(seed_manifest_ref),
        *learning_case.evidence_refs,
    ]

    if learning_case.status != "passed":
        failures.append("source_learning_fixture_case_not_passed")
    if seed is None:
        failures.append("outcome_seed_missing")
    else:
        if seed.executable_fixture_id != learning_case.executable_fixture_id:
            failures.append("executable_fixture_id_mismatch")
        if seed.family != learning_case.family:
            failures.append("family_mismatch")
        if seed.variant != learning_case.variant:
            failures.append("variant_mismatch")
        if seed.expected_budget_output_state != learning_case.expected_budget_output_state:
            failures.append("budget_output_state_mismatch")
        for loop_type in required_loops:
            refs = seed.replay_seed_refs_by_loop.get(loop_type, [])
            artifacts = seed.expected_replay_artifacts_by_loop.get(loop_type, [])
            loop_labels = seed.candidate_exception_lake_labels_by_loop.get(loop_type, [])
            expected_artifacts.extend(artifacts)
            labels.extend(loop_labels)
            evidence_refs.extend(refs)
            if loop_type in seeded_loops:
                if not refs:
                    missing_refs.append(loop_type)
                if not artifacts:
                    missing_artifacts.append(loop_type)
                if not loop_labels:
                    missing_labels.append(loop_type)
                required_artifacts = _required_artifacts_for_seed(seed, loop_type)
                if not required_artifacts.issubset(set(artifacts)):
                    missing_artifacts.append(loop_type)
                for ref in refs:
                    if not _ref_exists(ref, repo_root):
                        unresolved_refs.append(ref)
        if seed.expected_budget_output_state == "blocked_amount_budget" and (
            seeded_loops != ["blocked_budget_guard"]
        ):
            failures.append("blocked_seed_claims_non_guard_replay")
        if seed.expected_budget_output_state != "blocked_amount_budget" and (
            "blocked_budget_guard" in seeded_loops
        ):
            failures.append("nonblocking_seed_claims_blocked_guard")
        if _side_effects(seed):
            failures.append("outcome_seed_side_effect_boundary_failed")

    if missing_loops:
        failures.append("missing_seeded_learning_loop")
    if extra_loops:
        failures.append("extra_seeded_learning_loop")
    if missing_refs:
        failures.append("missing_replay_seed_refs")
    if missing_artifacts:
        failures.append("missing_expected_replay_artifacts")
    if missing_labels:
        failures.append("missing_candidate_exception_lake_labels")
    if unresolved_refs:
        failures.append("unresolved_replay_seed_refs")

    return LaborEmploymentBudgetOutcomeReplayReadinessCase(
        learning_fixture_id=learning_case.learning_fixture_id,
        executable_fixture_id=learning_case.executable_fixture_id,
        family=learning_case.family,
        variant=learning_case.variant,
        status="failed" if failures else "passed",
        expected_budget_output_state=learning_case.expected_budget_output_state,
        replay_scope=seed.replay_scope if seed else "scoped_partial",
        observed_budget_output_state=learning_case.observed_budget_output_state,
        outcome_seed_id=seed.outcome_seed_id if seed else None,
        required_learning_loop_types=required_loops,
        seeded_learning_loop_types=seeded_loops,
        missing_learning_loop_types=missing_loops,
        extra_learning_loop_types=extra_loops,
        missing_replay_seed_ref_loop_types=sorted(set(missing_refs)),
        missing_expected_artifact_loop_types=sorted(set(missing_artifacts)),
        missing_candidate_label_loop_types=sorted(set(missing_labels)),
        unresolved_source_refs=sorted(set(unresolved_refs)),
        expected_replay_artifacts=sorted(set(expected_artifacts)),
        candidate_exception_lake_labels=sorted(set(labels)),
        evidence_refs=sorted(set(evidence_refs)),
        failure_ids=sorted(set(failures)),
    )


def _checks(
    *,
    manifest: LaborEmploymentBudgetOutcomeReplaySeedManifest,
    learning_report: LaborEmploymentBudgetLearningFixtureReport,
    cases: list[LaborEmploymentBudgetOutcomeReplayReadinessCase],
) -> list[LaborEmploymentBudgetOutcomeReplayReadinessCheck]:
    failed_cases = [case.learning_fixture_id for case in cases if case.status == "failed"]
    learning_unready = (
        learning_report.status != "labor_employment_budget_learning_fixtures_ready_for_review"
    )
    learning_fixture_ids = {case.learning_fixture_id for case in learning_report.cases}
    seed_fixture_ids = {seed.learning_fixture_id for seed in manifest.seeds}
    extra_seeds = sorted(seed_fixture_ids - learning_fixture_ids)
    missing_seeds = sorted(learning_fixture_ids - seed_fixture_ids)
    unresolved_refs = sorted({ref for case in cases for ref in case.unresolved_source_refs})
    missing_loops = sorted({loop for case in cases for loop in case.missing_learning_loop_types})
    covered_loops = {loop for case in cases for loop in case.seeded_learning_loop_types}
    global_missing_loops = [
        loop for loop in REQUIRED_LEARNING_LOOP_TYPES if loop not in covered_loops
    ]
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
        if getattr(manifest, flag, False) is not False
        or getattr(learning_report, flag, False) is not False
    ]
    return [
        _check(
            "source_learning_fixture_report_ready",
            not learning_unready,
            "Source L&E budget-learning fixture report is ready for review.",
            evidence_refs=[learning_report.budget_learning_fixture_report_id],
            blocking_refs=[learning_report.status] if learning_unready else [],
        ),
        _check(
            "all_learning_fixture_cases_have_outcome_seeds",
            not missing_seeds and not extra_seeds,
            "Every L&E budget-learning fixture has exactly one outcome replay seed.",
            evidence_refs=sorted(learning_fixture_ids),
            blocking_refs=[*missing_seeds, *extra_seeds],
        ),
        _check(
            "all_outcome_replay_cases_pass",
            not failed_cases,
            "Every L&E budget outcome replay readiness case has refs, artifacts, labels, and matching state.",
            evidence_refs=[case.learning_fixture_id for case in cases],
            blocking_refs=failed_cases,
        ),
        _check(
            "required_learning_loop_types_seeded",
            not global_missing_loops and not missing_loops,
            "All required L&E learning-loop types are seeded for replay readiness.",
            evidence_refs=REQUIRED_LEARNING_LOOP_TYPES,
            blocking_refs=[*global_missing_loops, *missing_loops],
        ),
        _check(
            "replay_seed_refs_resolve",
            not unresolved_refs,
            "All local replay seed refs resolve under the repo root.",
            evidence_refs=[ref for case in cases for ref in case.evidence_refs],
            blocking_refs=unresolved_refs,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Seed manifest and learning report did not authorize budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[
                manifest.manifest_id,
                learning_report.budget_learning_fixture_report_id,
            ],
            blocking_refs=side_effects,
        ),
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str],
    blocking_refs: list[str],
) -> LaborEmploymentBudgetOutcomeReplayReadinessCheck:
    return LaborEmploymentBudgetOutcomeReplayReadinessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=sorted(set(evidence_refs)),
        blocking_refs=sorted(set(blocking_refs)),
    )


def _ref_exists(ref: str, repo_root: Path) -> bool:
    path_part = ref.split("#", maxsplit=1)[0]
    if not path_part:
        return True
    path = Path(path_part)
    if not path.is_absolute():
        path = repo_root / path
    try:
        resolved = path.resolve()
        root = repo_root.resolve()
    except OSError:
        return False
    return resolved.is_relative_to(root) and resolved.exists()


def _side_effects(seed: LaborEmploymentBudgetOutcomeReplaySeedSpec) -> bool:
    return any(
        getattr(seed, flag, False) is not False
        for flag in [
            "budget_submission_authorized",
            "matter_opening_authorized",
            "lake_write_performed",
            "sqlite_write_performed",
            "external_writes_performed",
            "silent_learning_performed",
        ]
    )


def _ordered_present(values: list, present: set) -> list:
    return [value for value in values if value in present]
