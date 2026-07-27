# Decision Trace — DT5 Multi-Line Canonical Pricing (Auto BI / GL / EPLI)

Slice: post-marathon workstream, successor to DT4 (PR #126, squash-merged).
Branch: `claude/dt5-multi-line-pricing`, off `main`. Candidate-only,
synthetic-only, deterministic; no ML, no promotion.

## Situation

The pricing engine (DT2) and pipeline stage (DT3) covered only med-mal. The CLCM
publishes distinct stage-share vectors and median hours for automobile tort,
premises liability, and employment — so absorbing the contract's other three
lines needed only a contract revision plus a small engine change. While mapping
the lines, a **contract bug** surfaced: the auto line defines `trial_likelihood`
and `appeal_likelihood` but never declared them as universal overrides, so the
universal `trial_posture` would have **double-counted trial** for auto matters.

## Decision

**Contract v1.1.0-candidate** (authored in the substrate, re-vendored digest
`4fd1f971… → 587e3b92…` through the deliberate re-pin path — third exercise):

1. `phase_baseline` restructured to **per-case-type** vectors, each from the
   CLCM's own Table 4 stage shares (Initiate+Settlement→L100, Pretrial→L200,
   Discovery→L300, Trial→L400, Post-disposition≈L500; whole-percent rounding
   residual added to L400 and recorded per vector):
   professional_malpractice 14/11/25/43/7 · automobile_tort 14/10/21/47/8 ·
   premises_liability 17/14/19/42/8 · employment 18/15/21/39/7.
2. **Auto override fix**: `universal_overrides` now maps
   `trial_posture→trial_likelihood`, `appeal→appeal_likelihood` (as med-mal
   already did) — trial can no longer double-count.

**Engine**: `LINE_TO_CLCM_CASE_TYPE` extended to all four lines; fractions read
from `by_case_type`. Nothing else changed — explicit profiles (`DT4`) already
support any line.

**Corpus**: the stratified corpus embeds the contract digest and plan ids, so it
was regenerated and re-frozen against v1.1 (same 174 matters, same split; new
digests).

## Observed results (test-pinned)

- **Auto** (attorney-involved severe trial-bound): base 196 hrs; L400 multiplier
  2.5×2.15×3.0 = 16.125 → **capped at 10.0**; L300 2.5.
- **EPLI class/systemic/punitive** — the correlated group's capped composite
  exercised for real: L100 = 6.0 × √4.5 × √2.5 × 1.65 ≈ 33.2 → **cap 10.0**;
  L400 (single group member) = largest-in-full **6.0**; partial group (multi_2_9
  + harassment) = 1.9×1.5 = **2.85**, uncapped.
- **GL catastrophic disputed-notice**: base 218 hrs; L100 11.86 → cap 10.0.
- **Med-mal regression pinned unchanged** (2.325 / 3.47375 / 202.96 base hours).

## Non-decision

- The pipeline's canonical stage still prices only med-mal (its inputs are the
  legacy med-mal sizing drivers); other lines price via explicit profiles. Wiring
  line-specific elicitation into the pipeline is future work.
- CLCM category labels are not line-exact (e.g. "employment" vs EPLI defense);
  confidence stays sourced_medium and `reference_class_only`.

## Evidence

`tests/test_multi_line_pricing.py` — 6 tests (failing-test-first): auto baseline +
cap + discovery multiplier; auto override fix (no `trial_posture`/`appeal` in the
line's driver ids); premises baseline + cap; EPLI full-group composite + cap and
single-member-full; partial group uncapped exact value; med-mal v1.1 regression
pin. All five DT suites green together (45).

## Alternatives rejected

- **One global phase vector for all lines.** Rejected: the CLCM publishes
  per-case-type vectors; using med-mal's for auto would misprice trial by 4pts
  and discovery by 4pts.
- **Leaving the auto double-count for later.** Rejected: it is a correctness bug
  in the contract; fixed in the same revision that touches the file.

## Validation

45/45 across DT suites; conformance gate green; ruff check + format clean;
`export_schemas` idempotent (530); stratified corpus regenerated + frozen. Full
local CI reproduction run bare on the committed tree, marker-verified, before
merge. No UI change.

## Human gate

Owner pre-authorized squash-merge on green local CI for this slice sequence.
Substrate contract promotion remains open.

## DAD

Preflight/lesson/asset-use/midflight-acks/postflight recorded.
