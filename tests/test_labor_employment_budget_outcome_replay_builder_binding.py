import pytest

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
from lawfirm_os_intake.models import LaborEmploymentBudgetOutcomeReplayBuilderBindingReport
from lawfirm_os_intake.util import digest_json, load_json, write_json


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


def test_labor_employment_budget_outcome_replay_builder_binding_binds_all_slots(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-builder-binding",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayBuilderBindingReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME)
    )

    assert persisted.builder_binding_report_id == report.builder_binding_report_id
    assert report.status == "labor_employment_budget_replay_builder_binding_ready_for_review"
    assert report.case_count == 8
    assert report.slot_count == 36
    assert report.bound_slot_count == 36
    assert report.unknown_artifact_count == 0
    assert report.blocked_slot_count == 0
    assert report.replay_input_gap_count > 0
    assert report.missing_case_prerequisite_count > 0
    assert all(case.status == "passed" for case in report.cases)
    assert all(check.status == "passed" for check in report.checks)
    assert any(
        binding.expected_artifact_name == "budget_learning_loop_report.json"
        and "carrier_rejection_review_packet.json" in binding.missing_case_prerequisite_artifacts
        for case in report.cases
        for binding in case.bindings
    )
    assert not any(
        case.replay_scope == "scoped_partial"
        and binding.expected_artifact_name == "budget_learning_loop_report.json"
        for case in report.cases
        for binding in case.bindings
    )
    assert any(
        "needs_synthetic_budget_actuals_source" in binding.replay_input_gap_ids
        for case in report.cases
        for binding in case.bindings
    )
    assert "labor_employment_budget_replay_builder_binding_candidate" in (
        report.candidate_exception_lake_labels
    )
    assert report.runtime_artifacts_created is False
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (
        run_dir / "labor_employment_budget_outcome_replay_builder_binding_report.md"
    ).read_text(encoding="utf-8")
    assert "does not run replay builders" in notes
    assert "Missing case prerequisites" in notes


def test_labor_employment_budget_outcome_replay_builder_binding_blocks_unknown_artifact(
    repo_root,
    tmp_path,
):
    execution = load_json(_execution_report(repo_root, tmp_path))
    execution["cases"][0]["artifact_slots"][0]["expected_artifact_name"] = (
        "unknown_future_runtime_report.json"
    )
    execution_path = write_json(tmp_path / "unknown-execution-report.json", execution)

    report, _ = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=execution_path,
        out_dir=tmp_path / "blocked-builder-binding",
        generated_at="2026-07-04T00:00:00Z",
    )
    failed_checks = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_replay_builder_binding"
    assert report.unknown_artifact_count == 1
    assert "all_slots_bound_to_known_builders" in failed_checks
    assert report.runtime_artifacts_created is False
    assert report.silent_learning_performed is False


def test_builder_binding_reconciles_only_schema_validated_input_pack_entries(
    repo_root,
    tmp_path,
):
    baseline, baseline_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "baseline-builder-binding",
        generated_at="2026-07-15T00:00:00Z",
    )
    input_pack, input_pack_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=(
            baseline_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
        ),
        input_pack_manifest_path=_input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "input-pack",
        generated_at="2026-07-15T00:00:00Z",
    )
    reconciled, _ = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        input_pack_report_path=(
            input_pack_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
        ),
        out_dir=tmp_path / "reconciled-builder-binding",
        generated_at="2026-07-15T00:00:00Z",
    )

    assert input_pack.source_builder_binding_report_id == baseline.builder_binding_report_id
    assert reconciled.builder_binding_report_id == baseline.builder_binding_report_id
    assert reconciled.source_input_pack_report_id == input_pack.input_pack_report_id
    assert reconciled.replay_input_gap_count < baseline.replay_input_gap_count
    assert reconciled.missing_case_prerequisite_count <= baseline.missing_case_prerequisite_count
    assert reconciled.replay_input_gap_count > 0
    assert reconciled.runtime_artifacts_created is False
    assert reconciled.external_writes_performed is False


