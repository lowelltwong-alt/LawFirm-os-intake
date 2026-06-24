from __future__ import annotations

from .models import (
    BudgetProposal,
    ConflictSeedPacket,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
    MatterOpeningReadiness,
)
from .util import new_id


def build_preflight_graph(packet: IntakePreflightPacket) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []

    nodes.append(
        EvidenceGraphNode(
            node_id=packet.packet_id, node_type="intake_preflight_packet", status="runtime_evidence"
        )
    )
    for source in packet.source_inventory:
        nodes.append(
            EvidenceGraphNode(
                node_id=source.source_id,
                node_type="source",
                status="source_evidence",
                attributes={
                    "source_type": source.source_type,
                    "filename": source.filename,
                    "read_state": source.read_state,
                    "availability_state": source.availability_state,
                    "source_sha256": source.source_sha256,
                },
            )
        )
    for segment in packet.segments:
        nodes.append(
            EvidenceGraphNode(
                node_id=segment.segment_id,
                node_type="segment",
                status="source_evidence",
                attributes={
                    "source_id": segment.source_id,
                    "segment_type": segment.segment_type,
                    "sha256": segment.sha256,
                    "start_offset": segment.start_offset,
                    "end_offset": segment.end_offset,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=segment.source_id,
                relationship="contains",
                target_node_id=segment.segment_id,
                status="observed",
            )
        )

    for party in packet.party_candidates:
        nodes.append(
            EvidenceGraphNode(
                node_id=party.party_candidate_id,
                node_type="party_candidate",
                status="candidate",
                attributes={"name": party.name},
            )
        )
        for ref in party.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_party_candidate",
                    target_node_id=party.party_candidate_id,
                    evidence_refs=[ref],
                )
            )
        for index, role in enumerate(party.role_candidates):
            role_node_id = f"{party.party_candidate_id}:role:{index}"
            nodes.append(
                EvidenceGraphNode(
                    node_id=role_node_id,
                    node_type="party_role_candidate",
                    status="candidate",
                    attributes={
                        "party_candidate_id": party.party_candidate_id,
                        "party_name": party.name,
                        "role": role.role,
                        "confidence": role.confidence,
                    },
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=party.party_candidate_id,
                    relationship="has_role_candidate",
                    target_node_id=role_node_id,
                    status="candidate",
                )
            )
            for ref in role.evidence_refs:
                edges.append(
                    EvidenceGraphEdge(
                        edge_id=new_id("edge"),
                        source_node_id=ref.segment_id,
                        relationship="supports_party_role_candidate",
                        target_node_id=role_node_id,
                        evidence_refs=[ref],
                    )
                )

    for node_type, support_relationship, anchor_relationship, candidates in [
        (
            "inbound_event_candidate",
            "supports_inbound_event_candidate",
            "anchors_inbound_event_candidate",
            packet.inbound_event_candidates,
        ),
        (
            "matter_family_candidate",
            "supports_matter_candidate",
            "anchors_matter_family_candidate",
            packet.matter_family_candidates,
        ),
        (
            "representation_posture_candidate",
            "supports_representation_posture_candidate",
            "anchors_representation_posture_candidate",
            packet.representation_posture_candidates,
        ),
    ]:
        for candidate in candidates:
            relationship = (
                support_relationship
                if candidate.source_evidence_status == "observed_support"
                else anchor_relationship
            )
            nodes.append(
                EvidenceGraphNode(
                    node_id=candidate.candidate_id,
                    node_type=node_type,
                    status="candidate",
                    attributes={
                        "label": candidate.label,
                        "confidence": candidate.confidence,
                        "calibration_label": candidate.calibration_label,
                        "source_evidence_status": candidate.source_evidence_status,
                    },
                )
            )
            for ref in candidate.observed_evidence_refs:
                edges.append(
                    EvidenceGraphEdge(
                        edge_id=new_id("edge"),
                        source_node_id=ref.segment_id,
                        relationship=relationship,
                        target_node_id=candidate.candidate_id,
                        evidence_refs=[ref],
                    )
                )

    for deadline in packet.deadline_candidates:
        nodes.append(
            EvidenceGraphNode(
                node_id=deadline.deadline_candidate_id,
                node_type="deadline_candidate",
                status="candidate",
                attributes={"expression": deadline.expression},
            )
        )
        for ref in deadline.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_deadline_candidate",
                    target_node_id=deadline.deadline_candidate_id,
                    evidence_refs=[ref],
                )
            )

    for missing in packet.missing_information_candidates:
        node_id = f"missing:{missing.field_name}"
        nodes.append(
            EvidenceGraphNode(
                node_id=node_id,
                node_type="missing_information_candidate",
                status="candidate",
                attributes={"field_name": missing.field_name, "reason": missing.reason},
            )
        )
        for ref in missing.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_missing_information_candidate",
                    target_node_id=node_id,
                    evidence_refs=[ref],
                )
            )

    for finding in packet.critic_findings:
        node_id = f"critic:{finding.code}"
        nodes.append(
            EvidenceGraphNode(
                node_id=node_id,
                node_type="critic_finding",
                status=finding.severity,
                attributes={"code": finding.code, "message": finding.message},
            )
        )
        for ref in finding.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_critic_finding",
                    target_node_id=node_id,
                    evidence_refs=[ref],
                )
            )

    return EvidenceGraph(graph_id=new_id("graph"), nodes=nodes, edges=edges)


