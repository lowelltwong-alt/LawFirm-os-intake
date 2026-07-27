# Synthetic Learning-Loop Marathon (LW0–LW4) — Plan Of Record + Goal Prompt

Status: **plan of record.** Successor program to the converged CW0–CW7 marathon
(`OPUS_MARATHON_GOAL_converged.md`), which is merged to `main`. Paste the GOAL block
at the bottom into a fresh Opus 4.8 session to execute LW0→LW4 autonomously.

## Context / why

CW0–CW7 built the pieces of an intake → route → drivers → sized budget vertical, but
as separate modules with small fixtures. This program (1) runs the whole chain
**end-to-end** on **tons of synthetic data**, (2) **captures the workflow as it
improves** across generator/rule revisions, and (3) stands up the **ML challenger** —
as a boundary-safe shadow, not a budget oracle.

Not greenfield: it composes existing modules and reuses the learning/replay/eval
scaffolding. It stays inside the §21 boundary the CW marathon held throughout.

## §21 / ML boundary (non-negotiable)

- **Dollars are always deterministic** from governed rates. The ML challenger
  predicts routing / drivers / phase-task **hours** only — never dollars.
- All ML artifacts are labeled `reference_class_only` / `learnability_only` —
  **never "calibrated."** No real-world accuracy claim.
- ML runs **shadow-only** through `reviewed_learning_gate` +
  `learning_shadow_eval_results`; no promotion, no auto-apply; a leakage proof
  (`calibration/leakage.py`) is required.
- Real data (if ever) enters only via the §18 / production governance gate — out of
  scope for this program.

## Reuse map (compose, don't reinvent)

| Need | Reuse |
|---|---|
| Routing + synthetic intake factory | `routing_eval.py`, `workers.classify_matter`, `workflow.run_preflight` |
| Drivers → sizing | `case_sizing.py`, `drivers.py` |
| Budget engine + projection | `budget.build_budget_proposal`, `workflow.run_budget`, `guidelines.build_carrier_compliant_projection` |
| Export; end-to-end case reference | `budget_exporters.py`; `firm_checkpoint.py` |
| Batch replay + capture | `budget_corpus_replay.py`, `budget_corpus_replay_execution.py` |
| Learning + shadow eval + gate | `budget_learning_loop.py`, `learning_shadow_eval_results.py`, `reviewed_learning_gate.py`, `learning_promotion_readiness.py` |
| Reference-class bands + leakage | `benchmarks.py`, `calibration/leakage.py` |

## Waves (WIP=1, one stacked PR per wave, stop at each named gate)

- **LW0 — End-to-end deterministic pipeline harness.** `case_pipeline.py`:
  `run_synthetic_case_pipeline(spec) -> SyntheticCasePipelineResult` composing intake
  bundle → route → confirm family (generator ground truth) → resolve drivers →
  `build_budget_proposal` → carrier projection → `case_sizing` → firm-Excel export.
  One typed result reconciling every stage fail-closed. GATE: pipeline-contract review.
- **LW1 — Scale synthetic generator (World-Builder-lite).** `synthetic_corpus_generator.py`:
  deterministic seeded batch generator of N labeled intake bundles with ground-truth
  case-spec (family, drivers, exposure, expected reference-class band) across diversity
  axes + doc-noise variants (quoted threads, missing attachments, injection-as-text).
  Extends the CW4 factory. Frozen manifest + digests under `examples/synthetic/corpus/`.
  Single in-repo module — no new repo. GATE: generator + label-integrity review.
- **LW2 — Batch capture + evaluation loop.** `pipeline_eval.py`: run the pipeline over
  the corpus → `SyntheticPipelineEvalReport` (routing accuracy + abstention correctness;
  driver-recovery accuracy; budget reference-class plausibility bands from `benchmarks.py`),
  recomputed fail-closed. Append each run to a versioned capture ledger (reuse
  `budget_corpus_replay`) so metric deltas across revisions are tracked. GATE: eval-capture review.
- **LW3 — ML shadow challenger (lightweight learnability probe).** `ml_learnability_probe.py`:
  a dependency-light learner predicting route / drivers / phase-task hours from case
  features; evaluate **learnability** on a frozen holdout (recovers the generator's
  driver math?) + reference-class plausibility; `reference_class_only` labels; dollars
  deterministic; route through `reviewed_learning_gate` + `learning_shadow_eval_results`
  with a `calibration/leakage.py` leakage proof; **no promotion, shadow only.**
  GATE: shadow-eval review.
- **LW4 — Improvement capture + hardening + delivery (END).** `learning_capture.py`:
  each corpus/rule/generator/model revision records a metrics-delta snapshot with
  monotonic-improvement tracking; hostile-fixture sweep over every new serialized
  artifact; delivery packet (capabilities, boundaries, synthetic status, firm-data
  recalibration lane, deferred full-XGBoost note). GATE: delivery review. END.
