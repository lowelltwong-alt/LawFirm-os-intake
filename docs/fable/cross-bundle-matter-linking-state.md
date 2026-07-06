# Cross-Bundle Matter Linking State — Hard Kernel

- Status: Fable design output, candidate-only, synthetic-only. Second pass; builds on `docs/fable/matter-linking-hard-kernel.md` (keys, tiers, rules R1–R14, ambiguity classes).
- Author: Fable 5, 2026-07-05.
- Owner boundaries: **Orchestrator owns persistent cluster state.** Intake owns per-run candidate extraction/clustering and stays write-free beyond its run directory. This doc is simultaneously the candidate design request to `LawFirm-os-orchestrator`.

## 1. Problem

The bundle-local linking kernel is deterministic and replayable, but matters live across many inbound bundles over months. Without memory: (a) a human SPLIT decision made in run N can be silently undone by re-clustering in run N+1; (b) HOLD documents never get resolved by later corroboration; (c) the same ambiguity is re-reviewed forever. With intake-owned memory: the no-Lake/no-SQLite boundary breaks and a candidate repo becomes a shadow system of record. The kernel is the state *contract* between the two.

## 2. Contract overview

```
run N   intake ──emits──► MatterLinkRunExport (candidate, immutable, in run dir)
                Orchestrator ──ingests──► MatterClusterStateStore (append-only ledger)
run N+1 Orchestrator ──provides──► PriorClusterContext (read-only, hashed, versioned)
        intake ──re-derives──► clusters = f(current keys, prior HUMAN decisions)
        wrong links / corrections ──► Exception Lake (events) + DAD (lessons)
```

Three axioms:

1. **State authority follows runtime authority.** Only Orchestrator persists; intake artifacts are per-run and immutable.
2. **Machine clusters are never memorized — only human decisions are.** The store keeps human SPLIT/MERGE/confirmation decisions and the key evidence they were made on; machine cluster proposals are re-derived fresh every run. This kills the ratchet failure where an early bad machine merge becomes permanent by inertia.
3. **Prior context is evidence, not identity.** `PriorClusterContext` enters intake with provenance `orchestrator_context`; human confirmation remains the only identity authority.

## 3. What intake emits per run: `MatterLinkRunExport`

One JSON artifact per run (schema-exported, additive to existing run outputs):

```
MatterLinkRunExport:
  schema_version, export_id, run_id, bundle_id
  key_sets: list[MatterLinkKeySet]                # per document, evidence-bound
  cluster_proposals: list[MatterClusterProposal]  # with ambiguity_class + disposition
  decision_records: list[MatterLinkDecisionRecord]# full replayable rule trace
  human_link_confirmations: list[MatterLinkHumanDecision]   # if a reviewer acted this run
  prior_context_consumed: {context_id, context_hash} | null
  candidate_only: true, matter_identity_asserted: false
```

`MatterLinkHumanDecision` (the ONLY thing eligible for long-term memory):

```
  decision_id, decided_at, reviewer_id
  decision_type: confirm_cluster | split | merge | reopen | retire
  subject_document_ids / subject_cluster_keys      # normalized keys, not run-scoped ids
  evidence_key_refs: list[MatterLinkKey]           # the keys the human saw
  note (observable rationale only)
  supersedes_decision_id: str | null
```

Subjects are expressed in **normalized key space** (claim numbers, docket refs, party-pair hashes), never in run-local document ids, so decisions survive across bundles whose documents differ.

## 4. What Orchestrator stores: `MatterClusterStateStore`

