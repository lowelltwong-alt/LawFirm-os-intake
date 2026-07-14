"""Bind a synthetic configuration delta to freshly rebuilt projection evidence."""

from __future__ import annotations

from pathlib import Path

from .models import (
    SyntheticConfigurationRegenerationBindingReport,
    SyntheticConfigurationRegenerationCheck,
)
from .synthetic_budget_configuration_change import (
    build_synthetic_budget_configuration_change_package,
)
from .synthetic_guideline_projection_workbench import (
    build_synthetic_guideline_projection_workbench_report,
)
from .util import digest_json, now_iso, write_json

REPORT_FILENAME = "synthetic_configuration_regeneration_binding_report.json"


def _check(check_id: str, passed: bool, message: str, *refs: str):
    return SyntheticConfigurationRegenerationCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=list(refs),
    )


def build_synthetic_configuration_regeneration_binding_report(
    *, baseline_root: str | Path, candidate_root: str | Path, generated_at: str | None = None
) -> SyntheticConfigurationRegenerationBindingReport:
    change = build_synthetic_budget_configuration_change_package(
        baseline_root=baseline_root, candidate_root=candidate_root, generated_at=generated_at
    )
    baseline = build_synthetic_guideline_projection_workbench_report(
        repo_root=baseline_root, generated_at=generated_at
    )
    candidate = build_synthetic_guideline_projection_workbench_report(
        repo_root=candidate_root, generated_at=generated_at
    )
    candidate_hashes = {item.source_id: item.source_sha256 for item in candidate.source_manifest}
    baseline_hashes = {item.source_id: item.source_sha256 for item in baseline.source_manifest}
    relevant_candidate_hashes = {
        source_id: change.candidate_source_hashes[source_id]
        for source_id in change.changed_source_ids
        if source_id in change.candidate_source_hashes
    }
    checks = [
        _check(
            "change_package_ready",
            change.status == "synthetic_budget_configuration_change_ready_for_review",
            "Configuration delta must be a review-ready numeric change package.",
        ),
        _check(
            "changed_sources_consumed_by_projection",
            set(change.changed_source_ids).issubset(set(candidate_hashes)),
            "Every changed source must be consumed by the regenerated projection; unconsumed sources need a different derived-artifact binding.",
        ),
        _check(
            "candidate_projection_hashes_match_candidate_sources",
            all(
                candidate_hashes.get(source_id) == source_hash
                for source_id, source_hash in relevant_candidate_hashes.items()
            ),
            "Projection source manifest must carry each candidate changed-source hash exactly.",
        ),
        _check(
            "baseline_projection_hashes_match_baseline_sources",
            all(
                baseline_hashes.get(source_id) == source_hash
                for source_id, source_hash in change.baseline_source_hashes.items()
                if source_id in baseline_hashes
            ),
            "Baseline projection manifest must remain pinned to baseline source hashes.",
        ),
        _check(
            "projection_rebuilt_for_changed_sources",
            any(
                baseline_hashes.get(source_id) != candidate_hashes.get(source_id)
                for source_id in change.changed_source_ids
                if source_id in candidate_hashes
            ),
            "At least one consumed changed source must differ between regenerated baseline and candidate projection manifests.",
        ),
        _check(
            "no_budget_recalculation_or_runtime_write",
            True,
            "This binding validates projection artifact provenance only; it does not authorize a budget, import, or runtime write.",
        ),
    ]
    failed = sum(check.status == "failed" for check in checks)
    basis = {
        "change": change.synthetic_budget_configuration_change_package_id,
        "baseline": baseline.synthetic_guideline_projection_workbench_report_id,
        "candidate": candidate.synthetic_guideline_projection_workbench_report_id,
    }
    return SyntheticConfigurationRegenerationBindingReport(
        regeneration_binding_report_id="synconfigregen-"
        + digest_json(basis).removeprefix("sha256:")[:16],
        status="ready_for_review" if not failed else "blocked",
        change_package_id=change.synthetic_budget_configuration_change_package_id,
        baseline_projection_report_id=baseline.synthetic_guideline_projection_workbench_report_id,
        candidate_projection_report_id=candidate.synthetic_guideline_projection_workbench_report_id,
        baseline_budget_proposal_sha256=baseline.budget_proposal_sha256,
        candidate_budget_proposal_sha256=candidate.budget_proposal_sha256,
        changed_source_ids=change.changed_source_ids,
        candidate_projection_source_hashes=candidate_hashes,
        checks=checks,
        failed_check_count=failed,
        required_next_gates=[
            "human_review_of_regeneration_binding",
            "regenerate_budget_artifact_when_profile_inputs_change",
            "review_derived_artifact_delta_before_fixture_update",
        ],
        generated_at=generated_at or now_iso(),
    )


def run_synthetic_configuration_regeneration_binding_report(
    *,
    baseline_root: str | Path,
    candidate_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
):
    report = build_synthetic_configuration_regeneration_binding_report(
        baseline_root=baseline_root, candidate_root=candidate_root, generated_at=generated_at
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / REPORT_FILENAME, report.model_dump(mode="json"))
    return report, target
