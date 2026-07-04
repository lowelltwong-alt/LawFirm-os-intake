# TRACE 2026-07-04: L&E Discrimination Harassment Messy-Thread Executable Fixture

## Decision

Add a synthetic-only executable fixture for `discrimination_harassment:messy_thread` and require the QA ladder to keep the budget output at `candidate_range_after_review_pending_human_review` when the intake source contains duplicated quoted correspondence, supervisor and HR role ambiguity, agency/right-to-sue deadline candidates, identified ESI sources, and missing forum/arbitration and handbook/policy files.

## Why

Discrimination and harassment intakes often arrive as forwarded correspondence dumps where claimant statements, HR summaries, supervisor responses, and duplicate thread copies are mixed together. This fixture exercises that common L&E path without real data: the system must preserve exact source evidence, detect duplicate correspondence, separate quoted history from current sender assertions, keep supervisor and HR participants as role candidates, treat right-to-sue dates as deadline-review candidates only, and avoid narrowing a budget from missing forum and policy materials.

## Boundary

- Source bundle is synthetic and candidate-only.
- Duplicate quoted-thread text must not inflate witness, deposition, ESI, deadline, or budget-driver scope.
- Ari Bell, Juniper Textile Works Inc., Evan Park, and Priya Shah are synthetic entities only.
- Supervisor and HR references remain role candidates, not confirmed individual defendants or separate-counsel triggers.
- Right-to-sue and agency-charge references are deadline/procedure candidates only and do not authorize docketing.
- Missing forum/arbitration and handbook/policy facts keep the budget review-bound.
- No budget submission, matter opening, conflict conclusion, deadline docketing, Lake write, SQLite write, external write, or silent learning is authorized.

## Evidence

- Added `examples/synthetic/labor-employment/executable-fixtures/le-discrimination-harassment-messy-thread.source-bundle.json`.
- Linked the executable fixture to `le-discrimination-harassment-messy-thread.v0_1`, moving executable coverage to 27 fixtures, 28 covered pack cases, and 4 remaining missing executable cases.
- Added fact bindings for supervisor/manager defendants, administrative exhaustion, employment timeline, ESI sources, forum/arbitration posture, and policy/handbook documents.
- Added the case to the reviewed nonblocking driver-impact replay spec, moving reviewed nonblocking cases to 14.
- Updated fixture, coverage, fact-binding, driver-binding, impact, nonblocking review, budget-output, QA-gate, smoke, and UI contract expectations.
- Updated read-only UI proof fixtures to show 27 executable fixtures, 28 covered pack cases, 4 remaining missing executable cases, 14 reviewed nonblocking cases, 5 range-or-hours-only cases, and 9 candidate range-after-review cases.

## Verification

- `python -m lawfirm_os_intake build-synthetic-qa-review-run --run-root .lawfirm-os-intake\tmp\le-discrimination-messy\full-run-1 --repo-root . --generated-at 2026-07-04T00:00:00Z`
