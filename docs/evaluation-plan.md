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

`record-budget-review` also writes `budget_change_ledger_report.json`,
`budget_change_ledger.jsonl`, and `budget_change_ledger_report.md`. Corrected
review outcomes must produce one ledger row per human change; no-change or
blocked outcomes must produce an outcome-only row. Each row preserves reviewer
metadata, before/after totals, evidence refs, structured refs, and local
candidate Lake labels while proving no source budget mutation, no superseding
budget write, no Lake/SQLite admission, no billing connector write, and no
silent learning.

`capture-carrier-rejections` writes `carrier_rejection_decision_ledger_report.json`,
`carrier_rejection_decision_ledger.jsonl`, and
`carrier_rejection_decision_ledger_report.md`. The ledger must preserve one
append-only candidate row for rejection states, duplicate collapse, pending
fix/appeal decisions, appeal results, and financial outcomes. Appeal-result
financial rows must preserve appealed, recovered, write-down, and remaining
write-down amounts while proving no appeal submission, no portal/email write, no
Lake/SQLite admission, and no silent learning.

The learning loop can write `reviewed_learning_gate_report.json`, then
`audit-learning-promotion-readiness` writes `learning_shadow_eval_plan.json` and
`learning_promotion_readiness_report.json`. `draft-learning-proposed-changes`
then writes `learning_proposed_change_set.json` and
`learning_proposed_changes.jsonl` with recommendations, why-notes, red-team
objections, required fixtures, eval suites, guardrails, and owning-repo routing.
`run-learning-shadow-eval` writes `learning_shadow_eval_result_report.json` and
`learning_shadow_eval_results.jsonl` after checking synthetic fixture result
evidence, required eval suites, regression guardrails, and no-mutation
boundaries. `build-learning-owner-handoffs` writes
`learning_owner_handoff_report.json` and owner-specific packages that separate
passed, failed, and blocked candidates by target repo. These artifacts are local
non-authoritative eval evidence: they plan the fixture updates, shadow evals, and
regression checks required before any learning candidate can be considered by an
owning repo. They do not apply proposed changes, mutate baselines, authorize
promotion, write Lake/SQLite records, write sibling repos, or replace
sibling-repo review.

The final local close-out eval is `audit-intake-vertical-readiness`. It consumes
`learning_owner_handoff_report.json`, checks the local candidate slices and the
generated learning artifact chain, and writes
`intake_vertical_readiness_audit_report.json`. Passing status means ready for
human PR review only; it does not mark a PR ready, promote canon, implement
connectors, admit Lake records, write SQLite, apply proposed changes, or prove
production readiness.

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
- keep `intake_vertical_readiness_audit_report.json` local and non-authoritative; it proves PR-review readiness for candidate artifacts only and keeps external adoption with the owning repos.

## Graduation gates

A smaller/local model may replace a stronger baseline only when task-specific evals show required quality, calibration, evidence completeness, and safety with no authority expansion.
