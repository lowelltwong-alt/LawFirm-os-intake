# Decision Trace — LW2 Batch Capture + Evaluation Loop

Wave: LW2 of the Synthetic Learning-Loop marathon. Branch:
`claude/lw2-pipeline-eval`, stacked on the LW1 branch. Candidate-only,
synthetic-only, deterministic, **no ML**.

## Situation

With the LW1 corpus in place, LW2 measures the deterministic pipeline over it and
captures each run so metric deltas across revisions are tracked. The premortem
bound the metric design (P1 stratification, P4 declared bands, P5 Goodhart-safe
capture).

## Decision

An additive `pipeline_eval` module producing `SyntheticPipelineEvalReport`:

1. **Routing accuracy + abstention correctness, stratified by difficulty (P1)** —
   the deterministic router runs on the rendered bundle (real signal, not the
   label). Each difficulty stratum reports routing accuracy and abstention recall,
   recomputed fail-closed; a stratum that is perfect on both is flagged
   `saturated_non_informative` so it cannot masquerade as improvement.
2. **Driver-effect recovery** — metamorphic invariants over `case_sizing` on the
   corpus drivers (more parties never decrease the plan; catastrophic ≥ soft
   tissue; disputed ≥ clear), recovering the generator's driver math (internal
   validity).
3. **Budget reference-class plausibility (P4)** — each case's sized work-plan total
   is checked against a **declared** reference-class band
   (`config/synthetic-reference-class-bands.yaml`) loaded fail-closed; a case type
   with no band is `not_evaluable`, never a silent pass.
4. **Versioned capture ledger (P5)** — each run appends a
   `SyntheticEvalCaptureLedgerEntry` recording every comparison axis (corpus
   seed/digest, generator/eval versions, code ref). `compute_metric_delta`
   compares two entries only when exactly one axis differs; a multi-axis diff is
   typed `not_comparable`; a negative metric is typed
   `metric_regression_requires_review` — never auto-blocked, never collapsed to a
   single scalar score.

Every report carries `metric_semantics="recovers_generator_truth_on_synthetic"`,
`real_world_accuracy_claim=False`, `calibration_claim=False` as literal fields.

## The eval found a real generator bug (honest-eval evidence)

Running LW2 exposed that the LW1 generator mis-scaled base work plans versus
exposure (a $3M case sized at ~$15k → ratio ~0.0001, plausibility **0.19**). The
fix — deriving the base work plan as a realistic fraction of exposure
(`BASE_WORK_PLAN_FRACTION`) plus generous band floors/ceilings so the ratio binds
— raised plausibility to **0.96** (50/52 within band, 2 legitimately over-sized).
This refinement to the LW1 generator + a regenerated frozen corpus rides in this
wave; that the eval caught the mis-scaling is exactly what an honest eval is for.

## Result

Overall routing accuracy 1.0 on expected-route cases, but **overall abstention
recall 0.43** — the router is genuinely imperfect (hard cases defeat it), so the
metrics are informative, not tautological. The `moderate` stratum is flagged
`saturated_non_informative`. All three driver invariants pass. Budget plausibility
0.96.

## Non-decision

- No ML (that is LW3); no promotion; no calibration claim.
- No change to the router, `case_sizing`, or the LW0 pipeline logic.
- No real data.

## Authority impact

Local candidate work; three new candidate schemas (`synthetic-pipeline-eval-report`,
`synthetic-eval-capture-ledger-entry`, `synthetic-eval-metric-delta`); a
generator/band refinement + regenerated corpus. No canonical/promoted contract
change; no cross-repo write.

## Evidence

- `tests/test_pipeline_eval.py` — 11 tests (failing-test-first): report
  reconciliation fail-closed; stratification + saturation flag; **non-tautology**
  (overall abstention recall < 1.0); driver-invariant recovery; plausibility
  evaluated-not-silent; missing-band `not_evaluable` fail-closed; band policy
  rejects real-firm data; single-axis typed-regression delta; multi-axis
  `not_comparable`; delta regression-flag integrity.

## Alternatives rejected

- **Single scalar "score."** Rejected (P5): metrics stay separate; regressions are
  typed for review.
- **Compute deltas across multi-axis changes.** Rejected (P5): only single-axis
  differences are comparable.
- **Tune the generator to hit 100% plausibility.** Rejected (Goodhart): the fix
  makes the economics realistic, and 2 cases remain legitimately over-band.

## Risks and rollback

- Risk: the reference-class bands are synthetic and not firm-calibrated. Contained
  by candidate status, the `real_world_accuracy_claim=False` literal, and the
  eval-capture review gate. Rollback is a single-branch revert.

## Validation

`validate_repo.py` passed; `export_schemas.py` idempotent (three new schemas); ruff
check + format clean; `run_full_pytest.py` full suite green; smoke demo green. No
UI change this wave.

## Human gate

LW2 human gate: **eval-capture review**. Opened by the agent; it does not merge its
own PR and does not push `main`.

## DAD

Per-wave preflight/midflight(acks)/lesson/asset-use/postflight through the
daemon-era `asset-dir` pipeline.
