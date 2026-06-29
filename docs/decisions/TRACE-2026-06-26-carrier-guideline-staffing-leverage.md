# TRACE: Carrier Guideline Staffing And Leverage Projection

Date: 2026-06-26

## Decision

Implement Slice C from the carrier rate and guideline layer: synthetic
staffing/leverage rules apply only inside `CarrierCompliantProjection`.

## Why

Carrier guidelines often object to staffing mix, not just rates or expense
amounts. A reviewer needs to see how a guideline would reshape the carrier-facing
projection without letting the guideline silently rewrite the firm's proposed
budget.

## Implemented Surface

- `config/synthetic-carrier-guideline.yaml` now includes synthetic
  `staffing_rules.task_role_overrides`.
- `CarrierCompliantProjectionLine` records proposed role, compliant role,
  staffing-rule rate, staffing-rule delta, rate-cap delta, expense-cap delta,
  and whether a staffing rule applied.
- `CarrierCompliantProjection` records staffing-rule delta,
  staffing-adjusted line count, proposed/compliant blended rates,
  blended-rate delta, and a role-level leverage summary.
- Review forms render staffing-adjusted lines, leverage summary, and
  blended-rate delta.
- Tests prove an L310 associate line remains unchanged in the proposal while
  the projection moves it to paralegal and lowers blended rate.

## Boundary

This is projection-only candidate math. It does not mutate proposal lines, apply
carrier approval, authorize client or carrier submission, create a billing rule,
write Lake/SQLite records, implement connectors, promote guidelines to canon, or
learn silently from carrier behavior.

## Red-Team Notes

- Staffing reshaping can create false precision if treated as an approved
  carrier budget rather than a review projection.
- Target-role rates are inferred only from existing proposal role rates; the
  slice does not invent a new timekeeper rate.
- Preapproval thresholds, second-carrier counterfactuals, named-timekeeper
  overrides, and broader P1 budget math fixes remain separate slices.

## Validation Plan

- Export schemas.
- Run focused carrier guideline tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
