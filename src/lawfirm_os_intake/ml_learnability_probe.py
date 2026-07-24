"""LW3 — ML shadow challenger (lightweight learnability probe).

A dependency-light learner (a term-frequency nearest-centroid classifier, pure
Python, no sklearn/xgboost) that predicts route family / an injury driver from
features computed ONLY from the rendered bundle text (the FeatureContract, P2 -
spec label fields are prohibited inputs). It is trained on the frozen TRAIN split
and evaluated on the frozen HOLDOUT split of the LW1 corpus.

Learnability is claimable for a target ONLY when the probe beats a majority-class
baseline AND survives two negative controls:

- **label-shuffle permutation** - retrain on shuffled labels; holdout accuracy must
  collapse to ~baseline (if a shuffled model still predicts, features leak labels);
- **feature ablation** - zero the top family-signal features; accuracy must degrade.

Boundaries (non-negotiable): all outputs are labeled ``reference_class_only`` /
``learnability_only`` - NEVER "calibrated"; the probe predicts routing/drivers
only, NEVER dollars (dollars stay deterministic from governed rates); the probe is
SHADOW-ONLY - its privacy leakage proof (``calibration/leakage.py``) is routed
through ``reviewed_learning_gate``, which REFUSES promotion without an approval id.
The privacy leakage proof and these feature/label-leakage controls are DISTINCT and
neither substitutes for the other (P3). No promotion; candidate-only, synthetic-only.
"""

from __future__ import annotations

import random
from pathlib import Path

from .calibration import build_calibration_leakage_proof
from .models import (
    GeneratedSyntheticCase,
    ML_PROBE_LABEL_FIELDS,
    MLLearnabilityProbeReport,
    MLLearnabilityTargetResult,
    MLProbeFeatureContract,
)
from .reviewed_learning_gate import check_calibration_leakage_proof_for_promotion
from .synthetic_corpus_generator import load_corpus, load_corpus_manifest
from .util import digest_json, load_json, now_iso
from .workers import MATTER_SIGNALS

PROBE_VERSION = "ml-learnability-probe.v0_1"
MIN_HOLDOUT_COUNT = 8
MIN_MARGIN = 0.10
SHUFFLE_TOLERANCE = 0.10
SHUFFLE_SEED = 20260723

# The privacy leakage proof reuses an existing synthetic calibration request.
CALIBRATION_REQUEST_REF = (
    "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
)

# Ablation removes the top family-signal features (each family's first two terms).
_ABLATION_TERMS_PER_FAMILY = 2


def _vocabulary() -> list[str]:
    terms: set[str] = set()
    for family_terms in MATTER_SIGNALS.values():
        terms.update(family_terms)
    return sorted(terms)


def _case_text(case: GeneratedSyntheticCase) -> str:
    return "\n".join(line.text for line in case.rendered_lines).lower()


def _feature_vector(case: GeneratedSyntheticCase, vocab: list[str]) -> dict[str, int]:
    text = _case_text(case)
    return {term: text.count(term.lower()) for term in vocab}


def _label(case: GeneratedSyntheticCase, target: str) -> str:
    if target == "route_family":
        return case.ground_truth_family
    if target == "injury_severity":
        return str(case.ground_truth_drivers.get("injury_severity", "unknown"))
    raise ValueError(f"unknown target {target!r}")


def _train_centroids(
    cases: list[GeneratedSyntheticCase],
    labels: list[str],
    vocab: list[str],
) -> dict[str, dict[str, float]]:
    sums: dict[str, dict[str, float]] = {}
    counts: dict[str, int] = {}
    for case, label in zip(cases, labels):
        vector = _feature_vector(case, vocab)
        centroid = sums.setdefault(label, {term: 0.0 for term in vocab})
        for term, value in vector.items():
            centroid[term] += value
        counts[label] = counts.get(label, 0) + 1
    for label, centroid in sums.items():
        n = counts[label]
        for term in centroid:
            centroid[term] /= n
    return sums


def _predict(
    case: GeneratedSyntheticCase,
    centroids: dict[str, dict[str, float]],
    vocab: list[str],
    *,
    ablated: set[str] | None = None,
) -> str | None:
    vector = _feature_vector(case, vocab)
    if ablated:
        for term in ablated:
            vector[term] = 0
    best_label: str | None = None
    best_score = -1.0
    for label in sorted(centroids):
        centroid = centroids[label]
        score = sum(vector[term] * centroid[term] for term in vocab)
        if score > best_score:
            best_score = score
            best_label = label
    # A zero-signal case (all features ablated/absent) yields no confident label.
    if best_score <= 0:
        return None
    return best_label


def _accuracy(
    holdout: list[GeneratedSyntheticCase],
    centroids: dict[str, dict[str, float]],
    vocab: list[str],
    target: str,
    *,
    ablated: set[str] | None = None,
) -> float:
    if not holdout:
        return 0.0
    correct = 0
    for case in holdout:
        predicted = _predict(case, centroids, vocab, ablated=ablated)
        if predicted is not None and predicted == _label(case, target):
            correct += 1
    return round(correct / len(holdout), 6)


def _majority_baseline(
    train_labels: list[str], holdout: list[GeneratedSyntheticCase], target: str
) -> float:
    if not holdout or not train_labels:
        return 0.0
    counts: dict[str, int] = {}
    for label in train_labels:
        counts[label] = counts.get(label, 0) + 1
    majority = max(sorted(counts), key=lambda label: counts[label])
    correct = sum(1 for case in holdout if _label(case, target) == majority)
    return round(correct / len(holdout), 6)


