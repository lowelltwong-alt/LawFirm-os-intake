from __future__ import annotations

from typing import Any

from .models import (
    BudgetPreconditionReport,
    BudgetProposal,
    ConflictSeedPacket,
    ContractStateReport,
    EvidenceGraph,
    ExceptionLakeReadinessReport,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    SafetyGateReport,
)


def _candidate_lines(candidates: list, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for candidate in candidates[:limit]:
        refs = ", ".join(_ref_text(ref) for ref in candidate.observed_evidence_refs[:3])
        context = ", ".join(candidate.context_signal_refs)
        context_text = f"; context: {context}" if context else ""
        lines.append(
            f"- {candidate.label} ({candidate.confidence:.2f}; {candidate.calibration_label}) "
            f"evidence: {refs or 'none'}{context_text}"
        )
    return lines or ["- none"]


def render_intake_review_form(packet: IntakePreflightPacket) -> str:
    party_lines = []
    for party in packet.party_candidates:
        roles = ", ".join(
            f"{role.role} ({role.confidence:.2f}; evidence: "
            f"{', '.join(_ref_text(ref) for ref in role.evidence_refs[:2]) or 'none'})"
            for role in party.role_candidates
        )
        refs = ", ".join(_ref_text(ref) for ref in party.evidence_refs[:3])
        party_lines.append(f"- {party.name}: {roles}; evidence: {refs}")

    missing_lines = [
        f"- {item.field_name}: {item.reason}; evidence: {_refs_text(item.evidence_refs, limit=3)}"
        for item in packet.missing_information_candidates
    ] or ["- none"]
    deadline_lines = [
        f"- {item.expression}: {item.deadline_type_candidate}; "
        f"human verification required; evidence: {_refs_text(item.evidence_refs, limit=3)}"
        for item in packet.deadline_candidates
    ] or ["- none"]
    finding_lines = [
        f"- [{finding.severity}] {finding.code}: {finding.message}; "
        f"evidence: {_refs_text(finding.evidence_refs, limit=3)}"
        for finding in packet.critic_findings
    ] or ["- none"]

    return "\n".join(
        [
            "# Intake Review Form",
            "",
            f"**Preflight packet ID:** {packet.packet_id}",
            f"**Run ID:** {packet.run_id}",
            f"**Status:** {packet.status}",
            "",
            "## Source Coverage",
            "",
            *_source_inventory_lines(packet),
            "",
            f"Coverage complete: `{packet.source_coverage_summary.get('coverage_complete')}`",
            f"Missing sources: `{packet.source_coverage_summary.get('missing_sources')}`",
            f"Unread sources: `{packet.source_coverage_summary.get('unread_sources')}`",
            f"Unreadable sources: `{packet.source_coverage_summary.get('unreadable_sources')}`",
            f"Duplicate sources: `{packet.source_coverage_summary.get('duplicate_sources')}`",
            f"Attachment references: `{packet.source_coverage_summary.get('attachment_reference_count')}`",
            "",
            "## Candidate Review",
            "",
            "### Inbound Event",
            *_candidate_lines(packet.inbound_event_candidates),
            "",
            "### Matter Family",
            *_candidate_lines(packet.matter_family_candidates),
            "",
            "### Representation Posture",
            *_candidate_lines(packet.representation_posture_candidates),
            "",
            "### Parties And Roles",
            *party_lines,
            "",
            "### Deadlines",
            *deadline_lines,
            "",
            "### Missing Information",
            *missing_lines,
            "",
            "## Evidence Critic",
            "",
            *finding_lines,
            "",
            "## Reviewer Decision",
            "",
            "- [ ] Confirm",
            "- [ ] Correct",
            "- [ ] Unknown",
            "- [ ] Needs more information",
            "- [ ] Human-only",
            "- [ ] Declined or referred by authorized human",
            "",
            "## Review Outcome Handling",
            "",
            *_review_outcome_handling_lines(),
            "",
            "## Prohibited Next Steps",
            "",
            *(f"- {item}" for item in packet.prohibited_next_steps),
            "",
            "This form does not clear conflicts, accept representation, docket deadlines, open a matter, or authorize communications.",
            "",
        ]
    )


def render_budget_review_form(budget: BudgetProposal) -> str:
    report = budget.calculation_report
    lines = [
        "# Proposed Legal Budget Review Form",
        "",
        f"**Budget proposal ID:** {budget.budget_proposal_id}",
        f"**Matter family:** {budget.matter_family}",
        f"**Representation posture:** {budget.representation_posture}",
        f"**Pricing status:** {budget.pricing_status}",
        f"**Scenario:** {budget.scenario_name}",
        "",
        "## Calculation Report",
        "",
    ]
    if report:
        lines.extend(
            [
                f"- Total hours: {report.total_hours}",
                f"- Priced lines: {report.priced_line_count}",
                f"- Unpriced lines: {report.unpriced_line_count}",
                f"- Subtotal fees: {report.subtotal_fees}",
                f"- Subtotal expenses: {report.subtotal_expenses}",
                f"- Contingency percent: {report.contingency_percent}",
                f"- Total proposed budget: {report.total_proposed_budget}",
                f"- Rate sources: {', '.join(report.rate_sources) or 'none'}",
            ]
        )
    else:
        lines.append("- No calculation report was produced.")

    lines.extend(
        [
            "",
            "## Budget Lines",
            "",
            *_budget_line_lines(budget),
            "",
            "## Evidence-Bound Budget Supports",
            "",
            *_budget_support_lines(budget),
        ]
    )

    lines.extend(
        [
            "",
            "## Review Checks",
            "",
            "- [ ] Matter type and posture were human-confirmed.",
            "- [ ] Staffing assumptions are appropriate.",
            "- [ ] Rates are authorized or explicitly synthetic/hours-only.",
            "- [ ] Phase/task assumptions are clear.",
            "- [ ] Expenses are supported or visibly estimated.",
            "- [ ] Unknowns and exclusions are visible.",
            "- [ ] Conflicts and engagement remain separate blockers.",
            "",
            "## Submission Boundary",
            "",
            f"- Approval state: {budget.approval_state}",
            f"- Client/carrier submission authorized: {not budget.not_authorized_for_client_submission}",
            "- Human budget review remains required before any client or carrier delivery.",
            "- Conflicts clearance, engagement authorization, and matter-opening authorization remain separate blockers.",
            "",
            "The generated proposal is not authorized for client or carrier submission.",
            "",
        ]
    )
    return "\n".join(lines)


def _review_outcome_handling_lines() -> list[str]:
    return [
        "- confirmed -> budget_precondition_gate; budget stage may proceed only after exact packet binding and evidence checks.",
        "- needs_more_information -> collect_missing_information; blocks conflict seed, budget proposal, readiness, safety, and final package output.",
        "- unknown -> human_classification_correction; blocks budget-stage output until corrected or superseded.",
        "- human_only -> human_only_handling; blocks automated budget-stage output.",
        "- declined or declined_or_referred -> declined_or_referred_handoff; blocks budget-stage output.",
        "- corrections use append_or_supersede_only; prior review outcomes are not silently mutated.",
    ]


def _lines_or_none(lines: list[str]) -> list[str]:
    return lines or ["- none"]


def _source_inventory_lines(packet: IntakePreflightPacket) -> list[str]:
    lines = []
    for item in packet.source_inventory:
        filename = item.filename or "none"
        duplicate_of = item.duplicate_of_source_id or "none"
        attachments = ", ".join(item.attachment_refs) or "none"
        metadata_keys = ", ".join(item.metadata_keys) or "none"
        lines.append(
            f"- {item.source_id}: {item.source_type}; read_state={item.read_state}; "
            f"availability={item.availability_state}; chars={item.character_count}; "
            f"sha={item.source_sha256}; filename={filename}; "
            f"duplicate_of={duplicate_of}; attachments={attachments}; "
            f"metadata_keys={metadata_keys}"
        )
    return lines or ["- none"]


def _contract_state_lines(report: ContractStateReport | None) -> list[str]:
    if report is None:
        return ["- Contract state report: unavailable"]
    lines = [
        f"- Contract state status: {report.status}",
        f"- Lock status: {report.lock_status or 'unknown'}",
        f"- Reviewed lock required: {report.reviewed_lock_required}",
        f"- Lockfile ref: `{report.lockfile_ref}`",
        f"- Topology lock ref: `{report.topology_lock_ref}`",
        "- Contract dependencies:",
    ]
    for dependency in report.dependencies:
        sha = dependency.sha or "missing-sha"
        lines.append(
            f"- {dependency.repo}: status={dependency.status}; "
            f"plane={dependency.authority_plane}; sha={sha}; "
            f"topology_matches_lock={dependency.topology_matches_lock}"
        )
    lines.append("- Contract checks:")
    lines.extend(f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks)
    return lines


def _human_review_outcome_lines(outcome: HumanReviewOutcomeRecord | None) -> list[str]:
    if outcome is None:
        return ["- Human review outcome: unavailable"]
    return [
        f"- Human review outcome status: {outcome.status}",
        f"- Reviewer: {outcome.reviewer_id}",
        f"- Reviewed at: {outcome.reviewed_at}",
        f"- Matches preflight packet: {outcome.matches_preflight_packet}",
        f"- Budget stage allowed: {outcome.budget_stage_allowed}",
        f"- Required next gate: {outcome.required_next_gate}",
        f"- Mutation policy: {outcome.mutation_policy}",
        f"- Decision evidence refs: {len(outcome.decision_evidence_refs)}",
        f"- Confirmed party evidence refs: {len(outcome.confirmed_party_evidence_refs)}",
    ]


def _budget_precondition_lines(report: BudgetPreconditionReport | None) -> list[str]:
    if report is None:
        return ["- Budget precondition report: unavailable"]
    blocked_state = report.blocked_state or "none"
    prohibited_outputs = ", ".join(report.prohibited_outputs) or "none"
    lines = [
        f"- Budget precondition status: {report.status}",
        f"- Budget blocked state: {blocked_state}",
        f"- Human review outcome ref: `{report.human_review_outcome_ref or 'missing'}`",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Prohibited outputs before gate failure: {prohibited_outputs}",
        "- Budget precondition checks:",
    ]
    lines.extend(f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks)
    return lines


def _budget_support_lines(budget: BudgetProposal) -> list[str]:
    lines = []
    for item in budget.budget_support_items:
        refs = ", ".join(_ref_text(ref) for ref in item.evidence_refs)
        support = refs or item.structured_ref or "missing support"
        lines.append(f"- {item.item_type}: {item.text} ({item.source_kind}; {support})")
    return lines or ["- none"]


def _money(value: float | None, currency: str) -> str:
    return f"{value:.2f} {currency}" if value is not None else "not priced"


def _hours_text(minimum: float | None, estimate: float, maximum: float | None) -> str:
    if minimum is not None and maximum is not None:
        return f"{minimum:.1f}-{maximum:.1f} hrs (estimate {estimate:.1f})"
    return f"{estimate:.1f} hrs"


def _budget_calculation_lines(budget: BudgetProposal) -> list[str]:
    report = budget.calculation_report
    if report is None:
        return ["- No calculation report was produced."]
    return [
        f"- Mode: {report.mode}",
        f"- Line count: {report.line_count}",
        f"- Total hours: {report.total_hours}",
        f"- Priced lines: {report.priced_line_count}",
        f"- Unpriced lines: {report.unpriced_line_count}",
        f"- Subtotal fees: {_money(report.subtotal_fees, budget.currency)}",
        f"- Subtotal expenses: {_money(report.subtotal_expenses, budget.currency)}",
        f"- Contingency percent: {report.contingency_percent}",
        f"- Contingency amount: {_money(report.contingency_amount, budget.currency)}",
        f"- Total proposed budget: {_money(report.total_proposed_budget, budget.currency)}",
        f"- Rate sources: {', '.join(report.rate_sources) or 'none'}",
        f"- Deterministic calculation: {report.deterministic}",
    ]


def _budget_line_lines(budget: BudgetProposal) -> list[str]:
    lines = []
    for line in budget.lines:
        hours = _hours_text(
            line.estimated_hours_min,
            line.estimated_hours,
            line.estimated_hours_max,
        )
        rate = _money(line.hourly_rate, budget.currency) if line.hourly_rate else "absent"
        fees = _money(line.estimated_fees, budget.currency)
        expenses = _money(line.estimated_expenses, budget.currency)
        assumptions = "; ".join(line.assumptions) or "none"
        formula = f"; formula: {line.calculation_formula}" if line.calculation_formula else ""
        external_code = (
            f"; external code candidate: {line.external_code_candidate}"
            if line.external_code_candidate
            else ""
        )
        lines.append(
            f"- {line.phase_name} / {line.task_name} / {line.staffing_role}: "
            f"{hours}; rate: {rate}; rate source: {line.rate_source}; "
            f"synthetic rate: {line.rate_is_synthetic}; fees: {fees}; "
            f"expenses: {expenses}; assumptions: {assumptions}; "
            f"evidence: {_refs_text(line.evidence_refs, limit=3)}"
            f"{formula}{external_code}"
        )
    return lines or ["- none"]


def _refs_text(refs: list[Any], limit: int | None = None) -> str:
    selected = refs if limit is None else refs[:limit]
    return ", ".join(_ref_text(ref) for ref in selected) or "none"


def _ref_text(ref: Any) -> str:
    return f"{ref.source_id}/{ref.segment_id}[{ref.start_offset}:{ref.end_offset}] sha={ref.sha256}"


def _confirmed_party_lines(confirmation: HumanConfirmation) -> list[str]:
    return [
        f"- {party.confirmed_role}: {party.name}"
        + (f" (aliases: {', '.join(party.aliases)})" if party.aliases else "")
        + f"; evidence: {_refs_text(party.evidence_refs, limit=3)}"
        for party in confirmation.confirmed_parties
    ]


def _party_candidate_lines(packet: IntakePreflightPacket) -> list[str]:
    lines = []
    for party in packet.party_candidates:
        aliases = f" (aliases: {', '.join(party.aliases)})" if party.aliases else ""
        role_text = "; ".join(
            f"{role.role} ({role.confidence:.2f}; evidence: "
            f"{_refs_text(role.evidence_refs, limit=2)})"
            for role in party.role_candidates
        )
        lines.append(
            f"- {party.name}{aliases}: role candidates: {role_text or 'none'}; "
            f"party evidence: {_refs_text(party.evidence_refs, limit=3)}"
        )
    return lines or ["- none"]


def _conflict_seed_lines(conflict_seed: ConflictSeedPacket) -> list[str]:
    lines = []
    for term in conflict_seed.normalized_search_terms:
        refs = ", ".join(_ref_text(ref) for ref in term.evidence_refs)
        lines.append(
            f"- {term.group} seed: {term.term} "
            f"(normalized: {term.normalized_term}; evidence: {refs or 'none'})"
        )
    return lines


def _exception_lines(candidates: list[dict[str, Any]]) -> list[str]:
    lines = []
    for candidate in candidates:
        lines.append(
            "- "
            f"{candidate.get('canonical_lake_class')}: "
            f"{candidate.get('local_event_label')} - "
            f"{candidate.get('reason')}"
        )
    return lines


def _exception_readiness_lines(report: ExceptionLakeReadinessReport | None) -> list[str]:
    if report is None:
        return ["- Exception Lake readiness: unavailable"]
    lines = [
        f"- Readiness status: {report.status}",
        f"- Admission state: {report.admission_state}",
        f"- Target runtime repo: {report.target_runtime_repo}",
        f"- Candidate count: {report.candidate_count}",
        f"- Candidate files: {', '.join(report.candidate_file_refs) or 'none'}",
        "- Readiness checks:",
    ]
    lines.extend(
        f"- {check.status}: {check.check_id} - {check.message}; "
        f"candidate_ids={len(check.candidate_ids)}"
        for check in report.checks
    )
    return lines


def _exception_candidate_detail_lines(candidates: list[dict[str, Any]]) -> list[str]:
    lines = []
    for candidate in candidates:
        evidence_refs = [
            _dict_ref_text(ref)
            for ref in candidate.get("evidence_refs", [])
            if isinstance(ref, dict)
        ]
        source_refs = candidate.get("source_inventory_refs", [])
        structured_refs = candidate.get("structured_refs", [])
        lines.append(
            f"- {candidate.get('candidate_id')}: {candidate.get('local_event_label')}; "
            f"class={candidate.get('canonical_lake_class')}; "
            f"status={candidate.get('status')}; "
            f"raw_payload_included={candidate.get('raw_payload_included')}; "
            f"canonical_promotion_required={candidate.get('canonical_promotion_required')}; "
            f"target={candidate.get('target_runtime_repo')}; "
            f"blocked_state={candidate.get('blocked_state') or 'none'}; "
            f"source_refs={', '.join(source_refs) or 'none'}; "
            f"evidence={', '.join(evidence_refs) or 'none'}; "
            f"structured_refs={', '.join(structured_refs) or 'none'}"
        )
    return lines or ["- none"]


def _dict_ref_text(ref: dict[str, Any]) -> str:
    sha = ref.get("sha256") or "missing-sha"
    return (
        f"{ref.get('source_id')}/{ref.get('segment_id')}"
        f"[{ref.get('start_offset')}:{ref.get('end_offset')}] sha={sha}"
    )


def _safety_gate_lines(report: SafetyGateReport) -> list[str]:
    return [f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks]


def _run_ledger_lines(
    artifact_refs: dict[str, str],
    run_ledger_events: dict[str, list[dict[str, Any]]],
) -> list[str]:
    lines = []
    ledgers = [
        ("preflight", artifact_refs.get("preflight_run_ledger", "")),
        ("budget", artifact_refs.get("budget_run_ledger", "")),
    ]
    for label, path in ledgers:
        events = run_ledger_events.get(label, [])
        lines.append(f"- {label} ledger: `{path or 'missing'}`; events={len(events)}")
        for event in events:
            notes = f"; notes={event['notes']}" if event.get("notes") else ""
            lines.append(
                f"- {label} step {event.get('step_index')}: {event.get('step_name')} "
                f"({event.get('status')}); inputs={len(event.get('input_refs') or [])}; "
                f"outputs={len(event.get('output_refs') or [])}{notes}"
            )
    return lines or ["- none"]


def _sorted_counts(values: list[str]) -> str:
    counts = {value: values.count(value) for value in sorted(set(values))}
    return ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"


def _evidence_graph_lines(
    artifact_refs: dict[str, str],
    evidence_graph: EvidenceGraph | None,
) -> list[str]:
    lines = [
        f"- Preflight graph: `{artifact_refs.get('preflight_evidence_graph', 'missing')}`",
        f"- Budget graph: `{artifact_refs.get('budget_evidence_graph', 'missing')}`",
    ]
    if evidence_graph is None:
        return [*lines, "- Graph details unavailable in package renderer."]

    node_types = [node.node_type for node in evidence_graph.nodes]
    relationships = [edge.relationship for edge in evidence_graph.edges]
    lines.extend(
        [
            f"- Graph ID: {evidence_graph.graph_id}",
            f"- Nodes: {len(evidence_graph.nodes)}",
            f"- Edges: {len(evidence_graph.edges)}",
            f"- Node types: {_sorted_counts(node_types)}",
            f"- Relationships: {_sorted_counts(relationships)}",
            "- Key provenance edges:",
        ]
    )
    key_relationships = [
        "supports_human_confirmation",
        "supports_party_role_candidate",
        "supports_conflict_search_term",
        "supports_budget_line",
        "supports_budget_support_item",
        "supports_budget_proposal",
    ]
    for relationship in key_relationships:
        edge = next(
            (item for item in evidence_graph.edges if item.relationship == relationship),
            None,
        )
        if edge is None:
            lines.append(f"- edge {relationship}: missing")
            continue
        lines.append(
            f"- edge {relationship}: {edge.source_node_id} -> {edge.target_node_id}; "
            f"status={edge.status}; evidence_refs={len(edge.evidence_refs)}"
        )
    return lines


def _required_human_gate_lines(
    confirmation: HumanConfirmation,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
) -> list[str]:
    return [
        f"- human_intake_confirmation: completed for confirmation `{confirmation.confirmation_id}`; "
        "classification, posture, and principal party roles remain review artifacts.",
        f"- human_conflicts_clearance: required before any conflict conclusion; current conflict output is `{conflict_seed.conclusion}`.",
        "- human_engagement_authorization: required before accepting representation; "
        f"current blockers: {', '.join(readiness.blockers)}.",
        f"- human_budget_review: required before client/carrier submission; current budget state is `{budget.approval_state}`.",
        f"- human_matter_opening_authorization: required before matter or workspace creation; current readiness is `{readiness.status}`.",
    ]


def render_matter_opening_review_package(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
    safety_report: SafetyGateReport,
    exception_candidates: list[dict[str, Any]],
    artifact_refs: dict[str, str],
    run_ledger_events: dict[str, list[dict[str, Any]]] | None = None,
    evidence_graph: EvidenceGraph | None = None,
    exception_readiness_report: ExceptionLakeReadinessReport | None = None,
    contract_state_report: ContractStateReport | None = None,
    human_review_outcome: HumanReviewOutcomeRecord | None = None,
    budget_precondition_report: BudgetPreconditionReport | None = None,
) -> str:
    source_summary = packet.source_coverage_summary
    deadline_lines = [
        f"- {item.expression}: {item.deadline_type_candidate}; not docketed; "
        f"evidence: {_refs_text(item.evidence_refs, limit=3)}"
        for item in packet.deadline_candidates
    ]
    missing_lines = [
        f"- missing information: {item.field_name}; {item.reason}; "
        f"evidence: {_refs_text(item.evidence_refs, limit=3)}"
        for item in packet.missing_information_candidates
    ] or [f"- missing information: {item}" for item in packet.missing_information]
    finding_lines = [
        f"- [{finding.severity}] {finding.code}: {finding.message}; "
        f"evidence: {_refs_text(finding.evidence_refs, limit=3)}"
        for finding in packet.critic_findings
    ]
    conflict_lines = _conflict_seed_lines(conflict_seed)
    artifact_lines = [f"- {name}: `{path}`" for name, path in sorted(artifact_refs.items())]

    total_budget = (
        f"{budget.total_proposed_budget:.2f} {budget.currency}"
        if budget.total_proposed_budget is not None
        else "no total; hours-only or insufficient information"
    )

    return "\n".join(
        [
            "# Matter Opening Review Package",
            "",
            f"**Run ID:** {packet.run_id}",
            f"**Preflight packet ID:** {packet.packet_id}",
            f"**Human confirmation ID:** {confirmation.confirmation_id}",
            f"**Final boundary:** {readiness.status}",
            "",
            "## Authority And Preconditions",
            "",
            "### Contract State",
            *_contract_state_lines(contract_state_report),
            "",
            "### Human Review Outcome",
            *_human_review_outcome_lines(human_review_outcome),
            "",
            "### Budget Preconditions",
            *_budget_precondition_lines(budget_precondition_report),
            "",
            "## Source Inventory",
            "",
            f"- Coverage complete: {source_summary.get('coverage_complete')}",
            f"- Missing sources: {source_summary.get('missing_sources')}",
            f"- Unread sources: {source_summary.get('unread_sources')}",
            f"- Unreadable sources: {source_summary.get('unreadable_sources')}",
            f"- Duplicate sources: {source_summary.get('duplicate_sources')}",
            f"- Attachment references: {source_summary.get('attachment_reference_count')}",
            *_source_inventory_lines(packet),
            "",
            "## What Is Known",
            "",
            f"- Human-confirmed inbound event: {confirmation.confirmed_inbound_event or 'unknown'}",
            f"- Human-confirmed matter family: {confirmation.confirmed_matter_family or 'unknown'}",
            f"- Human-confirmed representation posture: {confirmation.confirmed_representation_posture or 'unknown'}",
            f"- Human-confirmed jurisdiction: {confirmation.confirmed_jurisdiction or 'unknown'}",
            f"- Human confirmation decision evidence: {_refs_text(confirmation.decision_evidence_refs, limit=5)}",
            *_confirmed_party_lines(confirmation),
            "",
            "## Candidate Alternatives",
            "",
            "### Inbound Event Candidates",
            *_candidate_lines(packet.inbound_event_candidates),
            "",
            "### Matter Family Candidates",
            *_candidate_lines(packet.matter_family_candidates),
            "",
            "### Representation Posture Candidates",
            *_candidate_lines(packet.representation_posture_candidates),
            "",
            "### Party And Role Candidates",
            *_party_candidate_lines(packet),
            "",
            "## What Still Needs Human Review",
            "",
            f"- Source coverage complete: {source_summary.get('coverage_complete')}",
            f"- Missing sources: {source_summary.get('missing_sources')}",
            f"- Unread sources: {source_summary.get('unread_sources')}",
            f"- Unreadable sources: {source_summary.get('unreadable_sources')}",
            f"- Duplicate sources: {source_summary.get('duplicate_sources')}",
            *_lines_or_none(missing_lines),
            *_lines_or_none(deadline_lines),
            *_lines_or_none(finding_lines),
            *_lines_or_none([f"- budget unknown: {item}" for item in budget.unknowns]),
            "",
            "## Required Human Gates",
            "",
            *_required_human_gate_lines(confirmation, conflict_seed, budget, readiness),
            "",
            "## Conflict Search Seed",
            "",
            f"- Conclusion: {conflict_seed.conclusion}",
            *_lines_or_none(conflict_lines),
            "",
            "## Budget Proposal",
            "",
            f"- Approval state: {budget.approval_state}",
            f"- Client/carrier submission authorized: {not budget.not_authorized_for_client_submission}",
            f"- Scenario: {budget.scenario_name}",
            f"- Pricing status: {budget.pricing_status}",
            f"- Total proposed budget: {total_budget}",
            "",
            "### Calculation Summary",
            *_budget_calculation_lines(budget),
            "",
            "### Budget Lines",
            *_budget_line_lines(budget),
            "",
            "### Budget Supports",
            *_budget_support_lines(budget),
            "",
            "## Exception And Escalation Records",
            "",
            f"- Dry-run candidate count: {len(exception_candidates)}",
            *(
                [
                    "- Exception Lake readiness report: "
                    f"`{artifact_refs['budget_exception_lake_readiness_report']}`"
                ]
                if "budget_exception_lake_readiness_report" in artifact_refs
                else []
            ),
            *_lines_or_none(_exception_lines(exception_candidates)),
            "",
            "### Exception Lake Readiness",
            *_exception_readiness_lines(exception_readiness_report),
            "",
            "### Exception Candidate Details",
            *_exception_candidate_detail_lines(exception_candidates),
            "",
            "## Safety Gate",
            "",
            f"- Status: {safety_report.status}",
            f"- Final boundary: {safety_report.final_boundary}",
            f"- External writes performed: {safety_report.external_writes_performed}",
            *_safety_gate_lines(safety_report),
            "",
            "## Matter-Opening Blockers",
            "",
            *_lines_or_none([f"- satisfied: {item}" for item in readiness.satisfied]),
            *_lines_or_none([f"- blocker: {item}" for item in readiness.blockers]),
            *_lines_or_none(
                [f"- prohibited action: {item}" for item in readiness.prohibited_actions]
            ),
            "",
            "## Evidence Graph Summary",
            "",
            *_evidence_graph_lines(artifact_refs, evidence_graph),
            "",
            "## Run Ledger Summary",
            "",
            *_run_ledger_lines(artifact_refs, run_ledger_events or {}),
            "",
            "## Artifact References",
            "",
            *artifact_lines,
            "",
            "This package does not clear conflicts, accept representation, docket deadlines, open a matter, create an iManage workspace, send communications, submit a budget, or authorize client/carrier delivery.",
            "",
        ]
    )
