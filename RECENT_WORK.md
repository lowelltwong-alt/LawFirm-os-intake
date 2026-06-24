# Recent Work

## Exception Lake budget-change and actuals package slice - 2026-06-24

- Budget runs now write `exception_lake_mapping_package.json` for broken workbook formulas, missing code mappings, unknown budget drivers, guideline/cap issues, human budget changes, and actual-cost variance.
- Budget runs now write `budget_actual_comparison_report.json`; starter runs keep actuals unavailable and record no billing connector reads or writes.
- Added dry-run candidate builders for workbook mapping failures and actual-cost variance, while preserving Lake admission and SQLite ownership outside intake.

## Human-review hardening slice - 2026-06-24

- Budget runs now write `case_driver_profile.json` and embed `BudgetDriverProfileSummary` in `legal_budget_proposal.json`.
- The standalone budget review form and consolidated matter-opening review package render driver profile summary, scenario comparison, workbook mapping status, and unresolved budget assumptions.
- Package completeness now fails closed if those human-review surfaces, non-observed-fact boundaries, workbook non-submission posture, or case-driver artifact linkage drift.

## Starter creation — 2026-06-23

- Established remote target `lowelltwong-alt/LawFirm-os-intake`.
- Seeded private GitHub `main` and fixed CI validation order; latest verified seed commit is `4d3d67b0324c59aba90f9a3100dc082f19f8b84a`.
- Defined the repo as a vertical composition/evaluation layer rather than an authority plane.
- Added a synthetic-only local intake preflight and legal budget proposal demo.
- Added practice-context counterfactuals, human confirmation, conflict-search seeds, provenance-preserving segmentation, typed evidence graph, specialist manifests, frontier escalation limits, premortem, threat model, test plans, and cross-repo graduation paths.

## Build-out slice - 2026-06-23

- Hardened source inventory with hashes, duplicate detection, missing/unread/unreadable states, attachment refs, and coverage summary.
- Added typed missing-information candidates, strict evidence validation, generated intake review forms, grouped conflict-search terms, and deterministic budget calculation reports.
- Added synthetic holdout fixtures for duplicate/missing attachments and misleading sender/role ambiguity.
- Added a safe adapter boundary for deterministic and structured-model dry-run routing.

## Exception-candidate slice - 2026-06-23

- Added local `ExceptionLakeCandidate` schema and `exception_lake_candidates.jsonl` outputs for preflight and budget runs.
- Mapped missing/unread/unreadable sources to `retrieval_miss` and prompt injection, duplicate sources, critic findings, escalation, and matter-opening blockers to `workflow_escalation`.
- Kept the handoff dry-run only with no raw payload, no SQLite ownership, and no canonical event-class promotion from this repo.

## Review-package slice - 2026-06-23

- Added a consolidated `matter_opening_review_package.md` and `review_package_manifest.json` to the budget run output.
- The package links source coverage, known facts, unresolved review items, conflict-search seeds, budget scenario, exception candidates, blockers, prohibited actions, evidence graph refs, and run ledgers.

## Budget-support slice - 2026-06-23

- Added `BudgetSupportItem` records so proposal-level assumptions, exclusions, and unknowns carry evidence refs or structured refs.
- The budget review form and consolidated review package now expose those support records for human review.

## Safety-gate slice - 2026-06-23

- Added `SafetyGateReport` output for deterministic final checks over synthetic scope, human confirmation, conflict non-conclusion, budget non-submission, matter-opening blockers, docketing prohibition, billing/submission prohibition, and local-only artifacts.
- The workflow fails closed before final package acceptance if a safety check fails.

## North-star demo fixture - 2026-06-23

- Added `north-star-messy-intake.json` and matching confirmation template as the one-command acceptance fixture.
- Updated smoke coverage to require missing-source, duplicate-source, prompt-injection, safety-gate, review-package, and blocked-final-boundary outputs in one run.

## Conflict-seed evidence slice - 2026-06-23

- Required `ConflictSearchTerm` records to carry source-bound evidence refs from the human confirmation.
- Added fail-closed validation when conflict seed terms lack evidence, plus north-star and unit coverage.
- Tightened the Rust-ready ingestion ADR: Python stays the reference implementation, and Rust remains a future deterministic hot-path adapter only after profiling and golden parity.

## Human-review outcome history slice - 2026-06-23

- Added `HumanReviewOutcomeRecord` and schema export for typed review outcome handling.
- Budget runs now write `human_review_outcome.<confirmation_id>.json` and append it to `human_confirmation_history.jsonl` before budget preconditions.
- Added coverage that non-confirmed outcomes block budget output and superseding corrected confirmations append history instead of mutating prior outcomes.

