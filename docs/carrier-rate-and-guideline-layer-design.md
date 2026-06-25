# Carrier Rate & Guideline Layer — Design + Codex Handoff

**Status:** Slices A-B implemented (carrier x state x title rate resolution,
synthetic carrier guideline projection). Slices C-E and the P1 budget-math fixes
remain proposed and handed to Codex.
**Owner repo:** `LawFirm-os-intake` (vertical composition; owns no platform canon).
**Authority posture:** rate cards and guidelines are synthetic `candidate` artifacts;
promotion runs through the owning sibling repo. Builds on
`docs/driver-based-budget-model-design.md`.

## The architectural decision (read first)

Carrier guidelines must be able to **change the math**, but the proposal math must stay
pure (`BudgetGuidelineFlag.rewrites_budget` is `Literal[False]`). Resolve this by keeping
**two numbers**:

- **Proposed budget** — what the work costs at firm/authorized rates and full hours.
  Unchanged; `proposed_for_human_review`.
- **Carrier-compliant projection** — the same matter after the guideline layer applies
  (capped rates, disallowed tasks/expenses removed, staffing reshaped), emitted as a
  **separate, labeled artifact** with the delta (`over_cap_amount`, `disallowed_hours`,
  `reshaped_lines`). It is a *projection*, never a submission.

This lets guidelines reshape cost without a silent rewrite of the proposal.

## What guidelines actually do (and where each lands)

| Guideline rule | Changes | Engine site |
|---|---|---|
| Rate caps / freezes / named-timekeeper approval | resolved rate | rate layer → compliant projection |
| Staffing / leverage (no partner for routine discovery; one timekeeper per depo) | task → role assignment | reassignment pass → compliant projection |
| Billing judgment (block-billing ban, travel %, intra-office conf caps, non-billable activities) | billable hours + line coding | hours-haircut + LEDES coding |
| Pre-approval thresholds (experts > $X, depos > N, vendors, research > Y hrs) | gates work | feed existing escalation/exception layer |
| Expense rules (per-page copy caps, research caps, expert-invoice approval) | E-code lines | expense layer → compliant projection |

## Slice A — DONE (carrier x state x title rates)

- `config/synthetic-carrier-rate-card.yaml`: carriers → `schedule[state][title]`, aliases,
  jurisdiction aliases, effective dates.
- `src/lawfirm_os_intake/rates.py`: `resolve_role_rates(profile, confirmation, rate_card)`
  → `RoleRateResolution` with carrier/state provenance; flat-rate fallback.
- `build_budget_proposal(..., rate_resolution=...)`; `run_budget` discovers
  `profile.rate_card_ref` and resolves. Demo NV rates reproduce prior flat rates.
- Tests: `tests/test_carrier_rates.py`.

---

## Codex handoff — build these next (each: PR-sized, candidate-only, green CI, TRACE)

### B. Carrier guideline artifact + proposed-vs-compliant projection
**Status:** DONE in this repo as a local candidate slice.

- Add `config/synthetic-carrier-guideline.yaml` (one fake carrier): `rate_caps` by title,
  `expense_caps` by E-code, `contingency_allowed`, `budget_cadence`,
  `variance_approval_percent`.
- Add `CarrierCompliantProjection` (candidate model + schema) on the proposal:
  `proposed_total`, `compliant_total`, `over_cap_amount`, per-line `capped`/`disallowed`
  flags, and a basis block. Apply rate caps and expense caps **in the projection only**;
  leave the proposal lines untouched.
- Acceptance: a matter whose resolved partner rate exceeds the cap shows
  `proposed_total > compliant_total` with a non-zero `over_cap_amount`; proposal lines
  unchanged; `rewrites_budget` stays `False`; no submission.

### C. Staffing / leverage reshaping + blended-rate reporting
- Guideline `staffing_rules`: `task_role_overrides` (e.g. L320 → paralegal), `max_timekeepers_per_event`,
  `preferred_drafting_role`.
