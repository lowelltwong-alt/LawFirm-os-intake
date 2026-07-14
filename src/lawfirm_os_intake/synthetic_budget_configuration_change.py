"""Dry-run comparison for two synthetic budget-configuration source trees."""

from __future__ import annotations

from pathlib import Path

from .models import (
    SyntheticBudgetConfigurationChange,
    SyntheticBudgetConfigurationChangeCheck,
    SyntheticBudgetConfigurationChangePackage,
)
from .synthetic_budget_configuration_workbench import (
    build_synthetic_budget_configuration_workbench_report,
)
from .util import digest_json, now_iso, write_json

REPORT_FILENAME = "synthetic_budget_configuration_change_package.json"
MARKDOWN_FILENAME = "synthetic_budget_configuration_change_package.md"


def _check(check_id: str, passed: bool, message: str, *refs: str):
    return SyntheticBudgetConfigurationChangeCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=list(refs),
    )


def build_synthetic_budget_configuration_change_package(
    *, baseline_root: str | Path, candidate_root: str | Path, generated_at: str | None = None
) -> SyntheticBudgetConfigurationChangePackage:
    baseline = build_synthetic_budget_configuration_workbench_report(
        repo_root=baseline_root, generated_at=generated_at
    )
    candidate = build_synthetic_budget_configuration_workbench_report(
        repo_root=candidate_root, generated_at=generated_at
    )
    baseline_entries = {entry.entry_id: entry for entry in baseline.entries}
    candidate_entries = {entry.entry_id: entry for entry in candidate.entries}
    shared_ids = sorted(set(baseline_entries) & set(candidate_entries))
    changes = [
        SyntheticBudgetConfigurationChange(
            entry_id=entry_id,
            source_id=candidate_entries[entry_id].source_id,
            config_path=candidate_entries[entry_id].config_path,
            label=candidate_entries[entry_id].label,
            unit=candidate_entries[entry_id].unit,
            math_effect=candidate_entries[entry_id].math_effect,
            baseline_value=baseline_entries[entry_id].value,
            candidate_value=candidate_entries[entry_id].value,
            delta=round(candidate_entries[entry_id].value - baseline_entries[entry_id].value, 8),
        )
        for entry_id in shared_ids
        if baseline_entries[entry_id].value != candidate_entries[entry_id].value
    ]
    baseline_hashes = {source.source_id: source.source_sha256 for source in baseline.sources}
    candidate_hashes = {source.source_id: source.source_sha256 for source in candidate.sources}
    changed_sources = sorted(
        source_id
        for source_id in sorted(set(baseline_hashes) | set(candidate_hashes))
        if baseline_hashes.get(source_id) != candidate_hashes.get(source_id)
    )
    changed_entry_sources = sorted({change.source_id for change in changes})
    structure_unchanged = set(baseline_entries) == set(candidate_entries)
    source_change_matches_values = changed_sources == changed_entry_sources
    checks = [
        _check(
            "baseline_configuration_valid",
            baseline.status.endswith("ready_for_review"),
            "Baseline source tree must pass the synthetic configuration audit.",
        ),
        _check(
            "candidate_configuration_valid",
            candidate.status.endswith("ready_for_review"),
            "Candidate source tree must pass the synthetic configuration audit.",
        ),
        _check(
            "configuration_structure_unchanged",
            structure_unchanged,
            "This package compares numeric value changes only; added or removed configuration paths require a separate structural review.",
        ),
        _check(
            "at_least_one_numeric_change",
            bool(changes),
            "A dry-run change package requires at least one changed numeric configuration value.",
        ),
        _check(
            "source_hash_changes_match_numeric_changes",
            source_change_matches_values,
            "Every changed source hash must correspond exactly to one or more numeric configuration changes.",
        ),
        _check(
            "no_budget_recalculation_or_runtime_write",
            True,
            "This comparison only reports candidate source deltas; budget replay, import, and external writes remain unavailable.",
        ),
    ]
    failed = sum(check.status == "failed" for check in checks)
    basis = {
        "baseline": baseline_hashes,
        "candidate": candidate_hashes,
        "changes": [change.model_dump(mode="json") for change in changes],
    }
    return SyntheticBudgetConfigurationChangePackage(
        synthetic_budget_configuration_change_package_id="synconfigchange-"
        + digest_json(basis).removeprefix("sha256:")[:16],
        status=(
            "synthetic_budget_configuration_change_ready_for_review"
            if not failed
            else "blocked_by_synthetic_budget_configuration_change"
        ),
        baseline_report_id=baseline.synthetic_budget_configuration_workbench_report_id,
        candidate_report_id=candidate.synthetic_budget_configuration_workbench_report_id,
        baseline_source_hashes=baseline_hashes,
        candidate_source_hashes=candidate_hashes,
        changes=changes,
        changed_source_ids=changed_sources,
        change_count=len(changes),
        checks=checks,
        failed_check_count=failed,
        required_next_gates=[
            "human_review_of_synthetic_configuration_change",
            "regenerate_affected_budget_and_projection_artifacts",
            "review_generated_fixture_delta_before_promotion",
        ],
        generated_at=generated_at or now_iso(),
    )


def run_synthetic_budget_configuration_change_package(
    *,
    baseline_root: str | Path,
    candidate_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
):
    report = build_synthetic_budget_configuration_change_package(
        baseline_root=baseline_root, candidate_root=candidate_root, generated_at=generated_at
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / REPORT_FILENAME, report.model_dump(mode="json"))
    lines = [
        "# Synthetic Budget Configuration Change Package",
        "",
        f"- Status: `{report.status}`",
        f"- Changes: `{report.change_count}`",
        "",
        "## Changed Values",
        "",
    ]
    lines.extend(
        f"- `{change.config_path}`: `{change.baseline_value}` -> `{change.candidate_value}` ({change.delta:+g}; {change.math_effect})"
        for change in report.changes
    )
    (target / MARKDOWN_FILENAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report, target
