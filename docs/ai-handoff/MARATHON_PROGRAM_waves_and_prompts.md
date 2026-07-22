# Marathon Program — Waves And Prompts To 100%, Training, And The Carrier Guideline Engine

Status: master multi-day/multi-week marathon program. Candidate-only,
synthetic-first, human-gated. Executors: Codex + Opus 4.8 (medium) per the
per-packet rules in `CODEX_MARATHON_RUNBOOK_synthetic_silver.md` (base off the
real repo at `.codex-worktrees/workbench-completion-v2`, one PR per milestone,
Linux CI is the authoritative gate, stop at every human gate).

## Program goal (the long-run objective)

1. Finish the current slice to 100% (trust parity, validation, PR).
2. Stand up the World Builder + synthetic-silver factory with a public-gold
   anchor (per `PUBLIC_GOLD_STRATEGY_legal_budgets.md`).
3. Train the budget tool (intervals, variance risk, rejection risk) against
   the public-gold holdout; capture the full workflow as learnable traces.
4. Build the **Carrier Guideline Engine v2**: dozens of carrier guideline
   packs applied as deterministic overlays — rate caps by state × role,
   **task-hour allowances per role** (how many hours a partner / associate /
   counsel / paralegal may bill per task), staffing rules, expense rules,
   preapproval triggers — versioned, effective-dated, with per-rule provenance.
5. Build the **Firm Adaptation Layer**: any law firm can load its own billing
   prices (state × office × role × timekeeper) and see them resolved under any
   carrier's guidelines. Real-rate import stays behind a production human gate.
6. Ship the HTML UI surfaces for all of it (read-only, candidate-only until
   production gates).

Hard boundaries (every wave): synthetic-first; no real client/matter data; no
real negotiated rates without the production import gate; public-source
ingestion only through roadmap §18 gates; no silent learning; no budget
submission/matter opening; all promotion through reviewed human gates; DAD
contract-plane untouched (records emitted, never written into DAD).

Current engine baseline (verified in repo): `guidelines.py` +
`config/synthetic-carrier-guideline.yaml` already do per-carrier rate caps by
role, expense caps by E-code, task-role overrides, max-timekeepers-per-event,
preapproval thresholds, variance percent, cadence/contingency — for 2 synthetic
carriers, unversioned, no task-hour allowances. The rate card is already
carrier × state × title. Waves 4–6 extend this; nothing starts from zero.

---

## Wave 0 — Close the current slice to 100%

Objective: every open item from the trust review closed; branch published; CI green.
Builds: F5 (rate-card override count — populate row-level
`named_timekeeper_override` flag from the YAML and reconcile the count; update
model + TS types + fixtures + exported schema), F6 (guideline + rejection
builders get the captured-snapshot + end-of-build unchanged-source check),
then full local gate + push branch + PR (human merges).
Evidence: failing-mutation tests first; full suite green locally AND on CI.
Human gate: PR review/merge of the accumulated branch.

PROMPT W0:
```
Work in the real repo (.codex-worktrees/workbench-completion-v2), fresh branch off
main after merging claude/le-replay-expansion. Read
docs/ai-handoff/CODEX_MARATHON_RUNBOOK_synthetic_silver.md Part 3b and the M0
packet corrections. Implement F5 by adding a named_timekeeper_override boolean to
SyntheticRateCardWorkbenchRow, populating it in synthetic_rate_card_workbench.py
from the YAML overrides, reconciling named_timekeeper_override_count to the rows
in the model validator and data-contract.ts, refreshing fixtures/schemas. Implement
F6 by giving build_synthetic_guideline_projection_workbench_report and
build_synthetic_rejection_appeal_workbench_report one captured source snapshot
(read each source exactly once), a source_inputs_unchanged_during_build check, and
monkeypatched mid-build-mutation tests mirroring
tests/test_synthetic_workbench_source_integrity.py. Failing tests first. Run the
full validation gate. Stop at the PR human gate.
```

## Wave 1 — World Builder repo + DAD binding

Objective: create `lawfirm-synthetic-world-builder` per
`WORLD_BUILDER_BINDING_RECOMMENDATION.md`; enroll in DAD; bind the adapter.
Builds: repo scaffold (world-definition interface, one example world =
intake-bundle world, deterministic validators, JobManifest/JobResult
proposal-only worker contract against Law Firm Sim, DAD front-door files,
silver `provenance-record`/`release-manifest` emitters), CI.
Human gates: repo creation + DAD enrollment approval id + hub registry edit
binding `adapter:world-builder`.

