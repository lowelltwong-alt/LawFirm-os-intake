# Legal Budget Design

## Purpose

Translate a human-confirmed intake into a transparent, reviewable budget proposal. The proposal supports internal decision-making and later approved client/carrier workflows. It is not an engagement, fee agreement, or submitted budget.

## Preconditions

- intake packet exists;
- human confirmation binds to the exact intake packet;
- human has confirmed matter family and representation posture;
- human confirmation status is `confirmed`;
- human confirmation includes source-bound decision evidence refs;
- principal party roles are confirmed or unresolved roles are explicit;
- confirmed principal party roles include source-bound evidence refs;
- an approved practice template exists;
- rate/guideline source state is known;
- conflicts and engagement remain separate blockers.

The starter persists these runtime checks in `budget_precondition_report.json`. If the gate fails, the run records a blocked ledger event and dry-run Exception Lake candidate, then stops before conflict seed, budget proposal, readiness, safety, or review package output.

The later `safety_gate_report.json` verifies that emitted budget lines and support items still carry source-bound evidence refs or structured refs before the final review package is accepted.

## Labor/Employment fact sufficiency

Labor and employment budgets are especially sensitive to entity relationships and litigation posture. A source packet that merely names a person and a company is not enough to produce a reliable amount. The intake layer must distinguish, at candidate level, employees, former employees, applicants, employers, parent/subsidiary/affiliate entities, joint employers, staffing agencies, PEOs, franchises, unions, agencies, insurers/payers, opposing counsel, supervisors/managers, HR actors, individual defendants, witnesses, and experts.

The local `audit-labor-employment-budget-facts` command reads the synthetic CourtListener-style L&E manifest and `config/labor-employment-budget-fact-needs.yaml`. It emits `labor_employment_budget_fact_audit_report.json` with observed candidate facts, source refs, unknowns, human questions, and critical gaps. Required budget drivers include claims/causes of action, class or collective posture, administrative exhaustion, forum/removal/arbitration posture, employment timeline, damages categories, wage/hour volume, worksites, ESI/custodians, anticipated depositions, experts/vendors, policy or contract documents, and carrier/rate guideline source.

Critical missing or review-only facts set `budget_readiness_state=blocked_missing_critical_facts`. That state is a pricing guard, not a failed audit: it tells the reviewer the current packet should stay at hours-only, broad-range, or no-amount posture until the missing facts are confirmed. The report does not output a budget amount, submit a budget, clear conflicts, open a matter, write Lake/SQLite records, or learn from corrections.

When a human or harness supplies `labor_employment_budget_fact_audit_report.json`
to `build-budget`, the budget precondition gate consumes it explicitly. Critical
L&E gaps set `blocked_state=labor_employment_budget_facts_blocked` and stop
before conflict seed, budget proposal, readiness, safety, or review-package
output. Non-critical needs-review gaps do not rewrite the budget math; they add
supported `unknown` entries and `BudgetSupportItem` refs so human reviewers see
the broad-range or hours-only posture constraint alongside the proposal.

## Form structure

A budget proposal contains:

1. matter and posture summary;
2. template/profile identity and version;
3. phases and tasks;
4. staffing roles;
5. estimated hours;
6. rates, or explicit hours-only state;
7. deterministic fee calculation;
8. expenses;
9. contingency;
10. assumptions;
11. exclusions;
12. unknowns;
13. budget support items with evidence refs or structured refs;
14. source references;
15. scenario set with early, standard, and through-trial branches;
16. carrier-compliant projection when a synthetic guideline artifact is present;
17. human approval state.

The compatibility surface of `BudgetProposal` defaults to the `standard` scenario:
its `lines`, subtotal fields, calculation report, and `total_proposed_budget`
mirror the standard branch unless an observed or human-confirmed `resolution_path`
selects another scenario. The embedded `BudgetScenarioSet` preserves the wider
early, standard, and through-trial comparison with included phases, included UTBMS
code candidates, totals, min/max ranges, optional probabilities, and a labeled
expected total when probabilities are complete. Scenario vocabulary remains local
candidate data until promoted by the owning authority repo.

`BudgetDriverEffect` records show count scaling, bounded intensity multipliers,
coverage boundaries, and unknown drivers with driver value, provenance, structured
policy refs, and the `default_used_as_observed_fact=false` invariant. Profile
defaults may drive synthetic assumptions, but the review surfaces label them as
defaults rather than observed facts. Count-driver ranges widen hour and expense
ranges for unknown/profile-default drivers; human-confirmed counts remain tight.
`BudgetGuidelineFlag` records show synthetic
rate, phase, and total cap checks. A guideline flag can require human review, but it
does not rewrite hours, rates, expenses, or totals.

