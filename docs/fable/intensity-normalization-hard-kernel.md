# Intensity Normalization Hard Kernel (BK5)

- Status: Fable design output, candidate-only, synthetic-only. Second hard-kernel pass; expands the BK5 finding (F3) in `docs/fable/budget-truth-kernel.md`.
- Author: Fable 5, 2026-07-05.
- Owner boundaries: intake proposes and tests candidate math; the driver-policy taxonomy is Semantic Substrate promotion territory; headline-total changes require human sign-off.

## 1. Problem

`config/budget-driver-policy.yaml` applies intensity multipliers per tier (severity, liability, venue) while `matter_family_defaults` *defaults* those same drivers to non-1.0 tiers. Medical malpractice defaults to `severity_tier=significant` (×1.08 on L300/L400) and `liability_dispute=disputed` (×1.05 on L200/L300). A matter with zero observed facts therefore prices L300 at **×1.134** over template hours. If the template's hours were authored to describe the typical (default) matter — which is how template authoring works in practice — the policy double-counts the template's embedded assumptions.

Verified arithmetic on the live policy: L300 default product = 1.08 × 1.05 × 1.0 (venue neutral) = **1.134**; L400 default product = 1.08; L200 default product = 1.05.

## 2. Why this is hard

- There is no ground truth about what tier the template hours "mean" — the calibration anchor is a *declaration*, not a computation.
- Fixing it changes headline totals on every default-heavy budget, which is exactly the class of change that must never land silently.
- Both plausible fixes (renormalize policy vs re-author templates) produce identical numbers but very different audit trails.

## 3. The baseline/intensity model

**Core rule: intensity multipliers are offsets from a declared baseline, not absolute intensities.**

Decision: **templates declare, policy normalizes.** Two cooperating mechanisms:

1. Every budget template gains an optional declaration:
   ```yaml
   baseline_intensity:            # which tiers the template hours were authored at
     severity_tier: significant
     liability_dispute: disputed
     venue_difficulty: neutral
   ```
   If absent, the template's baseline is **defined** to be the matter family's `matter_family_defaults` tiers (the sane default: authors write templates for the typical case).

2. At policy load time (`drivers.py::load_driver_policy`, extended to take the template or family context), effective multipliers are normalized:

   ```
   M_eff(driver, tier, phase) = M_raw(driver, tier, phase) / M_raw(driver, baseline_tier(driver), phase)
   ```

   where `baseline_tier(driver)` comes from the template declaration, falling back to family defaults. Division happens only within each driver's own tier ladder (never across drivers) and only for phases where the raw effect applies. If `baseline_tier` has no raw entry for a phase, its raw multiplier is 1.0 there by construction.

### Invariant (I7, restated exactly)

For every matter family `f`, template `t(f)`, and phase `p`:

```
Π over drivers d of M_eff(d, baseline_tier_t(d), p) == 1.0            (exactly, by construction)
Π over drivers d of M_eff(d, defaults[f][d], p) ∈ [0.999, 1.001]      (when template declares no baseline)
```

The first line is a tautology of the formula — which is the point: correctness by construction, checked by a load-time assertion rather than trusted authoring discipline.

### Why normalize-in-code rather than renormalize-the-YAML

Both were designed; normalize-in-code wins:

| | Renormalize YAML values | Normalize at load (chosen) |
|---|---|---|
| Audit trail | new magic numbers (0.8796…) whose derivation lives in a PR description | raw human-meaningful tiers stay in YAML; normalization is a visible, tested formula |
| Template with a different declared baseline | needs a *separate* YAML per template | same YAML, per-template division |
| Drift risk | future edits re-break silently | invariant asserts on every load |

The YAML gains one explicit field so the intent is legible:

```yaml
intensity_multiplier_policy:
  normalization: baseline_relative     # new; absent/"raw" = legacy behavior for back-compat
```

`normalization: raw` (or absent) preserves current behavior so the switch is a deliberate, diffable policy change — not a silent code-side reprice.

## 4. Exact before/after examples

Raw policy (current): significant 1.08, soft_tissue 0.95, catastrophic_or_death 1.22 (L300/L400); disputed 1.05, clear 0.90, hotly_contested 1.18 (L200/L300; hotly also L400); venue favorable 0.95, neutral 1.0, plaintiff_friendly 1.12.

Effective multipliers after normalization against medmal defaults (significant/disputed/neutral):

