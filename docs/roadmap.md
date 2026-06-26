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
- Observed or human-confirmed `resolution_path` can select the headline scenario;
  otherwise the compatibility surface remains `standard`.
- Synthetic scenario probabilities are carried from the driver policy, and a
  labeled expected total is computed only when probabilities are complete and
  sum to 1.
- `early_resolution`, `standard`, and `through_trial` branch totals are monotonic; hours-only budgets prove monotonicity by hours.
- Scenario branch details render in `legal_budget_review_form.md` and `matter_opening_review_package.md`.

## 3. Stronger Budget Drivers

Status: implemented for the current synthetic slice.

Add severity, venue, liability, coverage, and guideline/cap handling without letting defaults masquerade as observed facts.

- Severity, liability, and venue drivers can apply bounded intensity multipliers from local synthetic policy.
- Cumulative multipliers are capped by policy, with a finite default cap and
  policy-controlled application to expense-bearing lines.
- Count-driver min/likely/max ranges widen hour and expense ranges for
  unknown/profile-default drivers while human-confirmed counts remain tight.
- Coverage posture remains a review boundary and is not blended into defense-fee math.
- Synthetic guideline caps produce `BudgetGuidelineFlag` records and unknown/review text; they do not rewrite rates, hours, or totals.
- `BudgetDriverEffect` records expose driver value, provenance, structured policy ref, applied phases/tasks, and whether a default was used as an observed fact.

## 3A. Carrier Guideline Projection

Status: implemented for the current synthetic slice.

Apply synthetic carrier guideline caps and staffing/leverage role overrides as a separate proposed-vs-compliant projection without mutating the proposed budget.

- `config/synthetic-carrier-guideline.yaml` is a synthetic-only candidate artifact, not a real carrier guideline.
- `CarrierCompliantProjection` is embedded in `legal_budget_proposal.json` and exported as a local candidate schema family.
- Rate caps, expense caps, and task-level staffing role overrides apply only inside the projection view; proposal lines stay unchanged.
- Two synthetic carrier guideline profiles support same-budget counterfactual tests: the proposed budget remains stable while compliant totals, caps, staffing deltas, contingency treatment, and preapproval thresholds differ by carrier.
- Synthetic named-timekeeper rate overrides are available in the rate card and take precedence only when a candidate budget task explicitly names a matching synthetic `timekeeper_id`; default demo budgets remain role-rate based.
- Review surfaces render proposed total, compliant total, deltas, capped lines, staffing-adjusted lines, leverage summary, blended-rate delta, and submission boundaries.
- Synthetic preapproval thresholds emit `carrier_preapproval_report.json`, pending `human_carrier_preapproval` gates, and dry-run `carrier_preapproval_required` candidates without authorizing carrier submission.
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
- `budget_actual_comparison_report.json` records budget-vs-actual posture; normal starter runs keep actuals unavailable and perform no billing connector reads or writes.
- Human budget changes can now be recorded as append-only/superseding candidate evidence with `record-budget-review`; intake does not mutate approved budgets or admit records to Lake storage.

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

Status: capture, reconciliation, dry-run mapping, human-review packet,
learning-candidate report, Orchestrator interface draft, and Exception Lake
admission proposal slices implemented for the current synthetic candidate;
production capture remains future Orchestrator/Lake work.

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
- It also writes `carrier_rejection_decision_ledger_report.json`,
  `carrier_rejection_decision_ledger.jsonl`, and
  `carrier_rejection_decision_ledger_report.md` so rejection states, duplicate
  collapse, pending fix/appeal decisions, appeal results, recovered amounts, and
  write-downs are append-only candidate evidence before Lake admission review.
- The local `review-carrier-rejections` command now turns a reconciliation report
  into a human-review packet with recommended actions, why-notes, red-team checks,
  decision templates, dry-run Lake candidate refs, and no-write/no-submission/no-
  silent-learning boundaries.
