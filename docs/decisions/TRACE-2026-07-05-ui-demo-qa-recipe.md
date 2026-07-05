# TRACE 2026-07-05: UI Demo QA Recipe

## Decision

Add `run-ui-demo-qa-recipe` as the deterministic local wrapper for the full
read-only UI QA fixture path.

The command either consumes a prebuilt validation-suite evidence report or runs
`scripts/run_validation_suite.py`, builds an initial synthetic QA run, promotes
that run into a scratch fixture copy, generates Rust boundary and manifest
evidence from the scratch fixture set, builds a final synthetic QA run from
those proofs, and performs the final checked fixture promotion only when
`--write-fixtures` is supplied.

## Rationale

The previous workflow was correct but hand-sequenced. That made it too easy to
refresh one layer of UI evidence while forgetting another layer, or to reuse
stale Rust/validation artifacts. The recipe keeps validation, synthetic QA,
Rust wrapper evidence, and checked fixture promotion in one auditable report.

## Deterministic Gates

- Validation evidence must be `validation_suite_passed`.
- Validation steps must match the canonical wrapper order exactly.
- Validation steps must all pass with return code `0`.
- Validation evidence must report `working_tree_dirty=false`.
- Initial and final synthetic QA runs must be
  `synthetic_qa_review_run_ready`.
- Final `ui_review_data_bundle.json` must be `ready_for_review`.
- Final `poc_qa_triage_report.json` must be `poc_qa_ready_for_review`.
- Rust boundary and manifest reports must be generated from the scratch fixture
  root and pass with zero failures.
- Final fixture promotion must be `ui_demo_fixture_promotion_verified`.

## Prohibited Outcomes

- No production connector calls.
- No Lake or SQLite writes.
- No matter opening, conflict conclusion, budget approval, or budget submission.
- No silent learning or calibration.
- No acceptance of partial validation evidence or stale Rust wrapper evidence as
  the final checked fixture proof.

## Validation

Focused test:

```text
python scripts\run_full_pytest.py tests\test_ui_demo_qa_recipe.py -q
```

Observed:

```text
1 passed
```