- In the compliant projection, reassign task roles per the rules and recompute fees; emit
  a `leverage_summary` (partner% / associate% / paralegal% of hours and fees) and the
  blended rate.
- Acceptance: a "no partner for routine discovery" rule moves L310/L320 hours to a lower
  role in the projection and lowers the blended rate; proposal unchanged; deterministic.

### D. Pre-approval thresholds → escalation/exception integration
- Guideline `pre_approval_thresholds`: `experts_over_count`, `expert_spend_over_amount`,
  `depositions_over_count`, `research_hours_over`, `vendor_spend_over_amount`.
- When a resolved driver/expense crosses a threshold, emit an Exception Lake **dry-run**
  candidate + a human-gate entry ("carrier pre-approval required"), reusing the existing
  escalation machinery. No external write; dry-run only.
- Acceptance: med-mal defaults (4 experts, $30k expert spend) trip the expert thresholds
  and produce dry-run candidates routed to the pre-approval human gate.

### E. Second fake carrier + carrier counterfactual eval
- Add a second guideline profile; add `tests/test_carrier_counterfactual.py`: the **same**
  matter under Carrier A vs Carrier B changes rates / caps / staffing / compliant total
  **deterministically and explainably**, while observed evidence and proposal lines stay
  stable (mirror the practice-context counterfactual discipline).

### Named-timekeeper overrides (fold into B or a small slice)
- Add a `timekeeper` concept (`id, title, state, approved_rate`) and
  `named_timekeeper_overrides` to the rate card; resolution precedence:
  named-TK → carrier×state×title → carrier×title default → firm default → absent
  (hours-only). Record which precedence tier fired.

---

## P1 budget-math fixes (from the algorithm review — do alongside B/C)

1. **Propagate uncertainty from driver unknowns.** Today `estimated_hours_min/max` is a
   flat `hours*0.8 … *1.25` and expenses have no range (`budget.py` `_budget_totals`).
   Give count drivers `min/likely/max` in `budget-driver-policy.yaml`; for
   `unknown`/`profile_default` drivers widen the band from the driver range; for
   `human_confirmed` keep it tight. Range **expenses** too. Acceptance: an unknown
   deposition count yields a materially wider total band than a confirmed one.
2. **Resolution path as a first-class lever.** When `resolution_path` is observed/confirmed,
   select that scenario as the headline (not hard-coded `standard`, `budget.py:668`). Add
   optional `probability` to `BudgetScenario` and an `expected_total` =
   Σ p·total when probabilities exist (the home for FJC-IDB disposition priors). Acceptance:
   confirmed "through_trial" makes the trial scenario the headline; probabilities sum→1.
3. **Make intensity matter and route it correctly.** `cumulative_multiplier_cap: 1.35`
   makes intensity nearly cosmetic and it only touches hours, not expenses/counts. Either
   widen the range/cap (e.g. 0.7–2.5) and apply to expense-bearing lines, or route severity
   into counts (catastrophic → more experts/depositions/trial_days). Pick one; document it;
   fix the cap-default footgun (`policy.get("cumulative_multiplier_cap", multiplier)` →
   default to a finite constant).
4. **Smaller:** include `task_ids` in `_driver_effect_key` (dedup drops tasks); compare
   actuals against the scenario matching the actual resolution path and flag
   `budgeted==0 & actual>0` as over-threshold (`budget_actuals.py`); replace the 6-tuple
   return of `_budget_totals` with a dataclass.

## Governance (unchanged for every slice)

Synthetic-only; rate cards/guidelines/timekeepers are `candidate`, hashed, promote through
Semantic Substrate. The proposal stays `proposed_for_human_review` and
`not_authorized_for_client_submission`; the compliant projection is a projection, not a
submission. No external writes, connectors, network, provider calls, conflict conclusions,
docketing, or matter opening. Exception/pre-approval outputs are dry-run candidates only.