## Budget-stage evidence graph slice - 2026-06-23

- Extended `evidence_graph.json` to include human review outcomes, conflict seed packets, conflict-search terms, budget lines, budget support items, and structured refs.
- Added graph edges from source segments or structured refs to conflict and budget artifacts so the graph proves the same provenance as the packets.
- Updated the matter-opening review package to show evidence refs for conflict-search terms.

## Budget-uncertainty exception slice - 2026-06-23

- Added `structured_refs` to dry-run `ExceptionLakeCandidate` records.
- Budget runs now emit workflow-escalation candidates for budget unknowns, missing synthetic templates, and hours-only missing-rate states.
- Added tests for normal budget unknowns, missing rates, and missing template exception candidates.

## Unread-source coverage slice - 2026-06-23

- Added a synthetic holdout fixture with an unread attachment.
- Source coverage summaries now count `unread_sources` separately from missing and unreadable sources.
- Unread sources now render in review summaries and emit `source_unread` dry-run `retrieval_miss` candidates.

## Safety-gate evidence-completeness slice - 2026-06-23

- Added deterministic safety-gate checks for evidence-bound conflict-search terms, budget lines, budget support items, and proposal-level budget texts.
- Added fail-closed coverage for evidence-free conflict seed terms, evidence-free budget lines, unsupported budget support items, and unsupported proposal-level budget text.
- Kept Rust readiness as a narrow future ingestion adapter boundary; Python remains the reference oracle until profiling and golden parity justify Rust.

## Python-reference ingestion boundary slice - 2026-06-23

- Added `IngestionResult` and `ingestion_result.json` as the Python reference parity oracle for source inventory, coverage summary, structural segments, and segment-level evidence refs.
- Wired preflight to consume that artifact while preserving existing `source_inventory.json`, `segments.json`, and CLI outputs.
- Added tests proving parity refs match segment offsets/hashes and fail closed on drift; no Rust runtime or authority expansion was added.

## Exception-Lake readiness slice - 2026-06-23

- Added `ExceptionLakeReadinessReport` and `exception_lake_readiness_report.json` for preflight, budget, and failed budget-precondition exception candidate files.
- The readiness gate proves candidates remain dry-run, raw-payload-free, promotion-required, target the Lake runtime repo, and carry valid source/evidence/structured/state support.
- Added fail-closed tests for raw-payload candidates and drifted exception evidence refs.

## Party-role evidence slice - 2026-06-23

- Added per-role evidence refs to `RoleCandidate` so relationship-role alternatives are source-bound instead of relying only on party-level support.
- Strict preflight validation now fails if a role candidate ref drifts from the cited segment.
- Evidence graphs now include `party_role_candidate` nodes and `supports_party_role_candidate` edges.

## Rust-ingestion readiness slice - 2026-06-24

- Added `RustIngestionReadinessReport` and `rust_ingestion_readiness_report.json` so each preflight run proves the Python ingestion artifact is suitable as a future Rust parity target.
- The report verifies adapter lock, source inventory coverage, recomputed source hashes, bounded segment offsets, recomputed segment hashes, segment evidence refs, and absence of legal decision scope.
- Kept `rust_replacement_allowed=false`; no Rust runtime, FFI bridge, connector write, legal classification, conflict decision, budget decision, or authority expansion was added.

## Review-package completeness slice - 2026-06-24

- Added `ReviewPackageCompletenessReport` and `review_package_completeness_report.json` as the final deterministic package-assembly proof.
- The report checks required artifact refs, linked file existence, markdown sections, human gates, final blockers, prohibited actions, safety-gate status, dry-run Exception Lake readiness, run ledgers, and non-authorization boundary flags.
- Added fail-closed tests for missing artifact keys and missing review sections before the package is accepted.

## Human-review evidence surface slice - 2026-06-24

- Updated the intake and matter-opening review Markdown to show evidence refs inline for human-confirmation decision evidence, confirmed parties, deadline candidates, missing-information candidates, and critic findings.
- Kept the change schema-neutral: underlying evidence contracts stay stable, and the Markdown becomes easier for reviewers to audit.
- Added tests and smoke coverage so the north-star review package cannot hide key evidence refs behind JSON-only artifacts.

## Final-package candidate alternatives slice - 2026-06-24

- Added a `Candidate Alternatives` section to the final matter-opening review package.
- The section renders top inbound-event, matter-family, representation-posture, and party-role candidates with source evidence refs and context signals.
- The completeness report now requires the section before final package acceptance.

