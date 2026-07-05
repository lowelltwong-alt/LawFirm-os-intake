from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentBudgetLearningLoopType,
    LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    LaborEmploymentBudgetOutcomeReplayBuilderBindingCase,
    LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck,
    LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
    LaborEmploymentBudgetOutcomeReplayBuilderContract,
    LaborEmploymentBudgetOutcomeReplayExecutionArtifact,
    LaborEmploymentBudgetOutcomeReplayExecutionCase,
    LaborEmploymentBudgetOutcomeReplayExecutionReport,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME = (
    "labor_employment_budget_outcome_replay_builder_binding_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_NOTES_FILENAME = (
    "labor_employment_budget_outcome_replay_builder_binding_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_replay_builder_binding_review",
    "add_synthetic_actuals_and_carrier_response_input_fixtures",
    "add_empty_complement_reports_or_relax_budget_learning_loop_contract",
    "compare_bound_replay_outputs_to_reviewed_gold",
    "reviewed_learning_gate_before_candidate_changes",
    "no_budget_submission_from_builder_binding_audit",
    "no_lake_or_sqlite_write_from_builder_binding_audit",
]

AGGREGATE_LEARNING_LOOP_INPUTS = [
    "budget_actual_comparison_report.json",
    "budget_actual_variance_ledger_report.json",
    "carrier_rejection_reconciliation_report.json",
    "carrier_rejection_decision_ledger_report.json",
    "carrier_rejection_review_packet.json",
    "carrier_rejection_learning_report.json",
    "reviewed_learning_gate_report.json",
]


def run_labor_employment_budget_outcome_replay_builder_binding_audit(
    *,
    execution_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetOutcomeReplayBuilderBindingReport, Path]:
    execution_ref = Path(execution_report_path)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    execution = LaborEmploymentBudgetOutcomeReplayExecutionReport.model_validate(
        load_json(execution_ref)
    )
    contracts = _builder_contracts()
    cases = [_binding_case(execution_case=case, contracts=contracts) for case in execution.cases]
    checks = _checks(execution=execution, cases=cases, contracts=contracts)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    slot_count = sum(case.slot_count for case in cases)
    bound_count = sum(case.bound_slot_count for case in cases)
    unknown_count = sum(case.unknown_artifact_count for case in cases)
    blocked_count = sum(case.blocked_slot_count for case in cases)
    input_gap_count = sum(case.replay_input_gap_count for case in cases)
    prerequisite_count = sum(case.missing_case_prerequisite_count for case in cases)
    generated = generated_at or now_iso()
    report_core = {
        "execution_report_id": execution.outcome_replay_execution_report_id,
        "case_count": len(cases),
        "slot_count": slot_count,
        "bound_count": bound_count,
        "unknown_count": unknown_count,
        "blocked_count": blocked_count,
        "failed_checks": [check.check_id for check in failed_checks],
    }
    report = LaborEmploymentBudgetOutcomeReplayBuilderBindingReport(
        builder_binding_report_id="lebudgetreplaybinding_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_labor_employment_budget_replay_builder_binding"
            if failed_cases or failed_checks
            else "labor_employment_budget_replay_builder_binding_ready_for_review"
        ),
        source_execution_report_ref=str(execution_ref),
        source_execution_report_id=execution.outcome_replay_execution_report_id,
        source_execution_report_status=execution.status,
        fixture_count=len(cases),
        case_count=len(cases),
        passed_case_count=len([case for case in cases if case.status == "passed"]),
        failed_case_count=len(failed_cases),
        slot_count=slot_count,
        bound_slot_count=bound_count,
        unknown_artifact_count=unknown_count,
        blocked_slot_count=blocked_count,
        replay_input_gap_count=input_gap_count,
        missing_case_prerequisite_count=prerequisite_count,
        builder_contracts=list(contracts.values()),
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=[
            "labor_employment_budget_replay_builder_binding_candidate",
            "labor_employment_budget_outcome_replay_execution_candidate",
        ],
        required_next_gates=REQUIRED_NEXT_GATES,
        red_team_notes=[
            "This audit binds replay slots to deterministic local builders but does not invoke them.",
            "A bound slot is not evidence that synthetic actuals, carrier responses, or review outcomes exist yet.",
            "Aggregate learning-loop replay still needs complement reports when a fixture only exercises actuals or carrier rejection lanes.",
        ],
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_NOTES_FILENAME).write_text(
        render_labor_employment_budget_replay_builder_binding_report(report), encoding="utf-8"
    )
    return report, output_dir


