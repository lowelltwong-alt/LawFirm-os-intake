from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import build_model_adapter_report, resolve_adapter
from .budget import build_budget_proposal
from .budget_actuals import build_budget_actual_comparison_report
from .budget_submission_guard import (
    build_budget_submission_guard_report,
    enforce_budget_submission_guard_report,
)
from .confirmation import build_human_review_outcome_record
from .contract_state import build_contract_state_report, enforce_contract_state
from .context import build_effective_context, load_profile
from .context_boundary import build_context_boundary_report, enforce_context_boundary_report
from .data_scope import build_data_scope_gate_report, enforce_data_scope_gate_report
from .deadline_guard import (
    build_deadline_docketing_guard_report,
    enforce_deadline_docketing_guard_report,
)
from .drivers import load_driver_policy, resolve_case_drivers
from .evidence import build_preflight_graph, extend_graph_with_budget
from .evidence_completeness import (
    build_evidence_completeness_report,
    enforce_evidence_completeness_report,
)
from .exception_handoff import (
    build_exception_lake_handoff_manifest,
    enforce_exception_lake_handoff_manifest,
)
from .exception_mapping import (
    build_exception_lake_mapping_package,
    enforce_exception_lake_mapping_package,
)
from .exception_readiness import (
    build_exception_lake_readiness_report,
    enforce_exception_lake_readiness,
)
from .exceptions import (
    build_budget_exception_candidates,
    build_budget_precondition_exception_candidates,
    build_preflight_exception_candidates,
)
from .gold import build_fixture_gold_report, enforce_fixture_gold_report
from .human_gates import build_human_gate_status_report, enforce_human_gate_status_report
from .ingestion import build_ingestion_result
from .ingestion_volume import build_ingestion_volume_profile
from .models import (
    BudgetSubmissionGuardReport,
    ConflictSearchTerm,
    ConflictSeedPacket,
    ContractStateReport,
    ContextBoundaryReport,
    DataScopeGateReport,
    DeadlineDocketingGuardReport,
    EvidenceCompletenessReport,
    EvidenceRef,
    ExceptionLakeCandidate,
    FixtureGoldSpec,
    HumanConfirmation,
    IntakePreflightPacket,
    MatterOpeningBlocker,
    MatterOpeningReadiness,
    ModelAdapterReport,
    ProhibitedActionGuardrail,
    ReviewPackageManifest,
    RunEvent,
    SourceBundle,
)
from .package_completeness import (
    build_review_package_completeness_report,
    enforce_review_package_completeness,
)
from .preconditions import build_budget_precondition_report, enforce_budget_preconditions
from .review import (
    render_budget_review_form,
    render_intake_review_form,
    render_matter_opening_review_package,
)
from .run_ledger import build_run_ledger_integrity_report, enforce_run_ledger_integrity
from .rust_readiness import (
    build_rust_ingestion_readiness_report,
    enforce_rust_ingestion_readiness,
)
from .safety import build_safety_gate_report, enforce_safety_gate
from .util import append_jsonl, load_json, load_jsonl, new_id, now_iso, write_json
from .workers import (
    classify_matter,
    extract_deadlines_and_gaps,
    extract_parties,
    missing_information_candidates,
    review_evidence,
)


PROHIBITED_NEXT_STEPS = [
    "do_not_clear_conflicts",
    "do_not_accept_representation",
    "do_not_send_client_or_carrier_communications",
    "do_not_open_matter_or_imanage_workspace",
    "do_not_docket_deadlines",
    "do_not_submit_budget",
]

PREFLIGHT_REQUIRED_LEDGER_STEPS = [
    "run_started",
    "adapter_selected",
    "contract_state_gate",
    "data_origin_gate",
    "context_resolution",
    "python_reference_ingestion",
    "specialist_workers",
    "preflight_packet_built",
]

BUDGET_REQUIRED_LEDGER_STEPS = [
    "budget_run_started",
    "human_review_outcome_recorded",
    "budget_precondition_gate",
    "human_confirmation_consumed",
    "conflict_seed_and_budget_proposal_built",
]

BLOCKED_BUDGET_REQUIRED_LEDGER_STEPS = [
    "budget_run_started",
    "human_review_outcome_recorded",
    "budget_precondition_gate",
    "budget_generation_blocked",
]


def _gate_bundle(bundle: SourceBundle) -> None:
    enforce_data_scope_gate_report(build_data_scope_gate_report("data_scope_gate_check", bundle))


def _event(run_id: str, index: int, step: str, status: str, **kwargs: Any) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        step_index=index,
        step_name=step,
        status=status,
        timestamp=now_iso(),
        **kwargs,
    )


def _ledger_events(ledger_path: Path) -> list[RunEvent]:
    return [RunEvent.model_validate(event) for event in load_jsonl(ledger_path)]


def _latest_ledger_attempt(events: list[RunEvent], start_step: str) -> list[RunEvent]:
    for index in range(len(events) - 1, -1, -1):
        if events[index].step_name == start_step:
            return events[index:]
    return events


def _matter_opening_blocker_details() -> list[MatterOpeningBlocker]:
    return [
        MatterOpeningBlocker(
            blocker_code="conflicts_not_cleared",
            label="Conflicts clearance is not complete",
            blocking_scope="conflicts",
            required_human_gate="human_conflicts_clearance",
            authority_owner="conflicts_review",
            support_kind="structured_workflow_policy",
            structured_ref="workflow/intake-to-budget.workflow.yaml#conflicts_review",
            reason="The workflow may prepare search seeds only; conflicts clearance is a separate human authority.",
            prohibits=["conflicts_cleared"],
        ),
        MatterOpeningBlocker(
            blocker_code="engagement_not_authorized",
            label="Engagement authorization is not complete",
            blocking_scope="engagement",
            required_human_gate="human_engagement_authorization",
            authority_owner="engagement_and_matter_opening",
            support_kind="structured_workflow_policy",
            structured_ref=(
                "workflow/intake-to-budget.workflow.yaml#engagement_and_matter_opening"
            ),
            reason="The workflow does not accept representation or send engagement communications.",
            prohibits=["accept_representation", "send_engagement_letter"],
        ),
        MatterOpeningBlocker(
            blocker_code="matter_opening_not_approved",
            label="Matter opening approval is not complete",
            blocking_scope="matter_opening",
            required_human_gate="human_matter_opening_authorization",
            authority_owner="engagement_and_matter_opening",
            support_kind="structured_workflow_policy",
            structured_ref="workflow/intake-to-budget.workflow.yaml#matter_opening_readiness",
            reason="The workflow remains a readiness packet and cannot create a matter or workspace.",
            prohibits=["open_matter", "create_imanage_workspace"],
        ),
        MatterOpeningBlocker(
            blocker_code="budget_review_not_completed",
            label="Budget review is not complete",
            blocking_scope="budget_submission",
            required_human_gate="human_budget_review",
            authority_owner="human_budget_review",
            support_kind="budget_submission_boundary",
            structured_ref="workflow/intake-to-budget.workflow.yaml#human_budget_review",
            reason="The budget remains proposed for human review and is not authorized for client or carrier submission.",
            prohibits=["budget_submitted", "billing_handoff"],
        ),
    ]


