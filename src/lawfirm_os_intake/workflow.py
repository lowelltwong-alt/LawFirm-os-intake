from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import resolve_adapter
from .budget import build_budget_proposal
from .context import build_effective_context, load_profile
from .evidence import build_preflight_graph, extend_graph_with_budget
from .exceptions import build_budget_exception_candidates, build_preflight_exception_candidates
from .models import (
    ConflictSearchTerm,
    ConflictSeedPacket,
    HumanConfirmation,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    RunEvent,
    SourceBundle,
)
from .review import render_budget_review_form, render_intake_review_form
from .segmenter import segment_bundle
from .util import append_jsonl, load_json, new_id, now_iso, write_json
from .workers import (
    classify_matter,
    extract_deadlines_and_gaps,
    extract_parties,
    missing_information_candidates,
    review_evidence,
    source_inventory,
    source_coverage_summary,
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
    segment_ids = {segment.segment_id for segment in packet.segments}

    def ensure_refs(label: str, refs: list) -> None:
        if not refs:
            raise ValueError(f"{label} lacks source-bound evidence references")
        for ref in refs:
            if ref.segment_id not in segment_ids:
                raise ValueError(f"{label} references unknown segment_id {ref.segment_id}")

    for party in packet.party_candidates:
        ensure_refs(f"party candidate {party.name}", party.evidence_refs)
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
    bundle = SourceBundle.model_validate(load_json(input_path))
    _gate_bundle(bundle)
    write_json(run_dir / "raw_input.json", bundle.model_dump(mode="json"))
    append_jsonl(
        ledger_path, _event(run_id, 2, "data_origin_gate", "completed").model_dump(mode="json")
    )

    profile = load_profile(profile_path)
    context = build_effective_context(profile)
    write_json(run_dir / "effective_context.json", context.model_dump(mode="json"))
    append_jsonl(
        ledger_path, _event(run_id, 3, "context_resolution", "completed").model_dump(mode="json")
    )

    segments = segment_bundle(bundle)
    write_json(run_dir / "segments.json", [s.model_dump(mode="json") for s in segments])
    append_jsonl(
        ledger_path,
        _event(run_id, 4, "provenance_preserving_segmentation", "completed").model_dump(
            mode="json"
        ),
    )

    parties = extract_parties(bundle, segments)
    inbound, matter, posture = classify_matter(bundle, segments, context)
    deadlines, missing = extract_deadlines_and_gaps(bundle, segments, context)
    missing_candidates = missing_information_candidates(missing, segments)
    findings, escalation = review_evidence(parties, matter, deadlines, missing, segments)
    append_jsonl(
        ledger_path, _event(run_id, 5, "specialist_workers", "completed").model_dump(mode="json")
    )

    inventory = source_inventory(bundle, segments)
    review_form_path = run_dir / "intake_review_form.md"
    exception_candidates_path = run_dir / "exception_lake_candidates.jsonl"
    packet = IntakePreflightPacket(
        packet_id=new_id("intake"),
        run_id=run_id,
        bundle_id=bundle.bundle_id,
        status="human_intake_review_required",
        data_origin=bundle.data_origin,
        source_inventory=inventory,
        source_coverage_summary=source_coverage_summary(inventory),
        segments=segments,
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
        exception_candidates_ref=str(exception_candidates_path),
        intake_review_form_ref=str(review_form_path),
    )
    if strict_evidence:
        _validate_refs(packet)
    graph = build_preflight_graph(packet)
    exception_candidates = build_preflight_exception_candidates(packet)
    exception_candidates_path.touch()
    for candidate in exception_candidates:
        append_jsonl(exception_candidates_path, candidate.model_dump(mode="json"))
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
            6,
            "preflight_packet_built",
            "completed",
            output_refs=[
                str(run_dir / "intake_preflight_packet.json"),
                str(review_form_path),
                str(run_dir / "evidence_graph.json"),
                str(exception_candidates_path),
            ],
        ).model_dump(mode="json"),
    )
    return packet, run_dir


def _party_names(confirmation: HumanConfirmation, role: str) -> list[str]:
    return [p.name for p in confirmation.confirmed_parties if p.confirmed_role == role]


def _normalized_term(term: str, group: str, source_role: str | None = None) -> ConflictSearchTerm:
    normalized = " ".join(term.casefold().replace(",", " ").split())
    return ConflictSearchTerm(
        term=term,
        normalized_term=normalized,
        group=group,  # type: ignore[arg-type]
        source_role=source_role,
    )


def build_conflict_seed(
    packet: IntakePreflightPacket, confirmation: HumanConfirmation
) -> ConflictSeedPacket:
    represented = _party_names(confirmation, "prospective_represented_client") + _party_names(
        confirmation, "represented_client"
    )
    instructing = _party_names(confirmation, "instructing_source") + _party_names(
        confirmation, "insurance_carrier"
    )
    payers = _party_names(confirmation, "payer")
    adverse = _party_names(confirmation, "adverse_party") + _party_names(confirmation, "claimant")
    insureds = _party_names(confirmation, "insured")
    opposing = _party_names(confirmation, "opposing_counsel")
    all_names = {p.name for p in confirmation.confirmed_parties}
    classified = set(represented + instructing + payers + insureds + adverse + opposing)
    unresolved = sorted(all_names - classified)
    aliases = sorted({alias for p in confirmation.confirmed_parties for alias in p.aliases})
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
        normalized_terms.extend(_normalized_term(term, group) for term in sorted(set(terms)))
    return ConflictSeedPacket(
        conflict_seed_id=new_id("conflictseed"),
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status="seed_ready_for_conflicts_team",
        prospective_represented_clients=sorted(set(represented)),
        instructing_sources=sorted(set(instructing)),
        payers=sorted(set(payers)),
        adverse_parties=sorted(set(adverse)),
        insureds=sorted(set(insureds)),
        opposing_counsel=sorted(set(opposing)),
        other_search_terms=aliases,
        unresolved_roles=unresolved,
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
    if confirmation.preflight_packet_id != packet.packet_id:
        raise ValueError("confirmation does not match preflight packet")
    if confirmation.status != "confirmed":
        raise ValueError("confirmation status must be confirmed")

    profile = load_profile(profile_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = run_dir / "run_ledger.jsonl"

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
    extended = extend_graph_with_budget(graph_model, confirmation, budget)

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
    ):
        append_jsonl(exception_candidates_path, candidate.model_dump(mode="json"))
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            6,
            "human_confirmation_consumed",
            "completed",
            input_refs=[str(confirmation_path)],
        ).model_dump(mode="json"),
    )
    append_jsonl(
        ledger_path,
        _event(
            packet.run_id,
            7,
            "conflict_seed_and_budget_proposal_built",
            "completed",
            output_refs=[
                str(run_dir / "conflict_search_seed_packet.json"),
                str(run_dir / "legal_budget_proposal.json"),
                str(run_dir / "matter_opening_readiness.json"),
                str(exception_candidates_path),
            ],
        ).model_dump(mode="json"),
    )
    return budget, run_dir
