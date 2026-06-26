from lawfirm_os_intake.carrier_rejection_roadmap_audit import (
    build_carrier_rejection_roadmap_audit,
    run_carrier_rejection_roadmap_audit,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import CarrierRejectionRoadmapAuditReport
from lawfirm_os_intake.util import load_json


def test_carrier_rejection_roadmap_audit_marks_local_slices_complete(repo_root):
    report = build_carrier_rejection_roadmap_audit(repo_root)

    assert report.status == "local_candidate_complete_external_adoption_required"
    assert report.review_readiness == "ready_for_intake_pr_review"
    assert report.implemented_slice_count == 8
    assert report.total_slice_count == 8
    assert report.missing_artifact_refs == []
    assert report.missing_command_refs == []
    assert all(
        slice_status.status == "implemented_local_candidate" for slice_status in report.slices
    )
    assert "LawFirm-os-orchestrator" in report.external_adoption_target_repos
    assert "LawFirm-os-exceptions-lake-runtime" in report.external_adoption_target_repos
    assert "LawFirm-os-semantic-substrate" in report.external_adoption_target_repos
    assert report.no_connector_implemented is True
    assert report.no_lake_admission_performed is True
    assert report.sqlite_write_performed is False
    assert report.lake_write_performed is False
    assert report.external_writes_performed is False
    assert report.no_sibling_repo_writes is True
    assert report.no_canonical_mutation is True


def test_carrier_rejection_roadmap_audit_fails_closed_when_artifacts_missing(tmp_path):
    report = build_carrier_rejection_roadmap_audit(tmp_path)

    assert report.status == "incomplete_missing_local_artifacts"
    assert report.review_readiness == "not_ready_missing_local_artifacts"
    assert report.implemented_slice_count == 0
    assert report.missing_artifact_refs
    assert report.missing_command_refs
    assert any(check.status == "failed" for check in report.checks)


def test_carrier_rejection_roadmap_audit_writes_json_and_markdown(tmp_path, repo_root):
    report, run_dir = run_carrier_rejection_roadmap_audit(
        tmp_path / "roadmap-audit",
        repo_root=repo_root,
    )
    payload = load_json(run_dir / "carrier_rejection_roadmap_audit_report.json")
    loaded = CarrierRejectionRoadmapAuditReport.model_validate(payload)
    notes_text = (run_dir / "carrier_rejection_roadmap_audit_report.md").read_text(encoding="utf-8")

    assert loaded.audit_report_id == report.audit_report_id
    assert "Local Slice Status" in notes_text
    assert "External Adoption Still Required" in notes_text
    assert "SQLite write performed: False" in notes_text
    assert "Production capture" in notes_text


def test_carrier_rejection_roadmap_audit_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-carrier-rejection-roadmap",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "roadmap-audit"),
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(tmp_path / "roadmap-audit" / "carrier_rejection_roadmap_audit_report.json")
    report = CarrierRejectionRoadmapAuditReport.model_validate(payload)

    assert exit_code == 0
    assert report.implemented_slice_count == 8
    assert '"status": "local_candidate_complete_external_adoption_required"' in captured.out
    assert '"external_writes_performed": false' in captured.out