- **LW5 — (deferred, NOT in this program)** Full XGBoost challenger behind its
  leakage/shadow-mode/deterministic-fallback/retirement gates — a future follow-on.

## Red-team premortem amendment (2026-07-23, pre-execution — binding)

Grounded in direct inspection of `routing_eval.py`, `benchmarks.py`,
`calibration/leakage.py`, `reviewed_learning_gate.py`, `learning_shadow_eval_results.py`,
`case_sizing.py`, `drivers.py`, `firm_checkpoint.py`, `guidelines.py`, and external
research on label-leakage permutation controls and metamorphic ML testing. Each
finding below is a **binding contract change** on the named wave.

- **P1 — Tautological accuracy (binds LW1, LW2).** `routing_eval` renders doc text
  directly from `MATTER_SIGNALS` terms — the same terms `classify_matter` scores.
  Corpus-scale routing accuracy would be ~100% *by construction*, making every
  captured "improvement" noise. LW1's generator MUST carry a declared difficulty
  model (signal-density parameter, distractor-family terms, paraphrase pools not
  drawn verbatim from `MATTER_SIGNALS`, noise variants) and emit per-case
  `difficulty` + `signal_terms_used`. LW2 metrics MUST be stratified by difficulty,
  carry `metric_semantics="recovers_generator_truth_on_synthetic"` and
  `real_world_accuracy_claim=False` as literal fields, and mark any saturated
  (100%) stratum non-informative for delta tracking.
- **P2 — Label leakage into probe features (binds LW1, LW3).** If LW3 features are
  read from the generator spec, the probe learns the identity function and
  "learnability" is meaningless. LW3 MUST declare a FeatureContract (features
  computed only from the rendered bundle / pipeline artifacts upstream of the
  predicted target; spec label fields are prohibited inputs, enforced by validator
  + test) and MUST ship three negative controls in-wave: (a) label-shuffle
  permutation control — holdout performance on shuffled labels must collapse to
  the chance band, else the wave fails closed; (b) majority-class/constant
  baseline reported beside probe performance — learnability is claimable only
  above baseline; (c) feature-ablation — deleting declared top features must
  degrade performance. Holdout split is assigned deterministically at LW1
  generation time (seeded hash of case_id), digest-frozen in the LW1 manifest;
  LW3 verifies the digest before eval and refuses below a declared holdout floor.
- **P3 — Privacy-proof vs label-leakage conflation (binds LW3).**
  `calibration/leakage.py` proves privacy/dominance/reconstruction properties
  (LOMO, k-anon, DP) — it does NOT test feature/label leakage. Both proofs are
  required and neither substitutes for the other; the LW3 decision trace must say
  so explicitly.
- **P4 — `benchmarks.py` has no budget bands (rewords LW2).** `benchmarks.py` is a
  pinned rate-benchmark replay auditor. The LW2 reference-class plausibility bands
  MUST be a new versioned synthetic policy under `config/` (per-case-type
  budget-to-exposure and per-phase share bands, following the case-sizing band
  pattern), loaded fail-closed: a missing band yields `not_evaluable`, never a
  silent pass. `benchmarks.py` is reused only for what it does (rate-source
  sanity), not misrepresented as the band source.
- **P5 — Goodhart / non-comparable deltas (binds LW2, LW4).** Capture-ledger
  entries MUST record every axis version+digest (corpus seed, generator version,
  rule/policy versions, probe version, code ref). Delta records are computed only
  between entries differing in exactly one axis; multi-axis deltas are typed
  `not_comparable`. "Monotonic-improvement tracking" means regressions become
  typed `metric_regression_requires_review` events — never auto-blocked, never
  silently dropped, never collapsed into a single scalar score.
- **P6 — Fail-open joints (binds LW0).** `build_carrier_compliant_projection`
  returns `None` on an unselected pack; `route_decision` abstains; a missing
  template yields exclusions. `SyntheticCasePipelineResult` MUST type every joint
  (`routed|abstained`, `projected|blocked_no_pack`, `sized|blocked_no_band`,
  `exported|not_exported`) and recompute stage-consistency + exact minor-unit
  total reconciliation in a fail-closed model validator. A `None` may never
  serialize as success.
- **P7 — Composition drift (binds LW0, LW4).** `firm_checkpoint._case` already
  mini-composes route→size→export. `case_pipeline` becomes the single canonical
  composition; `firm_checkpoint` stays the 3-case packet; the seam is recorded in
  the LW0 decision trace and the LW4 delivery packet.
