# TRACE-2026-06-30 - Synthetic Fixture Depth Audit

## Decision

Add `audit-synthetic-fixture-depth`, a local candidate-only audit that checks
whether the remaining-roadmap holdout manifest is deep enough for the next
budget, carrier-rejection, actuals, role-ambiguity, and learning-loop work.

## Why

`audit-synthetic-fixture-expansion` proves that holdout families, fixture refs,
test refs, and synthetic-only boundaries exist. It does not prove the holdouts
pressure the dangerous cases enough to guide the next build phases. A manifest
can cover each family once and still miss partial allowances, stale or denied
appeal outcomes, labor/employment budget fact gaps, and visible no-write or
no-silent-learning guardrails.

## Scope

- Add a typed `SyntheticFixtureDepthAuditReport`.
- Add a deterministic depth matcher for explicit risk dimensions.
- Add `audit-synthetic-fixture-depth`.
- Write `synthetic_fixture_depth_audit_report.json` and
  `synthetic_fixture_depth_audit_report.md`.
- Add tests for the current manifest ready state, depth-ready augmented
  manifest behavior, negative gap behavior, boundary violations, and CLI output.

## Current Main Findings

After the carrier-rejection counterfactual, ambiguous-role matrix,
missing-actuals, budget-driver, and labor/employment critical-fact holdouts were
merged, the current `main` holdout manifest audits successfully as
`synthetic_fixture_depth_ready_for_review`:

- seven holdouts;
- seven covered depth dimensions;
- zero missing depth dimensions;
- zero boundary violations.

This is still candidate review evidence, not calibration approval or production
readiness. Negative tests keep proving that prose-only matches, missing named
tests, unbound fixture refs, external refs, and recursive forbidden flags fail
closed.

## Boundaries

- Synthetic-only, local candidate evidence.
- No calibration approval.
- No GitHub issue or PR creation from the command.
- No sibling repo write.
- No Lake or SQLite admission.
- No external connector or submission write.
- No fixture mutation.
- No silent learning or profile/guideline/budget mutation.

## Red-Team Notes

- A depth audit can become false confidence if it is treated as calibration
  approval. The report keeps `calibration_approved=false`.
- Term-based matching is intentionally deterministic and reviewable. It is not a
  semantic proof that a fixture is sufficient.
- Covered dimensions require structural fixture evidence plus named test
  evidence; manifest prose alone is reported as a gap.
- A ready depth audit is useful only as a review gate. It keeps the roadmap
  honest by proving the currently declared synthetic holdouts hit the named
  danger dimensions, while separate negative tests keep gap behavior visible.

## Validation

Planned validation:

- `python scripts/run_full_pytest.py -q tests/test_synthetic_fixture_depth_audit.py`
- `python scripts/validate_repo.py`
- `python scripts/export_schemas.py`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/run_full_pytest.py`
- `bash scripts/smoke_demo.sh`
