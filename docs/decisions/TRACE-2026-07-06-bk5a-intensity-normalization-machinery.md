# TRACE 2026-07-06: BK5a Intensity Normalization Machinery

## Decision

Add baseline-relative intensity normalization machinery behind the existing `raw` default without changing current budget totals.

## Rationale

Fable's BK5 kernel showed that default matter-family intensity tiers can double-count template assumptions when multipliers are treated as absolute values. The number-changing fix requires human sign-off, so this slice only builds the deterministic machinery needed for a later reviewed policy flip.

## Scope

- Added effective intensity policy construction in `drivers.py`.
- Preserved `normalization: raw` as the default and current behavior.
- Added `baseline_relative` support that normalizes each driver tier against the template-declared baseline, falling back to matter-family defaults.
- Stored raw policy, effective policy, normalization mode, and baseline tiers on `CaseDriverProfile`.
- Updated budget intensity notes to show raw and effective multipliers.
- Added tests for raw-mode preservation, default-tier neutrality under baseline-relative mode, phase-specific ratios, and template baseline override.

## Non-Goals

- No flip of `config/budget-driver-policy.yaml` to `baseline_relative`.
- No approved signoff artifact, fixture-golden regeneration, or headline-total policy change.
- No real-data calibration, real rate ingestion, canonical driver-taxonomy promotion, budget submission, matter opening, Lake/SQLite write, connector write, or silent learning.
