# Budget Truth Kernel

- Status: Fable design/red-team output, candidate-only, synthetic-only.
- Author: Fable 5, 2026-07-05.
- Scope: `src/lawfirm_os_intake/budget.py`, `drivers.py`, `rates.py`, `guidelines.py`, `budget_actuals.py`, `config/budget-driver-policy.yaml`, `config/synthetic-carrier-rate-card.yaml`, `config/synthetic-carrier-guideline.yaml`, `context/synthetic-profiles/insurance-defense*.yaml`.
- Premise: green tests can still produce a bad legal budget. This doc lists where the current math is wrong, silently degraded, or under-specified, defines invariants that must always hold, and hands Codex a PR-sized fix sequence.

Two findings below (F1, F2) were **empirically reproduced** on this working tree on 2026-07-05, not just read from code.

---

## 1. P0/P1 findings

Severity legend: P0 = produces a wrong number or wrong scope silently; P1 = produces a misleading number/band or misses a required review trigger; P2 = footgun/defense-in-depth.

### F1 (P0) — Unknown `resolution_phase` silently includes ALL phases

`_included_phase_ids` (budget.py:650): if a scenario's `resolution_phase` is not in the template's phase order, the scenario includes **every phase**.

Reproduced: `_included_phase_ids(["L100","L200","L300","L400"], "L250")` → all four phases.

Consequences:
- A typo in `scenarios:` policy ("L250", "l200", "L500" on a template without L500) makes `early_resolution` cost the same as `through_trial`.
- Monotonicity check still passes (equal totals satisfy `<=`), so nothing flags.
- Expected value becomes meaningless while looking precise.

Required behavior: unknown `resolution_phase` must be a **deterministic block** — scenario set status `blocked_invalid_scenario_policy`, no headline total, exception candidate emitted. Never "include everything".

### F2 (P1) — Falsy-zero min collapses the lower band upward

`_budget_totals` (budget.py:697,710) uses `line.estimated_hours_min or line.estimated_hours` and `line.estimated_expenses_min or line.estimated_expenses`. Python's `or` treats a legitimate `0.0` minimum as missing.

Reproduced: a line with `estimated_hours=18, estimated_hours_min=0.0, hourly_rate=250` yields `total_min = 4500.0` instead of `0.0`.

This is live today: `count_driver_ranges.num_dispositive_motions.min: 0`, so any L340-style task scaled by an unknown/default motions driver has `hours_min = 0.0` and the proposal's `total_min` is silently overstated. Same bug shape wherever `x_min or x` / `x_max or x` appears (also `BudgetScenario` totals via the same helper).

Fix: `value if value is not None else fallback`. Grep target: `_min or ` / `_max or ` in budget.py.

### F3 (P1) — Default intensity multipliers inflate the *default* case by construction

`intensity_multiplier_policy` sets `severity_tier: significant → 1.08 (L300,L400)` and `liability_dispute: disputed → 1.05 (L200,L300)`. But `matter_family_defaults.medical_malpractice_defense` *defaults* severity to `significant` and liability to `disputed`. So a medmal intake with **no observed facts at all** gets L300 hours multiplied by `1.08 × 1.05 = 1.134`.

If template hours were authored to describe the typical (default) matter, defaults double-count: the template already embeds "significant/disputed", then the multiplier adds +13.4% on top. There is no calibration anchor stating which tier the template hours represent.

Required invariant (I7 below): for every matter family, the product of intensity multipliers evaluated at the family's `matter_family_defaults` must equal 1.0 per phase (± rounding), OR the template must carry an explicit `baseline_intensity` declaration and the policy must be normalized against it. Enforce in a test that loads the real policy file.

### F4 (P1) — Guideline flags are computed only on the selected scenario's lines

`build_budget_proposal` calls `_guideline_flags(selected_lines, selected_totals.total, ...)` (budget.py:1186). If the selected scenario is `early_resolution`, then:
- `phase_budget_caps.L300` is never evaluated (no L300 lines selected);
- `total_budget_cap` is checked against the truncated total, while `through_trial` may exceed the cap by 2×.

