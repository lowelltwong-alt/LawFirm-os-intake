# LawFirm OS Intake

**Canonical machine name:** `LawFirm-os-intake`  
**Remote:** `lowelltwong-alt/LawFirm-os-intake`  
**Role:** vertical workflow composition and evaluation  
**Authority plane:** none

This repository is the end-to-end reference implementation for a governed law-firm workflow that begins with messy inbound material and ends with a **human-reviewable legal budget proposal**.

It is not a second orchestrator, a conflicts system, an engagement system, or a DMS connector.

## Target workflow

```text
messy inbound source
-> reviewed contract-state gate for sibling repo locks
-> data-scope gate report proving synthetic-only authorization before raw payload write
-> source inventory
-> provenance-preserving segmentation
-> party and relationship-role candidates
-> inbound-event, matter-family, and representation-posture candidates
-> date/deadline and missing-information candidates
-> evidence completeness report proving candidate refs, unknown options, and review boundaries
-> context boundary report proving practice priors are context signals, not observed evidence
-> deadline docketing guard report proving review-only candidates and no docketing
-> independent evidence review
-> dry-run Exception Lake candidates for missing source, ambiguity, prompt injection, or blockers
-> human intake confirmation
-> budget precondition gate
-> conflict-search seed packet (no conflict conclusion)
-> legal budget proposal (not approved or submitted)
-> budget submission guard report proving no client/carrier delivery or billing handoff
-> matter-opening readiness packet
-> deterministic safety gate report
-> consolidated matter-opening review package, manifest, and completeness report
-> blocked pending conflicts, engagement, and authorized matter opening
```

The first usable slice is intentionally narrow: **synthetic input only, local files only, no external writes, and mandatory human confirmation before budget generation**.

## Why this repo exists

The five LawFirm OS repos already separate canonical authority, execution, evidence, reusable skills, and legal knowledge. Intake needs a vertical place to prove that those layers can cooperate on one real law-firm value stream without creating a new authority center.

| Repository | Role in this workflow |
|---|---|
| `LawFirm-os-semantic-substrate` | Canonical schemas, registries, practice-context contracts, governance, route and approval doctrine |
| `LawFirm-os-orchestrator` | Runtime owner for gates, model/tool routing, human pauses, budgets, checkpoints, and evidence assembly |
| `LawFirm-os-exceptions-lake-runtime` | Append-only runtime evidence, corrections, defects, escalations, and learning candidates |
| `LawFirm-os-skills-registry` | Promoted specialist skills, trust records, prompt versions, allowed contexts, and revocation |
| `LawFirm-os-legal-knowledge-runtime` | Bounded evidence retrieval, public-source adapters, provenance, and Legal Context Bundles |
| **`LawFirm-os-intake`** | Composes and evaluates the intake-to-budget vertical; owns no platform canon |

See `docs/lawfirm-os-integration.md` and `repo_topology.yaml`.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python scripts/export_schemas.py
python -m pytest

python -m lawfirm_os_intake demo \
  --input examples/synthetic/inbound/north-star-messy-intake.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --confirmation-template examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json \
  --out-dir .lawfirm-os-intake/demo
```

The demo emits:

```text
.lawfirm-os-intake/demo/
|-- human_confirmation.json
|-- preflight/<run_id>/
|   |-- contract_state_report.json
|   |-- data_scope_gate_report.json
|   |-- raw_input.json
|   |-- ingestion_result.json
|   |-- ingestion_volume_profile.json
|   |-- rust_ingestion_readiness_report.json
|   |-- source_inventory.json
|   |-- segments.json
|   |-- effective_context.json
|   |-- intake_preflight_packet.json
|   |-- intake_review_form.md
|   |-- evidence_completeness_report.json
|   |-- context_boundary_report.json
|   |-- deadline_docketing_guard_report.json
|   |-- exception_lake_candidates.jsonl
|   |-- exception_lake_readiness_report.json
|   |-- exception_lake_handoff_manifest.json
|   |-- evidence_graph.json
|   |-- run_ledger_integrity_report.json
|   `-- run_ledger.jsonl
`-- budget/
    |-- budget_precondition_report.json
    |-- human_review_outcome.<confirmation_id>.json
    |-- human_confirmation_history.jsonl
    |-- human_gate_status_report.json
    |-- budget_submission_guard_report.json
    |-- conflict_search_seed_packet.json
    |-- legal_budget_proposal.json
    |-- legal_budget_review_form.md
    |-- matter_opening_readiness.json
    |-- exception_lake_candidates.jsonl
    |-- exception_lake_readiness_report.json
    |-- exception_lake_handoff_manifest.json
    |-- safety_gate_report.json
    |-- matter_opening_review_package.md
    |-- review_package_manifest.json
    |-- review_package_completeness_report.json
    |-- evidence_graph.json
    |-- run_ledger_integrity_report.json
    `-- run_ledger.jsonl
```