PROMPT W1:
```
Create the lawfirm-synthetic-world-builder repo per
docs/ai-handoff/WORLD_BUILDER_BINDING_RECOMMENDATION.md in LawFirm-os-intake.
Scaffold: a world-definition interface (world = corpus family with generators,
deterministic validators, seed policy, provenance emitter); one example world that
generates synthetic intake bundles compatible with LawFirm-os-intake replay-input
contracts; JobManifest/JobResult proposal-only worker shims for Law Firm Sim; DAD
front door (AGENTS.md, dad-integration stub); emitters for the DAD
synthetic-silver-provenance-record and release-manifest schemas (copy schemas
read-only from the DAD hub; validate golden examples in CI). Every artifact
data_origin=synthetic with generator version + deterministic seed. Stop at the
human gates: repo publication, DAD enrollment, adapter binding.
```

## Wave 2 — Public gold anchor (reference-class dollar gold)

Objective: the pilot anchor set from `PUBLIC_GOLD_STRATEGY_legal_budgets.md`.
Builds: §18 gate-chain run for the chosen sources; anchor extraction schema
(span-provenance per value); ~30–50 adjudicated outcomes (10 Ch.11 budgets w/
fee-examiner budget-vs-actual, 20 fee-shifting opinions, 5 insurance-defense
rate adjudications incl. risk-pool schedules); stratification; frozen untouched
holdout; DAD release manifest; owner adjudication session for the mapping.
Human gates: §18 methodology + conversion reviews; owner mapping adjudication;
holdout freeze.

PROMPT W2:
```
In LawFirm-os-intake, implement the public-gold pilot per
docs/ai-handoff/PUBLIC_GOLD_STRATEGY_legal_budgets.md. Build the anchor schema
(case family, forum, era, size band, phase/task allocations, rates by role,
requested vs adjudicated amounts, cut reasons, span-level source provenance) and
the §18 gate-chain artifacts for each source family before ingesting anything.
Extract 30-50 outcomes across the three strata. Freeze a stratified holdout
excluded from all prompts/tuning/training with an enforcement test (holdout ids
must never appear in prompt-assembly fixtures). Emit a DAD release manifest. Stop
for owner mapping adjudication and holdout freeze approval.
```

## Wave 3 — Silver factory to S2

Objective: World Builder silver corpus calibrated against the gold anchor.
Builds: S0 generation at scale (per-item provenance records), S1 deterministic
validators (schema, arithmetic, referential integrity, dedupe, distribution
sanity), S2 calibration: per-stratum distribution agreement (phase shares, rate
ranges, variance magnitudes, cut frequencies) vs the public anchor; calibration
report with uncertainty; stratified human audit sample for S3 candidates.
Human gates: S2 calibration review; S3 audit.

PROMPT W3:
```
In lawfirm-synthetic-world-builder, take the intake-bundle world to S2 per the DAD
synthetic-silver contract. Generate S0 with per-item provenance records; implement
S1 hard validators (fail-closed, retained rejects with reasons); implement S2
calibration comparing per-stratum distributions against the LawFirm-os-intake
public-gold anchor (never touching the holdout), emitting a calibration report
with explicit uncertainty and a release manifest. Prepare a stratified S3 human
audit sample. No numeric threshold without calibration evidence. Stop at the S2
review gate.
```

## Wave 4 — Carrier Guideline Engine v2 (the hard core)

Objective: dozens of carrier guideline packs as versioned deterministic overlays.
Builds:
- **Guideline Contract Schema (GCS) v2**, versioned + effective-dated, per
  carrier (and per program line, e.g. EPLI vs GL vs D&O): rate caps by
  state × role (+ experience band), **task-hour allowances** (UTBMS task ×
  role → max hours, occurrence caps, frequency rules), staffing rules
  (role-per-task, max timekeepers, partner:associate ratios), activity rules
  (block-billing bans, intra-office conference caps, travel %, research-hour
  caps), expense rules, preapproval triggers, variance thresholds, submission
  cadence/format. Every rule: `rule_id`, parameters, severity
  (hard_cap | review_trigger), and a source-span provenance ref.
- **Overlay compiler/resolver**: firm rate card + GCS pack + matter context →
  compliant projection with **per-rule delta attribution** (which rule cut
  what, extending CarrierCompliantProjection), plus an ambiguity register
  (rules that could not be applied deterministically go to human review —
  never silently guessed).
- **Overlay algebra**: precedence order (state-law overlay e.g. independent-
  counsel rate floors > client addendum > carrier program pack > carrier base
  pack > firm defaults); conflicts surfaced, never auto-resolved.
