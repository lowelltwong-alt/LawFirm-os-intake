# Carrier Rejection Capture And Learning Loop Roadmap

## Goal

Capture 100% of future carrier budget and invoice rejections deterministically,
route them to the Exception Lake with source-bound evidence, drive a human-owned
fix or appeal workflow, capture the appeal result, and turn reviewed outcomes into
candidate guideline improvements.

The invariant is not "the classifier saw every rejection." The invariant is
"every submitted budget, invoice, appeal, or portal action has a reconciled response
state." Classification improves routing, but deterministic reconciliation proves
capture completeness.

## Authority Boundary

This repo may define candidate contracts, synthetic fixtures, dry-run mappings, and
evals for rejection capture. It must not own production email, carrier portal, billing,
or appeal-submission connectors.

Future production capture belongs to `LawFirm-os-orchestrator`; append-only storage,
admission validation, SQLite tables if any, correction/supersession, and record hashes
belong to `LawFirm-os-exceptions-lake-runtime`.

Intake may emit local dry-run evidence packets and synthetic fixtures only. It must not
commit real carrier portal payloads, real client data, real matter data, privileged
content, negotiated rates, or real guideline text.

## Capture Sources

Expected future channels:

- carrier portal notices and export files;
- email rejection notices;
- LEDES/e-billing rejection files or response reports;
- carrier budget-form comments or returned workbooks;
- appeal correspondence;
- manual human entry for phone-only or portal-only outcomes.

Every captured source should preserve:

- source channel and connector owner;
- received timestamp and carrier timestamp;
- carrier, matter, claim, invoice, budget, appeal, and submission identifiers;
- raw source hash;
- permitted excerpt refs, not raw privileged payload fanout;
- attachment inventory and hashes;
- parser version;
- idempotency key;
- reconciliation state.

## Deterministic Completeness

Use a reconciliation ledger keyed by submitted artifacts:

```text
submitted_budget_or_invoice
-> expected carrier response state opened
-> portal/email/LEDES/manual notice matched by deterministic identifiers
-> unmatched notices create investigation exceptions
-> missing expected responses create follow-up exceptions after SLA
-> final state requires accepted, rejected, partially accepted, appealed, withdrawn, or stale/no-response
```

Completeness checks:

- every submitted artifact has exactly one current response state;
- every rejection notice links to a known submission or becomes an unlinked-source exception;
- duplicate notices collapse by idempotency key but remain audit-visible;
- parser failures create exceptions rather than disappearing;
- stale expected responses trigger follow-up before the carrier deadline expires;
- manual overrides append/supersede; they never overwrite the prior record.

## Candidate Rejection Classes

Initial local labels should map to broad Lake classes until Semantic Substrate promotes
canonical event classes:

| Local label | Meaning | Initial Lake mapping |
|---|---|---|
| `carrier_rejection_notice_received` | A rejection or partial rejection was captured and linked | `workflow_escalation` |
| `carrier_rejection_unlinked` | Rejection notice could not be linked to a known submission | `retrieval_miss` |
| `carrier_rejection_parse_failed` | Source was captured but deterministic extraction failed | `workflow_escalation` |
| `carrier_rejection_duplicate_notice` | Duplicate carrier notice detected by idempotency key | `workflow_escalation` |
| `carrier_response_missing_after_sla` | Expected response not received inside configured window | `workflow_escalation` |
| `carrier_rate_reduction` | Carrier reduced hourly rate, title rate, or named timekeeper rate | `workflow_escalation` |
| `carrier_expense_disallowed` | Expense was rejected, capped, or reclassified | `workflow_escalation` |
| `carrier_preapproval_missing` | Carrier rejected due to absent preapproval | `workflow_escalation` |
| `carrier_staffing_or_leverage_rejection` | Rejection based on role, timekeeper count, or staffing mix | `workflow_escalation` |
| `carrier_narrative_deficiency` | Vague, block-billed, clerical, or guideline-deficient narrative | `workflow_escalation` |
| `carrier_code_mapping_rejection` | UTBMS/LEDES/task/expense code mismatch or missing code | `workflow_escalation` |
| `carrier_budget_phase_variance_rejection` | Rejection tied to phase/task budget overrun | `workflow_escalation` |
| `carrier_portal_submission_failure` | Portal/transport failure distinct from substantive rejection | `workflow_escalation` |
| `carrier_guideline_version_drift` | Rejection indicates local guideline profile is stale | `authority_conflict_override` |
| `carrier_appeal_submitted` | Human-approved appeal was sent by an authorized workflow | `workflow_escalation` |
| `carrier_appeal_result_received` | Appeal accepted, denied, partially accepted, or stale | `workflow_escalation` |

These labels are candidate evidence labels only. Canonical event classes, route IDs,
and Lake admission schemas must be promoted by the owning repos.

## Follow-Up And Appeal Workflow

Each captured rejection should open a `CarrierRejectionRemediationCase` candidate:

```text
captured
-> classified
-> linked to budget/invoice/projection/guideline version
-> assigned human owner
-> proposed fix or appeal reason
-> human approves appeal, accepts write-down, requests more info, or marks no appeal
-> authorized Orchestrator connector submits appeal or corrected artifact
-> appeal result captured
-> financial outcome recorded
-> learning candidate created
-> closed
```

Required fields:

- rejection ID and source refs;
- linked submission ID, budget proposal ID, invoice ID, phase/task/code, and line IDs;
- carrier guideline version and local guideline candidate version;
- rejection class and confidence plus deterministic rule evidence;
- disputed amount, accepted amount, appealed amount, recovered amount, and remaining write-down;
- appeal deadline candidate and source refs;
- human owner, decision, timestamp, and reason;
- appeal packet refs;
- appeal result state: `accepted`, `denied`, `partially_accepted`, `withdrawn`, `no_response`, or `stale`;
- supersession refs for corrected classifications or outcomes.