def test_builder_binding_rejects_input_pack_from_another_binding_run(repo_root, tmp_path):
    baseline, baseline_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "baseline-builder-binding",
        generated_at="2026-07-15T00:00:00Z",
    )
    _, input_pack_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=(
            baseline_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
        ),
        input_pack_manifest_path=_input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "input-pack",
        generated_at="2026-07-15T00:00:00Z",
    )
    input_pack_path = (
        input_pack_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    )
    stale = load_json(input_pack_path)
    stale["source_builder_binding_report_id"] = "lebudgetreplaybinding_stale"
    stale_path = write_json(tmp_path / "stale-input-pack.json", stale)

    with pytest.raises(ValueError, match="does not belong to the current builder binding"):
        run_labor_employment_budget_outcome_replay_builder_binding_audit(
            execution_report_path=_execution_report(repo_root, tmp_path),
            input_pack_report_path=stale_path,
            out_dir=tmp_path / "stale-reconciled-builder-binding",
            repo_root=repo_root,
            generated_at="2026-07-15T00:00:00Z",
        )


def test_builder_binding_reconciliation_rejects_alternate_executable_manifest(
    repo_root,
    tmp_path,
):
    baseline, baseline_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "baseline-builder-binding",
        repo_root=repo_root,
        generated_at="2026-07-15T00:00:00Z",
    )
    _, input_pack_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=(
            baseline_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
        ),
        input_pack_manifest_path=_input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "input-pack",
        generated_at="2026-07-15T00:00:00Z",
    )
    input_pack_path = (
        input_pack_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    )
    alternate_executable_manifest = load_json(
        repo_root / "examples/synthetic/labor-employment/"
        "labor-employment-executable-fixtures-manifest.json"
    )
    alternate_executable_manifest["manifest_id"] = "alternate-executable-manifest.v0_1"
    alternate_executable_path = write_json(
        tmp_path / "alternate-executable-manifest.json",
        alternate_executable_manifest,
    )
    alternate_input_manifest = load_json(_input_pack_manifest(repo_root))
    alternate_input_manifest["executable_fixture_manifest_ref"] = str(alternate_executable_path)
    alternate_input_manifest_path = write_json(
        tmp_path / "alternate-input-pack-manifest.json",
        alternate_input_manifest,
    )
    crafted = load_json(input_pack_path)
    crafted["source_input_pack_manifest_ref"] = str(alternate_input_manifest_path)
    crafted["source_executable_fixture_manifest_ref"] = str(alternate_executable_path)
    crafted["source_executable_fixture_manifest_id"] = alternate_executable_manifest["manifest_id"]
    crafted["source_executable_fixture_manifest_sha256"] = digest_json(
        alternate_executable_manifest
    )
    crafted_path = write_json(tmp_path / "crafted-input-pack-report.json", crafted)

    with pytest.raises(
        ValueError,
        match="does not match builder binding provenance",
    ):
        run_labor_employment_budget_outcome_replay_builder_binding_audit(
            execution_report_path=_execution_report(repo_root, tmp_path),
            input_pack_report_path=crafted_path,
            out_dir=tmp_path / "crafted-reconciled-builder-binding",
            repo_root=repo_root,
            generated_at="2026-07-15T00:00:00Z",
        )


def test_labor_employment_budget_outcome_replay_builder_binding_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-budget-outcome-replay-builder-binding",
            "--execution-report",
            str(_execution_report(repo_root, tmp_path)),
            "--out-dir",
            str(tmp_path / "le-budget-outcome-replay-builder-binding-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "labor_employment_budget_replay_builder_binding_ready_for_review"' in (
        captured.out
    )
    assert '"slot_count": 36' in captured.out
    assert '"bound_slot_count": 36' in captured.out
    assert '"unknown_artifact_count": 0' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path
        / "le-budget-outcome-replay-builder-binding-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
    ).is_file()
