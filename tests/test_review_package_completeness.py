import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    ExceptionLakeReadinessReport,
    HumanConfirmation,
    ReviewPackageManifest,
    SafetyGateReport,
)
from lawfirm_os_intake.package_completeness import (
    build_review_package_completeness_report,
    enforce_review_package_completeness,
)
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run_budget(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    _, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget_dir


def _load_inputs(budget_dir):
    return (
        ReviewPackageManifest.model_validate(
            load_json(budget_dir / "review_package_manifest.json")
        ),
        SafetyGateReport.model_validate(load_json(budget_dir / "safety_gate_report.json")),
        ExceptionLakeReadinessReport.model_validate(
            load_json(budget_dir / "exception_lake_readiness_report.json")
        ),
        budget_dir / "matter_opening_review_package.md",
    )


def test_review_package_completeness_fails_on_missing_artifact_key(tmp_path, repo_root):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    mutated = manifest.model_copy(deep=True)
    del mutated.artifact_refs["legal_budget_proposal"]

    report = build_review_package_completeness_report(
        manifest=mutated,
        review_package_path=review_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "required_artifact_keys_present" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="required_artifact_keys_present"):
        enforce_review_package_completeness(report)


def test_review_package_completeness_fails_on_missing_review_section(tmp_path, repo_root):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    review_path.write_text(
        review_path.read_text(encoding="utf-8").replace("## Safety Gate", "## Safety"),
        encoding="utf-8",
    )

    report = build_review_package_completeness_report(
        manifest=manifest,
        review_package_path=review_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "required_review_sections_present" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="required_review_sections_present"):
        enforce_review_package_completeness(report)
