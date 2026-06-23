# Specialist Agent Architecture

## Default architecture

Use one outer workflow owner and a small number of specialists. Specialists are tools/workers under Orchestrator authority, not autonomous peers.

| Worker | Model class | Input | Output | Cannot do |
|---|---|---|---|---|
| Source reader | deterministic/small local | raw bundle | inventory + structural segments | classify matter or use external tools |
| Party-role extractor | small local extractor | segments | entity/role candidates | decide client or adversity |
| Matter router | small reasoning model | segments + context | top candidates | final classification |
| Deadline-gap extractor | parser + small model | segments + required fields | date/gap candidates | docket or conclude deadline |
| Evidence critic | independent small critic | structured candidates | defects/escalation | approve or silently repair |
| Budget planner | deterministic + small model | confirmed facts + template | proposed budget | submit or approve |
| Frontier adjudicator | frontier model | bounded ambiguity packet | alternative analysis | replace human or expand authority |

## Harness requirements

Every worker declares:

- stable ID/version;
- purpose;
- model class;
- input/output schema;
- raw-source access;
- cross-matter access;
- network/tool access;
- write scope;
- budgets and stop conditions;
- evidence requirement;
- abstention support;
- escalation route;
- prohibited actions;
- prompt reference and hash in production.

## Handoff contract

Workers exchange JSON objects only. A handoff includes:

```yaml
handoff_id:
parent_run_id:
worker_id:
input_schema_ref:
output_schema_ref:
artifact_refs:
source_scope:
practice_context_hash:
allowed_tools:
budget:
status:
```

Do not forward raw prose instructions from a source document to another worker.

## Small/local model strategy

Smaller models are appropriate when the task is narrow, schema-constrained, locally testable, and supported by a deterministic validator. A frontier model is reserved for difficult ambiguity, not routine extraction.

The quality ceiling should first be established with a strong model on an approved evaluation set. Smaller/local models graduate only when they meet the required task-specific quality and calibration threshold.

## Escalation

Escalation is triggered by risk and evidence state—not only by confidence. See `config/escalation_policy.yaml`.

## Frontier reviewer independence

A frontier adjudicator should receive:

- structured source inventory;
- relevant evidence spans;
- competing candidates;
- context prior disclosure;
- critic findings;
- missing evidence;
- explicit legal/prohibited boundaries.

It should not receive an unbounded cross-matter corpus or authority to act.

## Harness declarations

Candidate execution envelopes are under `harnesses/`:

- `deterministic.yaml` for parsing, validation, hashing, calculations, and packet assembly;
- `small-local-worker.yaml` for future bounded local extractors/routers;
- `frontier-adjudication.yaml` for governed ambiguity escalation;
- `human-review.yaml` for separation of duties and mandatory review surfaces.

The harness controls turns, tools, data scope, writes, validation, and escalation. The model cannot expand the harness authority.

## Deterministic review forms

The reference workflow writes `intake_review_form.md` and `legal_budget_review_form.md`. These are review surfaces generated from validated packet objects; they are not legal or client-facing documents.