- The local `propose-carrier-rejection-learning` command now turns a review packet
  into candidate learning proposals for guideline, budget-driver, template,
  narrative, preapproval, parser, reconciliation, SLA, validation, and
  appeal-outcome loops. Every proposal requires human-reviewed outcome evidence,
  synthetic fixture updates, shadow eval, and owning-repo promotion review before
  it can affect future behavior.
- The local `draft-carrier-rejection-orchestrator-interface` command now emits a
  candidate interface for future Orchestrator-owned connector channels,
  response-state ledger duties, human pauses, appeal-submission gates, and
  guarded Lake handoff. Intake still implements no connector, no external write,
  no route/event assignment, and no Lake admission.
- The local `draft-carrier-rejection-lake-admission` command now emits a
  candidate Exception Lake admission proposal for append-only rejection,
  reconciliation, human review outcome, appeal submission, appeal result,
  financial outcome, and learning-candidate record families. It requires
  idempotency, support hashes, record hashes, Orchestrator evidence packets, and
  supersession corrections while performing no SQLite write or Lake admission.
- The local `audit-carrier-rejection-roadmap` command now emits
  `carrier_rejection_roadmap_audit_report.json` and
  `carrier_rejection_roadmap_audit_report.md`, proving local slices 1-8 have
  candidate proof artifacts while preserving Orchestrator, Exception Lake, and
  Semantic Substrate adoption as external required work.

## 11. Budget Revision And Actuals Lifecycle

Status: implemented for the current synthetic candidate slice; production actuals
and admitted Lake records remain future Orchestrator/Exception Lake work.

Close the loop from proposed budget to human revision to synthetic actual-cost
variance without turning intake into a billing connector, approval system, or
Lake runtime.

- `record-budget-review` writes `budget_review_change_record.json`,
  `budget_revision_history.jsonl`, `budget_revision_report.json`,
  `budget_revision_report.md`, `budget_change_ledger_report.json`,
  `budget_change_ledger.jsonl`, `budget_change_ledger_report.md`, and
  `budget_revision_exception_lake_candidates.jsonl`.
- Human budget changes are append-only candidate evidence. The report calculates
  phase and UTBMS-code deltas while preserving `original_budget_mutated=false`,
  `superseding_budget_written=false`, no submission authorization, no Lake write,
  and no external write.
- The budget change ledger records one row per human change or outcome-only
  decision with reviewer metadata, before/after totals, evidence refs,
  structured refs, and local candidate Lake labels. It remains candidate-only
  and does not admit Lake/SQLite records or authorize learning.
- `compare-budget-actuals` accepts a synthetic actuals source and optional
  `budget_revision_report.json`, then compares actuals against the original
  proposal or the human-revised candidate by phase and UTBMS code.
- The actuals report records comparison budget state, scenario ID, phase/code
  comparisons, variance-driver candidates, learning-disposition candidates, and
  dry-run variance candidates while preserving no billing connector reads/writes.
- `compare-budget-actuals` also writes
  `budget_actual_variance_ledger_report.json`,
  `budget_actual_variance_ledger.jsonl`, and
  `budget_actual_variance_ledger_report.md` so every phase/code comparison row,
  missing-actuals row, zero-budget/positive-actual row, and human-revised
  comparison context is append-only candidate evidence before Lake admission.
- When an actual resolution scenario is supplied, the comparison surface is
  filtered to that scenario before phase/code variance is calculated.
- The zero-budget/positive-actual case is classified as over-threshold rather
  than hidden by a missing percent denominator.
- Learning remains candidate-only: variance and human-revision evidence can feed
  future reviewed budget-driver, template-mapping, and validation-rule loops, but
  no profile, template, budget, or carrier guideline is silently mutated.

## 11A. Budget Event Lake Review Bundle

Status: implemented for the current synthetic candidate slice; Exception Lake
admission, SQLite persistence, record hashes, and canonical event classes remain
future owner work.

Bridge the budget-event ledgers into one hashed, run-specific owner-review
package without letting intake become the Lake runtime.

