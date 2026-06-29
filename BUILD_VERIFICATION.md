# Build Verification

Verified in the local build environment on 2026-06-29:

```text
python scripts/export_schemas.py
# exported 228 schemas

python scripts/validate_repo.py
# repository validation passed

python scripts/run_full_pytest.py
# 373 passed in 294.99s

python -m ruff check --no-cache src tests scripts
# All checks passed

python -m ruff format --check --no-cache src tests scripts
# 193 files already formatted

bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; bash scripts/smoke_demo.sh'
# completed without error and wrote starter, blocked-budget, and context-counterfactual audit reports
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.

Validation runtime ceilings are candidate-governed in
`config/validation-runtime-policy.yaml`. The full pytest path is intentionally
run through `scripts/run_full_pytest.py` so local validation does not inherit a
300 second ceiling as the suite grows. Direct pytest invocation is blocked by
the test harness; use the wrapper for full and focused test runs.

Repository validation now checks the AI/front-door orientation files for broken local file references and verifies that the public-data catalog remains planning-only metadata with no direct runtime ingestion. The builder reading order in `README.md`, `AI_WORK_START_HERE.md`, `AI_TABLE_OF_CONTENTS.md`, and `CLAUDE.md` must point only to existing local files or directories.

The smoke demo now also writes `starter_release_audit_report.json` after the north-star demo finishes. That report is a local, non-authoritative starter release audit over generated artifacts; it fails if required outputs, synthetic-only scope, public-data catalog metadata-only posture, source coverage states, candidate surface completeness, source-bound evidence refs, evidence-graph deliverable coverage, human-review package story coverage, human gates, carrier/client separation, conflict/budget boundaries, dry-run Exception Lake posture, safety boundary, fixture-gold gates, run ledgers, candidate-registry noncanonical status, or Rust-readiness posture drift.

The smoke demo also writes `blocked_budget_attempt_audit_report.json` from a synthetic `needs_more_information` confirmation. That report proves the budget path blocks before conflict seed, budget proposal, readiness packet, safety gate, or final package output while preserving the blocked precondition report, review outcome/history, dry-run exception candidate, readiness report, handoff manifest, and run ledger.

The smoke demo also writes `context_counterfactual_audit_report.json` from the same synthetic source under defense and plaintiff profiles. That report proves source inventory, segment signatures, and observed evidence refs stay stable while practice context may change rankings, and that context-only matter candidates remain graph anchors rather than observed facts.

The current demo also emits local `exception_lake_candidates.jsonl` files in preflight and budget outputs. These are dry-run candidates only; they are not canonical Exception Lake admissions and include no raw legal payload.

The preflight output now includes `contract_state_report.json`, which verifies the reviewed local sibling-repo lock state before source processing. The report is carried forward into the final review manifest and safety gate.

The preflight output now includes a finalized `model_adapter_report.json` for the selected adapter. The `structured-model` dry-run path requires reviewed synthetic gold, validates typed JSON, records deterministic baseline and structured dry-run candidate hashes, compares against the passing gold gate, and still performs no provider call, network access, external write, raw payload externalization, or real-data approval.

The preflight output now also includes `data_scope_gate_report.json`, which proves synthetic-only data scope before `raw_input.json` is written. Blocked non-synthetic runs write the gate report and ledger event, then stop before raw payload storage, packet generation, source inventory, ingestion, or review artifacts. The passing report is carried into the final review package, manifest, safety gate, completeness report, starter audit, schema export, and smoke checks.

The preflight output now also includes `evidence_completeness_report.json`, proving candidate evidence refs match the packet segment table for party, role, inbound-event, matter-family, posture, deadline, missing-information, and critic outputs. The final package renders the proof, and package completeness plus starter audit fail closed if it is missing or drifts.

The repo now includes `config/rust-ingestion-transition-policy.json`, a local candidate policy manifest for Rust profiling thresholds, benchmark dimensions, allowed hot-path scope, forbidden scope, parity dimensions, and transition gates. `ingestion_volume_profile.json` and `rust_ingestion_readiness_report.json` carry `rust_transition_policy_ref` and keep `rust_replacement_allowed=false`.

Source-bound evidence references now include segment offsets as well as source ID, segment ID, and hash. Strict evidence validation fails if a ref drifts from the cited segment.

Correspondence dumps with repeated `From:` boundaries now segment into message-indexed headers, body paragraphs, quoted history, signatures, attachment refs, offsets, and hashes. A synthetic holdout proves prohibited quoted instructions in a dump become dry-run exception candidates instead of actions.

Party-role alternatives now carry their own source-bound evidence refs, render in the intake review form, and appear as supported candidate nodes in the evidence graph.

ADR-004 records the Rust-ready ingestion boundary for future high-volume or constrained-compute document processing. Python remains the reference implementation until any Rust adapter proves golden parity.

Preflight runs now emit `ingestion_result.json` as the Python reference parity oracle for source inventory, coverage summary, segments, and segment-level evidence refs.

Preflight runs now emit `ingestion_volume_profile.json`, a deterministic source/segment scale report that can require profiling before any future Rust adapter proposal while keeping `rust_replacement_allowed=false`.

The ingestion volume profile now also records compute pressure signals, required performance profile dimensions, and the candidate Rust hot-path scope so constrained-compute pressure can be reviewed before any Rust adapter proposal.

Preflight runs now also emit `rust_ingestion_readiness_report.json`, proving the Python ingestion artifact is a valid future Rust parity target while keeping `rust_replacement_allowed=false`.

Preflight runs now also emit `deadline_docketing_guard_report.json`, proving deadline candidates are source-bound, review-only, proposed only for `human_deadline_review`, and not docketed. The final review package renders the guard, and package completeness fails if the guard is missing, evidence-free, or claims docketing occurred.

The preflight intake review form now renders detailed source inventory fields and explicit review outcome handling, including the fact that only confirmed outcomes can advance toward the budget precondition gate and that corrections append or supersede rather than silently mutating history.

The budget stage now emits `budget_precondition_report.json`; failed confirmation attempts write this report, a blocked ledger event, and a dry-run Exception Lake candidate before any proposal output is created. The gate requires the human confirmation to be matching, confirmed, and evidence-bound.

The budget output now includes `matter_opening_review_package.md` and `review_package_manifest.json` as the consolidated review surface for the north-star demo.

Budget runs now also emit `review_package_completeness_report.json`, proving the final review package has required artifacts, review sections, human gates, blockers, safety proof, dry-run Exception Lake readiness, run ledgers, run-ledger integrity reports, and non-authorization boundary flags before the package is accepted.

Preflight, confirmed budget, and blocked-budget attempts now emit `run_ledger_integrity_report.json`, proving required gate order, expected terminal state, local refs, existing outputs, and no external writes. Superseding corrected budget attempts preserve prior blocked history while validating the latest budget attempt segment.

The completeness report now also verifies that linked intake and budget review forms preserve their required human-review sections, evidence-hash visibility where source-bound evidence exists, and non-authorization boundary text, including source coverage, outcome handling, budget lines, support items, and submission boundary.

Matter-opening readiness now exports a candidate schema and carries structured blocker details plus prohibited-action guardrails. The safety gate and completeness report fail closed if conflicts, engagement, matter-opening, workspace, or budget-submission blockers lose workflow-policy or prohibited-transition support refs.

Budget runs now emit `human_gate_status_report.json`, proving intake confirmation is complete while conflicts clearance, engagement authorization, budget review, and matter-opening authorization remain pending human gates. The review package renders those gate states, and package completeness fails if a pending gate is omitted or incorrectly marked complete.

Budget runs now also emit `budget_submission_guard_report.json`, proving the budget remains proposed for human review, is not authorized for client or carrier submission, has no client submission, no carrier submission, no billing handoff, no external writes, and remains blocked by `human_budget_review`.

Budget proposals now embed `BudgetScenarioSet` with `early_resolution`, `standard`, and `through_trial` branches. The compatibility proposal fields map to `standard`, while the review forms render the branch comparison, ranges, included phases, included UTBMS code candidates, monotonic ordering, and non-submission boundary.

Budget proposals now also embed `BudgetDriverEffect` and `BudgetGuidelineFlag` records. Severity, liability, and venue can apply bounded synthetic intensity multipliers, coverage posture remains a review boundary, and synthetic guideline caps produce human-review flags without rewriting rates, hours, expenses, or totals. Profile defaults are labeled as defaults rather than observed facts.

Budget proposals now also embed `CarrierCompliantProjection` when the synthetic
profile names a carrier guideline artifact. The projection applies synthetic rate
and expense caps in a separate proposed-vs-compliant view, reports deltas, keeps
proposal lines unchanged, and carries `rewrites_budget=false`, no external writes,
and no client/carrier submission authority.

Budget runs now also write `case_driver_profile.json` and embed `BudgetDriverProfileSummary` in `legal_budget_proposal.json`. The review package and standalone budget form render driver profile summary, scenario comparison, workbook mapping status, and unresolved budget assumptions, and package completeness fails closed if those surfaces or non-observed-fact boundaries drift.

Budget runs now also write `exception_lake_mapping_package.json` and `budget_actual_comparison_report.json`. The mapping package covers broken workbook formulas, missing budget code mappings, unknown budget drivers, guideline/cap issues, human budget changes, and actual-cost variance as dry-run Lake evidence families. The actual comparison report is phase-level and records no billing connector read or write in the starter.

The repo now includes `promotion/cross_repo_promotion_package.json`, a candidate-only sibling review inventory for Semantic Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime. Tests validate required target repo coverage, proposal type coverage, local artifact refs, and no direct promotion or external writes.

The insurance-defense profile now includes a second synthetic matter family, `auto_liability_defense`, with its own UTBMS-coded template and driver defaults. The auto/BI fixture exercises preflight ranking, human confirmation binding, driver resolution, budget generation, scenario set, review package creation, and the same non-submission boundary as the med-mal fixture.

Human-facing review Markdown now renders evidence refs inline for confirmation evidence, confirmed parties, deadlines, missing-information candidates, critic findings, conflict-search terms, and budget supports.

Those reviewer-facing evidence refs now include source IDs, segment IDs, offsets, and hashes, so the final package exposes the full source-bound pointer without requiring JSON inspection first.

The final matter-opening review package now includes a candidate-alternatives section for inbound-event, matter-family, representation-posture, and party-role candidates, and package completeness requires that section.

The final matter-opening review package now includes a required-human-gates section for conflicts clearance, engagement authorization, budget review, and matter-opening authorization, and package completeness requires that section.

The final matter-opening review package now includes calculation summary, budget line, and budget support subsections, and package completeness requires those budget detail sections.

The standalone legal budget review form now includes itemized budget lines and a submission-boundary section so budget reviewers can inspect hours, rates, synthetic-rate labels, fees, expenses, assumptions, evidence refs, and non-authorization state without opening JSON first.

The final matter-opening review package now includes source-inventory detail and a run-ledger summary, and package completeness requires those auditability sections.

The final matter-opening review package now includes an evidence-graph summary with node/edge counts, node-type counts, relationship counts, and key provenance edge examples; package completeness requires that section.

Preflight runs now emit `context_boundary_report.json`, proving observed source evidence stays ahead of practice-context priors, context is not observed evidence, context refs remain structured, unknown options remain available, human confirmation remains required, and no external write or authoritative promotion occurred.

Template-backed budget form rendering now emits `budget_form_mapping_report.json` when requested and blocks before workbook creation if the carrier-style template loses required headers, UTBMS mappings, original-budget total formulas, phase subtotal formulas, or task remaining formulas.

The standalone `budget-form-audit` command now emits `budget_form_template_audit_report.json` before any matter-specific budget exists, using the same header, UTBMS code, and original-budget formula checks without mutating the workbook.

The final matter-opening review package now includes authority and precondition subsections for contract-state status, human-review outcome, and budget precondition checks; package completeness requires those sections.

The final matter-opening review package now includes Exception Lake readiness, handoff, and exception candidate detail subsections showing dry-run posture, raw-payload exclusion, promotion requirement, target runtime repo, no SQLite write, and support refs; package completeness requires those sections.

Exception candidate detail evidence refs now render source IDs, segment IDs, offsets, and hashes inline, matching the rest of the reviewer-facing evidence surface.

Budget runs now write `human_review_outcome.<confirmation_id>.json` and append it to `human_confirmation_history.jsonl` before budget preconditions run. Non-confirmed review outcomes remain blocked, and superseding corrections append new history rows instead of mutating prior outcomes.

Budget assumptions, exclusions, and unknowns now emit `budget_support_items` with evidence refs or structured refs for human review.

The budget-stage evidence graph now includes human review outcome, conflict seed packet, conflict-search term, budget line, budget support item, and structured-ref nodes with source-backed or structured-ref support edges.

Budget uncertainty now emits dry-run Exception Lake candidates for proposal unknowns, missing approved synthetic budget templates, and hours-only missing-rate states. These candidates may carry structured refs and still include no raw payload.

Unread sources now count as explicit source coverage gaps, render in review summaries, and emit `source_unread` dry-run `retrieval_miss` candidates.

Exception Lake candidate files now emit `exception_lake_readiness_report.json`, proving dry-run posture, raw-payload exclusion, promotion-required status, target runtime repo, and source/evidence ref integrity before future Lake handoff.

Exception Lake candidate files now also emit `exception_lake_handoff_manifest.json`, summarizing actual local labels, broad Lake classes, support modes, candidate file refs, paired readiness report, target runtime owner, `mapping_review_required=true`, `canonical_promotion_required=true`, `sqlite_write_performed=false`, and `external_writes_performed=false`.

The budget output also includes `safety_gate_report.json`; a failed safety check raises before the final review package is accepted.

The smoke demo runs the messy north-star synthetic fixture, not the clean carrier-only fixture.

Conflict-search seed packets now require every normalized search term to carry source-bound evidence refs from the human confirmation. The packet remains a search seed only and preserves `no_conflict_conclusion`.

The safety gate now independently verifies evidence completeness for conflict-search terms, budget lines, budget support items, and proposal-level assumptions, exclusions, and unknowns before accepting the final review package.

## GitHub seed verification

Verified on 2026-06-23:

```text
origin/main: 4d3d67b0324c59aba90f9a3100dc082f19f8b84a
GitHub Actions ci run: 28054850346
status: success
```
