from __future__ import annotations

import re
from pathlib import Path

from .labor_employment_budget_learning_fixtures import REQUIRED_LEARNING_LOOP_TYPES
from .models import (
    LaborEmploymentBudgetLearningLoopType,
    LaborEmploymentBudgetOutcomeReplayExecutionArtifact,
    LaborEmploymentBudgetOutcomeReplayExecutionCase,
    LaborEmploymentBudgetOutcomeReplayExecutionCheck,
    LaborEmploymentBudgetOutcomeReplayExecutionReport,
    LaborEmploymentBudgetOutcomeReplayReadinessReport,
    LaborEmploymentBudgetOutcomeReplaySeedManifest,
    LaborEmploymentBudgetOutcomeReplaySeedSpec,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME = (
    "labor_employment_budget_outcome_replay_execution_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_NOTES_FILENAME = (
    "labor_employment_budget_outcome_replay_execution_report.md"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_SLOT_FILENAME = (
    "labor_employment_budget_outcome_replay_artifact_slot.json"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_outcome_execution_review",
    "bind_materialized_slots_to_real_replay_artifact_builders",
    "compare_replay_outputs_to_reviewed_gold",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "no_budget_submission_from_outcome_replay_execution",
    "no_lake_or_sqlite_write_from_outcome_replay_execution",
]


def run_labor_employment_budget_outcome_replay_execution(
    *,
    seed_manifest_path: str | Path,
    readiness_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetOutcomeReplayExecutionReport, Path]:
    seed_ref = Path(seed_manifest_path)
    readiness_ref = Path(readiness_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = LaborEmploymentBudgetOutcomeReplaySeedManifest.model_validate(load_json(seed_ref))
    readiness = LaborEmploymentBudgetOutcomeReplayReadinessReport.model_validate(
        load_json(readiness_ref)
    )
    seeds_by_fixture = {seed.learning_fixture_id: seed for seed in manifest.seeds}
    readiness_ready = (
        readiness.status == "labor_employment_budget_outcome_replay_ready_for_review"
        and readiness.failed_case_count == 0
        and readiness.unresolved_source_ref_count == 0
    )
    cases = [
        _execution_case(
            readiness_case=readiness_case,
            seed=seeds_by_fixture.get(readiness_case.learning_fixture_id),
            readiness_ready=readiness_ready,
            output_dir=output_dir,
        )
        for readiness_case in readiness.cases
    ]
    checks = _checks(manifest=manifest, readiness=readiness, cases=cases)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    covered_loops = _ordered_present(
        REQUIRED_LEARNING_LOOP_TYPES,
        {loop for case in cases for loop in case.materialized_learning_loop_types},
    )
    missing_loops = [loop for loop in REQUIRED_LEARNING_LOOP_TYPES if loop not in covered_loops]
    labels = sorted(
        {
            "labor_employment_budget_outcome_replay_execution_candidate",
            *[label for case in cases for label in case.candidate_exception_lake_labels],
        }
    )
    generated = generated_at or now_iso()
    report_core = {
        "manifest_id": manifest.manifest_id,
        "readiness_report_id": readiness.outcome_replay_readiness_report_id,
        "cases": [
            {
                "learning_fixture_id": case.learning_fixture_id,
                "status": case.status,
                "slots": case.materialized_artifact_slot_count,
                "failures": case.failure_ids,
            }
            for case in cases
        ],
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentBudgetOutcomeReplayExecutionReport(
        outcome_replay_execution_report_id="lebudgetoutcomeexecution_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_outcome_replay_execution"
            if failed_cases or failed_checks
            else "labor_employment_budget_outcome_replay_execution_ready_for_review"
        ),
        source_seed_manifest_ref=str(seed_ref),
        source_seed_manifest_id=manifest.manifest_id,
        source_readiness_report_ref=str(readiness_ref),
        source_readiness_report_id=readiness.outcome_replay_readiness_report_id,
        source_readiness_report_status=readiness.status,
        fixture_count=len(cases),
        materialized_case_count=len([case for case in cases if case.status == "passed"]),
        failed_case_count=len(failed_cases),
        expected_artifact_slot_count=sum(case.expected_artifact_slot_count for case in cases),
        materialized_artifact_slot_count=sum(
            case.materialized_artifact_slot_count for case in cases
        ),
        runtime_artifact_count=0,
        covered_learning_loop_types=covered_loops,
        missing_learning_loop_types=missing_loops,
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=labels,
        required_next_gates=REQUIRED_NEXT_GATES,
        red_team_notes=[
            "This report materializes candidate replay slots, not actual carrier, billing, or Lake artifacts.",
            "A future harness must bind each slot to the existing deterministic artifact builder before budget calibration claims.",
            "Blocked amount-budget fixtures remain guard-only and cannot be routed into submitted-budget rejection or actuals loops.",
        ],
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_NOTES_FILENAME).write_text(
        render_labor_employment_budget_outcome_replay_execution_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_budget_outcome_replay_execution_report(
    report: LaborEmploymentBudgetOutcomeReplayExecutionReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Outcome Replay Execution Report",
        "",
        f"**Report ID:** {report.outcome_replay_execution_report_id}",
        f"**Status:** {report.status}",
        f"**Seed manifest:** `{report.source_seed_manifest_ref}`",
        f"**Readiness report:** `{report.source_readiness_report_ref}`",
        "",
        "## Materialized Slots",
        "",
        f"- Cases: {report.materialized_case_count}/{report.fixture_count}",
        f"- Artifact slots: {report.materialized_artifact_slot_count}/{report.expected_artifact_slot_count}",
        f"- Runtime artifacts created: {report.runtime_artifact_count}",
        "- Covered loops: " + ", ".join(f"`{loop}`" for loop in report.covered_learning_loop_types),
        "- Missing loops: "
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
                f"- Replay case dir: `{case.replay_case_dir}`",
                f"- Family/variant: {case.family}/{case.variant}",
                "- Materialized loops: "
                + (
                    ", ".join(f"`{loop}`" for loop in case.materialized_learning_loop_types)
                    or "none"
                ),
                f"- Artifact slots: {case.materialized_artifact_slot_count}/{case.expected_artifact_slot_count}",
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
            "This report is candidate-only synthetic QA evidence. It materializes slot "
            "manifests for later deterministic replay binding, but it does not create "
            "billing, carrier, submitted-budget, Lake, SQLite, calibration, or learning artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def _execution_case(
    *,
    readiness_case,
    seed: LaborEmploymentBudgetOutcomeReplaySeedSpec | None,
    readiness_ready: bool,
    output_dir: Path,
) -> LaborEmploymentBudgetOutcomeReplayExecutionCase:
    case_dir = output_dir / "cases" / _slug(readiness_case.learning_fixture_id)
    failures: list[str] = []
    if not readiness_ready:
        failures.append("source_readiness_report_not_ready")
    if readiness_case.status != "passed":
        failures.append("source_readiness_case_failed")
    if seed is None:
        failures.append("seed_missing_for_readiness_case")

    artifact_slots: list[LaborEmploymentBudgetOutcomeReplayExecutionArtifact] = []
    required_loops = list(readiness_case.required_learning_loop_types)
    materialized_loops: list[LaborEmploymentBudgetLearningLoopType] = []
    blocked_loops: list[LaborEmploymentBudgetLearningLoopType] = []
    labels = set(readiness_case.candidate_exception_lake_labels)

    if seed is not None:
        for loop in required_loops:
            expected_names = sorted(seed.expected_replay_artifacts_by_loop.get(loop, []))
            if not expected_names:
                failures.append(f"missing_expected_artifacts_for_{loop}")
                blocked_loops.append(loop)
                continue
            if failures:
                for name in expected_names:
                    artifact_slots.append(
                        _blocked_slot(
                            loop=loop,
                            artifact_name=name,
                            evidence_refs=[
                                seed.outcome_seed_id,
                                readiness_case.learning_fixture_id,
                            ],
                        )
                    )
                blocked_loops.append(loop)
                continue
            slot_dir = case_dir / loop / "artifact-slots"
            slot_dir.mkdir(parents=True, exist_ok=True)
            for artifact_name in expected_names:
                slot_path = slot_dir / f"{artifact_name}.slot.json"
                slot_payload = _slot_payload(
                    seed=seed,
                    readiness_case=readiness_case,
                    loop=loop,
                    artifact_name=artifact_name,
                    slot_path=slot_path,
                )
                write_json(slot_path, slot_payload)
                artifact_slots.append(
                    LaborEmploymentBudgetOutcomeReplayExecutionArtifact(
                        loop_type=loop,
                        expected_artifact_name=artifact_name,
                        artifact_slot_ref=str(slot_path),
                        artifact_slot_status="materialized_candidate_slot",
                        evidence_refs=[
                            seed.outcome_seed_id,
                            readiness_case.learning_fixture_id,
                            *seed.replay_seed_refs_by_loop.get(loop, []),
                        ],
                    )
                )
            materialized_loops.append(loop)
            labels.update(seed.candidate_exception_lake_labels_by_loop.get(loop, []))

    failed = bool(failures)
    execution_case_id = (
        "leoutcomeexecutioncase_"
        + digest_json(
            {
                "learning_fixture_id": readiness_case.learning_fixture_id,
                "outcome_seed_id": seed.outcome_seed_id if seed is not None else None,
                "failures": failures,
                "slots": [
                    (slot.loop_type, slot.expected_artifact_name, slot.artifact_slot_status)
                    for slot in artifact_slots
                ],
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    return LaborEmploymentBudgetOutcomeReplayExecutionCase(
        execution_case_id=execution_case_id,
        learning_fixture_id=readiness_case.learning_fixture_id,
        executable_fixture_id=readiness_case.executable_fixture_id,
        outcome_seed_id=seed.outcome_seed_id if seed is not None else None,
        family=readiness_case.family,
        variant=readiness_case.variant,
        status="failed" if failed else "passed",
        expected_budget_output_state=readiness_case.expected_budget_output_state,
        replay_case_dir=str(case_dir),
        required_learning_loop_types=required_loops,
        materialized_learning_loop_types=_ordered_present(required_loops, set(materialized_loops)),
        blocked_learning_loop_types=_ordered_present(required_loops, set(blocked_loops)),
        expected_artifact_slot_count=len(artifact_slots),
        materialized_artifact_slot_count=len(
            [
                slot
                for slot in artifact_slots
                if slot.artifact_slot_status == "materialized_candidate_slot"
            ]
        ),
        artifact_slots=artifact_slots,
        candidate_exception_lake_labels=sorted(labels),
        evidence_refs=[
            readiness_case.learning_fixture_id,
            readiness_case.executable_fixture_id,
            *(readiness_case.evidence_refs or []),
        ],
        failure_ids=sorted(set(failures)),
    )


def _slot_payload(
    *,
    seed: LaborEmploymentBudgetOutcomeReplaySeedSpec,
    readiness_case,
    loop: LaborEmploymentBudgetLearningLoopType,
    artifact_name: str,
    slot_path: Path,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "slot_id": "leoutcomeslot_"
        + digest_json(
            {
                "seed": seed.outcome_seed_id,
                "loop": loop,
                "artifact": artifact_name,
            }
        )[len("sha256:") : len("sha256:") + 16],
        "status": "candidate_replay_artifact_slot_materialized",
        "source_outcome_seed_id": seed.outcome_seed_id,
        "source_learning_fixture_id": readiness_case.learning_fixture_id,
        "source_executable_fixture_id": readiness_case.executable_fixture_id,
        "loop_type": loop,
        "expected_artifact_name": artifact_name,
        "artifact_slot_ref": str(slot_path),
        "artifact_contract_note": (
            "This is a candidate slot for a future deterministic replay artifact; it is "
            "not the runtime artifact named by expected_artifact_name."
        ),
        "runtime_artifact_created": False,
        "candidate_only": True,
        "non_authoritative": True,
        "synthetic_only": True,
        "local_json_only": True,
        "budget_submission_authorized": False,
        "matter_opening_authorized": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "silent_learning_performed": False,
    }


def _blocked_slot(
    *,
    loop: LaborEmploymentBudgetLearningLoopType,
    artifact_name: str,
    evidence_refs: list[str],
) -> LaborEmploymentBudgetOutcomeReplayExecutionArtifact:
    return LaborEmploymentBudgetOutcomeReplayExecutionArtifact(
        loop_type=loop,
        expected_artifact_name=artifact_name,
        artifact_slot_ref="",
        artifact_slot_status="blocked_not_materialized",
        evidence_refs=evidence_refs,
    )


def _checks(
    *,
    manifest: LaborEmploymentBudgetOutcomeReplaySeedManifest,
    readiness: LaborEmploymentBudgetOutcomeReplayReadinessReport,
    cases: list[LaborEmploymentBudgetOutcomeReplayExecutionCase],
) -> list[LaborEmploymentBudgetOutcomeReplayExecutionCheck]:
    failed_cases = [case for case in cases if case.status == "failed"]
    materialized_slots = [
        slot
        for case in cases
        for slot in case.artifact_slots
        if slot.artifact_slot_status == "materialized_candidate_slot"
    ]
    runtime_slots = [slot for slot in materialized_slots if slot.runtime_artifact_created]
    return [
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="readiness_report_ready",
            status=(
                "passed"
                if readiness.status == "labor_employment_budget_outcome_replay_ready_for_review"
                and readiness.failed_case_count == 0
                and readiness.unresolved_source_ref_count == 0
                else "failed"
            ),
            message="Source readiness report is ready with no failed cases or unresolved refs.",
            evidence_refs=[readiness.outcome_replay_readiness_report_id],
            blocking_refs=[]
            if not failed_cases
            else [case.learning_fixture_id for case in failed_cases],
        ),
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="one_execution_case_per_seed",
            status="passed" if len(cases) == len(manifest.seeds) else "failed",
            message="Execution materializes one case for each seed manifest row.",
            evidence_refs=[manifest.manifest_id],
            blocking_refs=[] if len(cases) == len(manifest.seeds) else [manifest.manifest_id],
        ),
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="all_expected_artifact_slots_materialized",
            status=(
                "passed"
                if not failed_cases
                and sum(case.expected_artifact_slot_count for case in cases)
                == len(materialized_slots)
                else "failed"
            ),
            message="Every expected replay artifact is represented by a candidate slot.",
            evidence_refs=[case.execution_case_id for case in cases],
            blocking_refs=[case.learning_fixture_id for case in failed_cases],
        ),
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="runtime_artifacts_not_created",
            status="passed" if not runtime_slots else "failed",
            message="Execution creates slot manifests only, not runtime carrier/billing/Lake artifacts.",
            evidence_refs=[slot.artifact_slot_ref for slot in materialized_slots[:10]],
            blocking_refs=[slot.artifact_slot_ref for slot in runtime_slots],
        ),
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="blocked_budget_cases_guard_only",
            status="passed" if _blocked_cases_guard_only(cases) else "failed",
            message="Blocked amount-budget cases are restricted to the blocked-budget guard loop.",
            evidence_refs=[case.learning_fixture_id for case in cases],
            blocking_refs=[
                case.learning_fixture_id
                for case in cases
                if case.expected_budget_output_state == "blocked_amount_budget"
                and set(case.required_learning_loop_types) != {"blocked_budget_guard"}
            ],
        ),
        LaborEmploymentBudgetOutcomeReplayExecutionCheck(
            check_id="side_effect_flags_remain_false",
            status="passed" if _no_side_effects(cases) else "failed",
            message="All execution cases and artifact slots preserve no-write/no-learning flags.",
            evidence_refs=[case.execution_case_id for case in cases],
            blocking_refs=[
                case.execution_case_id
                for case in cases
                if not (
                    case.lake_write_performed is False
                    and case.sqlite_write_performed is False
                    and case.external_writes_performed is False
                    and case.silent_learning_performed is False
                    and case.runtime_artifacts_created is False
                )
            ],
        ),
    ]


def _blocked_cases_guard_only(
    cases: list[LaborEmploymentBudgetOutcomeReplayExecutionCase],
) -> bool:
    for case in cases:
        loops = set(case.required_learning_loop_types)
        if case.expected_budget_output_state == "blocked_amount_budget":
            if loops != {"blocked_budget_guard"}:
                return False
        elif "blocked_budget_guard" in loops:
            return False
    return True


def _no_side_effects(cases: list[LaborEmploymentBudgetOutcomeReplayExecutionCase]) -> bool:
    for case in cases:
        if not (
            case.lake_write_performed is False
            and case.sqlite_write_performed is False
            and case.external_writes_performed is False
            and case.silent_learning_performed is False
            and case.runtime_artifacts_created is False
        ):
            return False
        for slot in case.artifact_slots:
            if not (
                slot.lake_write_performed is False
                and slot.sqlite_write_performed is False
                and slot.external_writes_performed is False
                and slot.silent_learning_performed is False
                and slot.runtime_artifact_created is False
            ):
                return False
    return True


def _ordered_present(
    ordered: list[LaborEmploymentBudgetLearningLoopType],
    present: set[LaborEmploymentBudgetLearningLoopType],
) -> list[LaborEmploymentBudgetLearningLoopType]:
    return [item for item in ordered if item in present]


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return slug or "unknown"