- `build-budget-event-lake-bundle` consumes optional
  `budget_change_ledger_report.json`,
  `budget_actual_variance_ledger_report.json`, and
  `carrier_rejection_decision_ledger_report.json` inputs.
- It infers each paired JSONL ledger when not supplied explicitly.
- It writes `budget_event_lake_admission_bundle_report.json` and
  `budget_event_lake_admission_bundle.md`.
- The bundle hashes every ledger artifact, checks report-vs-JSONL row counts,
  verifies event ID sets, requires consistent budget proposal and preflight
  packet IDs, and maps events to candidate record families for Exception Lake
  owner review.
- Missing artifacts, mismatched budget/preflight IDs, JSONL/report drift,
  duplicate artifact refs, missing candidate record families, or any prohibited
  Lake/SQLite/billing/submission/mutation/silent-learning flag block the bundle.
- Passing status is only `ready_for_exception_lake_review`; it does not admit
  records, create record hashes, write SQLite, write sibling repos, promote event
  classes, submit appeals or budgets, read billing, write billing, or apply
  learning.

## 11B. Budget Lifecycle Audit

Status: implemented for the current synthetic candidate slice; production
capture, real actuals, appeal submission, and Lake admission remain future owner
work.

Give reviewers one deterministic view of the whole budget lifecycle before any
Exception Lake or learning handoff is trusted.

- `audit-budget-lifecycle` consumes `budget_change_ledger_report.json`,
  `budget_actual_variance_ledger_report.json`,
  `carrier_rejection_decision_ledger_report.json`, and
  `budget_event_lake_admission_bundle_report.json`.
- It writes `budget_lifecycle_audit_report.json` and
  `budget_lifecycle_audit_report.md`.
- It checks that the budget-change, actual-variance, carrier-rejection, and
  Lake-bundle streams refer to the same budget proposal and preflight packet.
- It summarizes original budget, human revision delta, human-revised candidate
  budget, actual budget/actual/variance totals, carrier disputed amount,
  recovered amount, write-down amount, pending human decisions, proposed next
  actions, candidate record families, and local event labels.
- Missing artifacts, inconsistent IDs, empty lifecycle streams, failed Lake
  bundles, missing lifecycle record-family coverage, or prohibited
  Lake/SQLite/billing/submission/mutation/silent-learning flags block the audit.
- Pending human decisions are preserved as review content, not treated as an
  intake authority to fix, appeal, submit, or learn.
- Passing status is only `ready_for_budget_lifecycle_review`; it does not admit
  records, submit appeals or budgets, write billing, write SQLite, write sibling
  repos, mutate profiles/templates/budgets/guidelines, or apply learning.

## 11C. PR Review Checklist

Status: implemented for the current synthetic candidate slice; the actual PR
state change remains a human GitHub action.

Turn the final readiness audit into an explicit human-review checklist with
recommendations, why-notes, red-team objections, blocking readiness items,
validation commands, and required human decisions before a draft PR is moved
forward.

- `build-pr-review-checklist` consumes
  `intake_vertical_readiness_audit_report.json`.
- It writes `pr_review_checklist.json` and `pr_review_checklist.md`.
- Ready status is only `ready_for_human_pr_review`; it is not production
  readiness and does not override required owner adoption in Semantic Substrate,
  Orchestrator, or Exception Lake.
- A blocked readiness audit produces a blocking checklist item and keeps the
  recommendation at `keep_draft_until_human_review_complete`.
- The checklist records `pr_marked_ready=false`,
  `github_write_performed=false`, `promotion_authorized=false`,
  `proposed_changes_applied=false`, `no_lake_admission_performed=true`,
  `no_sibling_repo_writes=true`, `no_canonical_mutation=true`,
  `lake_write_performed=false`, `sqlite_write_performed=false`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.

## 11C. Cross-Repo Owner Adoption Packets

Status: implemented for the current synthetic candidate slice; actual owner repo
issues, PRs, canon promotion, runtime adoption, and Lake admission remain future
owner work.

