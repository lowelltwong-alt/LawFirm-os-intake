# TRACE 2026-07-06: L&E Nonlinear Template Contract Audit

## Status

Accepted as a local candidate-only intake slice.

## Context

Fable's L&E class/collective/PAGA kernel identified a high-risk budget failure mode:
class, collective, and PAGA defense work is stepwise and scenario-driven. A linear
claimant-count multiplier would hide certification, manageability, notice,
representative discovery, settlement-administration, and PAGA penalty/exposure
boundaries behind a misleading smooth budget.

The repo already had L&E critical-fact audits, executable fixtures, driver-impact
reports, blocked-review packets, output expectation gates, and replay slots. It did
not have a deterministic contract proving the nonlinear template skeleton itself was
safe to consume before a future priced budget path uses it.

## Decision

Add a synthetic-only nonlinear template contract and audit command:

- `examples/synthetic/labor-employment/labor-employment-nonlinear-budget-templates.json`
- `src/lawfirm_os_intake/labor_employment_nonlinear_templates.py`
- `lawfirm-os-intake audit-labor-employment-nonlinear-budget-template-candidates`

The audit validates:

- required `le-class-collective-defense` and `le-paga-shaped-defense` templates;
- C100-C600 phase skeletons;
- t0-t4 tier rows on tiered phases;
- t4 collective scale blocking with `collective_scale_requires_staffing_plan`;
- no cross-tier interpolation;
- period-month drivers only on `data_scope_task=true` tasks;
- PAGA manageability gate and no opt-in task leakage;
- PAGA penalty/exposure tasks do not authorize money or exposure modeling;
- human scenario/template-selection gates for certification, manageability, and
  hybrid PAGA/class posture.

## Boundary

This slice does not add priced L&E budget generation, real rates, carrier rates,
public-data ingestion, connector writes, Exception Lake/SQLite writes, budget
submission, matter opening, conflict conclusions, canonical taxonomy promotion, or
silent learning.

The artifact is a local candidate contract. Humans still own template selection and
nonlinear modeling choices. Legal Knowledge Runtime still owns governed research and
rate/proxy source retrieval.

## Tests

Added `tests/test_labor_employment_nonlinear_templates.py`.

Focused validation:

```text
python scripts\export_schemas.py
python scripts\run_full_pytest.py tests\test_labor_employment_nonlinear_templates.py -q
```

The focused test covers successful audit output and fail-closed reports for missing
tier rows, interpolation, period-driver misuse, PAGA penalty/exposure pricing,
PAGA opt-in leakage, and missing scenario gates.

## Follow-Ups

- Wire this report into the L&E budget QA ladder once the actual tiered math path is
  ready.
- Keep BK5b headline normalization paused until explicit human approval.
- Build future priced `tiered_v1` math only after the contract remains green under
  reviewed synthetic fixtures and policy-signoff gates.
