from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetActualComparisonReport,
    BudgetActualVarianceLedgerEvent,
    BudgetActualVarianceLedgerReport,
    BudgetActualVarianceOwnerAdoptionCheck,
    BudgetActualVarianceOwnerAdoptionPacket,
    BudgetActualVarianceOwnerAdoptionReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_REPORT_FILENAME = (
    "budget_actual_variance_owner_adoption_report.json"
)
BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_NOTES_FILENAME = (
    "budget_actual_variance_owner_adoption_report.md"
)
BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_PACKETS_FILENAME = (
    "budget_actual_variance_owner_adoption_packets.jsonl"
)
BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_DIRNAME = "budget_actual_variance_owner_packets"

TARGET_REPOS = [
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

BUDGET_ACTUAL_VARIANCE_OWNER_REQUIRED_NEXT_GATES = [
    "human_actual_variance_owner_review",
    "manual_owner_issue_creation_if_desired",
    "owning_repo_triage",
    "owner_repo_implementation_pr_if_accepted",
    "cross_repo_contract_validation_after_owner_changes",
    "no_intake_billing_lake_or_learning_write",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _owner_slug(owner: str) -> str:
    return owner.lower().replace("lawfirm-os-", "").replace("_", "-")


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> BudgetActualVarianceOwnerAdoptionCheck:
    return BudgetActualVarianceOwnerAdoptionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _comparison_boundary_clear(report: BudgetActualComparisonReport) -> bool:
    return (
        report.actuals_are_synthetic is True
        and report.billing_connector_read_performed is False
        and report.billing_connector_write_performed is False
        and report.external_writes_performed is False
        and report.non_authoritative is True
    )


def _event_boundary_clear(event: BudgetActualVarianceLedgerEvent) -> bool:
    return (
        event.append_only is True
        and event.candidate_only is True
        and event.non_authoritative is True
        and event.synthetic_only is True
        and event.not_authorized_for_lake_write is True
        and event.not_authorized_for_sqlite_write is True
        and event.not_authorized_for_external_submission is True
        and event.lake_write_performed is False
        and event.sqlite_write_performed is False
        and event.external_writes_performed is False
        and event.billing_connector_read_performed is False
        and event.billing_connector_write_performed is False
        and event.budget_mutation_performed is False
        and event.profile_mutation_performed is False
        and event.template_mutation_performed is False
        and event.carrier_guideline_mutation_performed is False
        and event.silent_learning_performed is False
    )


def _ledger_boundary_clear(report: BudgetActualVarianceLedgerReport) -> bool:
    return (
        report.candidate_only is True
        and report.non_authoritative is True
        and report.synthetic_only is True
        and report.append_only is True
        and report.not_authorized_for_lake_write is True
        and report.not_authorized_for_sqlite_write is True
        and report.not_authorized_for_external_submission is True
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.billing_connector_read_performed is False
        and report.billing_connector_write_performed is False
        and report.budget_mutation_performed is False
        and report.profile_mutation_performed is False
        and report.template_mutation_performed is False
        and report.carrier_guideline_mutation_performed is False
        and report.silent_learning_performed is False
        and all(_event_boundary_clear(event) for event in report.events)
    )


def _candidate_lake_event_labels(report: BudgetActualVarianceLedgerReport) -> list[str]:
    return sorted({event.local_event_label for event in report.events if event.local_event_label})


def _variance_driver_candidates(
    comparison: BudgetActualComparisonReport,
    ledger: BudgetActualVarianceLedgerReport,
) -> list[str]:
    labels = {driver.driver_label for driver in comparison.variance_driver_candidates}
    for event in ledger.events:
        labels.update(event.variance_driver_candidates)
    return sorted(labels)


def _learning_disposition_candidates(
    comparison: BudgetActualComparisonReport,
    ledger: BudgetActualVarianceLedgerReport,
) -> list[str]:
    labels = set(comparison.learning_disposition_candidates)
    for event in ledger.events:
        labels.update(event.learning_disposition_candidates)
    return sorted(labels)


def _build_checks(
    *,
    comparison: BudgetActualComparisonReport,
    comparison_ref: str,
    ledger: BudgetActualVarianceLedgerReport,
    ledger_ref: str,
) -> list[BudgetActualVarianceOwnerAdoptionCheck]:
    labels = _candidate_lake_event_labels(ledger)
    comparison_refs = [comparison_ref]
    ledger_refs = [ledger_ref]
    all_refs = [comparison_ref, ledger_ref]
    return [
        _check(
            "budget_actual_comparison_without_writes",
            _comparison_boundary_clear(comparison),
            "Budget actual comparison is synthetic, non-authoritative, and has no billing or external writes.",
            artifact_refs=comparison_refs,
        ),
        _check(
            "budget_actual_variance_ledger_without_writes",
            _ledger_boundary_clear(ledger),
            "Budget actual variance ledger and events are append-only candidate evidence with no Lake, SQLite, billing, mutation, or learning side effects.",
            artifact_refs=ledger_refs,
        ),
        _check(
            "budget_actual_variance_ledger_matches_comparison",
            ledger.budget_actual_comparison_report_id
            == comparison.budget_actual_comparison_report_id
            and ledger.run_id == comparison.run_id
            and ledger.preflight_packet_id == comparison.preflight_packet_id
            and ledger.budget_proposal_id == comparison.budget_proposal_id
            and ledger.budget_revision_report_id == comparison.budget_revision_report_id,
            "Ledger lineage matches the source actual comparison report.",
            artifact_refs=all_refs,
        ),
        _check(
            "budget_actual_variance_ledger_events_are_append_only",
            ledger.entry_count == len(ledger.events)
            and all(event.append_only for event in ledger.events),
            "Every variance ledger event is represented as append-only local candidate evidence.",
            artifact_refs=ledger_refs,
        ),
        _check(
            "budget_actual_variance_candidate_labels_present",
            bool(labels),
            "Actual-cost variance or source-followup labels are present for owner review.",
            artifact_refs=ledger_refs,
        ),
        _check(
            "budget_actual_variance_owner_review_signals_present",
            ledger.variance_review_event_count > 0
            or ledger.missing_actuals_event_count > 0
            or ledger.actuals_without_budget_event_count > 0,
            "Ledger contains actual variance, missing-actuals, or actuals-without-budget signals requiring governed owner review.",
            artifact_refs=ledger_refs,
        ),
    ]


def _adoption_focus(owner: str) -> str:
    return {
        "LawFirm-os-semantic-substrate": "semantic_actual_variance_label_review",
        "LawFirm-os-orchestrator": "runtime_billing_actuals_workflow",
        "LawFirm-os-exceptions-lake-runtime": "append_only_actual_variance_lake_admission",
    }[owner]


def _source_artifact_refs(*, comparison_ref: str, ledger_ref: str) -> list[str]:
    return [
        comparison_ref,
        ledger_ref,
        "schemas/budget-actual-comparison-report.schema.json",
        "schemas/budget-actual-variance-ledger-report.schema.json",
        "schemas/budget-actual-variance-ledger-event.schema.json",
    ]


def _candidate_contract_refs(owner: str) -> list[str]:
    refs = {
        "LawFirm-os-semantic-substrate": [
            "semantic-substrate://candidate/event-labels/budget-actual-variance.v0_1",
            "semantic-substrate://candidate/lifecycle-states/budget-actual-followup.v0_1",
            "semantic-substrate://candidate/governed-learning/actual-cost-driver-review.v0_1",
        ],
        "LawFirm-os-orchestrator": [
            "orchestrator://candidate/workflows/budget-actuals-governed-read.v0_1",
            "orchestrator://candidate/human-pauses/budget-actual-variance-review.v0_1",
            "orchestrator://candidate/evidence-packets/budget-actuals-to-lake.v0_1",
            "orchestrator://candidate/connectors/no-billing-read-without-contract.v0_1",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "exception-lake://candidate/admission/budget-actual-variance.v0_1",
            "exception-lake://candidate/admission/budget-actuals-missing-source.v0_1",
            "exception-lake://candidate/admission/budget-actuals-without-budget.v0_1",
            "exception-lake://candidate/admission/budget-actual-human-revision-context.v0_1",
            "exception-lake://candidate/sqlite/budget-actual-variance-idempotency.v0_1",
        ],
    }
    return refs[owner]


def _owner_actions(
    owner: str,
    comparison: BudgetActualComparisonReport,
    ledger: BudgetActualVarianceLedgerReport,
) -> list[str]:
    actions = {
        "LawFirm-os-semantic-substrate": [
            "Review actual-cost variance, missing-actuals, actuals-without-budget, and human-revision context labels as candidate vocabulary only.",
            "Decide whether actual-cost variance lifecycle states belong in canonical substrate contracts after owner review.",
            "Keep observed actual-cost evidence separate from budget-driver learning proposals and human-confirmed outcomes.",
            "Confirm that intake-local labels cannot become canonical Lake event classes from this packet alone.",
        ],
        "LawFirm-os-orchestrator": [
            "Design the governed billing-actuals read boundary before any real matter actuals are supplied to intake comparison.",
            "Track missing-actuals, actuals-without-budget, over-threshold, under-threshold, and human-revision context followups as runtime human pauses.",
            "Assemble evidence packets for Exception Lake owner review with comparison report hash, ledger hash, event IDs, source refs, and human outcome refs.",
            "Keep billing reads, billing writes, budget submissions, appeals, carrier portal actions, and learning updates impossible without separate authority.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Design append-only record families for actual-cost variance, missing actuals, actuals without budget, and revised-budget comparison context.",
            "Define idempotency keys from comparison report ID, ledger event ID, budget proposal ID, phase/code scope, and actuals source ref.",
            "Define record hashes, support hashes, source artifact hashes, correction records, and supersession rules for actual-cost events.",
            "Decide SQLite tables and migrations inside Exception Lake runtime only after owner review.",
        ],
    }
    if ledger.missing_actuals_event_count:
        actions["LawFirm-os-orchestrator"].append(
            f"Route {ledger.missing_actuals_event_count} missing-actuals event(s) to a governed source-followup queue before comparison is treated as complete."
        )
        actions["LawFirm-os-exceptions-lake-runtime"].append(
            "Represent missing actuals as source-availability evidence, not as a cost variance or learning signal."
        )
    if ledger.actuals_without_budget_event_count:
        actions["LawFirm-os-semantic-substrate"].append(
            "Review actuals-without-budget as a distinct candidate class from ordinary over-budget variance."
        )
        actions["LawFirm-os-exceptions-lake-runtime"].append(
            "Require zero-budget/positive-actual events to preserve phase/code scope and budget lineage for later correction or mapping review."
        )
    if ledger.variance_review_event_count:
        actions["LawFirm-os-orchestrator"].append(
            f"Track {ledger.variance_review_event_count} variance review event(s) until human disposition is recorded append-only."
        )
    if comparison.comparison_budget_state == "human_revised_candidate":
        actions["LawFirm-os-orchestrator"].append(
            "Preserve original-proposal and human-revised comparison states so actuals are not evaluated against the wrong budget baseline."
        )
        actions["LawFirm-os-exceptions-lake-runtime"].append(
            "Link actual-variance admission records to the human budget revision report when the comparison uses a revised candidate budget."
        )
    return actions[owner]


def _acceptance_checks(owner: str) -> list[str]:
    checks = {
        "LawFirm-os-semantic-substrate": [
            "No canonical event class, route ID, lifecycle state, or controlled vocabulary is created from intake-local actual variance packets.",
            "Actual-cost labels remain distinguishable from budget proposals, approved budgets, billing records, appeal results, and admitted Lake records.",
            "Learning disposition cannot mutate profiles, templates, rates, budgets, or guidelines without reviewed promotion.",
        ],
        "LawFirm-os-orchestrator": [
            "Future real actuals enter intake only through a governed read boundary and typed evidence packet.",
            "Every actual variance followup has a human pause, owner, timeout/escalation policy, and append-only outcome state.",
            "Evidence packets can be rebuilt deterministically from comparison report, variance ledger, actuals source refs, and human outcomes.",
            "Retries, duplicate actuals, revised budgets, and missing source rows cannot double-count variance outcomes.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Admission validates idempotency, support hashes, source hashes, record hashes, and append-only supersession.",
            "SQLite schema and migrations are owned only by Exception Lake runtime.",
            "Missing actuals, actuals-without-budget, and human-revision context are stored as distinct record families or typed states.",
            "No raw legal payload, real client data, or production billing payload is required for candidate admission review.",
        ],
    }
    return checks[owner]


def _red_team_notes(owner: str) -> list[str]:
    notes = {
        "LawFirm-os-semantic-substrate": [
            "Variance labels can look objective even when the source actuals are incomplete or mapped to the wrong phase.",
            "Actuals-without-budget should not be collapsed into ordinary overrun semantics; it can indicate template, scope, or billing-code mismatch.",
        ],
        "LawFirm-os-orchestrator": [
            "The highest-risk failure is reading production billing data without a governed contract and treating it as authorized intake evidence.",
            "A human-revised budget baseline can make variance look smaller or larger; runtime needs to preserve which baseline was used.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "The largest Lake risk is double-counting phase and code events as separate financial outcomes without explicit scope and idempotency.",
            "Missing actuals are evidence of an incomplete source chain, not evidence that a budget was accurate.",
        ],
    }
    return notes[owner]


def build_budget_actual_variance_owner_adoption_packets(
    *,
    comparison: BudgetActualComparisonReport,
    comparison_ref: str,
    ledger: BudgetActualVarianceLedgerReport,
    ledger_ref: str,
    checks: list[BudgetActualVarianceOwnerAdoptionCheck],
) -> list[BudgetActualVarianceOwnerAdoptionPacket]:
    ready = not any(check.status == "failed" for check in checks)
    source_refs = _source_artifact_refs(comparison_ref=comparison_ref, ledger_ref=ledger_ref)
    labels = _candidate_lake_event_labels(ledger)
    drivers = _variance_driver_candidates(comparison, ledger)
    learning = _learning_disposition_candidates(comparison, ledger)
    packets: list[BudgetActualVarianceOwnerAdoptionPacket] = []
    for owner in TARGET_REPOS:
        packets.append(
            BudgetActualVarianceOwnerAdoptionPacket(
                owner_adoption_packet_id=_stable_id(
                    "budgetactualownerpacket",
                    f"{comparison.budget_actual_comparison_report_id}|{ledger.budget_actual_variance_ledger_report_id}|{owner}",
                ),
                target_repo=owner,  # type: ignore[arg-type]
                adoption_focus=_adoption_focus(owner),  # type: ignore[arg-type]
                status=(
                    "ready_for_owner_review" if ready else "blocked_by_actual_variance_evidence"
                ),
                source_budget_actual_comparison_report_id=(
                    comparison.budget_actual_comparison_report_id
                ),
                source_budget_actual_comparison_report_ref=comparison_ref,
                source_budget_actual_comparison_status=comparison.status,
                source_budget_actual_variance_ledger_report_id=(
                    ledger.budget_actual_variance_ledger_report_id
                ),
                source_budget_actual_variance_ledger_report_ref=ledger_ref,
                source_budget_actual_variance_ledger_status=ledger.status,
                run_id=comparison.run_id,
                preflight_packet_id=comparison.preflight_packet_id,
                budget_proposal_id=comparison.budget_proposal_id,
                budget_revision_report_id=comparison.budget_revision_report_id,
                actuals_source_ref=comparison.actuals_source_ref,
                comparison_scope=comparison.comparison_scope,
                comparison_budget_state=comparison.comparison_budget_state,
                actual_resolution_scenario_id=comparison.actual_resolution_scenario_id,
                entry_count=ledger.entry_count,
                phase_event_count=ledger.phase_event_count,
                code_event_count=ledger.code_event_count,
                revision_context_event_count=ledger.revision_context_event_count,
                variance_review_event_count=ledger.variance_review_event_count,
                missing_actuals_event_count=ledger.missing_actuals_event_count,
                actuals_without_budget_event_count=ledger.actuals_without_budget_event_count,
                within_threshold_event_count=ledger.within_threshold_event_count,
                total_budgeted=ledger.total_budgeted,
                total_actual=ledger.total_actual,
                total_variance_amount=ledger.total_variance_amount,
                total_variance_percent=ledger.total_variance_percent,
                candidate_lake_event_labels=labels,
                variance_driver_candidates=drivers,
                learning_disposition_candidates=learning,
                source_artifact_refs=source_refs,
                candidate_contract_refs=_candidate_contract_refs(owner),
                required_owner_actions=_owner_actions(owner, comparison, ledger),
                acceptance_checks=_acceptance_checks(owner),
                red_team_notes=_red_team_notes(owner),
                required_next_gates=BUDGET_ACTUAL_VARIANCE_OWNER_REQUIRED_NEXT_GATES,
            )
        )
    return packets


def build_budget_actual_variance_owner_adoption_report(
    *,
    comparison: BudgetActualComparisonReport,
    comparison_ref: str,
    ledger: BudgetActualVarianceLedgerReport,
    ledger_ref: str,
    packets: list[BudgetActualVarianceOwnerAdoptionPacket],
    packet_output_refs: list[str],
    checks: list[BudgetActualVarianceOwnerAdoptionCheck],
) -> BudgetActualVarianceOwnerAdoptionReport:
    ready_count = sum(1 for packet in packets if packet.status == "ready_for_owner_review")
    blocked_count = len(packets) - ready_count
    return BudgetActualVarianceOwnerAdoptionReport(
        owner_adoption_report_id=_stable_id(
            "budgetactualownerreport",
            f"{comparison.budget_actual_comparison_report_id}|{ledger.budget_actual_variance_ledger_report_id}|{comparison_ref}|{ledger_ref}",
        ),
        status=(
            "budget_actual_variance_owner_adoption_packets_ready"
            if blocked_count == 0
            else "blocked_by_budget_actual_variance_evidence"
        ),
        source_budget_actual_comparison_report_id=comparison.budget_actual_comparison_report_id,
        source_budget_actual_comparison_report_ref=comparison_ref,
        source_budget_actual_comparison_status=comparison.status,
        source_budget_actual_variance_ledger_report_id=(
            ledger.budget_actual_variance_ledger_report_id
        ),
        source_budget_actual_variance_ledger_report_ref=ledger_ref,
        source_budget_actual_variance_ledger_status=ledger.status,
        target_repo_count=len(TARGET_REPOS),
        packet_count=len(packets),
        ready_packet_count=ready_count,
        blocked_packet_count=blocked_count,
        target_repos=TARGET_REPOS,  # type: ignore[arg-type]
        packets=packets,
        packet_output_refs=packet_output_refs,
        checks=checks,
        entry_count=ledger.entry_count,
        variance_review_event_count=ledger.variance_review_event_count,
        missing_actuals_event_count=ledger.missing_actuals_event_count,
        actuals_without_budget_event_count=ledger.actuals_without_budget_event_count,
        within_threshold_event_count=ledger.within_threshold_event_count,
        total_budgeted=ledger.total_budgeted,
        total_actual=ledger.total_actual,
        total_variance_amount=ledger.total_variance_amount,
        candidate_lake_event_labels=_candidate_lake_event_labels(ledger),
        variance_driver_candidates=_variance_driver_candidates(comparison, ledger),
        learning_disposition_candidates=_learning_disposition_candidates(comparison, ledger),
        required_next_gates=BUDGET_ACTUAL_VARIANCE_OWNER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_actual_variance_owner_adoption_packet(
    packet: BudgetActualVarianceOwnerAdoptionPacket,
) -> str:
    lines = [
        "# Budget Actual Variance Owner Packet",
        "",
        f"**Packet ID:** {packet.owner_adoption_packet_id}",
        f"**Target repo:** {packet.target_repo}",
        f"**Focus:** {packet.adoption_focus}",
        f"**Status:** {packet.status}",
        "",
        "## Source Evidence",
        "",
        f"- Actual comparison report: `{packet.source_budget_actual_comparison_report_ref}`",
        f"- Actual comparison status: {packet.source_budget_actual_comparison_status}",
        f"- Variance ledger report: `{packet.source_budget_actual_variance_ledger_report_ref}`",
        f"- Variance ledger status: {packet.source_budget_actual_variance_ledger_status}",
        f"- Budget proposal: {packet.budget_proposal_id}",
        f"- Budget revision report: {packet.budget_revision_report_id or 'none'}",
        f"- Actuals source: {packet.actuals_source_ref or 'none'}",
        "",
        "## Variance Summary",
        "",
        f"- Comparison scope: {packet.comparison_scope}",
        f"- Comparison budget state: {packet.comparison_budget_state}",
        f"- Actual resolution scenario: {packet.actual_resolution_scenario_id or 'none'}",
        f"- Ledger events: {packet.entry_count}",
        f"- Phase events: {packet.phase_event_count}",
        f"- Code events: {packet.code_event_count}",
        f"- Human-revision context events: {packet.revision_context_event_count}",
        f"- Variance review events: {packet.variance_review_event_count}",
        f"- Missing actuals events: {packet.missing_actuals_event_count}",
        f"- Actuals-without-budget events: {packet.actuals_without_budget_event_count}",
        f"- Within-threshold events: {packet.within_threshold_event_count}",
        f"- Budgeted total: {packet.total_budgeted}",
        f"- Actual total: {packet.total_actual}",
        f"- Variance amount: {packet.total_variance_amount}",
        f"- Variance percent: {packet.total_variance_percent}",
        "",
        "## Candidate Lake Event Labels",
        "",
    ]
    if not packet.candidate_lake_event_labels:
        lines.append("- No candidate labels recorded.")
    for label in packet.candidate_lake_event_labels:
        lines.append(f"- `{label}`")
    lines.extend(
        [
            "",
            "## Variance Driver Candidates",
            "",
        ]
    )
    if not packet.variance_driver_candidates:
        lines.append("- No variance driver candidates recorded.")
    for driver in packet.variance_driver_candidates:
        lines.append(f"- `{driver}`")
    lines.extend(
        [
            "",
            "## Learning Disposition Candidates",
            "",
        ]
    )
    if not packet.learning_disposition_candidates:
        lines.append("- No learning disposition candidates recorded.")
    for disposition in packet.learning_disposition_candidates:
        lines.append(f"- `{disposition}`")
    lines.extend(
        [
            "",
            "## Candidate Contract Refs",
            "",
            *(f"- `{ref}`" for ref in packet.candidate_contract_refs),
            "",
            "## Required Owner Actions",
            "",
            *(f"- [ ] {action}" for action in packet.required_owner_actions),
            "",
            "## Acceptance Checks",
            "",
            *(f"- [ ] {check}" for check in packet.acceptance_checks),
            "",
            "## Red-Team Notes",
            "",
            *(f"- {note}" for note in packet.red_team_notes),
            "",
            "## Boundary",
            "",
            f"- GitHub issue created: {packet.github_issue_created}",
            f"- Sibling repo write performed: {packet.sibling_repo_write_performed}",
            f"- Promotion authorized: {packet.promotion_authorized}",
            f"- Billing connector read performed: {packet.billing_connector_read_performed}",
            f"- Lake write performed: {packet.lake_write_performed}",
            f"- SQLite write performed: {packet.sqlite_write_performed}",
            f"- Budget mutation performed: {packet.budget_mutation_performed}",
            f"- Silent learning performed: {packet.silent_learning_performed}",
            "",
            "This packet is owner-review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, read/write billing systems, admit Lake/SQLite records, mutate budgets/profiles/templates/guidelines, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def render_budget_actual_variance_owner_adoption_report(
    report: BudgetActualVarianceOwnerAdoptionReport,
) -> str:
    lines = [
        "# Budget Actual Variance Owner Adoption Report",
        "",
        f"**Report ID:** {report.owner_adoption_report_id}",
        f"**Status:** {report.status}",
        f"**Actual comparison report:** `{report.source_budget_actual_comparison_report_ref}`",
        f"**Variance ledger report:** `{report.source_budget_actual_variance_ledger_report_ref}`",
        "",
        "## Packets",
        "",
        f"- Ready packets: {report.ready_packet_count}",
        f"- Blocked packets: {report.blocked_packet_count}",
        f"- Target repos: {', '.join(report.target_repos)}",
        "",
        "## Variance Summary",
        "",
        f"- Ledger events: {report.entry_count}",
        f"- Variance review events: {report.variance_review_event_count}",
        f"- Missing actuals events: {report.missing_actuals_event_count}",
        f"- Actuals-without-budget events: {report.actuals_without_budget_event_count}",
        f"- Within-threshold events: {report.within_threshold_event_count}",
        f"- Budgeted total: {report.total_budgeted}",
        f"- Actual total: {report.total_actual}",
        f"- Variance amount: {report.total_variance_amount}",
        "",
        "## Candidate Lake Event Labels",
        "",
    ]
    if not report.candidate_lake_event_labels:
        lines.append("- No candidate labels recorded.")
    for label in report.candidate_lake_event_labels:
        lines.append(f"- `{label}`")
    lines.extend(
        [
            "",
            "## Checks",
            "",
        ]
    )
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary",
            "",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Billing connector read performed: {report.billing_connector_read_performed}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- Budget mutation performed: {report.budget_mutation_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report prepares manual owner review packets only. Intake does not create issues, open PRs, write sibling repos, promote canon, read/write billing systems, admit Lake/SQLite records, mutate budgets/profiles/templates/guidelines, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_actual_variance_owner_adoption(
    *,
    budget_actual_comparison_report_path: str | Path,
    budget_actual_variance_ledger_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetActualVarianceOwnerAdoptionReport, Path]:
    comparison_path = Path(budget_actual_comparison_report_path)
    ledger_path = Path(budget_actual_variance_ledger_report_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet_dir = run_dir / BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)

    comparison = BudgetActualComparisonReport.model_validate(load_json(comparison_path))
    ledger = BudgetActualVarianceLedgerReport.model_validate(load_json(ledger_path))
    checks = _build_checks(
        comparison=comparison,
        comparison_ref=str(comparison_path),
        ledger=ledger,
        ledger_ref=str(ledger_path),
    )
    packets = build_budget_actual_variance_owner_adoption_packets(
        comparison=comparison,
        comparison_ref=str(comparison_path),
        ledger=ledger,
        ledger_ref=str(ledger_path),
        checks=checks,
    )

    packets_jsonl = run_dir / BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_PACKETS_FILENAME
    if packets_jsonl.exists():
        packets_jsonl.unlink()
    packet_refs = []
    for packet in packets:
        slug = _owner_slug(packet.target_repo)
        packet_json = packet_dir / f"{slug}.budget_actual_variance_owner_packet.json"
        packet_md = packet_dir / f"{slug}.budget_actual_variance_owner_packet.md"
        write_json(packet_json, packet.model_dump(mode="json"))
        packet_md.write_text(
            render_budget_actual_variance_owner_adoption_packet(packet),
            encoding="utf-8",
        )
        append_jsonl(packets_jsonl, packet.model_dump(mode="json"))
        packet_refs.append(str(packet_json))

    adoption_report = build_budget_actual_variance_owner_adoption_report(
        comparison=comparison,
        comparison_ref=str(comparison_path),
        ledger=ledger,
        ledger_ref=str(ledger_path),
        packets=packets,
        packet_output_refs=packet_refs,
        checks=checks,
    )
    write_json(
        run_dir / BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_REPORT_FILENAME,
        adoption_report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_ACTUAL_VARIANCE_OWNER_ADOPTION_NOTES_FILENAME).write_text(
        render_budget_actual_variance_owner_adoption_report(adoption_report),
        encoding="utf-8",
    )
    return adoption_report, run_dir
