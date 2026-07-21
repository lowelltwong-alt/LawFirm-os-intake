# TRACE: Serialized Workbench Trust Hardening

Date: 2026-07-18
Status: implemented candidate-only hardening

## Decision

Treat every checked workbench JSON artifact as an independently hostile serialization boundary. Derived summaries, financial partitions, displayed alternate views, and provenance digests must be recomputed or structurally validated from the serialized rows they claim to summarize.

## Evidence

A mutation probe showed that three otherwise-valid fixtures still accepted false derived values: a rate-card average, a budget-configuration effect bucket, and a rejection case recovered amount. Independent review also found that the actuals builder hashed one read of each source and parsed a later read, allowing a mid-build mutation to detach displayed math from the recorded digest.

## Implementation

- Rate-card carrier/state/title counts and per-carrier/state summaries are recomputed from serialized rows.
- Budget-configuration effect counts are recomputed by exact key and value.
- Rejection/appeal case IDs, source-bound readiness, per-case partitions, and aggregate disputed/recovered/write-down totals are validated.
- Actuals phase/code displayed rows are independently reconciled to report totals.
- Guideline projection lines, fee/expense subtotals, contingency, and priced totals are independently reconciled.
- All six workbench provenance fields require an exact lowercase SHA-256 reference.
- Actuals parsing and hashing use one captured source snapshot, followed by an end-of-build unchanged-source check.
- Browser smoke dynamically loads the TypeScript data contract and proves representative false serializations are rejected.
- Python and TypeScript use an explicit half-up cent rule, with positive and negative half-cent parity tests.
- The checked actuals fixture, UI bundle, and Rust fixture manifest were refreshed together.

## Boundaries

This changes validation only. It does not authorize real data, external writes, calibration, learning, budget submission, conflict clearance, matter opening, Lake writes, or SQLite writes.

## Verification

- TypeScript strict compile passed.
- The corrected focused hostile-fixture suite passed 45 tests.
- A pre-fix full suite exposed two blocked-actuals compatibility failures; reconciliation was narrowed to ready artifacts while component arithmetic remains universal.
- Rust fixture manifest, UI bundle source-hash, and fixture snapshot-coherence gates passed after the deterministic fixture refresh.
- Full Linux validation remains the exact-head publication gate.

## Independent Review

The first Terra oracle review identified the actuals immutable-snapshot defect and weak digest checks. A fresh independent review then found four additional P1 gaps: budget-input context hashes were not validated by Python, actuals row components were not reconciled to row totals, Python guideline deltas were not tied to proposal/compliant totals, and priced projections accepted null fee values. The hostile digest sweep also found unvalidated nested rejection source hashes. Each finding received a failing mutation before the validator was strengthened. The Luna corpus review identified the next highest-value evidence gaps: missing replay coverage for three L&E families, no missing-attachment replay, narrow adversarial coverage, and overuse of one clean EPLI proposal across downstream panels.

## DAD Status

The governed DAD preflight was attempted and failed at the central usage trace with an ACL error. No cross-repo or DAD writes were made. This local trace preserves observable evidence and decisions for a later governed learning-loop retry.

## Next Slice

Expand deterministic L&E replay coverage for retaliation/wrongful termination, restrictive covenant/trade secret, and administrative exhaustion; add missing-attachment and a non-ADA adversarial case; then exercise budget input and actuals against a materially different wage-hour or class/collective proposal.
