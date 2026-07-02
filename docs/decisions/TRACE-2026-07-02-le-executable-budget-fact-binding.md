# TRACE 2026-07-02: L&E Executable Budget-Fact Binding

## Decision

Add a candidate-only binding layer between executable L&E preflight fixtures and the L&E budget-fact audit. The new manifest and report prove that selected executable source bundles expose the expected budget-fact gaps with source text, source inventory refs, or dry-run exception labels.

## Why

Preflight execution alone proves that messy L&E source bundles can be ingested, segmented, hashed, and classified for safety exceptions. It does not prove that the missing facts which drive a labor/employment budget are visible to the review chain. The binding report closes that local QA gap without pretending to resolve the facts.

## Scope

- Commit `examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json`.
- Add `audit-labor-employment-executable-fact-binding`.
- Emit `labor_employment_executable_fact_binding_report.json` and `.md`.
- Include the report in schema export, smoke, synthetic QA bundle, UI review manifest, and UI local JSON contract.

## Boundaries

- Synthetic fixtures only.
- Candidate evidence only.
- No amount budget output.
- No conflict conclusion, matter opening, carrier/client submission, or billing action.
- No Lake/SQLite write.
- No model training or silent learning.
- No role taxonomy, fact taxonomy, or budget taxonomy promotion from this repo.

## Follow-Up

The binding report is not a budget precondition artifact. `build-budget` still requires the explicit `labor_employment_budget_fact_audit_report.json` when L&E fact sufficiency should gate pricing. The next higher-leverage slice is to generate more L&E fixture families through this path and then add reviewed-gold replay for budget fact audit outputs.
