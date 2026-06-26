from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import (
    CrossRepoOwnerAdoptionPacket,
    CrossRepoOwnerAdoptionReport,
    CrossRepoPromotionPackage,
    CrossRepoPromotionProposal,
    IntakeVerticalReadinessAuditReport,
    PRReviewChecklistReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


CROSS_REPO_OWNER_ADOPTION_REPORT_FILENAME = "cross_repo_owner_adoption_report.json"
CROSS_REPO_OWNER_ADOPTION_NOTES_FILENAME = "cross_repo_owner_adoption_report.md"
CROSS_REPO_OWNER_ADOPTION_PACKETS_FILENAME = "cross_repo_owner_adoption_packets.jsonl"
CROSS_REPO_OWNER_ADOPTION_DIRNAME = "owner_adoption_packets"

READY_READINESS_STATUS = "ready_for_pr_review_external_adoption_required"
READY_CHECKLIST_STATUS = "ready_for_human_pr_review"

REQUIRED_NEXT_GATES = [
    "human_pr_review_decision",
    "owning_repo_review",
    "owner_repo_implementation_pr_if_accepted",
    "cross_repo_contract_validation_after_owner_changes",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _owner_slug(owner: str) -> str:
    return owner.lower().replace("lawfirm-os-", "").replace("_", "-")


def _ready_for_owner_packets(
    readiness_report: IntakeVerticalReadinessAuditReport,
    pr_review_checklist: PRReviewChecklistReport,
) -> bool:
    return (
        readiness_report.status == READY_READINESS_STATUS
        and pr_review_checklist.status == READY_CHECKLIST_STATUS
        and pr_review_checklist.blocking_item_count == 0
        and pr_review_checklist.github_write_performed is False
        and pr_review_checklist.pr_marked_ready is False
    )


def _owner_actions(owner: str) -> list[str]:
    actions = {
        "LawFirm-os-semantic-substrate": [
            "Review candidate schemas, event labels, vocabularies, and lifecycle states against existing substrate canon.",
            "Decide which intake-local fields stay local and which deserve canonical contract proposals.",
            "Assign canonical schema IDs, event classes, route IDs, and lifecycle terms only inside Semantic Substrate if accepted.",
        ],
        "LawFirm-os-orchestrator": [
            "Review workflow ownership, human pauses, response-state ledgers, connector channels, and evidence-packet assembly.",
            "Decide whether any reference CLI behavior should become an Orchestrator-owned runtime interface.",
            "Keep all portal, email, billing, appeal-submission, and budget-submission writes behind Orchestrator authorization gates.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Review candidate record families, idempotency keys, support hashes, record hashes, and supersession/correction semantics.",
            "Decide append-only admission schemas, SQLite tables, migrations, and validation inside the Lake runtime.",
            "Require Orchestrator evidence packets before runtime admission of budget, rejection, appeal, or learning records.",
        ],
        "LawFirm-os-skills-registry": [
            "Review specialist metadata, accepted and forbidden context classes, tool authority, prompt hashes, and eval suites.",
            "Decide whether any local specialist should receive a draft or promoted skill trust record.",
            "Keep frontier-adjudicator authority deny-by-default until a separate skills review approves it.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "Review source, passage, claim, retrieval trace, and Legal Context Bundle refs needed by intake.",
            "Confirm raw legal payload fanout remains prohibited and context remains separate from observed evidence.",
            "Decide whether any source-ref or context-bundle helpers belong in Legal Knowledge Runtime.",
        ],
    }
    return actions[owner]


def _acceptance_checks(owner: str) -> list[str]:
    checks = {
        "LawFirm-os-semantic-substrate": [
            "No canonical ID is assigned from intake-local files.",
            "Accepted contracts map to substrate registries and governance docs.",
            "Rejected or local-only fields remain candidate references in intake.",
        ],
        "LawFirm-os-orchestrator": [
            "Runtime interface keeps one outer workflow owner and explicit human pause states.",
            "Connector and submission writes are impossible without promoted Orchestrator authority.",
            "Evidence packet assembly preserves source IDs, segment IDs, offsets, hashes, and gate history.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Admission schemas include idempotency, source/support hashes, record hashes, and supersession records.",
            "SQLite schema and migrations live in the Lake repo, not intake.",
            "Dry-run local labels are mapped to canonical event classes only after Lake/Substrate review.",
        ],
        "LawFirm-os-skills-registry": [
            "Skill trust records include reviewed prompt hashes, allowed tools, forbidden contexts, and eval coverage.",
            "No dynamic agent creation is introduced.",
            "Skills remain revocable and bound to typed input/output contracts.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "Context bundle refs are source-bound and hash-preserving.",
            "Practice context is never treated as observed matter evidence.",
            "Public or legal reference retrieval does not store raw client payloads.",
        ],
    }
    return checks[owner]


def _red_team_notes(owner: str) -> list[str]:
    notes = {
        "LawFirm-os-semantic-substrate": [
            "The largest risk is promoting local candidate labels into canon before conflicts with existing substrate vocabularies are checked.",
            "Budget and carrier terms may look general but could encode synthetic fixture assumptions.",
        ],
        "LawFirm-os-orchestrator": [
            "The largest risk is turning a reference CLI into a production workflow without explicit connector, retry, human-pause, and authorization contracts.",
            "Carrier appeal or budget submission must remain impossible until a human-authorized Orchestrator path exists.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "The largest risk is treating dry-run candidate JSONL as admitted evidence without idempotency, record hashes, or append-only storage validation.",
            "Budget actuals and carrier rejection events need correction/supersession semantics before real data.",
        ],
        "LawFirm-os-skills-registry": [
            "The largest risk is promoting long prompts as skills without supply-chain, context, and tool-authority review.",
            "Frontier adjudication cannot be trusted unless evidence refs, denylist, and eval gates are independently verified.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "The largest risk is letting retrieval context become observed evidence or leaking raw matter payloads into a knowledge runtime.",
            "Source/passage/claim refs need strict hash and currency semantics before production use.",
        ],
    }
    return notes[owner]


def _authority_plane(proposals: list[CrossRepoPromotionProposal]) -> str:
    planes = sorted({proposal.authority_plane for proposal in proposals})
    if len(planes) == 1:
        return planes[0]
    return "mixed"


def _group_proposals(
    package: CrossRepoPromotionPackage,
) -> dict[str, list[CrossRepoPromotionProposal]]:
    grouped: dict[str, list[CrossRepoPromotionProposal]] = defaultdict(list)
    for proposal in package.proposals:
        grouped[proposal.target_repo].append(proposal)
    for owner in package.target_repos:
        grouped.setdefault(owner, [])
    return dict(sorted(grouped.items()))


def build_cross_repo_owner_adoption_packets(
    *,
    promotion_package: CrossRepoPromotionPackage,
    promotion_package_ref: str,
    readiness_report: IntakeVerticalReadinessAuditReport,
    readiness_report_ref: str,
    pr_review_checklist: PRReviewChecklistReport,
    pr_review_checklist_ref: str,
) -> list[CrossRepoOwnerAdoptionPacket]:
    ready = _ready_for_owner_packets(readiness_report, pr_review_checklist)
    packets: list[CrossRepoOwnerAdoptionPacket] = []
    for owner, proposals in _group_proposals(promotion_package).items():
        packets.append(
            CrossRepoOwnerAdoptionPacket(
                adoption_packet_id=_stable_id(
                    "owneradoptionpacket",
                    f"{promotion_package.package_id}|{readiness_report.audit_report_id}|{owner}",
                ),
                target_repo=owner,  # type: ignore[arg-type]
                authority_plane=_authority_plane(proposals),  # type: ignore[arg-type]
                status=("ready_for_owner_review" if ready else "blocked_by_pr_readiness"),
                source_promotion_package_id=promotion_package.package_id,
                source_promotion_package_ref=promotion_package_ref,
                source_readiness_audit_report_id=readiness_report.audit_report_id,
                source_readiness_audit_report_ref=readiness_report_ref,
                source_readiness_status=readiness_report.status,
                source_pr_review_checklist_id=pr_review_checklist.checklist_report_id,
                source_pr_review_checklist_ref=pr_review_checklist_ref,
                source_pr_review_checklist_status=pr_review_checklist.status,
                proposal_count=len(proposals),
                proposals=proposals,
                required_owner_actions=_owner_actions(owner),
                acceptance_checks=_acceptance_checks(owner),
                red_team_notes=_red_team_notes(owner),
                required_next_gates=REQUIRED_NEXT_GATES,
            )
        )
    return packets


def build_cross_repo_owner_adoption_report(
    *,
    promotion_package: CrossRepoPromotionPackage,
    promotion_package_ref: str,
    readiness_report: IntakeVerticalReadinessAuditReport,
    readiness_report_ref: str,
    pr_review_checklist: PRReviewChecklistReport,
    pr_review_checklist_ref: str,
    packets: list[CrossRepoOwnerAdoptionPacket],
    packet_output_refs: list[str],
) -> CrossRepoOwnerAdoptionReport:
    ready_count = sum(1 for packet in packets if packet.status == "ready_for_owner_review")
    blocked_count = len(packets) - ready_count
    return CrossRepoOwnerAdoptionReport(
        owner_adoption_report_id=_stable_id(
            "owneradoptionreport",
            f"{promotion_package.package_id}|{readiness_report.audit_report_id}|{pr_review_checklist.checklist_report_id}",
        ),
        status=(
            "owner_adoption_packets_ready" if blocked_count == 0 else "blocked_by_pr_readiness"
        ),
        source_promotion_package_id=promotion_package.package_id,
        source_promotion_package_ref=promotion_package_ref,
        source_readiness_audit_report_id=readiness_report.audit_report_id,
        source_readiness_audit_report_ref=readiness_report_ref,
        source_readiness_status=readiness_report.status,
        source_pr_review_checklist_id=pr_review_checklist.checklist_report_id,
        source_pr_review_checklist_ref=pr_review_checklist_ref,
        source_pr_review_checklist_status=pr_review_checklist.status,
        source_pr_review_checklist_recommendation=pr_review_checklist.recommendation,
        target_repo_count=len(promotion_package.target_repos),
        packet_count=len(packets),
        ready_packet_count=ready_count,
        blocked_packet_count=blocked_count,
        proposal_count=sum(packet.proposal_count for packet in packets),
        target_repos=promotion_package.target_repos,  # type: ignore[arg-type]
        packets=packets,
        packet_output_refs=packet_output_refs,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_cross_repo_owner_adoption_packet(packet: CrossRepoOwnerAdoptionPacket) -> str:
    lines = [
        "# Cross-Repo Owner Adoption Packet",
        "",
        f"**Packet ID:** {packet.adoption_packet_id}",
        f"**Target repo:** {packet.target_repo}",
        f"**Authority plane:** {packet.authority_plane}",
        f"**Status:** {packet.status}",
        f"**Proposal count:** {packet.proposal_count}",
        "",
        "## Source Evidence",
        "",
        f"- Promotion package: `{packet.source_promotion_package_ref}`",
        f"- Readiness audit: `{packet.source_readiness_audit_report_ref}`",
        f"- PR review checklist: `{packet.source_pr_review_checklist_ref}`",
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
        "## Proposals",
        "",
    ]
    if not packet.proposals:
        lines.append("- none")
    for proposal in packet.proposals:
        lines.extend(
            [
                f"### {proposal.proposal_id}",
                "",
                f"- Type: {proposal.proposal_type}",
                f"- Summary: {proposal.summary}",
                "- Candidate artifacts: "
                + ", ".join(f"`{ref}`" for ref in proposal.candidate_artifact_refs),
                "- Proposed contract refs: "
                + ", ".join(f"`{ref}`" for ref in proposal.proposed_contract_refs),
                "- Required governance actions:",
                *(f"  - {action}" for action in proposal.required_governance_actions),
                "- Promotion blockers:",
                *(f"  - {blocker}" for blocker in proposal.promotion_blockers),
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary Flags",
            "",
            f"- Direct promotion performed: {packet.direct_promotion_performed}",
            f"- Promotion authorized: {packet.promotion_authorized}",
            f"- Sibling repo write performed: {packet.sibling_repo_write_performed}",
            f"- GitHub issue created: {packet.github_issue_created}",
            f"- GitHub PR created: {packet.github_pr_created}",
            f"- GitHub write performed: {packet.github_write_performed}",
            f"- Lake write performed: {packet.lake_write_performed}",
            f"- SQLite write performed: {packet.sqlite_write_performed}",
            f"- External writes performed: {packet.external_writes_performed}",
            f"- Silent learning performed: {packet.silent_learning_performed}",
            "",
            "This packet is local owner-review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, admit Lake records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def render_cross_repo_owner_adoption_report(report: CrossRepoOwnerAdoptionReport) -> str:
    lines = [
        "# Cross-Repo Owner Adoption Report",
        "",
        f"**Report ID:** {report.owner_adoption_report_id}",
        f"**Status:** {report.status}",
        f"**Source promotion package:** `{report.source_promotion_package_ref}`",
        f"**Source readiness audit:** `{report.source_readiness_audit_report_ref}`",
        f"**Source PR checklist:** `{report.source_pr_review_checklist_ref}`",
        f"**Ready packets:** {report.ready_packet_count}",
        f"**Blocked packets:** {report.blocked_packet_count}",
        f"**Proposal count:** {report.proposal_count}",
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
                f"- Authority plane: {packet.authority_plane}",
                f"- Proposal count: {packet.proposal_count}",
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
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report is local owner-adoption planning evidence only. It does not create issues, open PRs, write sibling repos, promote canon, admit Lake records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_cross_repo_owner_adoption(
    *,
    promotion_package_path: str | Path,
    readiness_audit_report_path: str | Path,
    pr_review_checklist_path: str | Path,
    out_dir: str | Path,
) -> tuple[CrossRepoOwnerAdoptionReport, Path]:
    promotion_path = Path(promotion_package_path)
    readiness_path = Path(readiness_audit_report_path)
    checklist_path = Path(pr_review_checklist_path)
    promotion_package = CrossRepoPromotionPackage.model_validate(load_json(promotion_path))
    readiness_report = IntakeVerticalReadinessAuditReport.model_validate(load_json(readiness_path))
    pr_review_checklist = PRReviewChecklistReport.model_validate(load_json(checklist_path))
    packets = build_cross_repo_owner_adoption_packets(
        promotion_package=promotion_package,
        promotion_package_ref=str(promotion_path),
        readiness_report=readiness_report,
        readiness_report_ref=str(readiness_path),
        pr_review_checklist=pr_review_checklist,
        pr_review_checklist_ref=str(checklist_path),
    )

    run_dir = Path(out_dir)
    packet_dir = run_dir / CROSS_REPO_OWNER_ADOPTION_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)
    packets_jsonl_path = run_dir / CROSS_REPO_OWNER_ADOPTION_PACKETS_FILENAME
    if packets_jsonl_path.exists():
        packets_jsonl_path.unlink()
    packet_output_refs: list[str] = []
    for packet in packets:
        slug = _owner_slug(packet.target_repo)
        packet_path = packet_dir / f"{slug}.owner_adoption_packet.json"
        notes_path = packet_dir / f"{slug}.owner_adoption_packet.md"
        write_json(packet_path, packet.model_dump(mode="json"))
        notes_path.write_text(render_cross_repo_owner_adoption_packet(packet), encoding="utf-8")
        append_jsonl(packets_jsonl_path, packet.model_dump(mode="json"))
        packet_output_refs.append(str(packet_path))

    report = build_cross_repo_owner_adoption_report(
        promotion_package=promotion_package,
        promotion_package_ref=str(promotion_path),
        readiness_report=readiness_report,
        readiness_report_ref=str(readiness_path),
        pr_review_checklist=pr_review_checklist,
        pr_review_checklist_ref=str(checklist_path),
        packets=packets,
        packet_output_refs=packet_output_refs,
    )
    write_json(run_dir / CROSS_REPO_OWNER_ADOPTION_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / CROSS_REPO_OWNER_ADOPTION_NOTES_FILENAME).write_text(
        render_cross_repo_owner_adoption_report(report),
        encoding="utf-8",
    )
    return report, run_dir
