# Decision Trace — DT2 Deterministic Canonical Pricing Engine

Slice: post-marathon workstream, successor to DT1 (PR #123, merged). Branch:
`claude/dt2-canonical-pricing`, off `main`. Candidate-only, synthetic-only,
deterministic; no ML, no promotion.

## Situation

DT1 delivered the machine-readable driver taxonomy and the intake adapter, but
nothing consumed `CanonicalDriverProfile` — the researched taxonomy still did not
price a budget. DT2 is the moment it does.

## Decision

An additive `canonical_pricing` module composing the three governed inputs:

1. **Baseline hours** — the contract's CLCM-sourced case-type median
   (professional malpractice: **472 attorney hours**; NCSC 2013) spread across
   UTBMS phases by the CLCM-sourced fractions (L100 14% / L200 11% / L300 25% /
   L400 43% / L500 7%).
2. **× driver multipliers** — elicited assignments apply their contract `point`
   values (or additive deltas) to the phases containing their target UTBMS rows;
   `not_elicited` drivers stay neutral 1.0 (already rule-attributed on the
   profile — no silent defaults). Correlated drivers compose via the contract's
   **capped-composite** rule (largest full, others sqrt); every phase multiplier
   is capped at the contract `row_multiplier_cap` (10.0). Posture flags and
   un-elicited phase blocks have no hour effect. **E-code expense rows (E115
   court reporter, E119 experts) are excluded** — expenses are a separate layer,
   stated on the plan.
3. **× governed rates** — the synthetic carrier rate card (carrier × state ×
   title; defaults `synthetic-carrier-a`/NV), blended through a **CLCM-sourced
   role mix** (auto-tort median 75.5 senior / 78 junior / 42.5 paralegal of 196
   hours — the only case type with published role detail), mapped
   senior→partner, junior→associate, paralegal→paralegal.

All arithmetic is `Decimal` with fixed quantization (hours 4dp HALF_UP; cell
dollars HALF_UP to integer minor units). The `CanonicalPricedWorkPlan` validators
**recompute every cell, row, and total from stored fields** — tampering any value
fails closed. Each applied driver carries its **confidence tag and source** onto
the plan, so a reviewer can see per-driver why the budget is what it is.

The engine refuses: a profile built against a different contract digest, a line
with no CLCM baseline mapping, a rate card claiming real negotiated rates, or a
missing rate schedule.

`compare_with_legacy_sizing` gives an informational side-by-side of the legacy
sizing math (unchanged, still authoritative for the pipeline) and the canonical
engine; totals are **not expected to match** while both are candidates — the
legacy path scales a given base total, the canonical path derives hours from the
CLCM baseline.

## Worked example (test-pinned)

For the standard legacy fixture (party_count 2, injury surgical, liability
disputed, exposure high, venue state_default), the phase multipliers compose
exactly: L100 = 1.5×1.55 = **2.325**; L200 = 1.55×1.15 = **1.7825**;
L300 = 1.5×1.55×1.15 + 0.8 = **3.47375**; L400 = L500 = **1.55**. Dropping
`liability_clarity` removes only the +0.8 causation delta (L300 → 2.67375),
proving not_elicited neutrality.

## Non-decision

- The legacy `case_sizing` path is **unchanged**; nothing in the pipeline
  consumes the canonical plan yet. Swapping the pipeline over is a later,
  deliberate slice behind review.
- Role-mix mapping (senior→partner) and the sqrt composite rule are governed
  **judgment** parameters, documented as such.
- No ML; no promotion; no real rates (loader refuses).

## Evidence

`tests/test_canonical_pricing.py` — 10 tests (failing-test-first): determinism;
exact phase-multiplier composition; not_elicited neutrality; CLCM baseline hours;
governed rate resolution (45000/25000/16000 minor); total + cell tamper
rejection; capped-composite rule (group sqrt + cap); confidence carried on
applied drivers; legacy-vs-canonical comparison.

## Alternatives rejected

- **Sub-phase row-level allocation.** Rejected for v1: no public sub-phase hour
  weights exist (CLCM publishes task-level detail only for auto tort); phase-level
  allocation is honest to the sourcing. Row-level lands when firm LEDES data does.
- **Blending `senior_associate` into the role mix.** Rejected: CLCM publishes a
  three-role split; inventing a fourth share would be unsourced.
- **Making the canonical engine authoritative now.** Rejected: it runs alongside
  legacy sizing as a candidate until reviewed.

## Validation

Targeted tests 21/21 (DT1+DT2) green; conformance CLI green; `export_schemas`
(+4: canonical-priced-work-plan, priced-phase-row, priced-role-cell,
applied-driver-effect); ruff check + format clean; full validation suite green.
No UI change.

## Human gate

DT2 PR review; the engine stays candidate/non-authoritative until the pipeline
swap-over slice is separately approved.

## DAD

Preflight/lesson/asset-use/midflight-acks/postflight recorded.