Turn the static cross-repo promotion package plus live PR readiness evidence into
owner-specific packets that are easier to hand to Semantic Substrate,
Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime.

- `build-cross-repo-owner-adoption` consumes
  `promotion/cross_repo_promotion_package.json`,
  `intake_vertical_readiness_audit_report.json`, and
  `pr_review_checklist.json`.
- It writes `cross_repo_owner_adoption_report.json`,
  `cross_repo_owner_adoption_report.md`,
  `cross_repo_owner_adoption_packets.jsonl`, and per-owner JSON/Markdown packets
  under `owner_adoption_packets/`.
- Each owner packet includes candidate proposal summaries, proposed contract
  refs, required owner actions, acceptance checks, red-team notes, and required
  next gates.
- A blocked readiness audit or blocked PR checklist keeps all owner packets at
  `blocked_by_pr_readiness`.
- The packets record `github_issue_created=false`,
  `github_pr_created=false`, `github_write_performed=false`,
  `sibling_repo_write_performed=false`, `promotion_authorized=false`,
  `lake_write_performed=false`, `sqlite_write_performed=false`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.

## 11D. Cross-Repo Owner Issue Drafts

Status: implemented for the current synthetic candidate slice; actual issue
creation, owner triage, implementation PRs, and sibling-repo writes remain
manual owner work.

Turn owner-adoption packets into ready-to-review issue text for the five owning
repos without creating issues or writing to GitHub.

- `build-cross-repo-owner-issue-drafts` consumes
  `cross_repo_owner_adoption_report.json`.
- It writes `cross_repo_owner_issue_draft_report.json`,
  `cross_repo_owner_issue_draft_report.md`,
  `cross_repo_owner_issue_drafts.jsonl`, and per-owner Markdown/JSON drafts
  under `owner_issue_drafts/`.
- Each issue draft includes a suggested title, labels, source evidence refs,
  candidate proposal summaries, required owner actions, acceptance checks,
  red-team notes, required next gates, and explicit no-write boundaries.
- Blocked owner-adoption packets produce blocked issue drafts.
- The report records `manual_creation_required=true`,
  `github_issue_created=false`, `github_pr_created=false`,
  `github_write_performed=false`, `sibling_repo_write_performed=false`,
  `promotion_authorized=false`, `lake_write_performed=false`,
  `sqlite_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

## 11E. Intake Local Closeout Audit

Status: implemented for the current synthetic candidate slice; PR state changes,
owner issue creation, owner implementation, canonical promotion, runtime
adoption, and Lake admission remain manual external work.

Aggregate the final readiness audit, PR checklist, owner-adoption packets, and
owner issue drafts into one local closeout report.

- `audit-intake-local-closeout` consumes
  `intake_vertical_readiness_audit_report.json`, `pr_review_checklist.json`,
  `cross_repo_owner_adoption_report.json`, and
  `cross_repo_owner_issue_draft_report.json`.
- It writes `intake_local_closeout_report.json` and
  `intake_local_closeout_report.md`.
- Passing status is
  `intake_local_closeout_ready_manual_actions_required`, which means
  intake-local candidate evidence is ready but human PR decision, manual owner
  issue creation, owner triage, owner implementation PRs if accepted, and
  cross-repo validation still remain.
- Blocked readiness, PR checklist, owner adoption, or owner issue-draft evidence
  blocks closeout.
- The report records `manual_pr_state_change_required=true`,
  `manual_owner_issue_creation_required=true`,
  `pr_state_change_performed=false`, `github_issue_created=false`,
  `github_pr_created=false`, `github_write_performed=false`,
  `sibling_repo_write_performed=false`, `promotion_authorized=false`,
  `proposed_changes_applied=false`, `lake_write_performed=false`,
  `sqlite_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

## 12. Reviewed Learning Gate

Status: implemented for the current synthetic candidate slice; owning-repo
promotion, admitted Lake records, and production learning remain future work.

Aggregate the learning pressure created by carrier rejections, human budget
revisions, appeal outcomes, and actual-cost variance without letting any source
silently mutate profiles, templates, budgets, carrier guidelines, connectors, or
canon.

