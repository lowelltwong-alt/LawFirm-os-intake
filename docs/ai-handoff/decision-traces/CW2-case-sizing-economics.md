# Decision Trace — CW2 Case Sizing + Settlement Economics v0

Wave: CW2 of the converged Opus marathon. Branch:
`claude/cw2-case-sizing-economics` (stacked on the CW1 branch; CW0/CW1 PRs not yet
merged). Candidate-only, synthetic-only, deterministic. Exact integer minor units.

## Situation

The converged premortem's "$10k case / $50k budget" problem and the case-sizing
design (`CASE_SIZING_AND_TRAINING_DESIGN.md`) require a sizing + economics layer:
what makes same-type cases differ in cost, a proportionality guard, and
settlement-posture economics — all deterministic and candidate-only, with no
real-world accuracy claim (§21 preserved).

## Decision

A self-contained `case_sizing` module (contract-first, additive — no change to
existing budget/projection fixtures) with:

1. **CaseCostDriver contract** (`CaseCostDriverSpec`/`CaseCostDriverCatalog`) — a
   versioned catalog of 5 drivers (party_count, injury_severity, liability_clarity,
   venue, exposure_band), each declaring measurement (provenance-bound), effect
   surface, and effect form (multiplier | additive | gate). Applied to a base
   work-plan total as exact-minor-unit `CaseSizingEffect`s composed into a
   `SizedWorkPlan` whose total is recomputed fail-closed from the effect chain.
2. **Proportionality gate** (`ProportionalityAssessment`) — budget-to-exposure
   ratio bands per case type; over-band ⇒ `blocked_disproportionate_budget`
   (typed, with the ratio and band) requiring human-override-with-reason; the
   default recommendation is the settle-lean plan. Status and ratio are recomputed
   in the model validator (fail-closed); an override reason never flips the status.
3. **Settlement-posture arithmetic** (`SettlementPostureAnalysis`) — settle-now vs
   defend-then-settle vs try compared by expected total cost of risk (indemnity +
   defense) on declared synthetic inputs (E, S, S', defense envelopes, win-prob
   band p). Ranked postures, a candidate recommended posture, and a budget
   envelope (recommended posture's defense cost). Win probability is a declared
   assumption, never inferred.

Composed by `build_case_sizing_report` into a candidate `CaseSizingReport` whose
validator asserts the sized work-plan total is what proportionality assesses —
the work plan is never overwritten by settlement/reimbursement economics.

## Non-decision

- No wiring into the UI (sizing/posture/exposure panels are CW3) and no change to
  `build_budget_proposal` or existing fixtures — the layer is additive.
- No ML, no calibration, no real-world accuracy claim; p stays a declared input.
- No new rule language; the sizing policy is synthetic candidate data.

## Authority impact

Local candidate work. New candidate schemas only; no canonical/promoted contract
change, no cross-repo write.

## Evidence

- `tests/test_case_sizing.py` — 13 golden + metamorphic tests (failing-test-first).
- `config/synthetic-case-sizing-policy.yaml` (synthetic factors + bands).
- Metamorphic invariants proven: party+1 ⇒ non-decreasing; catastrophic ≥
  soft-tissue; clear ≤ disputed; E↓ ⇒ envelope non-increasing; S≪defense ⇒ settle;
  p↑ ⇒ try-cost ↓.
- Exported schemas for all nine new contracts.

## Alternatives rejected

- **Rewire `build_budget_proposal`'s nonlinear templates directly.** Rejected for
  v1: it would trigger the full budget-fixture cascade for no contract-review
  benefit; the sizing layer composes on a base total and demonstrates the driver
  machinery cleanly. Deeper wiring can follow after contract review.
- **Float money.** Rejected in favor of integer minor units so every
  reconciliation and metamorphic invariant is exact.

## Risks and rollback

- Risk: the synthetic factors/bands are invented and not firm-calibrated — flagged
  for the firm checkpoint (CW5), never presented as real economics. Contained by
  candidate-only status and §21. Rollback is a single-branch revert; the module is
  additive with no consumers yet.

## Validation

From `<worktree-root>` with `PYTHONPATH=src` and the intake validation
runtime policy: ruff check/format clean; `export_schemas.py` idempotent (nine new
schemas); `validate_repo.py` passed; `run_full_pytest.py -q` full suite passed;
`npm run build` + `npm run smoke:browser` OK.

## Human gates

CW2 human gate: **sizing/economics contract review** of the new candidate schemas
and the synthetic policy. Opened by the agent; it does not merge its own PR and
does not push `main`.

## DAD

Preflight/postflight run for this session (trace `dad:trace:c520c714…`, handoff
`dad:handoff:2d6b1724…`); the CW0–CW2 lessons were captured through the canonical
`asset-dir lesson add` pipeline (superseding the mailbox transport) and compiled
into the DAD lesson graph.
