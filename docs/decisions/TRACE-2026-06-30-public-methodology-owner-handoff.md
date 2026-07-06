# TRACE: Public Methodology Owner Handoff

## Context

The public methodology chain now produces a methodology report, a
structure-only synthetic fixture conversion plan, and a conversion review
packet. Those artifacts are still local candidate evidence. Without a separate
owner handoff packet, later work could treat local public-methodology evidence as
platform approval, Legal Knowledge Runtime adapter authorization, Orchestrator
runtime workflow approval, or Exception Lake admission authority.

## Decision

Add `build-public-methodology-owner-handoff`.

The command consumes:

- `public_source_methodology_report.json`;
- `public_synthetic_fixture_conversion_plan.json`;
- `public_synthetic_fixture_conversion_review_packet.json`.

It writes:

- `public_methodology_owner_handoff_report.json`;
- `public_methodology_owner_handoff_report.md`;
- `public_methodology_owner_handoff_packets.jsonl`;
- per-owner JSON/Markdown packets under `public_methodology_owner_packets/`.

The target owner lanes are Intake, Legal Knowledge Runtime, Semantic Substrate,
Orchestrator, and Exception Lake. Skills Registry is intentionally excluded in
this slice because no reusable skill, prompt-trust package, or supply-chain
surface is being added.

## Boundary

The handoff is a local owner-review request packet only. It does not create
issues, open PRs, write sibling repos, promote canon, create fixtures, ingest
public records, commit raw public payloads, authorize adapters, write
Lake/SQLite records, perform external writes, or apply learning.

## Red-Team Notes

- A local handoff packet can look like owner approval; every packet must keep
  owner review and later implementation PR gates explicit.
- A public methodology report can look like platform policy; canonical policy
  remains owned by Semantic Substrate.
- Legal Knowledge Runtime adapter review is not adapter authorization.
- Exception Lake audit planning is not Lake admission and must not include raw
  public payloads or identity-bearing public records.

## Validation Plan

- Ready methodology, conversion plan, and conversion review artifacts emit five
  ready owner packets.
- Blocked methodology-chain evidence emits blocked owner packets and a blocked
  report.
- Mismatched methodology/plan/review lineage blocks.
- Source-to-spec coverage, spec-to-review coverage, and required red-team scopes
  are checked deterministically.
- CLI output proves no issue creation, no PR creation, no sibling repo write, no
  promotion, no fixture generation, no public ingestion, no adapter
  authorization, no Lake/SQLite writes, and no silent learning.
