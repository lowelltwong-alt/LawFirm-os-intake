"""LW4 — improvement capture + hardening + delivery (END OF PROGRAM).

Three deliverables:

1. **Improvement capture** — track metric deltas across revisions from the LW2
   capture ledger. Consecutive single-axis deltas are aggregated into a
   ``LearningCaptureReport`` with a monotonic-improvement status; a regression
   becomes a typed ``metric_regression_requires_review`` review event, never
   auto-blocked and never collapsed into a single scalar score (P5).
2. **Hostile-fixture sweep** — tamper a reconciled field on EVERY new serialized
   artifact from LW0-LW3 and prove each fails closed on revalidation.
3. **Delivery packet** — enumerate capabilities, boundaries, synthetic status, the
   firm-data recalibration lane, the deferred full-XGBoost (LW5) note, and the
   ``case_pipeline`` vs ``firm_checkpoint`` composition seam (P7).

Candidate-only, synthetic-only; the ML challenger stays shadow-only; dollars stay
deterministic from governed rates.
"""

from __future__ import annotations

from pathlib import Path

from .models import (
    HostileSweepArtifactResult,
    LearningCaptureReport,
    LearningLoopDeliveryPacket,
    LearningLoopHostileSweepReport,
    SyntheticEvalCaptureLedgerEntry,
    SyntheticEvalMetricDelta,
)
from .pipeline_eval import compute_metric_delta
from .util import digest_json, now_iso

DELIVERY_PROGRAM = "synthetic-learning-loop-marathon"

# Every new serialized artifact introduced by LW0-LW4, with a reconciled field a
# hostile edit must break.
HOSTILE_SWEEP_ARTIFACT_IDS = [
    "synthetic-case-pipeline-result",
    "generated-synthetic-case",
    "synthetic-corpus-manifest",
    "synthetic-pipeline-eval-report",
    "synthetic-eval-metric-delta",
    "ml-learnability-probe-report",
    "ml-learnability-target-result",
    "learning-capture-report",
    "learning-loop-delivery-packet",
]


def build_learning_capture_report(
    entries: list[SyntheticEvalCaptureLedgerEntry],
    *,
    generated_at: str | None = None,
) -> LearningCaptureReport:
    """Aggregate consecutive single-axis deltas from the capture ledger."""

    deltas: list[SyntheticEvalMetricDelta] = []
    for previous, current in zip(entries, entries[1:]):
        deltas.append(compute_metric_delta(previous, current))

    comparable = [d for d in deltas if d.comparability == "comparable"]
    not_comparable = [d for d in deltas if d.comparability == "not_comparable"]
    improved = sum(1 for d in comparable if d.status == "improved")
    regressed = sum(1 for d in comparable if d.status == "metric_regression_requires_review")
    unchanged = sum(1 for d in comparable if d.status == "unchanged")
    regressions = [
        f"{d.from_entry_id}->{d.to_entry_id}"
        for d in comparable
        if d.status == "metric_regression_requires_review"
    ]
    basis = {
        "entry_ids": [entry.entry_id for entry in entries],
        "delta_statuses": [d.status for d in deltas],
    }
    content_digest = digest_json(basis)
    return LearningCaptureReport(
        capture_report_id="learningcapture-" + content_digest.removeprefix("sha256:")[:16],
        entry_count=len(entries),
        deltas=deltas,
        comparable_delta_count=len(comparable),
        not_comparable_delta_count=len(not_comparable),
        improvement_count=improved,
        regression_count=regressed,
        unchanged_count=unchanged,
        monotonic_improvement=regressed == 0,
        regressions_requiring_review=regressions,
        content_digest=content_digest,
        generated_at=generated_at or now_iso(),
    )


def _rejects_on_tamper(model_cls, payload: dict, field_path: list, new_value) -> bool:
    """Return True iff tampering ``field_path`` to ``new_value`` fails revalidation."""

    import copy

    tampered = copy.deepcopy(payload)
    target = tampered
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = new_value
    try:
        model_cls.model_validate(tampered)
    except Exception:
        return True
    return False


