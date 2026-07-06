# TRACE 2026-07-06: BK4/BK7 Rate Projection Guardrails

## Decision

Fail closed on unsafe synthetic carrier-rate resolution and expose signed carrier-compliant projection deltas without removing legacy positive-delta fields.

## Rationale

Fable's budget truth kernel identified two ways the budget POC could look precise while hiding uncertainty or adverse guideline impact:

- carrier/state rate resolution could silently price by a default carrier or default state when confirmed carrier-role parties or jurisdictions did not match the synthetic rate card;
- carrier-compliant projection deltas clamped at zero, so a staffing rule that made a line more expensive could appear to have no impact.

The fix keeps the proposal candidate-only and human-review-only: unsafe rates produce hours-only output with explicit review issue codes, and compliant increases now carry signed deltas plus review flags.

## Scope

- Added deterministic carrier alias matching with role precedence: `insurance_carrier`, then `instructing_source`, then `payer`.
- Added hours-only review status for unmatched carrier-role parties, unmapped confirmed jurisdictions, and same-role multi-carrier ambiguity.
- Added named-timekeeper title-mismatch handling so mismatched overrides do not silently fall back to role rates.
- Added signed projection delta fields, compliant-increase fields, and per-line review issue codes while preserving legacy nonnegative delta fields.
- Passed resolved role-rate schedules into carrier projection so staffing reshapes use the carrier card instead of first-seen budget-line rates when available.
- Extended review text, coherence checks, schemas, and regression tests for the new guardrails.

## Non-Goals

- No fuzzy carrier matching, real carrier guidelines, real negotiated rates, or public/procurement rate ingestion.
- No canonical party-role, rate, guideline, event, or exception taxonomy promotion.
- No conflict conclusion, engagement decision, matter opening, budget approval, carrier submission, Lake/SQLite write, connector write, or silent learning.
- No change to BK5 intensity normalization or other headline-total policy changes.
