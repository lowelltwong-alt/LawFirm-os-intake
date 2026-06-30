from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import (
    PRMergeOrderCheck,
    PRMergeOrderReadinessPacket,
    PRMergeOrderRecommendation,
    PRMergeOrderSharedSurface,
    PRMergeOrderSnapshot,
    PRMergeOrderSnapshotItem,
)
from .util import digest_text, load_json, now_iso, write_json


PR_MERGE_ORDER_PACKET_FILENAME = "pr_merge_order_readiness_packet.json"
PR_MERGE_ORDER_NOTES_FILENAME = "pr_merge_order_readiness_packet.md"

READY_MERGEABLE_STATES = {"MERGEABLE", "CLEAN"}
READY_CHECKS_CONCLUSIONS = {"success"}
HIGH_RISK_SHARED_SURFACES = {
    ".ai/control/governance-dependency-map-mirror.json",
    "docs/roadmap.md",
    "docs/evaluation-plan.md",
    "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json",
    "tests/test_synthetic_fixture_expansion.py",
    "src/lawfirm_os_intake/cli.py",
    "src/lawfirm_os_intake/models.py",
    "scripts/export_schemas.py",
}

PR_MERGE_ORDER_REQUIRED_NEXT_GATES = [
    "manual_pr_review_before_any_merge",
    "manual_github_merge_or_ready_state_change_if_accepted",
    "rebase_and_rerun_ci_after_each_shared_surface_merge",
    "run_depth_audit_after_fixture_gap_prs",
    "run_full_long_ceiling_validation_after_each_merge",
    "no_automated_github_write",
    "no_sibling_repo_or_lake_write",
]

VALIDATION_REQUIRED = [
    "python scripts/validate_repo.py",
    "python scripts/export_schemas.py",
    "python -m ruff check src tests scripts",
    "python -m ruff format --check src tests scripts",
    "python scripts/run_full_pytest.py",
    "bash scripts/smoke_demo.sh",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
    warning: bool = False,
) -> PRMergeOrderCheck:
    return PRMergeOrderCheck(
        check_id=check_id,
        status="warning" if warning else ("passed" if passed else "failed"),
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed or warning else artifact_refs or []),
    )


def _item_boundary_clear(pr: PRMergeOrderSnapshotItem) -> bool:
    return (
        pr.ready_for_review_marked is False
        and pr.merge_performed is False
        and pr.github_write_performed is False
        and pr.sibling_repo_write_performed is False
        and pr.promotion_authorized is False
        and pr.lake_write_performed is False
        and pr.sqlite_write_performed is False
        and pr.external_writes_performed is False
        and pr.silent_learning_performed is False
    )


def _snapshot_boundary_clear(snapshot: PRMergeOrderSnapshot) -> bool:
    return (
        snapshot.ready_for_review_marked is False
        and snapshot.merge_performed is False
        and snapshot.github_issue_created is False
        and snapshot.github_pr_created is False
        and snapshot.github_write_performed is False
        and snapshot.sibling_repo_write_performed is False
        and snapshot.promotion_authorized is False
        and snapshot.lake_write_performed is False
        and snapshot.sqlite_write_performed is False
        and snapshot.external_writes_performed is False
        and snapshot.silent_learning_performed is False
        and all(_item_boundary_clear(pr) for pr in snapshot.prs)
    )


def _is_ready_for_manual_queue(pr: PRMergeOrderSnapshotItem) -> bool:
    return (
        pr.observed_state == "open"
        and pr.is_draft is True
        and pr.mergeable_state in READY_MERGEABLE_STATES
        and pr.checks_conclusion in READY_CHECKS_CONCLUSIONS
        and pr.status_check_count > 0
        and pr.status_check_count == pr.successful_status_check_count
        and bool(pr.changed_files)
        and _item_boundary_clear(pr)
    )


def _sequence_priority(pr: PRMergeOrderSnapshotItem) -> tuple[int, int]:
    gaps = set(pr.depth_gap_ids_addressed)
    title = pr.title.lower()
    head = pr.head_ref_name.lower()
    if "labor_employment_budget_fact_gap_holdout" in gaps or "l&e" in title:
        return (10, pr.pr_number)
    if "carrier_partial_allowance_and_appeal_outcome_variety" in gaps:
        return (20, pr.pr_number)
    if (
        pr.recommended_sequence_role == "fixture_role_expander"
        or "ambiguous-role" in head
        or "ambiguous role" in title
    ):
        return (30, pr.pr_number)
    if pr.recommended_sequence_role == "audit_verifier" or "depth-audit" in head:
        return (90, pr.pr_number)
    if pr.recommended_sequence_role == "fixture_gap_closer":
        return (40, pr.pr_number)
    return (50, pr.pr_number)


