# TRACE 2026-07-06: BK1 Budget Invariant Audit

## Decision

Fix the explicit-zero budget range bug and add a local candidate invariant report for the first Fable budget truth kernel slice.

## Rationale

Budget min/max math must distinguish `0.0` from missing data. The prior helper used truthiness, so a valid zero lower bound could be replaced by the point estimate. The new invariant report checks deterministic arithmetic and boundary rules before a budget run is treated as package-ready.

## Scope

- Corrected fee min/max calculations to use `is not None` checks.
- Added `budget_invariant_report.json` to budget runs.
- Extended serialized-artifact validation with BK1 invariants I1, I2, I4, I5, I13, and I15.
- Kept this slice synthetic-only and candidate-only.

## Non-Goals

- No scenario policy hardening.
- No scenario-selection behavior change.
- No carrier-rate calibration, real-data ingestion, budget approval, carrier submission, or Exception Lake write.
