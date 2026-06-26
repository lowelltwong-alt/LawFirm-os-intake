# Cross-Repo Promotion Package

This is a draft promotion package for stable intake components. It is not a direct promotion and does not mutate sibling repo authority.

Machine-readable proposal inventory: `promotion/cross_repo_promotion_package.json`.

The package is candidate-only. It records `no_canonical_mutation=true`,
`no_sibling_repo_writes=true`, and `no_external_writes_performed=true`. Sibling
repo owners must review and promote any accepted contracts inside their own repos.

## Semantic Substrate Candidates

- Intake source bundle, source inventory, and ingestion result contracts.
- Model adapter report contract for deterministic or structured-model dry-run posture, prompt hashes, model/tool budget, tool denylist, typed-output requirement, human gates, critic requirement, deterministic baseline authority, typed-JSON validation, deterministic baseline hash comparison, structured dry-run candidate hash, and reviewed synthetic-gold status.
- Rust transition policy, ingestion volume profile, and Rust ingestion readiness report contracts for future high-volume source inventory, segmentation, hashing, evidence-ref parity checks, compute pressure signals, required benchmark dimensions, hot-path scope, forbidden scope, parity dimensions, and transition gates.
- Evidence ref contract with source ID, segment ID, segment offsets, and segment hash.
- Human confirmation contract, including `confirmed`, `unknown`, `needs_more_information`, `human_only`, and `declined_or_referred` outcomes, decision evidence refs, and confirmed-party evidence refs.
- Human review outcome record contract for append-only confirmation history, superseding corrections, non-confirmed blocked states, and required next gates.
- Human gate status report contract for completed intake confirmation, pending conflicts/engagement/budget/matter-opening gates, artifact refs, workflow refs, blocked transitions, and no authorization effect.
- Deadline docketing guard report contract for source-bound deadline candidates, `human_deadline_review` as the only proposed next gate, no docketing action, no docketing authorization, no external writes, and prohibited-transition structured refs.
- Budget submission guard report contract for review-only budget proposals, pending `human_budget_review`, no client/carrier submission, no billing handoff, no external writes, guarded actions, and workflow/gate/prohibited-transition structured refs.
- Party/role candidate contract with aliases, normalized names, role alternatives, party evidence refs, per-role evidence refs, and candidate status.
- Matter-family, inbound-event, representation-posture, deadline, missing-information, and critic-finding candidate contracts.
- Conflict seed and conflict search term contracts that preserve `no_conflict_conclusion` and require evidence refs for every normalized search term.
- Budget proposal, calculation-report, and budget-support-item contracts.
- Budget scenario set, driver effect, driver profile summary, guideline flag, carrier-compliant projection, budget-form mapping, budget review change, budget revision report, budget actuals source, phase/code actual comparison, variance-driver candidate, and budget exception-mapping contracts.
- Matter-opening readiness contract for final blockers, structured blocker details, prohibited-action guardrails, required human gates, workflow-policy refs, and prohibited-transition refs.
- Evidence graph node and edge conventions for source-backed and structured-ref support across preflight, human review, conflict seed, budget artifacts, readiness blockers, and prohibited-action guardrails.
- Dry-run exception lake candidate contract with broad Lake class, local event label, source-inventory refs, evidence refs, structured refs, blocked state, `raw_payload_included=false`, and `canonical_promotion_required=true`.
- Exception Lake readiness report contract for candidate-file dry-run posture, raw-payload exclusion, promotion requirement, target runtime repo, support pointers, and source/evidence ref integrity.
- Exception Lake handoff manifest contract for local label-to-class summaries, support modes, candidate file refs, paired readiness report, target runtime owner, mapping review, promotion requirement, `sqlite_write_performed=false`, and `external_writes_performed=false`.
- Review package manifest contract tying the human-readable package to preflight, confirmation, conflict seed, budget proposal, readiness, evidence graph, exception candidates, and ledger refs.
- Review package completeness report contract for final artifact refs, review sections, human gates, blockers, safety proof, dry-run Exception Lake readiness, run ledgers, run-ledger integrity reports, and non-authorization flags.
- Run ledger integrity report contract for local gate-order proof, expected terminal state, existing local output refs, blocked-vs-success status, and no external writes.
- Fixture gold spec and report contracts for local synthetic evaluation gates, reviewed expectations, run artifact refs, pass/fail checks, and non-authoritative eval evidence.
- Contract state report contract tying each local run to reviewed lock status, sibling repo SHAs, authority planes, topology agreement, and fail-closed check results.
- Budget precondition report contract tying budget generation to a matching, confirmed, evidence-bound human confirmation and recording failed attempts before proposal output.
- Safety gate report contract for deterministic prohibited-transition and evidence-completeness checks.
- Intake event labels for later review: `intake_preflight_proposed`, `intake_classification_confirmed`, `intake_classification_corrected`, `party_role_corrected`, `practice_context_missing_or_misleading`, `conflict_seed_prepared`, `budget_proposal_created`, `budget_proposal_corrected`, `budget_human_change_recorded`, `budget_actual_cost_variance_requires_review`, and `profile_change_candidate`.

