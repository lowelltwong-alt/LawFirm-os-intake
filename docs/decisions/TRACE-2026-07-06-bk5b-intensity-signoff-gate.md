# TRACE 2026-07-06: BK5b Intensity Signoff Gate

## Decision

Add the BK5b signoff packet and validation gate for a future
`baseline_relative` intensity-normalization policy flip, without changing the
current `raw` default or regenerating budget goldens.

## Rationale

Fable's BK5 kernel showed that switching intensity multipliers from raw to
baseline-relative can change headline budget totals. That change is useful but
requires explicit human approval. This slice makes the approval evidence
deterministic before any number-changing policy flip can merge.

## Scope

- Added a candidate-only signoff report that compares raw vs baseline-relative
  default products and canonical demo budget totals.
- Added a Markdown rendering for human review.
- Added a validation gate that passes for `raw` mode but fails closed for
  `baseline_relative` unless an approved signoff artifact matches the active
  policy hash.
- Wired the gate into `scripts/validate_repo.py`.
- Added CLI commands for building and validating the signoff artifact.
- Added schema exports and deterministic tests.

## Non-Goals

- No flip of `config/budget-driver-policy.yaml` to `baseline_relative`.
- No approved human signoff artifact committed in this slice.
- No budget fixture-golden regeneration or headline-total policy change.
- No connector write, Exception Lake write, SQLite write, budget submission,
  matter opening, conflict conclusion, real-rate ingestion, or silent learning.

## Validation

Validation is recorded on the implementing PR. The targeted coverage includes
preview generation, raw-mode no-signoff pass, missing/unapproved signoff
failure, approved signoff pass, CLI output writing, schema export, and repo
validation gate behavior.
