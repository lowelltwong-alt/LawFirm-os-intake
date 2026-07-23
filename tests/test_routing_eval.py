"""CW4 — deterministic router evaluation (accuracy + abstention + injection inertness)."""

from lawfirm_os_intake.models import RouterEvalCaseSpec, RouterEvaluationReport
from lawfirm_os_intake.routing_eval import (
    build_router_evaluation_report,
    build_synthetic_intake_case,
    evaluate_router,
    load_router_eval_specs,
    route_decision,
)
from lawfirm_os_intake.workers import classify_matter
from lawfirm_os_intake.routing_eval import _synthetic_context


def _classify(spec: RouterEvalCaseSpec):
    case = build_synthetic_intake_case(spec)
    _inbound, matter, _posture = classify_matter(case.bundle, case.segments, _synthetic_context())
    return route_decision(matter)


def test_fixture_factory_is_deterministic():
    spec = RouterEvalCaseSpec(
        case_id="c",
        ground_truth_family="general_liability_defense",
        variant="clean",
        expected_decision="route",
    )
    first = build_synthetic_intake_case(spec)
    second = build_synthetic_intake_case(spec)
    assert first.bundle.model_dump() == second.bundle.model_dump()
    assert [s.sha256 for s in first.segments] == [s.sha256 for s in second.segments]


def test_clean_case_routes_to_ground_truth():
    family, decision, _reason = _classify(
        RouterEvalCaseSpec(
            case_id="c",
            ground_truth_family="medical_malpractice_defense",
            variant="clean",
            expected_decision="route",
        )
    )
    assert decision == "route"
    assert family == "medical_malpractice_defense"


def test_mixed_signals_case_abstains():
    _family, decision, reason = _classify(
        RouterEvalCaseSpec(
            case_id="c",
            ground_truth_family="general_liability_defense",
            variant="mixed_signals",
            expected_decision="abstain",
            secondary_family="commercial_litigation",
        )
    )
    assert decision == "abstain"
    assert reason == "ambiguous_multiple_families"


def test_missing_attachment_case_abstains():
    _family, decision, reason = _classify(
        RouterEvalCaseSpec(
            case_id="c",
            ground_truth_family="general_liability_defense",
            variant="missing_attachment",
            expected_decision="abstain",
        )
    )
    assert decision == "abstain"
    assert reason == "low_evidence"


def test_injection_as_text_is_inert_router_follows_real_signals():
    spec = RouterEvalCaseSpec(
        case_id="c",
        ground_truth_family="medical_malpractice_defense",
        variant="injection_as_text",
        expected_decision="route",
        secondary_family="commercial_litigation",
    )
    family, decision, _reason = _classify(spec)
    assert decision == "route"
    assert family == "medical_malpractice_defense"  # injection did not flip it
    # The injected instruction segment is flagged as a source instruction risk.
    case = build_synthetic_intake_case(spec)
    assert any(segment.source_instruction_risk for segment in case.segments)


def test_router_evaluation_report_reconciles_and_recovers_labels(repo_root):
    report = build_router_evaluation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    assert isinstance(report, RouterEvaluationReport)
    assert report.no_ml_router_used is True
    # The deterministic router recovers every known-truth label on the frozen set,
    # and abstains on every adversarial ambiguous / missing case.
    assert report.overall_accuracy == 1.0
    assert report.over_abstain_count == 0
    assert report.abstention_recall == 1.0
    assert report.expected_abstain_count >= 3
    for family in report.per_family_accuracy:
        assert family.accuracy == 1.0


def test_router_eval_report_tamper_is_rejected(repo_root):
    report = build_router_evaluation_report(
        repo_root=repo_root, generated_at="2026-07-23T00:00:00Z"
    )
    dumped = report.model_dump()
    dumped["correct_count"] = report.correct_count + 1
    import pytest

    with pytest.raises(ValueError):
        RouterEvaluationReport.model_validate(dumped)


def test_frozen_case_set_has_holdout_and_adversarial(repo_root):
    specs = load_router_eval_specs(repo_root)
    variants = {spec.variant for spec in specs}
    assert {"clean", "mixed_signals", "missing_attachment", "injection_as_text"} <= variants
    report = evaluate_router(specs, generated_at="2026-07-23T00:00:00Z")
    assert report.case_count == len(specs)