def extend_graph_with_budget(
    graph: EvidenceGraph,
    confirmation: HumanConfirmation,
    human_review_outcome: HumanReviewOutcomeRecord,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
) -> EvidenceGraph:
    nodes = list(graph.nodes)
    edges = list(graph.edges)
    nodes.append(
        EvidenceGraphNode(
            node_id=confirmation.confirmation_id,
            node_type="human_confirmation",
            status=confirmation.status,
        )
    )
    for ref in confirmation.decision_evidence_refs:
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=ref.segment_id,
                relationship="supports_human_confirmation",
                target_node_id=confirmation.confirmation_id,
                evidence_refs=[ref],
                status="human_confirmed",
            )
        )
    nodes.append(
        EvidenceGraphNode(
            node_id=human_review_outcome.review_outcome_id,
            node_type="human_review_outcome",
            status=human_review_outcome.status,
            attributes={
                "confirmation_id": human_review_outcome.confirmation_id,
                "required_next_gate": human_review_outcome.required_next_gate,
                "budget_stage_allowed": human_review_outcome.budget_stage_allowed,
                "mutation_policy": human_review_outcome.mutation_policy,
            },
        )
    )
    edges.append(
        EvidenceGraphEdge(
            edge_id=new_id("edge"),
            source_node_id=confirmation.confirmation_id,
            relationship="recorded_as_human_review_outcome",
            target_node_id=human_review_outcome.review_outcome_id,
            status="runtime_evidence",
        )
    )
    nodes.append(
        EvidenceGraphNode(
            node_id=conflict_seed.conflict_seed_id,
            node_type="conflict_seed_packet",
            status=conflict_seed.status,
            attributes={"conclusion": conflict_seed.conclusion},
        )
    )
    edges.append(
        EvidenceGraphEdge(
            edge_id=new_id("edge"),
            source_node_id=confirmation.confirmation_id,
            relationship="supports_conflict_seed_generation",
            target_node_id=conflict_seed.conflict_seed_id,
            status="human_confirmed",
        )
    )
    for index, term in enumerate(conflict_seed.normalized_search_terms):
        term_node_id = f"{conflict_seed.conflict_seed_id}:term:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=term_node_id,
                node_type="conflict_search_term",
                status="seed_only",
                attributes={
                    "term": term.term,
                    "normalized_term": term.normalized_term,
                    "group": term.group,
                    "source_role": term.source_role,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=term_node_id,
                relationship="included_in_conflict_seed",
                target_node_id=conflict_seed.conflict_seed_id,
                status="seed_only",
            )
        )
        for ref in term.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_conflict_search_term",
                    target_node_id=term_node_id,
                    evidence_refs=[ref],
                    status="human_confirmed",
                )
            )
    nodes.append(
        EvidenceGraphNode(
            node_id=budget.budget_proposal_id, node_type="budget_proposal", status="proposal"
        )
    )
    edges.append(
        EvidenceGraphEdge(
            edge_id=new_id("edge"),
            source_node_id=confirmation.confirmation_id,
            relationship="authorizes_budget_proposal_generation",
            target_node_id=budget.budget_proposal_id,
            status="human_confirmed",
        )
    )
    for index, line in enumerate(budget.lines):
        line_node_id = f"{budget.budget_proposal_id}:line:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=line_node_id,
                node_type="budget_line",
                status="proposal",
                attributes={
                    "phase_id": line.phase_id,
                    "task_id": line.task_id,
                    "staffing_role": line.staffing_role,
                    "estimated_hours": line.estimated_hours,
                    "rate_source": line.rate_source,
                    "rate_is_synthetic": line.rate_is_synthetic,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=line_node_id,
                relationship="included_in_budget_proposal",
                target_node_id=budget.budget_proposal_id,
                status="proposal",
            )
        )
        for ref in line.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_budget_line",
                    target_node_id=line_node_id,
                    evidence_refs=[ref],
                )
            )
    for index, item in enumerate(budget.budget_support_items):
        support_node_id = f"{budget.budget_proposal_id}:support:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=support_node_id,
                node_type="budget_support_item",
                status="proposal_support",
                attributes={
                    "item_type": item.item_type,
                    "text": item.text,
                    "source_kind": item.source_kind,
                    "structured_ref": item.structured_ref,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=support_node_id,
                relationship="supports_budget_proposal",
                target_node_id=budget.budget_proposal_id,
                status="proposal_support",
            )
        )
        for ref in item.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_budget_support_item",
                    target_node_id=support_node_id,
                    evidence_refs=[ref],
                )
            )
        if item.structured_ref:
            nodes.append(
                EvidenceGraphNode(
                    node_id=item.structured_ref,
                    node_type="structured_ref",
                    status="structured_evidence",
                    attributes={"source_kind": item.source_kind},
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=item.structured_ref,
                    relationship="supports_budget_support_item",
                    target_node_id=support_node_id,
                    status="structured_evidence",
                )
            )
    nodes.append(
        EvidenceGraphNode(
            node_id=readiness.readiness_id,
            node_type="matter_opening_readiness",
            status=readiness.status,
            attributes={
                "preflight_packet_id": readiness.preflight_packet_id,
                "confirmation_id": readiness.confirmation_id,
            },
        )
    )
    edges.append(
        EvidenceGraphEdge(
            edge_id=new_id("edge"),
            source_node_id=budget.budget_proposal_id,
            relationship="precedes_matter_opening_readiness",
            target_node_id=readiness.readiness_id,
            status="blocked",
        )
    )
    for blocker in readiness.blocker_details:
        blocker_node_id = f"{readiness.readiness_id}:blocker:{blocker.blocker_code}"
        nodes.append(
            EvidenceGraphNode(
                node_id=blocker_node_id,
                node_type="matter_opening_blocker",
                status=blocker.status,
                attributes={
                    "blocker_code": blocker.blocker_code,
                    "blocking_scope": blocker.blocking_scope,
                    "required_human_gate": blocker.required_human_gate,
                    "authority_owner": blocker.authority_owner,
                    "support_kind": blocker.support_kind,
                    "structured_ref": blocker.structured_ref,
                    "prohibits": blocker.prohibits,
                },
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=blocker_node_id,
                relationship="blocks_matter_opening_readiness",
                target_node_id=readiness.readiness_id,
                status="blocking",
            )
        )
        if blocker.structured_ref:
            nodes.append(
                EvidenceGraphNode(
                    node_id=blocker.structured_ref,
                    node_type="structured_ref",
                    status="structured_evidence",
                    attributes={"source_kind": blocker.support_kind},
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=blocker.structured_ref,
                    relationship="supports_matter_opening_blocker",
                    target_node_id=blocker_node_id,
                    status="structured_evidence",
                )
            )
        for ref in blocker.evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_matter_opening_blocker",
                    target_node_id=blocker_node_id,
                    evidence_refs=[ref],
                )
            )
    for guardrail in readiness.prohibited_action_details:
        guardrail_node_id = f"{readiness.readiness_id}:prohibited:{guardrail.action_code}"
        nodes.append(
            EvidenceGraphNode(
                node_id=guardrail_node_id,
                node_type="prohibited_action_guardrail",
                status="prohibited",
                attributes={
                    "action_code": guardrail.action_code,
                    "transition_blocked": guardrail.transition_blocked,
                    "required_human_gate": guardrail.required_human_gate,
                    "support_kind": guardrail.support_kind,
                    "structured_ref": guardrail.structured_ref,
                    "linked_blocker_codes": guardrail.linked_blocker_codes,
                },
            )
        )
        nodes.append(
            EvidenceGraphNode(
                node_id=guardrail.structured_ref,
                node_type="structured_ref",
                status="structured_evidence",
                attributes={"source_kind": guardrail.support_kind},
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=guardrail.structured_ref,
                relationship="supports_prohibited_action_guardrail",
                target_node_id=guardrail_node_id,
                status="structured_evidence",
            )
        )
        edges.append(
            EvidenceGraphEdge(
                edge_id=new_id("edge"),
                source_node_id=guardrail_node_id,
                relationship="guards_matter_opening_readiness",
                target_node_id=readiness.readiness_id,
                status="prohibited",
            )
        )
    return EvidenceGraph(
        schema_version=graph.schema_version, graph_id=graph.graph_id, nodes=nodes, edges=edges
    )
