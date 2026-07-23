# Codex Handoff: L&E Replay Expansion — Remaining Stage B Work

Date: 2026-07-21
Base: branch `claude/le-replay-expansion` off `main` (PR #107 head 8cfe030).
Prereq done: Stage A audit + F1/F2 hardening committed (`07e5e57`). See
`docs/decisions/TRACE-2026-07-21-workbench-trust-audit-and-le-replay-expansion.md`.

Keep every fixture synthetic, source-bound, candidate-only, holdout-excluded
from model-visible prompt assembly, and free of connector/Lake/SQLite/submission/
matter-opening/conflict-conclusion/silent-learning writes. Do not weaken any
fail-closed behavior. Do not train/tune XGBoost.

## What already exists (reuse, do not recreate)

- Source bundles for **all 8 families x {clean, adversarial, messy_thread,
  missing_attachment}** already live in
  `examples/synthetic/labor-employment/executable-fixtures/`.
- Seeds and learning-fixtures manifests already declare all 8 families:
  `labor-employment-budget-outcome-replay-seeds.json`,
  `labor-employment-budget-learning-fixtures.json`.
- Executable builder inputs (`replay-inputs/<case>/`) exist only for
  `discrimination-harassment-clean`, `wage-hour-clean`, `epli-carrier-clean`,
  `class-collective-clean`.
- The generation module CONSUMES `replay-inputs/<slug>/legal_budget_proposal.json`
  + `budget_actuals_source.json`; it does not synthesize them.

## Task 1 — Executable replay-inputs for the 3 uncovered families

For each of `retaliation-wrongful-termination-messy-thread`,
`restrictive-covenant-messy-thread`, `admin-exhaustion-clean` create
`examples/synthetic/labor-employment/replay-inputs/<case>/` with:

- `legal_budget_proposal.json` — a valid `BudgetProposal` (see
  discrimination-harassment-clean for the exact shape); `budget_proposal_id`
  `le-budget-<case>.v0_1`, `preflight_packet_id` `le-preflight-<case>.v0_1`,
  `not_authorized_for_client_submission=true`, `data_origin=synthetic`.
- `budget_actuals_source.json` — `BudgetActualsSource` whose `budget_proposal_id`
  matches, with phase and code actuals producing the seed's expected variance
  posture (retaliation/admin = `candidate_range_after_review`; restrictive-
  covenant = `range_or_hours_only`).
- `human_confirmation.json` — mirror an existing case; party names must satisfy
  `_party_name_matches_segment_text` / `_budget_confirmation_anchor_errors`
  against the family source bundle.
- carrier bundle only where the family's `learning_loop_types` includes
  `carrier_rejection_capture` (restrictive-covenant yes; retaliation/admin no).

Then add matching `entries` to
`labor-employment-budget-outcome-replay-input-pack.json` following the existing
per-loop entry pattern (builder_input roles, `confirmation_ref`,
`source_bundle_ref`).

Acceptance: "All eight declared L&E families have executable replay evidence."

## Task 2 — Missing-attachment case reaches replay and blocks/widens

Wire one `*-missing-attachment.source-bundle.json` (already present) into an
input-pack entry / execution path so it reaches replay and the output is blocked
or widened for the stated missing-attachment reason (not silently dropped).
Add a **prohibited-transition** assertion: a missing-attachment case must not
produce a ready submitted-budget/actuals output.

## Task 3 — Non-ADA adversarial case reaches replay

Add an adversarial replay case in a family other than ADA/FMLA (e.g.
`retaliation-wrongful-termination-adversarial` or
`restrictive-covenant-adversarial`; source bundles exist). Give >= 2 distinct
families adversarial replay coverage. Include a **counterfactual/metamorphic**
assertion (e.g. injected source text stays source text, does not become observed
fact) and a **prohibited-transition** assertion.

## Task 4 — Materially different proposal in workbench coverage

The actuals workbench builder (`synthetic_actuals_workbench.py`) is hardcoded to
the EPLI refs (`BUDGET_PROPOSAL_REF`/`ACTUALS_SOURCE_REF`). To exercise a 2nd
family it needs a family selector that also sets `budget_proposal_ref` /
`actuals_source_ref` on the report. Note wage-hour actuals are intentionally
`scoped_partial` (they fail `complete_actuals_coverage` and
`code_actual_total_reconciles`), so a **new complete-coverage** actuals fixture
is required (phase and code both fully cover and reconcile to the same
total_actual). Same idea for the budget-input workbench. Add tests exercising the
2nd family, including the variance/total reconciliation now enforced by F1/F2.

## Task 5 — Update hardcoded test expectations

`tests/test_labor_employment_budget_outcome_replay_input_pack.py` hardcodes
`case_count == 8`, `ready_case_count == 1`, `partial_case_count == 7`,
`ready_input_count == 35`, and per-case counts (discrimination/wage `== 8`, epli
`== 10`, class-collective `== 4` with `missing_input_count == 1`). Adding inputs
for the 3 families raises `ready_input_count` and the per-case ready counts —
recompute and update these, plus the readiness/execution/builder-binding tests
and any Markdown-string assertions (e.g. the "Preflight Gap Matrix" rows).

## Per-case requirements checklist (handoff spec)

data_origin=synthetic; generator version + deterministic seed; source/segment
refs + offsets + hashes where applicable; explicit unknowns/blocked gates;
expected status + reviewed synthetic gold; >=1 counterfactual/metamorphic
assertion; >=1 prohibited-transition assertion; holdout content excluded from
model-visible prompt assembly; no connector/Lake/SQLite/submission/matter-
opening/conflict-conclusion/silent-learning write.

## Also worth folding in (Stage A deferred findings F3-F6)

- F3: bind actuals row fee/expense components to source (not just the row total).
- F4: tie guideline `gross_reductions`/`gross_increases` to line-level deltas.
- F5: remove `named_timekeeper_override_count` or add a row-level override flag
  to reconcile it against.
- F6: give guideline & rejection builders the single captured-snapshot +
  end-of-build unchanged-source check that actuals/input/configuration have.

## Validation gate (Linux, long ceiling)

`python scripts/validate_repo.py`; `python scripts/export_schemas.py`;
`python -m ruff check src tests scripts`; `python -m ruff format --check`;
`python scripts/run_full_pytest.py -q`;
`npm run build --prefix apps/legal-intake-budget`;
`npm run smoke:browser --prefix apps/legal-intake-budget`;
`bash scripts/smoke_demo.sh`. Note: new replay-input files must be `git add`-ed —
the browser smoke rejects untracked replay source refs.
