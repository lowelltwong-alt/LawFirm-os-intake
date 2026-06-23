from __future__ import annotations

from .models import BudgetProposal, IntakePreflightPacket


def _candidate_lines(candidates: list, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for candidate in candidates[:limit]:
        refs = ", ".join(
            f"{ref.source_id}/{ref.segment_id}" for ref in candidate.observed_evidence_refs[:3]
        )
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
        refs = ", ".join(f"{ref.source_id}/{ref.segment_id}" for ref in party.evidence_refs[:3])
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