The consolidated `matter_opening_review_package.md` is the human-facing north-star artifact. It points back to the structured packets and tells the reviewer what is known, which candidate alternatives were considered, what remains uncertain, which human gates remain, which conflict-search seeds to use, what budget scenario and line items were proposed, which exception candidates exist, what the safety gate verified, and why the workflow is still blocked. Reviewer-facing known facts, candidate alternatives, party-role alternatives, deadlines, missing-information findings, critic findings, conflict terms, budget lines, budget supports, matter-opening blockers, and prohibited-action guardrails show their source evidence refs or structured policy refs inline instead of requiring a reviewer to hunt through JSON first.

The same package now renders authority/precondition checks, source inventory, human-gate status, exception readiness, dry-run handoff posture, candidate support details, evidence-graph summary, run-ledger summary, and run-ledger integrity status inline. Reviewers can see contract-state status, human-review outcome, budget precondition checks, completed and pending human gates, each source's read/missing/duplicate state, dry-run Exception Lake posture, the future Exception Lake runtime owner, the fact that no SQLite or external write occurred in intake, hashes, attachment refs, provenance graph counts and key support edges, and the preflight/budget gate trail before opening the JSON artifacts.

Preflight runs write `evidence_completeness_report.json`. This local proof artifact records that party candidates, role alternatives, inbound-event, matter-family, representation-posture, deadline, missing-information, and critic outputs carry source-bound refs that match packet segments by source ID, segment ID, offsets, and hashes. It also proves explicit unknown options remain available, deadline candidates remain human-review-only, and human confirmation plus prohibited next steps stay present. The final package renders the report and package completeness fails if it is missing, failed, or no longer linked.

Preflight runs also write `context_boundary_report.json`. This local proof artifact records the effective context profile ID, version, and hash; verifies observed source evidence remains first in context precedence; verifies context signal refs are structured practice-profile refs; and proves context-influenced candidates stay `source_anchor_only` unless independently observed. The final package renders the report and package completeness fails if practice context is treated as observed evidence.

The budget run also writes `review_package_completeness_report.json`. This deterministic report proves the final package includes required local artifact refs, required markdown sections, human gates, data-scope gate proof, evidence-completeness proof, context-boundary proof, deadline docketing guard proof, budget submission guard proof, structured blocker details, safety-gate proof, dry-run Exception Lake readiness, run ledgers, run-ledger integrity reports, and non-authorization flags before the package is accepted.

The completeness report also checks that the linked intake and budget review forms preserve their required human-review sections, evidence-hash visibility where source-bound evidence exists, and non-authorization boundary text, so those standalone forms cannot silently lose source coverage, outcome handling, budget lines, support items, or submission-boundary content while the consolidated package still passes.

Budget runs also write a typed human review outcome record and append it to `human_confirmation_history.jsonl`. Corrections are represented as later records with `supersedes_confirmation_id`; prior review outcomes are not silently mutated. The budget run also writes `human_gate_status_report.json`, which records intake confirmation as completed and conflicts clearance, engagement authorization, budget review, and matter-opening authorization as pending human gates with the artifacts and workflow refs each gate controls.

Budget runs also write `budget_submission_guard_report.json`. This local proof artifact records that the budget remains `proposed_for_human_review`, is not authorized for client or carrier submission, has no client submission, no carrier submission, no billing handoff, no external writes, and remains blocked by the pending `human_budget_review` gate.

Template-backed budget form rendering can also write `budget_form_mapping_report.json`. This local proof artifact records the template hash, header cells, UTBMS row/write-cell mappings, L/E amount totals, and original-budget formula checks before the renderer fills a carrier-style workbook copy. Failed mapping or formula checks block workbook rendering; the sanitized reference workbook remains local and is not committed.

Preflight runs write `deadline_docketing_guard_report.json`. This local proof artifact binds every deadline candidate back to source evidence refs, marks the only next gate as `human_deadline_review`, records `docketing_action_performed=false` and `docketing_action_allowed=false`, and is carried into the final package manifest and completeness check. It does not characterize legal effect or create a docketing action.

