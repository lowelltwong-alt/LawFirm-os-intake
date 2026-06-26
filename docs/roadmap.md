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

Status: implemented for the current synthetic slice.

Add severity, venue, liability, coverage, and guideline/cap handling without letting defaults masquerade as observed facts.

- Severity, liability, and venue drivers can apply bounded intensity multipliers from local synthetic policy.
- Cumulative multipliers are capped by policy.
- Coverage posture remains a review boundary and is not blended into defense-fee math.
- Synthetic guideline caps produce `BudgetGuidelineFlag` records and unknown/review text; they do not rewrite rates, hours, or totals.
- `BudgetDriverEffect` records expose driver value, provenance, structured policy ref, applied phases/tasks, and whether a default was used as an observed fact.

## 3A. Carrier Guideline Projection

Status: implemented for the current synthetic slice.

Apply synthetic carrier guideline caps as a separate proposed-vs-compliant projection without mutating the proposed budget.

- `config/synthetic-carrier-guideline.yaml` is a synthetic-only candidate artifact, not a real carrier guideline.
- `CarrierCompliantProjection` is embedded in `legal_budget_proposal.json` and exported as a local candidate schema family.
- Rate and expense caps apply only inside the projection view; proposal lines stay unchanged.
- Review surfaces render proposed total, compliant total, deltas, capped lines, and submission boundaries.
- `ReviewPackageCompletenessReport` fails closed if the projection surface loses `rewrites_budget=false`, unchanged proposal posture, or no-submission state.

## 4. Second Matter Family

Status: implemented for the current synthetic slice.

Add a second synthetic litigation family, likely auto/BI defense, to prove the engine is not med-mal-specific.

- `auto_liability_defense` now has synthetic driver defaults and a UTBMS-coded budget template.
- `carrier-assignment-auto-bi.json` and its confirmation fixture run through preflight, human confirmation binding, budget generation, and final review package creation.
- Tests prove the auto/BI family ranks from observed source text and uses the auto template rather than the med-mal template.

## 5. Human Review Hardening

Status: implemented for the current synthetic slice.

Render driver profile, scenario comparison, workbook mapping status, and unresolved budget assumptions in the final review package.

- Budget runs now write `case_driver_profile.json` and embed a `BudgetDriverProfileSummary` in `legal_budget_proposal.json`.
- `legal_budget_review_form.md` and `matter_opening_review_package.md` render driver profile summary, scenario comparison, workbook mapping status, and unresolved budget assumptions.
- Workbook mapping status fails closed as review posture: no template-backed workbook render is assumed unless a mapping report exists, and workbook submission remains unauthorized.
- `ReviewPackageCompletenessReport` now requires those human-review sections and verifies the driver-profile summary, non-observed-fact boundary, workbook mapping posture, and unresolved budget assumptions before package acceptance.

## 6. Exception Lake Package

Status: implemented for the current synthetic slice.

Draft mappings for broken template formulas, missing budget code mappings, unknown budget drivers, and guideline/cap issues. Intake remains dry-run only.

- Budget runs now write `exception_lake_mapping_package.json` with dry-run mappings for broken original-budget formulas, missing budget code mappings, unknown budget drivers, guideline/cap issues, human budget changes, and budget actual-cost variance.
- Budget exception candidates now include specific unknown-driver and guideline/cap review labels in addition to the broader budget-unknowns label.
- Template-backed workbook mapping failures can produce dry-run candidates for broken formulas and missing/duplicate/unmapped UTBMS code rows without committing the workbook.
- `budget_actual_comparison_report.json` records phase-level budget-vs-actual posture; normal starter runs keep actuals unavailable and perform no billing connector reads or writes.
- Human budget changes are documented as append-only/superseding records that map to future Lake evidence; intake does not mutate approved budgets or admit records to Lake storage.

## 7. Cross-Repo Promotion Package

Status: implemented for the current synthetic slice.

Prepare candidate contract proposals for Semantic Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime.