## Final-package human gates slice - 2026-06-24

- Added a `Required Human Gates` section to the final matter-opening review package.
- The section makes conflicts clearance, engagement authorization, budget review, and matter-opening authorization visibly required before any real-world action.
- The completeness report now requires the section before final package acceptance.

## Final-package budget detail slice - 2026-06-24

- Added calculation summary, budget line, and budget support subsections to the final matter-opening review package.
- Budget lines now render hours/ranges, rate source, synthetic-rate label, fees, expenses, assumptions, formula, and source evidence refs inline.
- The completeness report now requires those budget detail subsections before final package acceptance.

## Final-package source and ledger visibility slice - 2026-06-24

- Added source-inventory detail to the final matter-opening review package, including read/missing/duplicate states, hashes, attachment refs, and duplicate links.
- Added a run-ledger summary showing preflight and budget gate steps, statuses, input counts, output counts, and notes.
- The completeness report now requires source inventory and run-ledger sections before final package acceptance.

## Final-package evidence graph summary slice - 2026-06-24

- Added an evidence-graph summary to the final matter-opening review package.
- The summary renders graph refs, node/edge counts, node-type counts, relationship counts, and key provenance edge examples.
- The completeness report now requires the evidence-graph summary before final package acceptance.

## Final-package authority and preconditions slice - 2026-06-24

- Added authority and precondition subsections to the final matter-opening review package.
- The package now renders contract-state status, reviewed lock status, dependency pins, human review outcome, and budget precondition checks inline.
- The completeness report now requires those authority/precondition sections before final package acceptance.

## Final-package exception detail slice - 2026-06-24

- Added Exception Lake readiness and exception candidate detail subsections to the final matter-opening review package.
- The package now renders dry-run admission state, raw-payload exclusion, canonical-promotion requirement, target runtime repo, source refs, evidence refs, structured refs, and blocked states inline.
- The completeness report now requires those exception readiness/detail sections before final package acceptance.

## Final-package evidence-ref hash slice - 2026-06-24

- Updated reviewer-facing evidence refs to render source ID, segment ID, offsets, and hash inline.
- Added test and smoke coverage requiring the final matter-opening review package to expose evidence hashes.
- Kept the change schema-neutral: existing `EvidenceRef` records already carried hashes, and the Markdown now shows them.

## Exception-detail evidence-ref hash slice - 2026-06-24

- Updated the Exception Candidate Details renderer so dry-run candidate evidence refs also show source ID, segment ID, offsets, and hash inline.
- Added package and smoke coverage scoped to the exception-detail section, not just the package globally.
- Kept Exception Lake behavior dry-run only; no admission, SQLite, event-class promotion, or schema change was added.

## Intake-review outcome handling slice - 2026-06-24

- Expanded `intake_review_form.md` source coverage rows with filenames, duplicate links, attachment refs, metadata keys, character counts, and hashes.
- Added explicit review outcome handling so reviewers see which outcomes block budget-stage output and that corrections append or supersede prior records.
- Added tests and smoke coverage for detailed source inventory and outcome handling in the preflight review form.

## Budget-review line detail slice - 2026-06-24

- Added itemized budget lines to `legal_budget_review_form.md`, including hours/ranges, rates, synthetic-rate labels, fees, expenses, assumptions, formulas, and evidence refs.
- Added a submission-boundary section showing `proposed_for_human_review`, no client/carrier submission authorization, and remaining human review blockers.
- Added focused and smoke coverage so the standalone budget review form cannot become less auditable than the final matter-opening package.

## Linked-review-form completeness slice - 2026-06-24

- Extended `review_package_completeness_report.json` to verify required sections in the linked intake and budget review forms.
- The report now fails if the intake form loses source coverage, reviewer decision, outcome handling, or prohibited-next-step sections.
- The report also fails if the budget form loses calculation, budget line, support, review-check, or submission-boundary sections.

## Linked-review-form evidence and boundary slice - 2026-06-24

- Extended the review-package completeness report to verify linked review forms still expose evidence hashes where source-bound evidence exists and preserve non-authorization boundary text.
- Added regression coverage for intake-form evidence hash loss, budget-form evidence hash loss, and budget-form submission-boundary loss.
- Added smoke coverage for the new `linked_review_forms_preserve_evidence_and_boundaries` acceptance check.

## Ingestion-volume profile slice - 2026-06-24

