# TRACE-2026-07-12 - Pilot Review Workbench Contract Proof

## Context

The local review UI already showed synthetic intake, matter-linking, L&E budget,
and learning evidence. The newly merged cross-repo contract proof was available
only as a JSON/Markdown artifact, which made a critical runtime boundary harder
to inspect alongside the budget and evidence review surface.

## Decision

Render the checked synthetic cross-repo contract-proof report in the read-only
workbench. The panel shows the Intake request, Orchestrator owner packet, Lake
review packet, Exception Lake validation result, clean owner commit pins, and
the disabled authority flags.

The UI treats the intentional `blocked_pending_owner_review` and
`blocked_pending_exception_lake_owner_review` states as correct workflow
pauses, not errors to be hidden.

## Boundary

- The panel imports checked local JSON fixtures only.
- It makes no fetch, connector, command, mutation, Lake, SQLite, submission,
  matter-opening, conflict-clearance, or canonical-authority call.
- The displayed proof remains pinned-commit candidate evidence, not owner
  acceptance or production authorization.

## Red-Team Notes

- A green validation badge could be misread as permission to proceed. The UI
  therefore keeps the owner and Lake blocks in the handoff sequence and renders
  every prohibited authority as `blocked`.
- Dense synthetic fixture rows previously overflowed a mobile viewport. The
  workbench now uses explicit fixture-row grids and its Playwright smoke test
  checks both desktop and mobile, excluding only intentional horizontally
  scrollable table regions.

## Validation

- `npm run build`
- `npm run smoke:browser` at desktop and mobile viewports
- `python scripts/run_full_pytest.py tests/test_ui_foundation_contract.py -q`
