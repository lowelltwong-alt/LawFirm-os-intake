import pytest

from lawfirm_os_intake.context_counterfactual_audit import (
    build_context_counterfactual_audit_report,
    enforce_context_counterfactual_audit,
    run_context_counterfactual_audit,
)
from lawfirm_os_intake.workflow import run_preflight


def test_context_counterfactual_audit_passes_for_same_source_profiles(tmp_path, repo_root):
    report, audit_dir = run_context_counterfactual_audit(
        input_path=repo_root / "examples/synthetic/inbound/help-email.json",
        baseline_profile_path=repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        comparison_profile_path=(
            repo_root / "context/synthetic-profiles/plaintiff-personal-injury.yaml"
        ),
        out_dir=tmp_path / "context-counterfactual",
    )

    assert report.status == "passed"
    assert report.non_authoritative is True
    assert report.external_writes_performed is False
    assert {check.status for check in report.checks} == {"passed"}
    assert {
        "source_inventory_stable",
        "segment_signatures_stable",
        "observed_evidence_refs_stable",
        "practice_context_changes_ranking",
        "context_only_candidate_not_observed_fact",
    }.issubset({check.check_id for check in report.checks})
    assert (audit_dir / "context_counterfactual_audit_report.json").exists()
    enforce_context_counterfactual_audit(report)


def test_context_counterfactual_audit_fails_on_segment_drift(tmp_path, repo_root):
    input_path = repo_root / "examples/synthetic/inbound/help-email.json"
    baseline_packet, baseline_dir = run_preflight(
        input_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "baseline",
    )
    comparison_packet, comparison_dir = run_preflight(
        input_path,
        repo_root / "context/synthetic-profiles/plaintiff-personal-injury.yaml",
        tmp_path / "comparison",
    )
    drifted = comparison_packet.model_copy(deep=True)
    drifted.segments[0].sha256 = "sha256:" + ("0" * 64)

    report = build_context_counterfactual_audit_report(
        input_path=input_path,
        baseline_profile_path=repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        comparison_profile_path=(
            repo_root / "context/synthetic-profiles/plaintiff-personal-injury.yaml"
        ),
        baseline_packet=baseline_packet,
        comparison_packet=drifted,
        baseline_run_dir=baseline_dir,
        comparison_run_dir=comparison_dir,
    )

    assert report.status == "failed"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "segment_signatures_stable" in failed
    with pytest.raises(ValueError, match="segment_signatures_stable"):
        enforce_context_counterfactual_audit(report)
