from lawfirm_os_intake.budget_fixture_update_review import (
    build_budget_fixture_update_review_report,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetCalibrationReadinessCheck,
    BudgetCalibrationReadinessReport,
    BudgetFixtureUpdateReviewRecord,
    BudgetFixtureUpdateReviewReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


APPROVED_OUTPUT_REF = ".lawfirm-os-intake/replay/budget_revision_report.json"
TARGET_FIXTURE_REF = "examples/synthetic/budget-review/medmal-human-budget-review-change.json"


def _readiness_report(*, ready=True):
    return BudgetCalibrationReadinessReport(
        budget_calibration_readiness_report_id="budget-calibration-readiness-1",
        status=(
            "ready_for_manual_fixture_update_review" if ready else "blocked_by_calibration_chain"
        ),
        corpus_report_id="corpus-report-1",
        replay_plan_id="replay-plan-1",
        replay_execution_report_id="replay-execution-1",
        review_packet_id="review-packet-1",
        review_outcome_report_id="review-outcome-report-1",
        fixture_binding_candidate_report_id="fixture-binding-candidate-report-1",
        fixture_binding_handoff_report_id="fixture-binding-handoff-report-1",
        replay_case_id="replay-case-1",
        source_corpus_report_ref="budget_calibration_corpus_report.json",
        source_replay_plan_ref="budget_corpus_replay_plan.json",
        source_replay_execution_report_ref="budget_corpus_replay_execution_report.json",
        source_review_packet_ref="budget_corpus_replay_review_packet.json",
        source_review_outcome_report_ref="budget_corpus_replay_review_outcome_report.json",
        source_fixture_binding_candidate_report_ref="budget_fixture_binding_candidate_report.json",
        source_fixture_binding_handoff_report_ref="budget_fixture_binding_handoff_report.json",
        ready_fixture_binding_handoff_count=1,
        blocked_fixture_binding_handoff_count=0 if ready else 1,
        approved_output_refs=[APPROVED_OUTPUT_REF],
        proposed_target_fixture_refs=[TARGET_FIXTURE_REF],
        checks=[
            BudgetCalibrationReadinessCheck(
                check_id="calibration_readiness_fixture_check",
                status="passed" if ready else "failed",
                message="Synthetic readiness fixture.",
            )
        ],
        required_next_gates=[
            "human_fixture_update_review",
            "separate_fixture_update_pr_if_accepted",
            "append_only_fixture_update_record",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        ],
        generated_at="2026-06-26T00:00:00Z",
    )


def _review_record(
    *,
    decision="accept_for_separate_fixture_update_pr",
    accepted_output_refs=None,
    target_fixture_refs=None,
):
    accepted = decision in {
        "accept_for_separate_fixture_update_pr",
        "accept_with_corrections_for_separate_fixture_update_pr",
    }
    return BudgetFixtureUpdateReviewRecord(
        fixture_update_review_id=f"fixture-update-review-{decision}",
        budget_calibration_readiness_report_id="budget-calibration-readiness-1",
        fixture_binding_handoff_report_id="fixture-binding-handoff-report-1",
        replay_case_id="replay-case-1",
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-26T00:00:00Z",
        decision=decision,
        decision_reason="Synthetic fixture update review decision.",
        accepted_output_refs=accepted_output_refs
        if accepted_output_refs is not None
        else ([APPROVED_OUTPUT_REF] if accepted else []),
        rejected_output_refs=[] if accepted else [APPROVED_OUTPUT_REF],
        target_fixture_refs=target_fixture_refs
        if target_fixture_refs is not None
        else ([TARGET_FIXTURE_REF] if accepted else []),
        reviewer_corrections=(
            ["Preserve old fixture as superseded evidence."]
            if decision == "accept_with_corrections_for_separate_fixture_update_pr"
            else []
        ),
        required_followups=["Open a separate fixture-update PR."] if accepted else [],
        reviewed_red_team_notes=[
            "Confirmed this review record does not mutate fixtures or apply learning."
        ],
    )


def test_fixture_update_review_records_accepted_separate_pr_without_mutation():
    report = build_budget_fixture_update_review_report(
        readiness_report=_readiness_report(),
        readiness_report_ref="budget_calibration_readiness_report.json",
        review_record=_review_record(),
        history_ref="budget_fixture_update_review_history.jsonl",
    )

    assert report.status == "fixture_update_review_recorded_separate_pr_required"
    assert report.accepted_for_fixture_update_pr is True
    assert report.separate_fixture_update_pr_required is True
    assert report.accepted_output_refs == [APPROVED_OUTPUT_REF]
    assert report.target_fixture_refs == [TARGET_FIXTURE_REF]
    assert all(check.status == "passed" for check in report.checks)
    assert report.fixture_update_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.downstream_learning_gate_allowed is False
    assert report.calibration_applied is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_fixture_update_review_records_rejection_without_pr():
    report = build_budget_fixture_update_review_report(
        readiness_report=_readiness_report(),
        readiness_report_ref="budget_calibration_readiness_report.json",
        review_record=_review_record(decision="reject_fixture_update"),
        history_ref="budget_fixture_update_review_history.jsonl",
    )

    assert report.status == "fixture_update_review_recorded_no_fixture_pr"
    assert report.accepted_for_fixture_update_pr is False
    assert report.separate_fixture_update_pr_required is False
    assert report.rejected_output_refs == [APPROVED_OUTPUT_REF]
    assert all(check.status == "passed" for check in report.checks)
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_fixture_update_review_blocks_when_readiness_not_ready():
    report = build_budget_fixture_update_review_report(
        readiness_report=_readiness_report(ready=False),
        readiness_report_ref="budget_calibration_readiness_report.json",
        review_record=_review_record(),
        history_ref="budget_fixture_update_review_history.jsonl",
    )

    assert report.status == "blocked_by_fixture_update_review_evidence"
    assert report.accepted_for_fixture_update_pr is False
    assert report.separate_fixture_update_pr_required is False
    assert any(
        check.check_id == "calibration_readiness_allows_manual_review" and check.status == "failed"
        for check in report.checks
    )
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_fixture_update_review_cli_writes_report_and_history(tmp_path, capsys):
    readiness_path = write_json(
        tmp_path / "budget_calibration_readiness_report.json",
        _readiness_report().model_dump(mode="json"),
    )
    review_path = write_json(
        tmp_path / "fixture_update_review.json",
        _review_record().model_dump(mode="json"),
    )

    exit_code = main(
        [
            "record-budget-fixture-update-review",
            "--calibration-readiness-report",
            str(readiness_path),
            "--review",
            str(review_path),
            "--out-dir",
            str(tmp_path / "fixture-update-review"),
        ]
    )
    captured = capsys.readouterr()
    report_path = tmp_path / "fixture-update-review" / "budget_fixture_update_review_report.json"
    history_path = tmp_path / "fixture-update-review" / "budget_fixture_update_review_history.jsonl"
    notes_path = tmp_path / "fixture-update-review" / "budget_fixture_update_review_report.md"
    report = BudgetFixtureUpdateReviewReport.model_validate(load_json(report_path))
    history = load_jsonl(history_path)

    assert exit_code == 0
    assert report.status == "fixture_update_review_recorded_separate_pr_required"
    assert report.append_only_history_ref == str(history_path)
    assert len(history) == 1
    assert (
        history[0]["fixture_update_review_id"]
        == "fixture-update-review-accept_for_separate_fixture_update_pr"
    )
    assert '"fixture_update_pr_created": false' in captured.out
    assert '"fixture_files_mutated": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not update fixtures" in notes_path.read_text(encoding="utf-8")


def test_fixture_update_review_cli_rejects_unbound_output_ref(tmp_path, capsys):
    readiness_path = write_json(
        tmp_path / "budget_calibration_readiness_report.json",
        _readiness_report().model_dump(mode="json"),
    )
    review_path = write_json(
        tmp_path / "fixture_update_review.json",
        _review_record(accepted_output_refs=[".lawfirm-os-intake/replay/unbound.json"]).model_dump(
            mode="json"
        ),
    )

    exit_code = main(
        [
            "record-budget-fixture-update-review",
            "--calibration-readiness-report",
            str(readiness_path),
            "--review",
            str(review_path),
            "--out-dir",
            str(tmp_path / "fixture-update-review"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "not approved by readiness report" in captured.err
