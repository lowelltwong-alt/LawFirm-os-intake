# Evaluation Plan

## Evaluation object

Evaluate the complete harness—context resolver, segmenter, workers, validators, escalation, human packet, and packet writer—not the base model in isolation.

## Evaluation layers

### Contract tests

Schemas, required fields, enum/candidate status, source references, profile hashes, and prohibited transitions.

### Deterministic unit tests

Segmentation, hashing, context precedence, calculations, state transitions, and gates.

### Worker task evals

- party/entity precision and recall;
- role-candidate recall;
- top-three matter-family recall;
- deadline candidate recall;
- missing-information coverage;
- evidence-reference validity;
- abstention quality.

### End-state workflow evals

Grade emitted packets and terminal state rather than requiring an exact internal trajectory.

The CLI supports `--fixture-gold` for reviewed synthetic gold. It writes `fixture_gold_report.json` and fails closed on drift in expected source coverage, top-three matter recall, role candidates, deadline candidates, missing information, dry-run exception labels, conflict/budget boundaries, safety status, final blockers, or external-write boundaries.

The smoke harness also runs `scripts/audit_starter_release.py` after the north-star demo. It writes `starter_release_audit_report.json`, a local non-authoritative artifact-level audit over the generated demo outputs. The audit checks required artifacts, synthetic-only scope, source-bound refs, human gates, carrier/client separation, conflict-seed boundary, budget boundary, Exception Lake dry-run posture, terminal safety boundary, fixture-gold status, run ledgers, noncanonical candidate registries, and Rust-readiness posture.

The smoke harness also runs `scripts/audit_blocked_budget_attempt.py`. It writes `blocked_budget_attempt_audit_report.json`, a local non-authoritative fail-closed audit proving a synthetic `needs_more_information` human-review outcome stops before conflict seed, budget proposal, readiness packet, safety gate, or final package output while preserving the blocked precondition report, review outcome/history, dry-run exception candidate, readiness report, and run ledger.

The smoke harness also runs `scripts/audit_context_counterfactual.py`. It writes `context_counterfactual_audit_report.json`, a local non-authoritative same-source/different-profile audit proving source inventory, segment signatures, and observed evidence refs stay stable while practice context may change candidate ranking. It also checks that context-only matter candidates are graph anchors, not observed support facts.

Before any budget learning candidate moves into replay or shadow eval,
`audit-budget-calibration-corpus` can write
`budget_calibration_corpus_report.json`. The report classifies which budget
review, actuals, carrier rejection, reviewed-gold, learning-gate, and
shadow-eval fixtures are eligible for synthetic calibration review and which
are only supporting context. It blocks real/production/privileged flags,
mutation flags, Lake/SQLite writes, external writes, and silent-learning flags.
It does not calibrate or apply changes.

`plan-budget-corpus-replay` consumes that audit report and writes
`budget_corpus_replay_plan.json`. The plan binds each eligible synthetic
artifact to the deterministic local command chain needed to regenerate its
baseline budget evidence and route review, actuals, rejection, appeal/result,
or shadow-eval pressure through the existing human gates. Supporting context
fixtures are not executed, and blocked corpus reports produce no command
chains. The command is planning-only: it does not run replay commands, mutate
profiles/templates/guidelines, write Lake or SQLite records, or apply learning.

`replay-budget-corpus` consumes the replay plan and writes
`budget_corpus_replay_execution_report.json`. Dry-run mode is the default and
records planned command readiness without executing. With `--execute` and
optional `--case-id`, it can run selected synthetic command chains locally and
verify expected output artifacts. Missing placeholders, missing inputs,
unsupported commands, failed commands, and missing expected outputs fail closed.
Learning-support artifacts remain supporting context unless an upstream reviewed
chain produces the needed input. The report remains non-authoritative and does
not calibrate, mutate budgets/profiles/templates/guidelines, write Lake or
SQLite records, submit budgets, open matters, or apply learning.