- **Pack registry at scale**: 8–12 synthetic carrier packs spanning realistic
  variation (strict/lenient caps, task-hour matrices, different preapproval
  regimes), golden tests per pack, differential tests (one budget across all
  packs), metamorphic tests (tighten any cap → compliant total monotonically
  non-increasing; add hours allowance → never decreases).
Human gate: GCS v2 schema review; pack-set review.

PROMPT W4:
```
In LawFirm-os-intake, build Carrier Guideline Engine v2 on top of guidelines.py
and config/synthetic-carrier-guideline.yaml (do not rewrite the v1 projection —
extend it). Design GCS v2 as a versioned, effective-dated, per-carrier/per-program
schema adding task-hour allowances (UTBMS task x role -> max hours/occurrence/
frequency), activity rules, staffing ratios, and severity + source-span provenance
per rule. Implement the overlay compiler producing per-rule delta attribution and
an ambiguity register that fails to human review. Implement overlay precedence
(state-law > client addendum > program pack > base pack > firm defaults) with
surfaced conflicts. Author 8-12 synthetic packs spanning realistic variation.
Tests: golden per pack, differential one-budget-across-all-packs, metamorphic
monotonicity (tightening any cap never increases the compliant total), and
failing-mutation trust tests on the new serialized artifacts (recompute per-rule
deltas; reject unattributed money movement). Export schemas; update the exported
TS data contract. Synthetic packs only; contains_real_carrier_guidelines=false
everywhere. Stop at the schema-review human gate.
```

## Wave 5 — Firm Adaptation Layer

Objective: any firm's billing prices, resolved under any carrier pack.
Builds: firm rate-card contract v2 (firm × office × state × role ×
named-timekeeper, versioned, effective-dated); governed import pipeline
(validation, provenance, `real_rate_import_allowed` stays false until an
explicit production human gate — synthetic/sandbox rate cards until then);
resolution preview API: rate card × carrier pack × state → resolved rates +
which cap bound + per-rule attribution; cross-carrier comparison matrix
(one firm rate card under all packs).
Human gate: firm-config contract review; the production real-rate import gate
is designed but NOT opened.

PROMPT W5:
```
In LawFirm-os-intake, build the Firm Adaptation Layer: a versioned firm rate-card
contract (firm/office/state/role/named-timekeeper with effective dates), a
governed import pipeline that validates + records provenance and keeps
real_rate_import_allowed=false behind a documented production human gate (sandbox
synthetic rate cards only until that gate), and a deterministic resolution preview:
firm rate card x GCS pack x state -> resolved rate per timekeeper with the binding
rule identified, plus a cross-carrier comparison matrix artifact. Property tests:
resolution is total (every line resolves or lands in the ambiguity register),
deterministic, and monotone in caps. Wire into the budget-input workbench as a
candidate-only alternate rate source clearly labeled synthetic/sandbox. Stop at the
contract-review human gate.
```

## Wave 6 — ML: guideline intake + budget training

Objective: the machine-learning layer, human-gated end to end.
Builds:
- **Guideline intake extraction**: model converts unstructured guideline
  documents → GCS v2 candidate packs, span-provenance per rule, per-rule
  confidence, mandatory human review queue (a pack is never active without
  100% rule-level human sign-off); eval = extraction agreement vs the
  synthetic packs used as reviewed gold (holdout packs excluded from prompts).
- **Rejection/reduction risk**: train on silver S2 rejections + carrier packs,
  calibrate against public-gold cut frequencies/magnitudes per stratum;
  predict per-line cut probability + expected reduction with intervals.
- **Budget intervals**: quantile/conformal phase-cost and variance-risk models
  on silver S2, evaluated only on the frozen public-gold holdout; deterministic
  baseline challenger first (LoPucki-style regression) per roadmap §21 gates
  (temporal splits, leakage checks, SHAP review, prediction intervals).
Human gates: reviewed-learning gate per model; no model output ever
auto-applies (proposal-only, same as all learning loops).

PROMPT W6:
```
Implement the ML layer across lawfirm-synthetic-world-builder and
LawFirm-os-intake honoring roadmap §21 and the reviewed-learning gates. (1)
Guideline-intake extraction: unstructured guideline text -> GCS v2 candidate pack
with span provenance and per-rule confidence; human review queue; eval on held-out
synthetic packs never present in prompts. (2) Per-line rejection/reduction risk:
features from GCS rules x budget lines; train on silver S2; calibrate against
public-gold cut statistics per stratum; report intervals. (3) Phase-cost interval
models with a deterministic regression baseline challenger, temporal splits,
leakage checks, SHAP review, evaluated only on the frozen public-gold holdout.
Every model emits a shadow-eval report through learning_shadow_eval_results and
stops at the reviewed-learning gate. No auto-application anywhere.
```

