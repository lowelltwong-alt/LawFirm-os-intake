# Independent Review Prompt — Second Architect On The Budget-ML Program

Paste the block below into a fresh model/mode (Fable, or a different provider for
true independence). Give it repo read access to `LawFirm-os-intake`. Its job is to
disagree where warranted and propose its own design — not to confirm.

---

You are an independent second architect. Another AI (Opus 4.8) designed a program
and then red-teamed its own design. **Judge both independently. Do not assume
either the proposal or its self-critique is correct.** I want divergence, not
confirmation: tell me what the first AI got wrong in *both* directions — problems
it invented that aren't real, and problems it missed. If you think the whole
approach is misguided, say so and give the alternative.

## Context (ground truth)
- A solo builder is creating an intake→budget system to pitch to a law firm. The
  firm does insurance-defense / EPLI / labor-&-employment work. The firm will NOT
  release its own budgets/rates until the tool is delivered — so there is **no
  internal gold** for training or calibration until after v1 ships.
- Goal: (1) a deterministic intake→budget engine; (2) a "Carrier Guideline
  Engine" that applies dozens of carriers' billing guidelines as overlays — rate
  caps by state × role, task-hour allowances per role (how many hours a
  partner/associate/paralegal may bill per task), staffing/expense/preapproval
  rules; (3) a firm-adaptation layer (any firm loads its own rates); (4) ML that
  predicts budgets/variance/rejection; (5) an HTML UI. All synthetic-first,
  candidate-only, human-gated.
- Governance context: this repo integrates with a "DAD" hub that defines a
  **synthetic-silver program** (gold measures silver; tiers S0–S3/G1–G2;
  contract-plane in DAD, factory-plane in domain repos) and a **portfolio WIP
  policy of `maximum_active_family_builds: 1`**. A roadmap §21 fail-closed rule
  says: "do not train on the synthetic corpus and describe the result as
  calibrated," and training waits for governed reviewed historical outcomes.

## Read (then reason from the actual code, not summaries)
- `docs/ai-handoff/PLAN_2026-07-21_public_synthetic_silver_intake_budget_learning.md`
- `docs/ai-handoff/MARATHON_PROGRAM_waves_and_prompts.md` (the W0–W9 program)
- `docs/ai-handoff/PUBLIC_GOLD_STRATEGY_legal_budgets.md` (the training-data thesis)
- `docs/ai-handoff/CONVERGENCE_REVIEW_redteam_premortem.md` (the first AI's
  self-critique — attack this too)
- `docs/ai-handoff/WORLD_BUILDER_BINDING_RECOMMENDATION.md`
- `docs/roadmap.md` §18, §19, §21, §22, §23
- Ground the guideline claims in the real code: `src/lawfirm_os_intake/guidelines.py`
  and `config/synthetic-carrier-guideline.yaml` (what the v1 engine already does),
  and `config/synthetic-carrier-rate-card.yaml`.

## The questions I most need a second opinion on
1. **The gold thesis.** The plan trains a budget tool on public court-adjudicated
   fee data. The self-critique (RT1/RT2) says the budget-shaped gold (large
   Chapter 11 fee applications) is off-domain vs insurance defense, the on-domain
   sources are rate-only, and ~99% court approval makes adjudicated totals a weak
   quality signal. Is that critique right? Is there a *valid* way to use public
   data to train or calibrate a budget tool for this firm's domain — or should the
   ML ambition be cut back, and if so to what exactly?
2. **Sequencing.** The self-critique says lead with the deterministic Carrier
   Guideline Engine (needs no gold) and defer the ML. Agree? Or is there a better
   first deliverable that de-risks the firm pitch faster?
3. **Build-vs-simplify.** Is a full "dozens of carrier guidelines as versioned
   rule packs with an overlay compiler and ambiguity register" the right
   ambition, or is it over-engineered for a pre-firm pitch? What is the smallest
   thing that would prove value to the firm?
4. **The synthetic-first bet.** Everything is synthetic until delivery, with no
   firm feedback loop. Is that the right risk posture, or a trap?
5. **World Builder** as a new repo vs. generalizing the existing litigation-world
   kernel — which, given a solo owner and WIP=1?

## Deliverable
1. An independent verdict: is convergence necessary before executing, and where
   does your assessment differ from the first AI's?
2. A ranked list of what you would change, each with the evidence/reasoning.
3. A concrete alternative design for the parts you would do differently —
   specific enough to act on (schemas, sequencing, what to build first, what to
   cut). Where you agree with the first AI, say so briefly and move on.
4. Your own premortem: the top 3 ways this fails that the first AI did not name.

Respect the hard constraints (candidate-only, synthetic-first, DAD WIP=1, DAD
contract/factory split, §18 ingestion gates, §21 training boundary, human gates,
no real client/rate data without a production gate). Cite the files/sections you
rely on. Be specific and be willing to be blunt.

---
