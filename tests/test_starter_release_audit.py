import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.starter_audit import (
    build_starter_release_audit_report,
    enforce_starter_release_audit,
)
from lawfirm_os_intake.util import load_json, write_json


def _run_north_star_demo(tmp_path, repo_root):
    code = main(
        [
            "demo",
            "--input",
            str(repo_root / "examples/synthetic/inbound/north-star-messy-intake.json"),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense.yaml"),
            "--confirmation-template",
            str(
                repo_root
                / "examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json"
            ),
            "--fixture-gold",
            str(repo_root / "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json"),
            "--out-dir",
            str(tmp_path / "demo"),
        ]
    )
    assert code == 0
    return tmp_path / "demo"


def test_starter_release_audit_passes_on_north_star_demo(tmp_path, repo_root):
    demo_dir = _run_north_star_demo(tmp_path, repo_root)

    report = build_starter_release_audit_report(repo_root=repo_root, demo_dir=demo_dir)

    assert report.status == "passed"
    assert report.non_authoritative is True
    assert report.external_writes_performed is False
    assert {check.status for check in report.checks} == {"passed"}
    assert {
        "required_demo_artifacts_present",
        "evidence_refs_validate_against_segments",
        "conflict_seed_has_no_conclusion_and_evidence",
        "budget_boundary_and_math_hold",
        "exception_lake_candidates_are_dry_run_and_expected",
        "terminal_safety_boundary_holds",
    }.issubset({check.check_id for check in report.checks})
    enforce_starter_release_audit(report)


def test_starter_release_audit_fails_when_budget_submission_boundary_drifts(tmp_path, repo_root):
    demo_dir = _run_north_star_demo(tmp_path, repo_root)
    budget_path = demo_dir / "budget/legal_budget_proposal.json"
    budget = load_json(budget_path)
    budget["not_authorized_for_client_submission"] = False
    write_json(budget_path, budget)

    report = build_starter_release_audit_report(repo_root=repo_root, demo_dir=demo_dir)

    assert report.status == "failed"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "budget_boundary_and_math_hold" in failed
    with pytest.raises(ValueError, match="budget_boundary_and_math_hold"):
        enforce_starter_release_audit(report)
