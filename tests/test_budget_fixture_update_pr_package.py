from lawfirm_os_intake.budget_fixture_update_pr_package import (
    build_budget_fixture_update_pr_package_report,
    run_budget_fixture_update_pr_package,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetFixtureUpdatePRPackageReport,
    BudgetFixtureUpdateReviewCheck,
    BudgetFixtureUpdateReviewReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


APPROVED_OUTPUT_REF = ".lawfirm-os-intake/replay/budget_revision_report.json"
TARGET_FIXTURE_REF = "examples/synthetic/budget-review/medmal-human-budget-review-change.json"


def _review_report(*, status="fixture_update_review_recorded_separate_pr_required"):
    accepted = status == "fixture_update_review_recorded_separate_pr_required"
    blocked = status == "blocked_by_fixture_update_review_evidence"
    return BudgetFixtureUpdateReviewReport(
        fixture_update_review_report_id=f"fixture-update-review-report-{status}",
        status=status,
        source_budget_calibration_readiness_report_id="budget-calibration-readiness-1",
        source_budget_calibration_readiness_report_ref="budget_calibration_readiness_report.json",
        source_budget_calibration_readiness_status=(
            "blocked_by_calibration_chain" if blocked else "ready_for_manual_fixture_update_review"
        ),
        fixture_binding_handoff_report_id="fixture-binding-handoff-report-1",
        replay_case_id="replay-case-1",
        fixture_update_review_id="fixture-update-review-1",
        decision=(
            "accept_for_separate_fixture_update_pr"
            if accepted or blocked
            else "reject_fixture_update"
        ),
        decision_reason="Synthetic fixture update review for PR package tests.",
        accepted_output_refs=[APPROVED_OUTPUT_REF] if accepted or blocked else [],
        rejected_output_refs=[] if accepted or blocked else [APPROVED_OUTPUT_REF],
        target_fixture_refs=[TARGET_FIXTURE_REF] if accepted or blocked else [],
        append_only_history_ref="budget_fixture_update_review_history.jsonl",
        checks=[
            BudgetFixtureUpdateReviewCheck(
                check_id="synthetic_fixture_update_review_check",
                status="failed" if blocked else "passed",
                message="Synthetic fixture update review check.",
            )
        ],
        required_next_gates=[
            "append_only_fixture_update_review_record",
            "separate_fixture_update_pr_if_accepted",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        ],
        accepted_for_fixture_update_pr=accepted,
        separate_fixture_update_pr_required=accepted,
        generated_at="2026-06-26T00:00:00Z",
    )


def test_fixture_update_pr_package_ready_for_accepted_review():
    report = build_budget_fixture_update_pr_package_report(
        fixture_update_review_report=_review_report(),
        fixture_update_review_report_ref="budget_fixture_update_review_report.json",
    )
    item = report.package_items[0]

    assert report.status == "fixture_update_pr_package_ready_for_manual_pr"
    assert report.manual_fixture_update_pr_required is True
    assert report.item_count == report.ready_item_count == 1
    assert report.blocked_item_count == 0
    assert item.accepted_output_refs == [APPROVED_OUTPUT_REF]
    assert item.target_fixture_ref == TARGET_FIXTURE_REF
    assert item.proposed_manual_action == "update_synthetic_fixture_in_separate_pr"
    assert any("separate PR" in step for step in item.required_manual_steps)
    assert report.github_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.downstream_learning_gate_allowed is False
    assert report.calibration_applied is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_fixture_update_pr_package_not_needed_for_rejected_review():
    report = build_budget_fixture_update_pr_package_report(
        fixture_update_review_report=_review_report(
            status="fixture_update_review_recorded_no_fixture_pr"
        ),
        fixture_update_review_report_ref="budget_fixture_update_review_report.json",
    )

    assert report.status == "no_fixture_update_pr_package_needed"
    assert report.manual_fixture_update_pr_required is False
    assert report.package_items == []
    assert report.github_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_fixture_update_pr_package_blocks_failed_review():
    report = build_budget_fixture_update_pr_package_report(
        fixture_update_review_report=_review_report(
            status="blocked_by_fixture_update_review_evidence"
        ),
        fixture_update_review_report_ref="budget_fixture_update_review_report.json",
    )

    assert report.status == "blocked_by_fixture_update_review"
    assert report.manual_fixture_update_pr_required is False
    assert any(
        check.check_id == "fixture_update_review_recorded_without_writes"
        and check.status == "failed"
        for check in report.checks
    )
    assert report.github_pr_created is False
    assert report.fixture_files_mutated is False


def test_fixture_update_pr_package_cli_writes_report_and_items(tmp_path, capsys):
    review_report_path = write_json(
        tmp_path / "budget_fixture_update_review_report.json",
        _review_report().model_dump(mode="json"),
    )

    exit_code = main(
        [
            "build-budget-fixture-update-pr-package",
            "--fixture-update-review-report",
            str(review_report_path),
            "--out-dir",
            str(tmp_path / "fixture-update-pr-package"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path / "fixture-update-pr-package" / "budget_fixture_update_pr_package_report.json"
    )
    items_path = (
        tmp_path / "fixture-update-pr-package" / "budget_fixture_update_pr_package_items.jsonl"
    )
    notes_path = (
        tmp_path / "fixture-update-pr-package" / "budget_fixture_update_pr_package_report.md"
    )
    report = BudgetFixtureUpdatePRPackageReport.model_validate(load_json(report_path))
    items = load_jsonl(items_path)

    assert exit_code == 0
    assert report.status == "fixture_update_pr_package_ready_for_manual_pr"
    assert report.package_item_output_ref == str(items_path)
    assert len(items) == 1
    assert '"github_pr_created": false' in captured.out
    assert '"fixture_files_mutated": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not edit fixtures" in notes_path.read_text(encoding="utf-8")


def test_run_fixture_update_pr_package_blocks_failed_review(tmp_path):
    review_report_path = write_json(
        tmp_path / "budget_fixture_update_review_report.json",
        _review_report(status="blocked_by_fixture_update_review_evidence").model_dump(mode="json"),
    )

    report, run_dir = run_budget_fixture_update_pr_package(
        fixture_update_review_report_path=review_report_path,
        out_dir=tmp_path / "fixture-update-pr-package",
    )
    persisted = BudgetFixtureUpdatePRPackageReport.model_validate(
        load_json(run_dir / "budget_fixture_update_pr_package_report.json")
    )

    assert report.status == "blocked_by_fixture_update_review"
    assert persisted.fixture_update_pr_package_report_id == (
        report.fixture_update_pr_package_report_id
    )
    assert persisted.github_pr_created is False
    assert persisted.fixture_files_mutated is False