def render_labor_employment_budget_replay_builder_binding_report(
    report: LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Outcome Replay Builder Binding Report",
        "",
        f"**Report ID:** {report.builder_binding_report_id}",
        f"**Status:** {report.status}",
        f"**Execution report:** `{report.source_execution_report_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.passed_case_count}/{report.case_count} passed",
        f"- Bound slots: {report.bound_slot_count}/{report.slot_count}",
        f"- Unknown artifacts: {report.unknown_artifact_count}",
        f"- Blocked slots: {report.blocked_slot_count}",
        f"- Replay input gaps: {report.replay_input_gap_count}",
        f"- Missing case prerequisites: {report.missing_case_prerequisite_count}",
        "",
        "## Builder Contracts",
        "",
    ]
    for contract in sorted(
        report.builder_contracts,
        key=lambda item: (item.loop_type, item.artifact_name),
    ):
        lines.extend(
            [
                f"- `{contract.loop_type}` / `{contract.artifact_name}` -> "
                f"`{contract.builder_module}.{contract.builder_function}`",
                "  Inputs: " + ", ".join(f"`{item}`" for item in contract.required_input_artifacts),
                "  Emits: " + ", ".join(f"`{item}`" for item in contract.emitted_output_filenames),
            ]
        )
        if contract.intermediate_artifacts:
            lines.append(
                "  Intermediates: "
                + ", ".join(f"`{item}`" for item in contract.intermediate_artifacts)
            )
    lines.extend(["", "## Case Gaps", ""])
    for case in report.cases:
        gap_ids = sorted(
            {
                gap
                for binding in case.bindings
                for gap in [
                    *binding.replay_input_gap_ids,
                    *binding.missing_case_prerequisite_artifacts,
                ]
            }
        )
        lines.extend(
            [
                f"- `{case.learning_fixture_id}`: {case.bound_slot_count}/{case.slot_count} bound; "
                f"input gaps={case.replay_input_gap_count}; prerequisites={case.missing_case_prerequisite_count}",
                "  Gaps: " + (", ".join(f"`{item}`" for item in gap_ids) or "none"),
            ]
        )
    lines.extend(["", "## Checks", ""])
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
            "This report is candidate-only synthetic QA evidence. It does not run replay builders, "
            "create billing or carrier artifacts, admit Lake records, submit budgets, open matters, "
            "or silently learn from outcomes.",
            "",
        ]
    )
    return "\n".join(lines)


