from __future__ import annotations

from pathlib import Path

from .models import (
    PublicSyntheticFixtureConversionPlan,
    PublicSyntheticFixtureConversionReviewOutcomeReport,
    PublicSyntheticFixtureConversionSpec,
    PublicSyntheticFixturePRPackageCheck,
    PublicSyntheticFixturePRPackageItem,
    PublicSyntheticFixturePRPackageReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_REPORT_FILENAME = (
    "public_synthetic_fixture_pr_package_report.json"
)
PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_NOTES_FILENAME = "public_synthetic_fixture_pr_package_report.md"
PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_ITEMS_FILENAME = (
    "public_synthetic_fixture_pr_package_items.jsonl"
)

APPROVED_CONVERSION_REVIEW_STATUS = "conversion_review_recorded_separate_fixture_pr_required"

PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_REQUIRED_NEXT_GATES = [
    "manual_fixture_generation_pr_review",
    "create_fixture_only_in_separate_pr",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
    "legal_knowledge_runtime_owner_review_before_adapter",
    "no_public_payload_or_identity_contamination",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    source_ids: list[str] | None = None,
    conversion_spec_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> PublicSyntheticFixturePRPackageCheck:
    return PublicSyntheticFixturePRPackageCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        source_ids=source_ids or [],
        conversion_spec_ids=conversion_spec_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _review_outcome_boundary_clear(
    report: PublicSyntheticFixtureConversionReviewOutcomeReport,
) -> bool:
    return (
        report.fixture_generation_authorized is False
        and report.fixture_pr_created is False
        and report.fixture_files_mutated is False
        and report.public_records_ingested is False
        and report.raw_public_payload_committed is False
        and report.connector_implemented is False
        and report.legal_knowledge_adapter_authorized is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
        and report.silent_learning_performed is False
    )


def _find_spec(
    plan: PublicSyntheticFixtureConversionPlan,
    report: PublicSyntheticFixtureConversionReviewOutcomeReport,
) -> PublicSyntheticFixtureConversionSpec | None:
    return next(
        (
            spec
            for spec in plan.specs
            if spec.conversion_spec_id == report.conversion_spec_id
            and spec.source_id == report.source_id
        ),
        None,
    )


def _approved(report: PublicSyntheticFixtureConversionReviewOutcomeReport) -> bool:
    return (
        report.status == APPROVED_CONVERSION_REVIEW_STATUS
        and report.accepted_for_separate_fixture_pr
        and report.separate_fixture_generation_pr_required
    )


def _build_item(
    *,
    review_outcome_report: PublicSyntheticFixtureConversionReviewOutcomeReport,
    spec: PublicSyntheticFixtureConversionSpec,
) -> PublicSyntheticFixturePRPackageItem:
    return PublicSyntheticFixturePRPackageItem(
        package_item_id=_stable_id(
            "publicfixturepritem",
            f"{review_outcome_report.review_outcome_report_id}|{spec.conversion_spec_id}",
        ),
        review_outcome_report_id=review_outcome_report.review_outcome_report_id,
        conversion_review_id=review_outcome_report.conversion_review_id,
        source_id=spec.source_id,
        conversion_spec_id=spec.conversion_spec_id,
        target_fixture_family=spec.target_fixture_family,
        proposed_manual_action="create_non_identifying_synthetic_fixture_in_separate_pr",
        source_methodology_ref=spec.source_methodology_ref,
        proposed_fixture_scope=(
            f"Create non-identifying synthetic `{spec.target_fixture_family}` fixture material "
            f"from source `{spec.source_id}` structure only."
        ),
        allowed_structure_inputs=spec.allowed_structure_inputs,
        forbidden_inputs=spec.forbidden_inputs,
        identity_replacement_rules=spec.identity_replacement_rules,
        field_transformation_rules=spec.field_transformation_rules,
        required_synthetic_gold_checks=spec.required_synthetic_gold_checks,
        required_red_team_checks=spec.required_red_team_checks,
        required_manual_steps=[
            "Open a separate fixture-generation branch or PR for the synthetic fixture work.",
            "Use the conversion spec as structure guidance only; do not download or commit public payloads.",
            "Create synthetic source IDs, party names, matter identifiers, dates, locations, and payload text.",
            "Run the required synthetic gold checks before requesting fixture PR review.",
            "Run the required red-team identity reconstruction checks before requesting fixture PR review.",
            "Keep Legal Knowledge Runtime adapter work blocked until owner review.",
        ],
        red_team_notes=[
            "This package is an instruction set, not a fixture patch.",
            "Approval can be overread as permission to use real public records; it is not.",
            "Rare field combinations can reconstruct real public matters if the synthetic fixture is too specific.",
            "Do not treat public-source structure as observed intake, merits, conflict, or budget evidence.",
        ],
        required_next_gates=PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_REQUIRED_NEXT_GATES,
    )


def build_public_synthetic_fixture_pr_package_report(
    *,
    review_outcome_report: PublicSyntheticFixtureConversionReviewOutcomeReport,
    review_outcome_report_ref: str,
    conversion_plan: PublicSyntheticFixtureConversionPlan,
    conversion_plan_ref: str,
) -> PublicSyntheticFixturePRPackageReport:
    failed_review_checks = [
        check.check_id for check in review_outcome_report.checks if check.status == "failed"
    ]
    spec = _find_spec(conversion_plan, review_outcome_report)
    approved = _approved(review_outcome_report)
    spec_target_matches = spec is not None and review_outcome_report.target_fixture_family in {
        None,
        spec.target_fixture_family,
    }
    items = [
        _build_item(review_outcome_report=review_outcome_report, spec=spec)
        for _ in [0]
        if approved and spec is not None and spec_target_matches
    ]
    checks = [
        _check(
            "conversion_review_outcome_recorded_without_writes",
            review_outcome_report.status
            in {
                "conversion_review_recorded_separate_fixture_pr_required",
                "conversion_review_recorded_revision_or_rejection",
                "conversion_review_recorded_more_information_required",
                "conversion_review_recorded_human_only_hold",
            }
            and not failed_review_checks
            and _review_outcome_boundary_clear(review_outcome_report),
            "Public conversion review outcome is recorded and preserves no-write/no-learning boundaries.",
            artifact_refs=[review_outcome_report_ref],
            source_ids=[review_outcome_report.source_id],
            conversion_spec_ids=[review_outcome_report.conversion_spec_id],
            blocking_refs=failed_review_checks,
        ),
        _check(
            "conversion_plan_matches_review_outcome",
            conversion_plan.conversion_plan_id == review_outcome_report.conversion_plan_id
            and conversion_plan.status == "ready_for_human_conversion_review"
            and spec is not None
            and spec_target_matches,
            "Conversion plan is ready and contains the reviewed source/spec target family.",
            artifact_refs=[conversion_plan_ref],
            source_ids=[review_outcome_report.source_id],
            conversion_spec_ids=[review_outcome_report.conversion_spec_id],
        ),
        _check(
            "approved_outcome_packaged",
            (not approved) or len(items) == 1,
            "Approved conversion outcome is represented in one manual fixture PR package item.",
            artifact_refs=[review_outcome_report_ref],
            source_ids=[review_outcome_report.source_id],
            conversion_spec_ids=[review_outcome_report.conversion_spec_id],
        ),
        _check(
            "package_does_not_apply_patch",
            True,
            "Package generation creates review instructions only and does not edit fixtures or create a PR.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "blocked_by_public_fixture_review_outcome"
    elif approved:
        status = "public_fixture_pr_package_ready_for_manual_pr"
    else:
        status = "no_public_fixture_pr_package_needed"
    target_fixture_family = (
        spec.target_fixture_family if spec else review_outcome_report.target_fixture_family
    )
    return PublicSyntheticFixturePRPackageReport(
        fixture_pr_package_report_id=_stable_id(
            "publicfixtureprpackage",
            "|".join(
                [
                    review_outcome_report.review_outcome_report_id,
                    review_outcome_report.conversion_review_id,
                    review_outcome_report.outcome,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_review_outcome_report_id=review_outcome_report.review_outcome_report_id,
        source_review_outcome_report_ref=review_outcome_report_ref,
        source_review_outcome_status=review_outcome_report.status,
        source_conversion_plan_id=conversion_plan.conversion_plan_id,
        source_conversion_plan_ref=conversion_plan_ref,
        source_conversion_plan_status=conversion_plan.status,
        conversion_review_id=review_outcome_report.conversion_review_id,
        outcome=review_outcome_report.outcome,
        source_id=review_outcome_report.source_id,
        conversion_spec_id=review_outcome_report.conversion_spec_id,
        target_fixture_family=target_fixture_family,
        item_count=len(items),
        ready_item_count=len(items)
        if status == "public_fixture_pr_package_ready_for_manual_pr"
        else 0,
        blocked_item_count=len(items)
        if status == "blocked_by_public_fixture_review_outcome"
        else 0,
        package_items=items,
        checks=checks,
        required_next_gates=PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_REQUIRED_NEXT_GATES,
        manual_fixture_generation_pr_required=(
            status == "public_fixture_pr_package_ready_for_manual_pr"
        ),
        generated_at=now_iso(),
    )


def render_public_synthetic_fixture_pr_package_report(
    report: PublicSyntheticFixturePRPackageReport,
) -> str:
    lines = [
        "# Public Synthetic Fixture PR Package",
        "",
        f"**Report ID:** {report.fixture_pr_package_report_id}",
        f"**Status:** {report.status}",
        f"**Source outcome report:** `{report.source_review_outcome_report_ref}`",
        f"**Conversion plan:** `{report.source_conversion_plan_ref}`",
        f"**Outcome:** {report.outcome}",
        f"**Manual fixture-generation PR required:** {report.manual_fixture_generation_pr_required}",
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
                f"- Source: `{item.source_id}`",
                f"- Conversion spec: `{item.conversion_spec_id}`",
                f"- Target fixture family: `{item.target_fixture_family}`",
                f"- Proposed manual action: {item.proposed_manual_action}",
                f"- Fixture scope: {item.proposed_fixture_scope}",
                f"- Source methodology ref: `{item.source_methodology_ref}`",
                "- Allowed structure inputs:",
                *(f"  - {value}" for value in item.allowed_structure_inputs),
                "- Forbidden inputs:",
                *(f"  - {value}" for value in item.forbidden_inputs),
                "- Identity replacement rules:",
                *(f"  - {value}" for value in item.identity_replacement_rules),
                "- Required synthetic gold checks:",
                *(f"  - {value}" for value in item.required_synthetic_gold_checks),
                "- Required red-team checks:",
                *(f"  - {value}" for value in item.required_red_team_checks),
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
            f"- Fixture generation authorized: {report.fixture_generation_authorized}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- Fixture files mutated: {report.fixture_files_mutated}",
            f"- Public records ingested: {report.public_records_ingested}",
            f"- Raw public payload committed: {report.raw_public_payload_committed}",
            f"- Connector implemented: {report.connector_implemented}",
            f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This package is local review evidence only. It does not edit fixtures, create a GitHub PR, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_synthetic_fixture_pr_package(
    *,
    review_outcome_report_path: str | Path,
    conversion_plan_path: str | Path,
    out_dir: str | Path,
) -> tuple[PublicSyntheticFixturePRPackageReport, Path]:
    outcome_path = Path(review_outcome_report_path)
    plan_path = Path(conversion_plan_path)
    review_outcome_report = PublicSyntheticFixtureConversionReviewOutcomeReport.model_validate(
        load_json(outcome_path)
    )
    conversion_plan = PublicSyntheticFixtureConversionPlan.model_validate(load_json(plan_path))
    report = build_public_synthetic_fixture_pr_package_report(
        review_outcome_report=review_outcome_report,
        review_outcome_report_ref=str(outcome_path),
        conversion_plan=conversion_plan,
        conversion_plan_ref=str(plan_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    items_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_ITEMS_FILENAME
    if items_path.exists():
        items_path.unlink()
    for item in report.package_items:
        append_jsonl(items_path, item.model_dump(mode="json"))
    if report.package_items:
        report = report.model_copy(update={"package_item_output_ref": str(items_path)})
    write_json(
        run_dir / PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / PUBLIC_SYNTHETIC_FIXTURE_PR_PACKAGE_NOTES_FILENAME).write_text(
        render_public_synthetic_fixture_pr_package_report(report),
        encoding="utf-8",
    )
    return report, run_dir