- `review-learning-gate` accepts optional `carrier_rejection_learning_report.json`,
  `budget_revision_report.json`, and `budget_actual_comparison_report.json`
  inputs.
- It writes `reviewed_learning_gate_report.json`,
  `reviewed_learning_gate_report.md`, and
  `reviewed_learning_gate_candidates.jsonl`.
- Candidate sources include carrier rejection learning proposals, budget revision
  deltas, and budget actual variance-driver candidates.
- Every candidate is blocked until human-reviewed outcome evidence,
  append-only evidence recording, synthetic fixture updates, shadow evals, and
  owning-repo review are complete.
- The gate records `profile_mutation_performed=false`,
  `template_mutation_performed=false`, `connector_mutation_performed=false`,
  `budget_mutation_performed=false`,
  `carrier_guideline_mutation_performed=false`,
  `lake_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

## 13. Shadow Eval And Promotion Readiness

Status: implemented for the current synthetic candidate slice; actual proposed
changes, passing shadow eval results, and owning-repo promotion remain future
work.

Prepare every reviewed-learning candidate for a governed shadow eval and prove
that promotion is still blocked until evidence exists.

- `audit-learning-promotion-readiness` consumes
  `reviewed_learning_gate_report.json`.
- It writes `learning_shadow_eval_plan.json`, `learning_shadow_eval_plan.md`,
  `learning_promotion_readiness_report.json`, and
  `learning_promotion_readiness_report.md`.
- The shadow-eval plan creates one case per candidate with required fixture
  updates, eval suites, and regression guardrails for no conflict conclusion, no
  budget submission, no matter opening, no external writes, no silent learning,
  and stable source evidence.
- The promotion-readiness report records
  `promotion_authorized=false`, `proposed_changes_applied=false`,
  `profile_mutation_performed=false`, `template_mutation_performed=false`,
  `connector_mutation_performed=false`, `budget_mutation_performed=false`,
  `carrier_guideline_mutation_performed=false`, `lake_write_performed=false`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.
- Promotion remains blocked until proposed change artifacts, synthetic fixture
  updates, shadow eval results, regression checks, and owning-repo review exist.

## 14. Learning Proposed-Change Artifacts

Status: implemented for the current synthetic candidate slice; applying
proposed changes, passing shadow evals, and owning-repo promotion remain future
work.

Turn blocked shadow-eval cases into human-review draft change artifacts with
recommendations, why-notes, and red-team objections before any eval or promotion
path can claim a learning change is ready.

- `draft-learning-proposed-changes` consumes `learning_shadow_eval_plan.json`
  and optionally `learning_promotion_readiness_report.json`.
- It writes `learning_proposed_change_set.json`,
  `learning_proposed_change_set.md`, and `learning_proposed_changes.jsonl`.
- Each proposed change records the target learning loop, owning repo, change
  type, source artifact, support refs, recommendation, recommendation rationale,
  red-team notes, required fixture updates, eval suites, regression guardrails,
  and required next gates.
- Cross-repo owner routing is explicit: intake-owned budget candidates may be
  drafted for human review, while Orchestrator/Lake/Substrate-owned candidates
  are held for owning-repo review before implementation.
- The command records `promotion_authorized=false`,
  `proposed_change_applied=false`, `baseline_mutated=false`,
  `profile_mutation_performed=false`, `template_mutation_performed=false`,
  `connector_mutation_performed=false`, `budget_mutation_performed=false`,
  `carrier_guideline_mutation_performed=false`, `lake_write_performed=false`,
  `sqlite_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

## 15. Learning Shadow-Eval Results

Status: implemented for the current synthetic candidate slice; owning-repo
promotion decisions, runtime adoption, and real-data calibration remain future
work.

Evaluate draft proposed changes against synthetic fixture result evidence before
any candidate can leave the intake-local eval surface.