`review-budget-corpus-replay` consumes the replay execution report and writes a
human-facing review packet plus decision templates. The packet separates
executed-passed cases, dry-run-only cases, failed/blocked cases, selected-but-not
run cases, and supporting context. It records recommendations, red-team notes,
required human decisions, and append-only review outcome requirements. It still
does not approve fixture binding, apply learning, mutate
budgets/profiles/templates/guidelines, write Lake or SQLite records, submit
budgets, open matters, or authorize external action.

`record-budget-corpus-replay-review-outcome` records a reviewer decision as
append-only local evidence. It validates the outcome against the review packet
decision template, writes a single outcome record, appends that record to
`budget_corpus_replay_review_outcome_history.jsonl`, and writes an outcome
report. Mismatched packet IDs, unknown cases, disallowed outcomes, and unbound
approved output refs fail closed. Even an approved fixture-binding outcome does
not apply learning, mutate source fixtures, write Lake/SQLite records, submit
budgets, open matters, or authorize external action.

`propose-budget-fixture-bindings` consumes the replay review packet and replay
review outcome report, then writes a candidate fixture-binding report plus JSONL
candidate rows. It emits a ready candidate only when the append-only outcome is
`approve_fixture_binding` and approved output refs are present. Rejected,
repair, hold, or malformed approval states stay blocked. The report does not
change fixture files, apply learning, mutate profiles/templates/guidelines,
write Lake/SQLite records, submit budgets, open matters, or authorize external
action.

`build-budget-fixture-binding-handoff` consumes the fixture-binding candidate
report and writes a human fixture-update handoff report plus JSONL handoff
items. It must preserve ready-vs-blocked candidate state, include why-notes,
recommended owner actions, red-team objections, and required next gates, and
prove that no fixture update, fixture-binding application, PR creation, Lake or
SQLite write, calibration, or silent learning occurred.

`audit-budget-calibration-readiness` consumes the corpus, replay plan,
execution, review packet, review outcome, fixture-binding candidate, and
fixture-binding handoff reports. It must prove ID continuity across the chain,
ready status for manual fixture-update review, approved output refs, proposed
target fixture refs, required next gates, and no fixture mutation, no PR
creation, no calibration application, no Lake/SQLite write, no external write,
and no silent learning. Any rejected outcome, blocked handoff, missing approved
output, or chain mismatch must produce a blocked report.

`record-budget-fixture-update-review` consumes the calibration readiness report
and an explicit fixture-update review decision JSON. It must bind accepted output
refs and target fixture refs to the readiness report, append a local review
history row, distinguish accepted-for-separate-PR from rejected or
needs-more-information decisions, and prove that no fixture update, PR creation,
calibration, Lake/SQLite write, external write, or silent learning occurred.

`build-budget-fixture-update-pr-package` consumes the fixture-update review
report. It must create manual PR package items only for accepted fixture-update
decisions, record no-package-needed status for rejected or needs-more-information
decisions, block on failed review evidence, and prove that no fixture edit,
GitHub PR creation, calibration, Lake/SQLite write, external write, or silent
learning occurred.

`record-budget-review` also writes `budget_change_ledger_report.json`,
`budget_change_ledger.jsonl`, and `budget_change_ledger_report.md`. Corrected
review outcomes must produce one ledger row per human change; no-change or
blocked outcomes must produce an outcome-only row. Each row preserves reviewer
metadata, before/after totals, evidence refs, structured refs, and local
candidate Lake labels while proving no source budget mutation, no superseding
budget write, no Lake/SQLite admission, no billing connector write, and no
silent learning.

`compare-budget-actuals` also writes
`budget_actual_variance_ledger_report.json`,
`budget_actual_variance_ledger.jsonl`, and
`budget_actual_variance_ledger_report.md`. The ledger must preserve one
append-only candidate row for every phase and code comparison, plus context rows
for human-revised comparison budgets. Missing actuals and zero-budget/positive
actuals must become reviewable events. The ledger proves no billing connector
read or write, no Lake/SQLite admission, no budget mutation, and no silent
learning.

