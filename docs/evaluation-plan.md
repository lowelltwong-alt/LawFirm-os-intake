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

The learning loop can write `reviewed_learning_gate_report.json`, then
`audit-learning-promotion-readiness` writes `learning_shadow_eval_plan.json` and
`learning_promotion_readiness_report.json`. These artifacts are local
non-authoritative eval evidence: they plan the fixture updates, shadow evals, and
regression checks required before any learning candidate can be considered by an
owning repo. They do not apply proposed changes, mutate baselines, authorize
promotion, or replace sibling-repo review.

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

## Graduation gates

A smaller/local model may replace a stronger baseline only when task-specific evals show required quality, calibration, evidence completeness, and safety with no authority expansion.
