from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import POCQATriageReport
from lawfirm_os_intake.poc_qa_triage import (
    POC_QA_TRIAGE_REPORT_FILENAME,
    run_poc_qa_triage_report,
)
from lawfirm_os_intake.util import load_json


FIXTURE_DIR = "apps/legal-intake-budget/src/fixtures"


def _fixture(repo_root, name):
    return repo_root / FIXTURE_DIR / name


def _run(repo_root, out_dir, *, include_validation=True):
    kwargs = {}
    if include_validation:
        kwargs["validation_suite_evidence_path"] = _fixture(
            repo_root,
            "demo-validation-suite-evidence-report.json",
        )
    return run_poc_qa_triage_report(
        ui_manifest_path=_fixture(repo_root, "demo-run-manifest.json"),
        synthetic_confidence_summary_path=_fixture(
            repo_root,
            "demo-synthetic-confidence-summary-report.json",
        ),
        synthetic_qa_review_run_path=_fixture(
            repo_root,
            "demo-synthetic-qa-review-run-report.json",
        ),
        synthetic_qa_blocker_report_path=_fixture(
            repo_root,
            "demo-synthetic-qa-blocker-report.json",
        ),
        ui_review_data_bundle_path=_fixture(repo_root, "demo-ui-review-data-bundle.json"),
        matter_linking_preflight_path=_fixture(
            repo_root,
            "demo-matter-linking-preflight-report.json",
        ),
        labor_employment_qa_matrix_path=_fixture(
            repo_root,
            "demo-labor-employment-qa-matrix-report.json",
        ),
        blocked_driver_impact_review_path=_fixture(
            repo_root,
            "demo-labor-employment-blocked-driver-impact-review-report.json",
        ),
        budget_output_expectations_path=_fixture(
            repo_root,
            "demo-labor-employment-budget-output-expectations-report.json",
        ),
        out_dir=out_dir,
        repo_root=repo_root,
        generated_at="2026-07-03T00:00:00Z",
        **kwargs,
    )


def test_poc_qa_triage_report_clears_validation_blocker_with_evidence(repo_root, tmp_path):
    report, out_dir = _run(repo_root, tmp_path)
    persisted = POCQATriageReport.model_validate(load_json(out_dir / POC_QA_TRIAGE_REPORT_FILENAME))

    assert persisted.poc_qa_triage_report_id == report.poc_qa_triage_report_id
    assert report.status == "poc_qa_ready_for_review"
    assert report.item_count == len(report.items) == 10
    assert report.blocked_item_count == 0
    assert report.p0_blocked_item_count == 0
    assert report.needs_review_item_count == 5
    assert report.watch_item_count == 2
    assert report.passed_item_count == 3
    assert report.source_validation_suite_evidence_report_id
    assert {item.item_id for item in report.items} >= {
        "synthetic_qa_recipe_green",
        "qa_review_queue_visible",
        "matter_linking_requires_human_confirmation",
        "labor_employment_fact_gates_visible",
        "blocked_driver_review_queue_visible",
        "budget_output_partition_visible",
        "validation_evidence_not_fresh_in_ui_bundle",
        "production_actions_stay_blocked",
    }
    validation_item = next(
        item
        for item in report.items
        if item.item_id == "validation_evidence_not_fresh_in_ui_bundle"
    )
    assert validation_item.status == "passed"
    assert "apps/legal-intake-budget/src/fixtures/demo-validation-suite-evidence-report.json" in (
        validation_item.evidence_refs
    )
    assert "scripts/run_full_pytest.py" in validation_item.evidence_refs
    assert validation_item.candidate_exception_lake_labels == []
    assert report.budget_submission_authorized is False
    assert report.matter_opening_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_poc_qa_triage_without_validation_evidence_fails_closed(repo_root, tmp_path):
    report, _ = _run(repo_root, tmp_path, include_validation=False)
    validation_item = next(
        item
        for item in report.items
        if item.item_id == "validation_evidence_not_fresh_in_ui_bundle"
    )

    assert report.status == "blocked_by_poc_qa_triage"
    assert report.blocked_item_count == 1
    assert report.p0_blocked_item_count == 1
    assert validation_item.status == "blocked"
    assert "qa_validation_evidence_stale_or_missing" in (
        validation_item.candidate_exception_lake_labels
    )


def test_poc_qa_triage_cli_writes_candidate_report(repo_root, tmp_path, capsys):
    code = main(
        [
            "build-poc-qa-triage-report",
            "--ui-manifest",
            str(_fixture(repo_root, "demo-run-manifest.json")),
            "--synthetic-confidence-summary",
            str(_fixture(repo_root, "demo-synthetic-confidence-summary-report.json")),
            "--synthetic-qa-review-run-report",
            str(_fixture(repo_root, "demo-synthetic-qa-review-run-report.json")),
            "--synthetic-qa-blocker-report",
            str(_fixture(repo_root, "demo-synthetic-qa-blocker-report.json")),
            "--ui-review-data-bundle",
            str(_fixture(repo_root, "demo-ui-review-data-bundle.json")),
            "--matter-linking-preflight",
            str(_fixture(repo_root, "demo-matter-linking-preflight-report.json")),
            "--labor-employment-qa-matrix",
            str(_fixture(repo_root, "demo-labor-employment-qa-matrix-report.json")),
            "--blocked-driver-impact-review",
            str(
                _fixture(
                    repo_root,
                    "demo-labor-employment-blocked-driver-impact-review-report.json",
                )
            ),
            "--budget-output-expectations",
            str(
                _fixture(repo_root, "demo-labor-employment-budget-output-expectations-report.json")
            ),
            "--validation-suite-evidence",
            str(_fixture(repo_root, "demo-validation-suite-evidence-report.json")),
            "--out-dir",
            str(tmp_path),
            "--repo-root",
            str(repo_root),
            "--generated-at",
            "2026-07-03T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert '"status": "poc_qa_ready_for_review"' in captured.out
    assert '"blocked_item_count": 0' in captured.out
    assert '"p0_blocked_item_count": 0' in captured.out
    assert '"budget_submission_authorized": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / POC_QA_TRIAGE_REPORT_FILENAME).is_file()