Append-only ledger (implementation free — SQLite/Lake inside Orchestrator's authority is fine; that boundary is Orchestrator's, not intake's):

- `human_decisions`: every `MatterLinkHumanDecision`, keyed by `decision_id`, superseding via `supersedes_decision_id` chains (never update-in-place).
- `confirmed_clusters`: materialized view of currently-active confirmations: `cluster_key` (stable hash of the sorted strong-key set), member key sets, confirming decision ids.
- `split_edges`: pairs of key-set signatures a human declared distinct — the permanent "do not merge" fence (subject to §6 reopen).
- `key_index`: normalized_key → cluster_key for strong/medium keys of confirmed clusters.
- `context_snapshots`: every `PriorClusterContext` issued, with hash, for replay pinning.

Dedupe: ledger entries dedupe on `decision_id`; re-ingesting the same run export is idempotent (export_id recorded; second ingest is a no-op event, not duplicate rows).

## 5. What returns to intake: `PriorClusterContext`

```
PriorClusterContext:
  context_id, context_hash (sha256 of canonical body), issued_at, store_version
  confirmed_clusters: [{cluster_key, strong_keys, medium_keys, last_confirmed_at}]
  split_edges: [{key_signature_a, key_signature_b, decision_id, decided_at}]
  provenance: "orchestrator_context", read_only: true, identity_authority: false
```

Consumption rules inside intake:

- Context is an **input to the pure clustering function**: `clusters = f(current_key_sets, context)`. Determinism and permutation invariance still hold — context is just another argument, hashed into the replay record.
- A `split_edge` acts as rule **R0** (evaluated before R1–R14): documents matching opposite sides of a split edge are SPLIT, regardless of any key agreement, *unless* §6 triggers.
- A match into a `confirmed_cluster`'s strong key promotes the pair to `proposed_link` with ambiguity class computed normally, plus a `prior_confirmation_support` annotation — it never auto-confirms.
- **Stale context blocks:** if `context_hash` fails verification or `store_version` mismatches the run manifest's pin, matter linking emits `blocked_stale_prior_context` and holds everything. Never proceed on unverifiable memory.
- Missing context (first run, or Orchestrator absent) is legal: bundle-local behavior, with `prior_context_consumed: null` recorded.

## 6. Reopening prior decisions

The hard case: run N+1 brings a document that *contradicts* a human decision.

| Trigger | Behavior |
|---|---|
| New document matches strong keys on **both** sides of a split edge | `reopen_requested`: both clusters frozen for growth, human review packet cites the old decision + the new evidence. The old decision is never silently overridden (rule B3 from the base kernel, now with persistence). |
| New strong key contradicts a confirmed cluster (same claim number, disjoint insured set) | `blocked_conflict` referencing the confirmation decision id; human must issue a superseding decision. |
| Human issues `reopen`/`retire` decision | New ledger entry with `supersedes_decision_id`; the fence/confirmation stops applying **from the next issued context**, and the superseded chain remains queryable for audit. |

Invariant: **no machine transition may ever supersede a human decision** — only a newer human decision can. Machine evidence can only *request* reopening.

## 7. Replay, dedupe, audit requirements

- **Replay:** rerunning intake run N with the same bundle + same `PriorClusterContext` snapshot must reproduce identical cluster proposals (ids/timestamps excepted). The context snapshot hash in the run export makes this checkable forever.
- **Permutation:** shuffled document order + same context ⇒ identical clusters (extends the existing permutation holdout).
- **Ledger audit:** Orchestrator must be able to answer, for any cluster_key: which human decisions created it, which run exports contributed evidence, which contexts exposed it. All chains are id-linked; nothing requires text search.
- **Cross-run dedupe of review work:** a HOLD proposal whose supporting key-set signature is identical to a previously issued HOLD (per key_index) is annotated `previously_held (n runs)` rather than opening a fresh review thread — recurrence count, not repetition.

## 8. How DAD learns from wrong links and corrections

Events vs lessons split (per `docs/fable/exception-learning-taxonomy.md`):

- **Exception Lake (events):** every `reopen_requested`, `blocked_conflict`, human `split`-after-machine-`proposed_link` (i.e. a correction), and `blocked_stale_prior_context` becomes an exception candidate with identity_key = (issue_family | rule_id | normalized_subject_keys). Corrections are the gold signal: `human_correction_of_machine_output` with the diff (which rule proposed the link, which key evidence the human weighed).
- **DAD (lessons):** when correction events cluster (occurrence threshold per family), intake drafts ONE lesson: "rule Rx with key-type Y produced n corrected links; candidate rule/tier change Z; shadow-eval plan W" — routed through the outbox with before/after and eval. Rule/tier changes land only as reviewed policy diffs (no silent learning); holdout-origin evidence cannot tune the rules it holds out.

## 9. Codex handoff

1. **PR-ML-X1 (intake, low risk):** `MatterLinkRunExport` + `MatterLinkHumanDecision` models, schema export, emission from the (PR-ML2) clustering stage; `prior_context_consumed` pinning; tests: export determinism, key-space subject encoding.
2. **PR-ML-X2 (intake, medium):** `PriorClusterContext` consumption — R0 split edges, confirmation support annotation, stale-context block; tests: context-as-argument determinism, permutation with context, stale-hash block, reopen freeze (B3 persistent variant).
3. **Orchestrator design request (docs only from intake side):** this file + schema exports constitute the request; Orchestrator implements the ledger and context issuance under its own review. Intake must NOT stub a store, even "temporarily".

**Must not do:** persist anything across runs inside intake; auto-confirm from prior confirmations; let machine evidence supersede human decisions; proceed on unverifiable context; encode decisions against run-local document ids.
