# TRACE: Carrier Appeal Human Outcome Fixture

## Context

Carrier rejection capture, review packets, appeal-result evidence, learning
proposals, budget lifecycle audit, and owner-review handoffs already exist as
candidate-only local surfaces. The learning loop still needs reviewed human
outcome evidence before any carrier rejection or appeal result can become a
candidate learning signal.

## Decision

Add a synthetic fixture for a human-reviewed carrier appeal outcome:

- `examples/synthetic/budget-human-review/medmal-carrier-appeal-human-outcome.json`.

The fixture records three human decisions against the existing budget human
review packet templates:

- appeal follow-up for the carrier rejection;
- accepted write-off/financial outcome for the appeal result;
- explicit no-learning-change posture for the learning loop.

The test binds fixture placeholders to the generated packet and template IDs,
then runs the existing `record-budget-human-review-outcome` machinery.

## Boundary

This is reviewed synthetic evidence only. It does not submit an appeal, submit a
budget, send email, write a carrier portal, write billing, admit Lake/SQLite
records, mutate budgets/profiles/templates/guidelines, write sibling repos,
promote canon, or apply learning.

## Red-Team Notes

- An appeal decision is not appeal authority.
- A write-off decision is not billing write authority.
- A no-learning decision must stay explicit so future reviewers do not treat a
  carrier rejection as automatic guideline/profile mutation evidence.
- Fixture placeholders must bind to generated packet templates rather than
  hard-code unstable IDs.

## Validation Plan

- Focused outcome tests prove the fixture records one appeal decision, one
  write-off decision, and one no-learning-change decision.
- The persisted record and report keep all no-write/no-submission/no-learning
  flags false.
- Existing budget human review packet and reviewed-learning tests continue to
  prove the carrier rejection learning path remains blocked until reviewed
  evidence, shadow eval, and owner review exist.
