# Decision Trace — DT4 Driver-Stratified Synthetic Generator (Spec v2)

Slice: post-marathon workstream, successor to DT3 (PR #125, squash-merged).
Branch: `claude/dt4-stratified-generator`, off `main`. Candidate-only,
synthetic-only, deterministic; no ML, no promotion.

## Situation

The marathon's honest eval exposed its own biggest gap: drivers were sampled but
never expressed in the documents, so driver recovery was untestable
(`injury_severity` was correctly reported not-learnable). The generation spec
(`MEDICAL_MALPRACTICE_SYNTHETIC_MATTER_GENERATION_SPEC.md`) fixes this; DT4
implements it.

## Placement decision

The spec names world-maker as the eventual home. Implemented **intake-side** as a
self-contained module because world-maker has no local clone and every consumer
(pipeline_eval, the probe, and the canonical pricing engine that computes the
budgets) lives here; migration later is a lift-and-shift. Recorded deliberately.

## Decision

`stratified_corpus_generator` produces a frozen corpus of **174 matters** (vs the
marathon's 52): subtype × severity × specialties × difficulty × 2 variants, with
the contract's `subtype_priors` overriding pinned drivers —
birth-injury/obstetric is forced catastrophic + 3-plus specialties, anchoring the
hard/high-cost stratum by construction.

Load-bearing properties, all validator-enforced (fail-closed):

1. **Every explicit driver level is observable.** 14 drivers per matter each emit
   a concrete snippet (caption defendant count, expert-disclosure count,
   demand-letter severity/life-care-plan language + record pages + demand amount,
   answer causation contest, scheduling-order deposition count + posture +
   affidavit/panel sentences, discovery-request interrogatory sets + ESI volume)
   recorded in `observable_driver_evidence`; the model rejects a matter whose
   evidence is missing, empty, or absent from the documents.
2. **Dollars deterministic, never stated.** Budgets come only from
   `build_explicit_canonical_profile` (new in `driver_taxonomy`: explicit
   canonical levels, fail-closed on unknown ids/levels) + the DT2 engine; the
   documents never contain the computed total (regex-guarded validator; injecting
   it is rejected). The demand letter states EXPOSURE, derived from the priced
   total and a seeded ratio held inside the med-mal reference band — observed
   corpus ratios 0.060–0.380 against the [0.03, 0.40] band.
3. **Anti-tautology + leak-proof holdout** (LW1 mechanisms): difficulty controls
   signal/distractor density (hard ≥2 distractors, clear 0); the 119/55
   train/holdout split is a seeded hash, digest-frozen, seed-bound.
4. **Byte-identical regeneration** — no timestamps anywhere in the artifacts;
   frozen corpus + manifest committed under `examples/synthetic/stratified/`
   with a regeneration script.

## Non-decision

- Nothing consumes the stratified corpus yet (the eval/probe upgrade to run on it
  is a natural later slice); LW1's corpus and consumers unchanged.
- `appeal_likelihood` is pinned "low" for every matter (no pre-disposition
  appellate signal exists to render); documented.
- All names/entities invented; no real person or matter implied.

## Evidence

`tests/test_stratified_corpus.py` — 11 tests: explicit-profile fail-closed;
deterministic regeneration; frozen↔regenerated match; stratification coverage
(7 subtypes × 3 difficulties, ≥150 matters, birth-injury pinned); observability
(+2 tamper rejections); budget recomputability (plan_id + total match); documents
never state the budget (+ injection rejected); holdout frozen + seed-bound;
manifest fail-closed (×2); reference-band ratios; difficulty/distractor shape.
DT1+DT2 suites green alongside (32 total).

## Alternatives rejected

- **Random sampling at higher N.** Rejected: the spec demands deliberate cell
  coverage; randomness reproduces the marathon's saturation/imbalance problems.
- **Extending `GeneratedSyntheticCase` (LW1).** Rejected: v2's shape (documents,
  evidence map, canonical budget) differs structurally; churning the frozen LW1
  corpus and its consumers would violate the frozen-corpus discipline.
- **Stating budgets in documents for realism.** Prohibited: dollars are computed
  downstream only; the validator enforces their absence.

## Validation

DT4 11/11 + DT1/DT2 21 green; ruff check + format clean; `export_schemas` (+2:
stratified-synthetic-matter, stratified-corpus-manifest; 530 total). Full local
CI reproduction run bare on the committed tree, marker-verified, before merge.
No UI change.

## Human gate

Owner pre-authorized squash-merge on green local CI for this slice sequence.
Substrate spec promotion remains open.

## DAD

Preflight/lesson/asset-use/midflight-acks/postflight recorded.
