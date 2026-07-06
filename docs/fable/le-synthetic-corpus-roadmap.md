# Synthetic L&E Corpus and Eval Ladder Roadmap

- Status: Fable design output, synthetic-only.
- Author: Fable 5, 2026-07-05.
- Builds on: `labor_employment_budget_facts.py`, `config/labor-employment-budget-fact-needs.yaml`, existing holdouts (`holdout-*` bundles, L&E critical-facts holdout, ambiguous-role matrix, relationship topology), `courtlistener_dataset_strategy.py` for public-derived structure custody.
- Goal: make L&E budgets *testable* — every budget behavior claim in the Budget Truth Kernel needs a fixture that can falsify it, and L&E is where the matter-linking and fact-gap machinery is hardest.

## 1. Fixture matrix

Axes: **claim family** × **degradation variant**. Every cell is a candidate fixture; ✪ marks the 10 to build first (§2).

Claim families (priority order):
1. Discrimination/harassment (single plaintiff, Title VII-shaped synthetic)
2. Retaliation (often piggybacked — tests multi-theory budgeting)
3. Wage/hour individual (misclassification, OT)
4. Wage/hour class/collective + PAGA-shaped (drives the R13 collective cap and biggest budget nonlinearity)
5. ADA/FMLA (accommodation + interference; heavy on timeline facts)
6. Restrictive covenant / trade secret (employer-side plaintiff posture — flips representation posture assumptions)
7. Administrative exhaustion (EEOC/agency-charge stage only — pre-litigation budget shape, L100-heavy)
8. EPLI/carrier assignment (carrier-instructed defense, links to rate card + guideline layers)

Degradation variants (columns):
| Variant | What it stresses |
|---|---|
| clean | baseline gold |
| messy-thread | matter-link R5/R6, segmentation |
| missing-attachment | extraction gaps, R14 hold, fact-gap report |
| adversarial | prompt-injection + prohibited transitions inside L&E prose |
| rejection | carrier rejection capture → learning loop |
| appeal | appeal + human outcome recording |
| actuals-variance | budget_actuals over/under threshold |
| holdout | never used to tune; permutation/boundary variants |

## 2. Next 10 highest-value fixtures (✪)

| # | Fixture | Family × variant | Why now |
|---|---|---|---|
| 1 | `le-disc-harass-clean` | 1 × clean | anchor gold for the whole L&E ladder; exercises fact-needs policy end-to-end |
| 2 | `le-retaliation-piggyback` | 2 × clean | two theories, one matter — budget must not double-count shared discovery (tests template/task overlap policy) |
| 3 | `le-wage-hour-collective-cap` | 4 × clean | employer + 7 opt-ins: exercises R13 collective cap, per-plaintiff driver scaling limits, biggest nonlinear budget risk |
| 4 | `le-paga-shaped-penalty-exposure` | 4 × clean | penalties ≠ fees: budget must keep exposure modeling OUT (exclusion), tests boundary honesty |
| 5 | `le-ada-fmla-timeline-gaps` | 5 × missing-attachment | leave chronology absent → critical fact gaps → `range_only_pending_human_review` path (D10) |
| 6 | `le-exhaustion-eeoc-stage` | 7 × clean | pre-litigation budget: scenario set must truncate at L100/L200 analogs; tests I6 with a short phase order |
| 7 | `le-epli-carrier-assignment` | 8 × clean | carrier match + rate card + guideline caps on an L&E template (today only insurance-defense has them) |
| 8 | `le-restrictive-covenant-plaintiff` | 6 × clean | employer as plaintiff: posture flip must change template selection, not just a label |
| 9 | `le-disc-messy-thread-two-matters` | 1 × messy-thread | same HR sender, two employees, no matter numbers — the matter-linking kernel's L&E anchor |
| 10 | `le-rejection-staffing-leverage` | 8 × rejection | carrier rejects partner-heavy staffing → rejection→learning loop with staffing_rule_candidate |

Each fixture ships: bundle JSON (existing shape), reviewed gold JSON, and a one-page rationale (`docs/data/`) stating what it can falsify.

## 3. Reviewed gold requirements

- Gold is **reviewed** (a human read the fixture and asserted expected outputs) — `reviewed_gold: true` only after a recorded review; unreviewed golds may exist but never gate.
- Gold pins, minimum: matter_family candidates + expected confirmation; party roles (esp. ambiguous-role rows); critical fact gaps and `budget_readiness_state`; budget: pricing_status, per-phase hour totals (not just grand total — grand totals hide compensating errors), scenario set shape, flags expected; matter-link clusters (once ML lands); exception candidates expected (family + count, not ids).
- Gold must state **tolerances explicitly** (exact for counts/status, ±0.01 for currency); anything unpinned is declared unpinned, so silence is never accidental.
- Golds version with the policy files they assume (`gold.assumes_policy_hashes`) so a policy change invalidates affected golds loudly (stale-gold = qa_gate_defect exception, not silent pass).

