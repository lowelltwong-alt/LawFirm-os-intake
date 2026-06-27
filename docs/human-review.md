# Human Review Design

## Intake review must not be a rubber stamp

The reviewer should see:

- source coverage and unread sources;
- top alternatives, not only the winner;
- exact observed evidence;
- source anchors when an alternative is context-only or the explicit unknown option;
- practice-context influence;
- unknown option;
- party-role alternatives with their own evidence refs;
- contradictions and missing information;
- deadline candidates;
- escalation reason;
- prohibited next steps.

The reviewer can confirm, correct, select unknown, request more information, or route to human-only handling.

## Required intake decisions

- inbound event;
- matter family;
- representation posture;
- prospective represented client(s);
- instructing source and payer;
- insured(s);
- adverse party/claimant;
- jurisdiction if known;
- treatment of date/deadline candidates.

## Conflict review

The workflow prepares search terms and unresolved relationships. A conflicts professional or authorized lawyer performs the conflict process under firm policy.

## Budget review

The reviewer must verify template fit, staffing, hours, rates, guidelines, expenses, contingency, assumptions, exclusions, unknowns, and required approval authority.

Budget changes by a human reviewer must be append-only or superseding. A change
record captures reviewer identity, timestamp, proposal/version being changed,
target phase/task/code or assumption, previous value, new value, reason, evidence or
structured support refs, and whether it supersedes a prior budget review record.
The original proposal remains inspectable. The local `record-budget-review` command
writes `budget_review_change_record.json`, appends to
`budget_revision_history.jsonl`, writes `budget_revision_report.json` and `.md`,
calculates candidate phase/code deltas, and emits dry-run
`budget_human_change_recorded` evidence. It does not admit records to the Lake,
write SQLite, submit budgets, or mutate budget history silently.

## Decision evidence

A review record should contain reviewer identity, role, timestamp, packet ID, decisions, corrections, evidence reviewed, missing sources, and notes. Confirmed party roles carry source-bound evidence refs, and the confirmation as a whole carries decision evidence refs for the matter/posture decisions reviewed. Corrections are appended or superseding records; do not silently overwrite history.

Candidate lines must distinguish direct evidence from packet anchors. `observed_support` candidates render as evidence; `source_anchor_only` and `unknown_option` candidates render as source anchors so reviewers do not mistake practice-context priors or the unknown option for observed source facts.

The starter budget path writes `human_review_outcome.<confirmation_id>.json` and appends the same record to `human_confirmation_history.jsonl` before the budget precondition gate runs. The record preserves reviewer identity, status, supersession ID, evidence refs, required next gate, and whether budget-stage output is allowed. Only a `confirmed` outcome bound to the same preflight packet may be marked budget-stage eligible; every other review outcome remains blocked and inspectable.

The budget lifecycle path writes `budget_human_review_packet.json` so reviewers
can see budget revision, actual-variance, carrier-rejection, appeal-result,
Lake-handoff, and learning-loop pressure in one place. The packet must show
recommendations, why-notes, red-team notes, decision templates, and financial
summary without approving budget submission, appeal submission, Lake admission,
billing writes, profile/template/budget/guideline mutation, or learning.

The preflight path writes `evidence_completeness_report.json` so reviewers and future Orchestrator handoff can see that candidate evidence refs, unknown options, deadline review-only posture, and prohibited next steps were checked before the package was accepted. The report is local proof only, not platform canon.

## PR close-out review

Before a draft PR is moved forward, `build-pr-review-checklist` should consume
the final readiness audit and produce a reviewer checklist. Each item includes a
recommendation, why-note, artifact refs, red-team note, and required human
decision where applicable. A blocked readiness audit becomes a blocking checklist
item. A ready checklist remains human-review evidence only; it does not mark a
PR ready, call GitHub write APIs, promote canon, admit Lake records, write
SQLite, apply learning, or authorize production use.

After the local closeout report exists, `record-pr-readiness-decision` records
the human PR decision append-only. The allowed decisions are keep draft, needs
more work, split follow-up work, or mark ready for review. A mark-ready decision
only records that a separate manual GitHub action is required; it does not mark
the PR ready, create issues or PRs, write sibling repos, promote canon, admit
Lake/SQLite records, apply proposed changes, or apply learning.
