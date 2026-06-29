from hashlib import sha256

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.intake_vertical_readiness_audit import (
    run_intake_vertical_readiness_audit,
)
from lawfirm_os_intake.budget_fixture_update_review import (
    run_budget_fixture_update_review_record,
)
from lawfirm_os_intake.budget_fixture_update_pr_package import (
    run_budget_fixture_update_pr_package,
)
from lawfirm_os_intake.learning_owner_handoffs import run_learning_owner_handoffs
from lawfirm_os_intake.learning_proposed_changes import run_learning_proposed_changes
from lawfirm_os_intake.learning_shadow_eval_results import run_learning_shadow_eval_results
from lawfirm_os_intake.models import (
    BudgetCalibrationReadinessCheck,
    BudgetCalibrationReadinessReport,
    BudgetFixtureUpdateReviewCheck,
    BudgetFixtureUpdateReviewRecord,
    BudgetFixtureUpdateReviewReport,
    BudgetFixtureUpdatePRPackageCheck,
    BudgetFixtureUpdatePRPackageReport,
    BudgetLakeAdmissionBundleCheck,
    BudgetLakeAdmissionBundleReport,
    BudgetLakeEvidenceArtifact,
    IntakeVerticalReadinessAuditReport,
)
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.util import write_json


def _change_set_path(tmp_path, repo_root):
    _, run_dir = run_learning_proposed_changes(
        shadow_eval_plan_path=repo_root
        / "examples/synthetic/learning/proposed-change-shadow-eval-plan.json",
        promotion_readiness_report_path=repo_root
        / "examples/synthetic/learning/proposed-change-readiness-report.json",
        out_dir=tmp_path / "learning-proposed-changes",
    )
    return run_dir / "learning_proposed_change_set.json"


def _owner_handoff_report_path(tmp_path, repo_root, *, include_fixture_results=True):
    change_set_path = _change_set_path(tmp_path, repo_root)
    fixture_result_paths = []
    if include_fixture_results:
        fixture_result_paths = [
            repo_root / "examples/synthetic/learning/shadow-eval-result-budget-driver.json",
            repo_root / "examples/synthetic/learning/shadow-eval-result-capture-completeness.json",
        ]
    _, shadow_dir = run_learning_shadow_eval_results(
        proposed_change_set_path=change_set_path,
        fixture_result_paths=fixture_result_paths,
        out_dir=tmp_path / "learning-shadow-eval",
    )
    _, handoff_dir = run_learning_owner_handoffs(
        shadow_eval_result_report_path=shadow_dir / "learning_shadow_eval_result_report.json",
        out_dir=tmp_path / "learning-owner-handoffs",
    )
    return handoff_dir / "learning_owner_handoff_report.json"


def _sha256(path):
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _lake_bundle_report_path(tmp_path, *, ready=True):
    artifact_path = write_json(
        tmp_path / "lake-bundle-artifacts" / "budget_change_ledger_report.json",
        {"synthetic": True},
    )
    bundle_dir = tmp_path / "lake-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        BudgetLakeAdmissionBundleCheck(
            check_id="synthetic_bundle_check",
            status="passed" if ready else "failed",
            message="Synthetic readiness-audit fixture.",
        )
    ]
    report = BudgetLakeAdmissionBundleReport(
        bundle_report_id="budgetlakebundle-readiness-fixture",
        status=("ready_for_exception_lake_review" if ready else "blocked_inconsistent_evidence"),
        artifact_count=1,
        ledger_report_count=1,
        jsonl_row_count=0,
        total_event_count=1,
        budget_proposal_ids=["budget-proposal-readiness-fixture"],
        preflight_packet_ids=["preflight-readiness-fixture"],
        run_ids=["run-readiness-fixture"],
        candidate_record_families=["budget_human_change_record"],
        local_event_labels=["budget_human_change_recorded"],
        artifacts=[
            BudgetLakeEvidenceArtifact(
                artifact_id="budgetlakeartifact-readiness-fixture",
                artifact_kind="budget_change_ledger_report",
                artifact_ref=str(artifact_path),
                sha256=_sha256(artifact_path),
                report_id="budget-change-ledger-readiness-fixture",
                ledger_id="budget-change-ledger-readiness-fixture",
                run_id="run-readiness-fixture",
                preflight_packet_id="preflight-readiness-fixture",
                budget_proposal_id="budget-proposal-readiness-fixture",
                event_count=1,
                row_event_count=0,
                event_kind_counts={"human_budget_change_recorded": 1},
                local_event_labels=["budget_human_change_recorded"],
                candidate_record_families=["budget_human_change_record"],
            )
        ],
        checks=checks,
        required_next_gates=[
            "human_budget_event_lake_bundle_review",
            "exception_lake_runtime_admission_validation",
        ],
        generated_at="2026-06-26T00:00:00Z",
    )
    return write_json(
        bundle_dir / "budget_event_lake_admission_bundle_report.json",
        report.model_dump(mode="json"),
    )


