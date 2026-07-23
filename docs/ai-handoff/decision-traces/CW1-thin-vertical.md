# Decision Trace — CW1 Fail-Closed Core Of The Thin Vertical

Wave: CW1 of the converged Opus marathon (`OPUS_MARATHON_GOAL_converged.md`).
Branch: `claude/cw1-thin-vertical-fail-closed` (stacked on the CW0 branch because
PR #108 had not yet merged at wave start). Candidate-only, synthetic-only.

## Situation

The existing Guideline Projection engine had the operationally-wrong failure
modes the converged premortem named: applicability could silently fall open, the
adjustment math was not attributed as an ordered, non-commutative ledger, budget
lines had no stable identity, there was no aggregate task-hour rule, and the
output conflated the firm's work plan with what a carrier guideline would
reimburse.

## Decision

Five contract-first, fail-closed changes on the existing engine + UI:

1. **PackSelectionDecision** — a typed selection (`selected` /
   `blocked_missing_context` / `blocked_overlap` / `no_applicable_pack`) with
   confirmed carrier/program/jurisdiction/as-of, considered packs + exclusion
   reasons, and the selected revision + content hash. A missing or wrong
   confirmed carrier now returns `blocked_missing_context` and the projection is
   blocked — the old `carrier_id or default_carrier_id` fallback (which silently
   priced a missing carrier against the default pack) is gone.
2. **Stable `line_id`** on `BudgetLine`, recomputed fail-closed from the line's
   own identity when absent (never silently empty), threaded onto projection
   lines and used as the UI row key.
3. **Ordered `AdjustmentLedger`** in exact integer minor units: one entry per
   rule effect (`before`/`after`/`delta`/`rule_id`/`line_id` span) in the
   declared attribution order (pack/effective → task-hour caps → staffing → rate
   caps → expense caps → disallowance → contingency → unsupported). The model
   validator recomputes per-rule deltas and requires them to sum to the category
   deltas and the total, fail-closed.
4. **One aggregate task×role hour cap** (`L330`/`senior_associate`), wired
   end-to-end: proportional per-line compliant hours, a distinct `task_hour_cap`
   fee reduction computed on the rate-shaped fees (never overlapping the
   rate/staffing deltas), reflected in the projection totals, the coherence
   partition check, and ordered first among the money rules in the ledger.
5. **Output-language split** — `ProjectionReport` keeps `work_plan_total` (the
   immutable proposal baseline, never overwritten by reimbursement math),
   `guideline_adjusted_reimbursement`, and `unreimbursed_exposure` (recomputed
   fail-closed) semantically separate, rendered in the read-only UI with the
   existing candidate banners.

## Non-decision

- The budget core still does not depend on the guideline compiler; the projection
  composes on top of the immutable proposal.
- No new rule language: the hour cap is expressed as data in the synthetic
  guideline pack, reconciled with (not authored into) the Substrate OCG IR; no
  canonical rule IDs are minted.
- Case sizing, settlement economics, the exporter seam, and the routing eval are
  CW2+ and untouched here.

## Authority impact

Local candidate work in `lowelltwong-alt/LawFirm-os-intake`. No canonical or
promoted contract change; no cross-repo write. New local candidate schemas only.

## Evidence

- New tests (failing-test-first): `tests/test_pack_selection.py`,
  `tests/test_budget_line_id.py`, `tests/test_adjustment_ledger.py`,
  `tests/test_task_hour_cap.py`, `tests/test_projection_report_output_split.py`.
- Guideline workbench builds `ready_for_review` with the hour cap; its ledger
  reconciles exactly to the signed net delta (e.g. carrier-a net 25874.5 ==
  ledger total 2,587,450 minor units).
- Refreshed the guideline pinned source-digest manifest, the guideline/rejection
  demo fixtures, and the Rust fixture-manifest + UI review-bundle snapshots via
  the governed `refresh-ui-demo-fixtures` path.

## Alternatives rejected

- **Fold the hour cap into rate-cap math.** Rejected: it would misattribute the
  hour reduction; computing it on the rate-shaped fees as its own delta keeps the
  attribution exact and non-overlapping.
- **Emit projection lines with hour-reduced `proposed_hours`.** Rejected: it
  would destroy the proposed-vs-compliant distinction; the reduction lives on the
  compliant side only.
- **Represent ledger money as floats.** Rejected in favor of integer minor units
  so the fail-closed reconciliation is exact.

## Risks and rollback

- Risk: the new projection fields drift out of sync with fixtures/schemas.
  Contained by `export_schemas.py` idempotency, the exact-render fixture tests,
  the coherence partition check, and the Rust snapshot-coherence gate. Rollback is
  a single-branch revert; no data migration.

## Validation

From `C:/Users/lowel/lfw-le` with `PYTHONPATH=src` and
`LAWFIRM_OS_VALIDATION_RUNTIME_POLICY=intake-validation-runtime-policy.v1`:

- `ruff check` + `ruff format --check` — clean.
- `export_schemas.py` — idempotent.
- `validate_repo.py` — passed.
- `run_full_pytest.py -q` — full suite passed.
- `npm run build` (`tsc -b && vite build`) — OK.
- `npm run smoke:browser` — passed, no external runtime requests.

## Human gates

CW1 human gate: **contract review** of the new candidate schemas
(PackSelectionDecision, AdjustmentLedger, ProjectionReport, line_id, task-hour
cap). Opened by the agent; it does not merge its own PR and does not push `main`.
