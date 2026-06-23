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
-> data-origin and authorization gate
-> source inventory
-> provenance-preserving segmentation
-> party and relationship-role candidates
-> inbound-event, matter-family, and representation-posture candidates
-> date/deadline and missing-information candidates
-> independent evidence review
-> dry-run Exception Lake candidates for missing source, ambiguity, prompt injection, or blockers
-> human intake confirmation
-> conflict-search seed packet (no conflict conclusion)
-> legal budget proposal (not approved or submitted)
-> matter-opening readiness packet
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
  --input examples/synthetic/inbound/carrier-assignment-medmal.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --confirmation-template examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json \
  --out-dir .lawfirm-os-intake/demo
```

The demo emits:

```text
.lawfirm-os-intake/demo/
|-- human_confirmation.json
|-- preflight/<run_id>/
|   |-- raw_input.json
|   |-- source_inventory.json
|   |-- segments.json
|   |-- effective_context.json
|   |-- intake_preflight_packet.json
|   |-- intake_review_form.md
|   |-- exception_lake_candidates.jsonl
|   |-- evidence_graph.json
|   `-- run_ledger.jsonl
`-- budget/
    |-- conflict_search_seed_packet.json
    |-- legal_budget_proposal.json
    |-- legal_budget_review_form.md
    |-- matter_opening_readiness.json
    |-- exception_lake_candidates.jsonl
    |-- matter_opening_review_package.md
    |-- review_package_manifest.json
    |-- evidence_graph.json
    `-- run_ledger.jsonl
```

The consolidated `matter_opening_review_package.md` is the human-facing north-star artifact. It points back to the structured packets and tells the reviewer what is known, what remains uncertain, which conflict-search seeds were prepared, what budget scenario was proposed, which exception candidates exist, and why the workflow is still blocked.

## Practice context is configurable, not hidden prompt text

The same message can mean different things to different practices. A carrier assignment is common in an insurance-defense practice but unusual in a plaintiff practice. This repository therefore treats practice context as a versioned profile with explicit precedence and hashes.

Practice context may alter candidate rankings. It may **not** manufacture observed facts. Every classification preserves two distinct channels:

- `observed_evidence_refs`
- `context_signal_refs`

Human reviewers must confirm the matter type, representation posture, and principal party roles.

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

## Budget boundary

The budget output is a proposal only. It may contain phases, tasks, staffing, hours, authorized synthetic rates, fee calculations, expenses, contingency, assumptions, exclusions, and unknowns. It cannot be submitted until a separate human approval workflow exists.

If rates are absent, the system emits an **hours-only** proposal. It never invents rates or totals.

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
