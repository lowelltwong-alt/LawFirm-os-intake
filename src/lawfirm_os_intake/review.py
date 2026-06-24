from __future__ import annotations

from typing import Any

from .models import (
    BudgetProposal,
    ConflictSeedPacket,
    HumanConfirmation,
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
    source_lines = [
        (
            f"- {item.source_id}: {item.source_type}, {item.read_state}, "
            f"{item.availability_state}, sha={item.source_sha256}"
        )
        for item in packet.source_inventory
    ]
    party_lines = []
    for party in packet.party_candidates:
        roles = ", ".join(f"{role.role} ({role.confidence:.2f})" for role in party.role_candidates)
        refs = ", ".join(_ref_text(ref) for ref in party.evidence_refs[:3])
        party_lines.append(f"- {party.name}: {roles}; evidence: {refs}")

    missing_lines = [
        f"- {item.field_name}: {item.reason}" for item in packet.missing_information_candidates
    ] or ["- none"]
    deadline_lines = [
        f"- {item.expression}: {item.deadline_type_candidate}; human verification required"
        for item in packet.deadline_candidates
    ] or ["- none"]
    finding_lines = [
        f"- [{finding.severity}] {finding.code}: {finding.message}"
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
            *source_lines,
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
            "The generated proposal is not authorized for client or carrier submission.",
            "",
        ]
    )
    return "\n".join(lines)


def _lines_or_none(lines: list[str]) -> list[str]:
    return lines or ["- none"]


def _budget_support_lines(budget: BudgetProposal) -> list[str]:
    lines = []
    for item in budget.budget_support_items:
        refs = ", ".join(_ref_text(ref) for ref in item.evidence_refs)
        support = refs or item.structured_ref or "missing support"
        lines.append(f"- {item.item_type}: {item.text} ({item.source_kind}; {support})")
    return lines or ["- none"]


def _ref_text(ref: Any) -> str:
    return f"{ref.source_id}/{ref.segment_id}[{ref.start_offset}:{ref.end_offset}]"


def _confirmed_party_lines(confirmation: HumanConfirmation) -> list[str]:
    return [
        f"- {party.confirmed_role}: {party.name}"
        + (f" (aliases: {', '.join(party.aliases)})" if party.aliases else "")
        for party in confirmation.confirmed_parties
    ]


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


def _safety_gate_lines(report: SafetyGateReport) -> list[str]:
    return [f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks]


def render_matter_opening_review_package(
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
    safety_report: SafetyGateReport,
    exception_candidates: list[dict[str, Any]],
    artifact_refs: dict[str, str],
) -> str:
    source_summary = packet.source_coverage_summary
    deadline_lines = [
        f"- {item.expression}: {item.deadline_type_candidate}; not docketed"
        for item in packet.deadline_candidates
    ]
    finding_lines = [
        f"- [{finding.severity}] {finding.code}: {finding.message}"
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
            "## What Is Known",
            "",
            f"- Human-confirmed inbound event: {confirmation.confirmed_inbound_event or 'unknown'}",
            f"- Human-confirmed matter family: {confirmation.confirmed_matter_family or 'unknown'}",
            f"- Human-confirmed representation posture: {confirmation.confirmed_representation_posture or 'unknown'}",
            f"- Human-confirmed jurisdiction: {confirmation.confirmed_jurisdiction or 'unknown'}",
            *_confirmed_party_lines(confirmation),
            "",
            "## What Still Needs Human Review",
            "",
            f"- Source coverage complete: {source_summary.get('coverage_complete')}",
            f"- Missing sources: {source_summary.get('missing_sources')}",
            f"- Unread sources: {source_summary.get('unread_sources')}",
            f"- Unreadable sources: {source_summary.get('unreadable_sources')}",
            f"- Duplicate sources: {source_summary.get('duplicate_sources')}",
            *_lines_or_none(
                [f"- missing information: {item}" for item in packet.missing_information]
            ),
            *_lines_or_none(deadline_lines),
            *_lines_or_none(finding_lines),
            *_lines_or_none([f"- budget unknown: {item}" for item in budget.unknowns]),
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
            "## Artifact References",
            "",
            *artifact_lines,
            "",
            "This package does not clear conflicts, accept representation, docket deadlines, open a matter, create an iManage workspace, send communications, submit a budget, or authorize client/carrier delivery.",
            "",
        ]
    )
