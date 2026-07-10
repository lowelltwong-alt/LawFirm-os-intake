# TRACE 2026-07-10: ML-X1 Matter Link Run Export

## Decision

Add a deterministic, immutable `MatterLinkRunExport` candidate artifact for one intake
bundle. It packages source-bound key extraction, local cluster proposals, and the
replayable decision trace for a future `LawFirm-os-orchestrator` owner review.

Intake does not create or consume a cross-bundle store in this slice. Its only output
is JSON and a concise Markdown note inside the requested local run directory.

## Contract And Authority

- `LawFirm-os-intake` owns candidate extraction, bundle-local clustering, synthetic
  fixtures, and this per-run export.
- `LawFirm-os-orchestrator` is the sole future owner of persistent cross-bundle
  matter-link state and of any context it issues back to intake.
- A `MatterLinkHumanDecision` is explicitly expressed as SHA-256 signatures of
  normalized key subjects, never run-local document or cluster IDs. It is the only
  decision shape that could later be considered for Orchestrator persistence.
- This slice does not make a matter-identity assertion, open a matter, produce a
  budget, call a connector, write to the Exception Lake/SQLite, or learn silently.

## Fail-Closed Rules

1. The source key report and cluster report must both be reviewable, reference the
   same bundle, and carry the same source key report ID.
2. Export IDs are derived from immutable source IDs and proposal/decision IDs.
3. Human decision subjects must be hashed normalized-key signatures. A document ID
   is rejected because it cannot survive a later bundle.
4. The run export records persistence as an explicit next gate; it cannot act as a
   substitute for an Orchestrator ledger.

## Red-Team And Premortem

| Failure mode | Early signal | Containment |
| --- | --- | --- |
| Intake becomes a shadow state store | artifacts appear outside a run directory or a state dependency is added | model flags and tests require local-only output and explicit Orchestrator ownership |
| A machine proposal becomes durable identity | export has no human decision contract or identity becomes true | only separately shaped human decisions are persistence-eligible; identity remains false |
| Inputs from different runs are packaged together | report IDs or bundle IDs disagree | builder raises before writing any output |
| A later system applies an old decision to new documents | decision refers to document or cluster IDs | decision subjects are normalized-key hashes, with evidence-key references retained |
| Lake admission is mistaken for completion | output is treated as a Lake event | Lake admission remains a separate owner gate and no Lake write occurs |

## Deferred Follow-On

ML-X2 may consume a read-only, hash-pinned `PriorClusterContext` from Orchestrator.
It must verify the pin, block stale context, preserve permutation invariance, and
allow prior human decisions only as review support or split fences, never as automatic
identity confirmation.