def _ablation_terms() -> set[str]:
    ablated: set[str] = set()
    for family_terms in MATTER_SIGNALS.values():
        ablated.update(list(family_terms)[:_ABLATION_TERMS_PER_FAMILY])
    return ablated


def _evaluate_target(
    *,
    target: str,
    train: list[GeneratedSyntheticCase],
    holdout: list[GeneratedSyntheticCase],
    vocab: list[str],
) -> MLLearnabilityTargetResult:
    train_labels = [_label(case, target) for case in train]
    centroids = _train_centroids(train, train_labels, vocab)
    probe_accuracy = _accuracy(holdout, centroids, vocab, target)
    baseline_accuracy = _majority_baseline(train_labels, holdout, target)

    # Negative control 1: label-shuffle permutation. If a model trained on shuffled
    # labels still predicts the holdout, the features leak the label.
    shuffled = list(train_labels)
    random.Random(SHUFFLE_SEED).shuffle(shuffled)
    shuffle_centroids = _train_centroids(train, shuffled, vocab)
    shuffle_accuracy = _accuracy(holdout, shuffle_centroids, vocab, target)

    # Negative control 2: feature ablation. Zeroing the top family-signal features
    # must degrade a genuinely learning probe.
    ablation_accuracy = _accuracy(holdout, centroids, vocab, target, ablated=_ablation_terms())

    margin = round(probe_accuracy - baseline_accuracy, 6)
    beats_baseline = margin >= MIN_MARGIN
    shuffle_collapsed = shuffle_accuracy <= baseline_accuracy + SHUFFLE_TOLERANCE
    ablation_degrades = ablation_accuracy < probe_accuracy
    learnable = beats_baseline and shuffle_collapsed and ablation_degrades
    note = (
        "learnable: probe beats baseline, shuffle collapses, ablation degrades"
        if learnable
        else "not learnable on this synthetic holdout (honest negative or below-margin)"
    )
    return MLLearnabilityTargetResult(
        target=target,  # type: ignore[arg-type]
        holdout_count=len(holdout),
        probe_accuracy=probe_accuracy,
        baseline_accuracy=baseline_accuracy,
        shuffle_accuracy=shuffle_accuracy,
        ablation_accuracy=ablation_accuracy,
        learnability_margin=margin,
        min_margin=MIN_MARGIN,
        shuffle_tolerance=SHUFFLE_TOLERANCE,
        learnable=learnable,
        note=note,
    )


def build_ml_learnability_probe_report(
    *,
    repo_root: str | Path,
    generated_at: str | None = None,
) -> MLLearnabilityProbeReport:
    root = Path(repo_root)
    cases = load_corpus(root)
    manifest = load_corpus_manifest(root)

    # Verify the frozen holdout split before evaluating (P2). The split digest must
    # match the manifest; otherwise refuse.
    split_digest_basis = sorted(f"{case.case_id}:{case.holdout_split}" for case in cases)
    from .models import _digest_str_list

    if _digest_str_list(split_digest_basis) != manifest.holdout_split_digest:
        raise ValueError("corpus holdout split does not match the frozen manifest digest")

    train = [case for case in cases if case.holdout_split == "train"]
    holdout = [case for case in cases if case.holdout_split == "holdout"]
    vocab = _vocabulary()

    targets = [
        _evaluate_target(target="route_family", train=train, holdout=holdout, vocab=vocab),
        _evaluate_target(target="injury_severity", train=train, holdout=holdout, vocab=vocab),
    ]

    # Privacy leakage proof (calibration/leakage.py) routed through the reviewed
    # learning gate, which refuses promotion without an approval id (shadow-only).
    request = load_json(root / CALIBRATION_REQUEST_REF)["request"]
    proof = build_calibration_leakage_proof(request)
    gate_check = check_calibration_leakage_proof_for_promotion(
        proof,
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=proof.determinism.aggregate_input_digest,
    )
    blocks_promotion = gate_check.status == "failed"

    feature_contract = MLProbeFeatureContract(
        vocabulary_size=len(vocab),
        prohibited_feature_fields=list(ML_PROBE_LABEL_FIELDS),
    )

    content_basis = {
        "corpus_digest": manifest.corpus_digest,
        "probe_version": PROBE_VERSION,
        "targets": [t.model_dump(mode="json") for t in targets],
        "privacy_leakage_proof_id": proof.proof_id,
        "gate_check_id": gate_check.check_id,
    }
    content_digest = digest_json(content_basis)

    return MLLearnabilityProbeReport(
        probe_id="mllearnprobe-" + content_digest.removeprefix("sha256:")[:16],
        probe_version=PROBE_VERSION,
        corpus_id=manifest.corpus_id,
        corpus_digest=manifest.corpus_digest,
        holdout_split_digest=manifest.holdout_split_digest,
        holdout_count=len(holdout),
        min_holdout_count=MIN_HOLDOUT_COUNT,
        feature_contract=feature_contract,
        targets=targets,
        privacy_leakage_proof_id=proof.proof_id,
        reviewed_learning_gate_check_id=gate_check.check_id,
        reviewed_learning_gate_blocks_promotion=blocks_promotion,
        reviewed_learning_gate_block_reason=gate_check.message,
        content_digest=content_digest,
        generated_at=generated_at or now_iso(),
    )
