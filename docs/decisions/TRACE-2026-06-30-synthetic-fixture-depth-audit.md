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
- Add tests for current gaps, depth-ready augmented manifest behavior, boundary
  violations, and CLI output.

## Current Main Findings

The current `main` holdout manifest audits successfully but reports open depth
gaps:

- `carrier_partial_allowance_and_appeal_outcome_variety`;
- `labor_employment_budget_fact_gap_holdout`.

These are candidate review findings, not repo-health failures. They are meant to
shape the next fixture PRs and owner-review queue.

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
- Current gaps are useful because they keep the roadmap honest before real or
  synthetic training data expands.

## Validation

Planned validation:

- `python scripts/run_full_pytest.py -q tests/test_synthetic_fixture_depth_audit.py`
- `python scripts/validate_repo.py`
- `python scripts/export_schemas.py`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/run_full_pytest.py`
- `bash scripts/smoke_demo.sh`
