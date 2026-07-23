# Decision Trace — CW7 Regime Seam + Hardening + Delivery (END OF PROGRAM)

Wave: CW7 of the converged Opus marathon. Branch: `claude/cw7-regime-delivery`,
stacked on CW6. Candidate-only, synthetic-only, deterministic.

## Situation

The vertical (CW1–CW6) needs an economic-regime seam so carriers/case-types/regimes
compose as data packs (N+M+K, not N×M×K), a hostile-fixture sweep proving every new
serialized artifact fails closed, differential/monotonicity checks across packs, and
a delivery packet documenting capabilities, boundaries, synthetic status, and the
firm-data recalibration path.

## Decision

1. **Economic regime seam** — `EconomicRegimeProfile` (data-only) selecting payer,
   rate source, constraint-pack kind, proportionality policy, staffing norm, and
   transport; `EconomicRegimeCatalog` requires exactly one active, non-stub profile
   and at least one stub. `config/synthetic-economic-regime-profiles.yaml` ships
   insurance-defense **active** and a white-shoe **stub** proving the seam, with the
   corporate-OCG-as-pack note (corporate OCGs are a constraint pack of the same rule
   IR — no new rule language).
2. **Hostile-fixture sweep** — `tests/test_hostile_fixture_sweep.py` applies the
   workbench trust-suite methodology to every new serialized artifact
   (PackSelectionDecision, AdjustmentLedger, SizedWorkPlan, ProportionalityAssessment,
   SettlementPostureAnalysis, FirmExcelBudgetExport, RouterEvaluationReport,
   FirmCheckpointPacket, OCGContractReconciliationReport): build valid, tamper one
   reconciled field, assert the model validator rejects it.
3. **Differential + monotonicity fuzz** — carrier-a vs carrier-b projections are
   internally consistent (each ledger reconciles) and distinct (different pack content
   hashes); the signed category deltas partition the total delta within rounding.
4. **Delivery packet** — `DeliveryPacket` (built by `build_delivery_packet`) lists
   capabilities, boundaries, the hostile-swept artifacts, the firm-data recalibration
   path, and the open human gates (firm checkpoint, Substrate review, per-wave
   reviews); fail-closed on missing sections.

## Non-decision

- White-shoe is a stub proving the seam, not a designed-around regime.
- No ML; no calibration/accuracy claim; the ML challenger stays a later shadow lane.
- No change to the CW1–CW6 engine — CW7 is additive (a data-only seam + tests + a
  delivery report).

## Authority impact

Local candidate work; new candidate schemas + a data-only regime config. No
canonical/promoted change; no cross-repo write.

## Evidence

- `tests/test_regime_and_delivery.py` (6) + `tests/test_hostile_fixture_sweep.py` (10).
- Three exported schemas; regime config under `config/`.
- Delivery packet enumerates capabilities/boundaries/recalibration/open-gates.

## Alternatives rejected

- **N×M×K templates per carrier×case×regime.** Rejected for the composition seam
  (packs compose at runtime).
- **Assert regime/pack numeric equivalence in the differential fuzz.** Rejected — the
  packs legitimately differ; the invariant is internal consistency + distinctness,
  not equality.

## Risks and rollback

- Risk: the regime seam is mistaken for a firm-ready multi-regime product. Contained
  by the active/stub split, candidate status, and the delivery boundaries. Rollback is
  a single-branch revert; additive.

## Validation

ruff check/format clean; `export_schemas.py` idempotent (three new schemas);
`validate_repo.py` passed; `run_full_pytest.py -q` full suite passed; `npm run build`
+ `npm run smoke:browser` OK (no UI change this wave).

## Human gates

CW7 human gate: **delivery review**. Opened by the agent; it does not merge its own
PR and does not push `main`. **END OF PROGRAM** — the marathon's remaining real gate
is the firm checkpoint (real dispositions), which the CW5 synthetic placeholders do
not satisfy.

## DAD

Per-wave preflight/lesson/postflight through the canonical `asset-dir` lesson
pipeline.