A reviewer approving the scenario *set* sees "cap not exceeded" flags that are only true for the cheapest branch. Flags must be evaluated per scenario (or at minimum against the most expensive scenario) and each `BudgetGuidelineFlag` should carry `scenario_id`.

Same defect class in `guidelines.py`: `build_carrier_compliant_projection` and the preapproval report run on `budget.lines` (selected lines only, since the proposal stores selected lines), so carrier thresholds like `depositions_over_count` are never tested against the through-trial branch.

### F5 (P1) — Observed count drivers collapse uncertainty to a point

`_range_from_scaled_driver` (budget.py:267): when provenance is `observed_support`/`human_confirmed`, min = max = likely. Knowing the deposition **count** does not make `hours_per_unit` exact — the per-unit coefficient is itself a synthetic assumption. Today an observed `num_depositions=8` line carries a zero-width band while an unscaled 10-hour template task carries ±20-25%.

Required behavior: band width must never be zero on any line whose formula contains at least one `profile_default` or synthetic coefficient. Split uncertainty into two factors:

```
hours_low  = per_unit_low  × units_low
hours_high = per_unit_high × units_high
units_(low,high)   from provenance: observed → (units, units); default/unknown → range policy
per_unit_(low,high) from a new per-unit band in the template (default ±20% if absent)
```

This restores the honest statement: "count known, coefficient assumed."

### F6 (P1) — Carrier projection deltas clamp at zero and hide compliant *increases*

`guidelines.py::_delta` = `max(0, proposed − compliant)`. A staffing `task_role_override` can move a task to a **more expensive** role (e.g. carrier-b `L340 → senior_associate` on a line proposed at `associate`): compliant fees rise, but `staffing_rule_delta`, `over_cap_amount`, and `rate_cap_delta` all read 0. The reviewer's "guideline impact" columns say "no impact" while `compliant_total > proposed_total`.

Fix: keep signed deltas (`proposed − compliant`, negative = compliant is higher) or add explicit `compliant_increase_amount` fields; flag any line where `compliant_line_total > proposed_line_total` as `requires_human_review`.

### F7 (P1) — Rate/state fallback proceeds with wrong-carrier, wrong-state rates without forcing review

`rates.py::_match_carrier` falls back to `default_carrier_id`, and `_match_state` falls back to `default_state`, when no alias matches. Provenance is recorded (`default_carrier` / `default_state`) but nothing downstream escalates. Concretely: a confirmed jurisdiction of `"Arizona"` (not in `jurisdiction_aliases`) silently prices the whole budget at **NV** rates.

Also: if two confirmed parties match two different carriers (carrier + payer from different card entries), the winner is **dict iteration order of the YAML**, not role precedence.

Required behavior:
- `state_matched_by == "default_state"` while `confirmed_jurisdiction` is non-null and unmapped → hard block or `hours_only` + review flag; never silently price.
- `carrier_matched_by == "default_carrier"` while carrier-role parties exist → same.
- ≥2 distinct alias matches → deterministic block `ambiguous_carrier_for_rates` (ties broken by role precedence `insurance_carrier > instructing_source > payer` only when roles differ; same-role ties always block).

### F8 (P1) — Scenario monotonicity is checked in policy list order, not phase order

`_build_scenario_set` (budget.py:794-804) checks `totals[i] <= totals[i+1]` over the order scenarios appear in the policy file. Reordering the YAML makes the check meaningless (or false-fails). The check should sort scenarios by `phase_order.index(resolution_phase)` before comparing, and a `monotonic_total_order=False` result should be a **blocking** QA condition, not a stored boolean nobody reads.

### F9 (P2) — Expected value: exact `== 1` probability gate, silent None

