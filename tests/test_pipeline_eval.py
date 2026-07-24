"""LW2 — batch capture + evaluation loop over the frozen synthetic corpus.

Deterministic, candidate-only, synthetic-only, no ML. Metrics are recomputed
fail-closed and stratified by difficulty (P1); a saturated stratum is flagged
non-informative. Budget plausibility uses a declared band policy loaded
fail-closed (P4). The capture ledger records every axis and single-axis deltas
type regressions for review (P5).
"""

import pytest

from lawfirm_os_intake.pipeline_eval import (
    build_pipeline_eval_report,
    capture_ledger_entry,
    compute_metric_delta,
    load_reference_class_bands,
    REFERENCE_CLASS_BANDS_REF,
)
from lawfirm_os_intake.models import (
    SyntheticEvalMetricDelta,
    SyntheticPipelineEvalReport,
)


def _report(repo_root):
    return build_pipeline_eval_report(repo_root=repo_root, generated_at="2026-07-23T00:00:00Z")


def test_eval_report_recomputes_fail_closed(repo_root):
    report = _report(repo_root)
    assert isinstance(report, SyntheticPipelineEvalReport)
    assert report.real_world_accuracy_claim is False
    assert report.calibration_claim is False
    assert report.metric_semantics == "recovers_generator_truth_on_synthetic"
    # Tampering an overall metric away from what the strata imply is rejected.
    dumped = report.model_dump()
    dumped["overall_abstention_recall"] = round(report.overall_abstention_recall + 0.1, 6)
    with pytest.raises(ValueError):
        SyntheticPipelineEvalReport.model_validate(dumped)


def test_metrics_are_stratified_and_saturation_flagged(repo_root):
    report = _report(repo_root)
    difficulties = {s.difficulty for s in report.routing_by_difficulty}
    assert {"clear", "moderate", "hard"} <= difficulties
    for stratum in report.routing_by_difficulty:
        expected = stratum.routing_accuracy == 1.0 and stratum.abstention_recall == 1.0
        assert stratum.saturated_non_informative == expected


def test_eval_is_not_tautological(repo_root):
    # P1: the router is not perfect on the corpus -- overall abstention recall is
    # strictly below 1.0 (hard cases defeat it), so the eval carries real signal.
    report = _report(repo_root)
    assert report.overall_abstention_recall < 1.0


def test_driver_effect_invariants_recover_generator_math(repo_root):
    report = _report(repo_root)
    ids = {inv.invariant_id for inv in report.driver_effect_invariants}
    assert {
        "more_parties_non_decreasing",
        "catastrophic_at_least_baseline",
        "disputed_at_least_baseline",
    } <= ids
    for inv in report.driver_effect_invariants:
        assert inv.passed
        assert inv.checked_pairs > 0


def test_budget_plausibility_is_evaluated_not_silent(repo_root):
    report = _report(repo_root)
    bp = report.budget_plausibility
    assert bp.evaluated_count > 0
    assert bp.within_band_count + bp.out_of_band_count == bp.evaluated_count
    # The declared corpus case types all have bands, so nothing is not_evaluable.
    assert bp.not_evaluable_count == 0
    assert 0.0 <= bp.plausibility_rate <= 1.0


def test_missing_band_is_not_evaluable_fail_closed(repo_root, tmp_path):
    # P4: a case type with no declared band is not_evaluable, never a silent pass.
    from lawfirm_os_intake.case_sizing import CASE_SIZING_POLICY_REF, load_case_sizing_policy
    from lawfirm_os_intake.pipeline_eval import _budget_plausibility
    from lawfirm_os_intake.synthetic_corpus_generator import load_corpus

    cases = load_corpus(repo_root)
    sizing_policy = load_case_sizing_policy(repo_root / CASE_SIZING_POLICY_REF)
    bands_policy = {"bands": {}}  # no declared bands at all
    result = _budget_plausibility(cases, sizing_policy, bands_policy)
    assert result.evaluated_count == 0
    assert result.not_evaluable_count == len(cases)


def test_reference_class_bands_reject_real_firm_data(repo_root, tmp_path):
    bad = tmp_path / "bands.yaml"
    bad.write_text(
        "data_origin: synthetic\ncandidate_only: true\ncontains_real_firm_data: true\n"
        "bands:\n  x: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_reference_class_bands(bad)


def test_reference_class_bands_load(repo_root):
    policy = load_reference_class_bands(repo_root / REFERENCE_CLASS_BANDS_REF)
    assert policy["bands"]


def test_capture_ledger_single_axis_delta_and_typed_regression(repo_root):
    report = _report(repo_root)
    base = capture_ledger_entry(report, code_ref="ref-a", generated_at="2026-07-23T00:00:00Z")
    # Single axis changed (code_ref) + a routing regression -> typed for review.
    regressed = base.model_copy(
        update={
            "entry_id": "e2",
            "code_ref": "ref-b",
            "overall_routing_accuracy": round(base.overall_routing_accuracy - 0.1, 6),
        }
    )
    delta = compute_metric_delta(base, regressed)
    assert delta.comparability == "comparable"
    assert delta.changed_axis == "code_ref"
    assert delta.status == "metric_regression_requires_review"
    assert "routing_accuracy" in delta.regression_flags


def test_capture_ledger_multi_axis_is_not_comparable(repo_root):
    report = _report(repo_root)
    base = capture_ledger_entry(report, code_ref="ref-a", generated_at="2026-07-23T00:00:00Z")
    # Two axes changed -> not comparable (P5), no metric deltas carried.
    other = base.model_copy(
        update={"entry_id": "e3", "code_ref": "ref-b", "eval_version": "pipeline-eval.v0_2"}
    )
    delta = compute_metric_delta(base, other)
    assert delta.comparability == "not_comparable"
    assert delta.status == "not_comparable"
    assert delta.routing_accuracy_delta is None


def test_metric_delta_regression_flags_must_match():
    # A delta claiming no regression while carrying a negative metric is rejected.
    with pytest.raises(ValueError):
        SyntheticEvalMetricDelta(
            from_entry_id="a",
            to_entry_id="b",
            changed_axis="code_ref",
            comparability="comparable",
            routing_accuracy_delta=-0.2,
            abstention_recall_delta=0.0,
            budget_plausibility_delta=0.0,
            regression_flags=[],
            status="unchanged",
        )
