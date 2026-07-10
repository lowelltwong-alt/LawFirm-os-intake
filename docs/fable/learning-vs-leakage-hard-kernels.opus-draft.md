# Learning-vs-Leakage — Two Hardest Kernels + Fable 5 Prompt (Opus draft)

- **status:** candidate; author: Opus (first-pass architect); date: 2026-07-07; synthetic-only; not canon.
- Scope: the two hardest open problems at the learn/leak seam. Candidate solutions below; the Fable 5 prompt at the end asks Fable to break or strengthen them.
- Shared law: fail closed; no learned matcher; no auto-promotion; learning = versioned diff citing sources; extend `reviewed_learning_gate`, do not fork it; mark counsel inputs.

---

## The one crux both problems share

**Non-interference (NI-1) = "removing any one matter changes no output" is `Δ = 0`. Any *learning* parameter has `Δ > 0` by construction.** So the moment you learn from real matters, exact non-interference is impossible and must be replaced by a **provable bounded-leakage** guarantee. P1 bounds leakage for a *continuous fitted parameter*; P2 bounds it for a *discrete qualitative rule*. P1 admits a formal bound; P2 does not — that asymmetry is the whole game.

---

## P1 — Bounded-leakage calibration on real matters

**Problem.** `θ = A(matters)`. NI-1 demands `θ` unchanged under leave-one-matter-out (LOMO); impossible. Bound instead how much any single matter's confidential outcome is recoverable from `θ` and everything downstream (reports, rules, DAD lessons).

**Property to replace NI-1 — Per-Matter Bounded Influence (PBI).**
Relax `==` to `≤ budget`. Operationalize with **LOMO sensitivity**:
```
Δ = max over matters m of || A(D) − A(D \ {m}) ||   (in the reported metric)
PBI holds iff Δ ≤ Δ_max  AND  no single matter's leverage > p_dominance
```
LOMO *is* NI-1 with the equality relaxed — computable, deterministic, replayable. `Δ` above budget ⇒ that matter dominates ⇒ suppress or route to DP.

**Deterministic mechanism fork (per parameter):**
```
if distinct_matters ≥ K and top1_leverage ≤ p_dominance and Δ ≤ Δ_max:
    path = AGGREGATE_ONLY          # publish from POOLED sufficient statistics; NO noise; exact/replayable
                                   #   + (n,k) dominance suppression + complementary suppression
elif dp_budget_available and parameter_tolerates_noise:
    path = DP_SUFFICIENT_STATS     # noise added to sufficient stats (not raw); (ε,δ) bound; band widened + disclosed
else:
    FAIL_CLOSED                    # stay on synthetic prior / hours-only; publish nothing
```
- AGGREGATE_ONLY gives k-anon-style protection, **not** a formal ε — good when the estimate pools many matters.
- DP_SUFFICIENT_STATS gives a formal `(ε,δ)`: presence/absence of one matter changes the output distribution by ≤ `e^ε`. It is the *fallback* when k-anon can't be met; its noise is **disclosed** (`dp_epsilon` + widened uncertainty; never shown as precise). DP noise is awkward for low-volume legal params — hence fallback, not default.
- Never publish a per-matter fitted value; only functions of pooled sufficient statistics.

**Composition / differencing.** Every release debits a global ledger (ε for DP; a query/overlap budget for aggregate paths). Reject any release where differencing across published parameters reconstructs a suppressed cell → complementary suppression at parameter level.

**`CalibrationLeakageProof` (candidate schema).**
```
{estimator_id, parameter, path: aggregate_only|dp|refused,
 kanon:{distinct_matters, top1_leverage, K, dominance_ok},
 lomo:{delta_measured, delta_max, ok},
 dp:{epsilon, delta, mechanism, global_epsilon_after, ledger_ref}|null,
 reconstruction_test:{adversary_model, recovered_le_chance: true, margin},
 determinism:{aggregate_byte_identical|dp_seed_hash, rebuilt: true},
 corpus_version_ref, status: candidate, human_review_required: true, approval_id: null}
```
`reconstruction_test` = red-team membership-inference/reconstruction: try to recover a target matter's outcome from `θ` + declared auxiliary; assert `≤ chance + margin`.

