# Driver-Based Litigation Budget Model — Design

**Status:** Partially implemented in local candidate slices; stronger drivers, guideline constraints, and second matter family remain proposed.
**Owner repo:** `LawFirm-os-intake` (vertical composition; owns no platform canon)
**Authority posture:** all new vocabulary is `candidate`; promotion runs through the owning sibling repo

## 1. Problem

The current budget engine (`src/lawfirm_os_intake/budget.py`) is a flat template
lookup: it reads a per-matter-family template from the practice profile and computes
`hours * synthetic_rate` per fixed task, sums fees and expenses, and applies a flat
contingency percentage. The newer build adds hour ranges (`estimated_hours_min/max`),
a `BudgetCalculationReport`, `BudgetSupportItem` provenance, and a `scenario_name`
field — but the underlying number is still a frozen constant.

Consequence: a medical-malpractice trial line is identical whether the case has two
experts or nine, settles at mediation or tries for three weeks, and has clear or
hotly disputed liability. The output is internally consistent but is **not rooted in
what actually drives litigation cost**. This document specifies a model that is,
while preserving every governance boundary already established in this repo.

## 2. Design goals and non-goals

**Goals**

- Budgets scale on the real cost drivers of insurance-defense litigation.
- Generalize across litigation types (med-mal, auto/BI, premises/GL, products,
  professional liability, employment, construction defect, coverage) by sharing one
  engine and varying only base templates + default driver values.
- Replace false single-number precision with **scenario branches + ranges**.
- Keep math deterministic and fully explainable from inputs.

**Non-goals (unchanged platform boundaries)**

- No rate invention; missing rates still produce an hours-only proposal.
- No canonical schema/taxonomy mutation; UTBMS/LEDES stays `external_code_candidate`.
- No conflict clearance, engagement, matter opening, deadline docketing, or budget
  submission. Budget remains `proposed_for_human_review`.
- No model-chosen numbers; the planner is deterministic arithmetic over typed drivers.
- Synthetic data only; public data remains planning/calibration, never a case input.

## 3. Core model

### 3.1 Two structural changes

1. **A budget is a scenario set, not a point estimate.** The dominant cost lever in
   litigation is how far a case goes. Emit branches with phase cutoffs:
   - `S1 early_resolution` — motion to dismiss granted / pre-discovery settlement;
     stops after pleadings and any early ADR.
   - `S2 standard` — resolves at mediation or on summary judgment after fact and
     expert discovery; the modal path.
   - `S3 through_trial` — full discovery, dispositive motions, trial prep, trial,
     and (optionally) post-trial.
   Each scenario reuses the base template truncated at a declared `resolution_phase`.

2. **Within each scenario, task hours scale on case drivers** instead of a constant.

### 3.2 Driver taxonomy

| Class | Drivers | Effect |
|---|---|---|
| Resolution path | early-dismissal / settle-pre-discovery / settle-post-discovery / MSJ-out / trial | selects scenario truncation |
| Structural counts | depositions, experts (by discipline), parties + cross/third-party claims, plaintiffs, written-discovery rounds, ESI tier, trial days, dispositive motions | count-driven tasks compute `per_unit_hours * count` |
| Intensity | severity/exposure tier, policy-limits vs excess, disputed vs clear liability, venue difficulty, novelty/complexity | bounded multipliers on discovery/expert/trial phases |
| Coverage | reservation of rights, coverage counsel / DJ action, multiple policy layers | distinct line; never blended into defense fees |
| Guideline constraints | staffing caps, leverage requirements, rate caps, budget/phase caps, block-billing ban, task-code requirement | reshape/cap; do not inflate |

### 3.3 Deterministic math

```
hours(task) = base_hours(task) * Π intensity_multipliers(applicable) * count_factor(task)

count-driven examples:
  deposition_task.hours   = n_depos    * hours_per_depo(role)
  deposition_task.expense = n_depos    * per_depo_expense
  expert_task.hours       = n_experts  * hours_per_expert
  expert_task.expense     = Σ expert_fee_range(discipline)     # kept distinct from fees
  trial_task.hours        = trial_days * hours_per_day(role) + severity_mult * prep_base

scenario(S) = base_template truncated at S.resolution_phase
output(S)   = { lines, subtotal_fees, subtotal_expenses, contingency, total range(min/likely/max) }
```

`min/likely/max` derive from per-line `estimated_hours_min/max` (already in the model)
and from driver ranges where a count is unknown.

## 4. Driver provenance (the anti-bias rule)

Every driver value carries a source, mirroring the existing
`observed_evidence_refs` vs `context_signal_refs` split and the
`ScoredCandidate.source_evidence_status` channel
(`observed_support` / `source_anchor_only` / `unknown_option`):

- `observed_support` — extracted from confirmed intake evidence (carries `EvidenceRef`s).
- `human_confirmed` — set by the reviewer at the confirmation gate.
- `profile_default` — supplied by the synthetic driver policy; **labeled as an
  assumption**, never as observed fact.
- `unknown` — no value; widens ranges / branches scenarios; listed under `unknowns`.

