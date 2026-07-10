# Bounded-Leakage Calibration — Hard Kernel (Opus first-pass draft)

## 1. Status

- **status:** candidate; **author:** Opus (first-pass architect); **date:** 2026-07-08.
- **synthetic-only, not canon until human-approved.** Parallel draft; does not supersede a Fable 5 pass.
- Extends, does not replace: `reviewed_learning_gate.py`, `budget_calibration_corpus.py`, `backtesting.py` (billing sim), the carrier-rejection loops, `benchmarks.py`, and `cross-matter-noninterference-kernel.opus-draft.md` (this is the **calibration counterpart** of that kernel). No learned matcher. No boundary weakened. Mirrors the Mock Trial `probabilistic_calibration_boundary.md` gates (validation-data-gated, matter-source-separation, no runtime until approved).

## 2. Executive position

Exact cross-matter non-interference (NI-1: `Δ=0`, removing any matter changes no output) is **provably impossible** for a fitted parameter — learning *is* nonzero influence. The correct replacement is **matter-level differential privacy (matter-DP)**, of which **NI-1 is exactly the `ε=0` special case.** Real-data calibration is therefore not "break the wall" but "**move the wall from `ε=0` to a small, declared, ledgered `ε`**," with a fail-closed gate that refuses to publish any calibrated parameter lacking a `CalibrationLeakageProof`. The technical spine: (a) fits depend on data only through **sufficient statistics**; (b) each matter's contribution to those statistics is **clipped** to a known norm, making global sensitivity finite; (c) **DP noise** on the clipped statistics buys a formal `(ε,δ)` bound; (d) a **leave-one-matter-out (LOMO)** screen catches dominance before it reaches the noise mechanism; (e) an **aggregate-only** path (no noise) is allowed only for low-sensitivity pooled parameters that also pass a reconstruction test. Where the bound cannot be met with usable noise, the answer is **stay synthetic**.

## 3. Formal leakage bound (replaces NI-1)

**Neighboring unit = one matter** (all records/outcomes of a single matter added/removed) — the matter is the confidentiality boundary, so this is *matter-level* DP, not row-level.

- Mechanism `M` (a calibration procedure) is **(ε,δ)-matter-DP** iff for all matter-neighbors `D ~ D'` and all output sets `S`: `Pr[M(D)∈S] ≤ e^ε·Pr[M(D')∈S] + δ`.
- **NI-1 ≡ (0,0)-matter-DP.** Bounded leakage = `ε>0`. This is the single unifying statement of the whole program.
- **Global sensitivity** of a statistic `g`: `Δg = max_{D~D'} ||g(D) − g(D')||`. Noise scale is set by `Δg` and `ε` (Laplace `b=Δg/ε`; Gaussian `σ = Δg·√(2 ln(1.25/δ))/ε`).
- **Group privacy (mandatory here):** a client with `k` matters, or `k` affiliated matters (E4 in the entity kernel), differ by `k` — so their joint leakage is `k·ε`. **The budget must be set per the largest client/affiliate group, not per matter.** This is the calibration-side echo of the wall's client-vs-matter scope. `[COUNSEL: is the protected unit the matter, the client, or the affiliate group?]`

**LOMO** is the *computable relaxation of NI-1* used as a screen, not as the bound:
```
Δ_lomo = max_m || fit(D) − fit(D \ {m}) ||        # empirical, over matters present
```
LOMO catches **dominance** (one matter moving the fit) and verifies clipping is active. It does **not** prove the DP bound (the worst-case neighbor need not be in `D`). The formal bound comes from clipping + noise; LOMO is the necessary pre-screen.

## 4. Calibration loop inventory

Every place a real matter outcome would move a shared parameter:

| # | Estimator | Fit target | Sufficient stats | Default path |
|---|---|---|---|---|
| C1 | Budget drivers/thresholds (`budget_calibration_corpus`, `budget_learning_loop`) | phase/task hour & expense driver means, variance thresholds | sums, sums-of-squares, counts per (phase,task,role) | aggregate-only if ≥K matters; else DP |
| C2 | Payment-lag / DSO (billing sim survival/AFT) | lognormal-AFT params per carrier w/ shrinkage | Σ log(lag), Σ log²(lag), n, censoring counts | DP (small per-carrier n) |
| C3 | Rejection probability (carrier loops) | Beta-Binomial rejection rate per carrier | successes, trials | DP (rates are re-identifying at small n) |
| C4 | Appeal recovery | recovery fraction distribution | Σ recovered, Σ billed, n | DP |
| C5 | Rate benchmark cells (`benchmarks.py`) | (state,tier,role,year) low/median/high | order statistics | **stays public-proxy**; DP only if ever matter-derived |
| C6 | Correlation/common-shock σ (H1) | carrier/matter shock variance | dispersion of quarterly rates | aggregate-only + dominance |

Hierarchical **partial pooling helps privacy**: shrinking per-carrier estimates toward the pooled mean lowers each matter's leverage → smaller `Δ` → less noise. Prefer it wherever a per-carrier number is wanted (C2/C3).

## 5. Sensitivity taxonomy of calibrated outputs

- **may-publish-exact (aggregate-only, no noise):** low-sensitivity pooled parameters over ≥K matters with no dominance and a bounded query budget (C1 driver means, C6 σ). Weaker than DP — must pass the reconstruction test and register in the differencing ledger.
- **must-DP:** any per-carrier/per-segment rate, lag, or recovery parameter, or any estimate with small `n` or dominance (C2–C4). Formal `(ε,δ)`; noise disclosed; band widened.
- **stays-synthetic / refused:** parameters where usable ε forces noise larger than signal (utility floor breach), or where group size is unknown, or where the estimator can't be reduced to clipped sufficient statistics. Fail closed to the synthetic prior or hours-only.
- **prohibited as calibration input (never, at any ε):** raw privileged narrative, real negotiated firm rates, real carrier panel rates, individual settlement amounts presented as outputs. These are refused at admission (inherited from the source-boundary taxonomy), not noised.

## 6. Mechanism fork (deterministic)

```python
def calibrate(estimator, matters, screens, ledger, policy) -> Result:
    D = purge_walled(matters, screens)                 # non-interference kernel runs FIRST
    stats = per_matter_contributions(estimator, D)     # exponential-family sufficient stats
    group = max_group_size(D, screens)                 # client/affiliate group -> group privacy factor
    k_matters, top1 = distinct_matters(stats), top1_leverage(stats)
    lomo = max_leave_one_matter_out(estimator, D)      # dominance screen

    if lomo > policy.delta_max or top1 > policy.p_dominance:
        route = "DP"                                    # dominance -> must noise (or refuse)
    elif k_matters >= policy.K and low_sensitivity(estimator, policy):
        route = "AGGREGATE_ONLY"
    else:
        route = "DP"

    if route == "AGGREGATE_ONLY":
        theta = fit(pool(stats))                        # exact, replayable
        theta = complementary_suppress(theta, ledger)   # differencing guard
        proof = build_proof(route, kanon=..., lomo=lomo, dp=None)
    elif route == "DP":
        C = policy.clip_norm(estimator)                 # clip each matter's stat contribution
        clipped = clip_per_matter(stats, C)             # -> global sensitivity == C (per group: k*C)
        rho = policy.rho_for(estimator)                 # zCDP budget for this release
        if not ledger.can_spend(rho, group):            # composition accounting
            return FAIL_CLOSED("privacy_budget_exhausted")
        noised = gaussian_mechanism(sum(clipped), sensitivity=group*C, rho=rho, seed=sealed_seed)
        theta, band = fit(noised), widen_band(rho, C)
        if utility_floor_breached(theta, band, policy):
            return FAIL_CLOSED("noise_exceeds_signal_stay_synthetic")
        ledger.spend(rho, group)
        proof = build_proof(route, dp={epsilon,delta,rho,global_after:ledger.total})
    else:
        return FAIL_CLOSED("not_reducible_to_clipped_sufficient_stats")

    if not reconstruction_test(theta, D, policy.adversary) <= chance + policy.margin:
        return FAIL_CLOSED("reconstruction_test_failed")
    proof.status = "candidate"; proof.human_review_required = True
    return Result(theta, proof)                          # gate refuses to promote without proof + approval
```