`CarrierCompliantProjection` is the separate math surface for synthetic carrier
guidelines. It may cap rates and expenses and apply staffing/leverage role
overrides in the projection view, reports proposed vs compliant totals, deltas,
blended-rate change, and role-level leverage summary, and keeps the original
proposal lines unchanged.
It is `projected_for_human_review`, records `rewrites_budget=false`, and carries no
client or carrier submission authority.

`CarrierPreapprovalReport` is the separate review surface for synthetic
preapproval thresholds. It can require `human_carrier_preapproval` for expert
count, expert spend, deposition count, research-hour, or vendor-spend thresholds
and emit dry-run Exception Lake candidates, but it records
`preapproval_obtained=false`, `carrier_submission_authorized=false`, and no
external write.

`NamedTimekeeperRate` is a local candidate model for fake approved individual
rates in the synthetic carrier rate card. It applies only when a candidate budget
task explicitly names a matching synthetic `timekeeper_id`; otherwise the budget
remains role-rate based. Real timekeepers, negotiated rates, private rate stores,
and billing use remain outside this repo.

## Avoiding false precision

- Never infer a negotiated rate.
- Never fabricate client/carrier guidelines.
- Never make a relative deadline a fixed date without a confirmed trigger.
- Use ranges or scenario branches when the number of witnesses, experts, depositions, or trial days is unknown.
- Keep branch totals monotonic (`early_resolution <= standard <= through_trial`) when priced; hours-only budgets prove the same ordering by hours.
- Keep severity, liability, and venue multipliers bounded by cumulative cap policy.
- Treat coverage posture and guideline/cap issues as review boundaries unless separately approved.
- Keep expert/vendor costs distinct from law-firm fees.
- Mark all synthetic numbers.
- Assumptions, exclusions, and unknowns must have source-bound or structured support through `budget_support_items`.
- Unknowns, missing approved templates, and missing authorized rates must emit dry-run Exception Lake candidates for human/pricing review.

## External taxonomies

UTBMS/LEDES codes may be stored as `external_code_candidate` references. They are not canonical LawFirm OS values until the Semantic Substrate adopts a mapping. Client-specific code sets remain private and versioned.

## Carrier form rendering

Template-backed `.xlsx` rendering is validation-first. Before filling an existing UTBMS budget form, the renderer writes or can write `budget_form_mapping_report.json`, which records the template hash, header locations, code-to-row mappings, original-budget write cells, L/E totals, missing or duplicate codes, and original-budget formula checks.

The renderer does not repair workbook formulas. Missing or inconsistent original-budget total, phase subtotal, task remaining, header, or budget-code mapping checks block rendering before a filled workbook is created. The filled workbook remains `proposed_for_human_review` and is not authorized for carrier or client submission.

Template truth can be checked before a matter-specific budget exists with `budget-form-audit`, which writes `budget_form_template_audit_report.json`. The audit uses the same header, UTBMS code, and original-budget formula checks as template-backed rendering, but it records zero budget amounts and does not create a filled workbook.

## Budget refinement loop

Future runtime:

```text
intake-confirmed baseline
-> budget proposal
-> human budget review change record
-> superseding budget proposal or declined/referred budget outcome
-> authorized submission by Orchestrator-owned connector
-> deterministic carrier response reconciliation
-> carrier rejection or partial-allowance remediation case
-> human-approved fix, appeal, no-appeal decision, or write-down
-> appeal result capture and financial outcome
-> phase/code actuals comparison evidence
-> dry-run Exception Lake change or variance candidates
-> reviewed rejection-learning candidate
-> reviewed template-change proposal
-> governed promotion
```

No runtime correction automatically rewrites the template. Human budget changes are
append-only or superseding evidence records: a correction records who changed what,
which proposal/version it supersedes, the target phase/task/code, the previous value,
the new value, the reason, and the reviewed support. Those records can map to
Exception Lake as dry-run `budget_human_change_recorded` candidates, but Lake
admission and storage belong to the Exception Lake runtime.

The local `record-budget-review` command implements the candidate evidence slice
for this loop. It writes a bound `budget_review_change_record.json`, appends the
record to `budget_revision_history.jsonl`, emits `budget_revision_report.json` and
`.md`, calculates phase and UTBMS-code deltas, and writes dry-run revision
Exception Lake candidates. It also writes `budget_change_ledger_report.json`,
`budget_change_ledger.jsonl`, and `budget_change_ledger_report.md` so each human
review decision or field-level edit has reviewer metadata, before/after totals,
evidence refs, structured refs, and a local candidate Lake label. It does not
mutate the original proposal, write a superseding budget, authorize
client/carrier submission, write billing, write SQLite, or admit Lake records.