- `run-learning-shadow-eval` consumes `learning_proposed_change_set.json` and
  zero or more synthetic `LearningShadowEvalFixtureResult` files.
- It writes `learning_shadow_eval_result_report.json`,
  `learning_shadow_eval_result_report.md`, and
  `learning_shadow_eval_results.jsonl`.
- Missing fixture evidence produces `shadow_eval_blocked`; failed eval suites or
  failed regression guardrails produce `shadow_eval_failed`.
- Fully passing candidates are only `passed_for_owning_repo_review`; they are
  not promoted or applied.
- The harness checks required eval suites, regression guardrails, red-team
  notes, fixture/change ID binding, synthetic-only scope, and no-mutation
  boundaries.
- The command records `promotion_authorized=false`,
  `proposed_changes_applied=false`, `baseline_mutated=false`,
  `profile_mutation_performed=false`, `template_mutation_performed=false`,
  `connector_mutation_performed=false`, `budget_mutation_performed=false`,
  `carrier_guideline_mutation_performed=false`, `lake_write_performed=false`,
  `sqlite_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

## 16. Learning Owner Handoff Packages

Status: implemented for the current synthetic candidate slice; actual promotion
decisions, sibling-repo changes, runtime adoption, and real-data pilots remain
future work.

Package shadow-eval results by owning repo so review work can move to the right
authority plane without intake promoting or applying the change.

- `build-learning-owner-handoffs` consumes
  `learning_shadow_eval_result_report.json`.
- It writes `learning_owner_handoff_report.json`,
  `learning_owner_handoff_report.md`, `learning_owner_handoff_packages.jsonl`,
  and one JSON/Markdown package per target owner under `owner_handoffs/`.
- Each owner package separates ready, failed, and blocked items.
- Ready items mean only `ready_for_owner_review`; they are not approved,
  promoted, implemented, or adopted.
- Failed items require decline or repair; blocked items require missing fixture,
  eval, guardrail, or matching evidence before owner review.
- The command records `promotion_authorized=false`,
  `proposed_changes_applied=false`, `baseline_mutated=false`,
  `lake_write_performed=false`, `sqlite_write_performed=false`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.

## 17. Intake Vertical Readiness Audit

Status: implemented for local candidate proof; human PR review and all external
adoption decisions remain future work.

Close the build-out with a deterministic audit that separates the easy local
proof work from the higher-risk owner-adoption work.

- `audit-intake-vertical-readiness` consumes
  `learning_owner_handoff_report.json` and
  `budget_event_lake_admission_bundle_report.json`, plus
  `budget_calibration_readiness_report.json` and
  `budget_fixture_update_review_report.json` and
  `budget_fixture_update_pr_package_report.json`.
- It writes `intake_vertical_readiness_audit_report.json` and
  `intake_vertical_readiness_audit_report.md`.
- It checks that the intake-to-budget, budget revision, actual-cost comparison,
  carrier rejection, reviewed learning, proposed-change, shadow-eval,
  owner-handoff, budget-event Lake bundle, and cross-repo promotion surfaces
  have local candidate proof.
- It validates the generated learning artifact chain from owner handoff back to
  shadow eval, proposed changes, promotion readiness, shadow plan, and reviewed
  learning gate.
- It validates the generated budget-event Lake bundle for ready-for-owner-review
  status, existing artifact refs, candidate record-family coverage, and no
  Lake/SQLite/billing/submission/mutation/silent-learning side effects.
- It validates the generated calibration-readiness chain for manual
  fixture-update review status, source refs, approved replay-output refs, target
  fixture refs, and no fixture/calibration/Lake/SQLite/silent-learning side
  effects.
- It validates the generated fixture-update review record for append-only local
  history, accepted/rejected decision posture, source calibration-readiness
  binding, and no fixture/calibration/Lake/SQLite/silent-learning side effects.
- It validates the generated fixture-update PR package for manual PR package
  posture, source review binding, item JSONL refs, and no GitHub PR,
  fixture/calibration/Lake/SQLite/silent-learning side effects.
- Passing status is `ready_for_pr_review_external_adoption_required`, which
  means ready for human PR review only.
- The report records `pr_marked_ready=false`, `promotion_authorized=false`,
  `proposed_changes_applied=false`, `no_connector_implemented=true`,
  `no_lake_admission_performed=true`, `no_sibling_repo_writes=true`,
  `no_canonical_mutation=true`, `sqlite_write_performed=false`,
  `lake_write_performed=false`, `external_writes_performed=false`, and
  `silent_learning_performed=false`.

From here, the easy next work is mostly review packaging, fixture expansion,
and docs cleanup. The critical higher-risk work is owner adoption in Semantic
Substrate, Orchestrator, and Exception Lake, then governed real-data pilots only
after those owners promote the necessary contracts and runtime gates.

## 18. Budget Calibration Corpus

Status: implemented for the current synthetic candidate slice through corpus
audit, replay planning, selected replay execution audit, human replay review
packet/outcome recording, fixture-binding candidates, and fixture-update
handoff packaging, calibration-chain readiness audit, and manual fixture-update
review record plus manual fixture-update PR package; broader replay execution,
reviewed fixture edit PRs, real-data pilots, and owner adoption remain future
work.

Separate "we have synthetic evidence artifacts" from "we are allowed to learn
from them."

- `audit-budget-calibration-corpus` scans a synthetic fixture corpus and writes
  `budget_calibration_corpus_report.json` plus Markdown notes.
- The report classifies intake sources, confirmations, reviewed gold, human
  budget review changes, synthetic actuals, carrier rejection bundles,
  learning-gate fixtures, and shadow-eval fixture results by calibration role.
- Real/production/privileged flags, mutation flags, Lake/SQLite writes, external
  writes, and silent-learning flags block the corpus.
- Eligible artifacts are only `eligible_for_synthetic_calibration_review`; no
  calibration, profile mutation, template mutation, carrier-guideline mutation,
  or learning is applied.
- Required next gates are human corpus review, fixture-result binding, shadow
  eval before learning, owning-repo review, and no silent profile/template
  mutation.
- `plan-budget-corpus-replay` consumes the corpus audit and writes
  `budget_corpus_replay_plan.json` plus Markdown notes.
- The replay plan maps eligible artifacts to deterministic local command chains
  for baseline demo regeneration, human budget reviews, actual-cost comparison,
  carrier rejection capture/review/learning-gate routing, reviewed gold replay,
  learning-gate promotion readiness, proposed-change drafting, and shadow-eval
  fixture replay.
- Supporting intake/confirmation fixtures remain context-only and do not receive
  replay commands.
- If the source corpus report is blocked by real/production/privileged data or
  mutation flags, the replay plan is `blocked_by_corpus_report` and emits no
  command chains.
- The replay plan is still a plan, not a runner: it does not execute commands,
  calibrate, mutate budgets/profiles/templates/guidelines, write Lake or SQLite
  records, or authorize learning.
- `replay-budget-corpus` consumes the replay plan and writes
  `budget_corpus_replay_execution_report.json` plus Markdown notes.
- Dry-run mode is the default and records which command chains are ready,
  skipped as support context, blocked by the source plan, or missing required
  placeholders.
- `--execute --case-id <id>` can execute selected local synthetic command chains
  and verify expected output files before human corpus replay review.
- Execution uses argv lists against existing local CLI commands, not shell
  strings, and remains bounded to local synthetic artifacts under the replay run
  directory.
- Learning-support artifacts such as proposed-change readiness reports and
  shadow-eval plans are classified as `learning_support_fixture` and stay
  supporting context unless a reviewed upstream chain produces the required
  input.
- Replay execution audit still does not calibrate, mutate
  budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
  budgets, open matters, or authorize learning.
- `review-budget-corpus-replay` consumes the replay execution report and writes
  `budget_corpus_replay_review_packet.json`,
  `budget_corpus_replay_review_packet.md`, and
  `budget_corpus_replay_review_decision_template.json`.
- The review packet translates replay results into human-facing
  recommendations, red-team notes, and append-only decision templates.
- Executed-passed cases are eligible only for human fixture-binding review; dry
  runs remain blocked pending execution; failed or blocked cases require repair
  or exclusion; support-only cases remain non-executable context.
- Human review outcomes are append-only artifacts recorded by
  `record-budget-corpus-replay-review-outcome`. The packet itself does not
  approve fixture binding, apply learning, mutate
  budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
  budgets, open matters, or authorize external actions.
- `record-budget-corpus-replay-review-outcome` consumes a replay review packet
  and reviewer-supplied outcome JSON, then writes
  `budget_corpus_replay_review_outcome_record.json`,
  `budget_corpus_replay_review_outcome_history.jsonl`,
  `budget_corpus_replay_review_outcome_report.json`, and Markdown notes.
- Outcomes are validated against the decision template. Unknown cases,
  disallowed outcomes, mismatched packet IDs, and unbound approved output refs
  fail closed.
- Outcome records are append-only and may supersede earlier outcome IDs, but they
  do not mutate the packet, replay report, source fixtures, budget profiles,
  templates, carrier guidelines, Lake records, SQLite records, or learning
  state.
- `propose-budget-fixture-bindings` consumes the replay review packet and
  outcome report, then writes `budget_fixture_binding_candidate_report.json`,
  `budget_fixture_binding_candidates.jsonl`, and Markdown notes.
- Ready fixture-binding candidates require an append-only
  `approve_fixture_binding` outcome plus approved output refs. Rejected,
  repair, hold, or missing-output states generate blocked reports instead of
  guessing.
- The fixture-binding report still does not update fixture files, apply
  learning, mutate budgets/profiles/templates/guidelines, write Lake or SQLite
  records, submit budgets, open matters, or authorize external actions.
- `build-budget-fixture-binding-handoff` consumes the fixture-binding candidate
  report and writes `budget_fixture_binding_handoff_report.json`,
  `budget_fixture_binding_handoff_report.md`, and
  `budget_fixture_binding_handoff_items.jsonl`.
- The handoff preserves ready-vs-blocked state, explains why a candidate is or
  is not ready for human fixture-update review, adds recommended owner actions
  and red-team objections, and still does not update fixtures, create a PR,
  apply learning, mutate budgets/profiles/templates/guidelines, write Lake or
  SQLite records, submit budgets, open matters, or authorize external actions.
- `audit-budget-calibration-readiness` consumes the corpus report, replay plan,
  replay execution report, replay review packet, review outcome report,
  fixture-binding candidate report, and fixture-binding handoff report, then
  writes `budget_calibration_readiness_report.json` and Markdown notes.
- A passing readiness audit means the synthetic calibration chain is ready for
  manual fixture-update review only. It checks ID continuity, approved output
  refs, target fixture refs, required gates, and no side effects. It still does
  not update fixtures, create a PR, apply learning, mutate
  budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
  budgets, open matters, or authorize external actions.
- `record-budget-fixture-update-review` consumes the readiness report plus an
  explicit human fixture-update review decision JSON, then writes
  `budget_fixture_update_review_record.json`,
  `budget_fixture_update_review_history.jsonl`,
  `budget_fixture_update_review_report.json`, and Markdown notes.
- Accepted decisions require a separate human-reviewed fixture-update PR if
  humans choose to update fixtures. Rejected or needs-more-information decisions
  remain recorded evidence and do not open a PR. The recorder still does not
  update fixtures, create a PR, apply learning, mutate
  budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
  budgets, open matters, or authorize external actions.
- `build-budget-fixture-update-pr-package` consumes the fixture-update review
  report and writes `budget_fixture_update_pr_package_report.json`, Markdown
  notes, and package-item JSONL when accepted decisions require manual package
  items.
- The PR package is a reviewer-ready instruction set only. It does not edit
  fixtures, create a GitHub PR, apply learning, mutate
  budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
  budgets, open matters, or authorize external actions.
