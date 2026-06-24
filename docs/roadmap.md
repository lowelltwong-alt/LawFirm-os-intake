# Intake-To-Budget Roadmap

Status is tracked for the current governed build-out branch. Each item remains synthetic-only, candidate-only, and subordinate to LawFirm OS authority boundaries until promoted by the owning repo.

## 1. Budget Template Truth Layer

Status: implemented for the current synthetic slice.

- `budget_form_mapping_report.json` proves a matter-specific budget maps into a carrier-style UTBMS workbook before filling a copy.
- `budget-form-audit` and `budget_form_template_audit_report.json` test a workbook before a matter-specific budget exists.
- `docs/budget-template-checklist.md` records known-good template requirements.
- The supplied sanitized workbook currently fails audit because original-budget formulas are incomplete; repair happens outside this repo.

## 2. Budget V1 Scenario Sets

Status: implemented for the current synthetic slice.

Emit early, standard, and through-trial budget branches with ranges while preserving the current standard proposal path for compatibility.

- `BudgetScenarioSet` is embedded in `legal_budget_proposal.json` and exported as a local candidate schema.
- The legacy proposal totals and `budget.lines` map to `standard`.
- `early_resolution`, `standard`, and `through_trial` branch totals are monotonic; hours-only budgets prove monotonicity by hours.
- Scenario branch details render in `legal_budget_review_form.md` and `matter_opening_review_package.md`.

## 3. Stronger Budget Drivers

Status: pending.

Add severity, venue, liability, coverage, and guideline/cap handling without letting defaults masquerade as observed facts.

## 4. Second Matter Family

Status: pending.

Add a second synthetic litigation family, likely auto/BI defense, to prove the engine is not med-mal-specific.

## 5. Human Review Hardening

Status: pending.

Render driver profile, scenario comparison, workbook mapping status, and unresolved budget assumptions in the final review package.

## 6. Exception Lake Package

Status: pending.

Draft mappings for broken template formulas, missing budget code mappings, unknown budget drivers, and guideline/cap issues. Intake remains dry-run only.

## 7. Cross-Repo Promotion Package

Status: pending.

Prepare candidate contract proposals for Semantic Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime.

## 8. Provider Adapter Spike

Status: pending.

Add a structured-model adapter only behind existing gates, with no external writes and deterministic comparison against synthetic gold.

## 9. Rust Readiness

Status: pending.

Keep Python as reference runtime while adding benchmark thresholds and parity requirements for future Rust hot paths.
