"""DT3 — canonical pricing surfaced in the case pipeline (side-by-side).

The pipeline gains an INFORMATIONAL canonical-pricing stage: the DT2 engine's
priced plan rides alongside the legacy sized work plan so reviewers see both.
Legacy sizing remains authoritative; the canonical stage can never block the
chain. Candidate-only, synthetic-only, deterministic; fail-closed reconciliation
between the stage's copied legacy total and the sizing stage.
"""

import pytest

from lawfirm_os_intake.case_pipeline import run_synthetic_case_pipeline
from lawfirm_os_intake.models import (
    CanonicalPricedWorkPlan,
    SettlementPostureInput,
    SyntheticCasePipelineResult,
    SyntheticCasePipelineSpec,
)
from lawfirm_os_intake.util import load_json


def _medmal_spec() -> SyntheticCasePipelineSpec:
    return SyntheticCasePipelineSpec(
        case_id="dt3-medmal",
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


def _run(repo_root, tmp_path, case_id="dt3-medmal"):
    spec = _medmal_spec().model_copy(update={"case_id": case_id})
    return run_synthetic_case_pipeline(
        spec, repo_root=repo_root, out_dir=tmp_path / case_id, generated_at="2026-07-23T00:00:00Z"
    )


def test_pipeline_carries_canonical_stage(repo_root, tmp_path):
    result = _run(repo_root, tmp_path)
    stage = result.canonical
    assert stage is not None
    assert stage.status == "priced_candidate"
    assert stage.plan_id and stage.profile_id and stage.contract_digest
    assert stage.canonical_total_minor_units > 0
    assert stage.authoritative is False
    assert stage.candidate_only is True


def test_canonical_stage_reconciles_with_legacy_sizing(repo_root, tmp_path):
    result = _run(repo_root, tmp_path)
    assert result.sizing.status == "sized"
    assert (
        result.canonical.legacy_sized_total_minor_units
        == result.sizing.sized_work_plan_total_minor_units
    )


def test_canonical_stage_never_blocks(repo_root, tmp_path):
    result = _run(repo_root, tmp_path)
    assert result.status == "completed"
    assert not any("canonical" in reason for reason in result.blocking_reasons)


def test_canonical_plan_artifact_written_and_revalidates(repo_root, tmp_path):
    result = _run(repo_root, tmp_path)
    artifact = tmp_path / "dt3-medmal" / "canonical" / "canonical_priced_work_plan.json"
    assert artifact.exists()
    plan = CanonicalPricedWorkPlan.model_validate(load_json(artifact))
    assert plan.plan_id == result.canonical.plan_id
    assert plan.total_dollars_minor_units == result.canonical.canonical_total_minor_units


def test_unmapped_line_prices_as_typed_not_priced(repo_root, tmp_path):
    spec = _medmal_spec().model_copy(
        update={
            "case_id": "dt3-premises",
            "case_type": "premises_liability",
        }
    )
    result = run_synthetic_case_pipeline(
        spec,
        repo_root=repo_root,
        out_dir=tmp_path / "premises",
        generated_at="2026-07-23T00:00:00Z",
    )
    assert result.canonical.status == "not_priced"
    assert "premises_liability" in result.canonical.reason
    # Still informational: the not_priced canonical stage does not block.
    assert not any("canonical" in reason for reason in result.blocking_reasons)


def test_tampered_side_by_side_total_rejected(repo_root, tmp_path):
    result = _run(repo_root, tmp_path)
    dumped = result.model_dump()
    dumped["canonical"]["legacy_sized_total_minor_units"] += 1
    with pytest.raises(ValueError):
        SyntheticCasePipelineResult.model_validate(dumped)


def test_pipeline_stays_deterministic(repo_root, tmp_path):
    first = _run(repo_root, tmp_path, case_id="dt3-det-a")
    second = _run(repo_root, tmp_path, case_id="dt3-det-b")
    assert (
        first.canonical.canonical_total_minor_units == second.canonical.canonical_total_minor_units
    )
    assert first.canonical.plan_id == second.canonical.plan_id
