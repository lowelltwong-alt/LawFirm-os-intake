# TRACE-2026-06-30 - L&E Ready Critical Facts Holdout

## Context

The L&E budget fact audit already proved that missing entity, relationship, damages,
discovery, deposition, and carrier/rate facts block budget readiness. The remaining
fixture gap was the opposite edge: a source packet where all critical L&E budget
facts have source-bound candidate evidence, including supervisor and affiliate
relationships, while non-critical facts still require human review.

## Decision

Add `labor-employment-ready-critical-facts-manifest.json` as a synthetic
CourtListener-style holdout and register it under the existing
`budget_driver_edges` fixture-expansion family.

The fixture binds critical facts to existing synthetic snapshot segment IDs,
offsets, and hashes. It deliberately leaves expert/vendor and policy-document
signals in `needs_review` state so the audit lands at
`range_only_pending_human_review`, not budget approval or submission.

## Red-Team Notes

- Source-bound candidate evidence is not human confirmation.
- Supervisor, individual actor, affiliate, and carrier/rate labels must not clear
  conflicts, identify the represented client with finality, or authorize matter
  opening.
- The range-only posture must preserve no budget amount output, no submission, no
  Lake/SQLite write, no external write, and no silent learning.
- This fixture remains synthetic and non-authoritative; it does not promote L&E
  role, matter, budget, carrier, or guideline taxonomy.

## Validation

- `python scripts/run_full_pytest.py tests/test_labor_employment_budget_facts.py tests/test_synthetic_fixture_expansion.py tests/test_courtlistener_fixture_audit.py -q`
- `python scripts/validate_repo.py`