Preflight, confirmed budget, and blocked-budget attempts also write `run_ledger_integrity_report.json`. This local report proves required gate events appear in order, event run IDs match, output refs exist, refs stay local, blocked events only appear in blocked paths, and no external writes occurred. It is a vertical proof artifact only; Orchestrator remains the future run-ledger authority.

The quickstart uses `north-star-messy-intake.json`, a synthetic bundle with duplicate source text, a missing complaint attachment, misleading role/context signals, prompt-injection source content, missing intake fields, deadline candidates, and human-confirmed budget generation.

Use `--fixture-gold examples/synthetic/gold/north-star-messy-intake.fixture-gold.json` to gate a preflight or demo run against reviewed synthetic gold. The run writes `fixture_gold_report.json` and fails closed when expected source coverage, top-three matter recall, role candidates, deadline candidates, missing information, exception labels, conflict/budget boundaries, safety status, final blockers, or external-write boundaries drift.

Run `bash scripts/smoke_demo.sh` for the north-star release smoke. After the demo and fixture-gold checks, it runs `scripts/audit_starter_release.py` and writes `budget/starter_release_audit_report.json`. That audit report checks the generated artifacts against starter release invariants: required outputs, synthetic-only scope, public-data catalog metadata-only posture, source coverage states, candidate surface completeness, evidence refs, evidence-graph deliverable coverage, human-review package story coverage, human gates, carrier/client separation, conflict-seed boundary, budget boundary, dry-run Exception Lake posture, safety boundary, run ledgers, noncanonical candidate registries, and Rust-readiness posture. The smoke then runs `scripts/audit_blocked_budget_attempt.py`, which intentionally submits a synthetic `needs_more_information` confirmation and writes `blocked-budget/blocked_budget_attempt_audit_report.json`; the audit proves no conflict seed, budget proposal, readiness packet, safety gate, or final review package is emitted before confirmed human review. Finally, `scripts/audit_context_counterfactual.py` writes `context-counterfactual/context_counterfactual_audit_report.json` to prove the same synthetic source preserves source inventory, segments, and observed evidence refs across practice profiles while allowing context to change rankings. These reports are local evaluation evidence only and do not create platform canon or legal authority.

The preflight `intake_review_form.md` is the first human pause. It shows detailed source inventory rows, including duplicate links, attachment refs, filenames, metadata keys, hashes, candidate alternatives, deadline and missing-information evidence, and review outcome handling. Only `confirmed` can proceed toward the budget precondition gate, and even then only after exact packet binding and evidence checks; all other outcomes remain blocked or human-only.

Every source-bound evidence reference in the generated packets includes the cited source ID, segment ID, segment offsets, and segment hash. Strict mode rejects refs that drift from the segment table.

Candidate classifications also carry `source_evidence_status`. When it is `observed_support`, the refs are direct source support for the label. When it is `source_anchor_only`, the refs only bind the candidate back to the packet for review; they are not observed support for the label. `unknown_option` preserves an explicit human-selectable unknown candidate with a source anchor.

The preflight run also writes `ingestion_result.json`, a Python reference artifact for the future high-volume ingestion boundary. It packages source inventory, coverage summary, structural segments, and one segment-level evidence ref per segment under the `rust_ready_ingestion_v0_1` parity contract. Each preflight also writes `ingestion_volume_profile.json`, a deterministic source/segment scale profile that can require profiling before any Rust adapter proposal while still keeping `rust_replacement_allowed=false`. The profile now carries reviewer-visible compute pressure signals, required performance profile dimensions, candidate Rust hot-path scope, `rust_adapter_proposal_state`, and `required_rust_transition_gates` so constrained-compute pressure is explicit without authorizing a replacement. `rust_ingestion_readiness_report.json` then proves the current artifact is usable as a future Rust parity target while keeping replacement unauthorized.

The budget-stage `evidence_graph.json` carries the provenance forward into human review outcomes, conflict-search terms, budget lines, budget support items, matter-opening blockers, and prohibited-action guardrails. Structured refs such as human confirmations, synthetic practice-profile entries, workflow-policy references, and prohibited-transition policy references are represented separately from observed source evidence.

The standalone `legal_budget_review_form.md` also renders itemized budget lines with hours, ranges, rates, synthetic-rate labels, expenses, assumptions, evidence refs, and a submission boundary. It is an internal review surface only; it does not authorize client or carrier delivery.

## Practice context is configurable, not hidden prompt text

