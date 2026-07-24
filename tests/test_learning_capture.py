"""LW4 — improvement capture + hardening + delivery (END OF PROGRAM).

Candidate-only, synthetic-only, deterministic. Monotonic-improvement tracking
types regressions for review (P5); the hostile sweep proves every new artifact
fails closed on tamper; the delivery packet enumerates capabilities, boundaries,
the firm-data recalibration lane, the composition seam (P7), and the deferred
full-XGBoost note.
"""

import pytest

from lawfirm_os_intake.learning_capture import (
    HOSTILE_SWEEP_ARTIFACT_IDS,
    build_delivery_packet,
    build_learning_capture_report,
    run_hostile_fixture_sweep,
)
from lawfirm_os_intake.models import (
    LearningCaptureReport,
    LearningLoopDeliveryPacket,
    LearningLoopHostileSweepReport,
)
from lawfirm_os_intake.pipeline_eval import build_pipeline_eval_report, capture_ledger_entry


def _entries(repo_root):
    report = build_pipeline_eval_report(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    first = capture_ledger_entry(report, code_ref="rev-a", generated_at="2026-07-23T00:00:00Z")
    # Second generator revision: single axis (generator_version) changed, plus a
    # small plausibility improvement.
    second = first.model_copy(
        update={
            "entry_id": "rev2",
            "generator_version": "synthetic-corpus-generator.v0_2",
            "budget_plausibility_rate": min(1.0, first.budget_plausibility_rate + 0.02),
        }
    )
    return first, second


def test_capture_tracks_metric_delta_across_two_generator_revisions(repo_root):
    first, second = _entries(repo_root)
    report = build_learning_capture_report([first, second])
    assert isinstance(report, LearningCaptureReport)
    assert report.entry_count == 2
    assert report.comparable_delta_count == 1
    assert report.improvement_count == 1
    assert report.regression_count == 0
    assert report.monotonic_improvement is True


def test_capture_types_regression_for_review_not_auto_block(repo_root):
    first, _ = _entries(repo_root)
    regressed = first.model_copy(
        update={
            "entry_id": "rev-regressed",
            "generator_version": "synthetic-corpus-generator.v0_3",
            "overall_routing_accuracy": round(first.overall_routing_accuracy - 0.1, 6),
        }
    )
    report = build_learning_capture_report([first, regressed])
    assert report.regression_count == 1
    assert report.monotonic_improvement is False
    assert report.regressions_requiring_review == [f"{first.entry_id}->rev-regressed"]


def test_capture_multi_axis_delta_is_not_comparable(repo_root):
    first, _ = _entries(repo_root)
    multi = first.model_copy(
        update={
            "entry_id": "rev-multi",
            "generator_version": "synthetic-corpus-generator.v0_4",
            "eval_version": "pipeline-eval.v0_2",
        }
    )
    report = build_learning_capture_report([first, multi])
    assert report.not_comparable_delta_count == 1
    assert report.comparable_delta_count == 0


def test_capture_report_recomputed_fail_closed(repo_root):
    first, second = _entries(repo_root)
    report = build_learning_capture_report([first, second])
    dumped = report.model_dump()
    dumped["monotonic_improvement"] = not report.monotonic_improvement
    with pytest.raises(ValueError):
        LearningCaptureReport.model_validate(dumped)


def test_hostile_sweep_every_new_artifact_fails_closed(repo_root):
    report = run_hostile_fixture_sweep(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")
    assert isinstance(report, LearningLoopHostileSweepReport)
    assert report.all_rejected is True
    swept = {a.artifact_id for a in report.artifacts}
    assert set(HOSTILE_SWEEP_ARTIFACT_IDS) == swept
    for artifact in report.artifacts:
        assert artifact.rejected_on_tamper is True


def test_hostile_sweep_report_rejects_a_survivor():
    from lawfirm_os_intake.models import HostileSweepArtifactResult

    # An artifact that did NOT fail closed cannot be recorded.
    with pytest.raises(ValueError):
        HostileSweepArtifactResult(artifact_id="x", tampered_field="y", rejected_on_tamper=False)


def test_delivery_packet_is_complete_and_fail_closed():
    packet = build_delivery_packet(generated_at="2026-07-23T00:00:00Z")
    assert isinstance(packet, LearningLoopDeliveryPacket)
    assert packet.waves_delivered == ["LW0", "LW1", "LW2", "LW3", "LW4"]
    assert packet.capabilities and packet.boundaries
    assert packet.firm_data_recalibration_lane
    assert packet.deferred_full_xgboost_note
    assert packet.composition_seam_note
    assert packet.ml_status == "shadow_only_no_promotion"
    assert packet.dollars_status == "deterministic_from_governed_rates"
    # Dropping the recalibration lane fails closed.
    dumped = packet.model_dump()
    dumped["firm_data_recalibration_lane"] = []
    with pytest.raises(ValueError):
        LearningLoopDeliveryPacket.model_validate(dumped)


def test_delivery_packet_records_deferred_xgboost_and_seam():
    packet = build_delivery_packet(generated_at="2026-07-23T00:00:00Z")
    assert "XGBoost" in packet.deferred_full_xgboost_note
    assert "LW5" in packet.deferred_full_xgboost_note
    assert "case_pipeline" in packet.composition_seam_note
    assert "firm_checkpoint" in packet.composition_seam_note
