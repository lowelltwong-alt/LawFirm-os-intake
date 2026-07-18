from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Literal
import unicodedata

from pydantic import ValidationError

from .models import (
    BudgetActualComparisonReport,
    BudgetActualVarianceLedgerReport,
    BudgetActualsSource,
    BudgetLearningLoopReport,
    BudgetProposal,
    BudgetRevisionReport,
    CarrierRejectionCaptureSourceBundle,
    HumanConfirmation,
    CarrierRejectionDecisionLedgerReport,
    CarrierRejectionLearningReport,
    CarrierRejectionReviewPacket,
    CarrierResponseReconciliationReport,
    LaborEmploymentBlockedDriverImpactReviewReport,
    LaborEmploymentBudgetLearningFixtureManifest,
    LaborEmploymentBudgetLearningFixtureReport,
    LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    LaborEmploymentBudgetOutcomeReplayBuilderBindingCase,
    LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
    LaborEmploymentBudgetOutcomeReplayInputPackCase,
    LaborEmploymentBudgetOutcomeReplayInputPackCheck,
    LaborEmploymentBudgetOutcomeReplayInputPackEntry,
    LaborEmploymentBudgetOutcomeReplayInputPackItem,
    LaborEmploymentBudgetOutcomeReplayInputPackManifest,
    LaborEmploymentBudgetOutcomeReplayInputPackReport,
    LaborEmploymentBudgetOutputExpectationReport,
    LaborEmploymentBudgetQAGateReport,
    LaborEmploymentExecutableCoverageReport,
    LaborEmploymentExecutableFixtureManifest,
    ReviewedLearningGateReport,
    SourceBundle,
)
from .segmenter import segment_bundle
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME = (
    "labor_employment_budget_outcome_replay_input_pack_report.json"
)
LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_NOTES_FILENAME = (
    "labor_employment_budget_outcome_replay_input_pack_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_replay_input_pack_review",
    "add_case_specific_synthetic_budget_proposals",
    "add_case_specific_synthetic_actuals_sources",
    "add_case_specific_synthetic_carrier_response_and_appeal_bundles",
    "add_carrier_rejection_review_packets_for_learning_replay",
    "execute_only_ready_replay_slots_under_orchestrator_ownership",
    "no_budget_submission_from_replay_input_pack_audit",
    "no_lake_or_sqlite_write_from_replay_input_pack_audit",
]

PREFLIGHT_REQUIRED_INPUT_PRIORITY = {
    "legal_budget_proposal.json": 0,
    "budget_actuals_source.json": 1,
    "carrier_rejection_capture_source_bundle.json": 2,
    "carrier_rejection_capture_source_bundle_with_appeal_results.json": 3,
}

ARTIFACT_MODELS: dict[str, type[Any]] = {
    "legal_budget_proposal.json": BudgetProposal,
    "budget_actuals_source.json": BudgetActualsSource,
    "budget_actual_comparison_report.json": BudgetActualComparisonReport,
    "budget_actual_variance_ledger_report.json": BudgetActualVarianceLedgerReport,
    "budget_revision_report.json": BudgetRevisionReport,
    "carrier_rejection_capture_source_bundle.json": CarrierRejectionCaptureSourceBundle,
    "carrier_rejection_capture_source_bundle_with_appeal_results.json": (
        CarrierRejectionCaptureSourceBundle
    ),
    "carrier_rejection_reconciliation_report.json": CarrierResponseReconciliationReport,
    "carrier_rejection_decision_ledger_report.json": CarrierRejectionDecisionLedgerReport,
    "carrier_rejection_review_packet.json": CarrierRejectionReviewPacket,
    "carrier_rejection_learning_report.json": CarrierRejectionLearningReport,
    "reviewed_learning_gate_report.json": ReviewedLearningGateReport,
    "budget_learning_loop_report.json": BudgetLearningLoopReport,
    "labor_employment_budget_output_expectations_report.json": (
        LaborEmploymentBudgetOutputExpectationReport
    ),
    "labor_employment_blocked_driver_impact_review_report.json": (
        LaborEmploymentBlockedDriverImpactReviewReport
    ),
    "labor_employment_executable_coverage_report.json": LaborEmploymentExecutableCoverageReport,
    "labor_employment_budget_qa_gate_report.json": LaborEmploymentBudgetQAGateReport,
    "labor_employment_budget_learning_fixtures.json": (
        LaborEmploymentBudgetLearningFixtureManifest
    ),
    "labor_employment_budget_learning_fixtures_report.json": (
        LaborEmploymentBudgetLearningFixtureReport
    ),
}

CASE_IDENTITY_FIELDS = ("budget_proposal_id", "preflight_packet_id")
CASE_IDENTITY_ANCHOR_ARTIFACTS = {
    "legal_budget_proposal.json",
    "budget_actuals_source.json",
    "carrier_rejection_capture_source_bundle.json",
}
SOURCE_CASE_TOKEN_CONTEXT_KEY = "__source_case_tokens__"
RAW_SOURCE_CASE_IDENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "budget_actuals_source.json": ("budget_proposal_id",),
    "carrier_rejection_capture_source_bundle.json": (
        "budget_proposal_id",
        "preflight_packet_id",
    ),
    "carrier_rejection_capture_source_bundle_with_appeal_results.json": (
        "budget_proposal_id",
        "preflight_packet_id",
    ),
}
RAW_SOURCE_CASE_TOKEN_FIELDS: dict[str, tuple[str, ...]] = {
    "budget_actuals_source.json": ("actuals_source_id", "source_ref"),
    "carrier_rejection_capture_source_bundle.json": ("bundle_id", "run_id"),
    "carrier_rejection_capture_source_bundle_with_appeal_results.json": (
        "bundle_id",
        "run_id",
    ),
}
CASE_BOUND_REPORT_ARTIFACTS = {
    "budget_actual_comparison_report.json",
    "budget_actual_variance_ledger_report.json",
    "budget_revision_report.json",
    "carrier_rejection_reconciliation_report.json",
    "carrier_rejection_decision_ledger_report.json",
    "carrier_rejection_review_packet.json",
    "carrier_rejection_learning_report.json",
}
FAMILY_BOUND_ARTIFACTS = {
    "legal_budget_proposal.json",
}

