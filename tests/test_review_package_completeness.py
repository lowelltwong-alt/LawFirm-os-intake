import json
from pathlib import Path

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


@pytest.mark.parametrize(
    ("artifact_key", "old_heading", "new_heading"),
    [
        ("preflight_intake_review_form", "## Review Outcome Handling", "## Outcome Notes"),
        ("legal_budget_review_form", "## Budget Lines", "## Budget Details"),
    ],
)
def test_review_package_completeness_fails_on_incomplete_linked_review_forms(
    tmp_path,
    repo_root,
    artifact_key,
    old_heading,
    new_heading,
):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    linked_form = Path(manifest.artifact_refs[artifact_key])
    linked_form.write_text(
        linked_form.read_text(encoding="utf-8").replace(old_heading, new_heading),
        encoding="utf-8",
    )

    report = build_review_package_completeness_report(
        manifest=manifest,
        review_package_path=review_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )

    assert report.status == "failed"
    check = next(item for item in report.checks if item.check_id == "linked_review_forms_complete")
    assert check.status == "failed"
    assert artifact_key in check.details["missing_sections_by_form"]
    with pytest.raises(ValueError, match="linked_review_forms_complete"):
        enforce_review_package_completeness(report)


@pytest.mark.parametrize(
    ("artifact_key", "old_text", "new_text"),
    [
        ("preflight_intake_review_form", "] sha=sha256:", "] sha=redacted:"),
        ("legal_budget_review_form", "] sha=sha256:", "] sha=redacted:"),
        (
            "legal_budget_review_form",
            "The generated proposal is not authorized for client or carrier submission.",
            "The generated proposal is ready.",
        ),
    ],
)
def test_review_package_completeness_fails_when_linked_forms_lose_evidence_or_boundary(
    tmp_path,
    repo_root,
    artifact_key,
    old_text,
    new_text,
):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    linked_form = Path(manifest.artifact_refs[artifact_key])
    linked_form.write_text(
        linked_form.read_text(encoding="utf-8").replace(old_text, new_text),
        encoding="utf-8",
    )

    report = build_review_package_completeness_report(
        manifest=manifest,
        review_package_path=review_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )

    assert report.status == "failed"
    check = next(
        item
        for item in report.checks
        if item.check_id == "linked_review_forms_preserve_evidence_and_boundaries"
    )
    assert check.status == "failed"
    assert artifact_key in check.details["missing_content_by_form"]
    with pytest.raises(ValueError, match="linked_review_forms_preserve_evidence_and_boundaries"):
        enforce_review_package_completeness(report)


def test_review_package_completeness_fails_when_readiness_details_are_not_rendered(
    tmp_path, repo_root
):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    review_path.write_text(
        review_path.read_text(encoding="utf-8").replace(
            "workflow/intake-to-budget.workflow.yaml#conflicts_review",
            "workflow/intake-to-budget.workflow.yaml#redacted",
        ),
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
        check.check_id == "readiness_blocker_details_rendered" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="readiness_blocker_details_rendered"):
        enforce_review_package_completeness(report)


def test_review_package_completeness_fails_on_incorrect_human_gate_status(tmp_path, repo_root):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    gate_report_path = Path(manifest.artifact_refs["human_gate_status_report"])
    gate_report = load_json(gate_report_path)
    for gate in gate_report["gates"]:
        if gate["gate_id"] == "human_budget_review":
            gate["status"] = "completed"
            gate["completed_by_human"] = True
    gate_report["pending_gate_count"] = 3
    gate_report_path.write_text(json.dumps(gate_report, indent=2) + "\n", encoding="utf-8")

    report = build_review_package_completeness_report(
        manifest=manifest,
        review_package_path=review_path,
        safety_report=safety_report,
        exception_readiness_report=exception_readiness_report,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "human_gate_status_report_complete" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="human_gate_status_report_complete"):
        enforce_review_package_completeness(report)


def test_review_package_completeness_fails_on_failed_ledger_integrity_report(tmp_path, repo_root):
    budget_dir = _run_budget(tmp_path, repo_root)
    manifest, safety_report, exception_readiness_report, review_path = _load_inputs(budget_dir)
    ledger_report_path = Path(manifest.artifact_refs["budget_run_ledger_integrity_report"])
    ledger_report = load_json(ledger_report_path)
    ledger_report["status"] = "failed"
    ledger_report_path.write_text(
        json.dumps(ledger_report, indent=2) + "\n",
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
        check.check_id == "run_ledger_integrity_reports_passed" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="run_ledger_integrity_reports_passed"):
        enforce_review_package_completeness(report)
