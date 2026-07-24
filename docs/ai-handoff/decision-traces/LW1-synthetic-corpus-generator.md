# Decision Trace — LW1 Scaled Synthetic Corpus Generator (World-Builder-lite)

Wave: LW1 of the Synthetic Learning-Loop marathon. Branch:
`claude/lw1-synthetic-corpus-generator`, stacked on the LW0 branch. Candidate-only,
synthetic-only, deterministic.

## Situation

LW2/LW3 need a labeled corpus to evaluate routing/driver recovery and to train the
shadow ML probe. The premortem (P1) flagged the existing routing fixture factory as
tautological: it renders doc text directly from the same `MATTER_SIGNALS` terms
`classify_matter` scores, so corpus routing accuracy would be ~100% by
construction and every captured "improvement" would be noise.

## Pre-execution bindings (from the plan premortem)

- **P1 (tautology)** — the generator carries a declared difficulty model and emits
  `signal_terms_used` / `distractor_terms_used` so LW2 can stratify and mark
  saturated strata non-informative.
- **P2 (holdout leak)** — the train/holdout split is assigned at generation time by
  a seeded hash of `case_id` and digest-frozen in the manifest, so LW3 cannot leak
  across it.
- **P9 / P10 / P11** — seeded determinism with byte-identical regeneration; N frozen
  in-repo (52), larger corpora reproducible to scratch only; money exact minor units.

## Decision

An additive `synthetic_corpus_generator` module:

1. **Difficulty model** — signal density 3/2/1 genuine terms for
   `clear`/`moderate`/`hard`, plus 0/1/2 distractor-family terms, over four
   doc-noise variants (`clean`, `mixed_signals`, `quoted_thread_noise`,
   `injection_as_text`) that participate in the difficulty axis, plus one
   `missing_attachment` case per family (abstain-by-construction).
2. **Ground-truth case-spec** — each case carries family, difficulty, variant,
   expected route/abstain decision (construction intent), case_type, sampled
   drivers, exposure (minor units), base work-plan (minor units), and a
   `reference_class_band_id` from `config/synthetic-reference-class-bands.yaml`
   (a new declared synthetic band policy — P4, loaded fail-closed by LW2).
3. **Determinism + frozen split** — a seeded `random.Random("{seed}:{case_id}")`
   per case; a content digest per case; a corpus digest over the sorted case
   digests and a holdout-split digest over the sorted `(case_id, split)` pairs;
   the split via `sha256("{seed}:{case_id}") % 100 < holdout_percent`.
4. **Label integrity (fail-closed)** — `GeneratedSyntheticCase` validates that a
   clear case uses ≥1 genuine term, the injection line is flagged and carries no
   genuine terms, a missing-attachment case expects abstention, and distractor
   terms are disjoint from genuine terms. `SyntheticCorpusManifest` recomputes all
   counts and both digests fail-closed.
5. **Frozen artifacts** — `examples/synthetic/corpus/corpus_cases.json` +
   `corpus_manifest.json` (N=52), reproducible by
   `scripts/generate_synthetic_corpus.py`.

## Result

N=52 (13 per family × 4 families), 37 train / 15 holdout. Regeneration is
byte-identical (corpus + split digests). Crucially, the difficulty model is **not
tautological**: on `hard` cases the deterministic router disagrees with the
ground-truth family (routes to a distractor or abstains) — e.g. a hard
discrimination case routes to the `wage_hour_flsa_state` distractor — so LW2's
routing/abstention metrics will be genuinely informative rather than saturated.

## Non-decision

- No ML here; no new repo (single in-repo module, P10).
- No change to `classify_matter`, `route_decision`, or the LW0 pipeline.
- No real data; corpus is 100% synthetic candidate content.

## Authority impact

Local candidate work; two new candidate schemas (`generated-synthetic-case`,
`synthetic-corpus-manifest`), one new synthetic band config, one frozen corpus, one
regeneration script. No canonical/promoted contract change; no cross-repo write.

## Evidence

- `tests/test_synthetic_corpus_generator.py` — 10 tests (failing-test-first):
  regeneration determinism; frozen-corpus↔regeneration match; manifest
  reconciliation fail-closed; holdout stability + seed-boundness (P2);
  **difficulty non-tautology** (hard cases produce router disagreement — P1);
  clear-case genuine-signal integrity; injection-line flagging; missing-attachment
  abstention; tampered-case rejection; pinned default seed.

## Alternatives rejected

- **Reuse the CW4 factory verbatim.** Rejected (P1): its text is drawn from the
  same signals the router scores → tautological accuracy.
- **Random train/holdout split at eval time.** Rejected (P2): the split is frozen
  at generation by a seeded hash so the ML probe cannot leak across it.
- **Bands from `benchmarks.py`.** Rejected (P4): `benchmarks.py` is a rate-benchmark
  replay auditor; reference-class bands are a new declared config policy.

## Risks and rollback

- Risk: the difficulty gradient is synthetic and not firm-tuned. Contained by
  candidate status and the generator + label-integrity review gate. Rollback is a
  single-branch revert; the module and corpus are additive.

## Validation

`validate_repo.py` passed; `export_schemas.py` idempotent (two new schemas); ruff
check + format clean; `run_full_pytest.py` full suite green; smoke demo green. No
UI change this wave.

## Human gate

LW1 human gate: **generator + label-integrity review**. Opened by the agent; it
does not merge its own PR and does not push `main`.

## DAD

Per-wave preflight/midflight/lesson/asset-use/postflight through the daemon-era
`asset-dir` pipeline.
