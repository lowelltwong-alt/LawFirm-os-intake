# Case Sizing, Routing, And Training Design — Layers, Economics, Honest Semantics

Status: adopted design (owner direction 2026-07-21: "layers, not N×M; Excel is an
exporter"). Extends `CONVERGED_PLAN_OF_RECORD.md` and `MODULAR_ARCHITECTURE.md`.
Verified against the real repo before writing: `drivers.py` + `BudgetDriverEffect`
(+ scaling tests), nonlinear templates with `posture`/`math_model`/`scenario_gates`
(`labor-employment-nonlinear-budget-templates.json`), five practice profiles
(`context/synthetic-profiles/`), and the existing routing flow (preflight emits
`matter_family_candidates` → human confirms `confirmed_matter_family`). Everything
below extends these; nothing starts from zero.

## 0. The layered pipeline (decision of record)

```
1. case_model        confirmed intake facts (type, parties, exposure, venue, posture)
2. case_sizing       proportionality + drivers -> right-sized work plan (hours by role/task)
3. firm_rates        hours x firm rate schedule -> WORK-PLAN TOTAL (immutable baseline)
4. carrier_overlays  stacked guideline packs -> reimbursement + exposure + flags
5. exporters         one renderer per format: firm-Excel | LEDES | PDF | HTML UI
```

Mass customization by **composition**: carrier = data pack, case type = sizing
profile, regime = profile pack ⇒ N+M+K maintained artifacts, never N×M×K
spreadsheets. Excel is exporter #1 (the firm's sanitized template shape), not the
tool. The budget core stays independent of the overlay compiler (converged rule).

## 1. Routing: synthetic intake docs → case type

Deterministic first, ML as shadow only:
- Extraction of routing facts (claim type, injury/harm, forum, parties, carrier/
  payer) with span provenance; deterministic rules propose
  `matter_family_candidates`; **typed ambiguity** (≥2 candidates or low evidence
  → human confirmation, exactly as the existing preflight/confirmation flow).
- **Training signal comes free from the generator**: every synthetic intake
  bundle is emitted WITH its ground-truth case-spec (family, drivers, exposure).
  Generator-knows-truth = supervised labels by construction. This is process
  gold (synthetic), legitimate under the silver program; it is NOT monetary
  calibration, so §21 is not implicated.
- Router evaluation: frozen synthetic holdout + adversarial set (mixed-signal
  docs, quoted-thread noise, missing attachments, prompt-injection-as-text).
  Metrics: accuracy per family, and **abstention correctness** — the router must
  know when NOT to route. An ML router runs only as a shadow challenger vs the
  deterministic rules; deterministic + human confirm remain the authority.

## 2. What makes same-type cases differ in cost (driver taxonomy)

A versioned `CaseCostDriver` contract; every driver declares: measurement (which
intake facts, provenance-bound), effect surface (which phase/task hours, or an
additive task block, or a gate), effect form (multiplier | additive | gate), and
its tests. Starter set (slip-and-fall/premises shown; generalizes):

| Driver | Effect surface (example) |
|---|---|
| party_count / co-defendants / cross-claims | multiplies L110/L310/L330 (each party ⇒ discovery + depo surface) |
| injury severity band (soft-tissue → surgical → catastrophic) | multiplies expert tasks (L130/L340/L420, E119) + damages workup |
| claimed damages / exposure band | gates trial-phase inclusion; drives proportionality (§3) |
| liability clarity (clear / disputed / comparative-fault) | disputed ⇒ more investigation + dispositive-motion work; clear ⇒ settle-lean plan |
| coverage posture (SIR, layers, coverage dispute) | adds coverage-analysis tasks; changes payer dynamics |
| venue (state/court, trial rate, ADR mandates) | multiplies motion/trial phases; adds mandated-conference tasks |
| discovery volume proxies (custodians, document band, medical-records volume) | multiplies L320/L140 |
| expert specialties needed (count) | additive per-specialty blocks + preapproval triggers |
| representative posture (single / class / collective) | template switch (already modeled by nonlinear scenario gates) |
| plaintiff-counsel profile (volume filer vs trial firm) [synthetic only] | shifts settle-vs-try priors |

Effects compose through the existing driver machinery (`BudgetDriverEffect`) and
the nonlinear template `math_model`/`tiered_phase_ids` — extend, don't reinvent.
Every driver ships **metamorphic tests**: +1 party ⇒ budget non-decreasing;
clear-liability plan ≤ disputed-liability plan; catastrophic ≥ soft-tissue; etc.

## 3. Proportionality + settlement economics (the $10k case / $50k budget problem)

Deterministic decision arithmetic, candidate-only, human-gated:
- Declared inputs (v1 synthetic, provenance-bound): exposure E, settlement value
  estimate S, defense-cost envelopes per posture, win-probability band p
  (a declared assumption in v1 — never a model output).
- Compare postures by **expected total cost of risk** (indemnity + defense):
  settle-now (S + minimal defense) vs defend-then-settle (S' + partial defense)
  vs try ((1−p)·E + full defense). Output: ranked postures + a **recommended
  posture** as a candidate for human review; the budget envelope is the defense
  cost of the recommended posture.
- **Proportionality gate**: budget-to-exposure ratio bands per case type. A $10k
  slip-and-fall with a $50k plan does not pass silently — it emits
  `blocked_disproportionate_budget` (typed, with the ratio and band) requiring a
  human override with a recorded reason; the default recommendation is the
  settle-lean plan. Some cases legitimately exceed bands (precedent risk,
  pattern litigation) — that is what the override-with-reason is for.
- This mirrors carrier economics (carriers minimize cost of risk), so the same
  arithmetic powers guideline-side reasonableness review.
- Eval: golden scenarios + metamorphic invariants (E↓ ⇒ recommended budget
  non-increasing; S ≪ defense cost ⇒ settle recommended; p↑ ⇒ try-posture cost ↓).

## 4. Insurance-defense economics vs white-shoe bespoke (regimes as packs)

An `EconomicRegimeProfile` layer — data, not code — selects per matter:
- **payer**: carrier vs corporate client vs self-insured;
- **rate source**: panel/negotiated schedule vs firm standard rates;
- **constraint packs**: carrier guideline packs vs corporate-client OCGs —
  structurally the SAME rule IR (corporate OCGs cap rates/staffing/expenses too),
  so the overlay engine generalizes for free;
- **proportionality policy**: cost-of-risk bands (insurance defense) vs
  strategic-stakes weighting (bespoke: declared reputational/precedent multiplier
  + mandatory partner-judgment gate instead of hard bands);
- **staffing norms**: lean panel staffing vs leveraged pyramid;
- **transport**: LEDES/e-billing vs direct bill.
v1 ships the insurance-defense regime (the firm's market). White-shoe is a stub
profile proving the seam — deferred, not designed around.

## 5. Training loop — honest semantics (what "getting the math right" means)

1. **Routing/extraction/driver detection**: supervised by generator ground truth
   (synthetic process gold). Claimable: "recovers known-truth labels on held-out
   synthetic + adversarial sets at X%." Legitimate now.
2. **Sizing math v1 is deterministic** (templates × drivers × proportionality).
   Correctness = (a) internal validity: golden + metamorphic + counterfactual
   tests; (b) external plausibility: reference-class feasibility bands from
   public anchors (the per-task bands + implied-hours checks built during the
   firm-template audit); (c) **no real-world accuracy claim** — §21 stands.
3. **ML challengers (converged step 7, later)**: predict phase/task hours from
   case features. Pre-firm-data eval is limited to (i) learnability — does the
   model recover the generator's driver math on held-out synthetic worlds — and
   (ii) reference-class plausibility. All artifacts labeled
   `reference_class_only`, never "calibrated." Dollars always deterministic from
   governed rates.
4. **Firm-data unlock**: real dispositions/actuals replace declared assumptions
   (S, p, envelopes) through the governed recalibration lane; only then do
   accuracy claims exist.

## 6. Checks run for this design (verification trail)
- Driver machinery, scaling tests, nonlinear templates, profiles, routing flow:
  verified present in the real repo (paths above).
- Firm template audit: dollar-only form (no role/rate/hours), broken grand-total
  formula chain, P85 double-count, feasible demo numbers, E119 > $25k preapproval
  trip — all previously verified by direct inspection.
- Economics framing (cost-of-risk vs bespoke) is domain reasoning, not repo fact
  — flagged for the firm checkpoint to confirm against their actual practice.
