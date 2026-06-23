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

    for node_type, relationship, candidates in [
        (
            "inbound_event_candidate",
            "supports_inbound_event_candidate",
            packet.inbound_event_candidates,
        ),
        ("matter_family_candidate", "supports_matter_candidate", packet.matter_family_candidates),
        (
            "representation_posture_candidate",
            "supports_representation_posture_candidate",
            packet.representation_posture_candidates,
        ),
    ]:
        for candidate in candidates:
            nodes.append(
                EvidenceGraphNode(
                    node_id=candidate.candidate_id,
                    node_type=node_type,
                    status="candidate",
                    attributes={
                        "label": candidate.label,
                        "confidence": candidate.confidence,
                        "calibration_label": candidate.calibration_label,
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
