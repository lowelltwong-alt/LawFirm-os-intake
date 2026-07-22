# PLAN: Public-Data → Synthetic-Silver Intake-to-Budget Loop with Governed Self-Improvement

Status: GROUNDING SCAFFOLD (not the plan of record). Candidate-only,
synthetic-only, human-gated. Author: Claude (Opus 4.8). Date: 2026-07-21.
Target executor: Opus 4.8 (medium) marathon.

> This document is **input** for Fable's full-project plan of record. Fable is
> asked to plan Phase 0 **through project completion** — see
> `FABLE_PLANNING_BRIEF_public_synthetic_silver.md`. The phases and the "thin
> first slice" here are a starting structure and a *first increment*
> suggestion, not a scope cap. Fable may restructure freely.

## 0. One-paragraph objective

Stand up the existing intake→budget workflow end-to-end; feed it **synthetic
intake documents derived from public data** (via the synthetic world builder and
the already-present public-derived-synthetic gate chain); and design **governed
self-improvement learning loops** whose only available evaluation standard is
**synthetic silver** (reviewed synthetic expected-outputs), because no gold
(reviewed real historical outcomes) exists. Nothing here trains a predictive
model, mutates a profile/template/guideline, submits a budget, opens a matter,
writes to the Lake/SQLite, or applies learning without a human gate.

## 1. What already exists — build on it, do not rebuild

Grounding read of `src/lawfirm_os_intake/` and `docs/roadmap.md`:

- Intake→budget spine: intake → preflight (`workflow.run_preflight`) → human
  confirmation (`confirmation`) → budget proposal (`workflow.run_budget`) →
  budget-input workbench → actuals comparison (`budget_actuals`) → carrier
  rejection capture/review/learning (`carrier_rejections`,
  `carrier_rejection_review`, `carrier_rejection_learning`).
- Public data → synthetic: `public_derived_synthetic_qa_gate.py` +
  `PublicDataCacheAuditReport`; roadmap §18 "Public Source Methodology Audit".
  Its required gates already name the whole safe path: public-source methodology
  review → public-synthetic conversion review → append-only conversion outcome →
  separate synthetic-fixture-generation PR → synthetic-fixture gold review →
  red-team identity-reconstruction review → public-cache custody review.
- ~~Synthetic world builder pieces: `synthetic_factory.py`, `synthetic_research.py`,
  `synthetic_campaign.py`, `synthetic_qa.py`.~~ **CORRECTION (2026-07-21, Codex
  review):** these modules do NOT exist in the real repo — they were read from the
  stale top-level folder. World Builder is greenfield. See
  `CONVERGED_PLAN_OF_RECORD.md`.
- Evaluation standard: `gold.py` (`FixtureGoldReport`/`FixtureGoldSpec`) and
  `labor_employment_budget_fact_gold.py` — the mechanism exists but there is no
  gold data.
- Learning-loop pipeline (all human-gated): `budget_learning_loop.py`,
  `reviewed_learning_gate.py`, `learning_shadow_eval_results.py` /
  `learning_shadow_eval_fixture_results.py`, `learning_proposed_changes.py`,
  `learning_promotion_readiness.py`, `learning_owner_handoffs.py`.
- Calibration corpus / replay (roadmap §19): `budget_calibration_corpus.py`,
  `budget_calibration_readiness.py`, `budget_corpus_replay*.py`, plus the L&E
  outcome-replay chain (seeds → readiness → execution → builder-binding →
  input-pack → confidence-status). The current slice already made all 8 L&E
  families executable and the two workbench trust gaps fail-closed.
- DAD front door: `.digital-asset/` (mailbox-only under `.digital-asset/mail/**`;
  DAD graph surfaces via the `dad-local-graph-surfaces` MCP). Do not edit DAD
  directly.

Implication: this plan is mostly **wiring + one new evaluation tier (silver) +
loop governance design**, not greenfield.

## 2. The synthetic-silver idea — RECONCILED with the DAD program (2026-07-21)

