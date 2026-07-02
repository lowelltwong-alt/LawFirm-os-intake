from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_confidence_summary import (
    SYNTHETIC_CONFIDENCE_SUMMARY_NOTES_FILENAME,
    SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME,
    run_synthetic_confidence_summary,
)
from lawfirm_os_intake.util import load_json, write_json


def _write_inputs(tmp_path, *, blocked=False):
    review_run = write_json(
        tmp_path / "synthetic_qa_review_run_report.json",
        {
            "synthetic_qa_review_run_report_id": "syntheticqareviewrun_test",
            "status": (
                "blocked_by_synthetic_qa_review_run" if blocked else "synthetic_qa_review_run_ready"
            ),
            "step_count": 2,
            "failed_step_count": 1 if blocked else 0,
            "steps": [
                {"step_id": "budget_coherence", "status": "passed"},
                {
                    "step_id": "ui_review_data_bundle",
                    "status": "failed" if blocked else "passed",
                },
            ],
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )
    bundle = write_json(
        tmp_path / "synthetic_qa_bundle_report.json",
        {
            "synthetic_qa_bundle_report_id": "synthetic_qa_bundle_test",
            "status": "blocked" if blocked else "pending_review",
            "artifact_count": 3,
            "missing_required_artifact_count": 1 if blocked else 0,
            "blocked_artifact_count": 1 if blocked else 0,
            "pending_artifact_count": 1,
            "failed_artifact_count": 0,
            "artifacts": [],
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )
    manifest = write_json(
        tmp_path / "ui_review_manifest.json",
        {
            "manifestId": "ui_review_manifest_test",
            "overallStatus": "pending",
            "qualityGates": [
                {"gateId": "budget_coherence", "status": "passed"},
                {"gateId": "synthetic_qa_bundle", "status": "pending_review"},
                {
                    "gateId": "ui_review_data_bundle",
                    "status": "blocked" if blocked else "pending_review",
                },
            ],
        },
    )
    ui_bundle = write_json(
        tmp_path / "ui_review_data_bundle.json",
        {
            "ui_review_data_bundle_id": "ui_review_data_bundle_test",
            "status": "ready_for_review",
            "detail_report_count": 6,
            "present_detail_report_count": 6,
            "missing_required_detail_report_count": 0,
            "external_write_report_count": 0,
            "detail_reports": [],
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
        },
    )
    return review_run, bundle, manifest, ui_bundle


def test_synthetic_confidence_summary_ready_inputs(tmp_path):
    review_run, bundle, manifest, ui_bundle = _write_inputs(tmp_path)
    report, out_dir = run_synthetic_confidence_summary(
        synthetic_qa_review_run_report_path=review_run,
        synthetic_qa_bundle_report_path=bundle,
        ui_manifest_path=manifest,
        ui_review_data_bundle_path=ui_bundle,
        out_dir=tmp_path / "summary",
        generated_at="2026-07-02T00:00:00Z",
    )
    payload = load_json(out_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME)
    notes = (out_dir / SYNTHETIC_CONFIDENCE_SUMMARY_NOTES_FILENAME).read_text(encoding="utf-8")

    assert report.status == "synthetic_confidence_summary_ready_for_review"
    assert report.testing_readiness_state == "synthetic_qa_ready_pending_review"
    assert report.top_blockers == []
    assert report.qa_step_count == 2
    assert report.qa_passed_step_count == 2
    assert report.quality_gate_pending_count == 2
    assert report.readiness_item_count == 5
    assert report.display_banner["not_production_ready"] is True
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert payload["status"] == report.status
    assert "candidate-only local QA evidence" in notes


def test_synthetic_confidence_summary_blocks_missing_or_failed_evidence(tmp_path):
    review_run, bundle, manifest, ui_bundle = _write_inputs(tmp_path, blocked=True)
    report, _ = run_synthetic_confidence_summary(
        synthetic_qa_review_run_report_path=review_run,
        synthetic_qa_bundle_report_path=bundle,
        ui_manifest_path=manifest,
        ui_review_data_bundle_path=ui_bundle,
        out_dir=tmp_path / "summary",
    )

    assert report.status == "blocked_by_synthetic_confidence_summary"
    assert report.testing_readiness_state == "blocked_missing_or_failed_evidence"
    assert report.qa_failed_step_count == 1
    assert report.qa_missing_required_artifact_count == 1
    assert report.quality_gate_blocked_count == 1
    assert any("synthetic QA recipe steps failed" in blocker for blocker in report.top_blockers)
    assert report.required_next_actions[0].startswith("Resolve blocker:")


def test_synthetic_confidence_summary_cli(tmp_path, capsys):
    review_run, bundle, manifest, ui_bundle = _write_inputs(tmp_path)
    code = main(
        [
            "build-synthetic-confidence-summary",
            "--synthetic-qa-review-run-report",
            str(review_run),
            "--synthetic-qa-bundle-report",
            str(bundle),
            "--ui-manifest",
            str(manifest),
            "--ui-review-data-bundle",
            str(ui_bundle),
            "--out-dir",
            str(tmp_path / "summary"),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert '"status": "synthetic_confidence_summary_ready_for_review"' in captured.out
    assert '"testing_readiness_state": "synthetic_qa_ready_pending_review"' in captured.out
    assert '"budget_submission_authorized": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / "summary" / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME).is_file()
