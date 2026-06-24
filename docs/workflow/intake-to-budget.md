# Intake-to-Budget Workflow

## Scope

The workflow begins when a law firm receives incomplete or heterogeneous material and ends when an authorized human has a reviewable intake packet, conflict-search seed, and proposed legal budget.

## Inputs

Examples include:

- carrier assignment email;
- demand letter;
- complaint or summons notice;
- coverage inquiry;
- private help request;
- random correspondence dump;
- party list;
- public docket metadata used only in an approved test environment.

## Classification dimensions

Do not compress all intake meaning into one `case_type` field. Rank and confirm separately:

1. inbound event;
2. matter family;
3. representation posture;
4. relationship roles;
5. stage and urgency;
6. jurisdiction;
7. missing information.

## Detailed flow

### 1. Prove contract state

Validate the local reviewed lock files before reading the source bundle. The starter requires `contracts.lock.json` and `repo_topology.lock.yaml` to be present, parseable, marked `reviewed_seed_lock`, and pinned to immutable SHAs for the five governing LawFirm OS repos with matching authority planes.

The run writes `contract_state_report.json` and fails closed if the contract state is missing, stale, or mismatched.

The run also writes `model_adapter_report.json` for the selected adapter. `structured-model` is currently dry-run only: zero provider calls, zero external tools, no network or external writes, typed JSON-only requirements, prompt hashes, deterministic baseline authority, independent critic, and human gates.

When `--fixture-gold` is supplied, the run writes `fixture_gold_report.json` and fails closed if reviewed synthetic expectations drift. The gold report is local evaluation evidence, not canonical authority.

### 2. Receive and gate

Validate data origin, scope, and source bundle. The starter stops on non-synthetic content.

The run writes `data_scope_gate_report.json` before writing `raw_input.json` or producing derived ingestion artifacts. The report proves `synthetic_only` runtime mode, `synthetic` data origin, no real client data, no real matter data, no privileged data, no public-data direct ingestion, no external writes, and `raw_payload_written=false` at the gate.

If the report is blocked, the run records a blocked `data_origin_gate` ledger event, keeps `raw_input.json` absent, and stops before source inventory, segmentation, candidate extraction, review-form generation, or Exception Lake candidates.

### 3. Inventory

List every source and whether it was read, unread, missing, duplicated, or unreadable. Source coverage is part of the review packet.

### 4. Segment structurally

Preserve email headers, current body, quoted history, signatures, attachment boundaries, letter paragraphs, correspondence-dump message boundaries, headings, tables, pages, and source offsets.

### 5. Extract party and role candidates

Extract names and aliases, but keep role candidates separate. A sender may be a carrier, payer, referral source, or adverse entity. Do not decide the client automatically.

### 6. Rank intake candidates

Return top alternatives for inbound event, matter family, and posture. Show source evidence and profile-prior influence separately.

The run writes `context_boundary_report.json` after packet assembly. The report proves observed source evidence remains first in context precedence, context refs are structured practice-profile refs, context-influenced candidates stay source-anchor-only unless independently observed, unknown options remain available, and human confirmation remains required.

### 7. Identify dates and gaps

Dates, deadlines, and urgency are candidates. The system identifies missing fields but cannot docket or characterize a legally controlling deadline.

The run writes `deadline_docketing_guard_report.json`. The report proves every deadline candidate is source-bound, requires `human_deadline_review`, and has not been docketed. It records `docketing_action_performed=false`, `docketing_action_allowed=false`, no external writes, and the prohibited transition ref for `deadline_gap_candidates_ready->deadline_docketed`.

### 8. Independent critic

The critic checks evidence completeness, contradictions, worker disagreement, source coverage, close party-role alternatives, role ambiguity, and prohibited next steps.

### 9. Evidence completeness report

The run writes `evidence_completeness_report.json` after the preflight packet is assembled. The report proves party candidates, party-role alternatives, inbound-event candidates, matter-family candidates, representation-posture candidates, deadline candidates, missing-information candidates, and critic findings carry source-bound evidence refs that match the packet segment table by source ID, segment ID, offsets, and hash.

It also proves explicit unknown options remain available, deadline candidates still require human verification, human confirmation remains required, and prohibited next steps remain present. This is local evaluation evidence only; it does not promote evidence-ref doctrine into platform canon.

### 10. Escalation gate

Difficult cases may receive a bounded frontier adjudication before human review. The frontier result is still a proposal.

The workflow writes dry-run Exception Lake candidates for source gaps, close party-role alternatives, ambiguity, instruction-risk content, specific prohibited-transition attempts, critic findings, and escalation triggers. It also writes `exception_lake_readiness_report.json` to prove those candidates remain raw-payload-free, dry-run, promotion-required, and evidence- or state-supported before any future Lake handoff. `exception_lake_handoff_manifest.json` then summarizes the actual local labels, broad Lake classes, support modes, candidate files, target runtime owner, and `sqlite_write_performed=false`; it is not an admission log and does not persist to the Lake.

