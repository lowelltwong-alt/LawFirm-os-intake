from __future__ import annotations

from copy import deepcopy

import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.intensity_signoff import (
    build_intensity_normalization_signoff_report,
    validate_intensity_normalization_signoff_gate,
)
from lawfirm_os_intake.util import load_json, write_json


POLICY = "config/budget-driver-policy.yaml"
PROFILE = "context/synthetic-profiles/insurance-defense.yaml"
APPROVED_SIGNOFF = "docs/governance/intensity_normalization_signoff.json"


def _write_raw_policy(repo_root, tmp_path):
    policy = yaml.safe_load((repo_root / POLICY).read_text(encoding="utf-8"))
    policy = deepcopy(policy)
    policy["intensity_multiplier_policy"]["normalization"] = "raw"
    policy_path = tmp_path / "budget-driver-policy.raw.yaml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return policy_path


def _write_baseline_relative_policy(repo_root, tmp_path):
    policy = yaml.safe_load((repo_root / POLICY).read_text(encoding="utf-8"))
    policy = deepcopy(policy)
    policy["intensity_multiplier_policy"]["normalization"] = "baseline_relative"
    policy_path = tmp_path / "budget-driver-policy.baseline-relative.yaml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return policy_path


def test_intensity_signoff_preview_contains_default_products_and_demo_deltas(repo_root):
    report = build_intensity_normalization_signoff_report(
        policy_path=repo_root / POLICY,
        practice_profile_paths=[repo_root / PROFILE],
        generated_at="2026-07-06T00:00:00Z",
    )

    assert report.status == "preview_requires_human_approval"
    assert report.normalization_mode_before == "raw"
    assert report.normalization_mode_after == "baseline_relative"
    assert report.requires_human_approval is True
    assert report.approved_by is None
    assert report.external_writes_performed is False
    assert report.lake_write_performed is False

    families = {family.matter_family: family for family in report.per_family}
    medmal = families["medical_malpractice_defense"]
    assert medmal.baseline_source == "family_defaults"
    assert medmal.per_phase_default_product_before["L300"] == 1.134
    assert medmal.per_phase_default_product_after["L300"] == 1.0
    assert medmal.per_phase_default_product_before["L400"] == 1.08
    assert medmal.per_phase_default_product_after["L400"] == 1.0

    medmal_demo = {
        total.demo_case_id: total
        for total in medmal.demo_totals
        if total.demo_case_id == "carrier-assignment-medmal"
    }["carrier-assignment-medmal"]
    assert medmal_demo.total_proposed_budget_before is not None
    assert medmal_demo.total_proposed_budget_after is not None
    assert medmal_demo.total_proposed_budget_after < medmal_demo.total_proposed_budget_before
    assert medmal_demo.delta_amount is not None
    assert medmal_demo.delta_amount < 0


def test_intensity_signoff_gate_passes_explicit_raw_policy_without_signoff(repo_root, tmp_path):
    policy_path = _write_raw_policy(repo_root, tmp_path)

    report = validate_intensity_normalization_signoff_gate(policy_path=policy_path)

    assert report.status == "passed"
    assert report.normalization_mode == "raw"
    assert report.signoff_required is False
    assert {check.check_id for check in report.checks} == {"raw_mode_needs_no_signoff"}


def test_active_baseline_relative_policy_passes_with_committed_approved_signoff(repo_root):
    report = validate_intensity_normalization_signoff_gate(
        policy_path=repo_root / POLICY,
        signoff_path=repo_root / APPROVED_SIGNOFF,
    )
    markdown = (repo_root / "docs/governance/intensity_normalization_signoff.md").read_text(
        encoding="utf-8"
    )

    assert report.status == "passed"
    assert report.normalization_mode == "baseline_relative"
    assert report.signoff_required is True
    assert report.signoff_status == "approved_for_baseline_relative"
    assert markdown.startswith("# Intensity Normalization Approved Signoff")
    assert "## Decision\n" in markdown


def test_intensity_signoff_gate_fails_baseline_relative_without_signoff(repo_root, tmp_path):
    policy_path = _write_baseline_relative_policy(repo_root, tmp_path)

    report = validate_intensity_normalization_signoff_gate(policy_path=policy_path)

    assert report.status == "failed"
    assert report.signoff_required is True
    assert any(check.check_id == "baseline_relative_requires_signoff" for check in report.checks)


def test_intensity_signoff_gate_fails_unapproved_preview(repo_root, tmp_path):
    policy_path = _write_baseline_relative_policy(repo_root, tmp_path)
    signoff_path = tmp_path / "intensity_normalization_signoff.json"
    preview = build_intensity_normalization_signoff_report(
        policy_path=repo_root / POLICY,
        practice_profile_paths=[repo_root / PROFILE],
        generated_at="2026-07-06T00:00:00Z",
    )
    write_json(signoff_path, preview.model_dump(mode="json"))

    report = validate_intensity_normalization_signoff_gate(
        policy_path=policy_path,
        signoff_path=signoff_path,
    )

    assert report.status == "failed"
    assert any(check.check_id == "signoff_approved_status" for check in report.checks)


def test_intensity_signoff_gate_passes_approved_artifact(repo_root, tmp_path):
    policy_path = _write_baseline_relative_policy(repo_root, tmp_path)
    signoff_path = tmp_path / "intensity_normalization_signoff.json"
    preview = build_intensity_normalization_signoff_report(
        policy_path=repo_root / POLICY,
        practice_profile_paths=[repo_root / PROFILE],
        generated_at="2026-07-06T00:00:00Z",
    )
    approved = preview.model_copy(
        update={
            "status": "approved_for_baseline_relative",
            "approved_by": "synthetic-budget-owner",
            "approved_at": "2026-07-06T00:30:00Z",
        }
    )
    write_json(signoff_path, approved.model_dump(mode="json"))

    report = validate_intensity_normalization_signoff_gate(
        policy_path=policy_path,
        signoff_path=signoff_path,
    )

    assert report.status == "passed"
    assert report.signoff_status == "approved_for_baseline_relative"
    assert {check.status for check in report.checks} == {"passed"}


def test_intensity_signoff_cli_writes_preview_and_gate_report(repo_root, tmp_path):
    signoff_path = tmp_path / "intensity_normalization_signoff.json"
    markdown_path = tmp_path / "intensity_normalization_signoff.md"
    gate_report_path = tmp_path / "intensity_normalization_signoff_gate.json"

    result = main(
        [
            "intensity-signoff",
            "--policy",
            str(repo_root / POLICY),
            "--practice-profile",
            str(repo_root / PROFILE),
            "--out",
            str(signoff_path),
            "--markdown-out",
            str(markdown_path),
            "--generated-at",
            "2026-07-06T00:00:00Z",
        ]
    )
    assert result == 0
    payload = load_json(signoff_path)
    assert payload["status"] == "preview_requires_human_approval"
    assert "Candidate-only" in markdown_path.read_text(encoding="utf-8")

    result = main(
        [
            "validate-intensity-signoff",
            "--policy",
            str(repo_root / POLICY),
            "--signoff",
            str(repo_root / APPROVED_SIGNOFF),
            "--report-out",
            str(gate_report_path),
        ]
    )
    assert result == 0
    assert load_json(gate_report_path)["status"] == "passed"
