# TRACE: Replay Input Reconciliation Is Evidence-Bound

## Decision

The Labor/Employment outcome-replay builder-binding audit may consume an optional,
previously validated replay input-pack report. It clears a builder input gap only
when that report marks the exact case-bound input as `ready` after local path,
schema, family, identity, and no-write boundary validation.

It does not invoke builders, create runtime artifacts, treat declared input refs
as proof, or fabricate carrier, appeal, or learning-loop reports for a case that
does not exercise those lanes.

## Why

The initial binding audit correctly proved that every expected artifact slot had a
deterministic local builder. It intentionally reported static input gaps, even
when a later input-pack audit had already validated some synthetic source inputs.
That made the audit conservative but unable to distinguish verified inputs from
missing ones.

The replay seeds also include scoped cases that exercise only actuals or only
carrier rejection. The aggregate budget-learning-loop builder requires both
actuals and carrier artifacts. Producing empty complements just to make every
seed look complete would convert an explicit coverage gap into a false claim of
learning-loop evidence.

## Boundaries

- All sources remain local, synthetic, candidate-only, and human-review-bound.
- The reconciled report still has `runtime_artifacts_created=false`.
- No budget submission, matter opening, calibration, Lake/SQLite write, external
  write, or silent learning is authorized or performed.
- A partial replay remains partial until its genuinely applicable artifacts are
  produced and independently validated.

## Verification

`tests/test_labor_employment_budget_outcome_replay_builder_binding.py` proves:

1. The normal audit still binds every known slot without running builders.
2. A validated input-pack report reduces replay input gaps.
3. A report tied to a different builder-binding identity is rejected fail-closed.
4. The supplied manifest is revalidated at reconciliation time, so a prior
   `ready` label cannot stand in for the current file, schema, family, identity,
   or boundary checks.
5. Unresolved gaps remain explicit; reconciliation cannot make a partial loop
   appear complete.
6. The no-write and no-learning boundaries remain false/blocked.

## Next Decision

Before building a generator for the remaining inputs, separate complete
actuals-plus-carrier learning loops from scoped partial loops in the replay seed
contract. That design must define truthful partial-loop output semantics rather
than using aggregate-report filenames as a coverage proxy.
