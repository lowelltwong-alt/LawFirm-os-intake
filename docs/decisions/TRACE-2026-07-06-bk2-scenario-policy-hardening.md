# TRACE 2026-07-06: BK2 Scenario Policy Hardening

## Decision

Harden local candidate budget scenario policy so invalid phase cutoffs block, scenario monotonicity is validated by phase order, and incomplete probability weights are visible for human review.

## Rationale

A typo in a scenario `resolution_phase` must never expand a budget to every phase or produce a plausible headline number. Scenario order in policy files is display order, not proof order, so monotonic validation must sort by the template phase cutoff while preserving the emitted order. Probability weights are synthetic review inputs; when they are partial or do not sum to 1.0, the artifact must say why expected value was not computed or was bounded.

## Scope

- Changed invalid `resolution_phase` handling from "include every phase" to deterministic `scenario_policy_invalid` blocking.
- Preserved scenario display order while validating monotonic totals by phase cutoff.
- Added scenario-set status, probability-integrity status, and policy issue codes/notes.
- Extended `budget_invariant_report.json` coverage to BK2 invariants I6, I8, and I10.
- Added deterministic tests for Fable counterexamples CE1, CE9, and CE10.

## Non-Goals

- No scenario vocabulary promotion to Semantic Substrate.
- No carrier guideline, rate-card, or real-rate calibration change.
- No budget approval, carrier submission, matter opening, conflict conclusion, Exception Lake write, or connector write.
- No headline total policy change beyond blocking invalid scenario policy and surfacing probability review issues.
