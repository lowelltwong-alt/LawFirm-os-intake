from __future__ import annotations

from .models import (
    BudgetProposal,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    HumanConfirmation,
    IntakePreflightPacket,
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
                node_id=source["source_id"],
                node_type="source",
                status="source_evidence",
                attributes={
                    "source_type": source["source_type"],
                    "filename": source.get("filename"),
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

    for candidate in packet.matter_family_candidates:
        nodes.append(
            EvidenceGraphNode(
                node_id=candidate.candidate_id,
                node_type="matter_family_candidate",
                status="candidate",
                attributes={"label": candidate.label, "confidence": candidate.confidence},
            )
        )
        for ref in candidate.observed_evidence_refs:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=new_id("edge"),
                    source_node_id=ref.segment_id,
                    relationship="supports_matter_candidate",
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

    return EvidenceGraph(graph_id=new_id("graph"), nodes=nodes, edges=edges)


def extend_graph_with_budget(
    graph: EvidenceGraph,
    confirmation: HumanConfirmation,
    budget: BudgetProposal,
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
    return EvidenceGraph(
        schema_version=graph.schema_version, graph_id=graph.graph_id, nodes=nodes, edges=edges
    )
