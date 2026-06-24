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

## Graduation gates

A smaller/local model may replace a stronger baseline only when task-specific evals show required quality, calibration, evidence completeness, and safety with no authority expansion.
