from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import (
    LearningOwnerHandoffItem,
    LearningOwnerHandoffPackage,
    LearningOwnerHandoffReport,
    LearningShadowEvalResult,
    LearningShadowEvalResultReport,
)
from .util import append_jsonl, digest_text, load_json, new_id, now_iso, write_json


LEARNING_OWNER_HANDOFF_REPORT_FILENAME = "learning_owner_handoff_report.json"
LEARNING_OWNER_HANDOFF_NOTES_FILENAME = "learning_owner_handoff_report.md"
LEARNING_OWNER_HANDOFF_PACKAGES_FILENAME = "learning_owner_handoff_packages.jsonl"
LEARNING_OWNER_HANDOFF_DIRNAME = "owner_handoffs"

REQUIRED_NEXT_GATES = [
    "human_shadow_eval_review",
    "owning_repo_review",
    "promotion_decision_by_owning_repo",
    "contract_pinning_after_owning_repo_promotion",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _owner_slug(owner: str) -> str:
    return owner.lower().replace("lawfirm-os-", "").replace("_", "-")


def _disposition(result: LearningShadowEvalResult) -> str:
    if result.status == "passed_for_owning_repo_review":
        return "ready_for_owner_review"
    if result.status == "failed_shadow_eval":
        return "failed_before_owner_review"
    return "blocked_before_owner_review"


def _owner_actions(result: LearningShadowEvalResult) -> list[str]:
    if result.status == "passed_for_owning_repo_review":
        return [
            "Review synthetic shadow-eval evidence and red-team objections.",
            "Decide whether an owning-repo implementation proposal is warranted.",
            "If accepted, create the change inside the owning repo and keep intake as a candidate/eval consumer.",
        ]
    if result.status == "failed_shadow_eval":
        return [
            "Do not promote or implement the proposed change.",
            "Review failed eval suites or regression guardrails.",
            "Return the candidate to intake learning review with corrected evidence or decline it.",
        ]
    return [
        "Do not promote or implement the proposed change.",
        "Supply missing fixture, eval, guardrail, or matching evidence before owner review.",
        "Keep the candidate blocked in intake until the shadow-eval result is repaired.",
    ]


def _item_for_result(result: LearningShadowEvalResult) -> LearningOwnerHandoffItem:
    return LearningOwnerHandoffItem(
        handoff_item_id=_stable_id("ownerhandoffitem", result.shadow_eval_result_id),
        shadow_eval_result_id=result.shadow_eval_result_id,
        proposed_change_id=result.proposed_change_id,
        candidate_id=result.candidate_id,
        target_learning_loop=result.target_learning_loop,
        target_owner=result.target_owner,
        change_type=result.change_type,
        shadow_eval_status=result.status,
        disposition=_disposition(result),  # type: ignore[arg-type]
        passed_checks=result.passed_checks,
        failed_checks=result.failed_checks,
        blocked_checks=result.blocked_checks,
        required_owner_actions=_owner_actions(result),
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def _package_status(items: list[LearningOwnerHandoffItem]) -> str:
    ready = [item for item in items if item.disposition == "ready_for_owner_review"]
    blocked_or_failed = [item for item in items if item.disposition != "ready_for_owner_review"]
    if ready and not blocked_or_failed:
        return "ready_for_owner_review"
    if ready and blocked_or_failed:
        return "mixed_review_and_blockers"
    return "blocked_or_failed_before_review"


def _review_scope(package: LearningOwnerHandoffPackage) -> list[str]:
    scope = [
        "Confirm this package is candidate-only and non-authoritative.",
        "Verify that no proposed change was applied in LawFirm-os-intake.",
    ]
    if package.ready_items:
        scope.append("Review passed candidates for possible owning-repo implementation work.")
    if package.failed_items:
        scope.append("Review failed candidates and decide whether to decline or return for repair.")
    if package.blocked_items:
        scope.append("Keep blocked candidates out of promotion until missing evidence is supplied.")
    scope.append(
        "Do not assign canonical route IDs, event classes, or schema authority from this package."
    )
    return scope


def _package_for_owner(
    *,
    owner: str,
    source_report: LearningShadowEvalResultReport,
    items: list[LearningOwnerHandoffItem],
) -> LearningOwnerHandoffPackage:
    ready_items = [item for item in items if item.disposition == "ready_for_owner_review"]
    failed_items = [item for item in items if item.disposition == "failed_before_owner_review"]
    blocked_items = [item for item in items if item.disposition == "blocked_before_owner_review"]
    package = LearningOwnerHandoffPackage(
        owner_handoff_package_id=_stable_id(
            "ownerhandoff", f"{source_report.shadow_eval_result_report_id}|{owner}"
        ),
        target_owner=owner,  # type: ignore[arg-type]
        source_shadow_eval_result_report_id=source_report.shadow_eval_result_report_id,
        status=_package_status(items),  # type: ignore[arg-type]
        item_count=len(items),
        passed_candidate_count=len(ready_items),
        failed_candidate_count=len(failed_items),
        blocked_candidate_count=len(blocked_items),
        ready_items=ready_items,
        failed_items=failed_items,
        blocked_items=blocked_items,
        required_owner_review_scope=[],
        required_next_gates=REQUIRED_NEXT_GATES,
    )
    return package.model_copy(update={"required_owner_review_scope": _review_scope(package)})


def _report_status(packages: list[LearningOwnerHandoffPackage]) -> str:
    passed = sum(package.passed_candidate_count for package in packages)
    failed = sum(package.failed_candidate_count for package in packages)
    blocked = sum(package.blocked_candidate_count for package in packages)
    if not packages:
        return "no_learning_candidates"
    if passed and not failed and not blocked:
        return "owner_handoff_ready_review_required"
    if passed and (failed or blocked):
        return "owner_handoff_mixed_review_and_blockers"
    return "owner_handoff_blocked_or_failed"


def build_learning_owner_handoff_report(
    *,
    shadow_eval_result_report: LearningShadowEvalResultReport,
    shadow_eval_result_report_ref: str,
) -> LearningOwnerHandoffReport:
    grouped: dict[str, list[LearningOwnerHandoffItem]] = defaultdict(list)
    for result in shadow_eval_result_report.results:
        grouped[result.target_owner].append(_item_for_result(result))

    packages = [
        _package_for_owner(
            owner=owner,
            source_report=shadow_eval_result_report,
            items=items,
        )
        for owner, items in sorted(grouped.items())
    ]
    return LearningOwnerHandoffReport(
        owner_handoff_report_id=new_id("ownerhandoffreport"),
        source_shadow_eval_result_report_id=(
            shadow_eval_result_report.shadow_eval_result_report_id
        ),
        source_shadow_eval_result_report_ref=shadow_eval_result_report_ref,
        status=_report_status(packages),  # type: ignore[arg-type]
        package_count=len(packages),
        target_owners=[package.target_owner for package in packages],
        passed_candidate_count=sum(package.passed_candidate_count for package in packages),
        failed_candidate_count=sum(package.failed_candidate_count for package in packages),
        blocked_candidate_count=sum(package.blocked_candidate_count for package in packages),
        packages=packages,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_learning_owner_handoff_package(package: LearningOwnerHandoffPackage) -> str:
    lines = [
        "# Learning Owner Handoff Package",
        "",
        f"**Package ID:** {package.owner_handoff_package_id}",
        f"**Target owner:** {package.target_owner}",
        f"**Status:** {package.status}",
        f"**Passed:** {package.passed_candidate_count}",
        f"**Failed:** {package.failed_candidate_count}",
        f"**Blocked:** {package.blocked_candidate_count}",
        "",
        "## Boundary",
        "",
        f"- Promotion authorized: {package.promotion_authorized}",
        f"- Proposed changes applied: {package.proposed_changes_applied}",
        f"- Lake write performed: {package.lake_write_performed}",
        f"- SQLite write performed: {package.sqlite_write_performed}",
        f"- External writes performed: {package.external_writes_performed}",
        f"- Silent learning performed: {package.silent_learning_performed}",
        "",
        "## Owner Review Scope",
        "",
        *(f"- {item}" for item in package.required_owner_review_scope),
        "",
    ]
    for title, items in [
        ("Ready Items", package.ready_items),
        ("Failed Items", package.failed_items),
        ("Blocked Items", package.blocked_items),
    ]:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.append("- none")
        for item in items:
            lines.extend(
                [
                    f"- `{item.handoff_item_id}`: change={item.proposed_change_id}; "
                    f"candidate={item.candidate_id}; loop={item.target_learning_loop}; "
                    f"disposition={item.disposition}",
                    "  Required owner actions:",
                    *(f"  - {action}" for action in item.required_owner_actions),
                ]
            )
        lines.append("")
    lines.append(
        "This package is an owner-review handoff only. It does not promote, apply, or authorize any learning change."
    )
    lines.append("")
    return "\n".join(lines)


def render_learning_owner_handoff_report(report: LearningOwnerHandoffReport) -> str:
    lines = [
        "# Learning Owner Handoff Report",
        "",
        f"**Report ID:** {report.owner_handoff_report_id}",
        f"**Status:** {report.status}",
        f"**Package count:** {report.package_count}",
        f"**Passed:** {report.passed_candidate_count}",
        f"**Failed:** {report.failed_candidate_count}",
        f"**Blocked:** {report.blocked_candidate_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Non-authoritative: {report.non_authoritative}",
        f"- Promotion authorized: {report.promotion_authorized}",
        f"- Proposed changes applied: {report.proposed_changes_applied}",
        f"- Baseline mutated: {report.baseline_mutated}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Owner Packages",
        "",
    ]
    if not report.packages:
        lines.append("- none")
    for package in report.packages:
        lines.append(
            f"- `{package.target_owner}`: status={package.status}; "
            f"passed={package.passed_candidate_count}; failed={package.failed_candidate_count}; "
            f"blocked={package.blocked_candidate_count}"
        )
    lines.extend(
        [
            "",
            "Owner packages separate passed, failed, and blocked candidates. Passing packages still require human review and owning-repo promotion decisions outside intake.",
            "",
        ]
    )
    return "\n".join(lines)


def run_learning_owner_handoffs(
    *,
    shadow_eval_result_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[LearningOwnerHandoffReport, Path]:
    source_path = Path(shadow_eval_result_report_path)
    shadow_eval_result_report = LearningShadowEvalResultReport.model_validate(
        load_json(source_path)
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    package_dir = run_dir / LEARNING_OWNER_HANDOFF_DIRNAME
    package_dir.mkdir(parents=True, exist_ok=True)

    report = build_learning_owner_handoff_report(
        shadow_eval_result_report=shadow_eval_result_report,
        shadow_eval_result_report_ref=str(source_path),
    )
    package_refs = []
    packages_path = run_dir / LEARNING_OWNER_HANDOFF_PACKAGES_FILENAME
    packages_path.touch()
    for package in report.packages:
        slug = _owner_slug(package.target_owner)
        package_path = package_dir / f"{slug}.json"
        package_notes_path = package_dir / f"{slug}.md"
        write_json(package_path, package.model_dump(mode="json"))
        package_notes_path.write_text(
            render_learning_owner_handoff_package(package),
            encoding="utf-8",
        )
        append_jsonl(packages_path, package.model_dump(mode="json"))
        package_refs.append(str(package_path))

    report = report.model_copy(update={"package_output_refs": package_refs})
    report_path = run_dir / LEARNING_OWNER_HANDOFF_REPORT_FILENAME
    notes_path = run_dir / LEARNING_OWNER_HANDOFF_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_learning_owner_handoff_report(report), encoding="utf-8")
    return report, run_dir