- Added `ingestion_volume_profile.json` so preflight runs record deterministic source/segment scale before any future Rust adapter decision.
- Added a synthetic high-volume proxy fixture that crosses the local source-count profiling threshold while keeping `rust_replacement_allowed=false`.
- Carried the profile into the review package manifest and completeness checks so the Rust-readiness posture remains visible in the north-star package.

## Prohibited-transition exception slice - 2026-06-24

- Added specific dry-run `prohibited_transition_attempted_*` Exception Lake candidates for untrusted source attempts to clear conflicts, open matters, create iManage workspaces, docket deadlines, submit budgets, or send external messages.
- Added structured refs from those local candidates back to `workflow/prohibited-transitions.yaml` while keeping broad `workflow_escalation` lake mapping and no raw payload.
- Added unit, north-star, and smoke coverage so prohibited-transition attempts remain visible in exception artifacts and the final review package.

## Role-ambiguity critic slice - 2026-06-24

- Added a deterministic `ROLE_CANDIDATES_AMBIGUOUS` critic finding when party-role alternatives are too close for automatic reliance.
- The existing dry-run Exception Lake candidate path now emits `critic_role_candidates_ambiguous` workflow escalations with source-bound evidence refs.
- Added holdout, north-star, and smoke coverage so role uncertainty becomes an explicit review/evaluation record.

## Structured readiness blocker slice - 2026-06-24

- Added structured `blocker_details` and `prohibited_action_details` to `matter_opening_readiness.json`.
- The final review package now renders workflow-policy and prohibited-transition refs explaining why conflicts clearance, engagement, matter opening, workspace creation, and budget submission remain blocked.
- The safety gate, completeness report, evidence graph, schema export, north-star test, and smoke script now fail closed if readiness blockers or prohibited actions lose structured support.

## Human gate status report slice - 2026-06-24

- Added `human_gate_status_report.json` so confirmed budget runs have a typed record of completed intake confirmation and pending conflicts, engagement, budget-review, and matter-opening gates.
- The final review package now renders gate status, blocked transitions, artifact refs, and workflow refs beside the existing human-gate checklist.
- Package completeness, schema export, north-star tests, and smoke coverage now fail closed if pending human gates are omitted or incorrectly marked complete.

## Deadline docketing guard report slice - 2026-06-24

- Added `deadline_docketing_guard_report.json` so preflight runs have a typed proof that deadline candidates are source-bound, review-only, and not docketed.
- The final review package now renders the guard status, no-docket flags, `human_deadline_review`, candidate evidence refs, and prohibited-transition refs.
- The safety gate, package completeness, schema export, focused tests, north-star tests, and smoke coverage now fail closed if the deadline guard is missing, loses evidence, stops requiring human review, or claims docketing occurred.

## Budget submission guard report slice - 2026-06-24

- Added `budget_submission_guard_report.json` so confirmed budget runs have a typed proof that the proposal remains review-only and no client submission, carrier submission, billing handoff, or external write occurred.
- The final review package now renders the budget guard status, guarded actions, no-submission/no-billing flags, and required `human_budget_review` gate.
- The safety gate, package completeness, starter release audit, schema export, focused tests, north-star tests, and smoke coverage now fail closed if the budget guard is missing, loses the pending budget gate, or claims submission/billing occurred.

## Starter audit north-star content slice - 2026-06-24

- Hardened `starter_release_audit_report.json` so the release smoke proves more than file existence: source coverage states, candidate surface completeness, evidence-graph node/edge coverage, review-package story sections, and full preflight/budget ledger steps are now checked.
- Added fail-closed coverage for hollow matter-family candidates, missing budget-line graph nodes, and a review package that loses the Candidate Alternatives section.
- Smoke coverage now greps the new content-level audit checks so the north-star release path fails if those objective-level proofs disappear.

## Front-door reference validation slice - 2026-06-24

- Added `docs/claude-for-legal-lessons.md` so the AI/front-door reading order no longer points to a missing local policy file.
- Updated `AI_TABLE_OF_CONTENTS.md` to point completion readers at `BUILD_VERIFICATION.md` instead of the absent `VALIDATION_REPORT.md`.
- Hardened `scripts/validate_repo.py` and added tests so README, AI work start, AI table-of-contents, and Claude front-door file refs fail validation if they point to missing local files or directories.

## Data-scope gate report slice - 2026-06-24