**Gate.** `reviewed_learning_gate` refuses a calibrated parameter without a valid `CalibrationLeakageProof` + approval. Reuses the existing chokepoint.

**Fixtures (synthetic).**
| id | pins |
|---|---|
| `calib-aggregate-clean` | ≥K matters, no dominance → aggregate; LOMO ≤ budget; reconstruction ≤ chance |
| `calib-dominance-refuse` | one matter 80% leverage → aggregate refused → DP or fail-closed |
| `calib-dp-bound` | small n → DP path; ε debited; band widened; reconstruction fails |
| `calib-lomo-negative` (holdout) | param moves > budget under LOMO, published w/o suppression → **gate blocks** |
| `calib-differencing` (holdout) | two overlapping cells whose diff isolates one matter → complementary suppression fires |
| `calib-determinism` | aggregate rebuild byte-identical |

**Codex handoff.** PR-CL1 LOMO + k-anon/dominance on estimators (aggregate path) + proof + gate wire (low/med). PR-CL2 DP-on-sufficient-stats mechanism + ε ledger + composition (med/high). **DO NOT:** publish per-matter fits; present DP-noised numbers as precise; calibrate without a proof.
**Counsel/human policy:** values of `ε, K, Δ_max, p_dominance`; whether DP-noised outputs are ethically presentable; whether *any* real-outcome calibration is permitted pre-pilot.

---

## P2 — Disclosure budget of a qualitative learned rule

**Problem.** A distilled lesson (rule text) can re-identify a matter or carry work-product. `counts`/k-anon cover numeric cells, not discrete qualitative rules. Bound the leakage of a lesson **before** it publishes or crosses into DAD.

**Structured Lesson IR (kills the free-text smuggling surface by construction).**
```
LessonIR:
  atoms:[ {dim: carrier|jurisdiction|matter_type|role|issue_family|threshold_band,
           value, generalization_level, class: operational|strategy} ]
  claim: before/after (CLOSED template, like PROPOSAL_POLICY)   # not free prose
  provenance:{support_matter_ids (private), occurrence_count}
  free_text: advisory only — LINTED, never a consumed signal
```

**Re-identification bound — k-anonymity over the matter POPULATION, not the sample.**
Published atom set = conjunctive predicate `P`.
```
anonymity_set(P) = | matters in the reviewed plausible universe consistent with P |   # never undercount; unknown ⇒ fail closed
require anonymity_set(P) ≥ K_qual  AND  support_count ≥ K_support  AND  l_diversity(claim) ok
```
Below threshold ⇒ **generalize** up a reviewed lattice (deterministic minimal climb): `"$487/hr" → "$450–500" → "above market"`; `NV → Mountain-West → US`; `KemperCarrier → carrier-tier → any-carrier`. If top-of-lattice still fails ⇒ **suppress** the lesson (fail closed). No learned matcher — the lattice is reviewed vocabulary.

