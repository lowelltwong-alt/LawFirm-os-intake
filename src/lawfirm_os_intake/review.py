from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetPreconditionReport,
    BudgetProposal,
    BudgetSubmissionGuardReport,
    ConflictSeedPacket,
    ContractStateReport,
    ContextBoundaryReport,
    DataScopeGateReport,
    DeadlineDocketingGuardReport,
    EvidenceCompletenessReport,
    EvidenceGraph,
    ExceptionLakeHandoffManifest,
    ExceptionLakeReadinessReport,
    HumanConfirmation,
    HumanGateStatusReport,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    ModelAdapterReport,
    RunLedgerIntegrityReport,
    SafetyGateReport,
)
from .util import load_json


def _candidate_lines(candidates: list, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for candidate in candidates[:limit]:
        refs = ", ".join(_ref_text(ref) for ref in candidate.observed_evidence_refs[:3])
        context = ", ".join(candidate.context_signal_refs)
        context_text = f"; context: {context}" if context else ""
        status = candidate.source_evidence_status
        if status == "observed_support":
            ref_text = f"evidence: {refs or 'none'}"
        elif status == "unknown_option":
            ref_text = f"source anchor: {refs or 'none'}; explicit unknown option"
        else:
            ref_text = f"source anchor: {refs or 'none'}; no direct observed support"
        lines.append(
            f"- {candidate.label} ({candidate.confidence:.2f}; "
            f"{candidate.calibration_label}; {status}) {ref_text}{context_text}"
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
            "",
            "## Driver Profile Summary",
            "",
            *_budget_driver_profile_summary_lines(budget),
            "",
            "## Scenario Comparison",
            "",
            *_budget_scenario_lines(budget),
            "",
            "## Scenario Set",
            "",
            *_budget_scenario_lines(budget),
            "",
            "## Budget Driver Effects",
            "",
            *_budget_driver_effect_lines(budget),
            "",
            "## Guideline Flags",
            "",
            *_budget_guideline_flag_lines(budget),
            "",
            "## Workbook Mapping Status",
            "",
            *_budget_workbook_mapping_status_lines(),
            "",
            "## Unresolved Budget Assumptions",
            "",
            *_budget_unresolved_assumption_lines(budget),
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


def _budget_driver_profile_summary_lines(budget: BudgetProposal) -> list[str]:
    summary = budget.driver_profile_summary
    if summary is None:
        return [
            "- Case driver profile: not generated",
            "- Profile defaults treated as observed facts: False",
            "- Context priors treated as observed facts: False",
            "- Human budget review required: True",
        ]
    observed = ", ".join(summary.observed_or_confirmed_driver_ids) or "none"
    defaults = ", ".join(summary.default_driver_ids) or "none"
    unknowns = ", ".join(summary.unknown_driver_ids) or "none"
    return [
        f"- Case driver profile ID: {summary.case_driver_profile_id}",
        f"- Policy: {summary.policy_id}@{summary.policy_version}",
        f"- Driver count: {summary.driver_count}",
        f"- Observed or human-confirmed drivers: {observed}",
        f"- Profile default drivers needing review: {defaults}",
        f"- Unknown drivers needing review: {unknowns}",
        f"- Profile defaults treated as observed facts: {summary.profile_defaults_are_observed_facts}",
        f"- Context priors treated as observed facts: {summary.context_priors_are_observed_facts}",
        f"- Human budget review required: {summary.requires_human_review}",
        f"- Authoritative budget canon: {not summary.not_authoritative}",
    ]


def _budget_scenario_lines(budget: BudgetProposal) -> list[str]:
    if budget.scenario_set is None:
        return ["- none"]
    lines = [
        f"- Selected scenario: {budget.scenario_set.selected_scenario_id}",
        f"- Monotonic order: {budget.scenario_set.monotonic_total_order} "
        f"({budget.scenario_set.total_order_basis})",
    ]
    for scenario in budget.scenario_set.scenarios:
        lines.append(
            f"- {scenario.scenario_id}: through {scenario.resolution_phase}; "
            f"hours: {scenario.total_hours}; "
            f"fees: {_money(scenario.subtotal_fees, budget.currency)}; "
            f"expenses: {_money(scenario.subtotal_expenses, budget.currency)}; "
            f"total: {_money(scenario.total_proposed_budget, budget.currency)}; "
            f"range: {_money(scenario.total_budget_min, budget.currency)}-"
            f"{_money(scenario.total_budget_max, budget.currency)}; "
            f"codes: {', '.join(scenario.included_external_codes) or 'none'}"
        )
    return lines


def _budget_driver_effect_lines(budget: BudgetProposal) -> list[str]:
    lines = []
    for effect in budget.driver_effects:
        value = "unknown" if effect.driver_value is None else str(effect.driver_value)
        multiplier = f"; multiplier: {effect.multiplier}" if effect.multiplier is not None else ""
        capped = "; capped" if effect.capped else ""
        phases = ", ".join(effect.phase_ids) or "none"
        tasks = ", ".join(effect.task_ids) or "none"
        support = effect.structured_ref or ", ".join(effect.source_refs) or "none"
        lines.append(
            f"- {effect.driver_id}={value} ({effect.provenance}; {effect.effect_type}); "
            f"applied: {effect.applied}; phases: {phases}; tasks: {tasks}"
            f"{multiplier}{capped}; support: {support}; note: {effect.note}"
        )
    return lines or ["- none"]


def _budget_guideline_flag_lines(budget: BudgetProposal) -> list[str]:
    lines = []
    for flag in budget.guideline_flags:
        location = flag.phase_id or flag.role or "proposal"
        support = flag.structured_ref or "none"
        lines.append(
            f"- {flag.constraint_id} ({flag.constraint_type}; {location}): "
            f"{flag.status}; current={flag.current_value}; threshold={flag.threshold_value}; "
            f"rewrites budget: {flag.rewrites_budget}; support: {support}; note: {flag.note}"
        )
    return lines or ["- none"]


def _budget_workbook_mapping_status_lines(
    artifact_refs: dict[str, str] | None = None,
) -> list[str]:
    mapping_ref = (artifact_refs or {}).get("budget_form_mapping_report", "")
    if not mapping_ref:
        return [
            "- Template-backed workbook render attempted: False",
            "- Mapping report available: False",
            "- Required before relying on filled carrier form: budget_form_mapping_report.json with status=passed",
            "- Workbook submission authorized: False",
            "- Sanitized workbook committed or embedded in intake outputs: False",
        ]
    lines = [f"- Mapping report: `{mapping_ref}`"]
    try:
        payload = load_json(Path(mapping_ref))
    except (OSError, ValueError):
        return [
            *lines,
            "- Mapping report status: unavailable",
            "- Workbook submission authorized: False",
        ]
    if not isinstance(payload, dict):
        return [
            *lines,
            "- Mapping report status: unavailable",
            "- Workbook submission authorized: False",
        ]
    return [
        *lines,
        f"- Mapping report status: {payload.get('status', 'unknown')}",
        f"- Template hash: {payload.get('template_sha256', 'unknown')}",
        f"- Sheet name: {payload.get('sheet_name', 'unknown')}",
        "- Required before relying on filled carrier form: budget_form_mapping_report.json with status=passed",
        "- Workbook submission authorized: "
        f"{not payload.get('not_authorized_for_client_submission', True)}",
        f"- Formula checks passed: {payload.get('formula_checks_passed', 'unknown')}",
    ]


def _budget_unresolved_assumption_lines(budget: BudgetProposal) -> list[str]:
    lines: list[str] = []
    for unknown in budget.unknowns:
        lines.append(f"- budget unknown: {unknown}")
    for effect in budget.driver_effects:
        if effect.effect_type == "unknown_driver" or effect.provenance == "profile_default":
            value = "unknown" if effect.driver_value is None else str(effect.driver_value)
            lines.append(
                f"- driver review: {effect.driver_id}={value}; provenance={effect.provenance}; "
                f"applied={effect.applied}; note={effect.note}"
            )
    for flag in budget.guideline_flags:
        if flag.status != "not_triggered":
            lines.append(
                f"- guideline review: {flag.constraint_id}; status={flag.status}; "
                f"rewrites_budget={flag.rewrites_budget}; note={flag.note}"
            )
    return lines or ["- none"]


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


def _ingestion_volume_profile_lines(artifact_refs: dict[str, str]) -> list[str]:
    path = artifact_refs.get("preflight_ingestion_volume_profile", "")
    lines = [f"- Ingestion volume profile: `{path or 'missing'}`"]
    if not path:
        return lines
    try:
        payload = load_json(Path(path))
    except (OSError, ValueError):
        return [*lines, "- Ingestion volume profile details: unavailable"]
    if not isinstance(payload, dict):
        return [*lines, "- Ingestion volume profile details: unavailable"]

    scale_signals = ", ".join(payload.get("scale_signals") or []) or "none"
    compute_pressure = ", ".join(payload.get("compute_pressure_signals") or []) or "none"
    profile_dimensions = (
        ", ".join(payload.get("required_performance_profile_dimensions") or []) or "none"
    )
    hot_path_scope = ", ".join(payload.get("candidate_rust_hot_path_scope") or []) or "none"
    transition_gates = ", ".join(payload.get("required_rust_transition_gates") or []) or "none"
    return [
        *lines,
        f"- Rust transition policy: `{payload.get('rust_transition_policy_ref', 'unknown')}`",
        f"- Ingestion profile decision: {payload.get('decision', 'unknown')}",
        f"- Rust adapter proposal state: {payload.get('rust_adapter_proposal_state', 'unknown')}",
        "- Profiling before Rust required: "
        f"{payload.get('performance_profile_required_before_rust', 'unknown')}",
        f"- Rust replacement allowed: {payload.get('rust_replacement_allowed', 'unknown')}",
        f"- Scale signals: {scale_signals}",
        f"- Compute pressure signals: {compute_pressure}",
        f"- Required performance profile dimensions: {profile_dimensions}",
        f"- Candidate Rust hot path scope: {hot_path_scope}",
        f"- Required Rust transition gates: {transition_gates}",
    ]


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


def _data_scope_gate_lines(report: DataScopeGateReport | None) -> list[str]:
    if report is None:
        return ["- Data scope gate report: unavailable"]
    lines = [
        f"- Data scope gate status: {report.status}",
        f"- Data scope blocked state: {report.blocked_state or 'none'}",
        f"- Runtime mode: {report.runtime_mode}",
        f"- Data origin: {report.data_origin}",
        f"- Contains real client data: {report.contains_real_client_data}",
        f"- Contains real matter data: {report.contains_real_matter_data}",
        f"- Contains privileged data: {report.contains_privileged_data}",
        f"- Public data direct ingestion allowed: {report.public_data_direct_ingestion_allowed}",
        f"- Raw payload written before gate: {report.raw_payload_written}",
        f"- Data scope external writes performed: {report.external_writes_performed}",
        f"- Data scope policy refs: {', '.join(report.policy_refs)}",
        "- Data scope checks:",
    ]
    lines.extend(f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks)
    return lines


def _model_adapter_lines(report: ModelAdapterReport | None) -> list[str]:
    if report is None:
        return ["- Model adapter report: unavailable"]
    lines = [
        f"- Model adapter status: {report.status}",
        f"- Adapter: {report.adapter_name} ({report.adapter_mode})",
        f"- Provider call performed: {report.provider_call_performed}",
        f"- Model calls allowed: {report.model_calls_allowed}",
        f"- External tools allowed: {report.external_tools_allowed}",
        f"- Network access allowed: {report.network_access_allowed}",
        f"- External writes allowed: {report.external_writes_allowed}",
        f"- Approved for real data: {report.approved_for_real_data}",
        f"- Typed JSON only: {report.typed_json_only}",
        f"- Prompt registry: `{report.prompt_registry_ref}`",
        f"- Prompt hashes pinned: {len(report.prompt_hashes)}",
        f"- Baseline comparison state: {report.baseline_comparison_state}",
        f"- Comparison status: {report.comparison_status}",
        f"- Synthetic gold required: {report.synthetic_gold_required}",
        f"- Synthetic gold compared: {report.synthetic_gold_compared}",
        f"- Fixture gold status: {report.fixture_gold_status}",
        f"- Typed JSON validation status: {report.typed_json_validation_status}",
        f"- Deterministic baseline hash: {report.deterministic_baseline_hash}",
        f"- Structured candidate hash: {report.structured_candidate_hash}",
        f"- Required human gates: {', '.join(report.required_human_gates)}",
        "- Adapter guard checks:",
    ]
    lines.extend(f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks)
    return lines


def _evidence_completeness_lines(report: EvidenceCompletenessReport | None) -> list[str]:
    if report is None:
        return ["- Evidence completeness report: unavailable"]
    surface_counts = ", ".join(
        f"{surface}={count}" for surface, count in sorted(report.surface_counts.items())
    )
    source_status_counts = ", ".join(
        f"{status}={count}"
        for status, count in sorted(report.source_evidence_status_counts.items())
    )
    lines = [
        f"- Evidence completeness status: {report.status}",
        f"- Evidence completeness report ID: `{report.evidence_completeness_report_id}`",
        f"- Strict evidence required: {report.strict_evidence_required}",
        f"- Evidence refs checked: {report.evidence_ref_count}",
        f"- Human confirmation required: {report.human_confirmation_required}",
        f"- Source evidence status counts: {source_status_counts or 'none'}",
        f"- Surface counts: {surface_counts or 'none'}",
        "- Evidence completeness checks:",
    ]
    lines.extend(
        f"- {check.status}: {check.check_id} - {check.message}; "
        f"evidence_refs={len(check.evidence_refs)}"
        for check in report.checks
    )
    return lines


def _context_boundary_lines(report: ContextBoundaryReport | None) -> list[str]:
    if report is None:
        return ["- Context boundary report: unavailable"]
    lines = [
        f"- Context boundary status: {report.status}",
        f"- Context boundary report ID: `{report.context_boundary_report_id}`",
        f"- Effective context ID: `{report.effective_context_id}`",
        f"- Practice profile: {report.profile_id} v{report.profile_version}",
        f"- Practice profile hash: {report.profile_sha256}",
        f"- Observed source evidence precedence: {report.observed_source_evidence_precedence}",
        f"- Practice context is observed evidence: {report.practice_context_is_observed_evidence}",
        f"- Human confirmation required: {report.human_confirmation_required}",
        f"- Checked scored candidates: {report.checked_candidate_count}",
        f"- Context signal candidates: {report.context_signal_candidate_count}",
        f"- Context-only candidate count: {report.context_only_candidate_count}",
        f"- Observed-with-context candidate count: {report.observed_with_context_candidate_count}",
        f"- Unknown option count: {report.unknown_option_count}",
        "- Context boundary checks:",
    ]
    lines.extend(
        f"- {check.status}: {check.check_id} - {check.message}; "
        f"candidates={len(check.candidate_ids)}; context_refs={len(check.context_signal_refs)}"
        for check in report.checks
    )
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


def _exception_handoff_lines(report: ExceptionLakeHandoffManifest | None) -> list[str]:
    if report is None:
        return ["- Exception Lake handoff manifest: unavailable"]
    lines = [
        f"- Handoff status: {report.status}",
        f"- Stage: {report.stage}",
        f"- Admission state: {report.admission_state}",
        f"- Target runtime repo: {report.target_runtime_repo}",
        f"- Storage owner: {report.storage_owner}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Mapping review required: {report.mapping_review_required}",
        f"- Canonical promotion required: {report.canonical_promotion_required}",
        f"- Candidate count: {report.candidate_count}",
        "- Label summaries:",
    ]
    for summary in report.label_summaries:
        support_modes = ", ".join(summary.support_modes) or "none"
        blocked_states = ", ".join(summary.blocked_states) or "none"
        lines.append(
            f"- {summary.local_event_label}: class={summary.canonical_lake_class}; "
            f"count={summary.count}; support={support_modes}; "
            f"source_refs={summary.source_inventory_ref_count}; "
            f"evidence_refs={summary.evidence_ref_count}; "
            f"structured_refs={summary.structured_ref_count}; "
            f"blocked_states={blocked_states}"
        )
    lines.append("- Handoff checks:")
    lines.extend(f"- {check.status}: {check.check_id} - {check.message}" for check in report.checks)
    return lines


def _exception_mapping_package_lines(artifact_refs: dict[str, str]) -> list[str]:
    path = artifact_refs.get("budget_exception_lake_mapping_package", "")
    lines = [f"- Exception Lake mapping package: `{path or 'missing'}`"]
    if not path:
        return [*lines, "- Mapping package details: unavailable"]
    try:
        payload = load_json(Path(path))
    except (OSError, ValueError):
        return [*lines, "- Mapping package details: unavailable"]
    if not isinstance(payload, dict):
        return [*lines, "- Mapping package details: unavailable"]
    lines.extend(
        [
            f"- Mapping package status: {payload.get('status', 'unknown')}",
            f"- Admission state: {payload.get('admission_state', 'unknown')}",
            f"- Target runtime repo: {payload.get('target_runtime_repo', 'unknown')}",
            f"- SQLite write performed: {payload.get('sqlite_write_performed', 'unknown')}",
            f"- External writes performed: {payload.get('external_writes_performed', 'unknown')}",
            f"- Canonical promotion required: {payload.get('canonical_promotion_required', 'unknown')}",
            "- Mapping rules:",
        ]
    )
    for rule in payload.get("rules", []):
        if not isinstance(rule, dict):
            continue
        support_kinds = ", ".join(rule.get("support_ref_kinds") or []) or "none"
        lines.append(
            f"- {rule.get('mapping_id')}: issue={rule.get('issue_family')}; "
            f"label={rule.get('local_event_label')}; "
            f"class={rule.get('canonical_lake_class')}; "
            f"candidate_count={rule.get('candidate_count')}; support={support_kinds}"
        )
    return lines


def _budget_actual_comparison_lines(artifact_refs: dict[str, str]) -> list[str]:
    path = artifact_refs.get("budget_actual_comparison_report", "")
    lines = [f"- Budget actual comparison report: `{path or 'missing'}`"]
    if not path:
        return [*lines, "- Budget actual comparison details: unavailable"]
    try:
        payload = load_json(Path(path))
    except (OSError, ValueError):
        return [*lines, "- Budget actual comparison details: unavailable"]
    if not isinstance(payload, dict):
        return [*lines, "- Budget actual comparison details: unavailable"]
    lines.extend(
        [
            f"- Actual comparison status: {payload.get('status', 'unknown')}",
            f"- Comparison scope: {payload.get('comparison_scope', 'unknown')}",
            f"- Variance threshold percent: {payload.get('variance_threshold_percent', 'unknown')}",
            f"- Billing connector read performed: {payload.get('billing_connector_read_performed', 'unknown')}",
            f"- Billing connector write performed: {payload.get('billing_connector_write_performed', 'unknown')}",
            f"- External writes performed: {payload.get('external_writes_performed', 'unknown')}",
            "- Phase comparisons:",
        ]
    )
    for row in payload.get("phase_comparisons", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('phase_id')}: budgeted={row.get('budgeted_total')}; "
            f"actual={row.get('actual_total')}; "
            f"variance={row.get('variance_amount')} ({row.get('variance_percent')}%); "
            f"status={row.get('status')}"
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


def _run_ledger_integrity_lines(
    reports: list[dict[str, Any] | None] | None,
) -> list[str]:
    lines = []
    for payload in reports or []:
        if payload is None:
            continue
        report = RunLedgerIntegrityReport.model_validate(payload)
        lines.extend(
            [
                f"- {report.stage}: status={report.status}; "
                f"terminal={report.terminal_step_name} ({report.terminal_status}); "
                f"events={report.event_count}; ledger=`{report.run_ledger_ref}`",
                f"- {report.stage}: required steps={', '.join(report.required_steps)}",
                f"- {report.stage}: local artifact refs only={report.local_artifact_refs_only}; "
                f"external writes performed={report.external_writes_performed}",
            ]
        )
        for check in report.checks:
            lines.append(f"- {report.stage} check {check.check_id}: {check.status}")
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


def _readiness_blocker_detail_lines(readiness: MatterOpeningReadiness) -> list[str]:
    lines = []
    for blocker in readiness.blocker_details:
        structured = blocker.structured_ref or "none"
        prohibits = ", ".join(blocker.prohibits) or "none"
        lines.append(
            f"- blocker detail: {blocker.blocker_code}; gate={blocker.required_human_gate}; "
            f"scope={blocker.blocking_scope}; support={blocker.support_kind}; "
            f"structured_ref={structured}; prohibits={prohibits}; reason={blocker.reason}"
        )
    for guardrail in readiness.prohibited_action_details:
        linked = ", ".join(guardrail.linked_blocker_codes) or "none"
        lines.append(
            f"- prohibited action detail: {guardrail.action_code}; "
            f"blocks={guardrail.transition_blocked}; gate={guardrail.required_human_gate}; "
            f"support={guardrail.support_kind}; structured_ref={guardrail.structured_ref}; "
            f"linked blockers={linked}; reason={guardrail.reason}"
        )
    return lines or ["- none"]


def _human_gate_status_report_lines(
    artifact_refs: dict[str, str],
    report: HumanGateStatusReport | None,
) -> list[str]:
    path = artifact_refs.get("human_gate_status_report", "")
    lines = [f"- Human gate status report: `{path or 'missing'}`"]
    if report is None:
        if not path:
            return lines
        try:
            payload = load_json(Path(path))
            report = HumanGateStatusReport.model_validate(payload)
        except (OSError, ValueError):
            return [*lines, "- Human gate status report details: unavailable"]
    lines.extend(
        [
            f"- Human gate status: {report.status}",
            f"- Human gates completed: {report.completed_gate_count}",
            f"- Human gates pending: {report.pending_gate_count}",
        ]
    )
    for gate in report.gates:
        blocks = ", ".join(gate.blocks) or "none"
        structured_refs = ", ".join(gate.structured_refs) or "none"
        lines.append(
            f"- {gate.gate_id}: {gate.status}; owner={gate.authority_owner}; "
            f"completed_by_human={gate.completed_by_human}; blocks={blocks}; "
            f"structured_refs={structured_refs}"
        )
    return lines


def _deadline_docketing_guard_report_lines(
    artifact_refs: dict[str, str],
    report: DeadlineDocketingGuardReport | None,
) -> list[str]:
    path = artifact_refs.get("preflight_deadline_docketing_guard_report", "")
    lines = [f"- Deadline docketing guard report: `{path or 'missing'}`"]
    if report is None:
        if not path:
            return lines
        try:
            payload = load_json(Path(path))
            report = DeadlineDocketingGuardReport.model_validate(payload)
        except (OSError, ValueError):
            return [*lines, "- Deadline docketing guard report details: unavailable"]
    lines.extend(
        [
            f"- Deadline docketing guard status: {report.status}",
            f"- Deadline candidates under guard: {report.candidate_count}",
            f"- Deadline candidates requiring review: {report.review_required_count}",
            f"- Docketing action performed: {report.docketing_action_performed}",
            f"- Docketing action allowed: {report.docketing_action_allowed}",
            f"- Deadline guard external writes performed: {report.external_writes_performed}",
            f"- Deadline proposed next gate: {report.proposed_next_gate}",
        ]
    )
    for item in report.candidate_items:
        structured_refs = ", ".join(item.structured_refs) or "none"
        lines.append(
            f"- deadline guard item: {item.expression}; "
            f"type={item.deadline_type_candidate}; gate={item.proposed_next_gate}; "
            f"requires_human_verification={item.requires_human_verification}; "
            f"source_evidence_status={item.source_evidence_status}; "
            f"evidence={_refs_text(item.evidence_refs, limit=3)}; "
            f"structured_refs={structured_refs}"
        )
    for check in report.checks:
        structured_refs = ", ".join(check.structured_refs) or "none"
        lines.append(
            f"- deadline guard check {check.check_id}: {check.status}; "
            f"structured_refs={structured_refs}"
        )
    return lines


def _budget_submission_guard_report_lines(
    artifact_refs: dict[str, str],
    report: BudgetSubmissionGuardReport | None,
) -> list[str]:
    path = artifact_refs.get("budget_submission_guard_report", "")
    lines = [f"- Budget submission guard report: `{path or 'missing'}`"]
    if report is None:
        if not path:
            return lines
        try:
            payload = load_json(Path(path))
            report = BudgetSubmissionGuardReport.model_validate(payload)
        except (OSError, ValueError):
            return [*lines, "- Budget submission guard report details: unavailable"]
    lines.extend(
        [
            f"- Budget submission guard status: {report.status}",
            f"- Budget guard approval state: {report.approval_state}",
            "- Budget guard not authorized for client submission: "
            f"{report.not_authorized_for_client_submission}",
            f"- Client submission performed: {report.client_submission_performed}",
            f"- Carrier submission performed: {report.carrier_submission_performed}",
            f"- Billing handoff performed: {report.billing_handoff_performed}",
            f"- Budget guard external writes performed: {report.external_writes_performed}",
            f"- Budget guard required human gate: {report.required_human_gate}",
            f"- Budget guard actions: {', '.join(report.guarded_actions) or 'none'}",
        ]
    )
    for check in report.checks:
        structured_refs = ", ".join(check.structured_refs) or "none"
        lines.append(
            f"- budget submission guard check {check.check_id}: {check.status}; "
            f"structured_refs={structured_refs}"
        )
    return lines


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
    run_ledger_integrity_reports: list[dict[str, Any] | None] | None = None,
    evidence_graph: EvidenceGraph | None = None,
    exception_readiness_report: ExceptionLakeReadinessReport | None = None,
    exception_handoff_manifest: ExceptionLakeHandoffManifest | None = None,
    contract_state_report: ContractStateReport | None = None,
    data_scope_gate_report: DataScopeGateReport | None = None,
    model_adapter_report: ModelAdapterReport | None = None,
    human_review_outcome: HumanReviewOutcomeRecord | None = None,
    human_gate_status_report: HumanGateStatusReport | None = None,
    deadline_docketing_guard_report: DeadlineDocketingGuardReport | None = None,
    evidence_completeness_report: EvidenceCompletenessReport | None = None,
    context_boundary_report: ContextBoundaryReport | None = None,
    budget_submission_guard_report: BudgetSubmissionGuardReport | None = None,
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
            "### Data Scope Gate",
            *_data_scope_gate_lines(data_scope_gate_report),
            "",
            "### Model Adapter Boundary",
            *_model_adapter_lines(model_adapter_report),
            "",
            "### Evidence Completeness",
            *_evidence_completeness_lines(evidence_completeness_report),
            "",
            "### Context Boundary",
            *_context_boundary_lines(context_boundary_report),
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
            *_ingestion_volume_profile_lines(artifact_refs),
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
            *_deadline_docketing_guard_report_lines(artifact_refs, deadline_docketing_guard_report),
            *_lines_or_none(finding_lines),
            *_lines_or_none([f"- budget unknown: {item}" for item in budget.unknowns]),
            "",
            "## Required Human Gates",
            "",
            *_required_human_gate_lines(confirmation, conflict_seed, budget, readiness),
            *_human_gate_status_report_lines(artifact_refs, human_gate_status_report),
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
            *_budget_submission_guard_report_lines(artifact_refs, budget_submission_guard_report),
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
            "### Driver Profile Summary",
            *_budget_driver_profile_summary_lines(budget),
            "",
            "### Scenario Comparison",
            *_budget_scenario_lines(budget),
            "",
            "### Scenario Set",
            *_budget_scenario_lines(budget),
            "",
            "### Budget Driver Effects",
            *_budget_driver_effect_lines(budget),
            "",
            "### Guideline Flags",
            *_budget_guideline_flag_lines(budget),
            "",
            "### Workbook Mapping Status",
            *_budget_workbook_mapping_status_lines(artifact_refs),
            "",
            "### Unresolved Budget Assumptions",
            *_budget_unresolved_assumption_lines(budget),
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
            "### Exception Lake Handoff",
            *(
                [
                    "- Exception Lake handoff manifest: "
                    f"`{artifact_refs['budget_exception_lake_handoff_manifest']}`"
                ]
                if "budget_exception_lake_handoff_manifest" in artifact_refs
                else []
            ),
            *_exception_handoff_lines(exception_handoff_manifest),
            "",
            "### Exception Lake Mapping Package",
            *_exception_mapping_package_lines(artifact_refs),
            "",
            "### Exception Candidate Details",
            *_exception_candidate_detail_lines(exception_candidates),
            "",
            "### Budget Actual Comparison",
            *_budget_actual_comparison_lines(artifact_refs),
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
            *_readiness_blocker_detail_lines(readiness),
            "",
            "## Evidence Graph Summary",
            "",
            *_evidence_graph_lines(artifact_refs, evidence_graph),
            "",
            "## Run Ledger Summary",
            "",
            *_run_ledger_lines(artifact_refs, run_ledger_events or {}),
            "",
            "### Run Ledger Integrity",
            *_run_ledger_integrity_lines(run_ledger_integrity_reports),
            "",
            "## Artifact References",
            "",
            *artifact_lines,
            "",
            "This package does not clear conflicts, accept representation, docket deadlines, open a matter, create an iManage workspace, send communications, submit a budget, or authorize client/carrier delivery.",
            "",
        ]
    )
