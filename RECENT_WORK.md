# Recent Work

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