The same message can mean different things to different practices. A carrier assignment is common in an insurance-defense practice but unusual in a plaintiff practice. This repository therefore treats practice context as a versioned profile with explicit precedence and hashes.

Practice context may alter candidate rankings. It may **not** manufacture observed facts. Every classification preserves two distinct channels:

- `observed_evidence_refs`
- `source_evidence_status`
- `context_signal_refs`

The refs field remains nonempty for packet validation and review binding. The status field tells whether those refs are direct observed support, source anchors for a context/prior-only alternative, or anchors for the explicit unknown option.

Human reviewers must confirm the matter type, representation posture, and principal party roles.

## Contract state gate

Every preflight run emits `contract_state_report.json` before it accepts the source bundle. The report verifies that `contracts.lock.json` and `repo_topology.lock.yaml` are present, parseable, marked `reviewed_seed_lock`, and pin the five governing LawFirm OS repos by immutable SHAs with the expected authority planes.

If that local authority state is missing or stale, the run fails closed before source inventory or classification. The report is carried forward into the budget manifest and final safety gate.

## Data scope gate

Every preflight run emits `data_scope_gate_report.json` before `raw_input.json` is written. The report proves the starter is in `synthetic_only` runtime mode, the bundle origin is `synthetic`, real client data, real matter data, and privileged data flags are false, public-data direct ingestion is not allowed, no external write occurred, and the raw payload has not been stored before the gate.

If the data scope gate fails, the run writes only the blocked gate report and ledger event, then stops before raw input storage, source inventory, ingestion, segmentation, candidate extraction, or review packet output. The passing report is carried into the final package manifest, safety gate, review package, and completeness report.

## The carrier/client rule

An insurance carrier may be the sender, instructing source, payer, or source of guidelines. That does not automatically establish that the carrier is the represented client. The workflow keeps these roles separate:

- insurance carrier
- instructing source
- payer
- insured
- prospective represented client
- represented client
- claimant/adverse party
- opposing counsel

Every party candidate and every role alternative carries source-bound evidence refs. A role alternative without packet-bound refs fails strict evidence validation before the preflight packet is accepted.

## Conflict-search seed boundary

The conflict-search output is a seed packet only. It groups represented client, instructing source, payer, insured, adverse party, claimant, opposing counsel, aliases, and unresolved-role terms for a conflicts team or future governed conflicts workflow.

Each normalized search term is evidence-bound through the human confirmation. A term without source-bound evidence refs is rejected instead of being emitted as a search seed. The packet still preserves `no_conflict_conclusion`.

## Budget boundary

The budget output is a proposal only. It may contain phases, tasks, staffing, hours, authorized synthetic rates, fee calculations, expenses, contingency, assumptions, exclusions, and unknowns. It cannot be submitted until a separate human approval workflow exists.

Every proposal-level assumption, exclusion, and unknown is mirrored as a `budget_support_items` entry with source evidence refs or structured refs to the human confirmation, synthetic practice profile, or workflow policy.

If rates are absent, the system emits an **hours-only** proposal. It never invents rates or totals.

Budget-stage uncertainty is also emitted as dry-run Exception Lake candidates. Unknowns, missing approved templates, and hours-only missing-rate states become reviewable workflow escalations with source evidence refs or structured refs, not silent budget defects.

Every preflight and budget candidate file is checked by `exception_lake_readiness_report.json`. The report proves candidates remain dry-run, exclude raw payloads, require canonical promotion or reviewed mapping, target the Exception Lake runtime repo, and carry valid source-inventory refs, source evidence refs, structured refs, or blocked states. Each stage also writes `exception_lake_handoff_manifest.json`, a local non-authoritative map of actual labels to broad future Lake classes, support modes, candidate files, and target runtime ownership. It explicitly records `sqlite_write_performed=false`; any SQLite persistence belongs in `LawFirm-os-exceptions-lake-runtime`, not this intake repo. Close party-role alternatives are emitted as `critic_role_candidates_ambiguous` workflow escalations so role uncertainty is reviewable. Untrusted source attempts to clear conflicts, open a matter, create an iManage workspace, docket deadlines, submit a budget, or send external messages are emitted as specific local `prohibited_transition_attempted_*` workflow-escalation candidates with evidence refs and structured refs to `workflow/prohibited-transitions.yaml`.

Every budget run emits `budget_precondition_report.json`. If confirmation is missing, mismatched, incomplete, evidence-free, or not `confirmed`, the run writes that failed report, a blocked run-ledger event, and a dry-run Exception Lake candidate, then stops before producing a conflict seed, budget proposal, readiness packet, safety report, or review package.

