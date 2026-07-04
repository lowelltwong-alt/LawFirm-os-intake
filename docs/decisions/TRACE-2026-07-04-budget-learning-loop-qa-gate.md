# TRACE 2026-07-04: Budget Learning Loop QA Gate

## Decision

Make `budget_learning_loop_report.json` a required synthetic QA bundle artifact and a required UI detail report.

## Why

The budget learning loop builder and UI panel existed, but the aggregate synthetic QA bundle could still pass without proving that actuals variance, carrier rejection capture, appeal outcome, and reviewed-learning gate evidence were present. That left a gap between the displayed workbench and the QA evidence ladder.

## Scope

- Added `budget_learning_loop` to `QA_BUNDLE_ARTIFACTS`.
- Made the UI review data-bundle generator require the learning-loop report.
- Extended `build-synthetic-qa-review-run` to generate a deterministic synthetic learning-loop report from pinned medmal actuals/rejection fixtures.
- Extended smoke demo coverage so the bundle includes the learning-loop report before manifest/data-bundle generation.
- Refreshed the static UI demo counts and review-run fixture to show the new step.

## Boundary

This remains candidate-only and synthetic-only. The change writes local JSON/Markdown artifacts only. It does not write to SQLite, admit Exception Lake records, submit or appeal budgets, mutate carrier guidelines, perform billing writes, or silently learn from outcomes.

## Follow-Up

Add L&E-specific actuals and carrier rejection/appeal fixtures so the learning loop covers the first target practice area directly, not only the generic medmal synthetic budget chain.