| Driver | Tier | Raw | Effective |
|---|---|---|---|
| severity | soft_tissue | 0.95 | 0.95/1.08 = **0.8796** |
| severity | significant (baseline) | 1.08 | **1.0000** |
| severity | catastrophic_or_death | 1.22 | 1.22/1.08 = **1.1296** |
| liability | clear | 0.90 | 0.90/1.05 = **0.8571** |
| liability | disputed (baseline) | 1.05 | **1.0000** |
| liability | hotly_contested | 1.18 | 1.18/1.05 = **1.1238** |
| venue | all | — | unchanged (baseline neutral = 1.0) |

Worked totals (100-hour L300 task, associate @250, no scaling drivers):

| Case | Before (raw) | After (normalized) | Why it changes |
|---|---|---|---|
| All defaults (no observed facts) | 100h × 1.134 = 113.4h → $28,350 | 100h × 1.0 = 100h → $25,000 | default case no longer self-inflates |
| Observed catastrophic + hotly contested | 100 × 1.22 × 1.18 = 143.96h | 100 × 1.1296 × 1.1238 = 126.94h | deviation measured from baseline, not from an implicit 1.0 floor |
| Observed soft_tissue + clear | 100 × 0.95 × 0.90 = 85.5h | 100 × 0.8796 × 0.8571 = 75.39h | symmetric: mild cases get the full relief relative to baseline |

**Which totals change:** every budget where at least one intensity driver resolves at a non-baseline tier *or* was resolving at a default tier ≠ raw-1.0 — in practice, ALL current medmal/auto-BI demo totals change. Totals that do not change: hours-only budgets change hours identically; scenario *structure*, scaling-driver math, rates, expenses (except intensity-applied ones), and contingency percent are untouched.

## 5. Human sign-off artifact

PR-BK5 must attach a generated `intensity_normalization_signoff.json` (+ `.md` rendering):

```
{
  "signoff_id": ..., "policy_id": ..., "policy_version_before/after": ...,
  "normalization_mode_before": "raw", "normalization_mode_after": "baseline_relative",
  "per_family": [{
    "matter_family": ..., "baseline_source": "template_declaration" | "family_defaults",
    "per_phase_default_product_before": {"L200": 1.05, "L300": 1.134, "L400": 1.08},
    "per_phase_default_product_after": {"L200": 1.0, "L300": 1.0, "L400": 1.0},
    "demo_totals_before/after": {...per canonical fixture...},
    "effective_multiplier_table": [...as section 4...]
  }],
  "requires_human_approval": true, "approved_by": null, "approved_at": null
}
```

Generated by a small CLI (`python -m lawfirm_os_intake intensity-signoff --policy ... --profiles ...`), reviewed by a human, and the approved copy committed alongside the PR. The QA gate refuses `normalization: baseline_relative` policies whose signoff artifact is missing or unapproved.

## 6. Invariant tests (proposed, not committed broken)

| Test | Assertion |
|---|---|
| T1 load-time tautology | for each family/template: Π M_eff at baseline == 1.0 per phase |
| T2 default neutrality | budget built with all-default drivers == budget built with `case_drivers=None` template hours (± rounding) under `baseline_relative` |
| T3 deviation symmetry | observed tier below baseline reduces hours by exactly raw-ratio; above increases by raw-ratio |
| T4 legacy freeze | `normalization: raw` reproduces current 168-test outputs byte-identically |
| T5 cap interaction | cumulative cap (2.5) applies to the *effective* product; a capped effective product still records `capped=true` effect |
| T6 signoff gate | building with `baseline_relative` + missing/unapproved signoff artifact → blocked with explicit unknown |
| T7 declared-baseline override | template declaring `severity_tier: soft_tissue` gets M_eff(soft_tissue)=1.0 and M_eff(significant)=1.08/0.95 |

## 7. Codex handoff

**Build first (PR-BK5a, low risk):** normalization machinery behind `normalization: raw` default — `drivers.py` (compute effective table, carry both raw and effective in `CaseDriverProfile`), `budget.py::_intensity_adjustment` (consume effective; record raw+effective in each `BudgetDriverEffect.note`), tests T1, T3, T4, T5, T7. Zero behavior change while mode is `raw`.

**Then (PR-BK5b, requires human):** signoff CLI + artifact + QA-gate check (T6), flip `config/budget-driver-policy.yaml` to `baseline_relative`, regenerate demo goldens, attach approved signoff. Tests T2, T6.

**Must not do:** flip the mode and goldens in the same PR as the machinery; renormalize YAML values by hand; apply normalization to scaling drivers (`hours_per_unit` counts are not intensities); let the cumulative cap apply pre-normalization; touch expense-side policy semantics (`applies_to_expense_bearing_lines` keeps its meaning against effective multipliers).
