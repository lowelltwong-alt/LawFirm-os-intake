# Decision Trace — CW0 Trust Closeout (F5 + F6)

Wave: CW0 of the converged Opus marathon (`OPUS_MARATHON_GOAL_converged.md`).
Branch: `claude/le-replay-expansion`. Candidate-only, synthetic-only.

## Situation

Two trust findings remained open from the F1–F4 workbench hardening pass:

- **F5** — The synthetic rate-card workbench counted named-timekeeper overrides
  (`named_timekeeper_override_count`) but exposed no row-level provenance for
  which catalog cells actually carry an override, and the count reconciled to
  nothing. A stale or fabricated count could pass silently.
- **F6** — The guideline-projection and rejection-appeal workbenches pinned
  their source digests but, unlike the actuals / budget-input / budget-config
  workbenches, had no end-of-build guard that the declared sources stayed
  byte-identical *while the report was being built*. A mid-build source mutation
  was not caught fail-closed by a dedicated typed check.

## Decision

- **F5**: Added a row-level `named_timekeeper_override: bool` flag to
  `SyntheticRateCardWorkbenchRow`, populated from the rate-card YAML by matching
  each declared override to its unique `(carrier, state, title)` catalog cell.
  `named_timekeeper_override_count` is now derived from — and reconciled against —
  the flagged rows in the Python model validator
  (`SyntheticRateCardWorkbenchReport`) and in `data-contract.ts`
  (`assertSyntheticRateCardWorkbenchReport`). A second override colliding on the
  same catalog cell now fails the `named_timekeeper_overrides_valid` check
  (fail-closed) instead of silently reducing the reconciled count. `types.ts`,
  the exported JSON schemas, and the demo fixture were refreshed.
- **F6**: Both builders now capture a single immutable snapshot of their declared
  sources before any read, and emit a
  `source_inputs_unchanged_during_build` check that fails closed if any source
  changed on disk during the build — mirroring
  `tests/test_synthetic_workbench_source_integrity.py`. Added monkeypatched
  mid-build-mutation tests for both builders. Demo fixtures for both workbenches
  (and the Rust fixture manifest + UI review bundle snapshots) were refreshed.

## Non-decision

- No new rule language; the Substrate-owned OCG IR is untouched.
- The rate-card override *rate* resolution path (`rates.py`) is unchanged; the
  flag is catalog provenance only, not a pricing change.
- Row set, dimension counts, and state summaries are unchanged (the flag rides
  on existing schedule rows), so no reimbursement/work-plan math moved.
- No thin-vertical / sizing / exporter work (those are CW1+).

## Authority impact

Local candidate work in `lowelltwong-alt/LawFirm-os-intake`. No canonical/
promoted contract change; no cross-repo write. Candidate schemas only.

## Evidence

- Sources: `config/synthetic-carrier-rate-card.yaml` (3 overrides → 3 distinct
  cells: carrier-a/NV/partner, carrier-a/NV/associate, carrier-b/NV/partner).
- Pinned digests: `fixtures/synthetic/{guideline-projection,rejection-appeal}-workbench/pinned-source-digests.json`.
- Tests: `tests/test_synthetic_rate_card_workbench.py` (3 new),
  `tests/test_synthetic_workbench_source_integrity.py` (2 new).
- Refreshed via the governed `refresh-ui-demo-fixtures --write-fixtures` path
  (Rust hash + snapshot-coherence gates passed).

## Alternatives rejected

- **Emit a separate override row per timekeeper.** Rejected: it would pollute the
  state-summary min/max/avg and role counts with named-timekeeper rates and
  change dimension counts — a larger, riskier change than a trust closeout wants.
- **Flag schedule rows but keep the count as declared-entry count.** Rejected:
  duplicate/invalid overrides could make the count and the flagged rows diverge;
  deriving the count from flagged rows plus a fail-closed duplicate check keeps
  the invariant provable by construction.

## Risks and rollback

- Risk: fixtures/schemas drift out of sync with the model. Contained by the
  exact-render fixture tests, `export_schemas.py` idempotency, and the Rust
  snapshot-coherence gate. Rollback is a single-branch revert; no data migration.

## Validation

Run from `<worktree-root>` with
`PYTHONPATH=src`, `LAWFIRM_OS_VALIDATION_RUNTIME_POLICY=intake-validation-runtime-policy.v1`:

- `python -m ruff check --no-cache src tests scripts` → All checks passed.
- `python -m ruff format --check --no-cache src tests scripts` → all formatted.
- `python scripts/export_schemas.py` → 485 schemas; only the two rate-card
  schemas changed (intended), idempotent thereafter.
- `python scripts/validate_repo.py` → repository validation passed.
- `python scripts/run_full_pytest.py -q` → full suite passed (0 failures).
- `npm run build` (apps/legal-intake-budget) → `tsc -b && vite build` OK.
- `npm run smoke:browser` → all checks passed, no external runtime requests.

## Human gates

CW0 human gate: PR review and merge. This agent opens the PR and stops; it does
not merge its own PR and does not push `main`. Later waves branch off the new
`main` after merge.