Rules: **purge-then-calibrate** (the wall runs before the estimator); clipping makes sensitivity known **by construction**; the sealed noise seed is secret (proof carries `seed_hash`; an auditor re-runs with the sealed seed under control); AGGREGATE_ONLY and DP **both** must pass the reconstruction test (it is the empirical backstop for k-anon composition failures).

## 7. Candidate schemas

```
CalibrationEstimator: {estimator_id, family: expfam|survival|beta_binomial, sufficient_stats[],
                       clip_norm C, shrinkage: hierarchical|none, path_default}
PrivacyLedger:        {ledger_id, unit: matter|client|affiliate_group, accounting: zCDP,
                       rho_spent, rho_cap, entries:[{estimator_id, rho, group_size, at}]}
LomoRecord:           {estimator_id, delta_lomo, delta_max, top1_leverage, p_dominance, dominance_ok}
SufficientStatRelease:{stat_id, pre_clip_max_contrib, clip_norm C, clipped: true, noised: bool, mechanism}
ReconstructionTestRecord: {adversary_model, aux: "all-but-one-matter", target_metric,
                       recovered_rate, chance_rate, margin, passed}
CalibrationLeakageProof:
  {estimator_id, parameter, corpus_version_ref, screen_version,         # ties to the wall kernel
   path: aggregate_only|dp|refused,
   kanon:{distinct_matters, top1_leverage, K, dominance_ok},
   lomo: LomoRecord,
   dp:{epsilon, delta, rho, mechanism: gaussian, global_epsilon_after, ledger_ref}|null,
   reconstruction: ReconstructionTestRecord,
   utility:{band_width, utility_floor_ok},
   determinism:{aggregate_byte_identical | dp_seed_hash, rebuilt: true},
   group_privacy:{unit, max_group_size, effective_epsilon},
   status: candidate, human_review_required: true, approval_id: null}
```

## 8. DP mechanism & composition

- **Reduction to sufficient statistics:** exponential-family fits depend on data only through sums → noise the sums, fit on noised sums. Confines the entire privacy analysis to a few clipped statistics.
- **Mechanism:** Gaussian on clipped sums (default; supports zCDP). Laplace acceptable for a single count. Beta-Binomial (C3): noise `successes` and `trials` under a shared `ρ`, refit.
- **Composition:** account in **zCDP (`ρ`)** for tight composition across many releases, convert to `(ε,δ)` at report time (`ε = ρ + 2√(ρ ln(1/δ))`). Basic/advanced composition is looser — do not use as the accountant. Global `ρ_cap` per protected unit; **refuse** on exhaustion. `[COUNSEL: total ε/ρ cap; how often the cap resets, if ever.]`
- **Clipping** sets global sensitivity to `C` (per group `k·C`). Pre-clip max contribution is recorded; a matter far exceeding `C` pre-clip is an outlier whose clipping destroys utility → route to human, not silent clip.

## 9. Aggregate-only guard (differencing)

AGGREGATE_ONLY has **no formal ε** — it relies on: `distinct_matters ≥ K`, `top1_leverage ≤ p_dominance`, **complementary suppression** (suppress cells recoverable by differencing published parameters), and a **bounded query/overlap budget** in the ledger (too many overlapping aggregates ⇒ switch that family to DP). The reconstruction test is the empirical catch. If any of these can't be guaranteed, the parameter is promoted to the DP path.

## 10. Reconstruction / membership-inference test

Strong adversary by construction: give the attacker **all matters but one** plus the published `θ`/`band`; attacker infers the held-out matter's outcome (membership + attribute inference). Require `recovered_rate ≤ chance_rate + margin` across a synthetic sweep of held-out matters. This validates the chosen `ε`/`K` empirically and catches implementation leaks. A pass at strong-adversary is meaningful; a pass only at weak-adversary is theater — use the strong one.

## 11. Retroactive-screen interaction

If a matter is walled after calibration: sufficient stats are recomputed from the purged corpus and **re-noised with a fresh sealed seed**; the parameter is re-derived and the prior superseded (never deleted — append a superseding diff, per the wall kernel §7). Bonus property: because the old release was `(ε,δ)`-bounded, it leaked **≤ ε** about the now-walled matter — **bounded leakage caps retroactive damage**, which exact-but-unenforceable non-interference never could. Promoted rules citing the pre-screen parameter are flagged `screen_tainted` and re-derived.