Canonical source (now in the DAD hub, merged via PR #72):
`04_Digital_Assett_Directory/docs/SYNTHETIC_SILVER_PROGRAM.md`; program id
`synthetic-silver`; registry `registry/synthetic-silver-program-registry.json`;
schemas `synthetic-silver-{program-registry,provenance-record,release-manifest}.schema.json`.
This section is reconciled to that contract. Where my earlier draft differed, the
DAD contract wins.

DAD definition: *"Use synthetic silver to move a corpus; use human gold to
measure the silver; use immutable primary sources to correct both."* A versioned
synthetic-silver corpus is a large, automatically produced approximation of a
desired corpus state, with explicit provenance, hard deterministic validators,
calibrated model judging, stratified human audit, and versioned releases measured
against an **untouched human-gold holdout**.

Tier ladder (maps onto DAD candidate → reviewed → promoted):

| Tier | Name | Lifecycle | Required control |
|---|---|---|---|
| S0 | raw_synthetic | candidate | provenance record |
| S1 | machine_filtered | candidate | hard validators passed |
| S2 | calibrated_silver | candidate | **gold-anchor calibration** + active audit |
| S3 | human_sampled_silver | reviewed | stratified human audit |
| G1 | human_adjudicated | reviewed | qualified human review |
| G2 | authoritative | promoted | explicit human promotion via DAD gates |

Movement above S3 always requires a human decision; no metric, judge score, or
agreement rate promotes an artifact on its own.

CORRECTIONS TO MY EARLIER DRAFT (each changes the plan):
1. **Gold is not "gone"; it is the measuring holdout.** With no gold anchor yet,
   this program is **capped at S0/S1** (candidate; deterministic validators only).
   S2 "calibrated_silver" *requires* a gold anchor + untouched holdout. So the
   first human task is to stand up a *small* human-gold anchor/holdout — not to
   skip gold. "No gold" caps the tier; it does not delete the requirement.
2. **Contract plane vs factory plane.** DAD owns only the contract (doc,
   registry, the two record schemas, tier policy, adapters). The **factory**
   (generators, validators, judges, corpora, gold sets, releases, thresholds)
   lives in the domain repo and emits the DAD-registered
   `synthetic-silver-provenance-record` (per item) and
   `synthetic-silver-release-manifest` (per release) shapes. DAD never stores
   corpus content.
3. **The law-firm silver factory is pointed at the LawFirm Sim / litigation
   world** via `adapter:law-firm-sim` + `adapter:litigation-corpus-factory`
   (sovereignty_child_pointers): the deterministic kernel owns world truth and
   generative workers are **proposal-only (JobManifest/JobResult)**. OPEN: does
   the intake→budget silver factory live in the litigation world, in intake, or
   as a new binding? Confirm before building.
4. **Your "synthetic world builder" = `adapter:world-builder`, currently
   `target_unresolved` / proposed.** DAD's backlog says verbatim: "Confirm the
   World Builder target repository identity and bind adapter:world-builder or
   retire it." That confirmation is a Phase-0 human action and a hard dependency.
5. **14 non-negotiable controls apply verbatim** (canonical source never
   overwritten; gold holdout excluded from prompts/examples/tuning/threshold-
   selection/training; no model both generates and solely certifies; prompt
   variants of one model family are correlated, not independent votes;
   deterministic validators before any model judging; critical errors are binary
   gates that rubric scores cannot compensate; synthetic-only never establishes
   real-world readiness). These supersede any looser wording elsewhere here.
6. Drop "bronze" — not a DAD term. Use S0/S1 for unreviewed / machine-filtered.

## 3. Phases

### Phase 0 — Verify running + reconcile silver (no new behavior)
1. Run the workflow end-to-end on existing synthetic fixtures: `bash
   scripts/smoke_demo.sh`; confirm the CLI chain in `ENDPOINTS_AND_COMMANDS.md`.
2. Pull the DAD "synthetic silver" definition + company research via the DAD
   graph surfaces / mailbox front door; write a one-page reconciliation vs §2.
3. Inventory public-data sources that are *safe* (no re-identification): e.g.
   published agency guidance, court-rule fee schedules, public docket structure,
   published rate surveys — availability is uncertain ("if available"); record a
   go/no-go per source with the §18 methodology gate.
Acceptance: workflow runs green locally; silver definition reconciled and
signed off by Fable; a vetted public-source list (or an explicit "none yet").

### Phase 1 — Public data → synthetic intake (world builder)
1. Extend the synthetic world builder to emit intake bundles from a vetted public
   source through `public_derived_synthetic_qa_gate`: each bundle carries
   `data_origin=synthetic`, generator version + deterministic seed, source refs +
   segment offsets + hashes, explicit unknowns/blocked gates, and passes the
   red-team identity-reconstruction + cache-custody reviews.
2. Feed generated bundles through intake→preflight→confirmation→budget→actuals→
   carrier, reusing the L&E replay-input contract already in the repo.
Acceptance: N synthetic public-derived intake bundles reach a budget output
state through the governed gate chain; zero real/PII leakage (red-team pass);
holdout content excluded from any model-visible prompt assembly.

### Phase 2 — Synthetic-silver standard (evaluation without gold)
1. Add a **silver tier** alongside `gold.py`: `FixtureSilverSpec`/`SilverReport`
   (or a `tier: silver` on the existing gold models) with mandatory fields:
   provenance, generator+seed, reviewer id, confidence/uncertainty, applicability
   and non-applicability, and an explicit "not gold / not calibration evidence"
   marker.
2. For each synthetic case, author silver labels for the observable outputs the
   pipeline already produces: expected budget output state (blocked / range-or-
   hours-only / candidate-range), expected variance posture, expected exception
   labels, expected blocked/widened reasons. Human-review once; version them.
3. Wire silver into the existing shadow-eval machinery
   (`learning_shadow_eval_results`) as the eval target when gold is absent, with
   silver-vs-bronze never conflated.
Acceptance: a versioned silver label set; a silver-eval report that scores
pipeline outputs against silver with uncertainty; a red-team check that silver
cannot be silently promoted to gold or to calibration authority.

### Phase 3 — Governed self-improvement learning loops
1. Design candidate loops over replay outcomes vs silver, reusing the existing
   `expected_learning_targets`: budget-driver drift, template mapping, UTBMS code
   mapping, scenario range width, carrier-guideline mapping, source-capture
   completeness.
2. Each loop is **proposal-only**: replay → shadow-eval-against-silver →
   `reviewed_learning_gate` → `learning_promotion_readiness` →
   `learning_owner_handoffs`. Enforce prohibited transitions (no silent learning,
   no profile/template/guideline mutation, no submission/matter-opening/Lake/
   SQLite write) as hard invariants with counterfactual + metamorphic guardrail
   tests (a loop that would degrade silver-eval or cross a boundary must fail
   closed).
3. Self-improvement = the loop *proposes* a candidate change and *proves* (under
   silver-eval + shadow-eval) it would not regress, then stops at the human gate.
   It never self-applies.
Acceptance: each loop emits a candidate change package that is blocked at the
reviewed-learning gate with observable evidence; a deliberately regressive
candidate is rejected by silver shadow-eval; no boundary crossing in any path.

### Phase 4 — Marathon harness + guardrails
Deterministic seeds; per-iteration decision trace; DAD candidate lesson packets
(observable evidence, assumptions, applicability, non-applicability, danger if
misapplied, no hidden chain-of-thought); fresh `claude/` branch; no push to
protected branches; the repo's full validation gate green each iteration.

## 4. Hard boundaries (unchanged from platform canon)
No real matter/client/rate/carrier/public-case payload data. No predictive-model
training or tuning (XGBoost stays a *later* governed slice needing reviewed real
historical outcomes, temporal splits, leakage checks, prediction intervals, SHAP,
and a deterministic baseline challenger — synthetic silver may exercise feature-
shape and pipeline behavior only). No profile/template/guideline mutation, budget
submission, matter opening, conflict conclusion, Lake/SQLite/external writes, or
silent learning. No canonical Semantic Substrate / Orchestrator persistence
changes. DAD via the governed front door only.

## 5. Open questions for Fable
1. RESOLVED — the canonical DAD "synthetic silver" definition is now in the hub
   (PR #72) and reconciled into §2. Remaining bindings below.
2. **Gold anchor:** stand up a small human-gold anchor + untouched holdout so the
   program can pass S1 (without it, silver is capped at S0/S1). Who adjudicates it?
3. **World Builder binding:** confirm the repo identity for `adapter:world-builder`
   (currently `target_unresolved`) and bind it — or retire it. Hard dependency.
4. **Factory location:** does the intake→budget silver factory live in the
   LawFirm Sim / litigation world (per `adapter:law-firm-sim` /
   `adapter:litigation-corpus-factory`), in intake, or as a new binding?
5. Which public sources are actually available and cleared (Phase 0 go/no-go)?
6. Silver factory must emit the two DAD schemas (`provenance-record`,
   `release-manifest`) — where do those artifacts live vs. the calibration-corpus
   artifacts, and does silver reuse `gold.py`/shadow-eval or a new `silver.py`?
7. First-loop scope: one thin slice (recommend budget-driver drift) to prove the
   governance before breadth.

## 6. Recommended first marathon slice (thin, provable)
Phase 0 fully + Phase 1 for one family + Phase 2 silver for that family's budget
output state + Phase 3 for **one** loop (budget-driver drift), blocked at the
reviewed-learning gate. Prove the governance skeleton before breadth.