`build-budget-actual-variance-owner-adoption` consumes the actual comparison
report and variance ledger report. It writes an owner-adoption report, Markdown
notes, packet JSONL, and per-owner packets for Semantic Substrate, Orchestrator,
and Exception Lake. Ready packets require matching comparison/ledger lineage,
candidate local labels, review signals, append-only event posture, and no
billing, Lake/SQLite, mutation, sibling-repo, or learning side effects. Lineage
drift or prohibited flags must produce blocked owner packets.

`capture-carrier-rejections` writes `carrier_rejection_decision_ledger_report.json`,
`carrier_rejection_decision_ledger.jsonl`, and
`carrier_rejection_decision_ledger_report.md`. The ledger must preserve one
append-only candidate row for rejection states, duplicate collapse, pending
fix/appeal decisions, appeal results, and financial outcomes. Appeal-result
financial rows must preserve appealed, recovered, write-down, and remaining
write-down amounts while proving no appeal submission, no portal/email write, no
Lake/SQLite admission, and no silent learning.

`build-budget-event-lake-bundle` consumes the budget change ledger, budget
actual variance ledger, and carrier rejection decision ledger and writes
`budget_event_lake_admission_bundle_report.json` plus Markdown notes. The bundle
must hash each artifact, match JSONL rows to report event IDs, require consistent
budget/preflight IDs, map events to candidate record families, and fail closed on
missing artifacts or any Lake/SQLite/billing/submission/mutation/silent-learning
flag drift. Passing status means ready for Exception Lake owner review only.

`audit-budget-lifecycle` consumes the budget change ledger, budget actual
variance ledger, carrier rejection decision ledger, and budget-event Lake
bundle. It writes `budget_lifecycle_audit_report.json` and Markdown notes. The
audit must require consistent budget/preflight IDs, summarize original,
human-revised, actual, disputed, recovered, and write-down amounts, preserve
pending human decisions as review content, and fail closed on missing artifacts,
ID drift, Lake-bundle failure, missing lifecycle record families, or prohibited
write/submission/mutation/silent-learning flag drift.

`build-budget-human-review-packet` consumes the budget lifecycle audit and
optional budget revision, actual comparison, carrier rejection review, and
carrier rejection learning reports. It writes a consolidated human packet,
Markdown notes, and decision templates. The packet must include recommendations,
why-notes, red-team notes, required review sections, pending human decisions,
financial summary, and append-only decision templates while preserving no budget
submission, no appeal submission, no billing write, no Lake/SQLite write, no
budget/profile/template/guideline mutation, no sibling repo write, and no silent
learning. Blocked lifecycle audits must produce a blocked packet.

`record-budget-human-review-outcome` consumes the budget human review packet and
an explicit human outcome JSON. It writes an append-only outcome record, JSONL
history, outcome report, and Markdown notes. The report must prove every decision
is bound to a packet template, outcomes are allowed by that template,
follow-up-heavy decisions name owners/due dates, and candidate Lake event labels
remain review-only. Bad packet evidence or unbound outcome evidence must block
the report while preserving no budget/appeal submission, no Lake/SQLite write,
no budget/profile/template/guideline mutation, no sibling repo write, and no
silent learning.

`build-budget-human-review-outcome-owner-adoption` consumes the outcome report
and matching outcome record. It writes an owner-adoption report, Markdown notes,
packet JSONL, and per-owner packets for Semantic Substrate, Orchestrator, and
Exception Lake. Ready packets require a recorded outcome report, matching record
IDs, preserved followups, candidate Lake labels, and no side effects. Blocked
outcomes must produce blocked owner packets. The command must prove no issue/PR
creation, no sibling repo write, no canon promotion, no Lake/SQLite admission,
no budget or appeal submission, no mutation, and no silent learning.

`build-budget-actual-variance-owner-adoption` must remain narrower than the full
lifecycle owner packet: it reviews actual-cost variance labels, governed billing
actuals workflow needs, and append-only actual-variance Lake admission only. It
must not claim actuals are complete when the ledger contains missing-source
events, and it must not treat variance drivers as learning changes without the
reviewed learning gate.

