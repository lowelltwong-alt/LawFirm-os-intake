"""LW0 — end-to-end deterministic synthetic case pipeline harness.

Composes intake -> route -> confirm (generator ground truth) -> budget ->
carrier projection -> case sizing -> firm-Excel export into one typed result,
reconciled fail-closed. Deterministic, candidate-only, synthetic-only. Dollars
are always deterministic from governed rates; the immutable work-plan total is
never overwritten by the separate reimbursement figure.
"""

import pytest

from lawfirm_os_intake.case_pipeline import run_synthetic_case_pipeline
from lawfirm_os_intake.models import (
    PipelineRouteStage,
    SettlementPostureInput,
    SyntheticCasePipelineResult,
    SyntheticCasePipelineSpec,
)


def _medmal_spec(**overrides) -> SyntheticCasePipelineSpec:
    base = dict(
        case_id="medmal-lw0",
        inbound_ref="examples/synthetic/inbound/carrier-assignment-medmal.json",
        confirmation_template_ref=(
            "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
        ),
        profile_ref="context/synthetic-profiles/insurance-defense.yaml",
        ground_truth_family="medical_malpractice_defense",
        case_type="medical_malpractice",
        base_work_plan_total_minor_units=1_200_000,
        sizing_drivers={
            "party_count": 2,
            "injury_severity": "surgical",
            "liability_clarity": "disputed",
            "exposure_band": "high",
            "venue": "state_default",
        },
        posture_input=SettlementPostureInput(
            exposure_minor_units=8_000_000,
            settlement_value_minor_units=1_500_000,
            settlement_value_after_defense_minor_units=1_800_000,
            win_probability_percent=50.0,
            defense_cost_settle_now_minor_units=150_000,
            defense_cost_defend_settle_minor_units=800_000,
            defense_cost_try_minor_units=2_500_000,
        ),
    )
    base.update(overrides)
    return SyntheticCasePipelineSpec(**base)


def _run(spec, tmp_path, repo_root):
    return run_synthetic_case_pipeline(
        spec,
        repo_root=repo_root,
        out_dir=tmp_path,
        generated_at="2026-07-23T00:00:00Z",
    )


def test_pipeline_completes_end_to_end(tmp_path, repo_root):
    result = _run(_medmal_spec(), tmp_path, repo_root)
    assert isinstance(result, SyntheticCasePipelineResult)
    assert result.status == "completed"
    assert result.blocking_reasons == []
    assert result.route.status == "routed"
    assert result.route.routed_family == "medical_malpractice_defense"
    assert result.route.matched_ground_truth is True
    assert result.budget.status == "priced"
    assert result.budget.projection_status == "projected"
    assert result.sizing.status == "sized"
    assert result.export.status == "exported"


def test_confirmation_is_generator_ground_truth_not_human_review(tmp_path, repo_root):
    # P8: the pipeline confirms from generator ground truth; it must never be
    # mistakable for human review, which remains the production authority.
    result = _run(_medmal_spec(), tmp_path, repo_root)
    assert result.confirm.confirmation_source == "generator_ground_truth"
    assert result.confirm.is_human_review is False
    assert result.confirm.matched_ground_truth is True


def test_dollars_are_deterministic_across_runs(tmp_path, repo_root):
    # P9: byte-stable reconciled result across repeated runs (content digest is
    # computed over the deterministic stage outputs, not run ids/timestamps).
    first = _run(_medmal_spec(), tmp_path / "a", repo_root)
    second = _run(_medmal_spec(), tmp_path / "b", repo_root)
    assert first.content_digest == second.content_digest
    assert first.pipeline_result_id == second.pipeline_result_id
    assert first.budget.work_plan_total_minor_units == second.budget.work_plan_total_minor_units


def test_export_total_reconciles_to_work_plan_total(tmp_path, repo_root):
    # P11: the firm-Excel export renders the deterministic work-plan dollars
    # unchanged; its total equals the budget work-plan total in exact minor units.
    result = _run(_medmal_spec(), tmp_path, repo_root)
    assert result.export.firm_excel_original_total_minor_units == (
        result.budget.work_plan_total_minor_units
    )


def test_reimbursement_is_separate_from_work_plan_total(tmp_path, repo_root):
    # The guideline-adjusted reimbursement is a SEPARATE figure and never
    # overwrites the immutable work-plan total (carrier caps make it distinct).
    result = _run(_medmal_spec(), tmp_path, repo_root)
    assert result.budget.guideline_adjusted_reimbursement_minor_units is not None
    assert result.budget.guideline_adjusted_reimbursement_minor_units != (
        result.budget.work_plan_total_minor_units
    )


def test_missing_band_blocks_sizing_fail_closed(tmp_path, repo_root):
    # P4/P6: a case type with no declared proportionality band is not evaluable —
    # a typed blocked_no_band, never a silent pass.
    result = _run(_medmal_spec(case_type="undeclared_case_type"), tmp_path, repo_root)
    assert result.sizing.status == "blocked_no_band"
    assert result.sizing.sized_work_plan_total_minor_units is None
    assert result.status == "blocked"
    assert "sizing:blocked_no_band" in result.blocking_reasons


def test_tampered_export_total_is_rejected(tmp_path, repo_root):
    # Fail-closed: a serialized result whose export total no longer equals the
    # work-plan total is rejected on revalidation.
    result = _run(_medmal_spec(), tmp_path, repo_root)
    dumped = result.model_dump()
    dumped["export"]["firm_excel_original_total_minor_units"] = (
        result.export.firm_excel_original_total_minor_units + 1
    )
    with pytest.raises(ValueError):
        SyntheticCasePipelineResult.model_validate(dumped)


def test_tampered_status_is_rejected(tmp_path, repo_root):
    result = _run(_medmal_spec(case_type="undeclared_case_type"), tmp_path, repo_root)
    dumped = result.model_dump()
    # Claim "completed" while a joint is blocked -> rejected.
    dumped["status"] = "completed"
    dumped["blocking_reasons"] = []
    with pytest.raises(ValueError):
        SyntheticCasePipelineResult.model_validate(dumped)


def test_route_stage_none_family_cannot_serialize_as_routed():
    # A None joint may never serialize as success.
    with pytest.raises(ValueError):
        PipelineRouteStage(
            status="routed",
            ground_truth_family="medical_malpractice_defense",
            routed_family=None,
            decision_reason="clear_winner",
            matched_ground_truth=False,
        )
