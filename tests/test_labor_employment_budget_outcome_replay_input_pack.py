from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_builder_binding import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_builder_binding_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_execution import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_execution,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_input_pack import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_input_pack_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_readiness import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_readiness_audit,
)
from lawfirm_os_intake.models import (
    LaborEmploymentBudgetOutcomeReplayInputPackManifest,
    LaborEmploymentBudgetOutcomeReplayInputPackReport,
)
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"
LEARNING_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json"
)
OUTCOME_SEED_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-seeds.json"
)
INPUT_PACK_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json"
)


def _qa_gate(repo_root):
    return repo_root / FIXTURE_ROOT / "demo-labor-employment-budget-qa-gate-report.json"


def _learning_manifest(repo_root):
    return repo_root / LEARNING_MANIFEST_REF


def _seed_manifest(repo_root):
    return repo_root / OUTCOME_SEED_MANIFEST_REF


def _input_pack_manifest(repo_root):
    return repo_root / INPUT_PACK_MANIFEST_REF


def _learning_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=_learning_manifest(repo_root),
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "le-budget-learning-fixtures",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME


def _readiness_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=_seed_manifest(repo_root),
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-readiness",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME


def _execution_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=_seed_manifest(repo_root),
        readiness_report_path=_readiness_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-execution",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME


def _builder_binding_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-builder-binding",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME


def test_labor_employment_budget_replay_input_pack_marks_ready_and_missing_inputs(
    repo_root,
    tmp_path,
):
    manifest = LaborEmploymentBudgetOutcomeReplayInputPackManifest.model_validate(
        load_json(_input_pack_manifest(repo_root))
    )
    report, run_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=_input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayInputPackReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME)
    )

    assert manifest.manifest_id == "labor-employment-budget-outcome-replay-input-pack.v0_1"
    assert persisted.input_pack_report_id == report.input_pack_report_id
    assert report.status == "labor_employment_budget_replay_input_pack_partially_ready_for_review"
    assert report.case_count == 8
    assert report.ready_case_count == 1
    assert report.partial_case_count == 7
    assert report.blocked_case_count == 0
    assert report.ready_input_count == 5
    assert report.missing_input_count > 0
    assert report.invalid_input_count == 0
    assert report.one_of_signal_missing_count > 0
    assert all(check.status == "passed" for check in report.checks)
    blocked_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-ada-fmla-adversarial.v0_1"
    )
    assert blocked_case.status == "ready"
    assert {
        item.required_input_artifact for item in blocked_case.items if item.input_status == "ready"
    } == {
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_budget_learning_fixtures.json",
        "labor_employment_budget_qa_gate_report.json",
    }
    assert any(
        item.required_input_artifact == "labor_employment_executable_coverage_report.json"
        and item.validation_model == "LaborEmploymentExecutableCoverageReport"
        for item in blocked_case.items
    )
    assert report.runtime_artifacts_created is False
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_outcome_replay_input_pack_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not run builders" in notes
    assert "Rust Transition Candidates" in notes


def test_labor_employment_budget_replay_input_pack_without_manifest_is_all_missing(
    repo_root,
    tmp_path,
):
    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-missing",
        generated_at="2026-07-04T00:00:00Z",
    )

    assert report.status == "labor_employment_budget_replay_input_pack_partially_ready_for_review"
    assert report.ready_input_count == 0
    assert report.missing_input_count == report.required_input_count
    assert report.invalid_input_count == 0
    assert report.ready_case_count == 0
    assert report.partial_case_count == 8
    assert report.blocked_case_count == 0
    assert all(check.status == "passed" for check in report.checks)


def test_labor_employment_budget_replay_input_pack_blocks_invalid_declared_ref(
    repo_root,
    tmp_path,
):
    bad_payload_path = write_json(tmp_path / "bad-qa-gate-report.json", {"schema_version": "0.1"})
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if entry["required_input_artifact"] == "labor_employment_budget_qa_gate_report.json":
            entry["input_ref"] = str(bad_payload_path)
    manifest_path = write_json(tmp_path / "bad-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-invalid",
        generated_at="2026-07-04T00:00:00Z",
    )
    failed_checks = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count == 1
    assert report.blocked_case_count == 1
    assert "declared_input_refs_are_schema_valid" in failed_checks
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_labor_employment_budget_replay_input_pack_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-budget-outcome-replay-input-pack",
            "--builder-binding-report",
            str(_builder_binding_report(repo_root, tmp_path)),
            "--input-pack-manifest",
            str(_input_pack_manifest(repo_root)),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-budget-outcome-replay-input-pack-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        '"status": "labor_employment_budget_replay_input_pack_partially_ready_for_review"'
        in captured.out
    )
    assert '"ready_case_count": 1' in captured.out
    assert '"ready_input_count": 5' in captured.out
    assert '"invalid_input_count": 0' in captured.out
    assert '"runtime_artifacts_created": false' in captured.out
    assert (
        tmp_path
        / "le-budget-outcome-replay-input-pack-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    ).is_file()