def _prohibited_action_details() -> list[ProhibitedActionGuardrail]:
    return [
        ProhibitedActionGuardrail(
            action_code="do_not_open_imanage",
            transition_blocked="imanage_workspace_created",
            required_human_gate="human_matter_opening_authorization",
            support_kind="prohibited_transition_policy",
            structured_ref=(
                "workflow/prohibited-transitions.yaml#matter_opening_readiness"
                "->imanage_workspace_created"
            ),
            reason="Workspace creation is a prohibited transition from matter-opening readiness.",
            linked_blocker_codes=["matter_opening_not_approved"],
        ),
        ProhibitedActionGuardrail(
            action_code="do_not_create_matter",
            transition_blocked="matter_opened",
            required_human_gate="human_matter_opening_authorization",
            support_kind="prohibited_transition_policy",
            structured_ref="workflow/prohibited-transitions.yaml#raw_received->matter_opened",
            reason="Matter creation remains outside the starter workflow authority.",
            linked_blocker_codes=["matter_opening_not_approved"],
        ),
        ProhibitedActionGuardrail(
            action_code="do_not_submit_budget",
            transition_blocked="budget_submitted",
            required_human_gate="human_budget_review",
            support_kind="prohibited_transition_policy",
            structured_ref=(
                "workflow/prohibited-transitions.yaml#budget_proposal_ready->budget_submitted"
            ),
            reason="Budget submission is prohibited until a separate human budget-review authority approves it.",
            linked_blocker_codes=["budget_review_not_completed"],
        ),
    ]


def _validate_refs(packet: IntakePreflightPacket) -> None:
    segments_by_id = {segment.segment_id: segment for segment in packet.segments}

    def ensure_refs(label: str, refs: list) -> None:
        if not refs:
            raise ValueError(f"{label} lacks source-bound evidence references")
        for ref in refs:
            segment = segments_by_id.get(ref.segment_id)
            if segment is None:
                raise ValueError(f"{label} references unknown segment_id {ref.segment_id}")
            if ref.source_id != segment.source_id:
                raise ValueError(
                    f"{label} evidence ref source_id {ref.source_id} does not match "
                    f"segment {ref.segment_id}"
                )
            if ref.sha256 != segment.sha256:
                raise ValueError(
                    f"{label} evidence ref sha256 does not match segment {ref.segment_id}"
                )
            if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
                raise ValueError(
                    f"{label} evidence ref offsets do not match segment {ref.segment_id}"
                )

    for party in packet.party_candidates:
        ensure_refs(f"party candidate {party.name}", party.evidence_refs)
        for role in party.role_candidates:
            ensure_refs(f"role candidate {party.name}:{role.role}", role.evidence_refs)
    for candidate in (
        packet.inbound_event_candidates
        + packet.matter_family_candidates
        + packet.representation_posture_candidates
    ):
        ensure_refs(f"candidate {candidate.label}", candidate.observed_evidence_refs)
    for deadline in packet.deadline_candidates:
        ensure_refs(f"deadline candidate {deadline.expression}", deadline.evidence_refs)
    for missing in packet.missing_information_candidates:
        ensure_refs(f"missing information candidate {missing.field_name}", missing.evidence_refs)
    for finding in packet.critic_findings:
        ensure_refs(f"critic finding {finding.code}", finding.evidence_refs)