def run_hostile_fixture_sweep(
    *,
    repo_root: str | Path,
    generated_at: str | None = None,
) -> LearningLoopHostileSweepReport:
    """Tamper a reconciled field on every new artifact; each must fail closed."""

    from .case_pipeline import run_synthetic_case_pipeline
    from .ml_learnability_probe import build_ml_learnability_probe_report
    from .models import (
        GeneratedSyntheticCase,
        MLLearnabilityProbeReport,
        MLLearnabilityTargetResult,
        SyntheticCasePipelineResult,
        SyntheticCorpusManifest,
        SyntheticEvalMetricDelta,
        SyntheticPipelineEvalReport,
    )
    from .pipeline_eval import build_pipeline_eval_report, capture_ledger_entry
    from .synthetic_corpus_generator import load_corpus, load_corpus_manifest

    root = Path(repo_root)
    import tempfile

    results: list[HostileSweepArtifactResult] = []

    # Pipeline result (LW0): break the export<->work-plan minor-unit reconciliation.
    with tempfile.TemporaryDirectory() as tmp:
        from .models import SettlementPostureInput, SyntheticCasePipelineSpec

        spec = SyntheticCasePipelineSpec(
            case_id="sweep-medmal",
            inbound_ref="examples/synthetic/inbound/carrier-assignment-medmal.json",
            confirmation_template_ref=(
                "examples/synthetic/confirmations/"
                "carrier-assignment-medmal.confirmation-template.json"
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
        pipeline = run_synthetic_case_pipeline(
            spec, repo_root=root, out_dir=tmp, generated_at="2026-07-23T00:00:00Z"
        )
    results.append(
        HostileSweepArtifactResult(
            artifact_id="synthetic-case-pipeline-result",
            tampered_field="export.firm_excel_original_total_minor_units",
            rejected_on_tamper=_rejects_on_tamper(
                SyntheticCasePipelineResult,
                pipeline.model_dump(mode="json"),
                ["export", "firm_excel_original_total_minor_units"],
                (pipeline.export.firm_excel_original_total_minor_units or 0) + 1,
            ),
        )
    )

    cases = load_corpus(root)
    manifest = load_corpus_manifest(root)
    case = cases[0]
    results.append(
        HostileSweepArtifactResult(
            artifact_id="generated-synthetic-case",
            tampered_field="signal_terms_used",
            rejected_on_tamper=_rejects_on_tamper(
                GeneratedSyntheticCase,
                {**case.model_dump(mode="json"), "difficulty": "clear"},
                ["signal_terms_used"],
                [],
            ),
        )
    )
    results.append(
        HostileSweepArtifactResult(
            artifact_id="synthetic-corpus-manifest",
            tampered_field="cases[0].holdout_split",
            rejected_on_tamper=_rejects_on_tamper(
                SyntheticCorpusManifest,
                manifest.model_dump(mode="json"),
                ["cases", 0, "holdout_split"],
                "train" if manifest.cases[0].holdout_split == "holdout" else "holdout",
            ),
        )
    )

    eval_report = build_pipeline_eval_report(repo_root=root, generated_at="2026-07-23T00:00:00Z")
    results.append(
        HostileSweepArtifactResult(
            artifact_id="synthetic-pipeline-eval-report",
            tampered_field="overall_abstention_recall",
            rejected_on_tamper=_rejects_on_tamper(
                SyntheticPipelineEvalReport,
                eval_report.model_dump(mode="json"),
                ["overall_abstention_recall"],
                round(eval_report.overall_abstention_recall + 0.1, 6),
            ),
        )
    )

    entry = capture_ledger_entry(eval_report, code_ref="sweep", generated_at="2026-07-23T00:00:00Z")
    other = entry.model_copy(
        update={
            "entry_id": "sweep2",
            "code_ref": "sweep-b",
            "overall_routing_accuracy": round(entry.overall_routing_accuracy - 0.1, 6),
        }
    )
    delta = compute_metric_delta(entry, other)
    results.append(
        HostileSweepArtifactResult(
            artifact_id="synthetic-eval-metric-delta",
            tampered_field="status",
            rejected_on_tamper=_rejects_on_tamper(
                SyntheticEvalMetricDelta,
                delta.model_dump(mode="json"),
                ["status"],
                "improved",
            ),
        )
    )

    probe = build_ml_learnability_probe_report(repo_root=root, generated_at="2026-07-23T00:00:00Z")
    results.append(
        HostileSweepArtifactResult(
            artifact_id="ml-learnability-probe-report",
            tampered_field="reviewed_learning_gate_blocks_promotion",
            rejected_on_tamper=_rejects_on_tamper(
                MLLearnabilityProbeReport,
                probe.model_dump(mode="json"),
                ["reviewed_learning_gate_blocks_promotion"],
                False,
            ),
        )
    )
    target = probe.targets[0]
    results.append(
        HostileSweepArtifactResult(
            artifact_id="ml-learnability-target-result",
            tampered_field="learnability_margin",
            rejected_on_tamper=_rejects_on_tamper(
                MLLearnabilityTargetResult,
                target.model_dump(mode="json"),
                ["learnability_margin"],
                round(target.learnability_margin + 0.5, 6),
            ),
        )
    )

    capture = build_learning_capture_report([entry, other], generated_at="2026-07-23T00:00:00Z")
    results.append(
        HostileSweepArtifactResult(
            artifact_id="learning-capture-report",
            tampered_field="monotonic_improvement",
            rejected_on_tamper=_rejects_on_tamper(
                LearningCaptureReport,
                capture.model_dump(mode="json"),
                ["monotonic_improvement"],
                not capture.monotonic_improvement,
            ),
        )
    )

    packet = build_delivery_packet(generated_at="2026-07-23T00:00:00Z")
    results.append(
        HostileSweepArtifactResult(
            artifact_id="learning-loop-delivery-packet",
            tampered_field="capabilities",
            rejected_on_tamper=_rejects_on_tamper(
                LearningLoopDeliveryPacket,
                packet.model_dump(mode="json"),
                ["capabilities"],
                [],
            ),
        )
    )

    basis = {"artifacts": [r.artifact_id for r in results]}
    return LearningLoopHostileSweepReport(
        sweep_report_id="hostilesweep-" + digest_json(basis).removeprefix("sha256:")[:16],
        artifacts=results,
        all_rejected=all(r.rejected_on_tamper for r in results),
        generated_at=generated_at or now_iso(),
    )


def build_delivery_packet(*, generated_at: str | None = None) -> LearningLoopDeliveryPacket:
    capabilities = [
        "LW0: one canonical end-to-end deterministic case pipeline (intake -> route "
        "-> confirm -> budget -> carrier projection -> case sizing -> firm-Excel "
        "export) reconciled fail-closed with exact minor-unit money",
        "LW1: deterministic seeded synthetic corpus generator with a declared "
        "difficulty model that defeats tautological routing accuracy, plus a "
        "leak-proof frozen train/holdout split",
        "LW2: difficulty-stratified batch evaluation (routing/abstention, "
        "driver-effect invariants, reference-class budget plausibility) with a "
        "Goodhart-safe single-axis capture ledger",
        "LW3: a dependency-light ML learnability probe with a FeatureContract and "
        "label-shuffle/baseline/ablation negative controls, shadow-only",
        "LW4: monotonic-improvement capture, a hostile-fixture sweep over every new "
        "artifact, and this delivery packet",
    ]
    boundaries = [
        "candidate-only and synthetic-only throughout; no real client/carrier/rate/firm data",
        "dollars are always deterministic from governed rates; the ML challenger "
        "predicts routing/drivers/hours only, never dollars",
        "all ML artifacts are reference_class_only / learnability_only, never "
        "calibrated; no real-world accuracy claim",
        "the ML probe is shadow-only through reviewed_learning_gate with a "
        "calibration/leakage.py privacy proof; no promotion, no auto-apply",
        "the immutable work-plan total is never overwritten by reimbursement math",
        "no new rule language; no new repo; the budget core does not depend on the "
        "guideline compiler",
    ]
    firm_data_recalibration_lane = [
        "Real dispositions/actuals (settlement value S, win-probability p, defense "
        "envelopes) replace the declared synthetic assumptions ONLY through the "
        "governed section-18 production data gate with human reconciliation.",
        "Only after that gate do accuracy claims exist; until then every metric is "
        "recovers_generator_truth_on_synthetic, not a real-world claim.",
        "The ML probe's learnability signal informs the challenger design but is "
        "promoted only via reviewed_learning_gate + owner review with an approval id.",
    ]
    open_human_gates = [
        "LW0 pipeline-contract review",
        "LW1 generator + label-integrity review",
        "LW2 eval-capture review",
        "LW3 shadow-eval review",
        "LW4 delivery review",
    ]
    composition_seam_note = (
        "case_pipeline is the single canonical composition of the intake->export "
        "chain; firm_checkpoint remains the 3-case firm-checkpoint packet and is "
        "unchanged. Later waves drive case_pipeline, not a re-mini-composition (P7)."
    )
    deferred_full_xgboost_note = (
        "LW5 (full XGBoost challenger) is intentionally DEFERRED, behind its own "
        "leakage-proof, shadow-mode, deterministic-fallback, and retirement gates. "
        "LW3's dependency-light probe is a learnability probe, not that challenger."
    )
    basis = {"program": DELIVERY_PROGRAM, "capabilities": capabilities}
    return LearningLoopDeliveryPacket(
        packet_id="learningdelivery-" + digest_json(basis).removeprefix("sha256:")[:16],
        program=DELIVERY_PROGRAM,
        waves_delivered=["LW0", "LW1", "LW2", "LW3", "LW4"],
        capabilities=capabilities,
        boundaries=boundaries,
        hostile_sweep_artifacts=list(HOSTILE_SWEEP_ARTIFACT_IDS),
        firm_data_recalibration_lane=firm_data_recalibration_lane,
        open_human_gates=open_human_gates,
        composition_seam_note=composition_seam_note,
        deferred_full_xgboost_note=deferred_full_xgboost_note,
        generated_at=generated_at or now_iso(),
    )
