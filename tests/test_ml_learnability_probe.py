"""LW3 — ML shadow challenger (lightweight learnability probe).

Dependency-light, deterministic, candidate-only, synthetic-only. Features come
only from the rendered bundle (FeatureContract, P2); learnability requires the
probe to beat a majority-class baseline AND survive a label-shuffle permutation
and feature ablation. All labels are reference_class_only; the probe predicts
routing/drivers only, never dollars; it is SHADOW-ONLY through the
reviewed_learning_gate (no promotion). The privacy leakage proof
(calibration/leakage.py) is distinct from the label-leakage controls (P3).
"""

import pytest

from lawfirm_os_intake.ml_learnability_probe import (
    MIN_HOLDOUT_COUNT,
    build_ml_learnability_probe_report,
)
from lawfirm_os_intake.models import (
    ML_PROBE_LABEL_FIELDS,
    MLLearnabilityProbeReport,
    MLLearnabilityTargetResult,
    MLProbeFeatureContract,
)


def _report(repo_root):
    return build_ml_learnability_probe_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )


def _target(report, name):
    return next(t for t in report.targets if t.target == name)


def test_route_family_is_learnable_with_controls(repo_root):
    report = _report(repo_root)
    route = _target(report, "route_family")
    assert route.learnable is True
    # Probe beats the majority-class baseline by the margin.
    assert route.learnability_margin >= route.min_margin
    # Label-shuffle collapses to ~baseline (no label leakage into features).
    assert route.shuffle_accuracy <= route.baseline_accuracy + route.shuffle_tolerance
    # Feature ablation degrades the probe.
    assert route.ablation_accuracy < route.probe_accuracy


def test_driver_target_is_honestly_not_learnable(repo_root):
    # injury_severity is not encoded in the bundle text (randomly sampled), so the
    # probe cannot recover it -- an honest negative that proves the eval is not
    # rigged.
    report = _report(repo_root)
    injury = _target(report, "injury_severity")
    assert injury.learnable is False


def test_probe_is_shadow_only_gate_blocks_promotion(repo_root):
    report = _report(repo_root)
    assert report.reviewed_learning_gate_blocks_promotion is True
    assert report.promotion_authorized is False
    assert report.shadow_only is True
    # A report claiming the gate did NOT block promotion is rejected (fail closed).
    dumped = report.model_dump()
    dumped["reviewed_learning_gate_blocks_promotion"] = False
    with pytest.raises(ValueError):
        MLLearnabilityProbeReport.model_validate(dumped)


def test_labels_are_reference_class_only_never_calibrated(repo_root):
    report = _report(repo_root)
    assert report.label_class == "reference_class_only"
    assert report.learnability_only is True
    assert report.calibrated is False
    assert report.real_world_accuracy_claim is False
    assert report.predicts_dollars is False
    assert report.dollars_remain_deterministic is True


def test_feature_contract_prohibits_all_label_fields(repo_root):
    report = _report(repo_root)
    assert report.feature_contract.features_source == "rendered_bundle_terms_only"
    assert set(ML_PROBE_LABEL_FIELDS) <= set(report.feature_contract.prohibited_feature_fields)
    # Dropping a prohibited label field is rejected (leakage guard).
    with pytest.raises(ValueError):
        MLProbeFeatureContract(
            vocabulary_size=10,
            prohibited_feature_fields=[
                f for f in ML_PROBE_LABEL_FIELDS if f != "ground_truth_family"
            ],
        )


def test_privacy_proof_is_distinct_from_label_leakage_controls(repo_root):
    # P3: the calibration/leakage.py privacy proof and the feature/label-leakage
    # controls are distinct; both are present and neither substitutes for the other.
    report = _report(repo_root)
    assert report.privacy_leakage_proof_id
    assert report.privacy_leakage_proof_is_privacy_not_label_leakage is True
    # The label-leakage evidence lives in the per-target shuffle/ablation controls.
    for target in report.targets:
        assert target.shuffle_accuracy is not None
        assert target.ablation_accuracy is not None


def test_probe_is_deterministic(repo_root):
    first = _report(repo_root)
    second = _report(repo_root)
    assert first.content_digest == second.content_digest
    assert first.probe_id == second.probe_id


def test_holdout_floor_is_enforced(repo_root):
    report = _report(repo_root)
    assert report.holdout_count >= MIN_HOLDOUT_COUNT
    dumped = report.model_dump()
    dumped["holdout_count"] = MIN_HOLDOUT_COUNT - 1
    for target in dumped["targets"]:
        target["holdout_count"] = MIN_HOLDOUT_COUNT - 1
    with pytest.raises(ValueError):
        MLLearnabilityProbeReport.model_validate(dumped)


def test_learnable_flag_recomputed_fail_closed():
    # A target claiming learnable while the shuffle control did not collapse is
    # rejected.
    with pytest.raises(ValueError):
        MLLearnabilityTargetResult(
            target="route_family",
            holdout_count=15,
            probe_accuracy=0.8,
            baseline_accuracy=0.1,
            shuffle_accuracy=0.75,  # did NOT collapse -> not learnable
            ablation_accuracy=0.3,
            learnability_margin=0.7,
            min_margin=0.1,
            shuffle_tolerance=0.1,
            learnable=True,
        )
