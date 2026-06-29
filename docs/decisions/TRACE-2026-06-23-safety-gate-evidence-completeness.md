# TRACE-2026-06-23 - Safety Gate Evidence Completeness

## Context

The intake workflow already emitted source-bound evidence refs for conflict-search terms, budget lines, and budget support items. The final safety gate checked prohibited transitions, but it did not independently prove that those downstream artifacts still carried valid packet-bound evidence or structured support.

## Decision

Extend `SafetyGateReport` with deterministic evidence-completeness checks for:

- normalized conflict-search terms;
- budget lines;
- budget support items;
- proposal-level assumptions, exclusions, and unknowns.

Conflict-search terms and budget lines must cite evidence refs that match the packet segment table by source ID, segment ID, offsets, and hash. Budget support items must carry either matching source evidence refs or a structured ref. Proposal-level assumptions, exclusions, and unknowns must be mirrored by support items.

## Safety Boundary

This does not create a conflict conclusion, approve a budget, submit a budget, clear engagement, open a matter, docket a deadline, write to external systems, or promote intake schemas into platform canon.

This also does not add Rust. Rust remains a future deterministic ingestion acceleration path only after profiling shows the source inventory, segmentation, hashing, or evidence-ref emission layer is the bottleneck and a Rust adapter proves golden parity with the Python reference.

## Authority

This is local candidate-surface behavior in `LawFirm-os-intake`. Semantic Substrate remains the authority for promoted contract shape, route IDs, event classes, and evidence-ref canon. Orchestrator remains the future runtime owner for final package assembly and governed handoffs.

## Validation

- Unit coverage fails closed for an evidence-free conflict seed term.
- Unit coverage fails closed for an evidence-free budget line.
- Unit coverage fails closed for an unsupported budget support item.
- Unit coverage fails closed for proposal-level budget text that lacks a matching support item.
- Existing passing review-package flow now asserts that the new safety checks are present.

## Follow-Up

When the sibling repos promote stable contracts, propose the safety-gate evidence-completeness checks as part of the Orchestrator package-acceptance gate and Exception Lake admission evidence.