def run_preflight(
    input_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path,
    *,
    adapter: str = "deterministic",
    strict_evidence: bool = True,
    fixture_gold: str | Path | None = None,
) -> tuple[IntakePreflightPacket, Path]:
    run_id = new_id("run")
    run_dir = Path(out_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    ledger_path = run_dir / "run_ledger.jsonl"

    append_jsonl(ledger_path, _event(run_id, 0, "run_started", "started").model_dump(mode="json"))
    adapter_decision = resolve_adapter(adapter)
    model_adapter_report_path = run_dir / "model_adapter_report.json"
    model_adapter_report = build_model_adapter_report(run_id, adapter_decision)
    write_json(model_adapter_report_path, model_adapter_report.model_dump(mode="json"))
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            1,
            "adapter_selected",
            "completed",
            output_refs=[str(model_adapter_report_path)],
            notes=adapter_decision.notes,
        ).model_dump(mode="json"),
    )
    contract_state_report_path = run_dir / "contract_state_report.json"
    data_scope_gate_report_path = run_dir / "data_scope_gate_report.json"
    contract_state_report = build_contract_state_report(run_id)
    write_json(contract_state_report_path, contract_state_report.model_dump(mode="json"))
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            2,
            "contract_state_gate",
            "completed" if contract_state_report.status == "passed" else "failed",
            output_refs=[str(contract_state_report_path)],
        ).model_dump(mode="json"),
    )
    enforce_contract_state(contract_state_report)

    bundle = SourceBundle.model_validate(load_json(input_path))
    data_scope_gate_report = build_data_scope_gate_report(run_id, bundle)
    write_json(data_scope_gate_report_path, data_scope_gate_report.model_dump(mode="json"))
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            3,
            "data_origin_gate",
            "completed" if data_scope_gate_report.status == "passed" else "blocked",
            input_refs=[str(input_path)],
            output_refs=[str(data_scope_gate_report_path)],
            notes=data_scope_gate_report.blocked_state,
        ).model_dump(mode="json"),
    )
    enforce_data_scope_gate_report(data_scope_gate_report)
    write_json(run_dir / "raw_input.json", bundle.model_dump(mode="json"))

    profile = load_profile(profile_path)
    context = build_effective_context(profile)
    write_json(run_dir / "effective_context.json", context.model_dump(mode="json"))
    append_jsonl(
        ledger_path, _event(run_id, 4, "context_resolution", "completed").model_dump(mode="json")
    )

    ingestion_result = build_ingestion_result(bundle)
    ingestion_result_path = run_dir / "ingestion_result.json"
    ingestion_volume_profile_path = run_dir / "ingestion_volume_profile.json"
    rust_ingestion_readiness_report_path = run_dir / "rust_ingestion_readiness_report.json"
    write_json(ingestion_result_path, ingestion_result.model_dump(mode="json"))
    ingestion_volume_profile = build_ingestion_volume_profile(
        run_id=run_id,
        ingestion_result=ingestion_result,
    )
    write_json(ingestion_volume_profile_path, ingestion_volume_profile.model_dump(mode="json"))
    segments = ingestion_result.segments
    inventory = ingestion_result.source_inventory
    write_json(run_dir / "segments.json", [s.model_dump(mode="json") for s in segments])
    rust_ingestion_readiness_report = build_rust_ingestion_readiness_report(
        run_id=run_id,
        bundle=bundle,
        ingestion_result=ingestion_result,
    )
    write_json(
        rust_ingestion_readiness_report_path,
        rust_ingestion_readiness_report.model_dump(mode="json"),
    )
    enforce_rust_ingestion_readiness(rust_ingestion_readiness_report)
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            5,
            "python_reference_ingestion",
            "completed",
            output_refs=[
                str(ingestion_result_path),
                str(ingestion_volume_profile_path),
                str(rust_ingestion_readiness_report_path),
                str(run_dir / "segments.json"),
            ],
            notes=(
                "Rust-ready ingestion parity oracle and readiness report; no Rust runtime selected."
            ),
        ).model_dump(mode="json"),
    )

    parties = extract_parties(bundle, segments)
    inbound, matter, posture = classify_matter(bundle, segments, context)
    deadlines, missing = extract_deadlines_and_gaps(bundle, segments, context)
    missing_candidates = missing_information_candidates(missing, segments)
    findings, escalation = review_evidence(parties, matter, deadlines, missing, segments)
    append_jsonl(
        ledger_path, _event(run_id, 6, "specialist_workers", "completed").model_dump(mode="json")
    )

    review_form_path = run_dir / "intake_review_form.md"
    exception_candidates_path = run_dir / "exception_lake_candidates.jsonl"
    exception_readiness_report_path = run_dir / "exception_lake_readiness_report.json"
    exception_handoff_manifest_path = run_dir / "exception_lake_handoff_manifest.json"
    run_ledger_integrity_report_path = run_dir / "run_ledger_integrity_report.json"
    deadline_docketing_guard_report_path = run_dir / "deadline_docketing_guard_report.json"
    evidence_completeness_report_path = run_dir / "evidence_completeness_report.json"
    context_boundary_report_path = run_dir / "context_boundary_report.json"
    fixture_gold_report_path = run_dir / "fixture_gold_report.json" if fixture_gold else None
    packet = IntakePreflightPacket(
        packet_id=new_id("intake"),
        run_id=run_id,
        bundle_id=bundle.bundle_id,
        status="human_intake_review_required",
        data_origin=bundle.data_origin,
        source_inventory=inventory,
        source_coverage_summary=ingestion_result.source_coverage_summary,
        segments=segments,
        ingestion_result_ref=str(ingestion_result_path),
        rust_ingestion_readiness_report_ref=str(rust_ingestion_readiness_report_path),
        ingestion_volume_profile_ref=str(ingestion_volume_profile_path),
        effective_context=context,
        inbound_event_candidates=inbound,
        matter_family_candidates=matter,
        representation_posture_candidates=posture,
        party_candidates=parties,
        deadline_candidates=deadlines,
        missing_information=missing,
        missing_information_candidates=missing_candidates,
        critic_findings=findings,
        escalation=escalation,
        prohibited_next_steps=PROHIBITED_NEXT_STEPS,
        evidence_graph_ref=str(run_dir / "evidence_graph.json"),
        run_ledger_ref=str(ledger_path),
        contract_state_report_ref=str(contract_state_report_path),
        data_scope_gate_report_ref=str(data_scope_gate_report_path),
        model_adapter_report_ref=str(model_adapter_report_path),
        fixture_gold_report_ref=str(fixture_gold_report_path) if fixture_gold_report_path else None,
        exception_candidates_ref=str(exception_candidates_path),
        exception_lake_readiness_report_ref=str(exception_readiness_report_path),
        exception_lake_handoff_manifest_ref=str(exception_handoff_manifest_path),
        run_ledger_integrity_report_ref=str(run_ledger_integrity_report_path),
        deadline_docketing_guard_report_ref=str(deadline_docketing_guard_report_path),
        evidence_completeness_report_ref=str(evidence_completeness_report_path),
        context_boundary_report_ref=str(context_boundary_report_path),
        intake_review_form_ref=str(review_form_path),
    )
    context_boundary_report = build_context_boundary_report(packet)
    write_json(
        context_boundary_report_path,
        context_boundary_report.model_dump(mode="json"),
    )
    enforce_context_boundary_report(context_boundary_report)
    evidence_completeness_report = build_evidence_completeness_report(
        packet,
        strict_evidence_required=strict_evidence,
    )
    write_json(
        evidence_completeness_report_path,
        evidence_completeness_report.model_dump(mode="json"),
    )
    if strict_evidence:
        enforce_evidence_completeness_report(evidence_completeness_report)
        _validate_refs(packet)
    deadline_docketing_guard_report = build_deadline_docketing_guard_report(packet)
    enforce_deadline_docketing_guard_report(deadline_docketing_guard_report)
    write_json(
        deadline_docketing_guard_report_path,
        deadline_docketing_guard_report.model_dump(mode="json"),
    )
    graph = build_preflight_graph(packet)
    exception_candidates = build_preflight_exception_candidates(packet)
    exception_candidates_path.touch()
    for candidate in exception_candidates:
        append_jsonl(exception_candidates_path, candidate.model_dump(mode="json"))
    exception_readiness_report = build_exception_lake_readiness_report(
        packet,
        exception_candidates,
        [str(exception_candidates_path)],
    )
    enforce_exception_lake_readiness(exception_readiness_report)
    write_json(
        exception_readiness_report_path,
        exception_readiness_report.model_dump(mode="json"),
    )
    exception_handoff_manifest = build_exception_lake_handoff_manifest(
        packet=packet,
        candidates=exception_candidates,
        candidate_file_refs=[str(exception_candidates_path)],
        readiness_report=exception_readiness_report,
        readiness_report_ref=str(exception_readiness_report_path),
        stage="preflight",
    )
    enforce_exception_lake_handoff_manifest(exception_handoff_manifest)
    write_json(
        exception_handoff_manifest_path,
        exception_handoff_manifest.model_dump(mode="json"),
    )
    write_json(
        run_dir / "source_inventory.json",
        [item.model_dump(mode="json") for item in packet.source_inventory],
    )
    write_json(run_dir / "intake_preflight_packet.json", packet.model_dump(mode="json"))
    write_json(run_dir / "evidence_graph.json", graph.model_dump(mode="json"))
    review_form_path.write_text(render_intake_review_form(packet), encoding="utf-8")
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            7,
            "preflight_packet_built",
            "completed",
            output_refs=[
                str(run_dir / "intake_preflight_packet.json"),
                str(review_form_path),
                str(run_dir / "evidence_graph.json"),
                str(contract_state_report_path),
                str(data_scope_gate_report_path),
                str(model_adapter_report_path),
                str(exception_candidates_path),
                str(ingestion_result_path),
                str(ingestion_volume_profile_path),
                str(rust_ingestion_readiness_report_path),
                str(deadline_docketing_guard_report_path),
                str(exception_readiness_report_path),
                str(exception_handoff_manifest_path),
                str(evidence_completeness_report_path),
                str(context_boundary_report_path),
            ],
        ).model_dump(mode="json"),
    )
    if fixture_gold and fixture_gold_report_path:
        gold = FixtureGoldSpec.model_validate(load_json(fixture_gold))
        gold_report = build_fixture_gold_report(
            gold=gold,
            gold_ref=str(fixture_gold),
            packet=packet,
            stage="preflight",
            evaluated_artifact_refs={
                "preflight_packet": str(run_dir / "intake_preflight_packet.json"),
                "preflight_exception_candidates": str(exception_candidates_path),
                "preflight_exception_lake_readiness_report": str(exception_readiness_report_path),
                "preflight_exception_lake_handoff_manifest": str(exception_handoff_manifest_path),
            },
            preflight_exception_candidates=[
                candidate.model_dump(mode="json") for candidate in exception_candidates
            ],
        )
        write_json(fixture_gold_report_path, gold_report.model_dump(mode="json"))
        append_jsonl(
            ledger_path,
            _event(
                run_id,
                8,
                "fixture_gold_evaluated",
                "completed" if gold_report.status == "passed" else "failed",
                input_refs=[str(fixture_gold)],
                output_refs=[str(fixture_gold_report_path)],
            ).model_dump(mode="json"),
        )
        enforce_fixture_gold_report(gold_report)
    preflight_required_steps = list(PREFLIGHT_REQUIRED_LEDGER_STEPS)
    preflight_terminal_step = "preflight_packet_built"
    if fixture_gold:
        preflight_required_steps.append("fixture_gold_evaluated")
        preflight_terminal_step = "fixture_gold_evaluated"
    run_ledger_integrity_report = build_run_ledger_integrity_report(
        run_id=run_id,
        stage="preflight",
        run_ledger_ref=str(ledger_path),
        events=_ledger_events(ledger_path),
        required_steps=preflight_required_steps,
        terminal_step_name=preflight_terminal_step,
        terminal_status="completed",
    )
    enforce_run_ledger_integrity(run_ledger_integrity_report)
    write_json(
        run_ledger_integrity_report_path,
        run_ledger_integrity_report.model_dump(mode="json"),
    )
    return packet, run_dir