## 12. Required synthetic fixtures

| id | pins |
|---|---|
| `calib-aggregate-clean` | ≥K matters, no dominance → aggregate; LOMO ≤ budget; reconstruction ≤ chance |
| `calib-dominance-route-dp` | one matter 80% leverage → aggregate refused → DP path taken |
| `calib-dp-epsilon-bound` | small-n carrier rate → Gaussian on clipped sums; `ρ` debited; band widened; reconstruction fails at strong adversary |
| `calib-group-privacy` | one client with 6 matters → effective ε = 6× per-matter; budget set by group, not matter |
| `calib-utility-floor` | ε so small noise > signal → **FAIL_CLOSED stay-synthetic** (not a garbage number) |
| `calib-lomo-negative` (holdout) | parameter published without clipping/suppression that moves > budget under LOMO → **gate blocks** |
| `calib-differencing` (holdout) | two overlapping aggregate cells whose difference isolates one matter → complementary suppression fires |
| `calib-budget-exhausted` (holdout) | release that would exceed `ρ_cap` → refused |
| `calib-retro-rederive` | matter walled post-fit → re-noised re-derive; old superseded, not deleted; citing rule `screen_tainted` |
| `calib-determinism` | aggregate rebuild byte-identical; DP rebuild identical given sealed seed |

## 13. Red-team / premortem

1. **DP-washing:** noise added but presented as precise → BLOCK: proof mandates `band_width` + `dp.epsilon` on every DP-path number; language linter forbids "exact/actual" on DP outputs.
2. **Budget amnesia:** `ρ` spent but ledger not persisted → each release fails closed unless `ledger.spend` is durable; `global_epsilon_after` recorded in the proof.
3. **Group blindness (most likely real leak):** protecting per matter while a client owns many matters → group privacy factor mandatory; fixture `calib-group-privacy`.
4. **Clipping utility collapse:** aggressive clip → useless params published anyway → utility floor + human route for outliers.
5. **Aggregate-only over-trusted:** k-anon treated as DP → reconstruction test on both paths; differencing ledger; auto-promote family to DP on overlap.
6. **Sufficient-stat escape:** an estimator not in the exponential family (nonparametric) has unbounded sensitivity → refused unless clipped/reduced; no silent fit on raw data.
7. **Seed leak:** sealed noise seed committed → seed is secret material (keychain/env, never repo); proof carries `seed_hash` only.

## 14. Codex PR-sized handoff

- **PR-CL1 — sufficient-stats + LOMO + aggregate path (med).** `calibration/estimators.py` (expfam reduction, `clip_norm`), `lomo.py`, aggregate-only fit + `CalibrationLeakageProof` + `reconstruction_test.py` + gate wire. Fixtures: aggregate-clean, dominance-route-dp, lomo-negative, determinism. **DO NOT:** publish per-matter fits; skip the reconstruction test; fit non-expfam on raw data.
- **PR-CL2 — DP mechanism + zCDP ledger + composition (high).** Gaussian mechanism on clipped sums; `PrivacyLedger` (zCDP `ρ`, group-size accounting, durable); band widening; utility floor. Fixtures: dp-epsilon-bound, group-privacy, utility-floor, budget-exhausted. **DO NOT:** use basic composition as accountant; account per matter when a group is larger; present DP numbers as exact.
- **PR-CL3 — retroactive re-derive + wall integration (med).** Recompute-and-re-noise on `screen_version` bump; `screen_tainted` on citing rules; supersede-not-delete. Fixture: calib-retro-rederive. **DO NOT:** mutate/delete raw evidence; reuse the old seed.

## 15. Counsel / human policy inputs (not architect decisions)

- **Protected unit:** matter vs client vs affiliate group (sets the group-privacy factor).
- **Budget:** per-unit `ε`/`ρ` cap, and whether it ever resets.
- Whether DP-noised parameters are **ethically presentable** to finance/counsel, and with what disclosure.
- The **adversary model** the reconstruction test must assume.
- Whether **any** real-outcome calibration is permitted before the Phase-2 pilot approvals (privacy, counsel, data-owner, Substrate governance) — mirrors `probabilistic_calibration_boundary.md`; default remains **synthetic-only**.