Carrier rejection handling is a future governed loop, not a starter connector. Every
submitted budget, invoice, appeal, or portal action should have a reconciled response
state. Portal notices, email notices, LEDES response files, returned workbooks, appeal
correspondence, and manual human entries should be captured by Orchestrator-owned
connectors, admitted by the Exception Lake runtime, and classified with source refs.
Rejected or partially allowed amounts should open a human-owned remediation case that
tracks the proposed fix or appeal, human approval, appeal submission, appeal result,
recovered amount, remaining write-down, and any reviewed learning candidate. Intake
may provide candidate schemas, synthetic fixtures, dry-run mappings, and local
decision ledgers only. The local carrier rejection decision ledger records
captured rejection states, pending fix/appeal decisions, appeal results, recovered
amounts, and write-downs as append-only candidate evidence; it does not submit
appeals, write Lake/SQLite records, or mutate learning state. See
`docs/carrier-rejection-learning-loop-roadmap.md`.

## Actuals comparison boundary

Actual cost comparison is phase-level in normal starter runs and phase-plus-code
when governed synthetic actuals include UTBMS-code rows. A comparison report aligns
budgeted fees and expenses by phase and, when available, by code against supplied
actual fees and expenses. It computes variance amount and percent, flags
zero-budget/positive-actual rows as over-threshold, and proposes variance-driver
and learning-disposition candidates for human pricing review.

This repo does not read billing, write billing, or connect to a financial system.
Normal starter runs emit `budget_actual_comparison_report.json` with
`actuals_not_available`, `billing_connector_read_performed=false`, and
`billing_connector_write_performed=false`. The local `compare-budget-actuals`
command may pass synthetic actuals into the deterministic comparison builder,
may filter the comparison surface by an actual resolution scenario, and may
compare against a `budget_revision_report.json` from human review. Future
production actuals should arrive through Orchestrator under a governed billing-read
contract, then any variance candidate should be admitted by the Exception Lake
runtime, not by intake. Variance never silently mutates a profile, template,
carrier guideline, or budget.

The command also writes `budget_actual_variance_ledger_report.json`,
`budget_actual_variance_ledger.jsonl`, and
`budget_actual_variance_ledger_report.md`. The ledger records every phase and
code comparison row, not just over-threshold rows, so later Lake admission can
prove complete comparison coverage. It adds review events for zero-budget
positive-actual rows, missing actuals, and human-revised comparison context while
preserving `billing_connector_read_performed=false`,
`sqlite_write_performed=false`, `lake_write_performed=false`, and
`silent_learning_performed=false`.

The local `review-learning-gate` command aggregates budget revisions, budget
actual variance drivers, and carrier rejection learning proposals into one
candidate gate. It requires human-reviewed outcome evidence, append-only evidence
recording, synthetic fixture updates, shadow evals, and owning-repo review before
any learning candidate can move toward a profile, template, guideline, budget
driver, validation rule, or promoted contract change.

The local `build-budget-event-lake-bundle` command is the run-specific bridge
from append-only intake evidence to future Lake owner review. It can bundle the
budget change ledger, budget actual variance ledger, and carrier rejection
decision ledger into `budget_event_lake_admission_bundle_report.json` and
`budget_event_lake_admission_bundle.md`. The bundle hashes each artifact, checks
report-vs-JSONL row counts, verifies event IDs, requires one budget proposal and
preflight packet across provided ledgers, and blocks if any ledger claims a Lake,
SQLite, billing, submission, mutation, or silent-learning side effect. It does
not create Lake records or record hashes; those remain Exception Lake runtime
responsibilities.

## Sample synthetic defense families

The synthetic insurance-defense profile now demonstrates medical-malpractice defense
and auto-liability bodily-injury defense. Both use the same deterministic budget
engine, driver policy, scenario-set behavior, support-item model, review gates, and
submission boundary while varying only the local candidate template and defaults.

The medical-malpractice template demonstrates:

- intake and early case assessment;
- pleadings and initial motions;
- written/fact/expert discovery;
- dispositive motions and resolution;
- trial preparation and trial.

The auto/BI template demonstrates:

- accident investigation and damages strategy;
- answer and initial pleadings;
- written discovery, medical records, party/witness/treating-provider depositions, and expert discovery;
- trial preparation and trial attendance.

These are test templates, not universal legal budgets.