## Orchestrator Interface Draft

- Outer workflow owner: `LawFirm-os-orchestrator`.
- Intake runtime input: source bundle path, practice profile ref, adapter mode, strict-evidence setting.
- Intake runtime outputs: contract state report, data-scope gate report, model adapter report, optional fixture gold report, preflight packet, review form, deadline docketing guard report, evidence graph, run ledger, run ledger integrity report, dry-run exception candidates, exception readiness report, exception handoff manifest, human confirmation, human review outcome record, confirmation history, human gate status report, budget precondition report, conflict seed, case driver profile, budget proposal with optional carrier-compliant projection, budget review form, optional budget revision report, budget submission guard report, optional phase/code budget actual comparison report, Exception Lake mapping package, matter-opening readiness with structured blockers, safety gate report, consolidated review package, review package manifest, review package completeness report.
- Required gates: contract-state gate, model-adapter guard, data-origin gate, prompt/tool authority gate, human intake confirmation, budget precondition gate, prohibited-transition gate.
- Carrier rejection interface draft: Orchestrator owns future portal, email,
  LEDES, returned-workbook, appeal-correspondence, and manual-entry capture
  channels; response-state ledger creation; human rejection review pauses;
  human-authorized appeal submission; and guarded Lake handoff. Intake may
  provide reference commands and candidate artifacts only:
  `capture-carrier-rejections`, `review-carrier-rejections`,
  `propose-carrier-rejection-learning`, and
  `draft-carrier-rejection-orchestrator-interface`.
- Carrier rejection external-write boundary: the only proposed external write is
  Orchestrator-owned appeal submission after
  `human_appeal_submission_authorization` and connector authority checks. Intake
  remains prohibited from production connector capture, carrier portal writes,
  email sends, appeal submission, Lake admission, SQLite writes, profile
  mutation, template mutation, and route/event assignment.

## Exception Lake Mapping Draft

- `retrieval_miss`: missing source, unread source, unreadable attachment, unresolved source ref, incomplete context bundle, source coverage gap.
- `workflow_escalation`: human review required, close candidates, role ambiguity, prompt injection, prohibited transition attempted, budget blocked before confirmation, budget unknowns, unknown budget drivers, guideline/cap review, human budget changes, budget actual variance, missing budget template, hours-only missing rates.
- `authority_conflict_override`: unregistered route/event label, local candidate conflicts with canon, profile attempts to expand authority, missing reviewed lock, topology mismatch, contract SHA drift.
- Intake emits these as local `ExceptionLakeCandidate` rows and a local `ExceptionLakeHandoffManifest` only. The handoff manifest is not a SQLite schema or admission log; it records actual labels, broad Lake classes, support modes, target owner, and no SQLite/external write. The Exception Lake runtime should perform admission validation, append-only storage, record hashing, and correction/supersession handling.
- `ExceptionLakeMappingPackage` is the candidate bridge from local budget labels, human budget changes, budget revision reports, and phase/code actual-variance evidence to broad Lake classes. It is not an admission log.
- Carrier rejection Lake admission proposal: `draft-carrier-rejection-lake-admission`
  names candidate append-only record families for rejection notices,
  reconciliation records, human review outcomes, appeal submissions, appeal
  results, financial outcomes, and learning candidates.
- Carrier rejection admission requirements: every record family requires
  idempotency fields, source/support hashes, a Lake-owned record hash,
  Orchestrator evidence packet input, and correction-by-supersession rather than
  update-in-place.
- Carrier rejection Lake boundary: SQLite tables, migrations, admission
  validation, admitted record hashes, and correction/supersession records belong
  in `LawFirm-os-exceptions-lake-runtime`. Intake performs no SQLite write, Lake
  admission, canonical event assignment, record-hash authority, or raw payload
  storage.

## Skills Registry Draft

- Candidate specialists: source reader, party-role extractor, matter router, deadline/gap extractor, evidence critic, budget planner, frontier adjudicator.
- Required metadata: accepted context types, forbidden context types, evidence requirements, allowed autonomy level, required human gate, data scope, revocation path, trust status, prompt hash.

## Legal Knowledge Runtime Draft

- Intake may request SourceRef, PassageRef, ClaimRef, retrieval trace, and Legal Context Bundle objects.
- Runtime should return refs, offsets, hashes, authority level, source currency, and bundle hash.
- Runtime must not return raw legal payload fanout for Exception Lake storage.

## Promotion Rule

Stable components graduate through the owning sibling repo only. This intake repo pins promoted contracts after sibling review and removes or deprecates local candidate copies.
