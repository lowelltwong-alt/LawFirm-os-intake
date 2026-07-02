# TRACE 2026-07-02 Synthetic Confidence Summary

## Decision

Add a local, candidate-only `synthetic_confidence_summary_report.json` generated from the synthetic QA review-run report, synthetic QA bundle, UI manifest, and UI review data bundle.

## Rationale

The frontend had detailed QA panels but no single artifact that answered whether the current run is ready for synthetic QA review. Reviewers had to infer the state from many lower-level tables, which could hide missing evidence or create false confidence.

The new summary is intentionally not a probability, calibration score, production readiness claim, budget approval, or Exception Lake admission. It is a compact readiness banner over local synthetic evidence.

## Boundary

- Candidate-only and synthetic-only.
- Local JSON only.
- No budget submission, matter opening, conflict conclusion, Lake write, SQLite write, external write, calibration, or silent learning.
- Pending owner/human review remains required before any promotion.

## Tests

- `tests/test_synthetic_confidence_summary.py`
- `tests/test_synthetic_qa_review_run.py`
- `tests/test_ui_review_data_bundle.py`
- `tests/test_ui_foundation_contract.py`

## Red Team Notes

- Do not treat `synthetic_qa_ready_pending_review` as production readiness.
- Do not let the frontend display this summary without the candidate-only/no-submission banner.
- Do not let the lower-level synthetic QA bundle claim the full UI cockpit is ready before the confidence summary exists.
