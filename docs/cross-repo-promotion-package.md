# Cross-Repo Promotion Package

This is a draft promotion package for stable intake components. It is not a direct promotion and does not mutate sibling repo authority.

## Semantic Substrate Candidates

- Intake source bundle and source inventory contracts.
- Evidence ref contract with source ID, segment ID, segment offsets, and segment hash.
- Human confirmation contract, including `confirmed`, `unknown`, `needs_more_information`, `human_only`, and `declined_or_referred` outcomes.
- Party/role candidate contract with aliases, normalized names, role alternatives, evidence refs, and candidate status.
- Matter-family, inbound-event, representation-posture, deadline, missing-information, and critic-finding candidate contracts.
- Budget proposal, calculation-report, and budget-support-item contracts.
- Dry-run exception lake candidate contract with broad Lake class, local event label, source-inventory refs, evidence refs, blocked state, `raw_payload_included=false`, and `canonical_promotion_required=true`.
- Review package manifest contract tying the human-readable package to preflight, confirmation, conflict seed, budget proposal, readiness, evidence graph, exception candidates, and ledger refs.
- Contract state report contract tying each local run to reviewed lock status, sibling repo SHAs, authority planes, topology agreement, and fail-closed check results.
- Safety gate report contract for deterministic prohibited-transition checks.
- Intake event labels for later review: `intake_preflight_proposed`, `intake_classification_confirmed`, `intake_classification_corrected`, `party_role_corrected`, `practice_context_missing_or_misleading`, `conflict_seed_prepared`, `budget_proposal_created`, `budget_proposal_corrected`, and `profile_change_candidate`.

## Orchestrator Interface Draft

- Outer workflow owner: `LawFirm-os-orchestrator`.
- Intake runtime input: source bundle path, practice profile ref, adapter mode, strict-evidence setting.
- Intake runtime outputs: contract state report, preflight packet, review form, evidence graph, run ledger, dry-run exception candidates, human confirmation, conflict seed, budget proposal, budget review form, matter-opening readiness, safety gate report, consolidated review package, review package manifest.
- Required gates: contract-state gate, data-origin gate, prompt/tool authority gate, human intake confirmation, budget precondition gate, prohibited-transition gate.

## Exception Lake Mapping Draft

- `retrieval_miss`: missing source, unreadable attachment, unresolved source ref, incomplete context bundle, source coverage gap.
- `workflow_escalation`: human review required, close candidates, role ambiguity, prompt injection, prohibited transition attempted, budget blocked before confirmation.
- `authority_conflict_override`: unregistered route/event label, local candidate conflicts with canon, profile attempts to expand authority, missing reviewed lock, topology mismatch, contract SHA drift.
- Intake emits these as local `ExceptionLakeCandidate` rows only. The Exception Lake runtime should perform admission validation, append-only storage, record hashing, and correction/supersession handling.

## Skills Registry Draft

- Candidate specialists: source reader, party-role extractor, matter router, deadline/gap extractor, evidence critic, budget planner, frontier adjudicator.
- Required metadata: accepted context types, forbidden context types, evidence requirements, allowed autonomy level, required human gate, data scope, revocation path, trust status, prompt hash.

## Legal Knowledge Runtime Draft

- Intake may request SourceRef, PassageRef, ClaimRef, retrieval trace, and Legal Context Bundle objects.
- Runtime should return refs, offsets, hashes, authority level, source currency, and bundle hash.
- Runtime must not return raw legal payload fanout for Exception Lake storage.

## Promotion Rule

Stable components graduate through the owning sibling repo only. This intake repo pins promoted contracts after sibling review and removes or deprecates local candidate copies.
