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

### 2. Receive and gate

Validate data origin, scope, and source bundle. The starter stops on non-synthetic content.

### 3. Inventory

List every source and whether it was read, missing, duplicated, or unreadable. Source coverage is part of the review packet.

### 4. Segment structurally

Preserve email headers, current body, quoted history, signatures, attachment boundaries, letter paragraphs, headings, tables, pages, and source offsets.

### 5. Extract party and role candidates

Extract names and aliases, but keep role candidates separate. A sender may be a carrier, payer, referral source, or adverse entity. Do not decide the client automatically.

### 6. Rank intake candidates

Return top alternatives for inbound event, matter family, and posture. Show source evidence and profile-prior influence separately.

### 7. Identify dates and gaps

Dates, deadlines, and urgency are candidates. The system identifies missing fields but cannot docket or characterize a legally controlling deadline.

### 8. Independent critic

The critic checks evidence completeness, contradictions, worker disagreement, source coverage, role ambiguity, and prohibited next steps.

### 9. Escalation gate

Difficult cases may receive a bounded frontier adjudication before human review. The frontier result is still a proposal.

### 10. Human intake confirmation

The reviewer confirms or corrects matter family, posture, principal party roles, jurisdiction, and any date characterization.

### 11. Budget precondition gate

Before budget generation, the system verifies that the human confirmation binds to the exact preflight packet, has `confirmed` status, contains human-confirmed matter family, representation posture, and principal party roles, and carries source-bound evidence refs for both decision evidence and confirmed party roles.

The run writes `budget_precondition_report.json`. If the gate fails, it records a blocked run event and dry-run Exception Lake candidate, then stops before emitting a conflict seed, budget proposal, matter-opening readiness packet, safety report, or review package.

### 12. Conflict-search seed

The system builds normalized search terms grouped by prospective client, instructing source, payer, adverse party, opposing counsel, aliases, and unresolved roles. It makes no conflict conclusion.

### 13. Budget proposal

A confirmed matter type selects an approved practice template. The planner calculates hours, rates if authorized, fees, expenses, and contingency. Assumptions, exclusions, and unknowns remain visible.

### 14. Human budget review

Future governed step. The starter does not approve or submit.

### 15. Matter-opening readiness

The system reports satisfied preconditions and blockers. The starter always remains blocked pending conflicts, engagement, and matter-opening authorization.

### 16. Safety gate report

The deterministic safety gate verifies that the contract-state report is carried forward and that the final package contains no conflict clearance, engagement decision, docketed deadline, billing or submission state, external write, matter opening, iManage workspace creation, or client/carrier submission authorization. A failed check blocks final package acceptance.

## Terminal states

- `human_intake_review_required`
- `needs_more_information`
- `declined_or_referred` (human decision only)
- `budget_proposed_for_human_review`
- `blocked_pending_conflicts_and_engagement`
- `human_only`

There is no autonomous terminal state for conflicts cleared, client accepted, matter opened, iManage created, deadline docketed, or budget submitted.
