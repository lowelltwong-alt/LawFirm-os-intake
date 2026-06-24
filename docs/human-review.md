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

## Decision evidence

A review record should contain reviewer identity, role, timestamp, packet ID, decisions, corrections, evidence reviewed, missing sources, and notes. Confirmed party roles carry source-bound evidence refs, and the confirmation as a whole carries decision evidence refs for the matter/posture decisions reviewed. Corrections are appended or superseding records; do not silently overwrite history.

Candidate lines must distinguish direct evidence from packet anchors. `observed_support` candidates render as evidence; `source_anchor_only` and `unknown_option` candidates render as source anchors so reviewers do not mistake practice-context priors or the unknown option for observed source facts.

The starter budget path writes `human_review_outcome.<confirmation_id>.json` and appends the same record to `human_confirmation_history.jsonl` before the budget precondition gate runs. The record preserves reviewer identity, status, supersession ID, evidence refs, required next gate, and whether budget-stage output is allowed. Only a `confirmed` outcome bound to the same preflight packet may be marked budget-stage eligible; every other review outcome remains blocked and inspectable.