PROHIBITED_TRUE_FIELDS = {
    "billing_connector_write_performed",
    "budget_submission_authorized",
    "client_submission_authorized",
    "external_submission_authorized",
    "external_writes_performed",
    "lake_write_performed",
    "matter_opening_authorized",
    "runtime_artifact_created",
    "runtime_artifacts_created",
    "silent_learning_performed",
    "sqlite_write_performed",
    "training_pipeline_created",
}
PROHIBITED_REAL_DATA_FIELDS = {
    "contains_privileged_data",
    "contains_real_client_data",
    "contains_real_matter_data",
}
PROHIBITED_FALSE_AUTHORITY_FIELDS = {
    "not_authorized_for_budget_submission",
    "not_authorized_for_client_submission",
    "not_authorized_for_external_submission",
    "not_authorized_for_external_write",
    "not_authorized_for_lake_write",
    "not_authorized_for_matter_opening",
    "not_authorized_for_sqlite_write",
}


def _load_executable_fixture_source_refs(
    *,
    manifest: LaborEmploymentBudgetOutcomeReplayInputPackManifest | None,
    repo_root: Path,
    expected_manifest_ref: str | None,
    expected_manifest_sha256: str | None,
) -> tuple[dict[str, str], str | None, str | None, str | None, str | None]:
    if not expected_manifest_ref or not expected_manifest_sha256:
        return {}, None, None, None, "builder binding has no executable manifest provenance"
    if manifest is None or not manifest.executable_fixture_manifest_ref:
        return {}, None, None, None, "executable fixture manifest ref is missing"
    if manifest.executable_fixture_manifest_ref != expected_manifest_ref:
        return (
            {},
            manifest.executable_fixture_manifest_ref,
            None,
            None,
            "executable fixture manifest ref does not match builder binding provenance",
        )
    manifest_path = _resolve_local_ref(manifest.executable_fixture_manifest_ref, repo_root)
    if manifest_path is None:
        return (
            {},
            manifest.executable_fixture_manifest_ref,
            None,
            None,
            "executable fixture manifest ref is not a local JSON ref",
        )
    if not manifest_path.is_file():
        return (
            {},
            manifest.executable_fixture_manifest_ref,
            None,
            None,
            "executable fixture manifest ref does not exist",
        )
    try:
        manifest_payload = load_json(manifest_path)
        fixture_manifest = LaborEmploymentExecutableFixtureManifest.model_validate(manifest_payload)
        manifest_sha256 = digest_json(manifest_payload)
    except (OSError, ValueError, ValidationError) as exc:
        return (
            {},
            manifest.executable_fixture_manifest_ref,
            None,
            None,
            f"executable fixture manifest validation failed: {exc}",
        )
    if manifest_sha256 != expected_manifest_sha256:
        return (
            {},
            manifest.executable_fixture_manifest_ref,
            fixture_manifest.manifest_id,
            manifest_sha256,
            "executable fixture manifest hash does not match builder binding provenance",
        )
    return (
        {
            fixture.executable_fixture_id: fixture.source_bundle_ref
            for fixture in fixture_manifest.fixtures
        },
        manifest.executable_fixture_manifest_ref,
        fixture_manifest.manifest_id,
        manifest_sha256,
        None,
    )


