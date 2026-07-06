# L&E Class/Collective/PAGA Budget Template — Hard Kernel

- Status: Fable design output, candidate-only, synthetic-only. Second pass; deepens `docs/fable/le-synthetic-corpus-roadmap.md` (fixtures 2–4) and applies the intensity/uncertainty rules from the budget-truth and intensity-normalization kernels.
- Author: Fable 5, 2026-07-05.
- Owner boundaries: intake owns candidate synthetic templates and evals; Legal Knowledge Runtime owns any source research behind driver plausibility; humans own every nonlinear modeling choice; no exposure/penalty modeling anywhere.

## 1. Problem and why it is hard

Class/collective/PAGA defense cost is **stepwise in procedural outcomes** (certification, conditional certification, PAGA manageability), and its dominant cost objects (certification briefing, opt-in administration, representative-sampling discovery, penalty-period data pulls, settlement administration) simply do not exist in an individual-claim template. Multiplying an individual template by claimant count is a category error: it inflates the wrong phases, misses the right ones, and pretends smooth scaling where reality has cliffs. Green tests over a scalar model would still produce structurally wrong budgets.

## 2. Template family architecture

Six distinct templates (not variants of one), selected by confirmed matter posture; selection is a human-confirmed fact, never inferred from claimant count alone:

| Template id | Posture | Phase skeleton |
|---|---|---|
| `le-individual-defense` | single claimant, litigation | L100 assess / L200 pleadings / L300 discovery / L400 trial (existing UTBMS shape) |
| `le-multi-claimant-defense` | 2–4 related claimants, no class mechanism | individual skeleton + per-claimant scaled tasks (this is the ONLY place per-claimant linear scaling is legitimate) |
| `le-class-collective-defense` | Rule-23-shaped / collective (opt-in) | **C100** assess+remove / **C200** pleadings+early motions / **C300** pre-certification discovery / **C400** certification briefing+hearing / **C500** merits+decert / **C600** resolution+settlement administration |
| `le-paga-shaped-defense` | PAGA-shaped representative action | C-skeleton minus opt-in tasks, plus manageability motion task and penalty-period data-scoping tasks (data scoping ≠ exposure modeling) |
| `le-admin-exhaustion` | agency-charge stage only | A100 position statement / A200 agency investigation response / A300 mediation-conciliation (no litigation phases at all) |
| `le-arbitration-path` | compelled individual arbitration(s) | R100 motion to compel / R200 per-arbitration blocks × claimant tier / R300 mass-arbitration administration (its own nonlinearity when tier is high) |

Settlement is a phase (C600/R300), not a separate template: it truncates via the scenario set like any resolution path.

## 3. Drivers

New driver ids for `config/budget-driver-policy.yaml` (all resolve with the existing provenance machinery):

| driver_id | class | notes |
|---|---|---|
| `num_claimants` | count | multi-claimant template only; linear per-claimant scaling capped at 4 (above → class posture question, block) |
| `opt_in_tier` | count_tier | `t0:<10, t1:10-49, t2:50-249, t3:250-999, t4:1000+`; t4 blocks (human staffing plan) |
| `num_locations` | count | drives sampling discovery + witness travel scaling |
| `class_period_months` | count | scopes data volume tasks only |
| `paga_period_months` | count | ditto, PAGA template |
| `esi_volume_tier` | count_tier | reused from existing taxonomy |
| `certification_posture` | scenario | selects scenario branch (like `resolution_path`): `cert_denied / cert_granted / hybrid_partial`; PAGA analog: `manageability_granted / denied` |
| `arbitration_agreement_coverage` | intensity/tier | `none / partial / universal` — gates the arbitration template and the compel motion |
| `agency_stage` | scenario | exhaustion template truncation |
| `num_individual_defendants` | count | supervisors/managers named personally |

## 4. Per-phase math

The base formula per phase extends the two-factor uncertainty model from the budget-truth kernel:

```
phase_hours(p) = fixed_block(p)                                   # certification briefing etc.
              + tier_block(p, opt_in_tier)                        # step function, no interpolation
              + Σ_d per_unit(p, d) × units(d)                     # smooth drivers only (locations, ESI, defendants)
band: tier_block carries its own (min, likely, max) per tier;
      per_unit terms band exactly as in budget-truth-kernel §5 (count range × per-unit uncertainty);
      fixed_block bands ± declared percentage.
Intensity multipliers (if any) apply baseline-relative per the intensity-normalization kernel.
```