- Added `promotion/cross_repo_promotion_package.json` as a machine-readable candidate-only inventory.
- The package covers Semantic Substrate schema/event proposals, Orchestrator workflow/human-pause/evidence-packet interfaces, Exception Lake evidence mappings, Skills Registry specialist metadata, and Legal Knowledge Runtime context-bundle refs.
- Each proposal names candidate artifact refs, proposed contract refs, governance actions, blockers, and `direct_promotion_performed=false`.
- Tests validate target repo coverage, proposal type coverage, local artifact refs, and non-authoritative/no-write flags.

## 8. Provider Adapter Spike

Status: implemented for the current synthetic slice.

Add a structured-model adapter only behind existing gates, with no external writes and deterministic comparison against synthetic gold.

- `--adapter structured-model` remains dry-run only: no provider calls, no network, no external tools, no raw payload externalization, and no real-data approval.
- Structured-model runs now require reviewed synthetic gold through `--fixture-gold`; missing or failing gold fails closed in `model_adapter_report.json`.
- The final adapter report records typed-JSON validation, deterministic baseline projection hash, structured dry-run candidate hash, comparison status, fixture-gold status, prompt hashes, tool denylist, zero-call budget, independent critic requirement, and human gates.
- Deterministic workers remain authoritative until a separate governance decision approves real provider use.

## 9. Rust Readiness

Status: implemented for the current synthetic slice.

Keep Python as reference runtime while adding benchmark thresholds and parity requirements for future Rust hot paths.

- Added `config/rust-ingestion-transition-policy.json` as the local candidate policy for profiling thresholds, benchmark dimensions, hot-path scope, forbidden Rust scope, parity dimensions, and transition gates.
- `ingestion_volume_profile.json` and `rust_ingestion_readiness_report.json` now carry `rust_transition_policy_ref` and load their gates from that manifest.
- Python remains the reference implementation; the policy keeps `rust_replacement_allowed=false`, `no_rust_runtime_added=true`, and `external_writes_performed=false`.
- A future Rust adapter still requires profiling, golden parity, synthetic fixture and holdout parity, schema compatibility, Orchestrator adapter review, and Substrate review for promoted contract changes.

## 10. Carrier Rejection Capture And Learning Loop

Status: capture, reconciliation, dry-run mapping, and human-review packet slices
implemented for the current synthetic candidate; production capture remains future
Orchestrator/Lake work.

Capture 100% of future carrier budget and invoice rejections by deterministic
reconciliation, not by relying on model classification. See
`docs/carrier-rejection-learning-loop-roadmap.md`.

- Treat portal notices, email notices, LEDES/e-billing response files, returned
  workbooks, appeal correspondence, and manual human entries as untrusted source
  channels owned by future Orchestrator connectors.
- Keep a response-state ledger for every submitted budget, invoice, appeal, or
  portal action; missing expected responses and unlinked notices become exceptions.
- Classify rejections into candidate labels for rate reductions, expense
  disallowances, missing preapproval, staffing/leverage issues, narrative defects,
  code-mapping issues, budget-phase variance, portal transport failures, guideline
  drift, appeals, and appeal results.
- Route dry-run candidates to the Exception Lake mapping layer with source refs,
  idempotency keys, parser versions, disputed amounts, and human review state.
- Create a human-owned remediation case for each rejection: classify, link to the
  budget/invoice/projection/guideline version, propose fix or appeal, capture human
  approval, track appeal result, and close with financial outcome.
- Feed reviewed outcomes into candidate learning loops for guideline drift,
  budget drivers, UTBMS/template mappings, narrative rules, preapproval gates, and
  appeal-success patterns without silent profile mutation.
- The local `capture-carrier-rejections` command now reconciles a synthetic
  expected-response ledger against captured portal/email/workbook notices, emits
  remediation cases, collapses duplicate notices by idempotency key, catches
  unlinked notices and missing responses, records appeal results as append-only
  evidence, and writes dry-run Exception Lake candidates.
- The local `review-carrier-rejections` command now turns a reconciliation report
  into a human-review packet with recommended actions, why-notes, red-team checks,
  decision templates, dry-run Lake candidate refs, and no-write/no-submission/no-
  silent-learning boundaries.