- **P8 — Ground-truth confirmation provenance (binds LW0).** The pipeline's
  auto-confirmation from generator truth MUST be marked
  `confirmation_source="generator_ground_truth"` with a clearly synthetic
  reviewer identity — it must never be mistakable for human review, which remains
  the production authority.
- **P9 — Determinism (binds LW1).** Seeded `random.Random` only; canonical-JSON
  digests; sorted iteration; pinned `generated_at`; LF writes. A test regenerates
  the corpus from the manifest and asserts byte-identical digests.
- **P10 — Repo bloat (binds LW1).** Freeze N≈50 in-repo; larger corpora go to
  scratch/output dirs only, reproducible from manifest parameters.
- **P11 — Money discipline (binds all).** New serialized money is exact integer
  minor units only; stage totals reconcile exactly; no float-derived money fields.
- **P12 — Suite runtime (binds LW2+).** Unit tests use small N (8–12); the N≈50
  acceptance run is a script-produced artifact, not a per-test loop.

## Verification

Per wave: full gate (`validate_repo`, `export_schemas`, `ruff check`+`format`,
`run_full_pytest.py -q`, and `npm build`+`smoke:browser` only when the UI changes).
Acceptance: generate a small corpus (N≈50), run `pipeline_eval`, confirm routing
accuracy + driver recovery on the labeled holdout and budget bands within
reference-class plausibility; run the probe and confirm the learnability metric,
`reference_class_only` labels, and that `reviewed_learning_gate` blocks promotion;
capture-ledger shows a tracked metrics-delta across two generator revisions.

---

## GOAL PROMPT (paste into a fresh Opus 4.8 session with `/goal`)

```text
GOAL: Autonomously execute the Synthetic Learning-Loop marathon
(docs/ai-handoff/SYNTHETIC_LEARNING_LOOP_MARATHON.md) waves LW0 -> LW4 to 100%,
WITHOUT pausing for per-wave approval. I pre-approve every routine per-wave gate
(pipeline-contract, generator, eval-capture, shadow-eval, delivery). Do not wait
for me between waves; proceed straight into the next wave.

Working directory: <worktree-root>. Read first, in order:
docs/ai-handoff/SYNTHETIC_LEARNING_LOOP_MARATHON.md,
docs/ai-handoff/CASE_SIZING_AND_TRAINING_DESIGN.md (section 5),
docs/ai-handoff/CONVERGED_PLAN_OF_RECORD.md, AGENTS.md, CLAUDE.md. Branch off the
current main; each wave is its own branch stacked on the previous wave's branch,
one PR per wave.

Pre-authorization DOES cover: advancing from each wave's gate to the next without
waiting; opening a stacked PR per wave and letting CI run.

Pre-authorization does NOT override these hard rules (never break them): never
merge your own PR; never push or force-push main (waves accumulate as stacked PRs
for my review); candidate-only and synthetic-only, no real client/carrier/rate/
firm data; DOLLARS ALWAYS DETERMINISTIC from governed rates (the ML challenger
predicts routing/drivers/hours only, never dollars); all ML artifacts labeled
reference_class_only, NEVER "calibrated", no real-world accuracy claim; ML is
shadow-only through reviewed_learning_gate + learning_shadow_eval_results with a
calibration/leakage.py leakage proof, no promotion; failing test first;
contract-first modular; exact decimal money; every serialized derived value
recomputed or rule-attributed (fail-closed), never silent None/default; no new
rule language (reconcile with the Substrate OCG IR); no new repos; budget core
never depends on the guideline compiler; work-plan total never overwritten by
reimbursement math. Reuse the existing routing_eval / case_sizing / budget /
budget_corpus_replay / budget_learning_loop / learning_shadow_eval_results /
reviewed_learning_gate / calibration / benchmarks modules; extend, don't reinvent.

Per wave, in order: get the FULL validation gate green (validate_repo,
export_schemas, ruff check+format, run_full_pytest, and npm build + smoke:browser
only when the UI changes); write a decision trace under
docs/ai-handoff/decision-traces/; run the DAD loop the daemon-era way (asset-dir
agent preflight -> midflight ack -> lesson add -> lesson graph -> asset-use ->
agent postflight; NOT the legacy mailbox); update the governance dependency-map
mirror; commit; push the branch; open the stacked PR with the required governance
PR-description sections; wait for CI green; then immediately start the next wave.

Stop and wait for me ONLY if: (a) a wave's full gate cannot be made green after a
genuine fix attempt, (b) continuing would require breaking a hard rule above, or
(c) you finish LW4. Otherwise keep going. When you stop, leave all PRs open, list
every open PR (one per wave) with its gate in merge order, and note that LW5 (full
XGBoost challenger) is intentionally deferred.

Start now with LW0 and do not stop until LW4 is done or a stop condition is hit.
```
