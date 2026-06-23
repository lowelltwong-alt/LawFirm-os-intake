# Architecture

## Design decision

This repo is a vertical composition/evaluation layer over the LawFirm OS platform. It does not become a fourth platform plane or replace the three-plane control/execution/evidence architecture.

```text
Semantic Substrate (authority)
        ↓ pinned contracts
Orchestrator (execution owner)
        ↓ invokes approved skills and evidence tools
Intake vertical (workflow composition and evaluation)
        ↓ emits contract-locked runtime evidence
Exception Lake (append-only evidence)
```

Skills Registry and Legal Knowledge Runtime are governed capability providers, not authority peers.

## Deterministic versus model work

| Deterministic code | Bounded model work |
|---|---|
| data-origin gate | party/entity extraction candidates |
| schema validation | relationship-role candidates |
| source hashing | matter-family ranking |
| structural segmentation | missing-information suggestions |
| context precedence | contradiction/coverage critique |
| state transitions | budget narrative assumptions within approved template |
| authorization and revocation | difficult ambiguity adjudication |
| calculations | — |
| evidence graph assembly | — |
| packet writing | — |

Side effects and legal authority stay deterministic and human-governed.

## Stable domain seams

The vertical should integrate through provider-neutral interfaces:

- `ContextProvider`
- `SpecialistSkill`
- `EvidenceTool`
- `HumanApprovalGate`
- `RunLedger`
- `ExceptionSink`
- `ModelAdapter`
- `ArtifactStore`

Frameworks such as Claude Agent SDK, LangGraph, MCP, or Temporal may later implement execution seams. They must not become the domain model or audit authority.

## State externalization

Authoritative run state never lives only in a model context window. The workflow persists:

- source inventory;
- segments and hashes;
- effective context and profile hash;
- candidate outputs;
- critic findings;
- human confirmation;
- conflict seed;
- budget proposal;
- evidence graph;
- append-only run events.

## Graph posture

The starter emits a typed JSON evidence graph. It does not require a graph database or GraphRAG. A graph runtime may be justified later only if evaluation shows that cross-document relationship retrieval is the bottleneck.

## Rust-ready ingestion posture

Python is the reference implementation for the starter. If future document volume or constrained compute makes ingestion expensive, the only Rust-ready boundary is the deterministic source inventory, structural segmentation, hashing, and `EvidenceRef` emission layer.

Rust must not own legal classification, party roles, matter routing, conflict conclusions, budget decisions, connector writes, or authority policy. Before adoption, a Rust adapter must prove golden parity with the Python reference for offsets, hashes, segment structure, prompt-injection flags, duplicate/missing-source states, and schema-compatible JSON.

Preparing for Rust now means preserving JSON contracts, deterministic fixture outputs, and narrow adapter seams. The starter should not add a Rust crate or dual implementation until profiling shows ingestion is the bottleneck.

## Throughput

The first useful throughput unit is:

> Human-accepted, evidence-complete intake packets per reviewer hour.

For the budget stage:

> Human-accepted budget proposals per pricing/reviewer hour without safety or evidence defects.

Agent count, model calls, tokens, and raw processed messages are costs or diagnostics, not throughput.
