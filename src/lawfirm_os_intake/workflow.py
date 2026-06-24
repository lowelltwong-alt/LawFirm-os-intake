from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import resolve_adapter
from .budget import build_budget_proposal
from .confirmation import build_human_review_outcome_record
from .contract_state import build_contract_state_report, enforce_contract_state
from .context import build_effective_context, load_profile
from .evidence import build_preflight_graph, extend_graph_with_budget
from .exception_readiness import (
    build_exception_lake_readiness_report,
    enforce_exception_lake_readiness,
)
from .exceptions import (
    build_budget_exception_candidates,
    build_budget_precondition_exception_candidates,
    build_preflight_exception_candidates,
)
from .ingestion import build_ingestion_result
from .models import (
    ConflictSearchTerm,
    ConflictSeedPacket,
    EvidenceRef,
    ExceptionLakeCandidate,
    HumanConfirmation,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    ReviewPackageManifest,
    RunEvent,
    SourceBundle,
)
from .preconditions import build_budget_precondition_report, enforce_budget_preconditions
from .review import (
    render_budget_review_form,
    render_intake_review_form,
    render_matter_opening_review_package,
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


def _gate_bundle(bundle: SourceBundle) -> None:
    if bundle.data_origin != "synthetic":
        raise ValueError(
            "starter runtime is synthetic-only; public sources are planning/reference only"
        )
    if (
        bundle.contains_real_client_data
        or bundle.contains_real_matter_data
        or bundle.contains_privileged_data
    ):
        raise ValueError("real client, matter, or privileged data is prohibited")


def _event(run_id: str, index: int, step: str, status: str, **kwargs: Any) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        step_index=index,
        step_name=step,
        status=status,
        timestamp=now_iso(),
        **kwargs,
    )


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
) -> tuple[IntakePreflightPacket, Path]:
    run_id = new_id("run")
    run_dir = Path(out_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    ledger_path = run_dir / "run_ledger.jsonl"

    append_jsonl(ledger_path, _event(run_id, 0, "run_started", "started").model_dump(mode="json"))
    adapter_decision = resolve_adapter(adapter)
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            1,
            "adapter_selected",
            "completed",
            notes=adapter_decision.notes,
        ).model_dump(mode="json"),
    )
    contract_state_report_path = run_dir / "contract_state_report.json"
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
    _gate_bundle(bundle)
    write_json(run_dir / "raw_input.json", bundle.model_dump(mode="json"))
    append_jsonl(
        ledger_path, _event(run_id, 3, "data_origin_gate", "completed").model_dump(mode="json")
    )

    profile = load_profile(profile_path)
    context = build_effective_context(profile)
    write_json(run_dir / "effective_context.json", context.model_dump(mode="json"))
    append_jsonl(
        ledger_path, _event(run_id, 4, "context_resolution", "completed").model_dump(mode="json")
    )

    ingestion_result = build_ingestion_result(bundle)
    ingestion_result_path = run_dir / "ingestion_result.json"
    write_json(ingestion_result_path, ingestion_result.model_dump(mode="json"))
    segments = ingestion_result.segments
    inventory = ingestion_result.source_inventory
    write_json(run_dir / "segments.json", [s.model_dump(mode="json") for s in segments])
    append_jsonl(
        ledger_path,
        _event(
            run_id,
            5,
            "python_reference_ingestion",
            "completed",
            output_refs=[str(ingestion_result_path), str(run_dir / "segments.json")],
            notes="Rust-ready ingestion parity oracle; no Rust runtime selected.",
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
        exception_candidates_ref=str(exception_candidates_path),
        exception_lake_readiness_report_ref=str(exception_readiness_report_path),
        intake_review_form_ref=str(review_form_path),
    )
    if strict_evidence:
        _validate_refs(packet)
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
                str(exception_candidates_path),
                str(ingestion_result_path),
                str(exception_readiness_report_path),
            ],
        ).model_dump(mode="json"),
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


def run_budget(
    preflight_packet_path: str | Path,
    confirmation_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path,
) -> tuple[Any, Path]:
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
                ],
                notes=budget_precondition_report.blocked_state,
            ).model_dump(mode="json"),
        )
        enforce_budget_preconditions(budget_precondition_report)

    enforce_budget_preconditions(budget_precondition_report)
    profile = load_profile(profile_path)

    conflict_seed = build_conflict_seed(packet, confirmation)
    budget = build_budget_proposal(packet, confirmation, profile)
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
        prohibited_actions=["do_not_open_imanage", "do_not_create_matter", "do_not_submit_budget"],
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
    )

    write_json(run_dir / "human_confirmation.json", confirmation.model_dump(mode="json"))
    write_json(run_dir / "conflict_search_seed_packet.json", conflict_seed.model_dump(mode="json"))
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
    safety_gate_report_path = run_dir / "safety_gate_report.json"
    exception_readiness_report_path = run_dir / "exception_lake_readiness_report.json"
    artifact_refs = {
        "preflight_packet": str(preflight_packet_path),
        "human_confirmation": str(run_dir / "human_confirmation.json"),
        "conflict_search_seed": str(run_dir / "conflict_search_seed_packet.json"),
        "legal_budget_proposal": str(run_dir / "legal_budget_proposal.json"),
        "legal_budget_review_form": str(run_dir / "legal_budget_review_form.md"),
        "matter_opening_readiness": str(run_dir / "matter_opening_readiness.json"),
        "budget_evidence_graph": str(run_dir / "evidence_graph.json"),
        "preflight_evidence_graph": packet.evidence_graph_ref,
        "preflight_exception_candidates": packet.exception_candidates_ref or "",
        "preflight_exception_lake_readiness_report": (
            packet.exception_lake_readiness_report_ref or ""
        ),
        "budget_exception_candidates": str(exception_candidates_path),
        "budget_exception_lake_readiness_report": str(exception_readiness_report_path),
        "budget_run_ledger": str(ledger_path),
        "preflight_run_ledger": packet.run_ledger_ref,
        "human_review_outcome": str(human_review_outcome_path),
        "human_confirmation_history": str(human_confirmation_history_path),
        "contract_state_report": packet.contract_state_report_ref,
        "budget_precondition_report": str(budget_precondition_report_path),
        "safety_gate_report": str(safety_gate_report_path),
    }
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
        final_blockers=readiness.blockers,
        prohibited_actions=readiness.prohibited_actions,
        safety_gate_report_ref=str(safety_gate_report_path),
        contract_state_report_ref=packet.contract_state_report_ref,
        budget_precondition_report_ref=str(budget_precondition_report_path),
        evidence_graph_ref=str(run_dir / "evidence_graph.json"),
        run_ledger_refs=[packet.run_ledger_ref, str(ledger_path)],
        exception_candidate_refs=[
            ref for ref in [packet.exception_candidates_ref, str(exception_candidates_path)] if ref
        ],
        exception_lake_readiness_report_ref=str(exception_readiness_report_path),
    )
    write_json(manifest_path, manifest.model_dump(mode="json"))
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
                str(exception_candidates_path),
                str(safety_gate_report_path),
                str(exception_readiness_report_path),
            ],
        ).model_dump(mode="json"),
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            5,
            "matter_opening_review_package_built",
            "completed",
            output_refs=[str(review_package_path), str(manifest_path)],
        ).model_dump(mode="json"),
    )
    return budget, run_dir
