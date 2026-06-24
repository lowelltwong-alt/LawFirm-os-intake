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
-> data-origin and authorization gate
-> source inventory
-> provenance-preserving segmentation
-> party and relationship-role candidates
-> inbound-event, matter-family, and representation-posture candidates
-> date/deadline and missing-information candidates
-> independent evidence review
-> dry-run Exception Lake candidates for missing source, ambiguity, prompt injection, or blockers
-> human intake confirmation
-> budget precondition gate
-> conflict-search seed packet (no conflict conclusion)
-> legal budget proposal (not approved or submitted)
-> matter-opening readiness packet
-> deterministic safety gate report
-> consolidated matter-opening review package and manifest
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
|   |-- raw_input.json
|   |-- contract_state_report.json
|   |-- ingestion_result.json
|   |-- source_inventory.json
|   |-- segments.json
|   |-- effective_context.json
|   |-- intake_preflight_packet.json
|   |-- intake_review_form.md
|   |-- exception_lake_candidates.jsonl
|   |-- exception_lake_readiness_report.json
|   |-- evidence_graph.json
|   `-- run_ledger.jsonl
`-- budget/
    |-- budget_precondition_report.json
    |-- human_review_outcome.<confirmation_id>.json
    |-- human_confirmation_history.jsonl
    |-- conflict_search_seed_packet.json
    |-- legal_budget_proposal.json
    |-- legal_budget_review_form.md
    |-- matter_opening_readiness.json
    |-- exception_lake_candidates.jsonl
    |-- exception_lake_readiness_report.json
    |-- safety_gate_report.json
    |-- matter_opening_review_package.md
    |-- review_package_manifest.json
    |-- evidence_graph.json
    `-- run_ledger.jsonl
```

The consolidated `matter_opening_review_package.md` is the human-facing north-star artifact. It points back to the structured packets and tells the reviewer what is known, what remains uncertain, which conflict-search seeds were prepared, what budget scenario was proposed, which exception candidates exist, what the safety gate verified, and why the workflow is still blocked.

Budget runs also write a typed human review outcome record and append it to `human_confirmation_history.jsonl`. Corrections are represented as later records with `supersedes_confirmation_id`; prior review outcomes are not silently mutated.

The quickstart uses `north-star-messy-intake.json`, a synthetic bundle with duplicate source text, a missing complaint attachment, misleading role/context signals, prompt-injection source content, missing intake fields, deadline candidates, and human-confirmed budget generation.

Every source-bound evidence reference in the generated packets includes the cited source ID, segment ID, segment offsets, and segment hash. Strict mode rejects refs that drift from the segment table.

The preflight run also writes `ingestion_result.json`, a Python reference artifact for the future high-volume ingestion boundary. It packages source inventory, coverage summary, structural segments, and one segment-level evidence ref per segment under the `rust_ready_ingestion_v0_1` parity contract.

The budget-stage `evidence_graph.json` carries the provenance forward into human review outcomes, conflict-search terms, budget lines, and budget support items. Structured refs such as human confirmations, synthetic practice-profile entries, and workflow-policy references are represented separately from observed source evidence.

## Practice context is configurable, not hidden prompt text

The same message can mean different things to different practices. A carrier assignment is common in an insurance-defense practice but unusual in a plaintiff practice. This repository therefore treats practice context as a versioned profile with explicit precedence and hashes.

Practice context may alter candidate rankings. It may **not** manufacture observed facts. Every classification preserves two distinct channels:

- `observed_evidence_refs`
- `context_signal_refs`

Human reviewers must confirm the matter type, representation posture, and principal party roles.

## Contract state gate

Every preflight run emits `contract_state_report.json` before it accepts the source bundle. The report verifies that `contracts.lock.json` and `repo_topology.lock.yaml` are present, parseable, marked `reviewed_seed_lock`, and pin the five governing LawFirm OS repos by immutable SHAs with the expected authority planes.

If that local authority state is missing or stale, the run fails closed before source inventory or classification. The report is carried forward into the budget manifest and final safety gate.

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

## Conflict-search seed boundary

The conflict-search output is a seed packet only. It groups represented client, instructing source, payer, insured, adverse party, claimant, opposing counsel, aliases, and unresolved-role terms for a conflicts team or future governed conflicts workflow.

Each normalized search term is evidence-bound through the human confirmation. A term without source-bound evidence refs is rejected instead of being emitted as a search seed. The packet still preserves `no_conflict_conclusion`.

## Budget boundary

The budget output is a proposal only. It may contain phases, tasks, staffing, hours, authorized synthetic rates, fee calculations, expenses, contingency, assumptions, exclusions, and unknowns. It cannot be submitted until a separate human approval workflow exists.

Every proposal-level assumption, exclusion, and unknown is mirrored as a `budget_support_items` entry with source evidence refs or structured refs to the human confirmation, synthetic practice profile, or workflow policy.

If rates are absent, the system emits an **hours-only** proposal. It never invents rates or totals.

Budget-stage uncertainty is also emitted as dry-run Exception Lake candidates. Unknowns, missing approved templates, and hours-only missing-rate states become reviewable workflow escalations with source evidence refs or structured refs, not silent budget defects.

Every preflight and budget candidate file is checked by `exception_lake_readiness_report.json`. The report proves candidates remain dry-run, exclude raw payloads, require canonical promotion or reviewed mapping, target the Exception Lake runtime repo, and carry valid source-inventory refs, source evidence refs, structured refs, or blocked states.

Every budget run emits `budget_precondition_report.json`. If confirmation is missing, mismatched, incomplete, evidence-free, or not `confirmed`, the run writes that failed report, a blocked run-ledger event, and a dry-run Exception Lake candidate, then stops before producing a conflict seed, budget proposal, readiness packet, safety report, or review package.

## Safety gate

The final budget run emits `safety_gate_report.json`. This deterministic report checks that the output remains synthetic-only, contract-state-bound, human-confirmed, conflict-search-only, not submittable, blocked from engagement and matter opening, not docketed, not billed, and local-file-only.

The same gate also verifies evidence completeness for normalized conflict-search terms, budget lines, budget support items, and proposal-level assumptions, exclusions, and unknowns. A failed check raises before the final review package is accepted.

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

## Rust readiness

Python remains the starter reference implementation. If future document volume or constrained compute requires Rust, the only approved hot-path boundary is source inventory, segmentation, hashing, and evidence-ref emission. Any Rust adapter must prove parity with the Python reference for offsets, hashes, segment structure, prompt-injection flags, duplicate/missing-source states, and schema-compatible JSON before it can replace the Python path.

Preparation now means keeping that boundary narrow, schema-first, and golden-testable. The current `ingestion_result.json` is the local parity oracle: a Rust adapter may not replace it unless it produces schema-compatible inventory, segments, coverage summary, and segment evidence refs that match the Python reference on synthetic fixtures and holdouts. It does not mean adding a second runtime before profiling proves ingestion is the bottleneck.

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

Starter repository. The mock workflow is executable and testable. Canonical contract promotion into sibling repositories, live public-data ingestion, provider adapters, and production integration remain governed future work.