- Added `data_scope_gate_report.json` so preflight proves synthetic-only data scope before `raw_input.json` or derived ingestion artifacts are written.
- The gate fails closed on non-synthetic origin, real client or matter data flags, privileged data flags, public direct-ingestion posture, raw-payload-before-gate drift, or external writes.
- Carried the report into the final review package, manifest, safety gate, package completeness report, starter audit, schema export, focused tests, north-star tests, and smoke coverage.
- Kept the future Rust path subordinate to the same gate: Python remains the reference runtime, and any future Rust ingestion worker must run only after a passing data-scope report and prove parity before replacement.

## Public-data catalog boundary slice - 2026-06-24

- Added deterministic validation that `examples/public/catalog.yaml` remains planning-only metadata and no catalog entry allows direct runtime ingestion.
- `scripts/validate_repo.py` and `starter_release_audit_report.json` now fail closed if the public catalog drifts toward downloaded payloads or runtime ingestion.
- Added focused coverage proving `data_origin: public_reference` bundles block at the data-scope gate before raw input storage.

## Correspondence-dump message-boundary slice - 2026-06-24

- Added message-indexed segmentation for synthetic correspondence dumps with repeated `From:` boundaries.
- The segmenter now preserves dump preambles, headers, body paragraphs, quoted history, signatures, attachment refs, offsets, hashes, and source-instruction risk flags inside messy exports.
- Added a synthetic holdout proving risky quoted instructions in a dump become dry-run exception candidates instead of actions.

## Evidence-completeness report slice - 2026-06-24

- Added `evidence_completeness_report.json` so preflight runs durably prove candidate evidence refs match packet segments instead of relying only on no thrown exception.
- The report covers party candidates, role alternatives, inbound-event, matter-family, representation-posture, deadline, missing-information, and critic outputs, plus unknown options and human-review boundary flags.
- The final review package, manifest, package completeness report, starter audit, schema export, tests, and docs now fail closed if the evidence-completeness proof is missing or drifts.

## Context-boundary report slice - 2026-06-24

- Added `context_boundary_report.json` so preflight runs durably prove practice context remains a transparent prior rather than observed evidence.
- The report checks evidence precedence, structured context refs, context-influenced candidate status, unknown option preservation, human confirmation, non-authoritative posture, and no external writes.
- The final review package, manifest, package completeness report, starter audit, schema export, tests, and docs now fail closed if the context-boundary proof is missing or drifts.

## Budget-form mapping report slice - 2026-06-24

- Added `budget_form_mapping_report.json` for template-backed UTBMS workbook rendering.
- The report checks template hash, header coordinates, code-to-row/write-cell mappings, L/E amount totals, missing/duplicate/unmapped codes, original-budget total formulas, phase subtotal formulas, and task remaining formulas.
- The renderer blocks before creating a filled workbook when mapping or original-budget formula checks fail; the sanitized workbook remains local and only a structural test manifest is committed.

## Budget-form template audit slice - 2026-06-24

- Added `lawfirm-os-intake budget-form-audit` and `budget_form_template_audit_report.json` so a carrier-style UTBMS workbook can be tested before any matter-specific budget exists.
- Added `docs/budget-template-checklist.md` with known-good template requirements and the local audit command.
- The audit writes a report and returns nonzero on missing headers, missing/duplicate UTBMS codes, or broken original-budget formulas without mutating the workbook.

## Budget scenario-set slice - 2026-06-24

- Added embedded `BudgetScenarioSet` output with `early_resolution`, `standard`, and `through_trial` branches, ranges, included phases, and included UTBMS code candidates.
- The legacy `BudgetProposal` totals and lines now map to the selected `standard` scenario for compatibility while preserving through-trial visibility in the scenario set.
- Updated budget review and matter-opening review packages to render scenario comparison without authorizing client/carrier submission.

## Stronger budget-driver slice - 2026-06-24

- Added bounded severity, liability, and venue intensity multipliers from local synthetic driver policy.
- Added `BudgetDriverEffect` records so count scaling, intensity multipliers, coverage boundaries, and unknown drivers expose value, provenance, policy refs, affected phases/tasks, cap state, and the no-default-as-observed-fact invariant.
- Added `BudgetGuidelineFlag` records for synthetic role-rate, phase-budget, and total-budget caps; flags require human review when triggered and never rewrite budget values.

## Second matter-family slice - 2026-06-24

- Added `auto_liability_defense` synthetic driver defaults and a UTBMS-coded auto/BI defense budget template.
- Added `carrier-assignment-auto-bi.json` plus a matching confirmation fixture.
- Added end-to-end tests proving auto/BI preflight ranking, confirmation binding, driver resolution, budget generation, scenario set, driver effects, guideline flags, final review package, and non-submission boundary.
