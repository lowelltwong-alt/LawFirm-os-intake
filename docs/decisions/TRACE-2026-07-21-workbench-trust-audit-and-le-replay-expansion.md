# TRACE: Workbench Trust Audit And L&E Replay Expansion

Date: 2026-07-21
Status: Stage A audit complete; two P1 fail-open gaps fixed; Stage B (L&E replay
expansion) scoped and handed off. Candidate-only; validation only.

## Objective

Independently verify the merged serialized-workbench trust-hardening slice
(PR #107) with fresh hostile mutations, fix any fail-open defect without
weakening fail-closed behavior, then expand deterministic L&E replay coverage.
No real matters, rates, carrier payloads, or public-case payload text.

## Stage A: Independent Trust Audit

Method: read the six `Synthetic*WorkbenchReport` model validators
(`src/lawfirm_os_intake/models.py`), the builders, and the TypeScript data
contract; then ran fresh mutation probes (different fields than the existing
tests) against the checked demo fixtures. All eight explicitly-hardened
categories rejected. Nine further "preserve the headline" probes exposed
fail-open gaps.

### Findings (severity, evidence)

| ID | Sev | Finding | Evidence |
|----|-----|---------|----------|
| F1 | HIGH | Actuals variance never recomputed: `comparison.total_variance_amount`, `total_variance_percent`, and per-row `variance_amount`/`variance_percent` accepted arbitrarily on a *ready* report while budgeted/actual totals stay reconciled. Variance is the headline review signal. | `models.py` `BudgetActualComparisonReport` had no validator; actuals validator reconciled totals only. TS `assertSyntheticActualsWorkbenchReport` also omitted variance. Displayed at `synthetic_actuals_workbench.py` markdown. |
| F2 | HIGH | Budget-input `subtotal_fees`/`subtotal_expenses`/`contingency_amount`/`total_proposed_budget` not reconciled to lines in Python (TS `data-contract.ts` already guarded them). Python trust boundary weaker than TS. | `SyntheticBudgetInputWorkbenchReport` validator checked per-line only. |
| F3 | MED | Actuals row fee/expense split unbound (Python+TS): `fee+X / expense-X` preserves row and report totals. | `models.py` / `data-contract.ts` check only `total == fees+expenses`. |
| F4 | MED | Guideline `gross_reductions`/`gross_increases` not tied to line-level deltas; both inflatable by equal X (net_delta preserved). | guideline validator ties only their difference to `net_delta`. |
| F5 | LOW | Rate-card `named_timekeeper_override_count` structurally unvalidated (no backing row field). | rate-card validator never checks it; row model has no override flag. |
| F6 | MED | Immutable-snapshot enforcement inconsistent: only actuals/input/configuration builders have `source_inputs_unchanged_during_build`. Guideline & rejection builders read each source via multiple independent `read_text()` calls; mitigated (not closed) by a pinned-digest check read from yet another independent read. | `synthetic_rejection_appeal_workbench.py`, `synthetic_guideline_projection_workbench.py`. |

Robustness confirmed (no gap): rate-summary math, config effect-bucket swap,
rejection case money, deep nested `*_sha256` corruption, actuals row-component
recon, single-view break, guideline line+subtotal+total-with-preserved-delta,
null pricing in a priced projection, and a compensated cross-case rejection
money move all rejected under fresh probes.

## Fix (F1 + F2 — the two HIGH fail-open gaps)

- Actuals model now recomputes per-row and total variance from the reconciled
  money, mirroring the builder's `round()`/zero rules (percent `None` when
  `budgeted_total == 0 and actual > 0`; total variance `None` when actuals
  absent). Universal (blocked artifacts stay serializable because their internal
  math is coherent).
- Budget-input model now recomputes `subtotal_fees`/`subtotal_expenses` and
  `line_fee_total + line_expense_total + contingency == total_proposed_budget`
  from lines on a ready report, at parity with the TS contract.
- TS `assertSyntheticActualsWorkbenchReport` gained matching per-row and total
  variance reconciliation
  (`synthetic_actuals_workbench_row_variance_not_reconciled`,
  `..._total_variance_not_reconciled`).
- Five failing-mutation regression tests added to
  `tests/test_synthetic_workbench_serialized_coherence.py`; two false-
  serialization cases added to the browser smoke.

Each mutation failed before the validator was strengthened and passes after
(TRACE "failing mutation first" methodology).

### Before/after coverage matrix (Python + TS serialization boundary)

| Derived value | Before | After |
|---------------|--------|-------|
| Actuals total variance amount | trusted | recomputed (Py+TS) |
| Actuals total variance percent | trusted | recomputed (Py+TS) |
| Actuals per-row variance amount/percent | trusted | recomputed (Py+TS) |
| Budget-input subtotal_fees/expenses | Py trusted / TS guarded | recomputed (Py+TS) |
| Budget-input total_proposed_budget | Py trusted / TS guarded | recomputed (Py+TS) |
| Actuals row fee/expense split (F3) | trusted | trusted (deferred) |
| Guideline gross reductions/increases (F4) | trusted | trusted (deferred) |
| Rate-card override count (F5) | trusted | trusted (deferred) |
| Guideline/rejection source snapshot (F6) | pinned-digest only | pinned-digest only (deferred) |

## Verification

- `python -m pytest tests/test_synthetic_workbench_serialized_coherence.py
  tests/test_synthetic_workbench_source_integrity.py
  tests/test_synthetic_workbench_portfolio.py` → 41 passed (5 new tests
  included), run with `LAWFIRM_OS_VALIDATION_RUNTIME_POLICY` set and
  `PYTHONPATH=src`.
- Swept every repo JSON mapping to the two models: only the two demo fixtures
  exist and both still validate; no fixture regressed.
- Confirmed the new variance recon is correct on a materially different family
  (wage-hour actuals: 27.24% over-threshold variance built and round-tripped
  through the hardened model).
- Full Linux `scripts/run_full_pytest.py` + TS `npm run build` +
  `npm run smoke:browser` remain the exact-head publication gate (see handoff).

## Boundaries

Validation only. No authority change: no real data, external writes,
calibration, learning, budget submission, conflict clearance, matter opening,
Lake, or SQLite writes. No connectors, canonical Substrate contracts,
Orchestrator persistence, real-rate calibration, Rust replacement, or predictive
training touched.

## Stage B status

The 8 L&E families are declared in the learning-fixtures and seed manifests, but
the outcome-replay input pack wires executable builder inputs for only 5
(discrimination, wage-hour, epli, class-collective partial, ada-fmla blocked).
The three families without executable replay-input artifacts
(retaliation/wrongful-termination, restrictive-covenant/trade-secret,
administrative-exhaustion), the missing-attachment and non-ADA adversarial
replay cases, and the materially-different-proposal workbench coverage require
authoring new coherent, source-bound fixtures plus recounting several hardcoded
test expectations. Remaining work and precise code hints are captured in
`docs/ai-handoff/CODEX_LE_REPLAY_EXPANSION_REMAINING_2026-07-21.md`.

## XGBoost boundary

Untouched. No training/tuning from synthetic fixtures. Any calibration remains a
later governed slice with temporal splits, leakage checks, intervals, SHAP, and
a deterministic baseline challenger.

## DAD status

A governed DAD candidate lesson packet is proposed in the handoff; no cross-repo
or DAD writes were made from this session.