`build-budget-lifecycle-owner-adoption` consumes
`budget_lifecycle_audit_report.json` and writes
`budget_lifecycle_owner_adoption_report.json`, Markdown notes, and owner packet
JSONL. Ready reports must emit packets for Semantic Substrate, Orchestrator, and
Exception Lake with owner actions, acceptance checks, candidate contract refs,
and red-team notes. Blocked lifecycle audits must produce blocked packets. The
command must prove no issue/PR creation, no sibling repo write, no connector
implementation, no Lake/SQLite write, no budget or appeal submission, no budget
mutation, and no silent learning.

The learning loop can write `reviewed_learning_gate_report.json`, then
`audit-learning-promotion-readiness` writes `learning_shadow_eval_plan.json` and
`learning_promotion_readiness_report.json`. `draft-learning-proposed-changes`
then writes `learning_proposed_change_set.json` and
`learning_proposed_changes.jsonl` with recommendations, why-notes, red-team
objections, required fixtures, eval suites, guardrails, and owning-repo routing.
`record-learning-shadow-eval-fixture-results` records explicit reviewer evidence
for the current proposed-change IDs and writes
`learning_shadow_eval_fixture_evidence_report.json` plus fixture-result JSONL.
`run-learning-shadow-eval` writes `learning_shadow_eval_result_report.json` and
`learning_shadow_eval_results.jsonl` after checking reviewed or direct synthetic
fixture result evidence, required eval suites, regression guardrails, and
no-mutation boundaries. `build-learning-owner-handoffs` writes
`learning_owner_handoff_report.json` and owner-specific packages that separate
passed, failed, and blocked candidates by target repo. These artifacts are local
non-authoritative eval evidence: they plan the fixture updates, shadow evals, and
regression checks required before any learning candidate can be considered by an
owning repo. They do not apply proposed changes, mutate baselines, authorize
promotion, write Lake/SQLite records, write sibling repos, or replace
sibling-repo review.

The final local close-out eval is `audit-intake-vertical-readiness`. It consumes
`learning_owner_handoff_report.json` and
`budget_event_lake_admission_bundle_report.json`, plus
`budget_calibration_readiness_report.json` and
`budget_fixture_update_review_report.json` and
`budget_fixture_update_pr_package_report.json`, checks the local candidate
slices, generated learning artifact chain, generated budget-event Lake bundle,
budget lifecycle audit surface, budget human-review packet surface,
budget human-review outcome and outcome-owner-adoption surfaces, budget
actual-variance owner-adoption packet surface, budget lifecycle owner-adoption packet surface,
labor/employment budget fact-gap audit surface,
calibration-readiness chain, fixture-update review record, and fixture-update PR
package, and writes
`intake_vertical_readiness_audit_report.json`. Passing status means ready for
human PR review only; it does not mark a PR ready, promote canon, implement
connectors, admit Lake records, write SQLite, apply proposed changes, mutate
fixtures, apply calibration, or prove production readiness.

`build-pr-review-checklist` consumes the final readiness audit and writes
`pr_review_checklist.json` plus `pr_review_checklist.md`. The checklist is the
human close-out review packet for a draft PR: it records recommended checks,
why-notes, red-team notes, blocking readiness items, required human decisions,
and validation commands. A blocked readiness audit produces a blocking checklist
item. A ready checklist still records `pr_marked_ready=false` and
`github_write_performed=false`; it does not change PR state, promote canon,
write Lake/SQLite records, write sibling repos, or apply learning.

`build-cross-repo-owner-adoption` consumes the static cross-repo promotion
package plus the live readiness audit and PR checklist, then writes owner-specific
adoption packets for Semantic Substrate, Orchestrator, Exception Lake, Skills
Registry, and Legal Knowledge Runtime. The report is an owner-review planning
artifact: it groups candidate proposals by target owner, names owner actions,
acceptance checks, and red-team notes, and blocks if PR readiness evidence is
blocked. It does not create issues, open PRs, write sibling repos, promote canon,
admit Lake/SQLite records, or apply learning.

