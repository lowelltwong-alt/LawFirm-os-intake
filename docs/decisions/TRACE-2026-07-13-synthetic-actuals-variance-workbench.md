# TRACE: Synthetic Actuals Variance Workbench

## Decision

Expose a local, read-only synthetic EPLI actuals-versus-budget workbench. The packet is pinned to one synthetic budget proposal and one synthetic actuals source, each with a SHA-256 digest. It renders an aggregate and switchable phase/code drilldowns, then permits a local CSV export.

## Invariants

- Phase and code rows are alternate reconciled views of the same outcome. They must never be added together.
- The aggregate is sourced from phase actuals when phase actuals are available, matching the existing comparison contract.
- The fixed workbench declares its comparison baseline as `original_proposal`; a future revised baseline must include both revision ID and ref.
- Any partial actuals coverage, unbudgeted actual, or phase/code reconciliation mismatch blocks the packet from ready-for-review status.
- Carrier rejection, recovery, and write-down figures are outside this artifact. They remain a separate candidate evidence lane.

## Provenance And Boundaries

- Budget source: `examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json`
- Actuals source: `examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/budget_actuals_source.json`
- Both sources are synthetic, candidate-only, and non-authoritative.
- The UI imports checked local JSON only. It performs no billing read, carrier portal call, external write, Lake/SQLite write, budget submission, matter opening, calibration, or silent learning.

## Evidence

- Deterministic workbench artifact: `synthetic_actuals_workbench_report.json`
- Focused governed tests: `tests/test_synthetic_actuals_workbench.py` and `tests/test_ui_foundation_contract.py`
- The adversarial cases mutate only test-local synthetic copies and prove fail-closed behavior for mismatched code totals, partial actuals, and unbudgeted actuals.

## Next Gate

This is a review surface, not a calibration engine. A human-reviewed learning gate and Exception Lake owner review remain required before any candidate change or event admission.
