import pytest

from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_builder_binding import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_builder_binding_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_confidence_status import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_confidence_status,
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
    LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport,
    LaborEmploymentBudgetOutcomeReplayInputPackReport,
)
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
        generated_at="2026-07-05T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME


def _readiness_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=_seed_manifest(repo_root),
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-readiness",
        generated_at="2026-07-05T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME


def _execution_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=_seed_manifest(repo_root),
        readiness_report_path=_readiness_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-execution",
        generated_at="2026-07-05T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME


def _reconciled_reports(repo_root, tmp_path, manifest_path=None):
    execution_path = _execution_report(repo_root, tmp_path)
    baseline, baseline_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=execution_path,
        out_dir=tmp_path / "confidence-baseline-builder-binding",
        generated_at="2026-07-05T00:00:00Z",
    )
    _, input_pack_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=(
            baseline_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
        ),
        input_pack_manifest_path=manifest_path or _input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "confidence-input-pack",
        generated_at="2026-07-05T00:00:00Z",
    )
    input_pack_path = (
        input_pack_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    )
    _, binding_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=execution_path,
        input_pack_report_path=input_pack_path,
        repo_root=repo_root,
        out_dir=tmp_path / "confidence-reconciled-builder-binding",
        generated_at="2026-07-05T00:00:00Z",
    )
    assert baseline.builder_binding_report_id
    return (
        binding_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
        input_pack_path,
    )


def test_labor_employment_budget_outcome_replay_confidence_status_is_pending_inputs(
    repo_root,
    tmp_path,
):
    readiness_path = _readiness_report(repo_root, tmp_path)
    execution_path = _execution_report(repo_root, tmp_path)
    binding_path, input_pack_path = _reconciled_reports(repo_root, tmp_path)

    report, run_dir = run_labor_employment_budget_outcome_replay_confidence_status(
        readiness_report_path=readiness_path,
        execution_report_path=execution_path,
        builder_binding_report_path=binding_path,
        input_pack_report_path=input_pack_path,
        out_dir=tmp_path / "le-budget-outcome-replay-confidence-status",
        generated_at="2026-07-05T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayConfidenceStatusReport.model_validate(
        load_json(
            run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME
        )
    )
    stages = {stage.stage_id: stage for stage in persisted.stages}

    assert persisted.replay_confidence_status_report_id == report.replay_confidence_status_report_id
    assert report.status == "labor_employment_budget_outcome_replay_confidence_pending_inputs"
    assert report.stage_count == 4
    assert report.ready_stage_count == 2
    assert report.pending_stage_count == 2
    assert report.blocked_stage_count == 0
    assert stages["readiness"].status == "ready"
    assert stages["execution"].status == "ready"
    assert stages["builder_binding"].status == "pending_inputs"
    assert stages["input_pack"].status == "pending_inputs"
    assert report.builder_replay_input_gap_count == 51
    assert report.builder_missing_case_prerequisite_count > 0
    assert report.input_pack_missing_input_count > 0
    assert report.source_input_pack_report_sha256 == digest_json(load_json(input_pack_path))
    source_input_pack = LaborEmploymentBudgetOutcomeReplayInputPackReport.model_validate(
        load_json(input_pack_path)
    )
    assert (
        report.source_input_pack_manifest_sha256
        == source_input_pack.source_input_pack_manifest_sha256
    )
    assert "calibration" in report.display_banner["blocked_actions"]
    assert "deterministic_replay_confidence_status_aggregator" in (
        report.rust_transition_candidates
    )
    assert report.candidate_only is True
    assert report.synthetic_only is True
    assert report.local_json_only is True
    assert report.budget_submission_authorized is False
    assert report.matter_opening_authorized is False
    assert report.training_pipeline_created is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert (
        run_dir / "labor_employment_budget_outcome_replay_confidence_status_report.md"
    ).is_file()


def test_labor_employment_budget_outcome_replay_confidence_status_rejects_mixed_input_pack(
    repo_root,
    tmp_path,
):
    binding_path, input_pack_path = _reconciled_reports(repo_root, tmp_path)
    stale_binding = load_json(binding_path)
    stale_binding["source_input_pack_report_sha256"] = "sha256:" + ("0" * 64)
    stale_binding_path = write_json(tmp_path / "stale-binding.json", stale_binding)

    with pytest.raises(ValueError, match="report hash does not match builder binding"):
        run_labor_employment_budget_outcome_replay_confidence_status(
            readiness_report_path=_readiness_report(repo_root, tmp_path),
            execution_report_path=_execution_report(repo_root, tmp_path),
            builder_binding_report_path=stale_binding_path,
            input_pack_report_path=input_pack_path,
            out_dir=tmp_path / "stale-confidence-status",
            generated_at="2026-07-05T00:00:00Z",
        )


def test_labor_employment_budget_outcome_replay_confidence_status_blocks_invalid_input_pack(
    repo_root,
    tmp_path,
):
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if (
            entry["learning_fixture_id"] == "le-learning-wage-hour-clean.v0_1"
            and entry["loop_type"] == "actuals_variance"
            and entry["required_input_artifact"] == "budget_actuals_source.json"
        ):
            entry["input_ref"] = (
                "examples/synthetic/labor-employment/replay-inputs/"
                "discrimination-harassment-clean/budget_actuals_source.json"
            )
    manifest_path = write_json(tmp_path / "bad-input-pack-manifest.json", manifest)

    binding_path, input_pack_path = _reconciled_reports(repo_root, tmp_path, manifest_path)
    report, _ = run_labor_employment_budget_outcome_replay_confidence_status(
        readiness_report_path=_readiness_report(repo_root, tmp_path),
        execution_report_path=_execution_report(repo_root, tmp_path),
        builder_binding_report_path=binding_path,
        input_pack_report_path=input_pack_path,
        out_dir=tmp_path / "le-budget-outcome-replay-confidence-status-blocked",
        generated_at="2026-07-05T00:00:00Z",
    )
    input_pack_stage = next(stage for stage in report.stages if stage.stage_id == "input_pack")

    assert report.status == "blocked_by_labor_employment_budget_outcome_replay_confidence"
    assert report.blocked_stage_count == 1
    assert input_pack_stage.status == "blocked"
    assert report.input_pack_invalid_input_count >= 1
    assert any("invalid replay inputs" in blocker for blocker in report.top_blockers)