## Learning Loops

Learning is allowed only as reviewed candidate evidence. No silent mutation.

Feedback loops:

- guideline drift loop: repeated rejections propose updates to synthetic/private guideline candidates;
- budget model loop: recurring phase variance updates candidate budget drivers and ranges;
- template loop: code-mapping rejections propose UTBMS/workbook mapping fixes;
- narrative loop: repeated narrative deficiencies propose time-entry review rules;
- preapproval loop: threshold rejections propose earlier preapproval gates;
- appeal-success loop: successful appeals preserve the proposed budget position as defensible;
- appeal-failure loop: failed appeals propose tighter compliant projections or human warnings.

Each learning proposal should include:

- supporting rejection events;
- affected carrier/profile/matter family;
- before/after expected behavior;
- synthetic fixture update;
- shadow-eval result;
- human reviewer;
- target owning repo for promotion;
- explicit `silent_learning_performed=false`.

The current local candidate harness for this gate is `run-learning-shadow-eval`;
`build-learning-owner-handoffs` then packages passed, failed, and blocked
candidates by target owner. Passing results still require human review and
owning-repo promotion review.

## Metrics

Track these as deterministic reports:

- capture completeness: expected responses vs reconciled responses;
- unmatched rejection count;
- parser failure count;
- missing-response SLA count;
- rejection rate by carrier, matter family, phase, task, code, and guideline version;
- appealed amount, recovered amount, appeal win rate, partial-win rate, and cycle time;
- repeat rejection rate after a guideline or template fix;
- guideline drift candidates opened and accepted;
- false-positive and false-negative findings from human review.

The target for capture completeness is 100%. Classification precision can improve over
time, but missing capture is a production incident.

## PR-Sized Slices

1. Candidate schema and synthetic fixture for `CarrierRejectionNotice`,
   `CarrierRejectionRemediationCase`, and `CarrierAppealResult`.
   Status: implemented for the synthetic local slice through
   `capture-carrier-rejections`.
2. Dry-run Exception Lake mapping package for carrier rejection and appeal labels.
   Status: implemented for broad-class local mapping; canonical route/event
   promotion remains out of scope for this repo.
3. Deterministic reconciliation report for expected vs captured carrier responses.
   Status: implemented for the synthetic local slice through
   `carrier_rejection_reconciliation_report.json`,
   `carrier_rejection_decision_ledger_report.json`,
   `carrier_rejection_decision_ledger.jsonl`, and
   `carrier_rejection_decision_ledger_report.md`. The ledger records rejection
   states, duplicate collapse, pending fix/appeal decisions, appeal results, and
   financial outcomes as candidate evidence only.
4. Synthetic portal/email/LEDES rejection fixtures with duplicate, unlinked, malformed,
   partial-allowance, and appeal-result cases.
   Status: implemented for the current fixture family; more carrier/matter
   counterfactual fixtures remain useful.
5. Human review packet for rejection triage and appeal decision.
   Status: implemented for the synthetic local slice through
   `review-carrier-rejections`, `carrier_rejection_review_packet.json`,
   `carrier_rejection_review_notes.md`, and
   `carrier_rejection_review_decision_template.json`.
6. Learning-candidate report that proposes guideline, budget-driver, template, or
   narrative-rule updates without mutating profiles.
   Status: implemented for the synthetic local slice through
   `propose-carrier-rejection-learning`,
   `carrier_rejection_learning_report.json`, and
   `carrier_rejection_learning_report.md`. Proposals remain blocked until
   human-reviewed outcome evidence exists and perform no silent mutation.
7. Orchestrator interface draft for future connector-owned portal/email capture and
   appeal submission.
   Status: implemented for the synthetic local slice through
   `draft-carrier-rejection-orchestrator-interface`,
   `carrier_rejection_orchestrator_interface.json`, and
   `carrier_rejection_orchestrator_interface.md`. The draft names connector
   channels, response-state ledger duties, human pauses, appeal-submission gates,
   and guarded Lake handoff while implementing no connectors or external writes.
8. Exception Lake admission proposal for append-only rejection, appeal, outcome, and
   learning-candidate records.
   Status: implemented for the synthetic local slice through
   `draft-carrier-rejection-lake-admission`,
   `carrier_rejection_lake_admission_proposal.json`, and
   `carrier_rejection_lake_admission_proposal.md`. The proposal names append-only
   record families, idempotency fields, hash requirements, Orchestrator evidence
   packet prerequisites, and supersession rules while performing no SQLite write
   or Lake admission.

Local completion audit:

- `audit-carrier-rejection-roadmap` writes
  `carrier_rejection_roadmap_audit_report.json` and
  `carrier_rejection_roadmap_audit_report.md`.
- The audit checks local proof artifacts and command refs for slices 1-8, fails
  closed when required artifacts are missing, and records remaining external
  adoption actions for Orchestrator, Exception Lake, and Semantic Substrate.
- The audit is candidate-only. It does not implement production connectors,
  submit appeals, write SQLite, admit Lake records, write sibling repos, perform
  external writes, or mutate platform canon.

## Non-Goals

- No direct portal or email connectors in intake.
- No direct appeal submission from intake.
- No raw carrier portal payload storage in intake.
- No real matter, client, privileged, or negotiated-rate data in committed fixtures.
- No automatic write-down, appeal, budget approval, client notification, or carrier
  submission.
- No model-only classification gate; deterministic reconciliation is the capture proof.