def _shared_surface_risk(surface_ref: str, pr_numbers: list[int]) -> str:
    if len(pr_numbers) >= 3 or surface_ref in HIGH_RISK_SHARED_SURFACES:
        return "high"
    return "medium"


def _build_shared_surfaces(snapshot: PRMergeOrderSnapshot) -> list[PRMergeOrderSharedSurface]:
    by_surface: dict[str, set[int]] = defaultdict(set)
    for pr in snapshot.prs:
        for path in pr.changed_files:
            by_surface[_normalize_path(path)].add(pr.pr_number)

    shared = []
    for surface_ref, numbers in sorted(by_surface.items()):
        pr_numbers = sorted(numbers)
        if len(pr_numbers) < 2:
            continue
        risk = _shared_surface_risk(surface_ref, pr_numbers)
        reason = (
            "Multiple draft PRs touch this surface; merge order and rebases can change "
            "the final observed evidence."
        )
        if risk == "high":
            reason = (
                "This is a governance, roadmap, manifest, schema, CLI, model, or shared "
                "test surface touched by multiple drafts; humans should expect rebase "
                "and validation churn."
            )
        shared.append(
            PRMergeOrderSharedSurface(
                surface_ref=surface_ref,
                pr_numbers=pr_numbers,
                risk=risk,  # type: ignore[arg-type]
                reason=reason,
            )
        )
    return shared


def _recommendation_reason(pr: PRMergeOrderSnapshotItem) -> str:
    if pr.recommended_sequence_role == "audit_verifier":
        return (
            "Land after the fixture gap PRs so the depth audit reflects the updated "
            "holdout set instead of preserving a stale gap report."
        )
    if pr.recommended_sequence_role == "fixture_gap_closer":
        return (
            "Land before the depth audit because this draft closes a known fixture "
            "coverage gap that the audit is expected to measure."
        )
    if pr.recommended_sequence_role == "fixture_role_expander":
        return (
            "Land after direct gap closers and before the audit verifier because it "
            "hardens adjacent role-ambiguity coverage without owning the audit."
        )
    return "Land before the audit verifier unless a human reviewer finds a stronger dependency."


def _manual_actions(pr: PRMergeOrderSnapshotItem, shared_refs: list[str]) -> list[str]:
    actions = [
        f"Review draft PR #{pr.pr_number} in GitHub as a human action.",
        "If accepted, perform any ready-for-review or merge state change manually in GitHub.",
        "Preserve the PR's validation evidence and review discussion as source evidence.",
    ]
    if shared_refs:
        actions.append(
            "After this PR lands, rebase later draft PRs that touch shared surfaces: "
            + ", ".join(shared_refs)
        )
    return actions


def _red_team_notes(pr: PRMergeOrderSnapshotItem, shared_refs: list[str]) -> list[str]:
    notes = [
        "A green draft PR is not authority for production use or owner-repo adoption.",
        "This packet is a queue recommendation only; it does not merge, mark ready, or call GitHub write APIs.",
    ]
    if pr.recommended_sequence_role == "audit_verifier":
        notes.append(
            "If the audit lands before gap-closing fixtures, it can make current-main gaps look like roadmap truth."
        )
    if shared_refs:
        notes.append(
            "Shared surfaces can hide semantic conflicts even when GitHub reports the PR as mergeable."
        )
    return notes


def _build_recommendations(
    *,
    ready_prs: list[PRMergeOrderSnapshotItem],
    shared_surfaces: list[PRMergeOrderSharedSurface],
) -> list[PRMergeOrderRecommendation]:
    by_pr = defaultdict(list)
    for surface in shared_surfaces:
        for pr_number in surface.pr_numbers:
            by_pr[pr_number].append(surface.surface_ref)

    recommendations = []
    prior_numbers: list[int] = []
    for index, pr in enumerate(sorted(ready_prs, key=_sequence_priority), start=1):
        shared_refs = sorted(by_pr[pr.pr_number])
        recommendations.append(
            PRMergeOrderRecommendation(
                order_index=index,
                pr_number=pr.pr_number,
                title=pr.title,
                head_ref_name=pr.head_ref_name,
                recommended_sequence_role=pr.recommended_sequence_role,
                recommended_after_pr_numbers=prior_numbers.copy(),
                shared_surface_refs=shared_refs,
                reason=_recommendation_reason(pr),
                required_manual_actions=_manual_actions(pr, shared_refs),
                validation_required=VALIDATION_REQUIRED,
                red_team_notes=_red_team_notes(pr, shared_refs),
            )
        )
        prior_numbers.append(pr.pr_number)
    return recommendations


