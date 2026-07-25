# Decision Trace — DT1 Budget-Driver-Taxonomy@v1 Adapter + Conformance Gate

Slice: post-marathon workstream. Branch: `claude/budget-driver-taxonomy-v1`, off
`main`. Candidate-only, synthetic-only, deterministic; no ML, no promotion.

## Situation

The intake runtime's 5 sizing drivers (`party_count`, `injury_severity`,
`liability_clarity`, `exposure_band`, `venue`) drifted from the canonical driver
taxonomy in the semantic-substrate repo (~24 drivers after two research passes;
overlap of 2). The hazard was not the count mismatch but that intake silently
assumed baseline values for every driver it did not collect — violating the
fail-closed invariant ("every serialized derived value recomputed or
rule-attributed, never silent None/default"). Drift was possible because nothing
enforced alignment.

## Decision

Contract-first reconciliation, in four parts:

1. **Machine-readable canonical contract.** The two-pass-researched taxonomy is
   encoded as `budget-driver-taxonomy@1.0.0-candidate` (authored in the substrate:
   `docs/poc/budget-driver-taxonomy.v1.candidate.json`; proposal posture,
   not promoted canon). It carries the universal driver layer with the real FJC
   regression coefficients, four line layers (med-mal deep, EPLI, GL/premises,
   auto BI), subtype priors, a composition rule (capped composite for correlated
   drivers), confidence tags (`sourced_high`/`sourced_medium`/`anchored`/
   `judgment`) as first-class fields, and the legacy-intake mapping. The
   **phase-baseline vector is CLCM-sourced** (NCSC Civil Litigation Cost Model,
   Hannaford-Agor & Waters 2013, professional-malpractice stage shares: L100 14% /
   L200 11% / L300 25% / L400 43% / L500 7%; 472 median attorney hours) — the
   pass-3 dig that finally found public task-level hours data.
2. **Vendored, digest-pinned copy.** Intake consumes a byte-pinned copy
   (`config/budget-driver-taxonomy.v1.json`); `load_driver_taxonomy` recomputes
   sha256 (newline-normalized) against `EXPECTED_CONTRACT_DIGEST` and refuses any
   drifted/tampered copy. The CLCM update mid-slice exercised the deliberate
   re-pin path end-to-end (digest 227c86fb… → 4fd1f971…).
3. **Legacy → canonical adapter** (`driver_taxonomy.build_canonical_driver_profile`):
   maps the 5 legacy drivers via the contract's exhaustive level maps (unknown key
   or level = fail-closed error; lossy mappings carry a `mapping_note`; `venue`
   becomes a recorded posture passthrough, never a silent drop). **Every canonical
   driver of the line is assigned exactly once**: elicited, or `not_elicited` with
   a rule-attributed assumption note (neutral multiplier 1.0). Required-but-missing
   drivers (e.g. `implicated_specialties`, `trial_likelihood`) surface the existing
   `missing_required_budget_driver` exception trigger — typed for review, not
   auto-blocked.
4. **Conformance gate** (`scripts/validate_driver_taxonomy_conformance.py`, wired
   into `run_ci_locally.sh`): digest pin check; sizing-policy drivers ⊆ mapping and
   mapping ⊆ sizing-policy (both directions); every canonical target and mapped
   level valid against the contract. Re-drift is now a red build.

## Non-decision

- The deterministic pricing engine (phase-baseline × driver multipliers ×
  governed rates) is NOT built in this slice — the contract encodes the math
  contract; wiring it into `case_sizing` is the next slice.
- No change to `case_sizing` behavior, the sizing policy, or any prior module.
- No ML; dollars stay deterministic; no promotion; substrate canon untouched
  (contract is a docs/poc proposal awaiting the substrate's gates).

## Evidence

`tests/test_driver_taxonomy.py` — 11 tests (failing-test-first): digest pin +
tamper rejection; full-profile mapping (every line driver assigned once, correct
levels, venue passthrough); not_elicited-as-explicit-assumption; required-missing →
exception candidate; unknown key/level fail-closed; profile silent-default
rejection; assignment model fail-closed; conformance gate passes on repo and
catches an unmapped sizing driver.

## Alternatives rejected

- **Intake keeps its own driver vocabulary, documents map informally.** Rejected:
  that is exactly how the drift happened; documents cannot enforce.
- **Silent baseline defaults for un-collected drivers.** Prohibited by the
  fail-closed invariant; every assumption is explicit and attributed.
- **Cross-repo live read of the substrate contract.** Rejected (fragile across
  machines); vendored digest-pinned copy with a conformance gate instead.

## Risks and rollback

- Contract magnitudes remain `reference_class_only` (confidence-tagged); the
  contract cannot claim calibration (loader refuses `calibrated != false`).
- CLCM vintage is 2012, n=312, "professional malpractice" not med-mal-specific;
  recorded on the contract. Rollback is a single-branch revert; the adapter is
  additive and nothing consumes it yet.

## Validation

Targeted tests 11/11 green; conformance CLI green; `export_schemas` (+2 schemas:
`canonical-driver-assignment`, `canonical-driver-profile`); ruff check + format
clean; full validation suite green (rerun after the CLCM re-pin). No UI change.

## Human gate

Substrate contract promotion (CODEOWNERS/AUTHORITY_MAP review) remains open; the
intake PR is the review surface for the adapter. Agent does not merge its own PR.

## DAD

Preflight/lesson/asset-use/midflight-acks/postflight recorded through the
daemon-era `asset-dir` pipeline.
