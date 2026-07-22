# DAD Candidate Lesson/Asset Packet (ungoverned local candidate)

Packet id: dad-candidate-serialized-derived-value-trust.v0_1
Date: 2026-07-21
Status: candidate only — no DAD write performed. The governed DAD front door was
not exercised from this session (the prior slice's DAD preflight failed at the
central usage trace with an ACL error; this packet preserves observable evidence
for a later governed retry). Contains only observable evidence and decisions — no
hidden chain-of-thought.

## Lesson

Every displayed **derived** value on a serialized "ready" review artifact must be
recomputed from the serialized rows it summarizes, on **every** trust boundary
that renders it — not only the ones a prior slice happened to harden.

## Observable evidence

- Fresh hostile mutations against the merged trust-hardening slice (PR #107):
  altering `comparison.total_variance_amount` 6260.0 -> 1.0, `total_variance_
  percent` 11.57 -> 0.1, a phase row `variance_amount` -> 999999, and budget-input
  `total_proposed_budget` 54090 -> 99999 or `subtotal_fees` 49990 -> 88888 were
  each **accepted** by a `ready_for_review` artifact before the fix.
- Root cause (file evidence): `models.py` `BudgetActualComparisonReport` had no
  model validator; `SyntheticActualsWorkbenchReport` reconciled totals but not
  variance; TS `assertSyntheticActualsWorkbenchReport` also omitted variance;
  `SyntheticBudgetInputWorkbenchReport` reconciled per-line totals but never the
  report subtotals/total (the TS contract already did).
- After the fix the same mutations raise `ValueError` (Python) and push
  `synthetic_actuals_workbench_total_variance_not_reconciled` /
  `..._row_variance_not_reconciled` (TS); the real fixtures still validate; a
  materially different family (wage-hour, 27.24% variance) round-trips cleanly.

## Assumptions

- Recomputation must mirror the builder's arithmetic exactly (variance uses plain
  `round(x, 2)` and yields `None` when actuals are absent or `budgeted_total == 0
  and actual > 0`), or the fix falsely rejects valid fixtures.
- The serialized `checks[]` array is attacker-controllable, so a green check is
  not evidence; only model-level recomputation is.

## Applicability

- Any serialized review artifact with a displayed derived total/summary/variance
  that a human decision depends on, across both the Python model and the TS data
  contract (and the browser smoke that proves TS rejection).

## Non-applicability

- Intentionally `blocked_*` artifacts stay serializable when their internal math
  is coherent (blocking comes from a failed check, not tampered math); universal
  recomputation must not reject them.
- Does not authorize real data, calibration, learning, submission, matter
  opening, Lake/SQLite/external writes, or XGBoost training.

## Danger if misapplied

- Using `_round_money` (half-up) where the builder used `round` (half-even), or
  enforcing variance only when `ready`, would either falsely reject valid
  fixtures or leave a fail-open window. Recompute universally, match the builder.

## Deferred sibling gaps (see Codex handoff)

F3 actuals fee/expense split, F4 guideline gross reductions/increases, F5
rate-card override count, F6 guideline/rejection builder immutable-snapshot
parity — same lesson, not yet applied.
