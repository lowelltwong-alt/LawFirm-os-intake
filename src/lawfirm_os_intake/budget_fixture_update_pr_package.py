from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetFixtureUpdatePRPackageCheck,
    BudgetFixtureUpdatePRPackageItem,
    BudgetFixtureUpdatePRPackageReport,
    BudgetFixtureUpdateReviewReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_FIXTURE_UPDATE_PR_PACKAGE_REPORT_FILENAME = "budget_fixture_update_pr_package_report.json"
BUDGET_FIXTURE_UPDATE_PR_PACKAGE_NOTES_FILENAME = "budget_fixture_update_pr_package_report.md"
BUDGET_FIXTURE_UPDATE_PR_PACKAGE_ITEMS_FILENAME = "budget_fixture_update_pr_package_items.jsonl"

BUDGET_FIXTURE_UPDATE_PR_PACKAGE_REQUIRED_NEXT_GATES = [
    "manual_fixture_update_pr_review",
    "apply_fixture_update_only_in_separate_pr",
    "run_regression_after_fixture_update_pr",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
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
) -> BudgetFixtureUpdatePRPackageCheck:
    return BudgetFixtureUpdatePRPackageCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _review_boundary_clear(report: BudgetFixtureUpdateReviewReport) -> bool:
    return (
        report.source_readiness_report_mutated is False
        and report.fixture_update_pr_created is False
        and report.fixture_files_mutated is False
        and report.fixture_binding_applied is False
        and report.downstream_learning_gate_allowed is False
        and report.calibration_applied is False
        and report.profile_mutation_performed is False
        and report.template_mutation_performed is False
        and report.budget_mutation_performed is False
        and report.carrier_guideline_mutation_performed is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _build_item(
    *,
    review_report: BudgetFixtureUpdateReviewReport,
    target_fixture_ref: str,
) -> BudgetFixtureUpdatePRPackageItem:
    return BudgetFixtureUpdatePRPackageItem(
        package_item_id=_stable_id(
            "budgetfixtureupdatepritem",
            f"{review_report.fixture_update_review_id}|{target_fixture_ref}",
        ),
        fixture_update_review_id=review_report.fixture_update_review_id,
        decision=review_report.decision,
        accepted_output_refs=review_report.accepted_output_refs,
        target_fixture_ref=target_fixture_ref,
        proposed_manual_action="update_synthetic_fixture_in_separate_pr",
        manual_patch_summary=(
            "Use the accepted replay output refs to update the target synthetic fixture "
            "in a separate human-reviewed fixture-update PR. Preserve superseded fixture "
            "evidence instead of silently rewriting calibration history."
        ),
        reviewer_corrections=review_report.reviewer_corrections,
        required_manual_steps=[
            "Inspect the accepted replay output refs and target fixture before editing.",
            "Create a separate fixture-update branch or PR if the reviewer accepts the change.",
            "Apply fixture edits manually in that separate PR only.",
            "Rerun regression, replay, and shadow-eval checks after any fixture edit.",
            "Keep learning blocked until reviewed-learning and owning-repo gates pass.",
        ],
        red_team_notes=[
            "This package is a patch plan, not a patch application.",
            "Accepted fixture updates can encode bad replay output as reviewed gold if the output is not inspected.",
            "Do not mutate profiles, templates, budgets, carrier guidelines, or learning candidates from this package.",
        ],
        required_next_gates=BUDGET_FIXTURE_UPDATE_PR_PACKAGE_REQUIRED_NEXT_GATES,
    )


def build_budget_fixture_update_pr_package_report(
    *,
    fixture_update_review_report: BudgetFixtureUpdateReviewReport,
    fixture_update_review_report_ref: str,
) -> BudgetFixtureUpdatePRPackageReport:
    failed_review_checks = [
        check.check_id for check in fixture_update_review_report.checks if check.status == "failed"
    ]
    accepted = (
        fixture_update_review_report.status == "fixture_update_review_recorded_separate_pr_required"
        and fixture_update_review_report.accepted_for_fixture_update_pr
        and fixture_update_review_report.separate_fixture_update_pr_required
    )
    items = [
        _build_item(
            review_report=fixture_update_review_report,
            target_fixture_ref=target_fixture_ref,
        )
        for target_fixture_ref in fixture_update_review_report.target_fixture_refs
        if accepted
    ]
    source_ready = fixture_update_review_report.status in {
        "fixture_update_review_recorded_separate_pr_required",
        "fixture_update_review_recorded_no_fixture_pr",
    }
    checks = [
        _check(
            "fixture_update_review_recorded_without_writes",
            source_ready
            and not failed_review_checks
            and _review_boundary_clear(fixture_update_review_report),
            "Fixture-update review report is recorded and preserves no-write/no-learning boundaries.",
            artifact_refs=[fixture_update_review_report_ref],
            blocking_refs=failed_review_checks,
        ),
        _check(
            "accepted_review_refs_packaged",
            (not accepted)
            or (
                bool(fixture_update_review_report.accepted_output_refs)
                and bool(fixture_update_review_report.target_fixture_refs)
                and len(items) == len(fixture_update_review_report.target_fixture_refs)
            ),
            "Accepted fixture-update refs are represented in manual PR package items.",
            artifact_refs=[
                *fixture_update_review_report.accepted_output_refs,
                *fixture_update_review_report.target_fixture_refs,
            ],
        ),
        _check(
            "package_does_not_apply_patch",
            True,
            "Package generation creates review instructions only and does not edit fixtures or create a PR.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "blocked_by_fixture_update_review"
    elif accepted:
        status = "fixture_update_pr_package_ready_for_manual_pr"
    else:
        status = "no_fixture_update_pr_package_needed"
    return BudgetFixtureUpdatePRPackageReport(
        fixture_update_pr_package_report_id=_stable_id(
            "budgetfixtureupdateprpackage",
            "|".join(
                [
                    fixture_update_review_report.fixture_update_review_report_id,
                    fixture_update_review_report.fixture_update_review_id,
                    fixture_update_review_report.decision,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_budget_fixture_update_review_report_id=(
            fixture_update_review_report.fixture_update_review_report_id
        ),
        source_budget_fixture_update_review_report_ref=fixture_update_review_report_ref,
        source_budget_fixture_update_review_status=fixture_update_review_report.status,
        fixture_update_review_id=fixture_update_review_report.fixture_update_review_id,
        decision=fixture_update_review_report.decision,
        item_count=len(items),
        ready_item_count=len(items)
        if status == "fixture_update_pr_package_ready_for_manual_pr"
        else 0,
        blocked_item_count=len(items) if status == "blocked_by_fixture_update_review" else 0,
        accepted_output_refs=fixture_update_review_report.accepted_output_refs,
        target_fixture_refs=fixture_update_review_report.target_fixture_refs,
        package_items=items,
        checks=checks,
        required_next_gates=BUDGET_FIXTURE_UPDATE_PR_PACKAGE_REQUIRED_NEXT_GATES,
        manual_fixture_update_pr_required=(
            status == "fixture_update_pr_package_ready_for_manual_pr"
        ),
        generated_at=now_iso(),
    )


def render_budget_fixture_update_pr_package_report(
    report: BudgetFixtureUpdatePRPackageReport,
) -> str:
    lines = [
        "# Budget Fixture Update PR Package",
        "",
        f"**Report ID:** {report.fixture_update_pr_package_report_id}",
        f"**Status:** {report.status}",
        f"**Source review report:** `{report.source_budget_fixture_update_review_report_ref}`",
        f"**Decision:** {report.decision}",
        f"**Manual fixture-update PR required:** {report.manual_fixture_update_pr_required}",
        f"**Items:** {report.item_count}",
        "",
        "## Package Items",
        "",
    ]
    if not report.package_items:
        lines.append("- none")
    for item in report.package_items:
        lines.extend(
            [
                f"### {item.package_item_id}",
                "",
                f"- Target fixture: `{item.target_fixture_ref}`",
                f"- Proposed manual action: {item.proposed_manual_action}",
                f"- Accepted outputs: {', '.join(f'`{ref}`' for ref in item.accepted_output_refs)}",
                f"- Manual patch summary: {item.manual_patch_summary}",
                "- Required manual steps:",
                *(f"  - {step}" for step in item.required_manual_steps),
                "- Red-team notes:",
                *(f"  - {note}" for note in item.red_team_notes),
                "",
            ]
        )
    lines.extend(["## Checks", ""])
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
            f"- GitHub PR created: {report.github_pr_created}",
            f"- Fixture files mutated: {report.fixture_files_mutated}",
            f"- Fixture binding applied: {report.fixture_binding_applied}",
            f"- Downstream learning gate allowed: {report.downstream_learning_gate_allowed}",
            f"- Calibration applied: {report.calibration_applied}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This package is local review evidence only. It does not edit fixtures, create a GitHub PR, apply calibration, apply learning, write Lake/SQLite records, submit budgets, open matters, or authorize external action.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_fixture_update_pr_package(
    *,
    fixture_update_review_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetFixtureUpdatePRPackageReport, Path]:
    source_path = Path(fixture_update_review_report_path)
    review_report = BudgetFixtureUpdateReviewReport.model_validate(load_json(source_path))
    report = build_budget_fixture_update_pr_package_report(
        fixture_update_review_report=review_report,
        fixture_update_review_report_ref=str(source_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    items_path = run_dir / BUDGET_FIXTURE_UPDATE_PR_PACKAGE_ITEMS_FILENAME
    if items_path.exists():
        items_path.unlink()
    for item in report.package_items:
        append_jsonl(items_path, item.model_dump(mode="json"))
    if report.package_items:
        report = report.model_copy(update={"package_item_output_ref": str(items_path)})
    write_json(
        run_dir / BUDGET_FIXTURE_UPDATE_PR_PACKAGE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_FIXTURE_UPDATE_PR_PACKAGE_NOTES_FILENAME).write_text(
        render_budget_fixture_update_pr_package_report(report),
        encoding="utf-8",
    )
    return report, run_dir
