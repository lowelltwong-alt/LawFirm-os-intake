# Fable Planning Brief — Full Plan of Record (Phase 0 → Completion)

Paste the block below into a **Fable** session. Fable's job here is to PLAN the
whole project end to end, not to implement it and not to stop at Phase 0.

---

You are producing the **plan of record** for a project in the
`lowelltwong-alt/LawFirm-os-intake` repo. Plan it **end to end — from Phase 0
through project completion** — not a single phase and not a thin slice. Do not
write production code in this session; produce the plan.

PROJECT GOAL: Run the intake→budget workflow on **synthetic intake documents
derived from public data** (via the synthetic world builder and the existing
public-derived-synthetic gate chain), and stand up **governed self-improvement
learning loops** evaluated against a **synthetic-silver** standard (reviewed
synthetic expected-outputs), because no gold (reviewed real historical outcomes)
exists. Everything stays candidate-only, synthetic-only, and human-gated.

READ FOR GROUNDING (do not treat as the plan; restructure freely):
1. `docs/ai-handoff/PLAN_2026-07-21_public_synthetic_silver_intake_budget_learning.md`
   — my grounded scaffold (objective, what-already-exists inventory, phases,
   boundaries, open questions). Expand it into the real plan of record.
2. `docs/ai-handoff/MARATHON_GOAL_PROMPT_public_synthetic_silver.md` — how an
   Opus 4.8 (medium) executor will consume your plan.
3. `docs/roadmap.md` §18 (public source methodology) and §19 (calibration corpus);
   `src/lawfirm_os_intake/public_derived_synthetic_qa_gate.py`, `gold.py`,
   `reviewed_learning_gate.py`, `learning_shadow_eval_results.py`,
   `budget_learning_loop.py`, `learning_promotion_readiness.py`.
4. **The canonical DAD synthetic-silver program (now in the hub, PR #72):**
   `04_Digital_Assett_Directory/docs/SYNTHETIC_SILVER_PROGRAM.md`, its registry,
   and the three schemas. Plan §2 is already reconciled to it: adopt the
   S0-S3/G1-G2 tier ladder, the contract-plane (DAD) vs factory-plane (this repo)
   split, the `provenance-record` + `release-manifest` record schemas, and the 14
   non-negotiable controls. Key constraint: **with no human-gold anchor yet the
   program is capped at tier S1** — S2 "calibrated_silver" requires a gold anchor.

REQUIRED PHASE-0 DECISIONS (blocking — resolve each through a human gate before
any factory build; every downstream milestone depends on these):
A. **World Builder adapter binding — DIRECTION SET (owner decision 2026-07-21).**
   The World Builder is a **new, separate, modular repo**
   (`lawfirm-synthetic-world-builder`), not a fold-in to intake or Law Firm Sim.
   It works *with* Law Firm Sim as proposal-only JobManifest/JobResult producers
   on top of that deterministic kernel, builds *multiple* law-firm-document
   "worlds", emits the DAD provenance-record/release-manifest, and feeds intake.
   Plan the repo scope, the world-definition interface, its DAD enrollment (own
   wave), and the sequencing to bind `adapter:world-builder`. Details +
   candidate adapter entry: `docs/ai-handoff/WORLD_BUILDER_BINDING_RECOMMENDATION.md`.
B. **Gold anchor + untouched holdout — DELEGATED TO FABLE (owner deferred).**
   No *internal* gold exists (the firm will not release budgets until delivery),
   so the program is capped at S1 until a small human-adjudicated gold anchor +
   untouched holdout exist (excluded from prompts, examples, tuning, threshold
   selection, training). **Fable: recommend the first gold-anchor task** —
   options are (i) litigation-corpus foundation (1 case, ~80–150 artifacts, Law
   Firm Sim), (ii) intake→budget output states, (iii) document chunking (DAD's
   recommended deterministic first pilot), (iv) defer and run S0/S1 only, or
   **(v) the public-adjudicated fee corpus** — court-adjudicated real budgets and
   fee outcomes from the public record (large Chapter 11 budgets/staffing plans
   under the UST Appendix B guidelines with fee-examiner budget-vs-actual
   reports; fee-shifting award opinions; independent-counsel rate adjudications
   and public risk-pool rate standards for insurance defense) used as
   *reference-class dollar gold*, per
   `docs/ai-handoff/PUBLIC_GOLD_STRATEGY_legal_budgets.md` (web-verified,
   routed to DAD). Note the two-layer gold split in that doc: process gold
   (output states, synthetic) vs reference-class dollar gold (public,
   adjudicated) — (ii) and (v) are complementary, not competing. Ingestion of
   (v) must ride the roadmap §18 public-source gate chain.
C. **Factory location** — mostly resolved by A: the World Builder repo is the
   corpus factory; intake is a consumer and its own silver factory for budget
   outputs. Confirm this split and whether the litigation-corpus lane
   (`adapter:litigation-corpus-factory`) is in scope for the first increment.

PRODUCE A PLAN OF RECORD WITH:
1. **Definition of "done" for the whole project** — the observable end state that
   means the project is complete (and what is explicitly out of scope / deferred).
2. **Milestone breakdown, Phase 0 → completion.** For each milestone: objective;
   concrete work items; the modules/files it touches; upstream dependencies; the
   human gate(s) it must stop at; acceptance criteria (executable where possible);
   rollback / stop conditions; and its exit artifact.
3. **End-to-end sequencing / critical path** across all milestones, with which
   run in parallel vs. must be serial, and where each human gate sits.
4. **Cross-cutting tracks** carried through every milestone: governance gates,
   the synthetic-silver definition reconciliation with DAD, the public-data
   go/no-go per source, the XGBoost / calibration boundary, and DAD front-door
   usage.
5. **Risk register** — top risks with likelihood/impact and a mitigation or
   detection for each (include: silver silently promoted to gold; public-data
   re-identification; loop degrading eval; boundary creep into real data/training;
   concurrent-agent collisions).
6. **Open decisions to resolve** (answer where you can from the repo/DAD; flag
   the rest): the canonical DAD "synthetic silver" definition + its cited company
   research; which public sources are available and cleared; silver as a new tier
   on `gold.py` vs a `silver.py`; first-loop scope; where silver labels and loop
   candidate packages live vs. the calibration-corpus artifacts.
7. **Recommended increment order** — how to slice the full arc into marathon-sized
   PRs an Opus 4.8 (medium) executor can ship one gate at a time, with the first
   increment called out. This is sequencing *within* the full plan, not a
   substitute for it.

HARD BOUNDARIES the plan must respect (call out any milestone that would touch
one, and route it through a human gate): no real matter/client/rate/carrier/
public-case payload data; no predictive-model training/tuning (XGBoost is a later
governed slice needing reviewed real historical outcomes; synthetic silver is for
pipeline/behavior evaluation only); no profile/template/guideline mutation,
budget submission, matter opening, conflict conclusion, Lake/SQLite/external
write, or silent learning; no canonical Semantic Substrate / Orchestrator
persistence changes; DAD via the governed front door only. If the DAD "synthetic
silver" definition conflicts with the scaffold, the DAD definition wins — surface
the conflict in the plan.

DELIVERABLE: a single plan-of-record document (Phase 0 → completion) plus a
one-page executive summary and the open-decisions list, ready to hand to the
Opus 4.8 (medium) marathon executor.

---