### 11. Human intake confirmation

The reviewer confirms or corrects matter family, posture, principal party roles, jurisdiction, and any date characterization.

The budget workflow records the consumed review outcome as `human_review_outcome.<confirmation_id>.json` and appends it to `human_confirmation_history.jsonl`. Outcomes of `unknown`, `needs_more_information`, `human_only`, `declined`, and `declined_or_referred` stop before budget output. Corrected confirmations use `supersedes_confirmation_id` and append a new history row rather than overwriting the prior outcome.

Confirmed budget runs also write `human_gate_status_report.json`. The report records human intake confirmation as completed while conflicts clearance, engagement authorization, budget review, and matter-opening authorization remain pending gates that block their respective real-world transitions.

### 12. Budget precondition gate

Before budget generation, the system verifies that the human confirmation binds to the exact preflight packet, has `confirmed` status, contains human-confirmed matter family, representation posture, and principal party roles, and carries source-bound evidence refs for both decision evidence and confirmed party roles.

The run writes `budget_precondition_report.json`. If the gate fails, it records a blocked run event and dry-run Exception Lake candidate, then stops before emitting a conflict seed, budget proposal, matter-opening readiness packet, safety report, or review package.

### 13. Conflict-search seed

The system builds normalized search terms grouped by prospective client, instructing source, payer, insured, adverse party, claimant, opposing counsel, aliases, and unresolved roles. Each normalized term must carry source-bound evidence refs from the human confirmation. It makes no conflict conclusion.

### 14. Budget proposal

A confirmed matter type selects an approved practice template. The planner calculates hours, rates if authorized, fees, expenses, and contingency. Assumptions, exclusions, and unknowns remain visible.

The emitted `BudgetProposal` compatibility fields map to the selected `standard` scenario. Its embedded local `BudgetScenarioSet` also carries `early_resolution` and `through_trial` branches with included phases, included UTBMS code candidates, min/max ranges, and monotonic total or hours ordering. Scenario branches are comparison artifacts only and do not authorize submission.

### 15. Human budget review

Future governed step. The starter does not approve or submit.

Confirmed budget runs write `budget_submission_guard_report.json`. The report proves the proposal remains `proposed_for_human_review`, no client or carrier submission occurred, no billing handoff occurred, no external write occurred, and `human_budget_review` remains the required gate before any delivery or billing transition.

### 16. Matter-opening readiness

The system reports satisfied preconditions, blockers, structured blocker details, prohibited actions, and prohibited-action guardrails. Blocker details point to workflow-policy or prohibited-transition structured refs instead of pretending those boundaries are observed source facts.

The starter always remains blocked pending conflicts, engagement, matter-opening authorization, and budget review before submission.

### 17. Safety gate report

The deterministic safety gate verifies that the data-scope gate report, contract-state report, deadline docketing guard, and budget submission guard are carried forward and that the final package contains no conflict clearance, engagement decision, docketed deadline, billing or submission state, external write, matter opening, iManage workspace creation, or client/carrier submission authorization.

It also verifies that normalized conflict-search terms, budget lines, budget support items, proposal-level assumptions, exclusions, unknowns, readiness blockers, and prohibited-action guardrails remain evidence-bound or structured-ref-supported. A failed check blocks final package acceptance.

### 18. Review package completeness report

After the safety gate and review package are written, the workflow emits `review_package_completeness_report.json`. This deterministic report checks that the manifest includes all required local artifacts, those files exist, the markdown package has the expected review sections and boundary text, required human gates, data-scope gate status, human-gate status, evidence-completeness status, context-boundary status, deadline docketing guard status, budget submission guard status, final blockers, and structured blocker details are preserved, Exception Lake readiness remains dry-run and passed, run ledgers are linked, and the package still proves no conflict clearance, engagement decision, matter opening, docketing, billing, external write, or budget submission.

A failed completeness check blocks final package acceptance.

### 19. Run ledger integrity report

Preflight, confirmed budget, and blocked-budget attempts write `run_ledger_integrity_report.json`. This deterministic report proves local ledger events exist, share one run ID, preserve required gate order, stop at the expected terminal step, link existing local outputs, and record no external writes.

The report is local evaluation evidence only. Orchestrator remains the future owner of execution-plane passports, run-ledger policy, and evidence-packet assembly.

## Terminal states

- `human_intake_review_required`
- `needs_more_information`
- `declined_or_referred` (human decision only)
- `budget_proposed_for_human_review`
- `blocked_pending_conflicts_and_engagement`
- `human_only`

There is no autonomous terminal state for conflicts cleared, client accepted, matter opened, iManage created, deadline docketed, or budget submitted.
