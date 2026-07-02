# TRACE 2026-07-02: L&E Budget Fact Gold Gate

## Decision

Add a reviewed synthetic-gold gate for deterministic labor/employment budget fact audit outputs.

## Why

The L&E budget fact audit is now central to budget safety: it decides whether a matter is blocked, range-only, or candidate-ready for review. Unit tests are useful, but the QA process needs a committed reviewed-gold artifact that can be replayed by smoke, CI, and the read-only review UI.

## Scope

- Commit `examples/synthetic/gold/labor-employment-budget-fact-gold.json`.
- Add `validate-labor-employment-budget-fact-gold`.
- Emit `labor_employment_budget_fact_gold_report.json` and `.md`.
- Compare exact readiness state, counts, critical/warning gap IDs, relationship topology, selected finding states, source label refs, source-ref completeness, and no-write/no-budget boundaries.
- Include the report in schema export, smoke, synthetic QA bundle, UI review manifest, and frontend local JSON contract.

## Boundaries

- Synthetic gold only.
- Candidate QA evidence only.
- No fact resolution.
- No amount budget output.
- No budget submission, matter opening, conflict conclusion, Lake/SQLite write, model training, silent learning, or taxonomy promotion.

## Follow-Up

Expand this gold gate as more L&E fixture families become executable and as budget fact audit outputs mature into reviewed-gold replay cases.
