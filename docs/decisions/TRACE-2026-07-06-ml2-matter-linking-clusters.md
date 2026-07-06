# TRACE 2026-07-06 ML2 Matter-Linking Clusters

## Decision

Add deterministic pairwise matter-linking rules and review-only cluster
proposals on top of the ML1 key-extraction artifact. The new layer consumes
`MatterLinkKeyExtractionReport`, emits `MatterLinkDecisionRecord` rows and
`MatterClusterProposal` clusters, and remains candidate-only until human
matter-linking review.

## Why

The intake workflow must handle multiple documents from the same sender without
an official matter number. Same sender and shared policy are not enough. Strong
keys, medium corroboration, weak signals, conflicts, no-key documents, and bridge
documents need replayable decisions before any later preflight or budget work can
trust a bundle boundary.

## Boundary

- Candidate-only and synthetic-only.
- Consumes key-extraction reports; does not re-ingest raw production data.
- No budget generation, budget submission, conflict conclusion, matter opening,
  connector call, Lake write, SQLite write, persistent cross-bundle state, or
  silent learning.
- Clusters are proposals, not matter identity assertions.
- Human confirmation remains required before a cluster can feed downstream
  budget or conflict-seed workflows.

## Rule Coverage

- R1 strong-key disagreement splits.
- R2 same strong key merges if party context does not conflict.
- R3 same strong key with conflicting party-pair context blocks.
- R4 shared policy with different claimant/date context splits.
- R5 thread drift with conflicting strong keys blocks.
- R6/R7/R8 merge on same thread, adjuster ref, or party pair plus incident date.
- R9/R11/R14 hold same party without same incident, weak-only agreement, and
  insufficient keys.
- B2 bridge documents with multiple strong keys block transitive merge
  laundering.

## Tests

- Synthetic fixtures cover two matters from one sender, thread drift, claim-number
  reuse, shared policy, no-key attachment, and bridge document.
- A 20-shuffle permutation test verifies cluster signatures are order invariant.
- CLI test verifies `matter_cluster_proposals.json` and
  `matter_link_decisions.jsonl` are written locally only.

## Premortem

The highest-risk bug is transitive laundering: document A merges with bridge B,
bridge B merges with document C, and A/C strong-key disagreement disappears.
The implementation builds decisions from the full pairwise matrix and marks
split/block evidence inside connected components as `blocked_conflict`.

Another risk is treating cluster proposals as confirmed matters. The schema keeps
`matter_identity_asserted=false`, `matter_link_finalized=false`, and blocks all
budget, conflict-conclusion, Lake, SQLite, connector, and matter-opening
authority.
