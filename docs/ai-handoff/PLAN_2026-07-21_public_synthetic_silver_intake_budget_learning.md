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
- Synthetic world builder pieces: `synthetic_factory.py`, `synthetic_research.py`,
  `synthetic_campaign.py`, `synthetic_qa.py`.
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

## 2. The synthetic-silver idea (define, then reconcile with DAD)

Working definition (to be reconciled against the DAD repo's canonical "synthetic
silver" note and its company research in Phase 0 — do NOT ship on my definition):

- **Gold** = reviewed *real* historical outcome (ground truth). Unavailable here.
- **Silver** = reviewed *synthetic* expected-output label: a human-reviewed,
  versioned, provenance-bound expectation for a synthetic case, explicitly weaker
  than gold. Usable for pipeline/behavior evaluation and loop-governance
  rehearsal, **not** for predictive-calibration claims.
- **Bronze** = unreviewed generated output. Never self-certifies; never an eval
  label.

Real-world basis (general, not a DAD citation): silver-standard corpora and
weak/distant supervision — automatically or synthetically generated labels used
as a proxy when gold is scarce. Phase 0 must pull the DAD repo's specific
definition, guarantees, and the named companies/research it cites, and reconcile
any differences before Phase 2 builds on it. If the DAD note conflicts with this
working definition, the DAD note wins.

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
1. The canonical DAD "synthetic silver" definition + which company research it
   cites — does §2 match it?
2. Which public sources are actually available and cleared (Phase 0 go/no-go)?
3. Silver as a new tier on `gold.py` vs a separate `silver.py` module?
4. Loop scope for the first marathon: all six learning targets or a single
   thin-slice (recommend one: budget-driver drift) to prove the governance first?
5. Where do silver labels and loop candidate packages live relative to the
   existing calibration-corpus artifacts?

## 6. Recommended first marathon slice (thin, provable)
Phase 0 fully + Phase 1 for one family + Phase 2 silver for that family's budget
output state + Phase 3 for **one** loop (budget-driver drift), blocked at the
reviewed-learning gate. Prove the governance skeleton before breadth.
