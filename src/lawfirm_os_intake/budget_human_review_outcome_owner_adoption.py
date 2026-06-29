from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetHumanReviewOutcomeOwnerAdoptionCheck,
    BudgetHumanReviewOutcomeOwnerAdoptionPacket,
    BudgetHumanReviewOutcomeOwnerAdoptionReport,
    BudgetHumanReviewOutcomeRecord,
    BudgetHumanReviewOutcomeReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_REPORT_FILENAME = (
    "budget_human_review_outcome_owner_adoption_report.json"
)
BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_NOTES_FILENAME = (
    "budget_human_review_outcome_owner_adoption_report.md"
)
BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_PACKETS_FILENAME = (
    "budget_human_review_outcome_owner_adoption_packets.jsonl"
)
BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_DIRNAME = "budget_human_review_outcome_owner_packets"

READY_OUTCOME_STATUS = "budget_human_review_outcome_recorded"

TARGET_REPOS = [
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

BUDGET_OUTCOME_OWNER_REQUIRED_NEXT_GATES = [
    "human_budget_outcome_owner_review",
    "manual_owner_issue_creation_if_desired",
    "owning_repo_triage",
    "owner_repo_implementation_pr_if_accepted",
    "cross_repo_contract_validation_after_owner_changes",
    "no_intake_external_action_or_lake_admission",
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
) -> BudgetHumanReviewOutcomeOwnerAdoptionCheck:
    return BudgetHumanReviewOutcomeOwnerAdoptionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _report_boundary_clear(report: BudgetHumanReviewOutcomeReport) -> bool:
    return (
        report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.billing_connector_write_performed is False
        and report.carrier_portal_write_performed is False
        and report.email_send_performed is False
        and report.appeal_submission_performed is False
        and report.budget_submission_performed is False
        and report.budget_mutation_performed is False
        and report.profile_mutation_performed is False
        and report.template_mutation_performed is False
        and report.carrier_guideline_mutation_performed is False
        and report.silent_learning_performed is False
    )


def _record_boundary_clear(record: BudgetHumanReviewOutcomeRecord) -> bool:
    return (
        record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.billing_connector_write_performed is False
        and record.carrier_portal_write_performed is False
        and record.email_send_performed is False
        and record.appeal_submission_performed is False
        and record.budget_submission_performed is False
        and record.budget_mutation_performed is False
        and record.profile_mutation_performed is False
        and record.template_mutation_performed is False
        and record.carrier_guideline_mutation_performed is False
        and record.silent_learning_performed is False
    )


def _build_checks(
    *,
    outcome_report: BudgetHumanReviewOutcomeReport,
    outcome_report_ref: str,
    outcome_record: BudgetHumanReviewOutcomeRecord,
    outcome_record_ref: str,
) -> list[BudgetHumanReviewOutcomeOwnerAdoptionCheck]:
    report_checks_failed = [
        check.check_id for check in outcome_report.checks if check.status == "failed"
    ]
    return [
        _check(
            "budget_human_review_outcome_report_ready_without_writes",
            outcome_report.status == READY_OUTCOME_STATUS
            and not report_checks_failed
            and _report_boundary_clear(outcome_report),
            "Budget human review outcome report is recorded and has no side effects.",
            artifact_refs=[outcome_report_ref],
            blocking_refs=report_checks_failed,
        ),
        _check(
            "budget_human_review_outcome_record_matches_report",
            outcome_record.budget_human_review_outcome_record_id
            == outcome_report.budget_human_review_outcome_record_id
            and outcome_record.budget_human_review_packet_id
            == outcome_report.budget_human_review_packet_id,
            "Outcome record ID and packet ID match the outcome report.",
            artifact_refs=[outcome_report_ref, outcome_record_ref],
        ),
        _check(
            "budget_human_review_outcome_record_without_writes",
            _record_boundary_clear(outcome_record),
            "Budget human review outcome record has no external, Lake, SQLite, submission, mutation, or learning side effects.",
            artifact_refs=[outcome_record_ref],
        ),
        _check(
            "budget_human_review_outcome_followups_preserved",
            set(outcome_report.required_followups).issubset(
                {
                    followup
                    for decision in outcome_record.decisions
                    for followup in decision.required_followups
                }
            ),
            "Required followups in the report are present in the append-only outcome record.",
            artifact_refs=[outcome_report_ref, outcome_record_ref],
        ),
        _check(
            "budget_human_review_outcome_candidate_labels_present",
            bool(outcome_report.candidate_lake_event_labels),
            "Outcome report carries candidate Lake event labels for owner review.",
            artifact_refs=[outcome_report_ref],
        ),
    ]


def _adoption_focus(owner: str) -> str:
    return {
        "LawFirm-os-semantic-substrate": "semantic_outcome_label_review",
        "LawFirm-os-orchestrator": "runtime_action_followup_workflow",
        "LawFirm-os-exceptions-lake-runtime": "append_only_outcome_lake_admission",
    }[owner]


def _source_artifact_refs(
    *,
    outcome_report_ref: str,
    outcome_record_ref: str,
) -> list[str]:
    return [
        outcome_report_ref,
        outcome_record_ref,
        "schemas/budget-human-review-outcome-report.schema.json",
        "schemas/budget-human-review-outcome-record.schema.json",
        "schemas/budget-human-review-outcome-decision.schema.json",
        "schemas/budget-human-review-packet.schema.json",
    ]


def _candidate_contract_refs(owner: str) -> list[str]:
    refs = {
        "LawFirm-os-semantic-substrate": [
            "semantic-substrate://candidate/event-labels/budget-human-review-outcome.v0_1",
            "semantic-substrate://candidate/lifecycle-states/budget-outcome-followup.v0_1",
            "semantic-substrate://candidate/promotion-policy/no-silent-budget-learning.v0_1",
        ],
        "LawFirm-os-orchestrator": [
            "orchestrator://candidate/workflows/budget-human-review-outcome-followup.v0_1",
            "orchestrator://candidate/human-pauses/budget-appeal-writeoff-correction.v0_1",
            "orchestrator://candidate/evidence-packets/budget-outcome-to-lake.v0_1",
            "orchestrator://candidate/connectors/no-budget-or-appeal-submit-without-human-auth.v0_1",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "exception-lake://candidate/admission/budget-human-review-outcome.v0_1",
            "exception-lake://candidate/admission/budget-correction-followup.v0_1",
            "exception-lake://candidate/admission/carrier-appeal-followup.v0_1",
            "exception-lake://candidate/admission/carrier-financial-writeoff.v0_1",
            "exception-lake://candidate/admission/budget-learning-no-change.v0_1",
        ],
    }
    return refs[owner]


def _owner_actions(owner: str, report: BudgetHumanReviewOutcomeReport) -> list[str]:
    actions = {
        "LawFirm-os-semantic-substrate": [
            "Review outcome labels, follow-up states, and no-learning decisions as candidate vocabulary only.",
            "Decide whether any budget human-review outcome labels deserve canonical event-class or lifecycle-state promotion.",
            "Keep correction, appeal, write-off, owner-routing, and learning-disposition semantics distinct.",
            "Confirm that candidate Lake event labels do not become canonical from intake-local evidence alone.",
        ],
        "LawFirm-os-orchestrator": [
            "Design runtime human pauses for budget correction, actual-variance follow-up, appeal authorization, write-off confirmation, and learning disposition.",
            "Track required followups from the append-only outcome record until a human or owning workflow resolves them.",
            "Assemble evidence packets for Exception Lake owner review with outcome record hash, packet hash, reviewer identity, and decision refs.",
            "Keep budget submission, appeal submission, carrier portal writes, email sends, and billing connector writes impossible without separate human authorization.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Design append-only record families for budget human-review outcomes, correction followups, appeal followups, write-off outcomes, owner-routing, and no-learning decisions.",
            "Define idempotency keys from outcome record ID, decision ID, packet ID, reviewed_at, and supersession ID.",
            "Define record hashes, support hashes, source artifact hashes, correction records, and supersession rules.",
            "Decide SQLite tables and migrations inside Exception Lake runtime only after owner review.",
        ],
    }
    if report.appeal_decision_count:
        actions["LawFirm-os-orchestrator"].append(
            "Add an appeal-follow-up state that separates appeal recommendation, human authorization, submitted appeal, and appeal result."
        )
        actions["LawFirm-os-exceptions-lake-runtime"].append(
            "Require a separate submitted-appeal or appeal-result record before treating an appeal follow-up as externally acted on."
        )
    if report.write_off_decision_count:
        actions["LawFirm-os-exceptions-lake-runtime"].append(
            "Require financial amount, reviewer, support refs, and supersession semantics for write-off records."
        )
    if report.unresolved_followup_count:
        actions["LawFirm-os-orchestrator"].append(
            f"Track {report.unresolved_followup_count} unresolved follow-up(s) before any downstream closeout or learning gate."
        )
    return actions[owner]


def _acceptance_checks(owner: str) -> list[str]:
    checks = {
        "LawFirm-os-semantic-substrate": [
            "No canonical event class, route ID, lifecycle state, or controlled vocabulary is created from intake-local outcome packets.",
            "Outcome labels remain distinguishable from budget proposals, approved budgets, appeal submissions, and admitted Lake records.",
            "Learning disposition cannot mutate profiles, templates, rates, budgets, or guidelines without reviewed promotion.",
        ],
        "LawFirm-os-orchestrator": [
            "Every external action has a human authorization gate and a separately logged runtime state.",
            "Follow-up resolution is append-only and preserves reviewer, decision ID, source packet, hashes, and supersession refs.",
            "Evidence packets can be rebuilt deterministically from outcome record, packet, and source artifacts.",
            "Retries and duplicate carrier responses do not double-count appeals, write-offs, or actual variance outcomes.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Admission validates idempotency, support hashes, source hashes, record hashes, and append-only supersession.",
            "SQLite schema and migrations are owned only by Exception Lake runtime.",
            "Intake outcome records remain candidate evidence until admitted by the Lake owner.",
            "No raw legal payload, real client data, or production connector payload is required for candidate admission review.",
        ],
    }
    return checks[owner]


def _red_team_notes(owner: str) -> list[str]:
    notes = {
        "LawFirm-os-semantic-substrate": [
            "A consistent local label can look canonical; promotion still requires substrate governance.",
            "No-learning decisions are important evidence and should not be silently ignored by future learning loops.",
        ],
        "LawFirm-os-orchestrator": [
            "The largest risk is confusing a reviewer recommendation to appeal with authority to submit an appeal.",
            "Follow-up queues can become stale unless Orchestrator owns state transitions and timeout/escalation policy.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "The largest risk is double-counting the same human decision across outcome, appeal, and financial records.",
            "Write-offs and recovered amounts can become misleading without explicit supersession and actual-cost comparison links.",
        ],
    }
    return notes[owner]


def build_budget_human_review_outcome_owner_adoption_packets(
    *,
    outcome_report: BudgetHumanReviewOutcomeReport,
    outcome_report_ref: str,
    outcome_record: BudgetHumanReviewOutcomeRecord,
    outcome_record_ref: str,
    checks: list[BudgetHumanReviewOutcomeOwnerAdoptionCheck],
) -> list[BudgetHumanReviewOutcomeOwnerAdoptionPacket]:
    ready = outcome_report.status == READY_OUTCOME_STATUS and not any(
        check.status == "failed" for check in checks
    )
    source_refs = _source_artifact_refs(
        outcome_report_ref=outcome_report_ref,
        outcome_record_ref=outcome_record_ref,
    )
    packets: list[BudgetHumanReviewOutcomeOwnerAdoptionPacket] = []
    for owner in TARGET_REPOS:
        packets.append(
            BudgetHumanReviewOutcomeOwnerAdoptionPacket(
                owner_adoption_packet_id=_stable_id(
                    "budgetoutcomeownerpacket",
                    f"{outcome_report.budget_human_review_outcome_report_id}|{owner}",
                ),
                target_repo=owner,  # type: ignore[arg-type]
                adoption_focus=_adoption_focus(owner),  # type: ignore[arg-type]
                status=("ready_for_owner_review" if ready else "blocked_by_outcome_evidence"),
                source_budget_human_review_outcome_report_id=(
                    outcome_report.budget_human_review_outcome_report_id
                ),
                source_budget_human_review_outcome_report_ref=outcome_report_ref,
                source_budget_human_review_outcome_record_id=(
                    outcome_report.budget_human_review_outcome_record_id
                ),
                source_budget_human_review_outcome_record_ref=outcome_record_ref,
                source_budget_human_review_packet_id=(outcome_report.budget_human_review_packet_id),
                source_budget_human_review_outcome_status=outcome_report.status,
                overall_outcome=outcome_report.overall_outcome,
                decision_count=outcome_report.decision_count,
                appeal_decision_count=outcome_report.appeal_decision_count,
                write_off_decision_count=outcome_report.write_off_decision_count,
                correction_decision_count=outcome_report.correction_decision_count,
                route_to_owner_decision_count=outcome_report.route_to_owner_decision_count,
                no_learning_change_decision_count=(
                    outcome_report.no_learning_change_decision_count
                ),
                unresolved_followup_count=outcome_report.unresolved_followup_count,
                candidate_lake_event_labels=outcome_report.candidate_lake_event_labels,
                required_followups=outcome_report.required_followups,
                source_artifact_refs=source_refs,
                candidate_contract_refs=_candidate_contract_refs(owner),
                required_owner_actions=_owner_actions(owner, outcome_report),
                acceptance_checks=_acceptance_checks(owner),
                red_team_notes=_red_team_notes(owner),
                required_next_gates=BUDGET_OUTCOME_OWNER_REQUIRED_NEXT_GATES,
            )
        )
    return packets


def build_budget_human_review_outcome_owner_adoption_report(
    *,
    outcome_report: BudgetHumanReviewOutcomeReport,
    outcome_report_ref: str,
    outcome_record: BudgetHumanReviewOutcomeRecord,
    outcome_record_ref: str,
    packets: list[BudgetHumanReviewOutcomeOwnerAdoptionPacket],
    packet_output_refs: list[str],
    checks: list[BudgetHumanReviewOutcomeOwnerAdoptionCheck],
) -> BudgetHumanReviewOutcomeOwnerAdoptionReport:
    ready_count = sum(1 for packet in packets if packet.status == "ready_for_owner_review")
    blocked_count = len(packets) - ready_count
    return BudgetHumanReviewOutcomeOwnerAdoptionReport(
        owner_adoption_report_id=_stable_id(
            "budgetoutcomeownerreport",
            f"{outcome_report.budget_human_review_outcome_report_id}|{outcome_report_ref}|{outcome_record_ref}",
        ),
        status=(
            "budget_outcome_owner_adoption_packets_ready"
            if blocked_count == 0
            else "blocked_by_budget_outcome_evidence"
        ),
        source_budget_human_review_outcome_report_id=(
            outcome_report.budget_human_review_outcome_report_id
        ),
        source_budget_human_review_outcome_report_ref=outcome_report_ref,
        source_budget_human_review_outcome_record_id=(
            outcome_record.budget_human_review_outcome_record_id
        ),
        source_budget_human_review_outcome_record_ref=outcome_record_ref,
        source_budget_human_review_packet_id=outcome_report.budget_human_review_packet_id,
        source_budget_human_review_outcome_status=outcome_report.status,
        target_repo_count=len(TARGET_REPOS),
        packet_count=len(packets),
        ready_packet_count=ready_count,
        blocked_packet_count=blocked_count,
        target_repos=TARGET_REPOS,  # type: ignore[arg-type]
        packets=packets,
        packet_output_refs=packet_output_refs,
        checks=checks,
        candidate_lake_event_labels=outcome_report.candidate_lake_event_labels,
        required_followups=outcome_report.required_followups,
        required_next_gates=BUDGET_OUTCOME_OWNER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_human_review_outcome_owner_adoption_packet(
    packet: BudgetHumanReviewOutcomeOwnerAdoptionPacket,
) -> str:
    lines = [
        "# Budget Human Review Outcome Owner Packet",
        "",
        f"**Packet ID:** {packet.owner_adoption_packet_id}",
        f"**Target repo:** {packet.target_repo}",
        f"**Focus:** {packet.adoption_focus}",
        f"**Status:** {packet.status}",
        "",
        "## Source Evidence",
        "",
        f"- Outcome report: `{packet.source_budget_human_review_outcome_report_ref}`",
        f"- Outcome record: `{packet.source_budget_human_review_outcome_record_ref}`",
        f"- Outcome status: {packet.source_budget_human_review_outcome_status}",
        f"- Human review packet: {packet.source_budget_human_review_packet_id}",
        f"- Overall outcome: {packet.overall_outcome}",
        "",
        "## Decision Summary",
        "",
        f"- Decisions: {packet.decision_count}",
        f"- Corrections: {packet.correction_decision_count}",
        f"- Appeals: {packet.appeal_decision_count}",
        f"- Write-offs: {packet.write_off_decision_count}",
        f"- Owner routes: {packet.route_to_owner_decision_count}",
        f"- No-learning decisions: {packet.no_learning_change_decision_count}",
        f"- Unresolved followups: {packet.unresolved_followup_count}",
        "",
        "## Candidate Lake Event Labels",
        "",
        *(f"- `{label}`" for label in packet.candidate_lake_event_labels),
        "",
        "## Required Followups",
        "",
    ]
    if not packet.required_followups:
        lines.append("- No required followups recorded.")
    for followup in packet.required_followups:
        lines.append(f"- [ ] {followup}")
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
            f"- Lake write performed: {packet.lake_write_performed}",
            f"- SQLite write performed: {packet.sqlite_write_performed}",
            f"- Budget submission performed: {packet.budget_submission_performed}",
            f"- Appeal submission performed: {packet.appeal_submission_performed}",
            f"- Silent learning performed: {packet.silent_learning_performed}",
            "",
            "This packet is owner-review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, submit budgets or appeals, mutate budgets/profiles/templates/guidelines, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def render_budget_human_review_outcome_owner_adoption_report(
    report: BudgetHumanReviewOutcomeOwnerAdoptionReport,
) -> str:
    lines = [
        "# Budget Human Review Outcome Owner Adoption Report",
        "",
        f"**Report ID:** {report.owner_adoption_report_id}",
        f"**Status:** {report.status}",
        f"**Outcome report:** `{report.source_budget_human_review_outcome_report_ref}`",
        f"**Outcome record:** `{report.source_budget_human_review_outcome_record_ref}`",
        "",
        "## Packets",
        "",
        f"- Ready packets: {report.ready_packet_count}",
        f"- Blocked packets: {report.blocked_packet_count}",
        f"- Target repos: {', '.join(report.target_repos)}",
        "",
        "## Checks",
        "",
    ]
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
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- Budget submission performed: {report.budget_submission_performed}",
            f"- Appeal submission performed: {report.appeal_submission_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report prepares manual owner review packets only. Intake does not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, submit budgets or appeals, mutate budgets/profiles/templates/guidelines, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_human_review_outcome_owner_adoption(
    *,
    budget_human_review_outcome_report_path: str | Path,
    budget_human_review_outcome_record_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetHumanReviewOutcomeOwnerAdoptionReport, Path]:
    report_path = Path(budget_human_review_outcome_report_path)
    record_path = Path(budget_human_review_outcome_record_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet_dir = run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)
    outcome_report = BudgetHumanReviewOutcomeReport.model_validate(load_json(report_path))
    outcome_record = BudgetHumanReviewOutcomeRecord.model_validate(load_json(record_path))
    checks = _build_checks(
        outcome_report=outcome_report,
        outcome_report_ref=str(report_path),
        outcome_record=outcome_record,
        outcome_record_ref=str(record_path),
    )
    packets = build_budget_human_review_outcome_owner_adoption_packets(
        outcome_report=outcome_report,
        outcome_report_ref=str(report_path),
        outcome_record=outcome_record,
        outcome_record_ref=str(record_path),
        checks=checks,
    )
    packets_jsonl = run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_PACKETS_FILENAME
    if packets_jsonl.exists():
        packets_jsonl.unlink()
    packet_refs = []
    for packet in packets:
        slug = _owner_slug(packet.target_repo)
        packet_json = packet_dir / f"{slug}.budget_human_review_outcome_owner_packet.json"
        packet_md = packet_dir / f"{slug}.budget_human_review_outcome_owner_packet.md"
        write_json(packet_json, packet.model_dump(mode="json"))
        packet_md.write_text(
            render_budget_human_review_outcome_owner_adoption_packet(packet),
            encoding="utf-8",
        )
        append_jsonl(packets_jsonl, packet.model_dump(mode="json"))
        packet_refs.append(str(packet_json))
    adoption_report = build_budget_human_review_outcome_owner_adoption_report(
        outcome_report=outcome_report,
        outcome_report_ref=str(report_path),
        outcome_record=outcome_record,
        outcome_record_ref=str(record_path),
        packets=packets,
        packet_output_refs=packet_refs,
        checks=checks,
    )
    write_json(
        run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_REPORT_FILENAME,
        adoption_report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_HUMAN_REVIEW_OUTCOME_OWNER_ADOPTION_NOTES_FILENAME).write_text(
        render_budget_human_review_outcome_owner_adoption_report(adoption_report),
        encoding="utf-8",
    )
    return adoption_report, run_dir