`build-cross-repo-owner-issue-drafts` consumes the owner-adoption report and
writes per-owner Markdown/JSON issue drafts for manual creation. Drafts preserve
source evidence refs, candidate proposal summaries, owner actions, acceptance
checks, red-team notes, and no-write boundaries. A blocked owner-adoption packet
produces a blocked issue draft. The command does not create issues, open PRs,
write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.

`audit-intake-local-closeout` consumes the final readiness audit, PR checklist,
owner-adoption report, and owner issue-draft report. It writes
`intake_local_closeout_report.json` plus Markdown notes. Passing status means the
intake-local candidate evidence chain is ready for manual external actions, not
that the PR was marked ready or sibling repos adopted anything. Blocked evidence
blocks closeout. The command does not mark a PR ready, create issues, open PRs,
write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.

`record-pr-readiness-decision` consumes the PR checklist, local closeout report,
and an explicit human-authored decision JSON. It writes
`pr_readiness_decision_record.json`, appends
`pr_readiness_decision_history.jsonl`, and writes
`pr_readiness_decision_report.json` plus Markdown notes. Mark-ready decisions
must accept every checklist item and cite validation evidence; draft or followup
decisions must name required followups. The command records the decision only
and must not mark a PR ready, call GitHub write APIs, create issues, open PRs,
write sibling repos, promote canon, admit Lake/SQLite records, apply proposed
changes, or apply learning.

`plan-remaining-roadmap` consumes the final readiness audit, local closeout
report, and optional PR readiness decision report. It writes a typed remaining
roadmap report and JSONL item list that classify remaining work by owner,
workstream, effort, risk, gate, acceptance evidence, and red-team notes. Eval
coverage must prove the plan is blocked by failed source evidence, preserves
next recommended manual/owner steps, moves recommendations to owner follow-up
when `observed_pr_state=merged`, distinguishes easy local work from critical
owner-gated work, and performs no GitHub, sibling repo, Lake, SQLite, promotion,
real-data, or learning side effects.

`audit-synthetic-fixture-expansion` consumes the remaining-roadmap report and
the synthetic holdout manifest. Eval coverage must prove all required holdout
families are present, fixture and test refs stay under the repo root, scoped JSON
fixtures are synthetic-only and not calibration-approved, missing required
families fail closed, and the audit performs no fixture mutation, GitHub write,
sibling repo write, Lake/SQLite write, promotion, or learning.

### Counterfactual evals

Same source, different practice context. Evidence must remain unchanged.

### Adversarial evals

Prompt injection, misleading sender identity, missing attachment, duplicated text, conflicting roles, unsupported case type, stale profile, and budget false precision.

### Human factors

Measure review time, correction count, unknown selection, evidence-navigation burden, and rubber-stamp behavior.

## Metrics

- accepted packet rate per reviewer hour;
- median review time;
- party extraction precision/recall;
- top-three matter recall;
- principal-role correction rate;
- evidence completeness;
- source coverage completeness;
- high-confidence error rate;
- abstention appropriateness;
- escalation recall/precision;
- budget calculation error rate;
- invented rate/guideline count (must be zero);
- prohibited-action proposal count (must be zero or blocked before output).

## Evaluation integrity

