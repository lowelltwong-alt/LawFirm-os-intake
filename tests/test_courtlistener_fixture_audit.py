from lawfirm_os_intake.cli import main
from lawfirm_os_intake.courtlistener_fixture_audit import run_courtlistener_fixture_audit
from lawfirm_os_intake.models import (
    CourtListenerDatasetManifest,
    CourtListenerDocketSnapshot,
    CourtListenerFixtureAuditReport,
)
from lawfirm_os_intake.util import load_json, write_json


MANIFEST_REF = "examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json"
SNAPSHOT_REF = "examples/synthetic/courtlistener-derived/labor-employment-removal-snapshot.json"


def test_courtlistener_fixture_manifest_and_snapshot_validate(repo_root):
    manifest = CourtListenerDatasetManifest.model_validate(load_json(repo_root / MANIFEST_REF))
    snapshot = CourtListenerDocketSnapshot.model_validate(load_json(repo_root / SNAPSHOT_REF))

    assert manifest.primary_practice_area == "labor_employment"
    assert manifest.live_calls_performed is False
    assert manifest.training_pipeline_created is False
    assert snapshot.source_access_mode == "offline_fixture"
    assert snapshot.real_person_data_present is False
    assert snapshot.public_records_ingested is False
    assert snapshot.first_docket_day_count == 120


def test_courtlistener_fixture_audit_ready_for_review(tmp_path, repo_root):
    report, run_dir = run_courtlistener_fixture_audit(
        repo_root=repo_root,
        manifest_path=MANIFEST_REF,
        out_dir=tmp_path / "courtlistener-fixture-audit",
    )
    persisted = CourtListenerFixtureAuditReport.model_validate(
        load_json(run_dir / "courtlistener_fixture_audit_report.json")
    )

    assert persisted.courtlistener_fixture_audit_report_id == (
        report.courtlistener_fixture_audit_report_id
    )
    assert persisted.status == "courtlistener_fixture_ready_for_review"
    assert persisted.snapshot_count == 1
    assert persisted.document_label_count == 5
    assert persisted.conflict_seed_label_count == 4
    assert persisted.budget_driver_label_count == 6
    assert persisted.timeline_event_label_count == 3
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.public_records_ingested is False
    assert persisted.live_calls_performed is False
    assert persisted.pacer_purchase_performed is False
    assert persisted.recap_fetch_purchase_performed is False
    assert persisted.training_pipeline_created is False
    assert persisted.budget_accuracy_claimed is False
    assert persisted.external_writes_performed is False

    notes = (run_dir / "courtlistener_fixture_audit_report.md").read_text(encoding="utf-8")
    assert "Public records ingested: False" in notes
    assert "Budget accuracy claimed: False" in notes


def test_courtlistener_fixture_audit_blocks_label_hash_drift(tmp_path, repo_root):
    manifest = load_json(repo_root / MANIFEST_REF)
    manifest["intake_stage_document_labels"][0]["source_ref"]["sha256"] = "sha256:" + ("0" * 64)
    manifest_path = write_json(tmp_path / "hash-drift-manifest.json", manifest)

    report, _ = run_courtlistener_fixture_audit(
        repo_root=repo_root,
        manifest_path=manifest_path,
        out_dir=tmp_path / "hash-drift-audit",
    )

    assert report.status == "blocked_courtlistener_fixture"
    source_check = next(
        check
        for check in report.checks
        if check.check_id == "all_labels_have_resolving_source_refs_and_hashes"
    )
    assert source_check.status == "failed"
    assert source_check.details["issues"][0]["issue"] == "hash_mismatch"
    assert report.external_writes_performed is False


def test_courtlistener_fixture_audit_blocks_post_discovery_positive_leak(
    tmp_path,
    repo_root,
):
    snapshot = load_json(repo_root / SNAPSHOT_REF)
    for document in snapshot["documents"]:
        if document["source_document_id"] == "synthetic_deposition_notice_doc":
            document["case_stage"] = "intake_stage"
            document["filed_day"] = 80
    snapshot_path = write_json(tmp_path / "positive-leak-snapshot.json", snapshot)
    manifest = load_json(repo_root / MANIFEST_REF)
    manifest["fixture_snapshot_refs"] = [str(snapshot_path)]
    manifest_path = write_json(tmp_path / "positive-leak-manifest.json", manifest)

    report, _ = run_courtlistener_fixture_audit(
        repo_root=repo_root,
        manifest_path=manifest_path,
        out_dir=tmp_path / "positive-leak-audit",
    )

    assert report.status == "blocked_courtlistener_fixture"
    early_case_check = next(
        check
        for check in report.checks
        if check.check_id == "positive_document_labels_stay_early_case"
    )
    assert early_case_check.status == "failed"
    assert early_case_check.details["issues"][0]["issue"] == (
        "prohibited_document_type_in_positive_corpus"
    )


def test_courtlistener_fixture_audit_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-courtlistener-fixture",
            "--repo-root",
            str(repo_root),
            "--manifest",
            str(repo_root / MANIFEST_REF),
            "--out-dir",
            str(tmp_path / "courtlistener-fixture-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "courtlistener_fixture_ready_for_review"' in captured.out
    assert '"snapshot_count": 1' in captured.out
    assert '"live_calls_performed": false' in captured.out
    assert (
        tmp_path / "courtlistener-fixture-cli" / "courtlistener_fixture_audit_report.json"
    ).is_file()