`probability_sum == 1` (budget.py:821) after `round(...,6)`. `[0.25, 0.5, 0.24]` (author error) yields EV = None with no flag; a reviewer sees a missing EV and cannot tell "not configured" from "misconfigured". Emit a `BudgetGuidelineFlag`-style item when probabilities are present but don't sum to 1 within 1e-6. Also record that EV is a **scenario-weighted arithmetic mean of point totals**, not a distribution statistic (see I10).

### F10 (P2) — First-seen role rate in projection staffing rules

`guidelines.py::_role_rates_from_budget_lines` takes the first-seen rate per role. A named-timekeeper override line appearing first (e.g. partner at 430) becomes the role rate used for staffing reshaping across the whole budget. Deterministic but arbitrary. Use the rate *resolution* (card schedule) as the source for target-role rates, not budget lines.

### F11 (P2) — Named timekeeper title mismatch is silent

`budget.py::_task_rate`: override applies only when `override.title == role`; on mismatch it silently falls back to the role rate. A timekeeper listed on the card as `partner` staffed on an `associate` task is exactly the situation a carrier rejects — surface it as an unknown/flag.

### F12 (P2) — `apply_labor_employment_budget_fact_constraints` returns a clean budget for a blocked report

budget.py:115-119: a report with `blocked_missing_critical_facts` returns the budget **unchanged**. The workflow blocks earlier via `enforce_budget_preconditions`, so this is unreachable in `run_budget` — but the function contract is a footgun for any other caller. Defense-in-depth: raise or return the budget with `pricing_status="insufficient_information"` and an explicit unknown.

### F13 (P2) — Duplicated cap tables can drift

`role_rate_caps` exist in both `config/budget-driver-policy.yaml#synthetic_guideline_constraints` and `config/synthetic-carrier-guideline.yaml#carriers.*.rate_caps`. Today they agree (partner 425, …). Nothing checks agreement, and the driver-policy copy is carrier-blind. Add a consistency audit (or derive the driver-policy flags from the guideline of the resolved carrier).

---

## 2. Where the system must block / widen / go hours-only / require confirmation

Deterministic decision table (proposed; the "current" column is what the code does today):

| # | Condition | Current | Required |
|---|-----------|---------|----------|
| D1 | Scenario `resolution_phase` not in template phase order | include all phases (F1) | **block** scenario set |
| D2 | Confirmed jurisdiction unmapped in rate card | price at default state (F7) | **hours_only + review flag** |
| D3 | Carrier-role parties present, no alias match | price at default carrier (F7) | **hours_only + review flag** |
| D4 | ≥2 distinct carrier alias matches (same role tier) | dict-order pick (F7) | **block** `ambiguous_carrier_for_rates` |
| D5 | Any scaling driver `unknown` with no range policy | fall back to template hours, point band | keep fallback, but **widen** with per-unit band and add unknown flag (exists partially) |
| D6 | All of a scenario's totals unpriced | hours_only status (works) | keep; also suppress EV |
| D7 | Probabilities present but sum ≠ 1 | silent EV=None (F9) | **flag for human review** |
| D8 | `monotonic_total_order == False` (phase-ordered) | stored boolean | **block** QA gate |
| D9 | Compliant projection total > proposed total | deltas read 0 (F6) | **require human confirmation** flag |
| D10 | L&E fact report blocked/critical gaps | precondition gate blocks (works) | keep; make budget-layer call defensive (F12) |
| D11 | Intensity default product ≠ 1 at family defaults | silent inflation (F3) | **policy-load-time validation error** |
| D12 | Named timekeeper title ≠ task role | silent fallback (F11) | **review flag** |
| D13 | Actuals arrive with no matching budget rows | `actuals_without_budget` driver (works) | keep |
| D14 | Missing template for confirmed family | `insufficient_information` (works) | keep |

"Widen" always means: widen the band and say why in a support item; never move the likely value.

## 3. Invariant table

Every invariant is checkable deterministically from a `BudgetProposal` JSON alone (plus its policy files). Codex should implement them as a pure `audit_budget_invariants(proposal, policy, guideline) -> list[InvariantViolation]` in a new `budget_invariants.py`, wired into the QA gate and replay tests.