def _builder_contracts() -> dict[
    tuple[LaborEmploymentBudgetLearningLoopType, str],
    LaborEmploymentBudgetOutcomeReplayBuilderContract,
]:
    contracts = [
        _contract(
            "actuals_variance",
            "budget_actual_comparison_report.json",
            "lawfirm_os_intake.budget_actuals",
            "run_budget_actual_comparison",
            [
                "budget_actual_comparison_report.json",
                "budget_actual_variance_ledger_report.json",
                "budget_actual_variance_candidates.jsonl",
            ],
            ["legal_budget_proposal.json", "budget_actuals_source.json"],
        ),
        _contract(
            "actuals_variance",
            "budget_actual_variance_ledger_report.json",
            "lawfirm_os_intake.budget_actuals",
            "run_budget_actual_comparison",
            [
                "budget_actual_comparison_report.json",
                "budget_actual_variance_ledger_report.json",
                "budget_actual_variance_candidates.jsonl",
            ],
            ["legal_budget_proposal.json", "budget_actuals_source.json"],
            ["budget_actual_comparison_report.json"],
        ),
        _contract(
            "carrier_rejection_capture",
            "carrier_rejection_reconciliation_report.json",
            "lawfirm_os_intake.carrier_rejections",
            "run_carrier_rejection_capture",
            [
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_decision_ledger_report.json",
                "carrier_rejection_remediation_cases.json",
                "carrier_rejection_exception_lake_candidates.jsonl",
            ],
            ["legal_budget_proposal.json", "carrier_rejection_capture_source_bundle.json"],
        ),
        _contract(
            "carrier_rejection_capture",
            "carrier_rejection_decision_ledger_report.json",
            "lawfirm_os_intake.carrier_rejections",
            "run_carrier_rejection_capture",
            [
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_decision_ledger_report.json",
                "carrier_rejection_remediation_cases.json",
                "carrier_rejection_exception_lake_candidates.jsonl",
            ],
            ["legal_budget_proposal.json", "carrier_rejection_capture_source_bundle.json"],
            ["carrier_rejection_reconciliation_report.json"],
        ),
        _contract(
            "appeal_outcome",
            "carrier_rejection_decision_ledger_report.json",
            "lawfirm_os_intake.carrier_rejections",
            "run_carrier_rejection_capture",
            [
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_decision_ledger_report.json",
                "carrier_rejection_remediation_cases.json",
                "carrier_rejection_exception_lake_candidates.jsonl",
            ],
            [
                "legal_budget_proposal.json",
                "carrier_rejection_capture_source_bundle_with_appeal_results.json",
            ],
            ["carrier_rejection_reconciliation_report.json"],
        ),
        _contract(
            "appeal_outcome",
            "carrier_rejection_learning_report.json",
            "lawfirm_os_intake.carrier_rejection_learning",
            "run_carrier_rejection_learning",
            ["carrier_rejection_learning_report.json"],
            ["carrier_rejection_review_packet.json"],
            [
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_review_packet.json",
            ],
        ),
        _contract(
            "reviewed_learning_gate",
            "reviewed_learning_gate_report.json",
            "lawfirm_os_intake.reviewed_learning_gate",
            "run_reviewed_learning_gate",
            ["reviewed_learning_gate_report.json", "reviewed_learning_gate_candidates.jsonl"],
            [
                "one_or_more_of:carrier_rejection_learning_report.json,budget_actual_comparison_report.json,budget_revision_report.json",
            ],
        ),
        _contract(
            "reviewed_learning_gate",
            "budget_learning_loop_report.json",
            "lawfirm_os_intake.budget_learning_loop",
            "run_budget_learning_loop_report",
            ["budget_learning_loop_report.json"],
            AGGREGATE_LEARNING_LOOP_INPUTS,
            ["carrier_rejection_review_packet.json"],
        ),
        _contract(
            "blocked_budget_guard",
            "labor_employment_budget_qa_gate_report.json",
            "lawfirm_os_intake.labor_employment_budget_qa_gate",
            "run_labor_employment_budget_qa_gate",
            ["labor_employment_budget_qa_gate_report.json"],
            [
                "labor_employment_budget_output_expectations_report.json",
                "labor_employment_blocked_driver_impact_review_report.json",
                "labor_employment_executable_coverage_report.json",
            ],
        ),
        _contract(
            "blocked_budget_guard",
            "labor_employment_budget_learning_fixtures_report.json",
            "lawfirm_os_intake.labor_employment_budget_learning_fixtures",
            "run_labor_employment_budget_learning_fixture_audit",
            ["labor_employment_budget_learning_fixtures_report.json"],
            [
                "labor_employment_budget_learning_fixtures.json",
                "labor_employment_budget_qa_gate_report.json",
            ],
            ["labor_employment_budget_qa_gate_report.json"],
        ),
    ]
    return {(contract.loop_type, contract.artifact_name): contract for contract in contracts}