- use private/hidden holdouts for capability claims;
- block answer leakage and benchmark/source discovery paths;
- separate evaluator changes from workflow-output changes;
- label corpus/profile/template baseline changes;
- inspect traces and artifacts, not scores alone;
- retain reviewer disagreement rather than forcing false gold.
- keep `fixture_gold_report.json` local and non-authoritative; it is evaluation evidence, not canonical platform truth.
- keep `starter_release_audit_report.json` local and non-authoritative; it proves starter artifact invariants only and does not replace tests, CI, Semantic Substrate promotion, Orchestrator runtime ownership, or human legal review.
- keep `blocked_budget_attempt_audit_report.json` local and non-authoritative; it proves the synthetic blocked-budget canary only and does not authorize any budget-stage output.
- keep `context_counterfactual_audit_report.json` local and non-authoritative; it proves practice-context separation on synthetic fixtures only and does not promote profiles, priors, or taxonomies.
- keep learning shadow-eval and promotion-readiness reports local and non-authoritative; they plan required eval evidence and block promotion, but do not apply changes or prove production readiness by themselves.
- keep `budget_human_review_packet.json` local and non-authoritative; it gives humans recommendations, why-notes, red-team notes, and decision templates for budget lifecycle evidence but must not submit budgets or appeals, write billing, admit Lake/SQLite records, mutate budgets/profiles/templates/guidelines, write sibling repos, promote canon, or apply learning.
- keep `budget_human_review_outcome_report.json` local and non-authoritative; it records append-only human budget review decisions and followups, but must not submit budgets or appeals, write billing, admit Lake/SQLite records, mutate budgets/profiles/templates/guidelines, write sibling repos, promote canon, or apply learning.
- keep `budget_human_review_outcome_owner_adoption_report.json` local and non-authoritative; it turns recorded budget decisions into owner-review packets but must not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, submit budgets or appeals, mutate budgets/profiles/templates/guidelines, or apply learning.
- keep `intake_vertical_readiness_audit_report.json` local and non-authoritative; it proves PR-review readiness for candidate artifacts only and keeps external adoption with the owning repos.
- keep `pr_review_checklist.json` local and non-authoritative; it helps a human make the draft-PR decision but must not mark the PR ready, call GitHub write APIs, promote canon, write Lake/SQLite records, or apply learning.
- keep `cross_repo_owner_adoption_report.json` local and non-authoritative; it turns candidate proposals into owner-review packets but must not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.
- keep `cross_repo_owner_issue_draft_report.json` local and non-authoritative; it drafts owner issue text for manual use but must not create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.
- keep `intake_local_closeout_report.json` local and non-authoritative; it proves the local closeout evidence chain and remaining manual gates but must not mark a PR ready, create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, or apply learning.
- keep `pr_readiness_decision_report.json` local and non-authoritative; it records the human PR readiness decision append-only but must not mark a PR ready, call GitHub write APIs, create issues, open PRs, write sibling repos, promote canon, admit Lake/SQLite records, apply proposed changes, or apply learning.
- keep `public_source_methodology_report.json` local and non-authoritative; it prepares public-source methodology review but must not ingest public records, authorize adapters, commit public payloads, write Lake/SQLite records, or permit runtime public-data use.
- keep `public_synthetic_fixture_conversion_plan.json` local and non-authoritative; it plans structure-only synthetic fixture conversion but must not create fixture files, ingest public records, authorize adapters, commit payloads, write Lake/SQLite records, or apply public-data learning.
- keep `public_synthetic_fixture_conversion_review_packet.json` local and non-authoritative; it helps humans decide whether conversion specs may proceed to a separate fixture PR but must not approve fixture generation by itself, create PRs, mutate fixtures, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.
- keep `public_synthetic_fixture_conversion_review_outcome_report.json` local and non-authoritative; it records a human decision append-only but must not create fixtures, create PRs, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.
- keep `public_synthetic_fixture_pr_package_report.json` local and non-authoritative; it packages manual instructions for a separate fixture PR but must not edit fixtures, create PRs, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.
- keep `public_methodology_owner_handoff_report.json` local and non-authoritative; it routes the public methodology, conversion plan, and conversion review packet to Intake, Legal Knowledge Runtime, Semantic Substrate, Orchestrator, and Exception Lake for manual owner review, but must not create issues, open PRs, write sibling repos, promote canon, create fixtures, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.

## Graduation gates

A smaller/local model may replace a stronger baseline only when task-specific evals show required quality, calibration, evidence completeness, and safety with no authority expansion.
