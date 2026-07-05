# TRACE 2026-07-05 UI Demo Fixture Promotion

## Decision

Add an explicit `promote-ui-demo-run-fixtures` command for checked UI demo
fixtures.

## Rationale

The frontend imports checked JSON fixtures from
`apps/legal-intake-budget/src/fixtures/`, but generated QA runs write local
artifacts under ignored run roots. A wrapper refresh can update source hashes
and the fixture manifest, but it cannot safely decide which generated artifacts
should become checked demo evidence.

The promotion path therefore uses a static allowlist of UI-imported JSON
reports, recursively sanitizes generated run-root strings to `<demo-run-root>`,
blocks missing, ambiguous, out-of-root, leaking, or side-effecting artifacts,
and regenerates wrapper/gate reports after promotion.

## Boundaries

- Candidate-only and synthetic-only.
- Local JSON only.
- No arbitrary directory copy from a generated run root.
- No schema promotion.
- No budget submission, matter opening, connector write, Lake write, SQLite
  write, or silent learning.
- Rust boundary, UI source-hash, and snapshot-coherence gates must pass before
  the promotion report can be verified.

## Validation

- `tests/test_ui_demo_fixture_promotion.py`
- `python -m lawfirm_os_intake promote-ui-demo-run-fixtures --write-fixtures`
  remains explicit and fail-closed.