Hard rules:
- **No cross-tier interpolation** — a tier table is honest about ignorance between rows; interpolation would manufacture precision.
- **Tier blocks are per-phase**, because opt-in count hits C300/C400/C600 very differently than C200.
- `class_period_months`/`paga_period_months` may scale only tasks explicitly tagged `data_scope_task: true`; they must never touch briefing/hearing tasks (period length changes data volume, not argument count).
- Scenario truncation: `certification_posture` selects which of C500/C600 shapes apply — `cert_denied` truncates to C400 + individual-claims runoff task; `cert_granted` includes full C500/C600; `hybrid_partial` includes both with declared partial blocks. All three scenarios always emitted for review (same pattern as `resolution_path`); the driver only moves the *selected* scenario when human-confirmed.

## 5. Block / widen / hours-only / human-review table

| # | Condition | Action |
|---|---|---|
| B1 | `opt_in_tier` unknown | hours_only for C300+ phases; C100–C200 may price (early work is tier-insensitive) |
| B2 | `opt_in_tier == t4` | block: `collective_scale_requires_staffing_plan` |
| B3 | posture ambiguous (class allegations present but claimant count ≤4) | block template selection; human confirms posture (never auto-select by count — R13 alignment) |
| B4 | `certification_posture` unknown | scenario set emitted, selected = policy default (`cert_denied` as cheapest-honest default is WRONG — use `standard` = hybrid_partial and flag); wide bands retained |
| B5 | `arbitration_agreement_coverage` partial/universal but arbitration template not selected | block: posture/template mismatch |
| B6 | period drivers unknown | data-scope tasks widen with declared range policy; never block alone |
| B7 | PAGA + class hybrid pleaded | both templates flagged; human selects primary; budgets never merged automatically |
| B8 | any tier table lacking a row for a resolved tier | block (policy defect, exception candidate) — never nearest-row fallback |

Mandatory human review points (gate ids, extending `human_gates.yaml`): posture/template selection (B3/B7); any t3+ tier budget; certification scenario selection; settlement-administration phase pricing; every blocked state above.

## 6. Fixture/gold strategy

Per L&E corpus roadmap conventions (reviewed golds, per-phase pins, policy hashes):

| Fixture | Pins |
|---|---|
| `le-collective-t2-clean` | full C-skeleton, per-phase hours, tier-block provenance, three certification scenarios, monotonic C-phase truncation |
| `le-collective-tier-boundary` (holdout) | 49 vs 50 opt-ins ⇒ t1 vs t2 blocks differ exactly by table delta; bands asserted, not just points |
| `le-collective-t4-block` | B2 block artifact + exception candidate |
| `le-paga-manageability` | manageability scenario branch; period driver touches only data_scope tasks |
| `le-paga-penalty-exclusion` | budget contains NO exposure/penalty amounts; exclusion support item pinned |
| `le-posture-ambiguity` | B3 block on class allegations + 3 claimants |
| `le-arbitration-mass` | R200 per-arbitration blocks × tier; R300 administration nonlinearity |
| `le-exhaustion-only` | A-skeleton truncation; no litigation phases priced |
| `le-hybrid-paga-class` | B7 dual-flag review |

Gold rule inherited: pin per-phase totals and tier-block identities; grand totals hide compensating errors.

## 7. Codex handoff

1. **PR-LEC1 (low):** driver taxonomy additions + tier-table schema (`tier_blocks` in template YAML) + B8 validation; no template yet. Tests: policy load validation, tier resolution provenance.
2. **PR-LEC2 (medium):** `le-class-collective-defense` template + per-phase math (fixed/tier/per-unit decomposition in `budget.py` — additive code path keyed on template `math_model: tiered_v1`, leaving existing templates untouched) + fixtures 1–3. Requires PR-BK5a (normalization machinery) and PR-BK6 (two-factor bands) first.
3. **PR-LEC3 (medium):** certification scenario branching (generalize `resolution_path` selection to `certification_posture`) + fixtures 4–6.
4. **PR-LEC4 (low):** exhaustion + arbitration templates + fixtures 7–9; human-gate wiring.

**Must not do:** per-claimant line fan-out; cross-tier interpolation; auto-selecting posture from counts; penalty/exposure math anywhere; touching the existing insurance-defense math path (the tiered model is additive, `math_model` keyed); building any of this before BK5a/BK6 land (it would bake unnormalized intensity + zero-width bands into a new template family).