def run_labor_employment_budget_outcome_replay_input_pack_audit(
    *,
    builder_binding_report_path: str | Path,
    out_dir: str | Path,
    input_pack_manifest_path: str | Path | None = None,
    repo_root: str | Path = ".",
    generated_at: str | None = None,
) -> tuple[LaborEmploymentBudgetOutcomeReplayInputPackReport, Path]:
    binding_ref = Path(builder_binding_report_path)
    output_dir = Path(out_dir)
    root = Path(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    binding_report = LaborEmploymentBudgetOutcomeReplayBuilderBindingReport.model_validate(
        load_json(binding_ref)
    )
    manifest_ref = Path(input_pack_manifest_path) if input_pack_manifest_path else None
    manifest = (
        LaborEmploymentBudgetOutcomeReplayInputPackManifest.model_validate(load_json(manifest_ref))
        if manifest_ref
        else None
    )
    entries = manifest.entries if manifest else []
    (
        expected_source_bundle_refs,
        executable_manifest_ref,
        executable_manifest_id,
        executable_manifest_sha256,
        executable_manifest_error,
    ) = _load_executable_fixture_source_refs(
        manifest=manifest,
        repo_root=root,
        expected_manifest_ref=binding_report.source_executable_fixture_manifest_ref,
        expected_manifest_sha256=(binding_report.source_executable_fixture_manifest_sha256),
    )
    cases = [
        _input_pack_case(
            binding_case=case,
            entries=entries,
            repo_root=root,
            expected_source_bundle_refs=expected_source_bundle_refs,
        )
        for case in binding_report.cases
    ]
    checks = _checks(
        binding_report=binding_report,
        manifest=manifest,
        cases=cases,
        executable_manifest_error=executable_manifest_error,
        executable_manifest_ref=executable_manifest_ref,
    )
    failed_checks = [check for check in checks if check.status == "failed"]
    invalid_count = sum(case.invalid_input_count for case in cases)
    missing_count = sum(case.missing_input_count for case in cases)
    generated = generated_at or now_iso()
    report_core = {
        "binding_report_id": binding_report.builder_binding_report_id,
        "manifest_id": manifest.manifest_id if manifest else None,
        "case_statuses": [(case.learning_fixture_id, case.status) for case in cases],
        "missing": missing_count,
        "invalid": invalid_count,
        "failed_checks": [check.check_id for check in failed_checks],
        "executable_manifest_sha256": executable_manifest_sha256,
    }
    status = _report_status(
        missing_input_count=missing_count,
        invalid_input_count=invalid_count,
        failed_checks=failed_checks,
    )
    report = LaborEmploymentBudgetOutcomeReplayInputPackReport(
        input_pack_report_id="lebudgetreplayinputpack_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,
        source_builder_binding_report_ref=str(binding_ref),
        source_builder_binding_report_id=binding_report.builder_binding_report_id,
        source_builder_binding_report_status=binding_report.status,
        source_input_pack_manifest_ref=str(manifest_ref) if manifest_ref else None,
        source_input_pack_manifest_id=manifest.manifest_id if manifest else None,
        source_executable_fixture_manifest_ref=executable_manifest_ref,
        source_executable_fixture_manifest_id=executable_manifest_id,
        source_executable_fixture_manifest_sha256=executable_manifest_sha256,
        case_count=len(cases),
        ready_case_count=len([case for case in cases if case.status == "ready"]),
        partial_case_count=len([case for case in cases if case.status == "partially_ready"]),
        blocked_case_count=len([case for case in cases if case.status == "blocked"]),
        required_input_count=sum(case.required_input_count for case in cases),
        ready_input_count=sum(case.ready_input_count for case in cases),
        missing_input_count=missing_count,
        invalid_input_count=invalid_count,
        one_of_signal_missing_count=sum(case.one_of_signal_missing_count for case in cases),
        cases=cases,
        checks=checks,
        candidate_exception_lake_labels=sorted(
            {
                "labor_employment_budget_replay_input_pack_candidate",
                *[
                    label
                    for case in cases
                    for item in case.items
                    for label in item.candidate_exception_lake_labels
                ],
            }
        ),
        required_next_gates=REQUIRED_NEXT_GATES,
        red_team_notes=[
            "This audit validates replay input refs; it does not run builders or create runtime artifacts.",
            "Ready inputs are not proof that the resulting budget, rejection, actuals, or appeal math is correct.",
            "Synthetic confirmation anchors validate fixture provenance only and cannot complete a runtime human gate.",
            "Missing one-of reviewed learning signals must stay blocked until a reviewed candidate report exists.",
            "The deterministic input/path/schema checker is a future Rust leaf-tool candidate once Python remains the oracle.",
        ],
        rust_transition_candidates=[
            "deterministic_local_ref_resolution_and_path_safety_checker",
            "bulk_replay_input_schema_validation_helper",
            "side_effect_flag_scanner_for_candidate_json_artifacts",
        ],
        generated_at=generated,
    )
    write_json(
        output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (output_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_NOTES_FILENAME).write_text(
        render_labor_employment_budget_outcome_replay_input_pack_report(report),
        encoding="utf-8",
    )
    return report, output_dir


def render_labor_employment_budget_outcome_replay_input_pack_report(
    report: LaborEmploymentBudgetOutcomeReplayInputPackReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Outcome Replay Input-Pack Report",
        "",
        f"**Report ID:** {report.input_pack_report_id}",
        f"**Status:** {report.status}",
        f"**Builder binding report:** `{report.source_builder_binding_report_ref}`",
        f"**Input-pack manifest:** `{report.source_input_pack_manifest_ref or 'not supplied'}`",
        "",
        "## Summary",
        "",
        f"- Cases ready: {report.ready_case_count}/{report.case_count}",
        f"- Required inputs: {report.ready_input_count}/{report.required_input_count} ready",
        f"- Missing inputs: {report.missing_input_count}",
        f"- Invalid inputs: {report.invalid_input_count}",
        f"- Missing one-of reviewed signals: {report.one_of_signal_missing_count}",
        "",
        "## Preflight Gap Matrix",
        "",
        "This section is preflight-only. It validates declared local JSON refs and shows the "
        "next missing or invalid replay slots without running builders or creating runtime artifacts.",
        "",
    ]
    lines.extend(_render_preflight_gap_matrix(report))
    lines.extend(
        [
            "",
            "## Cases",
            "",
        ]
    )
    for case in report.cases:
        lines.extend(
            [
                f"### {case.learning_fixture_id}",
                "",
                f"- Status: {case.status}",
                f"- Inputs: {case.ready_input_count}/{case.required_input_count} ready",
                f"- Missing: {case.missing_input_count}; invalid: {case.invalid_input_count}",
            ]
        )
        missing = [item for item in case.items if item.input_status != "ready"]
        if missing:
            lines.append(
                "- Not ready: "
                + ", ".join(
                    f"`{item.required_input_artifact}` ({item.input_status})" for item in missing
                )
            )
        ready = [item for item in case.items if item.input_status == "ready"]
        if ready:
            lines.append(
                "- Ready refs: "
                + ", ".join(
                    f"`{item.required_input_artifact}` -> `{item.input_ref}`" for item in ready[:8]
                )
            )
        lines.append("")
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
    lines.extend(["", "## Rust Transition Candidates", ""])
    lines.extend(f"- {candidate}" for candidate in report.rust_transition_candidates)
    lines.extend(["", "## Red Team Notes", ""])
    lines.extend(f"- {note}" for note in report.red_team_notes)
    lines.extend(
        [
            "",
            "This report is candidate-only synthetic QA evidence. It does not submit budgets, "
            "open matters, write to the Exception Lake or SQLite, call connectors, or silently learn.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_preflight_gap_matrix(
    report: LaborEmploymentBudgetOutcomeReplayInputPackReport,
) -> list[str]:
    not_ready_cases = [
        case for case in report.cases if case.missing_input_count or case.invalid_input_count
    ]
    if not not_ready_cases:
        return ["All replay input-pack cases are ready for reviewed replay."]

    lines: list[str] = [
        "| Case | Family | Loop | Expected artifact | Required input | Role | Status | Validator |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in sorted(
        not_ready_cases,
        key=lambda item: (
            item.status != "blocked",
            -item.invalid_input_count,
            -item.missing_input_count,
            item.learning_fixture_id,
        ),
    ):
        for item in _not_ready_items_for_preflight(case):
            lines.append(
                " | ".join(
                    [
                        f"| `{_md_cell(case.learning_fixture_id)}`",
                        f"`{_md_cell(case.family)}`",
                        f"`{_md_cell(item.loop_type)}`",
                        f"`{_md_cell(item.expected_artifact_name)}`",
                        f"`{_md_cell(item.required_input_artifact)}`",
                        f"`{_md_cell(item.input_role)}`",
                        f"`{_md_cell(item.input_status)}`",
                        f"`{_md_cell(item.validation_model or 'unregistered')}` |",
                    ]
                )
            )

    lines.extend(["", "### Preflight Next Actions", ""])
    for case in not_ready_cases:
        next_item = _first_preflight_action_item(case)
        if next_item is None:
            continue
        lines.append(
            "- "
            f"`{case.learning_fixture_id}`: add or repair "
            f"`{next_item.required_input_artifact}` for `{next_item.loop_type}` -> "
            f"`{next_item.expected_artifact_name}`; "
            f"{next_item.validation_message}"
        )
    return lines


def _not_ready_items_for_preflight(
    case: LaborEmploymentBudgetOutcomeReplayInputPackCase,
) -> list[LaborEmploymentBudgetOutcomeReplayInputPackItem]:
    return sorted(
        [item for item in case.items if item.input_status != "ready"],
        key=lambda item: (
            item.input_status != "invalid",
            item.loop_type,
            item.expected_artifact_name,
            PREFLIGHT_REQUIRED_INPUT_PRIORITY.get(item.required_input_artifact, 100),
            item.required_input_artifact,
        ),
    )


def _first_preflight_action_item(
    case: LaborEmploymentBudgetOutcomeReplayInputPackCase,
) -> LaborEmploymentBudgetOutcomeReplayInputPackItem | None:
    items = _not_ready_items_for_preflight(case)
    builder_items = [item for item in items if item.input_role == "builder_input"]
    complement_items = [item for item in items if item.input_role == "complement_report"]
    one_of_items = [item for item in items if item.input_role == "one_of_signal"]
    ordered = [*builder_items, *complement_items, *one_of_items]
    return ordered[0] if ordered else None


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _input_pack_case(
    *,
    binding_case: LaborEmploymentBudgetOutcomeReplayBuilderBindingCase,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    repo_root: Path,
    expected_source_bundle_refs: dict[str, str],
) -> LaborEmploymentBudgetOutcomeReplayInputPackCase:
    items = [
        item
        for binding in binding_case.bindings
        if binding.binding_status == "bound_to_existing_builder"
        for item in _items_for_binding(
            binding=binding,
            entries=entries,
            repo_root=repo_root,
            expected_family=binding_case.family,
            expected_source_bundle_refs=expected_source_bundle_refs,
        )
    ]
    invalid = len([item for item in items if item.input_status == "invalid"])
    missing = len([item for item in items if item.input_status == "missing"])
    failures = sorted(
        {item.required_input_artifact for item in items if item.input_status == "invalid"}
    )
    status = "blocked" if invalid else "ready" if not missing else "partially_ready"
    input_pack_case_id = (
        "lebudgetreplayinputpackcase_"
        + digest_json(
            {
                "binding_case_id": binding_case.binding_case_id,
                "statuses": [
                    (item.binding_id, item.required_input_artifact, item.input_status)
                    for item in items
                ],
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    return LaborEmploymentBudgetOutcomeReplayInputPackCase(
        input_pack_case_id=input_pack_case_id,
        binding_case_id=binding_case.binding_case_id,
        execution_case_id=binding_case.execution_case_id,
        learning_fixture_id=binding_case.learning_fixture_id,
        executable_fixture_id=binding_case.executable_fixture_id,
        outcome_seed_id=binding_case.outcome_seed_id,
        family=binding_case.family,
        variant=binding_case.variant,
        status=status,
        expected_budget_output_state=binding_case.expected_budget_output_state,
        required_input_count=len(items),
        ready_input_count=len([item for item in items if item.input_status == "ready"]),
        missing_input_count=missing,
        invalid_input_count=invalid,
        one_of_signal_missing_count=len(
            [
                item
                for item in items
                if item.input_role == "one_of_signal" and item.input_status == "missing"
            ]
        ),
        items=items,
        evidence_refs=[binding_case.binding_case_id, *binding_case.evidence_refs],
        failure_ids=failures,
    )


def _items_for_binding(
    *,
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    repo_root: Path,
    expected_family: str,
    expected_source_bundle_refs: dict[str, str],
) -> list[LaborEmploymentBudgetOutcomeReplayInputPackItem]:
    return [
        _input_item(
            binding=binding,
            required_input_artifact=artifact,
            entries=entries,
            repo_root=repo_root,
            expected_family=expected_family,
            expected_source_bundle_ref=expected_source_bundle_refs.get(
                binding.executable_fixture_id
            ),
        )
        for artifact in binding.required_input_artifacts
    ]


def _input_item(
    *,
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    required_input_artifact: str,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    repo_root: Path,
    expected_family: str,
    expected_source_bundle_ref: str | None,
) -> LaborEmploymentBudgetOutcomeReplayInputPackItem:
    role = _input_role(required_input_artifact)
    if required_input_artifact.startswith("one_or_more_of:"):
        return _one_of_input_item(
            binding=binding,
            required_input_artifact=required_input_artifact,
            entries=entries,
            repo_root=repo_root,
            expected_family=expected_family,
        )
    entry = _matching_entry(
        entries=entries,
        binding=binding,
        required_input_artifact=required_input_artifact,
    )
    if entry is None:
        return _missing_item(binding, required_input_artifact, role)
    status, message, model_name = _validate_entry(
        entry=entry,
        artifact_name=required_input_artifact,
        repo_root=repo_root,
        expected_family=expected_family,
        case_identity_context=_case_identity_context(
            entries=entries,
            repo_root=repo_root,
            learning_fixture_id=binding.learning_fixture_id,
        ),
        expected_source_bundle_ref=expected_source_bundle_ref,
    )
    anchor_source_hash = (
        _source_bundle_hash(entry, repo_root)
        if status == "ready" and required_input_artifact == "legal_budget_proposal.json"
        else None
    )
    return _item(
        binding=binding,
        required_input_artifact=required_input_artifact,
        input_role=role,
        input_status=status,
        input_ref=entry.input_ref,
        selected_alternative_artifacts=[],
        validation_model=model_name,
        validation_message=message,
        anchor_refs=[ref for ref in [entry.confirmation_ref, entry.source_bundle_ref] if ref],
        confirmation_ref=entry.confirmation_ref if anchor_source_hash else None,
        source_bundle_ref=entry.source_bundle_ref if anchor_source_hash else None,
        source_bundle_sha256=anchor_source_hash,
    )


def _one_of_input_item(
    *,
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    required_input_artifact: str,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    repo_root: Path,
    expected_family: str,
) -> LaborEmploymentBudgetOutcomeReplayInputPackItem:
    alternatives = _one_of_alternatives(required_input_artifact)
    candidate_entries = [
        entry
        for entry in entries
        if _same_slot(entry, binding) and entry.required_input_artifact in alternatives
    ]
    if not candidate_entries:
        return _missing_item(binding, required_input_artifact, "one_of_signal")

    invalid_messages = []
    for entry in candidate_entries:
        status, message, model_name = _validate_entry(
            entry=entry,
            artifact_name=entry.required_input_artifact,
            repo_root=repo_root,
            expected_family=expected_family,
            case_identity_context=_case_identity_context(
                entries=entries,
                repo_root=repo_root,
                learning_fixture_id=binding.learning_fixture_id,
            ),
        )
        if status == "ready":
            return _item(
                binding=binding,
                required_input_artifact=required_input_artifact,
                input_role="one_of_signal",
                input_status="ready",
                input_ref=entry.input_ref,
                selected_alternative_artifacts=[entry.required_input_artifact],
                validation_model=model_name,
                validation_message=(
                    "At least one reviewed learning signal validated: "
                    f"{entry.required_input_artifact}."
                ),
            )
        invalid_messages.append(f"{entry.required_input_artifact}: {message}")
    return _item(
        binding=binding,
        required_input_artifact=required_input_artifact,
        input_role="one_of_signal",
        input_status="invalid",
        input_ref=candidate_entries[0].input_ref,
        selected_alternative_artifacts=[],
        validation_model=None,
        validation_message="No one-of alternative validated; " + "; ".join(invalid_messages),
    )


def _missing_item(
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    required_input_artifact: str,
    input_role: str,
) -> LaborEmploymentBudgetOutcomeReplayInputPackItem:
    return _item(
        binding=binding,
        required_input_artifact=required_input_artifact,
        input_role=input_role,  # type: ignore[arg-type]
        input_status="missing",
        input_ref=None,
        selected_alternative_artifacts=[],
        validation_model=_model_name(required_input_artifact),
        validation_message="No local synthetic input ref is declared for this replay slot.",
    )


def _item(
    *,
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    required_input_artifact: str,
    input_role: str,
    input_status: str,
    input_ref: str | None,
    selected_alternative_artifacts: list[str],
    validation_model: str | None,
    validation_message: str,
    anchor_refs: list[str] | None = None,
    confirmation_ref: str | None = None,
    source_bundle_ref: str | None = None,
    source_bundle_sha256: str | None = None,
) -> LaborEmploymentBudgetOutcomeReplayInputPackItem:
    input_check_id = (
        "lebudgetreplayinput_"
        + digest_json(
            {
                "binding": binding.binding_id,
                "artifact": required_input_artifact,
                "status": input_status,
                "ref": input_ref,
            }
        )[len("sha256:") : len("sha256:") + 16]
    )
    labels = ["labor_employment_budget_replay_input_pack_candidate"]
    if input_status == "ready":
        labels.append("labor_employment_budget_replay_input_ready_candidate")
    elif input_status == "missing":
        labels.append("labor_employment_budget_replay_input_missing_candidate")
    else:
        labels.append("labor_employment_budget_replay_input_invalid_candidate")
    if input_role == "one_of_signal":
        labels.append("reviewed_learning_signal_input_candidate")
    return LaborEmploymentBudgetOutcomeReplayInputPackItem(
        input_check_id=input_check_id,
        binding_id=binding.binding_id,
        learning_fixture_id=binding.learning_fixture_id,
        executable_fixture_id=binding.executable_fixture_id,
        outcome_seed_id=binding.outcome_seed_id,
        loop_type=binding.loop_type,
        expected_artifact_name=binding.expected_artifact_name,
        required_input_artifact=required_input_artifact,
        input_role=input_role,  # type: ignore[arg-type]
        input_status=input_status,  # type: ignore[arg-type]
        input_ref=input_ref,
        selected_alternative_artifacts=selected_alternative_artifacts,
        validation_model=validation_model,
        validation_message=validation_message,
        confirmation_scope="synthetic_fixture_only" if source_bundle_sha256 else None,
        confirmation_ref=confirmation_ref,
        source_bundle_ref=source_bundle_ref,
        source_bundle_sha256=source_bundle_sha256,
        offset_encoding="unicode_codepoint_v1" if source_bundle_sha256 else None,
        candidate_exception_lake_labels=labels,
        evidence_refs=[
            binding.binding_id,
            binding.artifact_slot_ref,
            *binding.evidence_refs,
            *(anchor_refs or []),
        ],
    )


def _source_bundle_hash(
    entry: LaborEmploymentBudgetOutcomeReplayInputPackEntry,
    repo_root: Path,
) -> str | None:
    if not entry.source_bundle_ref:
        return None
    source_path = _resolve_local_ref(entry.source_bundle_ref, repo_root)
    if source_path is None or not source_path.is_file():
        return None
    try:
        return digest_json(load_json(source_path))
    except (OSError, ValueError):
        return None


def _matching_entry(
    *,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
    required_input_artifact: str,
) -> LaborEmploymentBudgetOutcomeReplayInputPackEntry | None:
    exact = [
        entry
        for entry in entries
        if _same_slot(entry, binding)
        and entry.expected_artifact_name == binding.expected_artifact_name
        and entry.required_input_artifact == required_input_artifact
    ]
    if exact:
        return exact[0]
    generic = [
        entry
        for entry in entries
        if _same_slot(entry, binding)
        and entry.expected_artifact_name is None
        and entry.required_input_artifact == required_input_artifact
    ]
    return generic[0] if generic else None


def _same_slot(
    entry: LaborEmploymentBudgetOutcomeReplayInputPackEntry,
    binding: LaborEmploymentBudgetOutcomeReplayBuilderBinding,
) -> bool:
    return (
        entry.learning_fixture_id == binding.learning_fixture_id
        and entry.loop_type == binding.loop_type
    )


def _validate_entry(
    *,
    entry: LaborEmploymentBudgetOutcomeReplayInputPackEntry,
    artifact_name: str,
    repo_root: Path,
    expected_family: str,
    case_identity_context: dict[str, set[str]],
    expected_source_bundle_ref: str | None = None,
) -> tuple[str, str, str | None]:
    model = ARTIFACT_MODELS.get(artifact_name)
    if model is None:
        return "invalid", f"No validation model is registered for {artifact_name}.", None
    target = _resolve_local_ref(entry.input_ref, repo_root)
    if target is None:
        return "invalid", "Input ref is not a local JSON file ref.", model.__name__
    if not target.exists() or not target.is_file():
        return "invalid", f"Input ref does not exist: {target}.", model.__name__
    try:
        payload = load_json(target)
        model.model_validate(payload)
    except (OSError, ValueError, ValidationError) as exc:
        return "invalid", f"{model.__name__} validation failed: {exc}", model.__name__
    family_errors = _case_family_errors(
        payload=payload,
        artifact_name=artifact_name,
        expected_family=expected_family,
    )
    if family_errors:
        return (
            "invalid",
            "Input artifact does not match expected L&E replay family: "
            + ", ".join(family_errors[:8]),
            model.__name__,
        )
    confirmation_errors = _budget_confirmation_anchor_errors(
        entry=entry,
        payload=payload,
        repo_root=repo_root,
        expected_family=expected_family,
        expected_source_bundle_ref=expected_source_bundle_ref,
    )
    if confirmation_errors:
        return (
            "invalid",
            "Budget proposal confirmation anchor failed: " + ", ".join(confirmation_errors[:8]),
            model.__name__,
        )
    identity_errors = _case_identity_errors(
        payload=payload,
        artifact_name=artifact_name,
        case_identity_context=case_identity_context,
    )
    if identity_errors:
        return (
            "invalid",
            "Input artifact does not match same-case identity anchors: "
            + ", ".join(identity_errors[:8]),
            model.__name__,
        )
    boundary_errors = _boundary_errors(payload)
    if boundary_errors:
        return (
            "invalid",
            "Input artifact violates candidate/no-write boundary: "
            + ", ".join(boundary_errors[:8]),
            model.__name__,
        )
    return "ready", f"{model.__name__} validated from local synthetic ref.", model.__name__


def _party_name_matches_segment_text(name: str, text: str) -> bool:
    normalized_name = unicodedata.normalize("NFC", name).strip().casefold()
    if not normalized_name:
        return False
    normalized_text = unicodedata.normalize("NFC", text).casefold()
    return re.search(rf"(?<!\w){re.escape(normalized_name)}(?!\w)", normalized_text) is not None


def _budget_confirmation_anchor_errors(
    *,
    entry: LaborEmploymentBudgetOutcomeReplayInputPackEntry,
    payload: Any,
    repo_root: Path,
    expected_family: str,
    expected_source_bundle_ref: str | None,
) -> list[str]:
    if entry.required_input_artifact != "legal_budget_proposal.json":
        return []
    if not isinstance(payload, dict):
        return ["budget proposal payload is not an object"]
    if not entry.confirmation_ref or not entry.source_bundle_ref:
        return ["confirmation or source-bundle ref missing"]
    if not expected_source_bundle_ref:
        return ["executable fixture has no governed source-bundle mapping"]

    confirmation_path = _resolve_local_ref(entry.confirmation_ref, repo_root)
    source_path = _resolve_local_ref(entry.source_bundle_ref, repo_root)
    expected_source_path = _resolve_local_ref(expected_source_bundle_ref, repo_root)
    if confirmation_path is None or source_path is None or expected_source_path is None:
        return ["confirmation and source-bundle refs must be local JSON refs"]
    if source_path != expected_source_path:
        return ["source_bundle_ref does not match executable fixture manifest"]
    if not confirmation_path.is_file() or not source_path.is_file():
        return ["confirmation or source-bundle ref does not exist"]

    try:
        confirmation_payload = load_json(confirmation_path)
        source_payload = load_json(source_path)
        confirmation = HumanConfirmation.model_validate(confirmation_payload)
        bundle = SourceBundle.model_validate(source_payload)
    except (OSError, ValueError, ValidationError) as exc:
        return [f"anchor validation failed: {exc}"]

    errors: list[str] = []
    if confirmation.status != "confirmed":
        errors.append(f"confirmation status={confirmation.status!r} is not confirmed")
    if confirmation.confirmation_id != payload.get("confirmation_id"):
        errors.append("confirmation_id does not match budget proposal")
    if confirmation.preflight_packet_id != payload.get("preflight_packet_id"):
        errors.append("preflight_packet_id does not match budget proposal")
    if confirmation.confirmed_matter_family != expected_family:
        errors.append("confirmed matter family does not match replay family")
    if confirmation.confirmed_matter_family != payload.get("matter_family"):
        errors.append("confirmed matter family does not match budget proposal")
    if confirmation.confirmed_representation_posture != payload.get("representation_posture"):
        errors.append("confirmed representation posture does not match budget proposal")
    if not confirmation.reviewer_id.startswith("synthetic-"):
        errors.append("POC confirmation reviewer must be explicitly synthetic")
    if not confirmation.decision_evidence_refs:
        errors.append("confirmation has no decision evidence refs")
    if not confirmation.confirmed_parties:
        errors.append("confirmation has no confirmed principal parties")
    if any(not party.evidence_refs for party in confirmation.confirmed_parties):
        errors.append("confirmed party is missing evidence refs")

    segments = segment_bundle(bundle)
    segments_by_signature = {
        (
            segment.source_id,
            segment.start_offset,
            segment.end_offset,
            segment.sha256,
        ): segment
        for segment in segments
    }
    all_refs = [
        *confirmation.decision_evidence_refs,
        *[ref for party in confirmation.confirmed_parties for ref in party.evidence_refs],
    ]
    for ref in all_refs:
        signature = (ref.source_id, ref.start_offset, ref.end_offset, ref.sha256)
        if signature not in segments_by_signature:
            errors.append(
                "evidence ref does not match source ID, Unicode-codepoint offsets, and hash"
            )

    for party in confirmation.confirmed_parties:
        if not party.name.strip():
            errors.append("confirmed party name is empty")
            continue
        supporting_segments = [
            segments_by_signature.get((ref.source_id, ref.start_offset, ref.end_offset, ref.sha256))
            for ref in party.evidence_refs
        ]
        if not any(
            segment and _party_name_matches_segment_text(party.name, segment.text)
            for segment in supporting_segments
        ):
            errors.append(f"party {party.name!r} is not named in its evidence segment")

    errors.extend(_boundary_errors(source_payload, "$.source_bundle"))
    errors.extend(_boundary_errors(confirmation_payload, "$.confirmation"))
    return errors


def _case_identity_context(
    *,
    entries: list[LaborEmploymentBudgetOutcomeReplayInputPackEntry],
    repo_root: Path,
    learning_fixture_id: str,
) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {
        field: set() for field in (*CASE_IDENTITY_FIELDS, SOURCE_CASE_TOKEN_CONTEXT_KEY)
    }
    for entry in entries:
        if (
            entry.learning_fixture_id != learning_fixture_id
            or entry.required_input_artifact not in CASE_IDENTITY_ANCHOR_ARTIFACTS
        ):
            continue
        target = _resolve_local_ref(entry.input_ref, repo_root)
        if target is None or not target.exists() or not target.is_file():
            continue
        try:
            payload = load_json(target)
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        for field in CASE_IDENTITY_FIELDS:
            value = payload.get(field)
            if _is_concrete_case_identity_value(value):
                values[field].add(value)
        if entry.required_input_artifact == "legal_budget_proposal.json":
            values[SOURCE_CASE_TOKEN_CONTEXT_KEY].update(_case_tokens_from_budget_payload(payload))
    return values


def _case_family_errors(
    *,
    payload: Any,
    artifact_name: str,
    expected_family: str,
) -> list[str]:
    if artifact_name not in FAMILY_BOUND_ARTIFACTS:
        return []
    if not isinstance(payload, dict):
        return ["family-bound artifact payload is not an object"]
    actual = payload.get("matter_family")
    if actual != expected_family:
        return [f"matter_family={actual!r} expected {expected_family!r}"]
    return []


def _is_concrete_case_identity_value(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("__")
        and not value.startswith("filled-by-test-")
    )


def _case_tokens_from_budget_payload(payload: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for field, prefix in (
        ("budget_proposal_id", "le-budget-"),
        ("preflight_packet_id", "le-preflight-"),
    ):
        value = payload.get(field)
        if not _is_concrete_case_identity_value(value):
            continue
        token = value.removeprefix(prefix).split(".", 1)[0]
        if token:
            tokens.add(token)
    return tokens


def _extract_source_case_token(field: str, value: str) -> str | None:
    patterns = {
        "actuals_source_id": r"^le-actuals-(?P<token>.+?)\.v\d+_\d+$",
        "source_ref": r"^synthetic-actuals://labor-employment/(?P<token>[^/]+)/v\d+_\d+$",
        "bundle_id": r"^le-carrier-rejection-(?P<token>.+?)(?:-appeal)?\.v\d+_\d+$",
        "run_id": r"^le-carrier-rejection-run-(?P<token>.+?)(?:-appeal)?\.v\d+_\d+$",
    }
    pattern = patterns.get(field)
    if pattern is None:
        return None
    match = re.match(pattern, value)
    return match.group("token") if match else None


def _raw_source_case_token_errors(
    *,
    payload: dict[str, Any],
    artifact_name: str,
    case_identity_context: dict[str, set[str]],
) -> list[str]:
    fields = RAW_SOURCE_CASE_TOKEN_FIELDS.get(artifact_name)
    if not fields:
        return []

    expected_tokens = case_identity_context.get(SOURCE_CASE_TOKEN_CONTEXT_KEY, set())
    if len(expected_tokens) > 1:
        return [f"source case token anchors conflict: {sorted(expected_tokens)}"]
    if not expected_tokens:
        return ["source case token anchor missing"]

    expected = next(iter(expected_tokens))
    observed_values = [
        (field, value)
        for field in fields
        if isinstance((value := payload.get(field)), str) and value
    ]
    if not observed_values:
        return [f"source case token={expected!r} not found in {list(fields)}"]
    observed_tokens = [
        (field, _extract_source_case_token(field, value)) for field, value in observed_values
    ]
    if any(token != expected for _, token in observed_tokens):
        return [
            f"source case token={expected!r} does not exactly match "
            f"observed tokens={observed_tokens!r} in {list(fields)}"
        ]
    return []


def _case_identity_errors(
    *,
    payload: Any,
    artifact_name: str,
    case_identity_context: dict[str, set[str]],
) -> list[str]:
    if (
        artifact_name not in CASE_BOUND_REPORT_ARTIFACTS
        and artifact_name not in RAW_SOURCE_CASE_IDENTITY_FIELDS
        and artifact_name not in RAW_SOURCE_CASE_TOKEN_FIELDS
    ):
        return []
    if not isinstance(payload, dict):
        return ["case-bound artifact payload is not an object"]

    errors: list[str] = []
    fields = RAW_SOURCE_CASE_IDENTITY_FIELDS.get(artifact_name, CASE_IDENTITY_FIELDS)
    for field in fields:
        expected_values = case_identity_context.get(field, set())
        actual = payload.get(field)
        if len(expected_values) > 1:
            errors.append(f"{field} anchors conflict: {sorted(expected_values)}")
        elif not expected_values:
            errors.append(f"{field} anchor missing")
        elif (
            artifact_name in RAW_SOURCE_CASE_IDENTITY_FIELDS
            and not _is_concrete_case_identity_value(actual)
        ):
            continue
        elif actual not in expected_values:
            expected = next(iter(expected_values))
            errors.append(f"{field}={actual!r} expected {expected!r}")
    errors.extend(
        _raw_source_case_token_errors(
            payload=payload,
            artifact_name=artifact_name,
            case_identity_context=case_identity_context,
        )
    )
    return errors


def _resolve_local_ref(input_ref: str, repo_root: Path) -> Path | None:
    path_part = input_ref.split("#", 1)[0]
    if path_part.startswith(("http://", "https://", "app://")):
        return None
    candidate = Path(path_part)
    if candidate.is_absolute():
        return None
    resolved_repo = repo_root.resolve()
    resolved = (resolved_repo / candidate).resolve()
    if resolved_repo not in [resolved, *resolved.parents]:
        return None
    return resolved


def _boundary_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in PROHIBITED_TRUE_FIELDS and item is True:
                errors.append(item_path)
            if key in PROHIBITED_REAL_DATA_FIELDS and item is True:
                errors.append(item_path)
            if key in PROHIBITED_FALSE_AUTHORITY_FIELDS and item is False:
                errors.append(item_path)
            if key == "data_origin" and item not in {"synthetic", None}:
                errors.append(item_path)
            errors.extend(_boundary_errors(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_boundary_errors(item, f"{path}[{index}]"))
    return errors


def _input_role(
    artifact_name: str,
) -> Literal["builder_input", "complement_report", "one_of_signal"]:
    if artifact_name.startswith("one_or_more_of:"):
        return "one_of_signal"
    if artifact_name.endswith(("_report.json", "_packet.json")):
        return "complement_report"
    return "builder_input"


def _one_of_alternatives(required_input_artifact: str) -> list[str]:
    return [
        item.strip()
        for item in required_input_artifact.removeprefix("one_or_more_of:").split(",")
        if item.strip()
    ]


def _model_name(required_input_artifact: str) -> str | None:
    if required_input_artifact.startswith("one_or_more_of:"):
        names = [
            ARTIFACT_MODELS[item].__name__
            for item in _one_of_alternatives(required_input_artifact)
            if item in ARTIFACT_MODELS
        ]
        return " | ".join(names) if names else None
    model = ARTIFACT_MODELS.get(required_input_artifact)
    return model.__name__ if model else None


def _checks(
    *,
    binding_report: LaborEmploymentBudgetOutcomeReplayBuilderBindingReport,
    manifest: LaborEmploymentBudgetOutcomeReplayInputPackManifest | None,
    cases: list[LaborEmploymentBudgetOutcomeReplayInputPackCase],
    executable_manifest_error: str | None,
    executable_manifest_ref: str | None,
) -> list[LaborEmploymentBudgetOutcomeReplayInputPackCheck]:
    invalid_items = [
        item for case in cases for item in case.items if item.input_status == "invalid"
    ]
    ready_blocked_guard_cases = [
        case
        for case in cases
        if case.expected_budget_output_state == "blocked_amount_budget" and case.status == "ready"
    ]
    manifest_claims_blocked_guard = bool(
        manifest and any(entry.loop_type == "blocked_budget_guard" for entry in manifest.entries)
    )
    return [
        LaborEmploymentBudgetOutcomeReplayInputPackCheck(
            check_id="source_builder_binding_report_ready",
            status=(
                "passed"
                if binding_report.status
                == "labor_employment_budget_replay_builder_binding_ready_for_review"
                else "failed"
            ),
            message="Source builder-binding report is ready for input-pack validation.",
            evidence_refs=[binding_report.builder_binding_report_id],
            blocking_refs=[]
            if binding_report.status.endswith("ready_for_review")
            else [binding_report.builder_binding_report_id],
        ),
        LaborEmploymentBudgetOutcomeReplayInputPackCheck(
            check_id="executable_fixture_source_map_is_governed",
            status="passed" if executable_manifest_error is None else "failed",
            message=(
                "Executable fixture manifest resolves exact source-bundle refs for replay cases."
                if executable_manifest_error is None
                else executable_manifest_error
            ),
            evidence_refs=[executable_manifest_ref] if executable_manifest_ref else [],
            blocking_refs=[executable_manifest_error] if executable_manifest_error else [],
        ),
        LaborEmploymentBudgetOutcomeReplayInputPackCheck(
            check_id="declared_input_refs_are_schema_valid",
            status="passed" if not invalid_items else "failed",
            message="Every declared local input ref validates against its expected artifact model.",
            evidence_refs=[item.input_check_id for item in invalid_items[:20]],
            blocking_refs=[
                item.input_ref or item.required_input_artifact for item in invalid_items
            ],
        ),
        LaborEmploymentBudgetOutcomeReplayInputPackCheck(
            check_id="blocked_budget_guard_lane_has_ready_inputs_when_claimed",
            status=(
                "passed"
                if not manifest_claims_blocked_guard or ready_blocked_guard_cases
                else "failed"
            ),
            message=(
                "Blocked-budget guard input refs resolve to existing synthetic QA artifacts "
                "when the manifest claims that lane."
            ),
            evidence_refs=[case.input_pack_case_id for case in ready_blocked_guard_cases],
            blocking_refs=[]
            if ready_blocked_guard_cases or not manifest_claims_blocked_guard
            else ["blocked_budget_guard"],
        ),
        LaborEmploymentBudgetOutcomeReplayInputPackCheck(
            check_id="input_pack_audit_preserves_no_write_boundary",
            status="passed",
            message="Input-pack audit writes only local candidate report files and performs no runtime actions.",
            evidence_refs=[case.input_pack_case_id for case in cases],
        ),
    ]


def _report_status(
    *,
    missing_input_count: int,
    invalid_input_count: int,
    failed_checks: list[LaborEmploymentBudgetOutcomeReplayInputPackCheck],
) -> Literal[
    "labor_employment_budget_replay_input_pack_ready_for_review",
    "labor_employment_budget_replay_input_pack_partially_ready_for_review",
    "blocked_by_labor_employment_budget_replay_input_pack",
]:
    if invalid_input_count or failed_checks:
        return "blocked_by_labor_employment_budget_replay_input_pack"
    if missing_input_count:
        return "labor_employment_budget_replay_input_pack_partially_ready_for_review"
    return "labor_employment_budget_replay_input_pack_ready_for_review"
