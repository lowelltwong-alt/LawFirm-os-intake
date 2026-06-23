# Definition of Done

## Starter release

The starter is complete when all of the following are true:

1. The repository unpacks directly into `LawFirm-os-intake` without a nested duplicate root.
2. A new builder can identify the repo role, authority order, first command, and prohibited actions from the root files.
3. The package installs on Python 3.11+.
4. `python -m pytest` passes.
5. `bash scripts/smoke_demo.sh` completes locally.
6. The demo emits a source inventory, segments, effective context, preflight packet, human confirmation, conflict-search seed, legal budget proposal, matter-opening readiness packet, evidence graph, and run ledger.
7. Every observed candidate has a source-bound evidence reference with source ID, segment ID, offsets, and hash.
8. Practice context changes rankings without changing observed source evidence.
9. The carrier is not automatically labeled as the represented client.
10. Matter family, posture, and principal party roles require human confirmation.
11. Budget generation is blocked before confirmation.
12. Missing rates produce an hours-only proposal.
13. All monetary calculations are deterministic.
14. The budget is marked `proposed_for_human_review` and `not_authorized_for_client_submission`.
15. The terminal readiness state remains blocked pending conflicts and engagement.
16. No production connector, network call, external write, or live-model dependency exists.
17. Public data is cataloged but not directly ingested.
18. Local schemas are clearly candidate/reference schemas, not promoted canon.
19. Any future non-Python ingestion implementation has a documented parity boundary and cannot bypass source/ref/hash/offset validation.

## Safety invariants

The following must remain zero:

- unauthorized writes;
- real client/matter/privileged inputs;
- cross-matter access;
- automatic conflict conclusions;
- automatic represented-client conclusions;
- automatic engagement decisions;
- automatic deadline docketing;
- automatic budget submission;
- automatic matter/iManage creation;
- silent profile mutation;
- evidence-free material classifications;
- unregistered workers or dynamic agent creation.

## Future graduation metrics

Before production pilot, define and meet attorney-reviewed thresholds for:

- party/entity extraction precision and recall;
- top-three matter-family recall;
- principal-role correction rate;
- evidence completeness;
- reviewer touch time;
- high-confidence error rate;
- abstention appropriateness;
- deadline candidate recall with zero autonomous docketing;
- budget calculation accuracy;
- assumption/exclusion completeness;
- escalation recall for high-risk ambiguity;
- prompt-injection resistance;
- cross-profile counterfactual integrity.

No metric may trade away a safety invariant.