def _contract(
    loop_type: LaborEmploymentBudgetLearningLoopType,
    artifact_name: str,
    builder_module: str,
    builder_function: str,
    emitted_output_filenames: list[str],
    required_input_artifacts: list[str],
    intermediate_artifacts: list[str] | None = None,
) -> LaborEmploymentBudgetOutcomeReplayBuilderContract:
    return LaborEmploymentBudgetOutcomeReplayBuilderContract(
        artifact_name=artifact_name,
        loop_type=loop_type,
        builder_module=builder_module,
        builder_function=builder_function,
        emitted_output_filenames=emitted_output_filenames,
        required_input_artifacts=required_input_artifacts,
        intermediate_artifacts=intermediate_artifacts or [],
    )


def _binding_case(
    *,
    execution_case: LaborEmploymentBudgetOutcomeReplayExecutionCase,
    contracts: dict[
        tuple[LaborEmploymentBudgetLearningLoopType, str],
        LaborEmploymentBudgetOutcomeReplayBuilderContract,
    ],
) -> LaborEmploymentBudgetOutcomeReplayBuilderBindingCase:
    case_artifacts = {
        slot.expected_artifact_name
        for slot in execution_case.artifact_slots
        if slot.artifact_slot_status == "materialized_candidate_slot"
    }
    bindings = [
        _binding(
            execution_case=execution_case,
            slot=slot,
            contract=contracts.get((slot.loop_type, slot.expected_artifact_name)),
            case_artifacts=case_artifacts,
        )
        for slot in execution_case.artifact_slots
    ]
    failures = sorted(
        {
            failure
            for binding in bindings
            for failure in (
                [binding.binding_status]
                if binding.binding_status != "bound_to_existing_builder"
                else []
            )
        }
    )
    binding_case_id = (
        "lebudgetreplaybindingcase_"
        + digest_json(
            {
                "execution_case_id": execution_case.execution_case_id,
                "bindings": [
                    (binding.loop_type, binding.expected_artifact_name, binding.binding_status)
                    for binding in bindings
                ],
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    return LaborEmploymentBudgetOutcomeReplayBuilderBindingCase(
        binding_case_id=binding_case_id,
        execution_case_id=execution_case.execution_case_id,
        learning_fixture_id=execution_case.learning_fixture_id,
        executable_fixture_id=execution_case.executable_fixture_id,
        outcome_seed_id=execution_case.outcome_seed_id,
        family=execution_case.family,
        variant=execution_case.variant,
        status="failed" if failures else "passed",
        expected_budget_output_state=execution_case.expected_budget_output_state,
        slot_count=len(bindings),
        bound_slot_count=len(
            [
                binding
                for binding in bindings
                if binding.binding_status == "bound_to_existing_builder"
            ]
        ),
        unknown_artifact_count=len(
            [
                binding
                for binding in bindings
                if binding.binding_status == "blocked_unknown_artifact"
            ]
        ),
        blocked_slot_count=len(
            [
                binding
                for binding in bindings
                if binding.binding_status == "blocked_slot_not_materialized"
            ]
        ),
        replay_input_gap_count=sum(len(binding.replay_input_gap_ids) for binding in bindings),
        missing_case_prerequisite_count=sum(
            len(binding.missing_case_prerequisite_artifacts) for binding in bindings
        ),
        bindings=bindings,
        evidence_refs=[
            execution_case.execution_case_id,
            execution_case.learning_fixture_id,
            *execution_case.evidence_refs,
        ],
        failure_ids=failures,
    )


def _binding(
    *,
    execution_case: LaborEmploymentBudgetOutcomeReplayExecutionCase,
    slot: LaborEmploymentBudgetOutcomeReplayExecutionArtifact,
    contract: LaborEmploymentBudgetOutcomeReplayBuilderContract | None,
    case_artifacts: set[str],
) -> LaborEmploymentBudgetOutcomeReplayBuilderBinding:
    if slot.artifact_slot_status != "materialized_candidate_slot":
        status = "blocked_slot_not_materialized"
        notes = ["The source execution report did not materialize this candidate slot."]
        return _blocked_binding(execution_case, slot, status, notes)
    if contract is None:
        status = "blocked_unknown_artifact"
        notes = ["No deterministic local builder contract is registered for this slot."]
        return _blocked_binding(execution_case, slot, status, notes)

    missing_prerequisites = [
        artifact
        for artifact in _case_prerequisites(contract)
        if artifact not in case_artifacts and not artifact.startswith("one_or_more_of:")
    ]
    replay_gaps = _replay_input_gaps(contract)
    notes = [
        "Expected artifact is bound to an existing deterministic local builder contract.",
        "Binding audit does not invoke the builder or create runtime outputs.",
    ]
    if missing_prerequisites:
        notes.append(
            "Case-level complement artifacts are absent and must be supplied before full replay."
        )
    if replay_gaps:
        notes.append(
            "Synthetic input fixtures are still required before this builder can be exercised."
        )
    binding_id = (
        "lebudgetreplaybinding_"
        + digest_json(
            {
                "case": execution_case.execution_case_id,
                "loop": slot.loop_type,
                "artifact": slot.expected_artifact_name,
                "builder": contract.builder_function,
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    return LaborEmploymentBudgetOutcomeReplayBuilderBinding(
        binding_id=binding_id,
        execution_case_id=execution_case.execution_case_id,
        learning_fixture_id=execution_case.learning_fixture_id,
        executable_fixture_id=execution_case.executable_fixture_id,
        outcome_seed_id=execution_case.outcome_seed_id,
        loop_type=slot.loop_type,
        expected_artifact_name=slot.expected_artifact_name,
        artifact_slot_ref=slot.artifact_slot_ref,
        artifact_slot_status=slot.artifact_slot_status,
        binding_status="bound_to_existing_builder",
        builder_module=contract.builder_module,
        builder_function=contract.builder_function,
        emitted_output_filenames=contract.emitted_output_filenames,
        required_input_artifacts=contract.required_input_artifacts,
        intermediate_artifacts=contract.intermediate_artifacts,
        missing_case_prerequisite_artifacts=missing_prerequisites,
        replay_input_gap_ids=replay_gaps,
        side_effect_boundary=contract.side_effect_boundary,
        binding_notes=notes,
        evidence_refs=[
            execution_case.execution_case_id,
            execution_case.learning_fixture_id,
            slot.artifact_slot_ref,
            *slot.evidence_refs,
        ],
    )


def _blocked_binding(
    execution_case: LaborEmploymentBudgetOutcomeReplayExecutionCase,
    slot: LaborEmploymentBudgetOutcomeReplayExecutionArtifact,
    status: str,
    notes: list[str],
) -> LaborEmploymentBudgetOutcomeReplayBuilderBinding:
    binding_id = (
        "lebudgetreplaybinding_"
        + digest_json(
            {
                "case": execution_case.execution_case_id,
                "loop": slot.loop_type,
                "artifact": slot.expected_artifact_name,
                "status": status,
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    return LaborEmploymentBudgetOutcomeReplayBuilderBinding(
        binding_id=binding_id,
        execution_case_id=execution_case.execution_case_id,
        learning_fixture_id=execution_case.learning_fixture_id,
        executable_fixture_id=execution_case.executable_fixture_id,
        outcome_seed_id=execution_case.outcome_seed_id,
        loop_type=slot.loop_type,
        expected_artifact_name=slot.expected_artifact_name,
        artifact_slot_ref=slot.artifact_slot_ref,
        artifact_slot_status=slot.artifact_slot_status,
        binding_status=status,  # type: ignore[arg-type]
        binding_notes=notes,
        evidence_refs=[
            execution_case.execution_case_id,
            execution_case.learning_fixture_id,
            *slot.evidence_refs,
        ],
    )


def _case_prerequisites(
    contract: LaborEmploymentBudgetOutcomeReplayBuilderContract,
) -> list[str]:
    if contract.artifact_name == "budget_learning_loop_report.json":
        return AGGREGATE_LEARNING_LOOP_INPUTS
    return [
        artifact
        for artifact in contract.required_input_artifacts
        if artifact.endswith("_report.json") or artifact.endswith("_packet.json")
    ]


def _replay_input_gaps(contract: LaborEmploymentBudgetOutcomeReplayBuilderContract) -> list[str]:
    gaps = []
    for artifact in contract.required_input_artifacts:
        if artifact in {
            "legal_budget_proposal.json",
            "budget_actuals_source.json",
            "carrier_rejection_capture_source_bundle.json",
            "carrier_rejection_capture_source_bundle_with_appeal_results.json",
        }:
            gaps.append(f"needs_synthetic_{artifact.removesuffix('.json')}")
        if artifact.startswith("one_or_more_of:"):
            gaps.append("needs_at_least_one_reviewed_learning_signal_report")
    return sorted(gaps)


def _checks(
    *,
    execution: LaborEmploymentBudgetOutcomeReplayExecutionReport,
    cases: list[LaborEmploymentBudgetOutcomeReplayBuilderBindingCase],
    contracts: dict[
        tuple[LaborEmploymentBudgetLearningLoopType, str],
        LaborEmploymentBudgetOutcomeReplayBuilderContract,
    ],
) -> list[LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck]:
    slots = [binding for case in cases for binding in case.bindings]
    unknown = [binding for binding in slots if binding.binding_status == "blocked_unknown_artifact"]
    blocked = [
        binding for binding in slots if binding.binding_status == "blocked_slot_not_materialized"
    ]
    bound = [binding for binding in slots if binding.binding_status == "bound_to_existing_builder"]
    side_effect_violations = [
        binding
        for binding in bound
        if not (
            binding.lake_write_performed is False
            and binding.sqlite_write_performed is False
            and binding.external_writes_performed is False
            and binding.silent_learning_performed is False
            and binding.runtime_artifact_created is False
        )
    ]
    return [
        LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck(
            check_id="source_execution_report_ready",
            status=(
                "passed"
                if execution.status
                == "labor_employment_budget_outcome_replay_execution_ready_for_review"
                else "failed"
            ),
            message="Source execution report is ready and contains materialized candidate slots.",
            evidence_refs=[execution.outcome_replay_execution_report_id],
            blocking_refs=[] if not blocked else [binding.artifact_slot_ref for binding in blocked],
        ),
        LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck(
            check_id="all_slots_bound_to_known_builders",
            status="passed" if not unknown and not blocked else "failed",
            message="Every replay slot maps to a deterministic local builder contract.",
            evidence_refs=[binding.binding_id for binding in bound[:20]],
            blocking_refs=[
                binding.expected_artifact_name
                for binding in [*unknown, *blocked]
                if binding.expected_artifact_name
            ],
        ),
        LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck(
            check_id="builder_contracts_are_no_write",
            status="passed" if not side_effect_violations else "failed",
            message="Builder bindings preserve local candidate/no-write/no-learning boundaries.",
            evidence_refs=[contract.artifact_name for contract in contracts.values()],
            blocking_refs=[binding.binding_id for binding in side_effect_violations],
        ),
        LaborEmploymentBudgetOutcomeReplayBuilderBindingCheck(
            check_id="replay_gaps_are_explicit",
            status="passed",
            message="Synthetic input gaps and missing complement reports are explicit review data.",
            evidence_refs=[case.binding_case_id for case in cases],
        ),
    ]