## 4. Eval ladder

Rungs run in CI order; a rung failing stops the ladder (cheap → expensive):

| Rung | What runs | Gate |
|---|---|---|
| E0 schema/validation | export_schemas, validate_repo, policy load-time checks (incl. I7 default-neutrality) | hard |
| E1 unit invariants | `budget_invariants` on every fixture's proposal (I1–I17) | hard |
| E2 fixture golds | clean-variant golds | hard |
| E3 degradation | messy/missing/adversarial variants — expected *degraded* outputs (holds, blocks, gaps), not success | hard |
| E4 replay determinism | corpus replay ×2 + matter-link permutation shuffles ⇒ byte-identical (modulo ids/timestamps) | hard |
| E5 counterfactual | carrier B vs A, revision vs original, rejection→proposal shadow evals | report-only initially |
| E6 holdouts | holdout set, run last, results recorded but NEVER cited in tuning PRs (see exception taxonomy §7.4) | hard for regressions, forbidden for tuning |

## 5. Holdout strategy

- Keep ≥1 holdout per claim family; holdouts are *variants* of tuned fixtures (boundary shifted: one more party, one changed date, shuffled order) so they detect overfitting to fixture literals.
- Holdout golds are reviewed like normal golds but stored under `examples/synthetic/inbound/holdout-*` with `holdout: true`; the reviewed-learning gate refuses proposals citing only holdout evidence.
- Rotation: when a holdout fails and the fix lands, that holdout is "burned" — promote it to the tuned set and cut a fresh variant as the new holdout (record the rotation in the run ledger).

## 6. Non-reconstruction checks for public-derived structures

For structures derived from public data (CourtListener-shaped timelines, docket skeletons) via `courtlistener_dataset_strategy.py`:
- fixtures may inherit *structure* (event ordering, phase durations, motion sequences) but never text spans; enforce with an n-gram overlap audit (no ≥8-token shingle shared with the source snapshot) — a deterministic leaf tool (Rust candidate, see rust roadmap);
- party/entity names must come from the synthetic name generator namespace (`*.example`, synthetic registries), enforced by regex custody scan;
- each converted fixture records `public_source_methodology` provenance + the custody audit report ref; conversion review flow (`public_synthetic_fixture_conversion_review*`) already exists — extend its checks with the shingle audit.

## 7. Codex handoff (ordered)

### PR-LE1 — Fixtures 1, 5, 6 + golds (risk: low)
- Files: `examples/synthetic/inbound/le-*.json`, gold files per existing `test_fixture_gold.py` pattern, `config/labor-employment-budget-fact-needs.yaml` additions if fact-needs are missing for ADA/FMLA timelines.
- Tests: golds through existing fixture-gold machinery; E3 expectations for #5.
- Do NOT: add an L&E budget template beyond what fact-needs can support; if no template exists, the correct gold is `insufficient_information` (that IS the product behavior).

### PR-LE2 — L&E budget template + fixtures 2, 3, 4 (risk: medium)
- Purpose: first L&E UTBMS template (discrimination/harassment defense) in a synthetic profile + collective-scaling caps; extend `config/budget-driver-policy.yaml` with L&E drivers (num_plaintiffs, num_opt_ins, agency_charge_stage, num_individual_defendants) **after** PR-BK5 normalization rules exist.
- Tests: per-phase gold pins; R13-style cap behavior; I7 holds for the new family defaults.
- Do NOT: model penalty/exposure amounts (#4 pins their exclusion).

### PR-LE3 — Fixtures 7, 8, 10 + carrier layer on L&E (risk: medium)
- Extends rate card/guideline to the L&E synthetic profile; rejection fixture drives the staffing-leverage learning loop end-to-end.

### PR-LE4 — Fixture 9 + holdout rotation policy (risk: low; depends on PR-ML2)
- The messy-thread two-matter L&E bundle as matter-linking anchor; add holdout rotation notes to `docs/evaluation-plan.md`.

### PR-LE5 — Shingle/custody audit for public-derived fixtures (risk: low)
- Python reference implementation first (Rust later per rust roadmap); wire into `public_synthetic_fixture_conversion_review`.