def _calibration_readiness_report_path(tmp_path, *, ready=True):
    calibration_dir = tmp_path / "budget-calibration-readiness"
    source_dir = calibration_dir / "source-chain"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_refs = {}
    for name in [
        "budget_calibration_corpus_report",
        "budget_corpus_replay_plan",
        "budget_corpus_replay_execution_report",
        "budget_corpus_replay_review_packet",
        "budget_corpus_replay_review_outcome_report",
        "budget_fixture_binding_candidate_report",
        "budget_fixture_binding_handoff_report",
    ]:
        source_refs[name] = write_json(source_dir / f"{name}.json", {"synthetic": True})
    checks = [
        BudgetCalibrationReadinessCheck(
            check_id="synthetic_calibration_readiness_check",
            status="passed" if ready else "failed",
            message="Synthetic calibration readiness fixture.",
            artifact_refs=[str(path) for path in source_refs.values()],
        )
    ]
    report = BudgetCalibrationReadinessReport(
        budget_calibration_readiness_report_id="budget-calibration-readiness-fixture",
        status=(
            "ready_for_manual_fixture_update_review" if ready else "blocked_by_calibration_chain"
        ),
        corpus_report_id="corpus-report-readiness-fixture",
        replay_plan_id="replay-plan-readiness-fixture",
        replay_execution_report_id="replay-execution-readiness-fixture",
        review_packet_id="review-packet-readiness-fixture",
        review_outcome_report_id="review-outcome-readiness-fixture",
        fixture_binding_candidate_report_id="fixture-binding-candidate-readiness-fixture",
        fixture_binding_handoff_report_id="fixture-binding-handoff-readiness-fixture",
        replay_case_id="replay-case-readiness-fixture",
        source_corpus_report_ref=str(source_refs["budget_calibration_corpus_report"]),
        source_replay_plan_ref=str(source_refs["budget_corpus_replay_plan"]),
        source_replay_execution_report_ref=str(
            source_refs["budget_corpus_replay_execution_report"]
        ),
        source_review_packet_ref=str(source_refs["budget_corpus_replay_review_packet"]),
        source_review_outcome_report_ref=str(
            source_refs["budget_corpus_replay_review_outcome_report"]
        ),
        source_fixture_binding_candidate_report_ref=str(
            source_refs["budget_fixture_binding_candidate_report"]
        ),
        source_fixture_binding_handoff_report_ref=str(
            source_refs["budget_fixture_binding_handoff_report"]
        ),
        ready_fixture_binding_handoff_count=1 if ready else 0,
        blocked_fixture_binding_handoff_count=0 if ready else 1,
        approved_output_refs=[".lawfirm-os-intake/replay/budget_revision_report.json"]
        if ready
        else [],
        proposed_target_fixture_refs=[
            "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
        ]
        if ready
        else [],
        checks=checks,
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
    return write_json(
        calibration_dir / "budget_calibration_readiness_report.json",
        report.model_dump(mode="json"),
    )


def _fixture_update_review_record(readiness: BudgetCalibrationReadinessReport):
    return BudgetFixtureUpdateReviewRecord(
        fixture_update_review_id="fixture-update-review-readiness-fixture",
        budget_calibration_readiness_report_id=(readiness.budget_calibration_readiness_report_id),
        fixture_binding_handoff_report_id=readiness.fixture_binding_handoff_report_id,
        replay_case_id=readiness.replay_case_id,
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-26T00:00:00Z",
        decision="accept_for_separate_fixture_update_pr",
        decision_reason="Synthetic readiness-audit fixture update review.",
        accepted_output_refs=[".lawfirm-os-intake/replay/budget_revision_report.json"],
        target_fixture_refs=[
            "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
        ],
        required_followups=["Separate fixture-update PR remains required."],
        reviewed_red_team_notes=[
            "Fixture update review does not mutate fixtures or apply learning."
        ],
    )


def _fixture_update_review_report_path(
    tmp_path,
    calibration_readiness_report_path,
    *,
    ready=True,
):
    fixture_review_dir = tmp_path / "budget-fixture-update-review"
    readiness = BudgetCalibrationReadinessReport.model_validate(
        load_json(calibration_readiness_report_path)
    )
    review_record = _fixture_update_review_record(readiness)
    review_path = write_json(
        fixture_review_dir / "fixture_update_review.json",
        review_record.model_dump(mode="json"),
    )
    if ready and readiness.status == "ready_for_manual_fixture_update_review":
        _, run_dir = run_budget_fixture_update_review_record(
            calibration_readiness_report_path=calibration_readiness_report_path,
            review_path=review_path,
            out_dir=fixture_review_dir,
        )
        return run_dir / "budget_fixture_update_review_report.json"

    history_path = write_json(
        fixture_review_dir / "budget_fixture_update_review_history.jsonl",
        review_record.model_dump(mode="json"),
    )
    report = BudgetFixtureUpdateReviewReport(
        fixture_update_review_report_id="budget-fixture-update-review-blocked-fixture",
        status="blocked_by_fixture_update_review_evidence",
        source_budget_calibration_readiness_report_id=(
            readiness.budget_calibration_readiness_report_id
        ),
        source_budget_calibration_readiness_report_ref=str(calibration_readiness_report_path),
        source_budget_calibration_readiness_status=readiness.status,
        fixture_binding_handoff_report_id=readiness.fixture_binding_handoff_report_id,
        replay_case_id=readiness.replay_case_id,
        fixture_update_review_id=review_record.fixture_update_review_id,
        decision=review_record.decision,
        decision_reason=review_record.decision_reason,
        accepted_output_refs=review_record.accepted_output_refs,
        target_fixture_refs=review_record.target_fixture_refs,
        append_only_history_ref=str(history_path),
        checks=[
            BudgetFixtureUpdateReviewCheck(
                check_id="synthetic_fixture_update_review_blocker",
                status="failed",
                message="Synthetic blocked fixture-update review.",
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
        generated_at="2026-06-26T00:00:00Z",
    )
    return write_json(
        fixture_review_dir / "budget_fixture_update_review_report.json",
        report.model_dump(mode="json"),
    )


def _fixture_update_pr_package_report_path(
    tmp_path,
    fixture_update_review_report_path,
    *,
    ready=True,
):
    package_dir = tmp_path / "budget-fixture-update-pr-package"
    if ready:
        _, run_dir = run_budget_fixture_update_pr_package(
            fixture_update_review_report_path=fixture_update_review_report_path,
            out_dir=package_dir,
        )
        return run_dir / "budget_fixture_update_pr_package_report.json"

    review_report = BudgetFixtureUpdateReviewReport.model_validate(
        load_json(fixture_update_review_report_path)
    )
    report = BudgetFixtureUpdatePRPackageReport(
        fixture_update_pr_package_report_id="budget-fixture-update-pr-package-blocked-fixture",
        status="blocked_by_fixture_update_review",
        source_budget_fixture_update_review_report_id=(
            review_report.fixture_update_review_report_id
        ),
        source_budget_fixture_update_review_report_ref=str(fixture_update_review_report_path),
        source_budget_fixture_update_review_status=review_report.status,
        fixture_update_review_id=review_report.fixture_update_review_id,
        decision=review_report.decision,
        item_count=0,
        ready_item_count=0,
        blocked_item_count=0,
        accepted_output_refs=review_report.accepted_output_refs,
        target_fixture_refs=review_report.target_fixture_refs,
        package_items=[],
        checks=[
            BudgetFixtureUpdatePRPackageCheck(
                check_id="synthetic_fixture_update_pr_package_blocker",
                status="failed",
                message="Synthetic blocked fixture-update PR package.",
            )
        ],
        required_next_gates=[
            "manual_fixture_update_pr_review",
            "apply_fixture_update_only_in_separate_pr",
            "run_regression_after_fixture_update_pr",
            "reviewed_learning_gate_before_candidate_changes",
            "shadow_eval_before_learning",
            "owning_repo_review",
            "no_silent_profile_template_or_guideline_mutation",
        ],
        generated_at="2026-06-26T00:00:00Z",
    )
    return write_json(
        package_dir / "budget_fixture_update_pr_package_report.json",
        report.model_dump(mode="json"),
    )


def test_intake_vertical_readiness_audit_marks_pr_review_ready_but_not_promoted(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
    )

    report, run_dir = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness",
    )
    persisted = IntakeVerticalReadinessAuditReport.model_validate(
        load_json(run_dir / "intake_vertical_readiness_audit_report.json")
    )

    assert persisted.audit_report_id == report.audit_report_id
    assert persisted.status == "ready_for_pr_review_external_adoption_required"
    assert persisted.review_readiness == "ready_for_human_pr_review_not_auto_marked"
    assert persisted.source_budget_event_lake_bundle_report_ref == str(lake_bundle_report_path)
    assert persisted.source_budget_calibration_readiness_report_ref == str(
        calibration_readiness_report_path
    )
    assert persisted.source_budget_fixture_update_review_report_ref == str(
        fixture_update_review_report_path
    )
    assert persisted.source_budget_fixture_update_pr_package_report_ref == str(
        fixture_update_pr_package_report_path
    )
    assert persisted.implemented_slice_count == persisted.total_slice_count == 23
    assert persisted.missing_artifact_refs == []
    assert persisted.missing_command_refs == []
    assert all(
        slice_status.status == "implemented_local_candidate" for slice_status in report.slices
    )
    assert all(check.status == "passed" for check in persisted.artifact_checks)
    assert any(
        check.check_id == "budget_event_lake_bundle_ready_without_writes"
        and check.status == "passed"
        for check in persisted.artifact_checks
    )
    assert any(
        check.check_id == "budget_calibration_readiness_ready_without_writes"
        and check.status == "passed"
        for check in persisted.artifact_checks
    )
    assert any(
        check.check_id == "budget_fixture_update_review_recorded_without_writes"
        and check.status == "passed"
        for check in persisted.artifact_checks
    )
    assert any(
        check.check_id == "budget_fixture_update_pr_package_ready_without_writes"
        and check.status == "passed"
        for check in persisted.artifact_checks
    )
    assert {
        "LawFirm-os-semantic-substrate",
        "LawFirm-os-orchestrator",
        "LawFirm-os-exceptions-lake-runtime",
    }.issubset(set(persisted.external_adoption_target_repos))
    assert persisted.pr_marked_ready is False
    assert persisted.promotion_authorized is False
    assert persisted.proposed_changes_applied is False
    assert persisted.no_connector_implemented is True
    assert persisted.no_lake_admission_performed is True
    assert persisted.no_sibling_repo_writes is True
    assert persisted.no_canonical_mutation is True
    assert persisted.sqlite_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "intake_vertical_readiness_audit_report.md").read_text(encoding="utf-8")
    assert "External Adoption Still Required" in notes_text
    assert "does not mark a PR ready" in notes_text


def test_intake_vertical_readiness_audit_fails_closed_for_missing_local_surfaces(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=tmp_path / "empty-repo-root",
        out_dir=tmp_path / "intake-vertical-readiness-missing",
    )

    assert report.status == "incomplete_missing_local_artifacts"
    assert report.review_readiness == "not_ready_missing_local_artifacts"
    assert report.implemented_slice_count == 0
    assert report.missing_artifact_refs
    assert report.pr_marked_ready is False
    assert report.promotion_authorized is False


def test_intake_vertical_readiness_audit_blocks_failed_or_missing_learning_chain(
    tmp_path,
    repo_root,
):
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
    )
    owner_handoff_report_path = _owner_handoff_report_path(
        tmp_path,
        repo_root,
        include_fixture_results=False,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-blocked",
    )

    assert report.status == "blocked_missing_or_failed_learning_artifacts"
    assert report.review_readiness == "not_ready_learning_artifact_chain_blocked"
    assert report.implemented_slice_count == report.total_slice_count == 23
    assert any(
        check.check_id == "owner_handoff_ready_without_writes" and check.status == "failed"
        for check in report.artifact_checks
    )
    assert any(
        check.check_id == "shadow_eval_results_passed_without_writes" and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.external_writes_performed is False


def test_intake_vertical_readiness_audit_blocks_failed_lake_bundle(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path, ready=False)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-lake-blocked",
    )

    assert report.status == "blocked_missing_or_failed_lake_bundle"
    assert report.review_readiness == "not_ready_lake_bundle_blocked"
    assert any(
        check.check_id == "budget_event_lake_bundle_ready_without_writes"
        and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.no_lake_admission_performed is True
    assert report.sqlite_write_performed is False


def test_intake_vertical_readiness_audit_blocks_failed_calibration_readiness(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(
        tmp_path,
        ready=False,
    )
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
        ready=False,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
        ready=False,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-calibration-blocked",
    )

    assert report.status == "blocked_missing_or_failed_calibration_readiness"
    assert report.review_readiness == "not_ready_calibration_readiness_blocked"
    assert any(
        check.check_id == "budget_calibration_readiness_ready_without_writes"
        and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.external_writes_performed is False


def test_intake_vertical_readiness_audit_blocks_failed_fixture_update_review(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
        ready=False,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
        ready=False,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-fixture-review-blocked",
    )

    assert report.status == "blocked_missing_or_failed_fixture_update_review"
    assert report.review_readiness == "not_ready_fixture_update_review_blocked"
    assert any(
        check.check_id == "budget_fixture_update_review_recorded_without_writes"
        and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.external_writes_performed is False


def test_intake_vertical_readiness_audit_blocks_failed_fixture_update_pr_package(
    tmp_path,
    repo_root,
):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
        ready=False,
    )

    report, _ = run_intake_vertical_readiness_audit(
        owner_handoff_report_path=owner_handoff_report_path,
        budget_event_lake_bundle_report_path=lake_bundle_report_path,
        budget_calibration_readiness_report_path=calibration_readiness_report_path,
        budget_fixture_update_review_report_path=fixture_update_review_report_path,
        budget_fixture_update_pr_package_report_path=fixture_update_pr_package_report_path,
        repo_root=repo_root,
        out_dir=tmp_path / "intake-vertical-readiness-fixture-pr-package-blocked",
    )

    assert report.status == "blocked_missing_or_failed_fixture_update_pr_package"
    assert report.review_readiness == "not_ready_fixture_update_pr_package_blocked"
    assert any(
        check.check_id == "budget_fixture_update_pr_package_ready_without_writes"
        and check.status == "failed"
        for check in report.artifact_checks
    )
    assert report.pr_marked_ready is False
    assert report.external_writes_performed is False


def test_intake_vertical_readiness_audit_cli(tmp_path, repo_root, capsys):
    owner_handoff_report_path = _owner_handoff_report_path(tmp_path, repo_root)
    lake_bundle_report_path = _lake_bundle_report_path(tmp_path)
    calibration_readiness_report_path = _calibration_readiness_report_path(tmp_path)
    fixture_update_review_report_path = _fixture_update_review_report_path(
        tmp_path,
        calibration_readiness_report_path,
    )
    fixture_update_pr_package_report_path = _fixture_update_pr_package_report_path(
        tmp_path,
        fixture_update_review_report_path,
    )

    exit_code = main(
        [
            "audit-intake-vertical-readiness",
            "--owner-handoff-report",
            str(owner_handoff_report_path),
            "--budget-event-lake-bundle-report",
            str(lake_bundle_report_path),
            "--budget-calibration-readiness-report",
            str(calibration_readiness_report_path),
            "--budget-fixture-update-review-report",
            str(fixture_update_review_report_path),
            "--budget-fixture-update-pr-package-report",
            str(fixture_update_pr_package_report_path),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "intake-vertical-readiness-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_pr_review_external_adoption_required"' in captured.out
    assert '"review_readiness": "ready_for_human_pr_review_not_auto_marked"' in captured.out
    assert '"budget_event_lake_bundle_report_ref":' in captured.out
    assert '"budget_calibration_readiness_report_ref":' in captured.out
    assert '"budget_fixture_update_review_report_ref":' in captured.out
    assert '"budget_fixture_update_pr_package_report_ref":' in captured.out
    assert '"pr_marked_ready": false' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert (
        tmp_path / "intake-vertical-readiness-cli" / "intake_vertical_readiness_audit_report.json"
    ).is_file()
