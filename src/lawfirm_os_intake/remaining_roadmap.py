from __future__ import annotations

from pathlib import Path

from .models import (
    IntakeLocalCloseoutReport,
    IntakeVerticalReadinessAuditReport,
    PRReadinessDecisionReport,
    RemainingRoadmapCheck,
    RemainingRoadmapItem,
    RemainingRoadmapReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


REMAINING_ROADMAP_REPORT_FILENAME = "remaining_roadmap_report.json"
REMAINING_ROADMAP_NOTES_FILENAME = "remaining_roadmap_report.md"
REMAINING_ROADMAP_ITEMS_FILENAME = "remaining_roadmap_items.jsonl"

READY_READINESS_STATUS = "ready_for_pr_review_external_adoption_required"
READY_CLOSEOUT_STATUS = "intake_local_closeout_ready_manual_actions_required"

REMAINING_ROADMAP_REQUIRED_NEXT_GATES = [
    "human_pr_state_decision",
    "manual_owner_issue_creation_if_desired",
    "owner_repo_triage",
    "owner_repo_implementation_prs_if_accepted",
    "cross_repo_validation_after_owner_changes",
    "no_intake_external_write_or_promotion",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> RemainingRoadmapCheck:
    return RemainingRoadmapCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _closeout_boundary_clear(report: IntakeLocalCloseoutReport) -> bool:
    return (
        report.pr_state_change_performed is False
        and report.github_issue_created is False
        and report.github_pr_created is False
        and report.github_write_performed is False
        and report.sibling_repo_write_performed is False
        and report.promotion_authorized is False
        and report.proposed_changes_applied is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _pr_decision_boundary_clear(report: PRReadinessDecisionReport | None) -> bool:
    if report is None:
        return True
    return (
        report.pr_marked_ready is False
        and report.github_write_performed is False
        and report.github_issue_created is False
        and report.github_pr_created is False
        and report.sibling_repo_write_performed is False
        and report.promotion_authorized is False
        and report.proposed_changes_applied is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _build_checks(
    *,
    readiness: IntakeVerticalReadinessAuditReport,
    readiness_ref: str,
    closeout: IntakeLocalCloseoutReport,
    closeout_ref: str,
    pr_decision: PRReadinessDecisionReport | None,
    pr_decision_ref: str | None,
) -> list[RemainingRoadmapCheck]:
    refs = [readiness_ref, closeout_ref]
    if pr_decision_ref:
        refs.append(pr_decision_ref)
    checks = [
        _check(
            "readiness_audit_ready_for_remaining_plan",
            readiness.status == READY_READINESS_STATUS
            and readiness.implemented_slice_count == readiness.total_slice_count
            and not readiness.missing_artifact_refs
            and not readiness.missing_command_refs
            and not any(check.status == "failed" for check in readiness.artifact_checks),
            "Readiness audit is complete locally and still external-adoption gated.",
            artifact_refs=[readiness_ref],
        ),
        _check(
            "local_closeout_ready_for_remaining_plan",
            closeout.status == READY_CLOSEOUT_STATUS
            and closeout.blocking_check_count == 0
            and bool(closeout.manual_actions_remaining),
            "Local closeout is ready and still names manual actions.",
            artifact_refs=[closeout_ref],
        ),
        _check(
            "remaining_plan_sources_have_no_side_effects",
            _closeout_boundary_clear(closeout) and _pr_decision_boundary_clear(pr_decision),
            "Source reports show no GitHub, sibling repo, Lake, SQLite, promotion, mutation, external write, or silent-learning side effects.",
            artifact_refs=refs,
        ),
    ]
    if pr_decision is not None:
        checks.append(
            _check(
                "pr_readiness_decision_preserves_manual_state",
                pr_decision.status
                in {
                    "pr_readiness_decision_recorded_keep_draft",
                    "pr_readiness_decision_recorded_more_work_required",
                    "pr_readiness_decision_recorded_split_followup_work",
                    "pr_readiness_decision_recorded_manual_ready_action_required",
                }
                and pr_decision.pr_marked_ready is False,
                "PR readiness decision is recorded locally and did not change GitHub state.",
                artifact_refs=[pr_decision_ref] if pr_decision_ref else [],
            )
        )
    else:
        checks.append(
            RemainingRoadmapCheck(
                check_id="pr_readiness_decision_not_supplied",
                status="warning",
                message=(
                    "No PR readiness decision report was supplied; plan still requires "
                    "a human PR state decision."
                ),
                artifact_refs=[],
            )
        )
    return checks


def _item(
    *,
    item_id: str,
    title: str,
    workstream: str,
    owner: str,
    effort: str,
    risk: str,
    gate: str,
    status: str,
    why_now: str,
    source_evidence_refs: list[str],
    required_next_actions: list[str],
    acceptance_evidence_required: list[str],
    red_team_notes: list[str],
) -> RemainingRoadmapItem:
    return RemainingRoadmapItem(
        item_id=item_id,
        title=title,
        workstream=workstream,  # type: ignore[arg-type]
        owner=owner,  # type: ignore[arg-type]
        effort=effort,  # type: ignore[arg-type]
        risk=risk,  # type: ignore[arg-type]
        gate=gate,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        why_now=why_now,
        source_evidence_refs=source_evidence_refs,
        required_next_actions=required_next_actions,
        acceptance_evidence_required=acceptance_evidence_required,
        red_team_notes=red_team_notes,
    )


def _roadmap_items(
    *,
    readiness_ref: str,
    closeout_ref: str,
    pr_decision_ref: str | None,
) -> list[RemainingRoadmapItem]:
    evidence = [readiness_ref, closeout_ref]
    if pr_decision_ref:
        evidence.append(pr_decision_ref)
    return [
        _item(
            item_id="human-pr-review-and-state-decision",
            title="Human PR Review And State Decision",
            workstream="human_pr_review",
            owner="Human reviewer",
            effort="easy",
            risk="medium",
            gate="manual_human_review",
            status="ready_to_start",
            why_now="Local readiness and closeout evidence are ready; the PR remains draft until a human decides.",
            source_evidence_refs=evidence,
            required_next_actions=[
                "Review pr_review_checklist.md and intake_local_closeout_report.md.",
                "Decide keep draft, mark ready manually, split follow-up work, or request more work.",
                "Record any decision append-only before changing PR state.",
            ],
            acceptance_evidence_required=[
                "Reviewed PR checklist with no unresolved blocking items.",
                "Human-authored PR readiness decision record.",
                "If marked ready, GitHub state change performed manually by the human reviewer.",
            ],
            red_team_notes=[
                "Ready local evidence is not production readiness.",
                "Automating the GitHub state change would break the review boundary.",
            ],
        ),
        _item(
            item_id="manual-owner-issue-creation",
            title="Manual Owner Issue Creation From Drafts",
            workstream="manual_owner_issue_creation",
            owner="Human reviewer",
            effort="easy",
            risk="medium",
            gate="manual_human_review",
            status="ready_to_start",
            why_now="Owner issue drafts exist locally, but intake did not create issues.",
            source_evidence_refs=[closeout_ref],
            required_next_actions=[
                "Review generated owner issue drafts for Semantic Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime.",
                "Create only the issues the human owner wants to pursue.",
                "Preserve source evidence refs when creating any issue manually.",
            ],
            acceptance_evidence_required=[
                "Human-created issue URLs or a decision to defer issue creation.",
                "Owner repo labels and scope reviewed by humans.",
            ],
            red_team_notes=[
                "Issue drafts may look authoritative but are local candidate text.",
                "Creating every issue blindly can overload owner repos with untriaged work.",
            ],
        ),
        _item(
            item_id="owner-triage-and-pr-splitting",
            title="Owner Triage And PR Splitting",
            workstream="owner_triage",
            owner="Cross-repo owners",
            effort="medium",
            risk="high",
            gate="owner_repo_review",
            status="blocked_until_owner_action",
            why_now="The local vertical now names adoption packets, but implementation belongs in owning repos.",
            source_evidence_refs=[readiness_ref, closeout_ref],
            required_next_actions=[
                "Each owning repo triages its packet and decides accepted, rejected, or split follow-up scope.",
                "Open separate implementation PRs only inside the owning repo.",
                "Run cross-repo validation after any owner change lands.",
            ],
            acceptance_evidence_required=[
                "Owner repo triage decision or issue comment.",
                "Implementation PR links when accepted.",
                "Cross-repo validation output after owner changes.",
            ],
            red_team_notes=[
                "Bundling owner changes back into intake would blur authority boundaries.",
                "A green intake PR does not prove owner repos can safely adopt the contracts.",
            ],
        ),
        _item(
            item_id="semantic-substrate-contract-review",
            title="Semantic Substrate Contract Review",
            workstream="semantic_contract_promotion",
            owner="LawFirm-os-semantic-substrate",
            effort="large",
            risk="critical",
            gate="governance_approval",
            status="blocked_until_owner_action",
            why_now="Candidate schemas, event labels, lifecycle states, and governance terms need canonical review before runtime use.",
            source_evidence_refs=[readiness_ref, closeout_ref],
            required_next_actions=[
                "Review candidate schema families and event labels from the promotion package.",
                "Accept, revise, or reject canonical promotion in Semantic Substrate.",
                "Update registry/control-plane validation if any contract is promoted.",
            ],
            acceptance_evidence_required=[
                "Semantic Substrate PR with schema/registry/governance changes if accepted.",
                "Substrate validation output.",
                "Updated contract pins for consuming repos.",
            ],
            red_team_notes=[
                "Local candidate schemas can accidentally become de facto canon if copied without governance.",
                "Route IDs and event classes must not be invented in intake.",
            ],
        ),
        _item(
            item_id="orchestrator-runtime-adoption",
            title="Orchestrator Runtime Adoption",
            workstream="runtime_orchestration_adoption",
            owner="LawFirm-os-orchestrator",
            effort="large",
            risk="critical",
            gate="owner_repo_review",
            status="blocked_until_owner_action",
            why_now="Production execution, human pauses, connector reads, evidence packets, and external-action gates belong to Orchestrator.",
            source_evidence_refs=[readiness_ref, closeout_ref],
            required_next_actions=[
                "Design Orchestrator-owned workflow states for intake, budget review, actuals, carrier rejections, appeals, and owner followups.",
                "Implement only bounded connector reads/writes approved by governance.",
                "Assemble typed evidence packets for Lake admission without storing raw legal payloads in intake.",
            ],
            acceptance_evidence_required=[
                "Orchestrator design or implementation PR.",
                "Human pause and external-action gate tests.",
                "Evidence packet validation against promoted contracts.",
            ],
            red_team_notes=[
                "The highest-risk bug is treating a recommendation as authorization to submit, appeal, docket, or bill.",
                "Billing actuals must not be read by intake directly.",
            ],
        ),
        _item(
            item_id="exception-lake-runtime-admission",
            title="Exception Lake Runtime Admission",
            workstream="exception_lake_admission",
            owner="LawFirm-os-exceptions-lake-runtime",
            effort="large",
            risk="critical",
            gate="owner_repo_review",
            status="blocked_until_owner_action",
            why_now="Append-only evidence, idempotency, hashes, supersession, and SQLite persistence belong to Exception Lake runtime.",
            source_evidence_refs=[readiness_ref, closeout_ref],
            required_next_actions=[
                "Review candidate budget, rejection, actual-variance, and outcome record families.",
                "Define idempotency keys, record hashes, support hashes, and supersession rules.",
                "Implement SQLite migrations only in the Lake runtime if approved.",
            ],
            acceptance_evidence_required=[
                "Exception Lake PR with admission schemas or migrations if accepted.",
                "Idempotency and duplicate-admission tests.",
                "No raw legal payload retention proof.",
            ],
            red_team_notes=[
                "Double-counting phase and code variance events can corrupt financial learning.",
                "Lake admission is not a write-through cache for intake-local candidate files.",
            ],
        ),
        _item(
            item_id="fixture-and-eval-expansion",
            title="Synthetic Fixture And Eval Expansion",
            workstream="fixture_and_eval_expansion",
            owner="LawFirm-os-intake",
            effort="medium",
            risk="medium",
            gate="local_candidate",
            status="ready_to_start",
            why_now="More synthetic variation improves confidence before any real-data pilot, while staying inside intake authority.",
            source_evidence_refs=[readiness_ref],
            required_next_actions=[
                "Add synthetic holdouts for ambiguous roles, missing actuals, carrier rejection variants, and budget driver edge cases.",
                "Bind approved outputs through fixture review records before calibration use.",
                "Run replay, shadow eval, and readiness checks after fixture updates.",
            ],
            acceptance_evidence_required=[
                "Separate fixture-update PR with reviewed synthetic data only.",
                "Fixture gold and shadow-eval results.",
                "No real client, matter, privileged, or negotiated-rate data.",
            ],
            red_team_notes=[
                "Synthetic fixtures can overfit the current deterministic implementation.",
                "Fixture updates should not silently improve scores without reviewed gold.",
            ],
        ),
        _item(
            item_id="public-source-methodology-next-pass",
            title="Public Source Methodology Next Pass",
            workstream="public_source_methodology",
            owner="LawFirm-os-legal-knowledge-runtime",
            effort="medium",
            risk="high",
            gate="owner_repo_review",
            status="blocked_until_owner_action",
            why_now="Public source structure can help synthetic fixture design, but public payload ingestion remains disabled.",
            source_evidence_refs=[readiness_ref],
            required_next_actions=[
                "Review source licenses, privacy posture, retention posture, and allowed methodology use.",
                "Approve or reject any Legal Knowledge Runtime lookup/retrieval helper.",
                "Keep public records out of intake fixtures unless converted into non-identifying synthetic structures.",
            ],
            acceptance_evidence_required=[
                "Legal Knowledge Runtime owner review.",
                "Public-source methodology decision record.",
                "Synthetic conversion review before any fixture PR.",
            ],
            red_team_notes=[
                "Public court and email corpora may contain identity and sensitive facts even when public.",
                "Methodology references must not become payload ingestion.",
            ],
        ),
        _item(
            item_id="skills-registry-specialist-review",
            title="Skills Registry Specialist Review",
            workstream="skill_registry_review",
            owner="LawFirm-os-skills-registry",
            effort="medium",
            risk="high",
            gate="owner_repo_review",
            status="blocked_until_owner_action",
            why_now="Reusable specialist metadata needs supply-chain, tool authority, and eval review before promotion.",
            source_evidence_refs=[readiness_ref],
            required_next_actions=[
                "Review source reader, party-role extractor, matter router, deadline/gap extractor, evidence critic, budget planner, and frontier adjudicator metadata.",
                "Decide draft/promoted trust states inside Skills Registry.",
                "Keep frontier adjudication deny-by-default until prompt hashes, tool denylist, and evals are reviewed.",
            ],
            acceptance_evidence_required=[
                "Skills Registry PR or explicit rejection decision.",
                "Skill metadata with prompt hashes, allowed tools, forbidden context, and eval coverage.",
            ],
            red_team_notes=[
                "Long prompts are not safe skills without supply-chain review.",
                "Specialist promotion can accidentally expand model authority.",
            ],
        ),
        _item(
            item_id="governed-real-data-pilot",
            title="Governed Real-Data Pilot Decision",
            workstream="real_data_pilot_governance",
            owner="Cross-repo owners",
            effort="large",
            risk="critical",
            gate="production_pilot_approval",
            status="deferred_governance_required",
            why_now="Real data is the eventual proof point, but the current repo is synthetic-only and lacks owner-approved runtime contracts.",
            source_evidence_refs=[readiness_ref, closeout_ref],
            required_next_actions=[
                "Define a minimum viable real-data pilot scope outside intake.",
                "Approve data classes, retention, access controls, redaction, billing-read boundary, Lake admission, and human review gates.",
                "Run shadow mode before any production action or learning mutation.",
            ],
            acceptance_evidence_required=[
                "Cross-repo governance approval.",
                "Data protection and privilege review.",
                "Shadow-mode pilot report with no external actions and no silent learning.",
            ],
            red_team_notes=[
                "A real-data pilot before owner adoption would bypass the architecture this repo is trying to prove.",
                "Production connector payloads and negotiated rates are forbidden in this repo.",
            ],
        ),
    ]


def build_remaining_roadmap_report(
    *,
    readiness: IntakeVerticalReadinessAuditReport,
    readiness_ref: str,
    closeout: IntakeLocalCloseoutReport,
    closeout_ref: str,
    pr_decision: PRReadinessDecisionReport | None = None,
    pr_decision_ref: str | None = None,
) -> RemainingRoadmapReport:
    checks = _build_checks(
        readiness=readiness,
        readiness_ref=readiness_ref,
        closeout=closeout,
        closeout_ref=closeout_ref,
        pr_decision=pr_decision,
        pr_decision_ref=pr_decision_ref,
    )
    items = _roadmap_items(
        readiness_ref=readiness_ref,
        closeout_ref=closeout_ref,
        pr_decision_ref=pr_decision_ref,
    )
    failed = [check for check in checks if check.status == "failed"]
    next_ids = [
        "human-pr-review-and-state-decision",
        "manual-owner-issue-creation",
        "owner-triage-and-pr-splitting",
    ]
    return RemainingRoadmapReport(
        remaining_roadmap_report_id=_stable_id(
            "remainingroadmap",
            "|".join(
                [
                    readiness.audit_report_id,
                    closeout.closeout_report_id,
                    pr_decision.pr_readiness_decision_report_id
                    if pr_decision
                    else "no-pr-decision",
                ]
            ),
        ),
        status=(
            "blocked_by_source_evidence"
            if failed
            else "remaining_roadmap_ready_manual_execution_required"
        ),
        source_readiness_audit_report_id=readiness.audit_report_id,
        source_readiness_audit_report_ref=readiness_ref,
        source_readiness_status=readiness.status,
        source_closeout_report_id=closeout.closeout_report_id,
        source_closeout_report_ref=closeout_ref,
        source_closeout_status=closeout.status,
        source_pr_readiness_decision_report_id=(
            pr_decision.pr_readiness_decision_report_id if pr_decision else None
        ),
        source_pr_readiness_decision_report_ref=pr_decision_ref,
        source_pr_readiness_decision_status=pr_decision.status if pr_decision else None,
        source_pr_readiness_decision=pr_decision.decision if pr_decision else None,
        item_count=len(items),
        easy_item_count=sum(1 for item in items if item.effort == "easy"),
        medium_item_count=sum(1 for item in items if item.effort == "medium"),
        large_item_count=sum(1 for item in items if item.effort == "large"),
        critical_item_count=sum(1 for item in items if item.risk == "critical"),
        owner_gated_item_count=sum(
            1
            for item in items
            if item.gate
            in {
                "owner_repo_review",
                "cross_repo_validation",
                "governance_approval",
                "production_pilot_approval",
            }
        ),
        local_or_human_item_count=sum(
            1 for item in items if item.gate in {"local_candidate", "manual_human_review"}
        ),
        next_recommended_item_ids=next_ids,
        items=items,
        checks=checks,
        required_next_gates=REMAINING_ROADMAP_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_remaining_roadmap_report(report: RemainingRoadmapReport) -> str:
    lines = [
        "# Remaining Roadmap Report",
        "",
        f"**Report ID:** {report.remaining_roadmap_report_id}",
        f"**Status:** {report.status}",
        f"**Readiness audit:** `{report.source_readiness_audit_report_ref}` ({report.source_readiness_status})",
        f"**Local closeout:** `{report.source_closeout_report_ref}` ({report.source_closeout_status})",
        f"**PR decision:** `{report.source_pr_readiness_decision_report_ref or 'not supplied'}` ({report.source_pr_readiness_decision_status or 'not supplied'})",
        "",
        "## Summary",
        "",
        f"- Items: {report.item_count}",
        f"- Easy items: {report.easy_item_count}",
        f"- Medium items: {report.medium_item_count}",
        f"- Large items: {report.large_item_count}",
        f"- Critical-risk items: {report.critical_item_count}",
        f"- Owner-gated items: {report.owner_gated_item_count}",
        f"- Local/human-gated items: {report.local_or_human_item_count}",
        "",
        "## Next Recommended",
        "",
    ]
    by_id = {item.item_id: item for item in report.items}
    for item_id in report.next_recommended_item_ids:
        item = by_id[item_id]
        lines.append(
            f"- [ ] {item.title} (`{item.item_id}`): {item.owner}; {item.effort} effort; {item.risk} risk."
        )
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(["", "## Items", ""])
    for item in report.items:
        lines.extend(
            [
                f"### {item.title}",
                "",
                f"- ID: `{item.item_id}`",
                f"- Owner: {item.owner}",
                f"- Workstream: {item.workstream}",
                f"- Effort: {item.effort}",
                f"- Risk: {item.risk}",
                f"- Gate: {item.gate}",
                f"- Status: {item.status}",
                f"- Why now: {item.why_now}",
                "- Required next actions:",
                *(f"  - [ ] {action}" for action in item.required_next_actions),
                "- Acceptance evidence required:",
                *(f"  - {evidence}" for evidence in item.acceptance_evidence_required),
                "- Red-team notes:",
                *(f"  - {note}" for note in item.red_team_notes),
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Proposed changes applied: {report.proposed_changes_applied}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This roadmap is local planning evidence only. It does not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, approve real-data pilots, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_remaining_roadmap_plan(
    *,
    readiness_audit_report_path: str | Path,
    intake_local_closeout_report_path: str | Path,
    out_dir: str | Path,
    pr_readiness_decision_report_path: str | Path | None = None,
) -> tuple[RemainingRoadmapReport, Path]:
    readiness_path = Path(readiness_audit_report_path)
    closeout_path = Path(intake_local_closeout_report_path)
    pr_decision_path = (
        Path(pr_readiness_decision_report_path) if pr_readiness_decision_report_path else None
    )
    pr_decision = (
        PRReadinessDecisionReport.model_validate(load_json(pr_decision_path))
        if pr_decision_path
        else None
    )
    report = build_remaining_roadmap_report(
        readiness=IntakeVerticalReadinessAuditReport.model_validate(load_json(readiness_path)),
        readiness_ref=str(readiness_path),
        closeout=IntakeLocalCloseoutReport.model_validate(load_json(closeout_path)),
        closeout_ref=str(closeout_path),
        pr_decision=pr_decision,
        pr_decision_ref=str(pr_decision_path) if pr_decision_path else None,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    items_path = run_dir / REMAINING_ROADMAP_ITEMS_FILENAME
    if items_path.exists():
        items_path.unlink()
    for item in report.items:
        append_jsonl(items_path, item.model_dump(mode="json"))
    write_json(run_dir / REMAINING_ROADMAP_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / REMAINING_ROADMAP_NOTES_FILENAME).write_text(
        render_remaining_roadmap_report(report),
        encoding="utf-8",
    )
    return report, run_dir
