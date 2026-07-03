from scripts import run_validation_suite

from lawfirm_os_intake.models import ValidationSuiteEvidenceReport, ValidationSuiteStepEvidence


def _step(step_id: str, *, status: str = "passed", return_code: int = 0):
    return ValidationSuiteStepEvidence(
        step_id=step_id,
        command_key=step_id if step_id != "validate_repo_final" else "validate_repo",
        command=["python", "synthetic-command.py"],
        command_display="python synthetic-command.py",
        status=status,
        return_code=return_code,
        timeout_seconds=3600 if step_id in {"full_pytest", "smoke_demo"} else 180,
        duration_seconds=1.25,
        started_at="2026-07-03T00:00:00Z",
        completed_at="2026-07-03T00:00:01Z",
        evidence_refs=[f"synthetic/{step_id}.txt"],
    )


def _all_passed_steps():
    return [
        _step("validate_repo"),
        _step("export_schemas"),
        _step("ruff_check"),
        _step("ruff_format_check"),
        _step("full_pytest"),
        _step("smoke_demo"),
        _step("validate_repo_final"),
    ]


def test_validation_suite_evidence_report_records_passing_wrapper_run():
    report = run_validation_suite.build_validation_suite_evidence_report(
        steps=_all_passed_steps(),
        generated_at="2026-07-03T00:00:00Z",
        git_commit="abc123",
        working_tree_dirty=False,
    )
    persisted = ValidationSuiteEvidenceReport.model_validate(report.model_dump(mode="json"))

    assert persisted.status == "validation_suite_passed"
    assert persisted.step_count == 7
    assert persisted.passed_step_count == 7
    assert persisted.failed_step_count == 0
    assert persisted.timed_out_step_count == 0
    assert persisted.policy_id == "intake-validation-runtime-policy"
    assert persisted.policy_ref == "config/validation-runtime-policy.yaml"
    assert persisted.budget_submission_authorized is False
    assert persisted.matter_opening_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False


def test_validation_suite_evidence_report_blocks_failed_step():
    steps = _all_passed_steps()
    steps[4] = _step("full_pytest", status="failed", return_code=1)

    report = run_validation_suite.build_validation_suite_evidence_report(
        steps=steps,
        generated_at="2026-07-03T00:00:00Z",
        git_commit="abc123",
        working_tree_dirty=True,
    )

    assert report.status == "blocked_by_validation_suite"
    assert report.failed_step_count == 1
    assert report.timed_out_step_count == 0
    assert "Fix failed or timed-out validation steps" in report.required_next_actions[0]