## Safety gate

The final budget run emits `safety_gate_report.json`. This deterministic report checks that the output remains synthetic-only, data-scope-gated, contract-state-bound, human-confirmed, conflict-search-only, not submittable, blocked from engagement and matter opening, carries forward the deadline docketing and budget submission guards, is not docketed, not billed, and local-file-only.

The same gate also verifies evidence completeness for normalized conflict-search terms, budget lines, budget support items, proposal-level assumptions, exclusions, unknowns, structured matter-opening blockers, and prohibited-action guardrails. A failed check raises before the final review package is accepted.

After the safety gate passes, `review_package_completeness_report.json` verifies package assembly itself. It fails closed if the manifest omits required artifacts, linked files are missing, review sections disappear, human gates, data-scope gate proof, deadline docketing guard proof, budget submission guard proof, or structured blocker details are absent, or the boundary flags no longer prove no conflict clearance, no budget submission, no raw payload, and no external writes.

## Agent architecture

The planned runtime uses bounded specialists, not a swarm:

1. source reader
2. party/role extractor
3. matter router
4. deadline/gap extractor
5. evidence critic
6. budget planner
7. frontier adjudicator only on governed escalation

A deterministic packet writer assembles outputs. Dynamic agent creation is prohibited. Every handoff is typed. A frontier model cannot replace human confirmation.

## Provider adapter boundary

The CLI accepts `--adapter deterministic` and `--adapter structured-model`. The structured-model path is a dry-run boundary only: it writes `model_adapter_report.json`, records the prompt registry hashes, sets a zero-call model budget, denies network/external-write/production connector tools, requires typed JSON under exported schemas, preserves the independent critic and human gates, and keeps deterministic workers authoritative.

No provider call is made, no raw payload is externalized, and the report is carried into the final review package under `### Model Adapter Boundary`.

## Rust readiness

Python remains the starter reference implementation. If future document volume or constrained compute requires Rust, the only approved hot-path boundary is source inventory, segmentation, hashing, and evidence-ref emission. Any Rust adapter must prove parity with the Python reference for offsets, hashes, segment structure, prompt-injection flags, duplicate/missing-source states, and schema-compatible JSON before it can replace the Python path.

Preparation now means keeping that boundary narrow, schema-first, measurable, and golden-testable. The current `data_scope_gate_report.json` proves a source bundle is authorized before any ingestion worker, Python or future Rust, stores raw input or emits derived artifacts. The current `ingestion_result.json` is the local parity oracle, `ingestion_volume_profile.json` records whether synthetic source/segment scale requires profiling before any Rust proposal, what compute pressure signals are present, which benchmark dimensions must be captured, and which deterministic hot-path functions Rust may cover. `rust_ingestion_readiness_report.json` records the checks a future adapter must satisfy before comparison even begins. A Rust adapter may not replace the Python path unless profiling justifies it, transition gates are reviewed, and it produces schema-compatible inventory, segments, coverage summary, and segment evidence refs that match the Python reference on synthetic fixtures and holdouts. See `docs/rust-ingestion-transition-plan.md` for the gate sequence. It does not mean adding a second runtime before profiling proves ingestion is the bottleneck.

## Current boundaries

- synthetic data only;
- no real client or matter data;
- no privileged data;
- no live email, iManage, conflicts, billing, carrier-portal, or court connector;
- no conflict clearance;
- no engagement decision;
- no matter opening;
- no deadline docketing;
- no budget submission;
- no canonical schema or taxonomy mutation;
- no external write;
- no dynamic agent creation.

## Start here

A builder or AI coding agent must read in this order:

1. `AI_WORK_START_HERE.md`
2. `REPO_ROLE.md`
3. `NON_GOALS.md`
4. `skill-agent-manifest.json`
5. `AGENTS.md`
6. `docs/sibling-repo-entry-points.md`
7. `docs/architecture.md`
8. `docs/workflow/intake-to-budget.md`
9. `docs/lawfirm-os-integration.md`
10. `docs/claude-for-legal-lessons.md`
11. `PREMORTEM.md`
12. `DEFINITION_OF_DONE.md`
13. `docs/ai-handoff/BUILDER_BRIEF.md`

## Status

Starter repository. The mock workflow is executable and testable. Canonical contract promotion into sibling repositories, live public-data ingestion, real provider calls, and production integration remain governed future work.
