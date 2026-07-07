# TRACE 2026-07-07: BK5b Approved Intensity Normalization Flip

## Decision

Flip `config/budget-driver-policy.yaml` from legacy `raw` intensity
normalization to `baseline_relative` after explicit human approval in the Codex
thread on 2026-07-07.

## Rationale

The prior raw policy multiplied default matter-family intensity tiers into
template-authored baseline hours. For the current synthetic defaults, that meant
default L200, L300, and L400 work could be multiplied by `1.05`, `1.134`, and
`1.08` before any observed or human-confirmed intensity fact existed. Fable's
BK5 kernel identified that as default-tier double counting.

Baseline-relative normalization keeps the human-readable raw tier ladder in the
policy, but interprets intensity multipliers as deviations from the
family/template baseline. Family-default tiers now normalize to `1.0` for each
phase.

## Approval Evidence

Committed signoff artifacts:

- `docs/governance/intensity_normalization_signoff.json`
- `docs/governance/intensity_normalization_signoff.md`

The signoff records:

- status `approved_for_baseline_relative`;
- approval timestamp `2026-07-07T04:17:06Z`;
- policy hash before and after;
- family-default phase products before and after;
- canonical demo budget totals before and after;
- candidate-only, synthetic-only, no real firm data, no budget submission
  authority, no matter-opening authority, no conflict-clearance authority, no
  Lake write, and no external write.

Canonical demo deltas in the signoff:

- `carrier-assignment-auto-bi`: `68627.79` -> `63227.80` (`-5399.99`).
- `carrier-assignment-medmal`: `162027.66` -> `148406.00` (`-13621.66`).

## Scope

- Add `normalization: baseline_relative` to the synthetic budget-driver policy.
- Commit the approved signoff JSON and Markdown.
- Keep legacy `raw` behavior covered through explicit temp-policy tests.
- Update active docs/data-flow surfaces to explain the approved policy gate.
- Keep the signoff validation in `scripts/validate_repo.py`.

## Non-Goals

- No carrier/client submission.
- No matter opening.
- No conflict conclusion.
- No real-rate, real-guideline, or real-matter ingestion.
- No Exception Lake or SQLite write.
- No Semantic Substrate promotion of the local driver taxonomy.
- No manual renormalization of YAML multiplier values.

## Validation

This slice must pass focused intensity/budget tests and the full validation
suite before merge. The expected smoke-demo terminal boundary remains
`blocked_pending_conflicts_and_engagement`.