def _build_checks(
    *,
    snapshot: PRMergeOrderSnapshot,
    snapshot_ref: str,
    shared_surfaces: list[PRMergeOrderSharedSurface],
) -> list[PRMergeOrderCheck]:
    open_draft_blockers = [
        f"PR #{pr.pr_number}"
        for pr in snapshot.prs
        if not (pr.observed_state == "open" and pr.is_draft is True)
    ]
    mergeable_blockers = [
        f"PR #{pr.pr_number}"
        for pr in snapshot.prs
        if not (
            pr.mergeable_state in READY_MERGEABLE_STATES
            and pr.checks_conclusion in READY_CHECKS_CONCLUSIONS
            and pr.status_check_count > 0
            and pr.status_check_count == pr.successful_status_check_count
        )
    ]
    changed_file_blockers = [f"PR #{pr.pr_number}" for pr in snapshot.prs if not pr.changed_files]
    boundary_blockers = [
        f"PR #{pr.pr_number}" for pr in snapshot.prs if not _item_boundary_clear(pr)
    ]
    return [
        _check(
            "pr_snapshot_has_open_draft_prs",
            bool(snapshot.prs) and not open_draft_blockers,
            "Every PR in the snapshot is an open draft requiring human review.",
            artifact_refs=[snapshot_ref],
            blocking_refs=open_draft_blockers,
        ),
        _check(
            "pr_snapshot_mergeable_and_checks_green",
            not mergeable_blockers,
            "Every draft PR is observed mergeable with successful status checks.",
            artifact_refs=[snapshot_ref],
            blocking_refs=mergeable_blockers,
        ),
        _check(
            "pr_snapshot_has_changed_file_evidence",
            not changed_file_blockers,
            "Every draft PR includes changed-file evidence for shared-surface analysis.",
            artifact_refs=[snapshot_ref],
            blocking_refs=changed_file_blockers,
        ),
        _check(
            "pr_merge_order_no_side_effects",
            _snapshot_boundary_clear(snapshot) and not boundary_blockers,
            "The snapshot and PR items show no ready-state, merge, GitHub write, sibling repo, Lake, SQLite, external write, or learning side effects.",
            artifact_refs=[snapshot_ref],
            blocking_refs=boundary_blockers,
        ),
        _check(
            "shared_surfaces_require_rebase_attention",
            True,
            "Shared surfaces were identified for manual merge-order and rebase attention.",
            artifact_refs=[surface.surface_ref for surface in shared_surfaces],
            warning=bool(shared_surfaces),
        ),
    ]


def build_pr_merge_order_readiness_packet(
    *,
    snapshot: PRMergeOrderSnapshot,
    snapshot_ref: str,
) -> PRMergeOrderReadinessPacket:
    shared_surfaces = _build_shared_surfaces(snapshot)
    checks = _build_checks(
        snapshot=snapshot,
        snapshot_ref=snapshot_ref,
        shared_surfaces=shared_surfaces,
    )
    ready_prs = [pr for pr in snapshot.prs if _is_ready_for_manual_queue(pr)]
    blocked_pr_numbers = sorted(
        pr.pr_number for pr in snapshot.prs if not _is_ready_for_manual_queue(pr)
    )
    recommendations = _build_recommendations(
        ready_prs=ready_prs,
        shared_surfaces=shared_surfaces,
    )
    failed = [check for check in checks if check.status == "failed"]
    recommended_numbers = [item.pr_number for item in recommendations]
    return PRMergeOrderReadinessPacket(
        packet_id=_stable_id(
            "prmergeorder",
            "|".join(
                [
                    snapshot.snapshot_id,
                    snapshot.repository_full_name,
                    ",".join(str(pr.pr_number) for pr in snapshot.prs),
                ]
            ),
        ),
        status=(
            "blocked_by_pr_merge_order_evidence"
            if failed
            else "pr_merge_order_ready_manual_queue_required"
        ),
        source_snapshot_id=snapshot.snapshot_id,
        source_snapshot_ref=snapshot_ref,
        repository_full_name=snapshot.repository_full_name,
        base_ref_name=snapshot.base_ref_name,
        strategy="gap_first_then_depth_audit",
        pr_count=len(snapshot.prs),
        ready_queue_count=len(recommendations),
        blocked_pr_count=len(blocked_pr_numbers),
        recommended_merge_order_pr_numbers=recommended_numbers,
        blocked_pr_numbers=blocked_pr_numbers,
        shared_surface_count=len(shared_surfaces),
        high_risk_shared_surface_count=sum(
            1 for surface in shared_surfaces if surface.risk == "high"
        ),
        recommendations=recommendations,
        shared_surfaces=shared_surfaces,
        checks=checks,
        required_next_gates=PR_MERGE_ORDER_REQUIRED_NEXT_GATES,
        observed_at=snapshot.observed_at,
        generated_at=now_iso(),
    )


