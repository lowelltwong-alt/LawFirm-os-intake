from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetLifecycleAuditReport,
    BudgetLifecycleOwnerAdoptionPacket,
    BudgetLifecycleOwnerAdoptionReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_LIFECYCLE_OWNER_ADOPTION_REPORT_FILENAME = "budget_lifecycle_owner_adoption_report.json"
BUDGET_LIFECYCLE_OWNER_ADOPTION_NOTES_FILENAME = "budget_lifecycle_owner_adoption_report.md"
BUDGET_LIFECYCLE_OWNER_ADOPTION_PACKETS_FILENAME = "budget_lifecycle_owner_adoption_packets.jsonl"
BUDGET_LIFECYCLE_OWNER_ADOPTION_DIRNAME = "budget_lifecycle_owner_packets"

READY_LIFECYCLE_STATUS = "ready_for_budget_lifecycle_review"

TARGET_REPOS = [
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

BUDGET_LIFECYCLE_OWNER_REQUIRED_NEXT_GATES = [
    "human_budget_lifecycle_owner_review",
    "manual_owner_issue_creation_if_desired",
    "owning_repo_triage",
    "owner_repo_implementation_pr_if_accepted",
    "cross_repo_contract_validation_after_owner_changes",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _owner_slug(owner: str) -> str:
    return owner.lower().replace("lawfirm-os-", "").replace("_", "-")


def _ready_for_owner_packets(report: BudgetLifecycleAuditReport) -> bool:
    return report.status == READY_LIFECYCLE_STATUS and not any(
        check.status == "failed" for check in report.checks
    )


def _source_artifact_refs(report: BudgetLifecycleAuditReport, report_ref: str) -> list[str]:
    return [
        report_ref,
        report.source_budget_change_ledger_report_ref,
        report.source_budget_actual_variance_ledger_report_ref,
        report.source_carrier_rejection_decision_ledger_report_ref,
        report.source_budget_event_lake_bundle_report_ref,
        "schemas/budget-lifecycle-audit-report.schema.json",
        "schemas/budget-change-ledger-report.schema.json",
        "schemas/budget-actual-variance-ledger-report.schema.json",
        "schemas/carrier-rejection-decision-ledger-report.schema.json",
        "schemas/budget-lake-admission-bundle-report.schema.json",
    ]


def _adoption_focus(owner: str) -> str:
    return {
        "LawFirm-os-semantic-substrate": "semantic_contract_and_event_labels",
        "LawFirm-os-orchestrator": "runtime_capture_and_human_workflow",
        "LawFirm-os-exceptions-lake-runtime": "append_only_lake_admission",
    }[owner]


def _candidate_contract_refs(owner: str) -> list[str]:
    refs = {
        "LawFirm-os-semantic-substrate": [
            "semantic-substrate://candidate/contracts/budget-lifecycle-event.v0_1",
            "semantic-substrate://candidate/event-labels/budget-lifecycle.v0_1",
            "semantic-substrate://candidate/lifecycle-states/budget-review-actuals-rejection.v0_1",
        ],
        "LawFirm-os-orchestrator": [
            "orchestrator://candidate/workflows/budget-lifecycle-capture.v0_1",
            "orchestrator://candidate/interfaces/billing-actuals-read.v0_1",
            "orchestrator://candidate/interfaces/carrier-response-capture.v0_1",
            "orchestrator://candidate/interfaces/human-budget-lifecycle-pause.v0_1",
            "orchestrator://candidate/interfaces/exception-lake-evidence-packet.v0_1",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "exception-lake://candidate/admission/budget-human-change.v0_1",
            "exception-lake://candidate/admission/budget-actual-variance.v0_1",
            "exception-lake://candidate/admission/carrier-rejection-decision.v0_1",
            "exception-lake://candidate/admission/carrier-appeal-financial-outcome.v0_1",
        ],
    }
    return refs[owner]


def _owner_actions(owner: str) -> list[str]:
    actions = {
        "LawFirm-os-semantic-substrate": [
            "Review local budget lifecycle event kinds, decision statuses, candidate record families, and lifecycle states against existing substrate doctrine.",
            "Decide which budget change, actual variance, carrier rejection, appeal result, and financial outcome labels deserve canonical event classes.",
            "Define canonical correction/supersession semantics for human budget edits, actuals updates, carrier appeal results, and write-down outcomes.",
            "Keep UTBMS, rate, carrier guideline, and budget-driver terms as external or candidate vocabularies unless separately promoted.",
        ],
        "LawFirm-os-orchestrator": [
            "Design the runtime workflow that captures human budget edits, carrier notices, appeal/fix decisions, appeal outcomes, and actual-cost comparison inputs.",
            "Define connector boundaries for email, portal, LEDES, billing actuals read, and any appeal or budget submission path.",
            "Add human pauses for budget edit review, carrier rejection disposition, appeal authorization, financial outcome confirmation, and learning disposition.",
            "Assemble hash-preserving evidence packets for Exception Lake admission without giving intake connector or write authority.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Design append-only record families for budget human changes, actual variance, carrier rejection decisions, appeal results, and financial outcomes.",
            "Define idempotency keys, source hashes, support hashes, record hashes, correction records, and supersession rules.",
            "Decide SQLite tables and migrations inside the Exception Lake runtime, not intake.",
            "Require Orchestrator-owned evidence packets before admitting any real budget lifecycle records.",
        ],
    }
    return actions[owner]


def _acceptance_checks(owner: str) -> list[str]:
    checks = {
        "LawFirm-os-semantic-substrate": [
            "No canonical schema ID, route ID, lifecycle state, or event class is assigned from intake-local artifacts.",
            "Accepted labels are mapped through substrate registries and governance docs.",
            "Budget proposal, budget approval, budget submission, carrier appeal, and actual-cost concepts remain separately modeled.",
            "Learning from corrections remains an explicit reviewed lifecycle, not an implicit mutation.",
        ],
        "LawFirm-os-orchestrator": [
            "Runtime capture uses one outer workflow owner and typed human pause states.",
            "Portal, email, LEDES, billing, appeal-submission, and budget-submission writes are impossible without human authorization.",
            "Evidence packets preserve source IDs, offsets, hashes, reviewer decisions, before/after amounts, appeal outcomes, and actual-cost refs.",
            "Retries, duplicate carrier notices, missing responses, and correction/supersession paths are deterministic.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Admission validates idempotency, source/support hashes, record hashes, and append-only correction semantics.",
            "SQLite schema and migrations live only in the Lake runtime repo.",
            "Dry-run intake JSONL rows cannot be treated as admitted evidence.",
            "Raw payload storage stays prohibited unless a separate governed record family explicitly allows it.",
        ],
    }
    return checks[owner]


def _red_team_notes(owner: str) -> list[str]:
    notes = {
        "LawFirm-os-semantic-substrate": [
            "Budget lifecycle labels may look canonical because they are consistent locally, but they remain candidate vocabulary.",
            "A carrier-specific rule can accidentally become global doctrine if promotion does not distinguish guideline, template, and evidence semantics.",
        ],
        "LawFirm-os-orchestrator": [
            "The largest risk is converting a local audit into production connector behavior without human authorization and retry/failure contracts.",
            "Appeal submission, budget submission, and billing reads are high-risk gates and cannot be inferred from a passing intake audit.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "The largest risk is double-counting duplicate carrier notices or treating corrected budget edits as destructive updates.",
            "Actuals and carrier outcomes can become misleading learning signals unless supersession and review outcome records are append-only.",
        ],
    }
    return notes[owner]


def build_budget_lifecycle_owner_adoption_packets(
    *,
    lifecycle_audit_report: BudgetLifecycleAuditReport,
    lifecycle_audit_report_ref: str,
) -> list[BudgetLifecycleOwnerAdoptionPacket]:
    ready = _ready_for_owner_packets(lifecycle_audit_report)
    source_artifact_refs = _source_artifact_refs(
        lifecycle_audit_report,
        lifecycle_audit_report_ref,
    )
    packets: list[BudgetLifecycleOwnerAdoptionPacket] = []
    for owner in TARGET_REPOS:
        packets.append(
            BudgetLifecycleOwnerAdoptionPacket(
                owner_adoption_packet_id=_stable_id(
                    "budgetlifecycleownerpacket",
                    f"{lifecycle_audit_report.lifecycle_audit_report_id}|{owner}",
                ),
                target_repo=owner,  # type: ignore[arg-type]
                adoption_focus=_adoption_focus(owner),  # type: ignore[arg-type]
                status=("ready_for_owner_review" if ready else "blocked_by_lifecycle_audit"),
                source_budget_lifecycle_audit_report_id=(
                    lifecycle_audit_report.lifecycle_audit_report_id
                ),
                source_budget_lifecycle_audit_report_ref=lifecycle_audit_report_ref,
                source_budget_lifecycle_audit_status=lifecycle_audit_report.status,
                source_budget_proposal_id=lifecycle_audit_report.budget_proposal_id,
                source_preflight_packet_id=lifecycle_audit_report.preflight_packet_id,
                source_artifact_refs=source_artifact_refs,
                candidate_contract_refs=_candidate_contract_refs(owner),
                required_owner_actions=_owner_actions(owner),
                acceptance_checks=_acceptance_checks(owner),
                red_team_notes=_red_team_notes(owner),
                required_next_gates=BUDGET_LIFECYCLE_OWNER_REQUIRED_NEXT_GATES,
            )
        )
    return packets


def build_budget_lifecycle_owner_adoption_report(
    *,
    lifecycle_audit_report: BudgetLifecycleAuditReport,
    lifecycle_audit_report_ref: str,
    packets: list[BudgetLifecycleOwnerAdoptionPacket],
    packet_output_refs: list[str],
) -> BudgetLifecycleOwnerAdoptionReport:
    ready_count = sum(1 for packet in packets if packet.status == "ready_for_owner_review")
    blocked_count = len(packets) - ready_count
    return BudgetLifecycleOwnerAdoptionReport(
        owner_adoption_report_id=_stable_id(
            "budgetlifecycleownerreport",
            f"{lifecycle_audit_report.lifecycle_audit_report_id}|{lifecycle_audit_report_ref}",
        ),
        status=(
            "owner_adoption_packets_ready" if blocked_count == 0 else "blocked_by_lifecycle_audit"
        ),
        source_budget_lifecycle_audit_report_id=lifecycle_audit_report.lifecycle_audit_report_id,
        source_budget_lifecycle_audit_report_ref=lifecycle_audit_report_ref,
        source_budget_lifecycle_audit_status=lifecycle_audit_report.status,
        target_repo_count=len(TARGET_REPOS),
        packet_count=len(packets),
        ready_packet_count=ready_count,
        blocked_packet_count=blocked_count,
        target_repos=TARGET_REPOS,  # type: ignore[arg-type]
        packets=packets,
        packet_output_refs=packet_output_refs,
        required_next_gates=BUDGET_LIFECYCLE_OWNER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_lifecycle_owner_adoption_packet(
    packet: BudgetLifecycleOwnerAdoptionPacket,
) -> str:
    lines = [
        "# Budget Lifecycle Owner Adoption Packet",
        "",
        f"**Packet ID:** {packet.owner_adoption_packet_id}",
        f"**Target repo:** {packet.target_repo}",
        f"**Focus:** {packet.adoption_focus}",
        f"**Status:** {packet.status}",
        "",
        "## Source Evidence",
        "",
        f"- Lifecycle audit: `{packet.source_budget_lifecycle_audit_report_ref}`",
        f"- Lifecycle status: {packet.source_budget_lifecycle_audit_status}",
        f"- Budget proposal: {packet.source_budget_proposal_id or 'none'}",
        f"- Preflight packet: {packet.source_preflight_packet_id or 'none'}",
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
        "## Source Artifact Refs",
        "",
        *(f"- `{ref}`" for ref in packet.source_artifact_refs),
        "",
        "## Boundary Flags",
        "",
        f"- Direct promotion performed: {packet.direct_promotion_performed}",
        f"- Promotion authorized: {packet.promotion_authorized}",
        f"- Sibling repo write performed: {packet.sibling_repo_write_performed}",
        f"- GitHub issue created: {packet.github_issue_created}",
        f"- GitHub PR created: {packet.github_pr_created}",
        f"- Connector implemented: {packet.connector_implemented}",
        f"- Lake write performed: {packet.lake_write_performed}",
        f"- SQLite write performed: {packet.sqlite_write_performed}",
        f"- External writes performed: {packet.external_writes_performed}",
        f"- Budget submission performed: {packet.budget_submission_performed}",
        f"- Appeal submission performed: {packet.appeal_submission_performed}",
        f"- Silent learning performed: {packet.silent_learning_performed}",
        "",
        "This packet is local owner-review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, implement connectors, admit Lake records, write SQLite, submit budgets or appeals, mutate budgets, or apply learning.",
        "",
    ]
    return "\n".join(lines)


def render_budget_lifecycle_owner_adoption_report(
    report: BudgetLifecycleOwnerAdoptionReport,
) -> str:
    lines = [
        "# Budget Lifecycle Owner Adoption Report",
        "",
        f"**Report ID:** {report.owner_adoption_report_id}",
        f"**Status:** {report.status}",
        f"**Source lifecycle audit:** `{report.source_budget_lifecycle_audit_report_ref}`",
        f"**Ready packets:** {report.ready_packet_count}",
        f"**Blocked packets:** {report.blocked_packet_count}",
        "",
        "## Owner Packets",
        "",
    ]
    for packet, output_ref in zip(report.packets, report.packet_output_refs, strict=True):
        lines.extend(
            [
                f"### {packet.target_repo}",
                "",
                f"- Status: {packet.status}",
                f"- Focus: {packet.adoption_focus}",
                f"- Packet ref: `{output_ref}`",
                "- First required action: "
                + (packet.required_owner_actions[0] if packet.required_owner_actions else "none"),
                "- First red-team note: "
                + (packet.red_team_notes[0] if packet.red_team_notes else "none"),
                "",
            ]
        )
    lines.extend(
        [
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary Flags",
            "",
            f"- Direct promotion performed: {report.direct_promotion_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- Connector implemented: {report.connector_implemented}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Budget submission performed: {report.budget_submission_performed}",
            f"- Appeal submission performed: {report.appeal_submission_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report is local owner-adoption planning evidence only. It does not create issues, open PRs, write sibling repos, promote canon, implement connectors, admit Lake records, write SQLite, submit budgets or appeals, mutate budgets, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_lifecycle_owner_adoption(
    *,
    budget_lifecycle_audit_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetLifecycleOwnerAdoptionReport, Path]:
    audit_path = Path(budget_lifecycle_audit_report_path)
    lifecycle_audit_report = BudgetLifecycleAuditReport.model_validate(load_json(audit_path))
    packets = build_budget_lifecycle_owner_adoption_packets(
        lifecycle_audit_report=lifecycle_audit_report,
        lifecycle_audit_report_ref=str(audit_path),
    )

    run_dir = Path(out_dir)
    packet_dir = run_dir / BUDGET_LIFECYCLE_OWNER_ADOPTION_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)
    packets_jsonl_path = run_dir / BUDGET_LIFECYCLE_OWNER_ADOPTION_PACKETS_FILENAME
    if packets_jsonl_path.exists():
        packets_jsonl_path.unlink()

    packet_output_refs: list[str] = []
    for packet in packets:
        slug = _owner_slug(packet.target_repo)
        packet_path = packet_dir / f"{slug}.budget_lifecycle_owner_packet.json"
        notes_path = packet_dir / f"{slug}.budget_lifecycle_owner_packet.md"
        write_json(packet_path, packet.model_dump(mode="json"))
        notes_path.write_text(
            render_budget_lifecycle_owner_adoption_packet(packet),
            encoding="utf-8",
        )
        append_jsonl(packets_jsonl_path, packet.model_dump(mode="json"))
        packet_output_refs.append(str(packet_path))

    report = build_budget_lifecycle_owner_adoption_report(
        lifecycle_audit_report=lifecycle_audit_report,
        lifecycle_audit_report_ref=str(audit_path),
        packets=packets,
        packet_output_refs=packet_output_refs,
    )
    write_json(
        run_dir / BUDGET_LIFECYCLE_OWNER_ADOPTION_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_LIFECYCLE_OWNER_ADOPTION_NOTES_FILENAME).write_text(
        render_budget_lifecycle_owner_adoption_report(report),
        encoding="utf-8",
    )
    return report, run_dir