## Wave 7 — Workflow capture

Objective: the full intake→budget→guideline→actuals→rejection→appeal workflow
captured as replayable, learnable traces.
Builds: trace capture packets (every stage emits hashed inputs/outputs +
decisions + gate states into an append-only run ledger), replay determinism
tests (same trace → same artifacts), trace→learning-loop bridge (traces become
candidate learning evidence through the existing corpus/replay machinery §19).
Human gate: trace-schema review.

PROMPT W7:
```
In LawFirm-os-intake, formalize workflow capture: an append-only trace packet per
stage (intake, preflight, confirmation, budget, guideline overlay, actuals,
rejection, appeal) with hashed inputs/outputs, decision records, gate states, and
provenance, written to the local run ledger only. Add replay determinism tests
(identical trace inputs reproduce identical artifacts byte-for-byte where
generated_at is pinned) and a bridge that registers traces as candidate calibration
corpus entries through the §19 corpus/replay machinery. No Lake/SQLite/external
writes. Stop at the trace-schema human gate.
```

## Wave 8 — HTML UI

Objective: the human-facing surfaces for all of it, read-only candidate-only.
Builds (extend `apps/legal-intake-budget`): guideline pack explorer (rules,
provenance, versions, effective dates); overlay diff view (budget before/after
with per-rule attribution — every dollar cut names its rule); firm rate sandbox
(edit synthetic rate card, preview resolution under any carrier);
cross-carrier comparison matrix; training-eval dashboard (calibration plots,
holdout metrics, intervals); trace timeline viewer. All banners: synthetic-only,
candidate-only, human-review-required; TS data-contract assertions for every new
artifact; browser-smoke false-serialization cases per panel.

PROMPT W8:
```
Extend apps/legal-intake-budget with: a guideline pack explorer (rule table with
severity, parameters, source-span provenance, version/effective-date switcher); an
overlay diff view showing proposed vs compliant per line with per-rule delta
attribution; a firm rate-card sandbox (synthetic only) with live resolution
preview under a selected carrier pack and state; a cross-carrier comparison
matrix; a training-eval dashboard rendering calibration and holdout-interval
reports; and a workflow trace timeline. Every panel read-only candidate-only with
explicit synthetic banners. Add data-contract.ts assertions and ui-browser-smoke
false-serialization rejection cases for each new artifact. tsc strict + vite build
+ browser smoke green.
```

## Wave 9 — Hardening, eval, delivery

Objective: red-team the whole stack; produce the firm delivery packet.
Builds: hostile-fixture sweeps over GCS packs and firm rate cards (the same
mutation methodology as the workbench trust suite — every derived number
recomputed or attributed); differential fuzzing across packs; a delivery
packet for the firm (what it does, boundaries, what unlocks with firm data —
the internal-gold recalibration path); DAD candidate lesson packets per wave;
runbook/roadmap updates.
Human gate: delivery review — the moment the firm hands over budgets, the
recalibration lane (already designed in Wave 6) replaces the reference-class
anchor with firm gold.

PROMPT W9:
```
Red-team the guideline engine and firm layer with the workbench trust-suite
methodology: fresh hostile mutations against every serialized artifact (per-rule
deltas, resolved rates, comparison matrices, training reports) — every derived
number must be recomputed or rule-attributed, fail-closed. Differential-fuzz one
budget across all packs and assert monotonicity invariants. Produce the firm
delivery packet: capabilities, boundaries, synthetic/candidate status, the
§18-gated public-gold basis, and the firm-data recalibration path. Emit DAD
candidate lesson packets for the program's transferable lessons. Update
docs/roadmap.md statuses. Stop at the delivery review gate.
```

---

## Sequencing and parallelism

Critical path: W0 → W1 → (W2 ∥ W4) → W3 (needs W1+W2) → W5 (needs W4) →
W6 (needs W2+W3+W4) → W7 (anytime after W0, best after W4) → W8 (after W4/W5,
extended after W6/W7) → W9 last. W2 and W4 are independent and can run as
parallel marathon lanes. Each wave = one or more PR-sized packets under the
runbook's per-packet rules; every wave ends at a named human gate.

## DAD learning
Every wave emits its transferable lesson as a DAD candidate outbox packet
(metadata + pointer, template-conformant) so the lesson-graph ingests the whole
program over time.
