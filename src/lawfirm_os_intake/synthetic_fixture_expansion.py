from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    RemainingRoadmapReport,
    SyntheticFixtureExpansionCheck,
    SyntheticFixtureExpansionFamily,
    SyntheticFixtureExpansionManifest,
    SyntheticFixtureExpansionReport,
)
from .util import digest_text, load_json, now_iso, write_json


SYNTHETIC_FIXTURE_EXPANSION_REPORT_FILENAME = "synthetic_fixture_expansion_report.json"
SYNTHETIC_FIXTURE_EXPANSION_NOTES_FILENAME = "synthetic_fixture_expansion_report.md"

REQUIRED_FAMILIES: tuple[SyntheticFixtureExpansionFamily, ...] = (
    "ambiguous_roles",
    "missing_actuals",
    "carrier_rejection_variants",
    "budget_driver_edges",
)


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _ref_path_part(ref: str) -> str:
    return ref.split("::", maxsplit=1)[0].split("#", maxsplit=1)[0]


def _resolve_repo_ref(repo_root: Path, ref: str) -> Path | None:
    path_part = _ref_path_part(ref)
    target = Path(path_part)
    resolved = target.resolve() if target.is_absolute() else (repo_root / target).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    return resolved


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> SyntheticFixtureExpansionCheck:
    return SyntheticFixtureExpansionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _json_scope_failures(payload: Any, ref: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    failures: list[str] = []
    if payload.get("data_origin") not in {None, "synthetic"}:
        failures.append(f"{ref}: data_origin is not synthetic")
    for flag in (
        "contains_real_client_data",
        "contains_real_matter_data",
        "contains_privileged_data",
        "billing_connector_read_performed",
        "billing_connector_write_performed",
        "external_writes_performed",
        "silent_learning_performed",
    ):
        if payload.get(flag) is True:
            failures.append(f"{ref}: {flag}=true")
    if payload.get("calibration_approved") is True:
        failures.append(f"{ref}: calibration_approved=true")
    return failures


def _load_fixture_scope_failures(repo_root: Path, fixture_refs: list[str]) -> list[str]:
    failures: list[str] = []
    for ref in fixture_refs:
        resolved = _resolve_repo_ref(repo_root, ref)
        if resolved is None:
            failures.append(f"{ref}: resolves outside repo root")
            continue
        if not resolved.exists():
            failures.append(f"{ref}: missing")
            continue
        if resolved.suffix.lower() == ".json":
            try:
                failures.extend(_json_scope_failures(load_json(resolved), ref))
            except ValueError as exc:
                failures.append(f"{ref}: invalid JSON ({exc})")
    return failures


def _build_checks(
    *,
    roadmap: RemainingRoadmapReport,
    roadmap_ref: str,
    manifest: SyntheticFixtureExpansionManifest,
    manifest_ref: str,
    repo_root: Path,
) -> list[SyntheticFixtureExpansionCheck]:
    item = next(
        (item for item in roadmap.items if item.item_id == "fixture-and-eval-expansion"),
        None,
    )
    required = set(REQUIRED_FAMILIES)
    manifest_required = set(manifest.required_families)
    covered = {holdout.family for holdout in manifest.holdouts}
    all_fixture_refs = [ref for holdout in manifest.holdouts for ref in holdout.fixture_refs]
    all_test_refs = [ref for holdout in manifest.holdouts for ref in holdout.test_refs]
    resolved_fixture_refs = [_resolve_repo_ref(repo_root, ref) for ref in all_fixture_refs]
    resolved_test_refs = [_resolve_repo_ref(repo_root, ref) for ref in all_test_refs]
    missing_or_external_fixture_refs = [
        ref
        for ref, resolved in zip(all_fixture_refs, resolved_fixture_refs, strict=True)
        if resolved is None or not resolved.exists()
    ]
    missing_or_external_test_refs = [
        ref
        for ref, resolved in zip(all_test_refs, resolved_test_refs, strict=True)
        if resolved is None or not resolved.exists()
    ]
    scope_failures = _load_fixture_scope_failures(repo_root, all_fixture_refs)
    return [
        _check(
            "remaining_roadmap_allows_fixture_expansion",
            roadmap.status == "remaining_roadmap_ready_manual_execution_required"
            and item is not None
            and item.owner == "LawFirm-os-intake"
            and item.gate == "local_candidate"
            and item.status == "ready_to_start",
            "Remaining roadmap has a ready local fixture/eval expansion item.",
            artifact_refs=[roadmap_ref],
        ),
        _check(
            "manifest_bound_to_fixture_expansion_item",
            manifest.source_remaining_roadmap_item_id == "fixture-and-eval-expansion",
            "Manifest is bound to the fixture-and-eval expansion roadmap item.",
            artifact_refs=[manifest_ref],
        ),
        _check(
            "required_holdout_families_declared",
            required.issubset(manifest_required) and required.issubset(covered),
            "Manifest declares and covers ambiguous roles, missing actuals, carrier rejection variants, and budget driver edge cases.",
            artifact_refs=[manifest_ref],
        ),
        _check(
            "fixture_refs_exist_and_stay_in_repo",
            not missing_or_external_fixture_refs,
            "All fixture refs exist and resolve under the repo root.",
            artifact_refs=all_fixture_refs,
            blocking_refs=missing_or_external_fixture_refs,
        ),
        _check(
            "test_refs_exist_and_stay_in_repo",
            not missing_or_external_test_refs,
            "All test refs exist and resolve under the repo root.",
            artifact_refs=all_test_refs,
            blocking_refs=missing_or_external_test_refs,
        ),
        _check(
            "fixture_refs_are_synthetic_only_and_not_calibration_approved",
            not scope_failures,
            "JSON fixture refs are synthetic-only where scoped and are not calibration-approved.",
            artifact_refs=all_fixture_refs,
            blocking_refs=scope_failures,
        ),
        _check(
            "audit_preserves_no_write_boundary",
            manifest.fixture_files_mutated_by_audit is False
            and manifest.lake_write_performed is False
            and manifest.sqlite_write_performed is False
            and manifest.external_writes_performed is False
            and manifest.silent_learning_performed is False,
            "Fixture expansion audit mutates no fixtures, writes no Lake/SQLite records, performs no external writes, and applies no learning.",
            artifact_refs=[manifest_ref],
        ),
    ]


def build_synthetic_fixture_expansion_report(
    *,
    roadmap: RemainingRoadmapReport,
    roadmap_ref: str,
    manifest: SyntheticFixtureExpansionManifest,
    manifest_ref: str,
    repo_root: Path,
) -> SyntheticFixtureExpansionReport:
    checks = _build_checks(
        roadmap=roadmap,
        roadmap_ref=roadmap_ref,
        manifest=manifest,
        manifest_ref=manifest_ref,
        repo_root=repo_root,
    )
    item = next(
        (item for item in roadmap.items if item.item_id == "fixture-and-eval-expansion"),
        None,
    )
    family_counts: dict[str, int] = {}
    for holdout in manifest.holdouts:
        family_counts[holdout.family] = family_counts.get(holdout.family, 0) + 1
    missing_required = [
        family for family in manifest.required_families if family not in set(family_counts)
    ]
    failed = [check for check in checks if check.status == "failed"]
    return SyntheticFixtureExpansionReport(
        fixture_expansion_report_id=_stable_id(
            "syntheticfixtureexpansion",
            "|".join([roadmap.remaining_roadmap_report_id, manifest.manifest_id]),
        ),
        status=(
            "blocked_by_fixture_expansion_evidence"
            if failed
            else "synthetic_fixture_expansion_ready_for_review"
        ),
        source_remaining_roadmap_report_id=roadmap.remaining_roadmap_report_id,
        source_remaining_roadmap_report_ref=roadmap_ref,
        source_remaining_roadmap_status=roadmap.status,
        source_remaining_roadmap_item_id="fixture-and-eval-expansion",
        source_remaining_roadmap_item_status=item.status if item else "missing",
        manifest_id=manifest.manifest_id,
        manifest_ref=manifest_ref,
        required_family_count=len(manifest.required_families),
        holdout_count=len(manifest.holdouts),
        family_counts=family_counts,
        missing_required_families=missing_required,
        holdouts=manifest.holdouts,
        checks=checks,
        generated_at=now_iso(),
    )


def render_synthetic_fixture_expansion_report(
    report: SyntheticFixtureExpansionReport,
) -> str:
    lines = [
        "# Synthetic Fixture Expansion Report",
        "",
        f"**Report ID:** {report.fixture_expansion_report_id}",
        f"**Status:** {report.status}",
        f"**Roadmap:** `{report.source_remaining_roadmap_report_ref}` ({report.source_remaining_roadmap_status})",
        f"**Manifest:** `{report.manifest_ref}`",
        "",
        "## Summary",
        "",
        f"- Required families: {report.required_family_count}",
        f"- Holdouts: {report.holdout_count}",
        f"- Missing required families: {', '.join(report.missing_required_families) if report.missing_required_families else 'none'}",
        "- Family counts:",
        *(f"  - {family}: {count}" for family, count in sorted(report.family_counts.items())),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(["", "## Holdouts", ""])
    for holdout in report.holdouts:
        lines.extend(
            [
                f"### {holdout.holdout_id}",
                "",
                f"- Family: {holdout.family}",
                f"- Description: {holdout.description}",
                f"- Fixture refs: {', '.join(f'`{ref}`' for ref in holdout.fixture_refs)}",
                f"- Test refs: {', '.join(f'`{ref}`' for ref in holdout.test_refs)}",
                "- Expected signals:",
                *(f"  - {signal}" for signal in holdout.expected_signals),
                "- Red-team notes:",
                *(f"  - {note}" for note in holdout.red_team_notes),
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            f"- Calibration approved: {report.calibration_approved}",
            f"- Fixture files mutated by audit: {report.fixture_files_mutated_by_audit}",
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
            "This report proves synthetic holdout coverage for review. It does not approve calibration, mutate fixtures during audit, create PRs or issues, write sibling repos, admit Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_synthetic_fixture_expansion_audit(
    *,
    remaining_roadmap_report_path: str | Path,
    manifest_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
) -> tuple[SyntheticFixtureExpansionReport, Path]:
    roadmap_path = Path(remaining_roadmap_report_path)
    manifest_ref = str(manifest_path)
    manifest = SyntheticFixtureExpansionManifest.model_validate(load_json(manifest_path))
    report = build_synthetic_fixture_expansion_report(
        roadmap=RemainingRoadmapReport.model_validate(load_json(roadmap_path)),
        roadmap_ref=str(roadmap_path),
        manifest=manifest,
        manifest_ref=manifest_ref,
        repo_root=Path(repo_root).resolve(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / SYNTHETIC_FIXTURE_EXPANSION_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / SYNTHETIC_FIXTURE_EXPANSION_NOTES_FILENAME).write_text(
        render_synthetic_fixture_expansion_report(report),
        encoding="utf-8",
    )
    return report, run_dir