def _dedup_evidence_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    dedup: dict[tuple[str, str, int, int, str], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.source_id, ref.segment_id, ref.start_offset, ref.end_offset, ref.sha256)] = ref
    return list(dedup.values())


def _party_term_map(
    confirmation: HumanConfirmation, roles: set[str]
) -> dict[str, list[EvidenceRef]]:
    terms: dict[str, list[EvidenceRef]] = {}
    for party in confirmation.confirmed_parties:
        if party.confirmed_role in roles:
            terms.setdefault(party.name, []).extend(party.evidence_refs)
    return {term: _dedup_evidence_refs(refs) for term, refs in terms.items()}


def _alias_term_map(confirmation: HumanConfirmation) -> dict[str, list[EvidenceRef]]:
    aliases: dict[str, list[EvidenceRef]] = {}
    for party in confirmation.confirmed_parties:
        for alias in party.aliases:
            aliases.setdefault(alias, []).extend(party.evidence_refs)
    return {term: _dedup_evidence_refs(refs) for term, refs in aliases.items()}


def _normalized_term(
    term: str,
    group: str,
    evidence_refs: list[EvidenceRef],
    source_role: str | None = None,
) -> ConflictSearchTerm:
    if not evidence_refs:
        raise ValueError(f"conflict search term {term} lacks source-bound evidence refs")
    normalized = " ".join(term.casefold().replace(",", " ").split())
    return ConflictSearchTerm(
        term=term,
        normalized_term=normalized,
        group=group,  # type: ignore[arg-type]
        source_role=source_role,
        evidence_refs=evidence_refs,
    )


