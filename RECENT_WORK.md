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
