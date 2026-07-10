# TRACE 2026-07-10: Owner Adoption Package Audit

## Decision

Treat the static cross-repo promotion package as an auditable candidate artifact,
not as sufficient proof of a routed handoff. Before owner packets are marked
ready, Intake now verifies that every candidate artifact exists locally, every
candidate contract URI names the appropriate owner namespace, proposal IDs are
unique, and the required high-risk contracts are present.

The required high-risk coverage is deliberately narrow and explicit:

- Semantic Substrate: matter-link and entity candidate semantics.
- Orchestrator: persistent cross-bundle matter-link state and carrier-rejection
  workflow ownership.
- Exception Lake: carrier-rejection admission candidates.
- Legal Knowledge Runtime: governed rate-benchmark snapshot candidates.

## Boundary

The audit reads local candidate artifacts only. It does not create GitHub issues,
write a sibling repository, promote a schema/event/route/skill, admit a Lake
record, create SQLite state, or apply learning. Owner issue creation remains a
manual human decision after local review.

## Fail-Closed Behavior

1. A missing or path-traversing candidate artifact ref blocks owner packets.
2. A contract URI using the wrong owner namespace blocks owner packets.
3. Missing persistent-link, carrier-lifecycle, or benchmark-routing proposals
   block owner packets.
4. When blocked, downstream issue drafts remain blocked and cannot be called
   ready for manual owner review.

## Red-Team And Premortem

| Failure mode | Early signal | Containment |
| --- | --- | --- |
| A handoff refers to an artifact that does not exist at review time | broken ref in packet or issue draft | local resolution audit blocks packet generation |
| A candidate URI looks canonical or targets the wrong authority plane | owner-prefix mismatch | namespace audit blocks the package before review |
| A low-risk inventory hides a missing high-risk responsibility | no explicit matter-link, rejection, or benchmark proposal | required coverage check fails closed |
| A local pass is mistaken for adoption | all local packets ready but no owner evidence | packets remain candidate-only and require owner-repo implementation/review |
| Intake opens GitHub issues or mutates siblings as a shortcut | write flags or side-effecting command added | contracts, tests, and docs retain manual/no-write boundaries |

## Deferred Work

This does not implement the Orchestrator ledger, carrier connectors, Lake
admission, public rate retrieval, or canonical schema promotion. Those actions
must happen in their owning repositories after owner review.
