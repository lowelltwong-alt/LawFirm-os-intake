"""LW2 — batch capture + evaluation loop over the frozen synthetic corpus.

Runs the deterministic pipeline stages over the LW1 corpus and produces a
``SyntheticPipelineEvalReport`` whose metrics are recomputed fail-closed and
STRATIFIED by difficulty (premortem P1): a saturated (100%) clear stratum is
flagged ``saturated_non_informative`` so it cannot masquerade as improvement.
Every metric carries explicit semantics (``recovers_generator_truth_on_synthetic``,
``real_world_accuracy_claim=False``) so no run is mistaken for a calibration claim.

Three metric families:

1. **Routing accuracy + abstention correctness** — the deterministic router runs
   on the rendered bundle (real signal, not the label); accuracy is the fraction
   of expected-route cases routed to the ground-truth family, abstention recall is
   the fraction of expected-abstain cases the router abstains on.
2. **Driver-effect recovery** — metamorphic invariants over ``case_sizing`` on the
   corpus drivers (more parties never decrease the plan; catastrophic ≥ soft
   tissue; clear ≤ disputed), recovering the generator's driver math (internal
   validity).
3. **Budget reference-class plausibility** — each case's sized work-plan total is
   checked against a DECLARED reference-class band
   (``config/synthetic-reference-class-bands.yaml``) loaded fail-closed; a missing
   band is ``not_evaluable``, never a silent pass (P4).

Each run is appended to a versioned capture ledger recording every comparison axis
(corpus seed/digest, generator/eval versions, code ref); deltas are computed only
between single-axis-differing entries and regressions are typed for review, never
auto-blocked or collapsed to a scalar (P5). Deterministic, candidate-only,
synthetic-only; no ML; dollars deterministic from the sizing policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .case_sizing import CASE_SIZING_POLICY_REF, load_case_sizing_policy, size_work_plan
from .models import (
    BudgetPlausibilityResult,
    DriverEffectInvariantResult,
    GeneratedSyntheticCase,
    RoutingDifficultyStratum,
    SyntheticEvalCaptureLedgerEntry,
    SyntheticEvalMetricDelta,
    SyntheticPipelineEvalReport,
)
from .routing_eval import _synthetic_context, route_decision
from .synthetic_corpus_generator import (
    build_bundle_and_segments,
    load_corpus,
    load_corpus_manifest,
)
from .util import append_jsonl, digest_json, now_iso, write_json
from .workers import classify_matter

EVAL_VERSION = "pipeline-eval.v0_1"
REFERENCE_CLASS_BANDS_REF = "config/synthetic-reference-class-bands.yaml"
CAPTURE_LEDGER_REF = "examples/synthetic/corpus/eval_capture_ledger.jsonl"

_DIFFICULTIES = ("clear", "moderate", "hard")


def load_reference_class_bands(path: str | Path) -> dict[str, Any]:
    """Load the declared synthetic reference-class band policy, fail-closed."""

    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("reference-class band policy must be a mapping")
    if policy.get("contains_real_firm_data", False):
        raise ValueError("real firm reference-class bands are prohibited in this repository")
    if policy.get("data_origin") != "synthetic" or policy.get("candidate_only") is not True:
        raise ValueError("reference-class band policy must be synthetic candidate-only")
    bands = policy.get("bands")
    if not isinstance(bands, dict) or not bands:
        raise ValueError("reference-class band policy requires a non-empty bands mapping")
    return policy


def _route_case(case: GeneratedSyntheticCase) -> tuple[str | None, str]:
    bundle, segments = build_bundle_and_segments(case)
    _inbound, matter, _posture = classify_matter(bundle, segments, _synthetic_context())
    routed_family, decision, _reason = route_decision(matter)
    return routed_family, decision


def _routing_strata(cases: list[GeneratedSyntheticCase]) -> list[RoutingDifficultyStratum]:
    strata: list[RoutingDifficultyStratum] = []
    for difficulty in _DIFFICULTIES:
        subset = [case for case in cases if case.difficulty == difficulty]
        if not subset:
            continue
        expected_route = [c for c in subset if c.expected_decision == "route"]
        expected_abstain = [c for c in subset if c.expected_decision == "abstain"]
        routed_correct = 0
        correct_abstain = 0
        for case in subset:
            routed_family, decision = _route_case(case)
            if case.expected_decision == "route":
                if decision == "route" and routed_family == case.ground_truth_family:
                    routed_correct += 1
            elif decision == "abstain":
                correct_abstain += 1
        routing_accuracy = round(routed_correct / len(expected_route), 6) if expected_route else 1.0
        abstention_recall = (
            round(correct_abstain / len(expected_abstain), 6) if expected_abstain else 1.0
        )
        strata.append(
            RoutingDifficultyStratum(
                difficulty=difficulty,  # type: ignore[arg-type]
                case_count=len(subset),
                expected_route_count=len(expected_route),
                routed_correct_count=routed_correct,
                expected_abstain_count=len(expected_abstain),
                correct_abstain_count=correct_abstain,
                routing_accuracy=routing_accuracy,
                abstention_recall=abstention_recall,
                saturated_non_informative=(routing_accuracy == 1.0 and abstention_recall == 1.0),
            )
        )
    return strata


def _sized_total(
    case: GeneratedSyntheticCase, policy: dict[str, Any], *, drivers: dict[str, Any] | None = None
) -> int:
    sized = size_work_plan(
        base_work_plan_total_minor_units=case.base_work_plan_total_minor_units,
        case_type=case.case_type,
        drivers=drivers if drivers is not None else case.ground_truth_drivers,
        policy=policy,
    )
    return sized.sized_work_plan_total_minor_units


def _driver_effect_invariants(
    cases: list[GeneratedSyntheticCase], policy: dict[str, Any]
) -> list[DriverEffectInvariantResult]:
    # Metamorphic invariants: perturb one driver on each case's own drivers and
    # assert the sized total moves in the declared direction. This recovers the
    # generator's driver math (internal validity), independent of the sampled
    # driver values.
    invariants: list[DriverEffectInvariantResult] = []

    def _check(invariant_id: str, description: str, perturb, monotone) -> None:
        checked = 0
        violations = 0
        for case in cases:
            base = case.ground_truth_drivers
            other = perturb(dict(base))
            if other is None:
                continue
            checked += 1
            base_total = _sized_total(case, policy)
            other_total = _sized_total(case, policy, drivers=other)
            if not monotone(base_total, other_total):
                violations += 1
        invariants.append(
            DriverEffectInvariantResult(
                invariant_id=invariant_id,
                description=description,
                checked_pairs=checked,
                violations=violations,
                passed=violations == 0,
            )
        )

    def _more_parties(drivers: dict[str, Any]) -> dict[str, Any] | None:
        drivers["party_count"] = int(drivers.get("party_count", 1)) + 1
        return drivers

    def _catastrophic(drivers: dict[str, Any]) -> dict[str, Any] | None:
        if drivers.get("injury_severity") == "catastrophic":
            return None
        drivers["injury_severity"] = "catastrophic"
        return drivers

    def _disputed(drivers: dict[str, Any]) -> dict[str, Any] | None:
        if drivers.get("liability_clarity") == "disputed":
            return None
        drivers["liability_clarity"] = "disputed"
        return drivers

    _check(
        "more_parties_non_decreasing",
        "adding a party never decreases the sized work plan",
        _more_parties,
        lambda base, other: other >= base,
    )
    _check(
        "catastrophic_at_least_baseline",
        "raising injury severity to catastrophic never decreases the plan",
        _catastrophic,
        lambda base, other: other >= base,
    )
    _check(
        "disputed_at_least_baseline",
        "raising liability clarity to disputed never decreases the plan",
        _disputed,
        lambda base, other: other >= base,
    )
    return invariants


def _budget_plausibility(
    cases: list[GeneratedSyntheticCase],
    sizing_policy: dict[str, Any],
    bands_policy: dict[str, Any],
) -> BudgetPlausibilityResult:
    bands = bands_policy["bands"]
    within = 0
    out = 0
    not_evaluable = 0
    for case in cases:
        band = bands.get(case.case_type)
        if band is None or case.case_type not in sizing_policy.get("proportionality_bands", {}):
            # Fail-closed: no declared band (or no sizing band) -> not evaluable.
            not_evaluable += 1
            continue
        sized_total = _sized_total(case, sizing_policy)
        exposure = case.exposure_minor_units
        ratio = sized_total / exposure if exposure else float("inf")
        min_ratio = float(band["min_budget_to_exposure_ratio"])
        max_ratio = float(band["max_budget_to_exposure_ratio"])
        floor = int(band["floor_minor_units"])
        ceiling = int(band["ceiling_minor_units"])
        plausible = min_ratio <= ratio <= max_ratio and floor <= sized_total <= ceiling
        if plausible:
            within += 1
        else:
            out += 1
    evaluated = within + out
    return BudgetPlausibilityResult(
        evaluated_count=evaluated,
        within_band_count=within,
        out_of_band_count=out,
        not_evaluable_count=not_evaluable,
        plausibility_rate=round(within / evaluated, 6) if evaluated else 1.0,
    )


def build_pipeline_eval_report(
    *,
    repo_root: str | Path,
    generated_at: str | None = None,
) -> SyntheticPipelineEvalReport:
    root = Path(repo_root)
    cases = load_corpus(root)
    manifest = load_corpus_manifest(root)
    sizing_policy = load_case_sizing_policy(root / CASE_SIZING_POLICY_REF)
    bands_policy = load_reference_class_bands(root / REFERENCE_CLASS_BANDS_REF)

    strata = _routing_strata(cases)
    invariants = _driver_effect_invariants(cases, sizing_policy)
    plausibility = _budget_plausibility(cases, sizing_policy, bands_policy)

    total_route = sum(s.expected_route_count for s in strata)
    total_route_hit = sum(s.routed_correct_count for s in strata)
    total_abstain = sum(s.expected_abstain_count for s in strata)
    total_abstain_hit = sum(s.correct_abstain_count for s in strata)
    overall_routing = round(total_route_hit / total_route, 6) if total_route else 1.0
    overall_abstention = round(total_abstain_hit / total_abstain, 6) if total_abstain else 1.0

    content_basis = {
        "corpus_id": manifest.corpus_id,
        "corpus_digest": manifest.corpus_digest,
        "eval_version": EVAL_VERSION,
        "overall_routing_accuracy": overall_routing,
        "overall_abstention_recall": overall_abstention,
        "routing_by_difficulty": [s.model_dump(mode="json") for s in strata],
        "driver_effect_invariants": [i.model_dump(mode="json") for i in invariants],
        "budget_plausibility": plausibility.model_dump(mode="json"),
    }
    content_digest = digest_json(content_basis)

    return SyntheticPipelineEvalReport(
        eval_report_id="pipelineeval-" + content_digest.removeprefix("sha256:")[:16],
        corpus_id=manifest.corpus_id,
        corpus_digest=manifest.corpus_digest,
        corpus_seed=manifest.corpus_seed,
        generator_version=manifest.generator_version,
        eval_version=EVAL_VERSION,
        case_count=len(cases),
        overall_routing_accuracy=overall_routing,
        overall_abstention_recall=overall_abstention,
        routing_by_difficulty=strata,
        driver_effect_invariants=invariants,
        budget_plausibility=plausibility,
        content_digest=content_digest,
        generated_at=generated_at or now_iso(),
    )


def capture_ledger_entry(
    report: SyntheticPipelineEvalReport,
    *,
    code_ref: str,
    generated_at: str | None = None,
) -> SyntheticEvalCaptureLedgerEntry:
    passed = sum(1 for inv in report.driver_effect_invariants if inv.passed)
    basis = {
        "eval_report_id": report.eval_report_id,
        "corpus_digest": report.corpus_digest,
        "eval_version": report.eval_version,
        "code_ref": code_ref,
    }
    content_digest = digest_json(basis)
    return SyntheticEvalCaptureLedgerEntry(
        entry_id="evalcapture-" + content_digest.removeprefix("sha256:")[:16],
        eval_report_id=report.eval_report_id,
        corpus_id=report.corpus_id,
        corpus_seed=report.corpus_seed,
        corpus_digest=report.corpus_digest,
        generator_version=report.generator_version,
        eval_version=report.eval_version,
        code_ref=code_ref,
        overall_routing_accuracy=report.overall_routing_accuracy,
        overall_abstention_recall=report.overall_abstention_recall,
        budget_plausibility_rate=report.budget_plausibility.plausibility_rate,
        driver_invariants_passed=passed,
        driver_invariants_total=len(report.driver_effect_invariants),
        content_digest=content_digest,
        generated_at=generated_at or now_iso(),
    )


def append_capture_ledger(entry: SyntheticEvalCaptureLedgerEntry, *, repo_root: str | Path) -> Path:
    path = Path(repo_root) / CAPTURE_LEDGER_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(path, entry.model_dump(mode="json"))
    return path


def load_capture_ledger(repo_root: str | Path) -> list[SyntheticEvalCaptureLedgerEntry]:
    path = Path(repo_root) / CAPTURE_LEDGER_REF
    if not path.exists():
        return []
    entries: list[SyntheticEvalCaptureLedgerEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            entries.append(SyntheticEvalCaptureLedgerEntry.model_validate(json.loads(raw)))
    return entries


_AXES = ("corpus_seed", "corpus_digest", "generator_version", "eval_version", "code_ref")


def compute_metric_delta(
    from_entry: SyntheticEvalCaptureLedgerEntry,
    to_entry: SyntheticEvalCaptureLedgerEntry,
) -> SyntheticEvalMetricDelta:
    """Delta between two ledger entries; only single-axis differences compare (P5)."""

    differing = [axis for axis in _AXES if getattr(from_entry, axis) != getattr(to_entry, axis)]
    if len(differing) != 1:
        return SyntheticEvalMetricDelta(
            from_entry_id=from_entry.entry_id,
            to_entry_id=to_entry.entry_id,
            changed_axis="code_ref",
            comparability="not_comparable",
            status="not_comparable",
        )
    routing_delta = round(
        to_entry.overall_routing_accuracy - from_entry.overall_routing_accuracy, 6
    )
    abstention_delta = round(
        to_entry.overall_abstention_recall - from_entry.overall_abstention_recall, 6
    )
    plausibility_delta = round(
        to_entry.budget_plausibility_rate - from_entry.budget_plausibility_rate, 6
    )
    regressed = [
        name
        for name, value in (
            ("routing_accuracy", routing_delta),
            ("abstention_recall", abstention_delta),
            ("budget_plausibility", plausibility_delta),
        )
        if value < 0
    ]
    improved = any(v > 0 for v in (routing_delta, abstention_delta, plausibility_delta))
    if regressed:
        status = "metric_regression_requires_review"
    elif improved:
        status = "improved"
    else:
        status = "unchanged"
    return SyntheticEvalMetricDelta(
        from_entry_id=from_entry.entry_id,
        to_entry_id=to_entry.entry_id,
        changed_axis=differing[0],  # type: ignore[arg-type]
        comparability="comparable",
        routing_accuracy_delta=routing_delta,
        abstention_recall_delta=abstention_delta,
        budget_plausibility_delta=plausibility_delta,
        regression_flags=regressed,
        status=status,  # type: ignore[arg-type]
    )


def run_pipeline_eval(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[SyntheticPipelineEvalReport, Path]:
    report = build_pipeline_eval_report(repo_root=repo_root, generated_at=generated_at)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "synthetic_pipeline_eval_report.json", report.model_dump(mode="json"))
    return report, run_dir