**Privilege/work-product screen (separate check).** Atoms are partitioned `operational` vs `strategy`. Any `strategy`-class atom (litigation strategy, mental impressions) is **prohibited** — the lesson is **blocked, not generalized** (matches the taxonomy's `prohibited` tier: it never had permission to be signal).

**Cross-lesson differencing.** Combining a new lesson with already-published lessons may narrow an anonymity set below `K_qual` → suppress the new one (qualitative analog of complementary suppression).

**`LessonDisclosureProof` (candidate schema).**
```
{lesson_id, atoms+generalization_levels, anonymity_set, K_qual, support_count, K_support,
 l_diversity_ok, generalization_path:[{dim, from, to}],
 privilege_screen:{strategy_atoms_present: false},        # MUST be false
 differencing_check:{narrows_below_K: false},
 free_text_lint:{signal_bearing_free_text: none},
 adversary_model, status: candidate, requires: reviewed_learning_gate + approval}
```

**Honest residue (the Fable-worthy part).** k-anon over an *estimated* universe is only as strong as the universe model; an adversary who knows the firm's real matter list can re-identify even at `k ≥ K`. DP-for-text is not practical. So P2 bottoms out at **bounded re-identification under a *declared adversary model*** + privilege partition + human sign-off — **no clean formal bound exists.** State the adversary model explicitly; do not overclaim.

**Fixtures.**
| id | pins |
|---|---|
| `lesson-kanon-generalize` | specific threshold uniquely IDs support matter → climb to band → k met |
| `lesson-suppress` | top-of-lattice still k<K → suppressed |
| `lesson-privilege-block` | strategy atom present → **blocked**, not generalized |
| `lesson-differencing` (holdout) | two individually-safe lessons combine to isolate one matter → suppress 2nd |
| `lesson-freetext-lint` (holdout) | signal in free_text → blocked |
| `lesson-determinism` | same inputs → same generalization path |

**Codex handoff.** PR-QL1 LessonIR + closed vocab + generalization lattice + k-anon/suppress + privilege partition + proof + gate wire (med). PR-QL2 cross-lesson differencing + DAD-boundary enforcement (the payload schema gap in `dad-learning-process-audit.md` D2) (med). **DO NOT:** let free_text carry meaning; generalize a strategy atom instead of blocking; publish without a stated adversary model.
**Counsel/human policy:** `K_qual, K_support`; the adversary model; which dims are `strategy`-class; whether any qualitative lesson may cross to DAD pre-pilot.

---

## FABLE 5 PROMPT — break or strengthen these two kernels

You are Fable 5 (architecture red-team + simulation-methods researcher + ontology critic). Two candidate kernels above (P1 bounded-leakage calibration, P2 qualitative-rule disclosure) claim to replace exact non-interference with provable bounded leakage. **Conserve tokens. Do not summarize the file back.** Produce `docs/fable/learning-vs-leakage-hard-kernels.fable5.md` answering only:

**P1 checks.**
1. Is **LOMO influence ≤ Δ_max** a *sound* relaxation of NI-1, or does it miss a leakage channel (e.g., group-of-2 influence, or influence via variance not mean)? Give the counterexample or confirm.
2. Is **AGGREGATE_ONLY via pooled sufficient statistics** actually leak-safe under composition/differencing across many overlapping cells, or is k-anon-without-noise breakable? If breakable, the minimal fix.
3. Is **DP-on-sufficient-statistics** the right mechanism vs output/objective perturbation? Name a defensible ε and the composition accounting (basic vs advanced vs zCDP). When is DP noise so large the parameter is useless — i.e., where must the answer be "stay synthetic"?
4. Does the `reconstruction_test` adversary model match a real membership-inference threat, or is it theater?

**P2 checks.**
5. Is **k-anon over an estimated matter universe** defensible for legal work-product, or does the auxiliary-knowledge adversary defeat it so thoroughly that only suppression (never generalization) is safe for `support_count = 1`? State the adversary model you would require.
6. Is the **generalization lattice** sound, or does minimal-climb leak the *fact that a rare value was generalized*?
7. Does the **operational/strategy partition** actually hold, or is "operational fact" itself sometimes work-product (e.g., that the firm *studied* carrier X's pattern)?
8. Is there any bound better than "declared adversary + human sign-off" — a formal one — or is P2 genuinely unsolvable formally (confirm and say so plainly)?

**Deliverable.** For each of P1/P2: verdict (`sound` | `holed` | `needs-fix`), the sharpest counterexample, the minimal patch (schema/predicate/fixture), and one added negative fixture that would catch the hole. End with: which of the two blocks the real-data pilot harder, and the single smallest safe first step. Prefer formulas, pseudocode, fixtures over prose. Mark counsel/legal-judgment items as policy inputs, not your decision.