| ID | Invariant | Formal statement |
|----|-----------|------------------|
| I1 | Line arithmetic | `estimated_fees == round(estimated_hours × hourly_rate, 2)` for every priced line |
| I2 | Band sanity | `hours_min ≤ hours ≤ hours_max`; `expenses_min ≤ expenses ≤ expenses_max`; all ≥ 0 |
| I3 | Nonzero band on assumed coefficients | if line formula uses any `profile_default`/synthetic per-unit coefficient then `hours_min < hours_max` (kills F5) |
| I4 | Totals additivity | `subtotal_fees == round(Σ line fees, 2)`; same for expenses; `total == subtotal_fees + subtotal_expenses + contingency_amount` |
| I5 | Band totals honor explicit zeros | `total_min == Σ (hours_min if hours_min is not None else hours) × rate + …` (kills F2) |
| I6 | Scenario nesting | scenario with later `resolution_phase` includes a superset of phases; `included_phase_ids` is always a prefix of phase order; **every** `resolution_phase` ∈ phase order (kills F1) |
| I7 | Default-intensity neutrality | ∀ family, ∀ phase: Π multiplier(defaults[family]) ∈ [0.999, 1.001] unless template declares `baseline_intensity` (kills F3) |
| I8 | Monotone scenarios | totals sorted by phase-order rank of `resolution_phase` are non-decreasing (kills F8) |
| I9 | Cap-flag completeness | for every scenario s and every cap c in effective guideline: a flag exists with `scenario_id == s`, `constraint_id == c` evaluated on s's lines (kills F4) |
| I10 | EV integrity | `expected_total` present ⇔ all probabilities present ∧ |Σp − 1| ≤ 1e-6 ∧ all scenarios priced; EV ∈ [min scenario total, max scenario total] |
| I11 | Projection conservation | `compliant_subtotal_fees == Σ compliant line fees`; signed per-line deltas sum to `proposed_total − compliant_total` (kills F6's ledger gap) |
| I12 | Rate provenance honesty | `source == "carrier_rate_card"` ⇒ `carrier_matched_by/state_matched_by` recorded; any `default_*` match ⇒ a review flag exists (kills F7) |
| I13 | Contingency scope | `contingency_amount == round(subtotal_fees × pct/100, 2)`; contingency never applied to expenses; compliant contingency 0 when carrier disallows |
| I14 | No-rewrite boundary | proposal totals/lines identical before and after projection/flag attachment; projection lives only in `carrier_compliant_projection` |
| I15 | Hours-only purity | `pricing_status == "hours_only"` ⇒ `subtotal_fees is None ∧ total is None ∧ contingency_amount is None` |
| I16 | Determinism | same inputs (packet, confirmation, profile, drivers, card, guideline) ⇒ identical proposal modulo generated ids/timestamps |
| I17 | Band interpretation label | proposal carries a fixed statement that `total_min/max` are arithmetic bounds under stated ranges, not confidence intervals or probabilities |

## 4. Counterexample table

Each row is a proposed regression fixture (all synthetic). None are committed as failing tests; they are specs.

| CE | Setup | Current wrong output | Correct output |
|----|-------|----------------------|----------------|
| CE1 | Scenario policy with `resolution_phase: L250` | scenario includes L100–L400; no flag | blocked scenario set |
| CE2 | Task scaled by `num_dispositive_motions`, driver unknown, range min=0 | `total_min` counts 18h at full rate (verified: 4500 instead of 0) | `total_min` honors 0.0 |
| CE3 | Medmal, zero observed facts, all defaults | L300/L400 hours ×1.134 vs template | ×1.0 (or declared baseline) |
| CE4 | `resolution_path=early_resolution` confirmed; L300 phase cap 90k; through-trial L300 total 120k | no phase-cap flag anywhere | flag on `through_trial` scenario |
| CE5 | Confirmed jurisdiction "Arizona" (unmapped) | full budget priced at NV rates, no flag | hours_only + review flag |
| CE6 | Parties: Harbor Point (insurance_carrier) + Cascade (payer) | dict-order carrier wins | block `ambiguous_carrier_for_rates` |
| CE7 | carrier-b guideline; L340 proposed `associate` @250, override → `senior_associate` @325 | `staffing_rule_delta = 0`, `over_cap_amount = 0`, compliant_total silently ↑ | signed delta −X, review flag |
| CE8 | Observed `num_depositions = 8` | deposition lines have zero-width band | band ≥ per-unit uncertainty |
| CE9 | Probabilities `[0.25, 0.5, 0.24]` | EV silently None | flag `probability_sum != 1` |
| CE10 | Scenario YAML listed `through_trial` first | monotonic check compares wrong order | phase-order sort before check |
| CE11 | Named timekeeper `synthetic-tk-harbor-partner-nv` on an `associate` task | silent fallback to associate rate | review flag |
| CE12 | Actuals for phase L500 (not budgeted) | works (`actuals_without_budget`) | keep as regression pin |

## 5. Proposed formulas (candidate spec)

Per-line, all deterministic, all recorded in `calculation_formula`:

```
units_likely        = driver.value                      (observed/confirmed/default)
units_low, units_high:
    observed/confirmed → (units_likely, units_likely)
    default/unknown    → (range.min, range.max)         (from count_driver_ranges)
per_unit_low  = hours_per_unit × (1 − u)                u = per-unit uncertainty, template field
per_unit_high = hours_per_unit × (1 + u)                default u = 0.20 when template omits it
hours_likely  = hours_per_unit × units_likely × M
hours_low     = per_unit_low  × units_low  × M_low
hours_high    = per_unit_high × units_high × M_high
M             = Π capped intensity multipliers (phase-scoped), normalized so that
                Π multiplier(family defaults) == 1 per phase          (I7)
M_low/M_high  = M (intensity is a modeled shift, not an uncertainty source, v1)
fees_x        = round(hours_x × rate, 2)                x ∈ {low, likely, high}
expenses_x    = base + expense_per_unit × units_x       (then intensity if policy says so)
total_x       = Σ fees_x + Σ expenses_x + round(Σ fees_x × contingency_pct/100, 2)
```

Band semantics (I17): `[total_low, total_high]` is the arithmetic envelope under the stated per-unit and count ranges. It is **not** a probability interval; do not present percentiles. Scenario probabilities are review weights supplied by policy, and EV is their weighted mean — label both as synthetic policy inputs.

## 6. What Fable did NOT change

No budget engine rewrite. The engine's shape (template × drivers × intensity × scenarios × projection) is sound; the defects are local. Rejection/appeal learning (`carrier_rejection_learning.py`, `reviewed_learning_gate.py`) is already human-gated and append-only — no math defects found there in this pass beyond noting that learning proposals must reference the invariant audit once it exists.

## 7. Codex handoff (ordered, PR-sized)

### PR-BK1 — Falsy-zero band fix + invariant audit skeleton (risk: low)
- Purpose: kill F2; create `audit_budget_invariants` with I1, I2, I4, I5, I13, I15.
- Edit: `src/lawfirm_os_intake/budget.py` (`_budget_totals` None-checks), new `src/lawfirm_os_intake/budget_invariants.py`, wire into QA gate where `BudgetProposal` is validated.
- Tests: new `tests/test_budget_invariants.py` (CE2, CE12 pins); extend `tests/test_budget_gate_and_math.py`.
- Artifacts: `budget_invariant_report.json` in run dir.
- Validate: `PYTHONPATH=src pytest tests/test_budget_invariants.py tests/test_budget_gate_and_math.py tests/test_budget_scenarios.py`, then full `pytest`, `ruff check`, `python -m lawfirm_os_intake demo` smoke.
- Do NOT: change any likely values, template hours, or scenario selection.

### PR-BK2 — Scenario policy hardening (risk: low)
- Purpose: F1, F8, F9 → I6, I8, I10.
- Edit: `budget.py` (`_included_phase_ids` raises/blocks via a validation path; `_build_scenario_set` phase-order sort; probability-sum flag), `models.py` (`BudgetScenarioSet` gains `status` or reuse guideline-flag list; keep back-compat defaults).
- Tests: CE1, CE9, CE10 in `tests/test_budget_scenarios.py`.
- Do NOT: silently reorder scenarios in the emitted artifact; preserve policy order for display, sort only for the check.

### PR-BK3 — Per-scenario guideline flags + preapproval (risk: medium)
- Purpose: F4 → I9. Add `scenario_id` to `BudgetGuidelineFlag` and evaluate caps per scenario; run carrier preapproval thresholds against the max-scope scenario as well as the selected one.
- Edit: `budget.py::_guideline_flags`, `guidelines.py::build_carrier_preapproval_report`, `models.py`.
- Tests: CE4 in `tests/test_carrier_guidelines.py`, `tests/test_budget_scenarios.py`.
- Do NOT: rewrite lines; flags remain review-only (`rewrites_budget` stays type-locked False).

### PR-BK4 — Rate resolution guardrails (risk: medium)
- Purpose: F7, F11 → D2–D4, D12, I12.
- Edit: `rates.py` (ambiguity detection, unmapped-jurisdiction/carrier flags returned on `RoleRateResolution`), `budget.py` (consume flags → hours_only or unknowns), `workflow.py::run_budget` wiring.
- Tests: CE5, CE6, CE11 in `tests/test_carrier_rates.py`, `tests/test_carrier_role.py`.
- Do NOT: invent a fuzzy-match; alias matching stays exact casefold.

### PR-BK5 — Intensity normalization (risk: medium, policy change)
- Purpose: F3 → I7, D11. Add load-time validation in `drivers.py::load_driver_policy` that family-default multiplier product == 1 per phase, and renormalize `config/budget-driver-policy.yaml` (e.g. significant 1.08→1.0, soft_tissue 0.95→0.88, catastrophic 1.22→1.13; disputed 1.05→1.0, clear 0.9→0.857, hotly_contested 1.18→1.124; keep neutral venue 1.0).
- Tests: CE3; update any total-pinning tests (demo totals WILL change — that is the point; record before/after in the PR body and in a DECISION_TRACE).
- Do NOT: merge without human review of the new numbers; this changes headline totals.

### PR-BK6 — Two-factor uncertainty (risk: medium)
- Purpose: F5 → I3, formulas §5. Template gains optional `per_unit_uncertainty`; scaled lines get nonzero bands even with observed counts.
- Edit: `budget.py::_range_from_scaled_driver` (+ callers), `context/synthetic-profiles/insurance-defense*.yaml`.
- Tests: CE8.
- Do NOT: touch likely values.

### PR-BK7 — Signed projection deltas (risk: low)
- Purpose: F6, F10 → I11, D9.
- Edit: `guidelines.py` (`_delta` → signed fields `compliant_delta_signed`, keep old max-0 fields for back-compat; role rates from resolution not first-seen line), `models.py` additive fields.
- Tests: CE7 in `tests/test_carrier_guidelines.py`, `tests/test_carrier_counterfactual.py`.
- Do NOT: remove existing fields (downstream reports consume them).

### PR-BK8 — Cap-table consistency audit + L&E defensive contract (risk: low)
- Purpose: F12, F13.
- Edit: `budget.py` (blocked L&E report → insufficient_information), new consistency check between driver-policy caps and resolved-carrier guideline caps emitted as a flag.
- Tests: extend `tests/test_labor_employment_*` and `tests/test_carrier_guidelines.py`.

Sequencing note: BK1 and BK2 first (pure correctness, no number changes except bands). BK5 is the only PR that changes headline totals; isolate it and require explicit human sign-off.
