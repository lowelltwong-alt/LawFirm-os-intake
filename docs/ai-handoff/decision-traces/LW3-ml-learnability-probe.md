# Decision Trace — LW3 ML Shadow Challenger (Learnability Probe)

Wave: LW3 of the Synthetic Learning-Loop marathon. Branch:
`claude/lw3-ml-learnability-probe`, stacked on the LW2 branch. Candidate-only,
synthetic-only, deterministic. **The first ML in the program — shadow-only, no
promotion.**

## Situation

The program's ML step: does a learner recover routing/driver structure from
observable features on a frozen holdout? This is the most safety-sensitive wave;
the §21 boundary and the premortem (P2 label leakage, P3 privacy-vs-label-leakage)
govern every choice.

## Decision

An additive `ml_learnability_probe` module — a **dependency-light** term-frequency
nearest-centroid classifier (pure Python, no sklearn/xgboost) — with:

1. **FeatureContract (P2)** — features are term counts from the rendered bundle
   text ONLY; every spec label field (`ground_truth_family`, `difficulty`,
   `ground_truth_drivers`, `exposure`, `holdout_split`, …) is a prohibited input,
   enforced by a model validator + test.
2. **Frozen-holdout verification (P2)** — the corpus holdout split is recomputed
   and checked against the LW1 manifest `holdout_split_digest` before evaluation;
   a mismatch refuses. A declared `MIN_HOLDOUT_COUNT` floor is enforced.
3. **Three learnability signals per target** — probe holdout accuracy, a
   **majority-class baseline**, and two negative controls: a **label-shuffle
   permutation** (retrain on shuffled labels — holdout accuracy must collapse to
   ~baseline, else features leak the label) and **feature ablation** (zero the top
   family-signal terms — accuracy must degrade). `learnable` is true ONLY when the
   probe beats baseline by a margin AND the shuffle collapses AND ablation
   degrades — recomputed fail-closed in the model.
4. **Two targets, one positive + one honest negative** — `route_family` (learnable
   from bundle terms) and `injury_severity` (a randomly-sampled driver NOT encoded
   in the text → not learnable). Including a no-signal target that the eval
   correctly reports as not-learnable is the strongest evidence the methodology is
   not rigged.
5. **Boundary labels** — `reference_class_only` / `learnability_only`,
   `calibrated=False`, `real_world_accuracy_claim=False`, `predicts_dollars=False`,
   `dollars_remain_deterministic=True` as literal fields.
6. **Shadow-only through the gate (no promotion)** — a privacy leakage proof is
   built with `calibration/leakage.py` and routed through
   `reviewed_learning_gate.check_calibration_leakage_proof_for_promotion`, which
   **refuses promotion** (no approval id → `failed` / `missing_approval_id`). The
   report's validator requires the gate to block promotion (fail-closed).
7. **P3 separation** — the calibration/leakage.py proof is a **privacy** proof; it
   is explicitly distinct from the feature/label-leakage controls (the
   shuffle/ablation results), and neither substitutes for the other. Both are
   recorded.

## Result

On the frozen 15-case holdout:
- **route_family**: probe **0.60** vs baseline **0.067**; label-shuffle **0.067**
  (collapses to chance — no leakage); ablation **0.20** (degrades). → **learnable**.
- **injury_severity**: probe **0.20** vs baseline **0.267**, margin negative. →
  **not learnable** (honest negative — the driver is not in the text).
- reviewed_learning_gate **blocks promotion** (`missing_approval_id`); the probe is
  shadow-only, predicts no dollars, and is labeled `reference_class_only`.

## Non-decision

- No XGBoost / heavy ML (LW5, deferred); no promotion, no auto-apply, no baseline
  mutation, no silent learning.
- No dollars predicted; dollars stay deterministic from governed rates.
- No change to the router, `case_sizing`, the pipeline, or the corpus.

## Authority impact

Local candidate work; one new candidate schema (`ml-learnability-probe-report`).
Reuses `calibration/leakage.py` + `reviewed_learning_gate` unchanged. No
canonical/promoted contract change; no cross-repo write; no promotion.

## Evidence

- `tests/test_ml_learnability_probe.py` — 9 tests (failing-test-first):
  route_family learnable-with-controls; driver honestly not-learnable; shadow-only
  gate blocks promotion (+ tamper rejection); reference_class_only/never-calibrated
  labels; FeatureContract prohibits all label fields (+ leakage-guard rejection);
  privacy-proof-vs-label-leakage-control distinction (P3); determinism; holdout
  floor enforced; learnable-flag fail-closed recomputation.

## Alternatives rejected

- **Force the probe through `LearningProposedChangeSet`.** Rejected: that contract
  is scoped to carrier/budget learning sources; encoding an ML probe as a
  `carrier_rejection_learning_proposal` would misrepresent it. The boundary-correct
  integration is the calibration-proof promotion gate.
- **Feed the probe the spec drivers as features.** Rejected (P2): that is label
  leakage; features come only from the rendered bundle.
- **Report only the learnable target.** Rejected: the honest negative
  (injury_severity) is the proof the eval is not rigged.
- **Label any output "calibrated."** Prohibited (§21): `reference_class_only` only.

## Risks and rollback

- Risk: a reader could over-read "learnable" as a real-world accuracy claim.
  Contained by the literal `real_world_accuracy_claim=False` /
  `label_class=reference_class_only` fields and the decision trace. Rollback is a
  single-branch revert; the module is additive and promotes nothing.

## Validation

`validate_repo.py` passed; `export_schemas.py` idempotent (one new schema); ruff
check + format clean; `run_full_pytest.py` full suite green; smoke demo green. No
UI change this wave.

## Human gate

LW3 human gate: **shadow-eval review**. Opened by the agent; it does not merge its
own PR and does not push `main`. The probe promotes nothing.

## DAD

Per-wave preflight/midflight(acks)/lesson/asset-use/postflight through the
daemon-era `asset-dir` pipeline.