def render_pr_merge_order_readiness_packet(report: PRMergeOrderReadinessPacket) -> str:
    lines = [
        "# PR Merge Order Readiness Packet",
        "",
        f"**Packet ID:** {report.packet_id}",
        f"**Status:** {report.status}",
        f"**Repository:** {report.repository_full_name}",
        f"**Base ref:** {report.base_ref_name}",
        f"**Snapshot:** `{report.source_snapshot_ref}`",
        f"**Strategy:** {report.strategy}",
        "",
        "## Summary",
        "",
        f"- PRs: {report.pr_count}",
        f"- Ready queue: {report.ready_queue_count}",
        f"- Blocked PRs: {report.blocked_pr_count}",
        f"- Shared surfaces: {report.shared_surface_count}",
        f"- High-risk shared surfaces: {report.high_risk_shared_surface_count}",
        f"- Recommended order: {', '.join(f'#{n}' for n in report.recommended_merge_order_pr_numbers)}",
        "",
        "## Recommended Manual Queue",
        "",
    ]
    for item in report.recommendations:
        lines.extend(
            [
                f"### {item.order_index}. PR #{item.pr_number}: {item.title}",
                "",
                f"- Branch: `{item.head_ref_name}`",
                f"- Role: {item.recommended_sequence_role}",
                f"- After PRs: {', '.join(f'#{n}' for n in item.recommended_after_pr_numbers) or 'none'}",
                f"- Shared surfaces: {', '.join(f'`{ref}`' for ref in item.shared_surface_refs) or 'none'}",
                f"- Reason: {item.reason}",
                "- Required manual actions:",
                *(f"  - [ ] {action}" for action in item.required_manual_actions),
                "- Validation required:",
                *(f"  - {command}" for command in item.validation_required),
                "- Red-team notes:",
                *(f"  - {note}" for note in item.red_team_notes),
                "",
            ]
        )
    lines.extend(["## Shared Surfaces", ""])
    for surface in report.shared_surfaces:
        lines.append(
            f"- `{surface.surface_ref}`: {surface.risk}; PRs "
            f"{', '.join(f'#{number}' for number in surface.pr_numbers)}. {surface.reason}"
        )
    if not report.shared_surfaces:
        lines.append("- none")
    lines.extend(["", "## Checks", ""])
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
            f"- Ready for review marked: {report.ready_for_review_marked}",
            f"- Merge performed: {report.merge_performed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This packet is local candidate evidence only. It consumes an observed PR snapshot and does not mark any PR ready, merge any PR, call GitHub write APIs, create issues, write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_pr_merge_order_readiness_packet(
    *,
    pr_snapshot_path: str | Path,
    out_dir: str | Path,
) -> tuple[PRMergeOrderReadinessPacket, Path]:
    snapshot_path = Path(pr_snapshot_path)
    snapshot = PRMergeOrderSnapshot.model_validate(load_json(snapshot_path))
    report = build_pr_merge_order_readiness_packet(
        snapshot=snapshot,
        snapshot_ref=str(snapshot_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / PR_MERGE_ORDER_PACKET_FILENAME, report.model_dump(mode="json"))
    (run_dir / PR_MERGE_ORDER_NOTES_FILENAME).write_text(
        render_pr_merge_order_readiness_packet(report),
        encoding="utf-8",
    )
    return report, run_dir
