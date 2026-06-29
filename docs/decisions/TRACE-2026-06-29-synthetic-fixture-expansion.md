# TRACE-2026-06-29 - Synthetic Fixture Expansion Audit

## Context

The remaining-roadmap report names `fixture-and-eval-expansion` as the next
local candidate work that intake can execute without owner-repo adoption. The
repo already had several synthetic holdouts, but reviewers needed one typed
proof surface showing which risk families were covered and whether those
fixtures were safe to use as review evidence.

## Decision

Add a synthetic holdout manifest and audit command:

- `examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json`
- `audit-synthetic-fixture-expansion`
- `synthetic_fixture_expansion_report.json`
- `synthetic_fixture_expansion_report.md`

The manifest covers:

- ambiguous roles;
- missing actuals;
- carrier rejection variants;
- budget driver edge cases.

This slice also adds:

- `examples/synthetic/actuals/medmal-missing-actuals.json`;
- `examples/synthetic/budget-drivers/medmal-driver-edge-cases.json`.

## Boundaries

- Holdouts are synthetic-only and candidate-only.
- The audit mutates no fixture files.
- The audit does not approve calibration or fixture-gold status.
- The audit creates no issues or PRs.
- The audit writes no sibling repos.
- The audit performs no Lake or SQLite admission.
- The audit applies no learning.

## Rationale

Fixture expansion is the safest remaining roadmap item to execute inside
`LawFirm-os-intake`. It improves review coverage before any real-data pilot,
while preserving the separation between holdout availability, fixture-update
review, shadow eval, owner adoption, and calibration.

## Red-Team Notes

- A holdout manifest can create false confidence if it is mistaken for coverage
  sufficiency or calibration approval.
- Missing actuals must not be treated as zero spend.
- Carrier rejection duplicates can double-count disputed amounts if not
  collapsed deterministically.
- Budget driver edge cases can overfit deterministic multipliers unless later
  shadow evals and owner review agree.

## Acceptance

- Ready remaining-roadmap evidence plus the manifest produces
  `synthetic_fixture_expansion_ready_for_review`.
- Missing required holdout family coverage fails closed.
- Fixture/test refs must exist under the repo root.
- Scoped JSON fixtures must remain synthetic-only and not calibration-approved.
- The report preserves no GitHub, sibling repo, Lake, SQLite, calibration,
  fixture-mutation, external-write, or learning side effects.
