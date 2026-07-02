from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_qa_blocker_report import (
    SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
    run_synthetic_qa_blocker_report,
)
from lawfirm_os_intake.util import load_json, write_json


def _write_inputs(tmp_path, *, blocked=False, side_effect=False):
    manifest = write_json(
        tmp_path / "ui_review_manifest.json",
        {
            "manifestId": "ui_review_manifest_test",
            "overallStatus": "pending",
            "qualityGates": [
                {
                    "gateId": "budget_coherence",
                    "label": "Budget Coherence",
                    "status": "passed",
                    "evidenceFile": "budget_coherence_report.json",
                    "owner": "qa-reference",
                    "notes": ["Budget math holds."],
                },
                {
                    "gateId": "synthetic_qa_blocker_report",
                    "label": "Synthetic QA Blocker Report",
                    "status": "pending_review",
                    "evidenceFile": "synthetic_qa_blocker_report.json",
                    "owner": "qa-reference",
                    "notes": ["Self gate should not create a recursive blocker row."],
                },
                {
                    "gateId": "labor_employment_qa_matrix",
                    "label": "L&E QA Matrix",
                    "status": "blocked" if blocked else "pending_review",
                    "evidenceFile": "labor_employment_qa_matrix_report.json",
                    "owner": "qa-reference",
                    "notes": ["L&E matrix remains under review."],
                },
            ],
        },
    )
    confidence = write_json(
        tmp_path / "synthetic_confidence_summary_report.json",
        {
            "synthetic_confidence_summary_report_id": "synthetic_confidence_summary_test",
            "status": (
                "blocked_by_synthetic_confidence_summary"
                if blocked
                else "synthetic_confidence_summary_ready_for_review"
            ),
            "readiness_items": [
                {
                    "item_id": "synthetic_qa_recipe",
                    "label": "Synthetic QA Recipe",
                    "owner": "qa-reference",
                    "state": "ready_for_review",
                    "evidence_refs": ["synthetic_qa_review_run_report.json"],
                    "notes": ["Recipe passed."],
                },
                {
                    "item_id": "owner_review_backlog",
                    "label": "Owner Review Backlog",
                    "owner": "human-or-owner-review",
                    "state": "blocked" if blocked else "pending_review",
                    "evidence_refs": ["ui_review_manifest.json"],
                    "notes": ["Owner review is still required."],
                },
            ],
            "top_blockers": ["Required QA artifact is blocked"] if blocked else [],
            "required_next_actions": [
                "Start manual synthetic QA review from the read-only UI.",
                "Keep candidate-only boundaries in place.",
            ],
            "external_writes_performed": side_effect,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "training_pipeline_created": False,
        },
    )
    review_run = write_json(
        tmp_path / "synthetic_qa_review_run_report.json",
        {
            "synthetic_qa_review_run_report_id": "synthetic_qa_review_run_test",
            "status": (
                "blocked_by_synthetic_qa_review_run" if blocked else "synthetic_qa_review_run_ready"
            ),
            "steps": [
                {
                    "step_id": "budget_coherence",
                    "label": "Budget Coherence",
                    "status": "passed",
                    "observed_status": "passed",
                    "artifact_ref": "budget_coherence_report.json",
                    "notes": ["Coherence passed."],
                },
                {
                    "step_id": "labor_employment_qa_matrix",
                    "label": "L&E QA Matrix",
                    "status": "failed" if blocked else "passed",
                    "observed_status": "blocked" if blocked else "ready",
                    "artifact_ref": "labor_employment_qa_matrix_report.json",
                    "notes": ["Matrix failed." if blocked else "Matrix passed."],
                },
            ],
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "silent_learning_performed": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "training_pipeline_created": False,
        },
    )
    return manifest, confidence, review_run


def test_synthetic_qa_blocker_report_ready_pending_queue(tmp_path):
    manifest, confidence, review_run = _write_inputs(tmp_path)
    report, out_dir = run_synthetic_qa_blocker_report(
        ui_manifest_path=manifest,
        synthetic_confidence_summary_path=confidence,
        synthetic_qa_review_run_report_path=review_run,
        out_dir=tmp_path / "blockers",
        generated_at="2026-07-02T00:00:00Z",
    )
    payload = load_json(out_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME)

    assert report.status == "synthetic_qa_blocker_report_ready_for_review"
    assert report.row_count == 2
    assert report.failed_row_count == 0
    assert report.blocked_row_count == 0
    assert report.pending_review_row_count == 2
    assert report.blocked_action_count == 0
    assert report.needs_review_action_count == 2
    assert report.fixed_action_count == 0
    assert report.ready_action_count == 0
    assert report.review_queue_state == "needs_review"
    assert {row.source for row in report.rows} == {"quality_gate", "readiness_item"}
    assert all(row.state == "pending_review" for row in report.rows)
    assert all(row.action_state == "needs_review" for row in report.rows)
    assert all(row.recommended_next_action for row in report.rows)
    assert all(row.candidate_exception_lake_labels for row in report.rows)
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert payload["row_count"] == report.row_count


def test_synthetic_qa_blocker_report_blocks_failed_evidence(tmp_path):
    manifest, confidence, review_run = _write_inputs(tmp_path, blocked=True)
    report, _ = run_synthetic_qa_blocker_report(
        ui_manifest_path=manifest,
        synthetic_confidence_summary_path=confidence,
        synthetic_qa_review_run_report_path=review_run,
        out_dir=tmp_path / "blockers",
    )

    assert report.status == "blocked_by_synthetic_qa_blocker_report"
    assert report.failed_row_count == 1
    assert report.blocked_row_count == 3
    assert report.blocked_action_count == 4
    assert report.needs_review_action_count == 0
    assert report.review_queue_state == "blocked"
    assert any(row.source == "qa_step" and row.state == "failed" for row in report.rows)
    assert any(row.source == "top_blocker" for row in report.rows)
    assert all(row.action_state == "blocked" for row in report.rows)
    assert report.required_next_actions[0].startswith("Resolve")


def test_synthetic_qa_blocker_report_fails_side_effect_boundary(tmp_path):
    manifest, confidence, review_run = _write_inputs(tmp_path, blocked=True, side_effect=True)
    report, _ = run_synthetic_qa_blocker_report(
        ui_manifest_path=manifest,
        synthetic_confidence_summary_path=confidence,
        synthetic_qa_review_run_report_path=review_run,
        out_dir=tmp_path / "blockers",
    )

    assert report.status == "failed_synthetic_qa_blocker_boundary"
    assert "Do not write to Exception Lake" in report.required_next_actions[1]
    assert report.external_writes_performed is False
    assert report.lake_write_performed is False


def test_synthetic_qa_blocker_report_cli(tmp_path, capsys):
    manifest, confidence, review_run = _write_inputs(tmp_path)
    code = main(
        [
            "build-synthetic-qa-blocker-report",
            "--ui-manifest",
            str(manifest),
            "--synthetic-confidence-summary",
            str(confidence),
            "--synthetic-qa-review-run-report",
            str(review_run),
            "--out-dir",
            str(tmp_path / "blockers"),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert '"status": "synthetic_qa_blocker_report_ready_for_review"' in captured.out
    assert '"pending_review_row_count": 2' in captured.out
    assert '"review_queue_state": "needs_review"' in captured.out
    assert '"budget_submission_authorized": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / "blockers" / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME).is_file()