def build_conflict_seed(
    packet: IntakePreflightPacket, confirmation: HumanConfirmation
) -> ConflictSeedPacket:
    represented = _party_term_map(
        confirmation, {"prospective_represented_client", "represented_client"}
    )
    instructing = _party_term_map(confirmation, {"instructing_source", "insurance_carrier"})
    payers = _party_term_map(confirmation, {"payer"})
    adverse = _party_term_map(confirmation, {"adverse_party", "claimant"})
    insureds = _party_term_map(confirmation, {"insured"})
    opposing = _party_term_map(confirmation, {"opposing_counsel"})
    all_names = {
        party.name: _dedup_evidence_refs(party.evidence_refs)
        for party in confirmation.confirmed_parties
    }
    classified = set().union(represented, instructing, payers, insureds, adverse, opposing)
    unresolved = {term: refs for term, refs in all_names.items() if term not in classified}
    aliases = _alias_term_map(confirmation)
    normalized_terms = []
    for group, terms in [
        ("prospective_represented_client", represented),
        ("instructing_source", instructing),
        ("payer", payers),
        ("insured", insureds),
        ("adverse_party", adverse),
        ("opposing_counsel", opposing),
        ("alias", aliases),
        ("unresolved_role", unresolved),
    ]:
        normalized_terms.extend(
            _normalized_term(term, group, refs) for term, refs in sorted(terms.items())
        )
    return ConflictSeedPacket(
        conflict_seed_id=new_id("conflictseed"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status="seed_ready_for_conflicts_team",
        prospective_represented_clients=sorted(represented),
        instructing_sources=sorted(instructing),
        payers=sorted(payers),
        adverse_parties=sorted(adverse),
        insureds=sorted(insureds),
        opposing_counsel=sorted(opposing),
        other_search_terms=sorted(aliases),
        unresolved_roles=sorted(unresolved),
        normalized_search_terms=normalized_terms,
    )


def _find_driver_policy_path(profile_path: Path) -> Path | None:
    for parent in [profile_path.parent, *profile_path.parents]:
        candidate = parent / "config" / "budget-driver-policy.yaml"
        if candidate.is_file():
            return candidate
    repo_candidate = Path(__file__).resolve().parents[2] / "config" / "budget-driver-policy.yaml"
    if repo_candidate.is_file():
        return repo_candidate
    return None


def _resolve_demo_case_drivers(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    profile: dict[str, Any],
    profile_path: str | Path,
):
    """Resolve case drivers for the local demo, or None when no policy is discoverable."""

    if not confirmation.confirmed_matter_family:
        return None
    policy_path = _find_driver_policy_path(Path(profile_path))
    if policy_path is None:
        return None
    return resolve_case_drivers(packet, confirmation, profile, load_driver_policy(policy_path))


def run_budget(
    preflight_packet_path: str | Path,
    confirmation_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path,
    *,
    fixture_gold: str | Path | None = None,
) -> tuple[Any, Path]:
    preflight_packet_path = Path(preflight_packet_path)
    confirmation_path = Path(confirmation_path)
    packet = IntakePreflightPacket.model_validate(load_json(preflight_packet_path))
    confirmation = HumanConfirmation.model_validate(load_json(confirmation_path))
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = run_dir / "run_ledger.jsonl"
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            0,
            "budget_run_started",
            "started",
            input_refs=[str(preflight_packet_path), str(confirmation_path)],
        ).model_dump(mode="json"),
    )
    human_review_outcome = build_human_review_outcome_record(packet, confirmation)
    human_review_outcome_path = (
        run_dir / f"human_review_outcome.{confirmation.confirmation_id}.json"
    )
    human_confirmation_history_path = run_dir / "human_confirmation_history.jsonl"
    write_json(human_review_outcome_path, human_review_outcome.model_dump(mode="json"))
    append_jsonl(
        human_confirmation_history_path,
        human_review_outcome.model_dump(mode="json"),
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            1,
            "human_review_outcome_recorded",
            "completed",
            input_refs=[str(confirmation_path)],
            output_refs=[str(human_review_outcome_path), str(human_confirmation_history_path)],
            notes=human_review_outcome.required_next_gate,
        ).model_dump(mode="json"),
    )
    budget_precondition_report_path = run_dir / "budget_precondition_report.json"
    budget_precondition_report = build_budget_precondition_report(
        packet,
        confirmation,
        [str(preflight_packet_path), str(confirmation_path), str(human_review_outcome_path)],
        str(human_review_outcome_path),
    )
    write_json(
        budget_precondition_report_path,
        budget_precondition_report.model_dump(mode="json"),
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            2,
            "budget_precondition_gate",
            "completed" if budget_precondition_report.status == "passed" else "blocked",
            output_refs=[str(budget_precondition_report_path)],
        ).model_dump(mode="json"),
    )
    if budget_precondition_report.status == "failed":
        exception_candidates_path = run_dir / "exception_lake_candidates.jsonl"
        exception_readiness_report_path = run_dir / "exception_lake_readiness_report.json"
        exception_handoff_manifest_path = run_dir / "exception_lake_handoff_manifest.json"
        run_ledger_integrity_report_path = run_dir / "run_ledger_integrity_report.json"
        exception_candidates_path.touch()
        exception_candidates = build_budget_precondition_exception_candidates(
            budget_precondition_report
        )
        for candidate in exception_candidates:
            append_jsonl(exception_candidates_path, candidate.model_dump(mode="json"))
        exception_readiness_report = build_exception_lake_readiness_report(
            packet,
            exception_candidates,
            [str(exception_candidates_path)],
        )
        enforce_exception_lake_readiness(exception_readiness_report)
        write_json(
            exception_readiness_report_path,
            exception_readiness_report.model_dump(mode="json"),
        )
        exception_handoff_manifest = build_exception_lake_handoff_manifest(
            packet=packet,
            candidates=exception_candidates,
            candidate_file_refs=[str(exception_candidates_path)],
            readiness_report=exception_readiness_report,
            readiness_report_ref=str(exception_readiness_report_path),
            stage="budget_precondition_blocked",
        )
        enforce_exception_lake_handoff_manifest(exception_handoff_manifest)
        write_json(
            exception_handoff_manifest_path,
            exception_handoff_manifest.model_dump(mode="json"),
        )
        append_jsonl(
            ledger_path,
            _event(
                packet.run_id,
                3,
                "budget_generation_blocked",
                "blocked",
                output_refs=[
                    str(budget_precondition_report_path),
                    str(exception_candidates_path),
                    str(exception_readiness_report_path),
                    str(exception_handoff_manifest_path),
                ],
                notes=budget_precondition_report.blocked_state,
            ).model_dump(mode="json"),
        )
        run_ledger_integrity_report = build_run_ledger_integrity_report(
            run_id=packet.run_id,
            stage="budget_precondition_blocked",
            run_ledger_ref=str(ledger_path),
            events=_latest_ledger_attempt(_ledger_events(ledger_path), "budget_run_started"),
            required_steps=BLOCKED_BUDGET_REQUIRED_LEDGER_STEPS,
            terminal_step_name="budget_generation_blocked",
            terminal_status="blocked",
        )
        enforce_run_ledger_integrity(run_ledger_integrity_report)
        write_json(
            run_ledger_integrity_report_path,
            run_ledger_integrity_report.model_dump(mode="json"),
        )
        enforce_budget_preconditions(budget_precondition_report)

    enforce_budget_preconditions(budget_precondition_report)
    profile = load_profile(profile_path)
    case_drivers = _resolve_demo_case_drivers(packet, confirmation, profile, profile_path)

    conflict_seed = build_conflict_seed(packet, confirmation)
    budget = build_budget_proposal(packet, confirmation, profile, case_drivers=case_drivers)
    readiness = MatterOpeningReadiness(
        readiness_id=new_id("readiness"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status="blocked_pending_conflicts_and_engagement",
        satisfied=[
            "human_intake_classification_confirmed",
            "conflict_search_seed_prepared",
            "budget_proposal_prepared",
        ],
        blockers=[
            "conflicts_not_cleared",
            "engagement_not_authorized",
            "matter_opening_not_approved",
        ],
        blocker_details=_matter_opening_blocker_details(),
        prohibited_actions=["do_not_open_imanage", "do_not_create_matter", "do_not_submit_budget"],
        prohibited_action_details=_prohibited_action_details(),
    )

    graph_path = Path(packet.evidence_graph_ref)
    graph = (
        load_json(graph_path)
        if graph_path.exists()
        else {"schema_version": "0.1", "graph_id": new_id("graph"), "nodes": [], "edges": []}
    )
    from .models import EvidenceGraph

    graph_model = EvidenceGraph.model_validate(graph)
    extended = extend_graph_with_budget(
        graph_model,
        confirmation,
        human_review_outcome,
        conflict_seed,
        budget,
        readiness,
    )

    write_json(run_dir / "human_confirmation.json", confirmation.model_dump(mode="json"))
    write_json(run_dir / "conflict_search_seed_packet.json", conflict_seed.model_dump(mode="json"))
    write_json(run_dir / "case_driver_profile.json", case_drivers.model_dump(mode="json"))
    write_json(run_dir / "legal_budget_proposal.json", budget.model_dump(mode="json"))
    (run_dir / "legal_budget_review_form.md").write_text(
        render_budget_review_form(budget), encoding="utf-8"
    )
    write_json(run_dir / "matter_opening_readiness.json", readiness.model_dump(mode="json"))
    write_json(run_dir / "evidence_graph.json", extended.model_dump(mode="json"))
    exception_candidates_path = run_dir / "exception_lake_candidates.jsonl"
    exception_candidates_path.touch()
    for candidate in build_budget_exception_candidates(
        packet.run_id,
        readiness,
        confirmation.decision_evidence_refs,
        budget,
    ):
        append_jsonl(exception_candidates_path, candidate.model_dump(mode="json"))

    preflight_exception_candidates = (
        load_jsonl(packet.exception_candidates_ref) if packet.exception_candidates_ref else []
    )
    budget_exception_candidates = load_jsonl(exception_candidates_path)
    all_exception_candidates = preflight_exception_candidates + budget_exception_candidates
    review_package_path = run_dir / "matter_opening_review_package.md"
    manifest_path = run_dir / "review_package_manifest.json"
    human_gate_status_report_path = run_dir / "human_gate_status_report.json"
    budget_submission_guard_report_path = run_dir / "budget_submission_guard_report.json"
    safety_gate_report_path = run_dir / "safety_gate_report.json"
    exception_readiness_report_path = run_dir / "exception_lake_readiness_report.json"
    exception_handoff_manifest_path = run_dir / "exception_lake_handoff_manifest.json"
    exception_mapping_package_path = run_dir / "exception_lake_mapping_package.json"
    actual_comparison_report_path = run_dir / "budget_actual_comparison_report.json"
    run_ledger_integrity_report_path = run_dir / "run_ledger_integrity_report.json"
    completeness_report_path = run_dir / "review_package_completeness_report.json"
    fixture_gold_report_path = run_dir / "fixture_gold_report.json" if fixture_gold else None
    preflight_dir = preflight_packet_path.parent
    artifact_refs = {
        "preflight_packet": str(preflight_packet_path),
        "data_scope_gate_report": packet.data_scope_gate_report_ref or "",
        "preflight_source_inventory": str(preflight_dir / "source_inventory.json"),
        "preflight_segments": str(preflight_dir / "segments.json"),
        "preflight_ingestion_result": packet.ingestion_result_ref or "",
        "preflight_ingestion_volume_profile": packet.ingestion_volume_profile_ref or "",
        "preflight_rust_ingestion_readiness_report": (
            packet.rust_ingestion_readiness_report_ref or ""
        ),
        "preflight_model_adapter_report": packet.model_adapter_report_ref or "",
        "preflight_intake_review_form": packet.intake_review_form_ref or "",
        "preflight_deadline_docketing_guard_report": (
            packet.deadline_docketing_guard_report_ref or ""
        ),
        "preflight_evidence_completeness_report": (packet.evidence_completeness_report_ref or ""),
        "preflight_context_boundary_report": (packet.context_boundary_report_ref or ""),
        "human_confirmation": str(run_dir / "human_confirmation.json"),
        "conflict_search_seed": str(run_dir / "conflict_search_seed_packet.json"),
        "case_driver_profile": str(run_dir / "case_driver_profile.json"),
        "legal_budget_proposal": str(run_dir / "legal_budget_proposal.json"),
        "legal_budget_review_form": str(run_dir / "legal_budget_review_form.md"),
        "matter_opening_readiness": str(run_dir / "matter_opening_readiness.json"),
        "budget_evidence_graph": str(run_dir / "evidence_graph.json"),
        "preflight_evidence_graph": packet.evidence_graph_ref,
        "preflight_exception_candidates": packet.exception_candidates_ref or "",
        "preflight_exception_lake_readiness_report": (
            packet.exception_lake_readiness_report_ref or ""
        ),
        "preflight_exception_lake_handoff_manifest": (
            packet.exception_lake_handoff_manifest_ref or ""
        ),
        "preflight_run_ledger_integrity_report": (packet.run_ledger_integrity_report_ref or ""),
        "budget_exception_candidates": str(exception_candidates_path),
        "budget_exception_lake_readiness_report": str(exception_readiness_report_path),
        "budget_exception_lake_handoff_manifest": str(exception_handoff_manifest_path),
        "budget_exception_lake_mapping_package": str(exception_mapping_package_path),
        "budget_actual_comparison_report": str(actual_comparison_report_path),
        "budget_run_ledger_integrity_report": str(run_ledger_integrity_report_path),
        "budget_run_ledger": str(ledger_path),
        "preflight_run_ledger": packet.run_ledger_ref,
        "human_review_outcome": str(human_review_outcome_path),
        "human_confirmation_history": str(human_confirmation_history_path),
        "human_gate_status_report": str(human_gate_status_report_path),
        "budget_submission_guard_report": str(budget_submission_guard_report_path),
        "contract_state_report": packet.contract_state_report_ref,
        "budget_precondition_report": str(budget_precondition_report_path),
        "safety_gate_report": str(safety_gate_report_path),
        "matter_opening_review_package": str(review_package_path),
        "review_package_manifest": str(manifest_path),
        "review_package_completeness_report": str(completeness_report_path),
    }
    if fixture_gold_report_path:
        artifact_refs["fixture_gold_report"] = str(fixture_gold_report_path)
    human_gate_status_report = build_human_gate_status_report(
        packet=packet,
        confirmation=confirmation,
        human_review_outcome=human_review_outcome,
        conflict_seed=conflict_seed,
        budget=budget,
        readiness=readiness,
        artifact_refs=artifact_refs,
    )
    enforce_human_gate_status_report(human_gate_status_report)
    write_json(
        human_gate_status_report_path,
        human_gate_status_report.model_dump(mode="json"),
    )
    budget_submission_guard_report = build_budget_submission_guard_report(
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        budget=budget,
        readiness=readiness,
        human_gate_status_report=human_gate_status_report,
        artifact_refs=artifact_refs,
    )
    enforce_budget_submission_guard_report(budget_submission_guard_report)
    write_json(
        budget_submission_guard_report_path,
        budget_submission_guard_report.model_dump(mode="json"),
    )
    safety_report = build_safety_gate_report(
        packet,
        confirmation,
        conflict_seed,
        budget,
        readiness,
        artifact_refs,
    )
    enforce_safety_gate(safety_report)
    exception_readiness_report = build_exception_lake_readiness_report(
        packet,
        [
            ExceptionLakeCandidate.model_validate(candidate)
            for candidate in all_exception_candidates
        ],
        [ref for ref in [packet.exception_candidates_ref, str(exception_candidates_path)] if ref],
    )
    enforce_exception_lake_readiness(exception_readiness_report)
    write_json(safety_gate_report_path, safety_report.model_dump(mode="json"))
    write_json(
        exception_readiness_report_path,
        exception_readiness_report.model_dump(mode="json"),
    )
    exception_handoff_manifest = build_exception_lake_handoff_manifest(
        packet=packet,
        candidates=[
            ExceptionLakeCandidate.model_validate(candidate)
            for candidate in all_exception_candidates
        ],
        candidate_file_refs=[
            ref for ref in [packet.exception_candidates_ref, str(exception_candidates_path)] if ref
        ],
        readiness_report=exception_readiness_report,
        readiness_report_ref=str(exception_readiness_report_path),
        stage="budget_combined",
    )
    enforce_exception_lake_handoff_manifest(exception_handoff_manifest)
    write_json(
        exception_handoff_manifest_path,
        exception_handoff_manifest.model_dump(mode="json"),
    )
    exception_mapping_package = build_exception_lake_mapping_package(
        packet=packet,
        candidates=[
            ExceptionLakeCandidate.model_validate(candidate)
            for candidate in all_exception_candidates
        ],
    )
    enforce_exception_lake_mapping_package(exception_mapping_package)
    write_json(
        exception_mapping_package_path,
        exception_mapping_package.model_dump(mode="json"),
    )
    actual_comparison_report = build_budget_actual_comparison_report(
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        budget=budget,
    )
    write_json(
        actual_comparison_report_path,
        actual_comparison_report.model_dump(mode="json"),
    )
    contract_state_report = ContractStateReport.model_validate(
        load_json(packet.contract_state_report_ref)
    )
    data_scope_gate_report = (
        DataScopeGateReport.model_validate(load_json(packet.data_scope_gate_report_ref))
        if packet.data_scope_gate_report_ref
        else None
    )
    model_adapter_report = (
        ModelAdapterReport.model_validate(load_json(packet.model_adapter_report_ref))
        if packet.model_adapter_report_ref
        else None
    )
    deadline_docketing_guard_report = (
        DeadlineDocketingGuardReport.model_validate(
            load_json(packet.deadline_docketing_guard_report_ref)
        )
        if packet.deadline_docketing_guard_report_ref
        else None
    )
    evidence_completeness_report = (
        EvidenceCompletenessReport.model_validate(
            load_json(packet.evidence_completeness_report_ref)
        )
        if packet.evidence_completeness_report_ref
        else None
    )
    context_boundary_report = (
        ContextBoundaryReport.model_validate(load_json(packet.context_boundary_report_ref))
        if packet.context_boundary_report_ref
        else None
    )
    budget_submission_guard_report = BudgetSubmissionGuardReport.model_validate(
        load_json(budget_submission_guard_report_path)
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            3,
            "human_confirmation_consumed",
            "completed",
            input_refs=[str(confirmation_path)],
        ).model_dump(mode="json"),
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            4,
            "conflict_seed_and_budget_proposal_built",
            "completed",
            output_refs=[
                str(run_dir / "conflict_search_seed_packet.json"),
                str(run_dir / "legal_budget_proposal.json"),
                str(run_dir / "matter_opening_readiness.json"),
                str(human_gate_status_report_path),
                str(budget_submission_guard_report_path),
                str(exception_candidates_path),
                str(safety_gate_report_path),
                str(exception_readiness_report_path),
                str(exception_handoff_manifest_path),
                str(exception_mapping_package_path),
                str(actual_comparison_report_path),
            ],
        ).model_dump(mode="json"),
    )
    if fixture_gold and fixture_gold_report_path:
        gold = FixtureGoldSpec.model_validate(load_json(fixture_gold))
        gold_report = build_fixture_gold_report(
            gold=gold,
            gold_ref=str(fixture_gold),
            packet=packet,
            stage="demo",
            evaluated_artifact_refs=artifact_refs,
            preflight_exception_candidates=preflight_exception_candidates,
            confirmation=confirmation,
            conflict_seed=conflict_seed,
            budget=budget,
            readiness=readiness,
            budget_exception_candidates=budget_exception_candidates,
            budget_precondition_report=budget_precondition_report,
            safety_report=safety_report,
        )
        write_json(fixture_gold_report_path, gold_report.model_dump(mode="json"))
        append_jsonl(
            ledger_path,
            _event(
                packet.run_id,
                5,
                "fixture_gold_evaluated",
                "completed" if gold_report.status == "passed" else "failed",
                input_refs=[str(fixture_gold)],
                output_refs=[str(fixture_gold_report_path)],
            ).model_dump(mode="json"),
        )
        enforce_fixture_gold_report(gold_report)
    budget_required_steps = list(BUDGET_REQUIRED_LEDGER_STEPS)
    budget_terminal_step = "conflict_seed_and_budget_proposal_built"
    if fixture_gold:
        budget_required_steps.append("fixture_gold_evaluated")
        budget_terminal_step = "fixture_gold_evaluated"
    run_ledger_integrity_report = build_run_ledger_integrity_report(
        run_id=packet.run_id,
        stage="budget_success",
        run_ledger_ref=str(ledger_path),
        events=_latest_ledger_attempt(_ledger_events(ledger_path), "budget_run_started"),
        required_steps=budget_required_steps,
        terminal_step_name=budget_terminal_step,
        terminal_status="completed",
    )
    enforce_run_ledger_integrity(run_ledger_integrity_report)
    write_json(
        run_ledger_integrity_report_path,
        run_ledger_integrity_report.model_dump(mode="json"),
    )
    review_package_path.write_text(
        render_matter_opening_review_package(
            packet,
            confirmation,
            conflict_seed,
            budget,
            readiness,
            safety_report,
            all_exception_candidates,
            artifact_refs,
            run_ledger_events={
                "preflight": load_jsonl(packet.run_ledger_ref),
                "budget": load_jsonl(ledger_path),
            },
            run_ledger_integrity_reports=[
                load_json(packet.run_ledger_integrity_report_ref)
                if packet.run_ledger_integrity_report_ref
                else None,
                run_ledger_integrity_report.model_dump(mode="json"),
            ],
            evidence_graph=extended,
            exception_readiness_report=exception_readiness_report,
            exception_handoff_manifest=exception_handoff_manifest,
            contract_state_report=contract_state_report,
            data_scope_gate_report=data_scope_gate_report,
            model_adapter_report=model_adapter_report,
            human_review_outcome=human_review_outcome,
            human_gate_status_report=human_gate_status_report,
            deadline_docketing_guard_report=deadline_docketing_guard_report,
            evidence_completeness_report=evidence_completeness_report,
            context_boundary_report=context_boundary_report,
            budget_submission_guard_report=budget_submission_guard_report,
            budget_precondition_report=budget_precondition_report,
        ),
        encoding="utf-8",
    )
    manifest = ReviewPackageManifest(
        review_package_id=new_id("reviewpkg"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        conflict_seed_id=conflict_seed.conflict_seed_id,
        budget_proposal_id=budget.budget_proposal_id,
        readiness_id=readiness.readiness_id,
        status=readiness.status,
        human_readable_review_ref=str(review_package_path),
        artifact_refs=artifact_refs,
        required_human_gates=[
            "human_intake_confirmation",
            "human_conflicts_clearance",
            "human_engagement_authorization",
            "human_budget_review",
            "human_matter_opening_authorization",
        ],
        human_gate_status_report_ref=str(human_gate_status_report_path),
        final_blockers=readiness.blockers,
        prohibited_actions=readiness.prohibited_actions,
        safety_gate_report_ref=str(safety_gate_report_path),
        contract_state_report_ref=packet.contract_state_report_ref,
        data_scope_gate_report_ref=packet.data_scope_gate_report_ref,
        budget_precondition_report_ref=str(budget_precondition_report_path),
        evidence_completeness_report_ref=packet.evidence_completeness_report_ref,
        context_boundary_report_ref=packet.context_boundary_report_ref,
        evidence_graph_ref=str(run_dir / "evidence_graph.json"),
        run_ledger_refs=[packet.run_ledger_ref, str(ledger_path)],
        run_ledger_integrity_report_refs=[
            ref
            for ref in [
                packet.run_ledger_integrity_report_ref,
                str(run_ledger_integrity_report_path),
            ]
            if ref
        ],
        exception_candidate_refs=[
            ref for ref in [packet.exception_candidates_ref, str(exception_candidates_path)] if ref
        ],
        exception_lake_readiness_report_ref=str(exception_readiness_report_path),
        exception_lake_handoff_manifest_ref=str(exception_handoff_manifest_path),
        review_package_completeness_report_ref=str(completeness_report_path),
        budget_submission_guard_report_ref=str(budget_submission_guard_report_path),
    )
    write_json(manifest_path, manifest.model_dump(mode="json"))
    completeness_report = build_review_package_completeness_report(
        manifest=manifest,
        review_package_path=review_package_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )
    write_json(completeness_report_path, completeness_report.model_dump(mode="json"))
    enforce_review_package_completeness(completeness_report)
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            6 if fixture_gold_report_path else 5,
            "matter_opening_review_package_built",
            "completed",
            output_refs=[
                str(review_package_path),
                str(manifest_path),
                str(completeness_report_path),
            ],
        ).model_dump(mode="json"),
    )
    return budget, run_dir