Only `observed_support` and `human_confirmed` drivers reduce the `unknowns` list.
A `profile_default` never silently masquerades as an observed fact.

## 5. Generalization across litigation types

The driver taxonomy is matter-type-agnostic — every litigation type has depositions,
experts, parties, motions, a severity, and a resolution path. Only two things vary by
type: the **base phase template** and the **default driver set**. Adding a litigation
type is therefore: drop in a base template + defaults; the engine is shared. A
matter family with no approved template still returns `insufficient_information`
(current behavior preserved).

## 6. Where the model lives (governance fit)

- **`config/budget-driver-policy.yaml`** (new, synthetic, versioned, hashed): driver
  taxonomy, per-unit hours, multipliers, caps, scenario definitions. Drivers live in
  versioned policy, never hidden in code — mirroring the practice-context discipline.
- **Practice profiles** carry per-matter-family **default driver values** and base
  templates (extends today's `budget_templates`).
- **`budget.py`** now has deterministic count-driver scaling and emits the
  `standard` scenario as the compatibility proposal surface.
- New typed artifacts: `CaseDriverProfile`, `BudgetScenario`, `BudgetScenarioSet`
  (all `candidate`). UTBMS/LEDES unchanged as `external_code_candidate`.

## 7. Calibration with public + synthetic data

- **Public data → priors and sanity bands only, never case facts.** FJC IDB
  (nature-of-suit × disposition × time-to-disposition → scenario probabilities and
  phase-duration bands); NHTSA (auto severity priors); NPDB (med-mal exposure priors);
  CourtListener/RECAP (party / motion / deposition-count proxies). This stays inside
  the existing planning-only boundary enforced by `public_data.py`.
- **Synthetic data → engine behavior.** Counterfactuals must move monotonically and
  explainably: more depositions ⇒ more hours; higher severity ⇒ higher total;
  `total(S1) ≤ total(S2) ≤ total(S3)`. Adversarial fixtures: a missing driver must
  widen the range and add an `unknown`, never silently default while appearing observed.

## 8. Red-team / premortem (budget-specific; extends `PREMORTEM.md`)

| Failure | Mitigation in this design |
|---|---|
| Profile default masquerades as observed fact | driver provenance channel; defaults labeled `profile_default` and listed as assumptions |
| Single expected value hides path risk | always emit scenario set + ranges; expected value optional and labeled |
| Multiplier stacking → unrealistic blowup | cap cumulative multiplier; calibrate against public time-to-disposition bands; sensitivity tests |
| Budget tuned to hit a carrier cap | cap is a flag, not an input that rewrites hours; over-cap scenarios surfaced |
| Reviewer rubber-stamps the "likely" scenario | review form shows all scenarios and which drivers are unknown/assumed |
| Cross-type leakage (med-mal defaults onto a contract dispute) | base template + defaults keyed only to human-confirmed matter family; mismatch ⇒ `insufficient_information` |
| Overfitting to public aggregates | public data sets priors/bands only; a case driver is never auto-filled from an aggregate |
| Driver extraction becomes a hidden classifier with no evidence | drivers are candidates with evidence refs and provenance; unverified drivers stay `unknown` |

## 9. Build slices (each PR-sized, candidate-only, green-testable, with a TRACE)

1. **Driver capture, not yet applied.** Add `CaseDriverProfile` + `budget-driver-policy.yaml`
   (taxonomy + med-mal defaults/multipliers). Extract drivers from the confirmed packet
   and confirmation with provenance. Record drivers in the proposal but do **not** change
   the math → all existing tests stay green; add provenance tests.
2. **Driver-scaled counts.** Scale hours/expenses for count-driven tasks (depositions,
   experts, written discovery, trial days) behind a profile flag; counterfactual tests.
3. **Scenario set.** Emit `ScenarioSet` (S1/S2/S3) via `resolution_phase` truncation;
   update the budget review form; assert `S1 ≤ S2 ≤ S3`; legacy template maps to
   `standard` for back-compat.
4. **Intensity multipliers.** Severity / liability / venue / coverage with a cumulative
   cap; sensitivity tests.
5. **Guideline constraint layer.** Staffing reshaping, rate caps, budget-cap flags.
6. **Second matter family.** Auto-liability base template + defaults to prove
   generalization; cross-type counterfactual test.
7. **Calibration harness.** Public catalog → synthetic driver-distribution fixtures +
   holdout; scenario-probability priors. Stays synthetic-only.

## 10. Promotion map (what graduates and to where)

- driver taxonomy / scenario vocabulary / budget schema → **Semantic Substrate**
- runtime budget gate / approval routing → **Orchestrator**
- variance/actuals and template-change candidates → **Exception Lake**
- reusable budget-planner specialist → **Skills Registry**
- public-data calibration adapters → **Legal Knowledge Runtime**

Until promoted, every item here remains a local `candidate` and is pinned after promotion.

## 11. Human gates (unchanged)

Human confirmation precedes budget generation. The budget is a proposal only,
`not_authorized_for_client_submission = true`. Conflicts clearance, engagement
authorization, and matter opening remain separate blockers.
